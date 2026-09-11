import streamlit as st
from datetime import date
from google import genai
import base64

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.6-flash"

# ------------------------------------------------------------
# SESSION USAGE
# ------------------------------------------------------------
if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { padding-top: 1rem; }
    .app-title {
        text-align: center;
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 15px;
        margin-bottom: 25px;
    }
    .section {
        font-size: 21px;
        font-weight: 650;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .info-box {
        padding: 15px;
        border-radius: 12px;
        background: #f5f7fa;
        margin-top: 10px;
        margin-bottom: 15px;
    }
    .disclaimer {
        font-size: 12px;
        color: #666;
        padding: 12px;
        border-radius: 10px;
        background: #f7f7f7;
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="app-title">🦷 AMRs Dental X-ray AI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">AI-Assisted Dental Radiographic Assessment</div>',
    unsafe_allow_html=True,
)

remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count

if remaining > 0:
    st.info(
        f"🧪 AI analyses remaining today: "
        f"{remaining} / {DAILY_ANALYSIS_LIMIT}"
    )
else:
    st.warning(
        "⏳ Your 3 AI analyses for today have been used. "
        "Please try again tomorrow."
    )

# ------------------------------------------------------------
# PATIENT INFORMATION
# ------------------------------------------------------------
st.markdown(
    '<div class="section">👤 Patient Information</div>',
    unsafe_allow_html=True,
)

patient_name = st.text_input(
    "Patient Name",
    placeholder="Enter patient name",
)

col1, col2 = st.columns(2)

with col1:
    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        value=0,
        step=1,
    )

with col2:
    sex = st.selectbox(
        "Sex",
        ["Select", "Male", "Female", "Other"],
    )

op_number = st.text_input(
    "OP Number",
    placeholder="Enter OP number",
)

examination_date = st.date_input(
    "Examination Date",
    value=date.today(),
)

# ------------------------------------------------------------
# RADIOGRAPH TYPE
# ------------------------------------------------------------
st.markdown(
    '<div class="section">🩻 Radiograph Type</div>',
    unsafe_allow_html=True,

)
radiograph_type = st.selectbox(
    "Select radiograph type",
    [
        "IOPA",
        "OPG",
        "Bitewing",
        "Occlusal",
        "Facial radiograph",
        "Lateral Cephalogram (Ceph)",
        "Other / Not reliably classifiable",
    ],
)

st.info(f"🩻 Selected radiograph: {radiograph_type}")


# ------------------------------------------------------------
# CEPHALOMETRIC ANALYSIS
# Show ONLY when Lateral Cephalogram is selected
# ------------------------------------------------------------

ceph_analysis = None

if radiograph_type == "Lateral Cephalogram (Ceph)":

    CEPH_ANALYSES = [
        "Steiner",
        "Downs",
        "McNamara",
        "Tweed",
        "Wits Appraisal",
        "Jarabak",
        "Soft Tissue",
        "Combined / All Analyses",
    ]

    ceph_analysis = st.selectbox(
        "Select the analysis you want to perform",
        CEPH_ANALYSES,
        key="ceph_analysis_selector",
    )

    st.info(f"📊 Selected Ceph analysis: {ceph_analysis}")


# ------------------------------------------------------------
# UPLOAD
# ------------------------------------------------------------
st.markdown(
    '<div class="section">📤 Upload Dental Radiograph</div>',
    unsafe_allow_html=True,
)

st.info("Upload a dental X-ray image in JPG, JPEG or PNG format.")

xray = st.file_uploader(
    "📷 Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
    key="dental_xray_upload",
)

# ------------------------------------------------------------
# COMMON SAFETY PROMPT
# ------------------------------------------------------------
SAFETY_RULES = """
You are AMRs Dental X-ray AI.

You are an AI-assisted radiographic assessment system for
qualified dental professionals.

CORE PRINCIPLE:
The actual uploaded radiograph is the source of truth.

SAFETY RULES:
1. Analyze ONLY the actual uploaded image.
2. Never invent, hallucinate, or fabricate findings.
3. Never use random, fixed, default, or predetermined findings.
4. Report only findings supported by visible image evidence.
5. If something cannot be assessed reliably, say:
   "Not clearly assessable."
6. Do not diagnose something merely because it is common.
7. Do not force every checklist item into the report.
8. Describe normal anatomy only when it is actually visible.
9. Report pathology only when actual visual evidence supports it.
10. Do not generate a long list of diseases merely to say absent.
11. Clearly distinguish clearly visible, possible, and unclear findings.
12. Use FDI tooth numbers only when reliably identifiable from anatomy.
13. Never assign an FDI number from image position alone.
14. Do not provide a definitive diagnosis.
15. Do not prescribe medication.
16. Do not provide definitive treatment planning.
17. Do not use patient information to create radiographic findings.
18. When uncertain, choose uncertainty rather than guessing.
19. Final diagnosis and treatment decisions must be made by a qualified
    dental professional.
"""

# ------------------------------------------------------------
# RADIOGRAPH PROMPTS
# ------------------------------------------------------------
IOPA_PROTOCOL = """
IOPA SYSTEMATIC ASSESSMENT

Assess the actual uploaded IOPA systematically.

IMAGE QUALITY:
- Exposure
- Contrast
- Sharpness
- Positioning
- Cropping
- Cone cut
- Distortion
- Other technical limitations

DENTAL STRUCTURES:
- Crowns
- Roots
- Visible teeth
- Obvious caries
- Obvious restorations
- Gross tooth abnormalities
- Root morphology when visible

PERIODONTAL STRUCTURES:
- Lamina dura when visible
- Periodontal ligament space when visible
- Alveolar crest
- Obvious periodontal bone loss

PERIAPICAL REGION:
- Periapical radiolucency
- Periapical radiopacity
- Root abnormalities
- Other visible periapical findings

OTHER:
- Impacted or unerupted teeth when clearly visible
- Other obvious abnormalities

Do not automatically label a periapical lesion as abscess,
granuloma, or cyst when the image does not support that distinction.
Describe the radiographic appearance and uncertainty.
"""

OPG_PROTOCOL = """
OPG SYSTEMATIC PANORAMIC ASSESSMENT

Perform a systematic panoramic assessment from one side to the
other and then review the entire image.

The following are TARGETS TO INSPECT, not findings that must
appear in the report.

1. IMAGE QUALITY AND ARTIFACTS
Inspect:
- Positioning
- Rotation
- Head tilt
- Anteroposterior positioning
- Exposure
- Motion blur
- Cropping
- Magnification
- Distortion
- Superimposition
- Ghost images

Ghost images are artifacts, not pathology. Report them only
when an actual artifact is visible.

2. ANATOMICAL LANDMARKS
When actually visible, inspect:
- Incisive foramen
- Median palatal suture
- Nasal fossa
- Nasal septum
- Maxillary sinus
- Zygomatic process of maxilla
- Zygomatic arch
- Pterygoid plates
- Pterygoid hamulus
- Coronoid process
- Condyles
- Mandibular ramus
- Mandibular angle
- Lingual foramen
- Genial tubercles
- Mental foramen
- Inferior alveolar canal
- Mylohyoid ridge
- External oblique ridge
- Inferior border of mandible
- Glossopalatal air space
- Nasopharyngeal air space

Do not force identification of a landmark that is not adequately
visualized.

3. DENTITION
Inspect:
- Present teeth
- Missing teeth when reliably evident
- Unerupted teeth
- Impacted teeth
- Impacted third molars
- Impacted canines
- Supernumerary teeth
- Odontomes
- Gross developmental abnormalities
- Obvious caries
- Obvious restorations
- Gross root abnormalities
- Actual periapical abnormalities

Use FDI numbering only when anatomically reliable.

4. PERIODONTAL STRUCTURES
Inspect:
- Alveolar crest
- General alveolar bone level
- Obvious horizontal bone loss
- Obvious vertical/angular bone loss
- Other clearly visible periodontal changes

Do not overcall subtle bone-level changes.

5. PERIAPICAL / DENTOALVEOLAR FINDINGS
Look for actual evidence of:
- Periapical radiolucency
- Periapical radiopacity
- Inflammatory-looking periapical changes
- Root abnormalities
- Other dentoalveolar abnormalities

Do not automatically call a lesion an abscess, granuloma,
or radicular cyst unless the image supports that conclusion.

6. ODONTOGENIC CYSTS / TUMORS / LESIONS
Inspect for actual image-supported evidence of:
- Dentigerous cyst
- Radicular cyst
- Odontogenic keratocyst (OKC)
- Ameloblastoma
- Odontome
- Other odontogenic lesions

These are screening targets only. Do not report them merely
because they are listed here.

If a lesion is visible but its exact diagnosis is uncertain,
describe:
- Radiolucent / radiopaque / mixed appearance
- Location
- Relationship to teeth
- Borders if visible
- Effect on surrounding structures if visible
- Confidence

7. MAXILLA AND MAXILLARY SINUSES
When visible, inspect:
- Maxillary bone
- Maxillary sinus
- Sinus outline
- Obvious opacification
- Air-fluid level
- Gross mucosal thickening when clearly visible
- Other obvious abnormalities

Do not provide a definitive medical sinus diagnosis.

8. MANDIBLE
When visible, inspect:
- Body
- Inferior border
- Ramus
- Angle
- Alveolar process
- Cortical outline
- Inferior alveolar canal
- Mental foramina
- Other obvious abnormalities

9. TMJ / CONDYLES
When adequately visualized, inspect:
- Condylar size
- Condylar shape
- Gross asymmetry
- Gross deformity
- Obvious enlargement
- Obvious reduction in size

Do not definitively diagnose condylar hyperplasia or hypoplasia
from an OPG alone.

10. BONY ABNORMALITIES
Inspect for actual evidence of:
- Osteomyelitis-related changes
- Fibrous-dysplasia-like changes
- Other radiolucent lesions
- Other radiopaque lesions
- Cortical expansion
- Cortical destruction
- Other gross bony abnormalities

Do not diagnose from vague density changes alone.

OPG REPORTING RULE:
Do not output a huge checklist of diseases with "absent".
Describe relevant anatomy actually visualized and report only
actual abnormalities supported by the image.
"""

BITEWING_PROTOCOL = """
BITEWING SYSTEMATIC ASSESSMENT

Inspect:
- Interproximal surfaces
- Obvious interproximal caries
- Occlusal surfaces when visible
- Existing restorations
- Alveolar crest
- Obvious periodontal bone loss
- Obvious calculus when visible
- Other clearly visible findings

Do not label subtle radiolucencies as caries without evidence.
"""

OCCLUSAL_PROTOCOL = """
OCCLUSAL RADIOGRAPH SYSTEMATIC ASSESSMENT

Inspect:
- Teeth
- Unerupted/developing teeth
- Jaw structures
- Cortical outlines
- Gross bony abnormalities
- Obvious radiolucencies
- Obvious radiopacities
- Supernumerary teeth when clearly visible
- Other clearly visible abnormalities

Report only actual image-supported findings.
"""

FACIAL_PROTOCOL = """
FACIAL BONE / TRAUMA SYSTEMATIC ASSESSMENT

The main purpose is conservative assessment of visible facial
bones and screening for obvious traumatic bony abnormalities.

1. IMAGE QUALITY
Assess:
- Positioning
- Rotation
- Exposure
- Sharpness
- Motion
- Cropping
- Superimposition
- Whether relevant facial bones are adequately included

2. FACIAL BONES
When included and visible, inspect:
- Nasal bones
- Nasal septum
- Orbital margins
- Orbital walls
- Zygomatic bones
- Zygomatic arches
- Zygomaticomaxillary region
- Maxillary bones
- Maxillary sinus walls
- Frontal facial bone regions
- Alveolar processes
- Mandible if included

3. FRACTURE SCREENING
Look for actual evidence of:
- Fracture line
- Cortical discontinuity
- Step deformity
- Displacement
- Abnormal alignment
- Gross traumatic asymmetry
- Other obvious traumatic bony abnormalities

If convincing evidence is present, describe:
- Location
- Visible fracture features
- Displacement if visible
- Confidence

If suspicious but insufficient:
"Possible fracture — requires professional radiographic and
clinical correlation."

Never call an uncertain fracture confirmed.

4. ASSOCIATED FINDINGS
When actually visible, inspect for:
- Maxillary sinus opacification
- Air-fluid level
- Radiographically visible soft-tissue swelling
- Other associated abnormalities

Do not automatically attribute these findings to trauma.

5. LIMITATIONS
If a facial region is not adequately visualized, state:
"Not reliably assessable on this radiograph."

Do not assume a fracture is absent merely because the region
cannot be evaluated.
Do not provide definitive fracture treatment or management.
"""

TWEED_PROTOCOL = """
TWEED CEPHALOMETRIC ANALYSIS — CORE

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE TWEED PARAMETERS WHEN RELIABLY MEASURABLE:
- FMA: Frankfort horizontal to mandibular plane angle
- IMPA: long axis of mandibular central incisor to mandibular plane
- FMIA: long axis of mandibular central incisor to Frankfort horizontal

TWEED TRIANGLE:
- Assess the relationship among FMA, IMPA, and FMIA.
- If all three required measurements are reliably available, report
  the measured values and describe the overall incisor inclination /
  vertical skeletal relationship conservatively.
- Do not force a Tweed classification when landmarks or incisor axes
  are unclear.

LANDMARK / REFERENCE REQUIREMENTS:
- Porion and Orbitale (or a reliably established Frankfort horizontal)
- Gonion and Menton for mandibular plane
- Long axis of the mandibular central incisor

REPORTING:
- Give numerical values only when the relevant landmarks and planes
  can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not use Tweed norms as a substitute for visible image evidence.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

DOWNS_PROTOCOL = """
DOWNS CEPHALOMETRIC ANALYSIS — CORE

Analyze only a true lateral cephalogram. First assess image quality and
landmark visibility. Do not invent landmarks or measurements.

CORE DOWNS PARAMETERS WHEN RELIABLY MEASURABLE:
- Facial angle
- Angle of convexity
- A-B plane angle
- Mandibular plane angle
- Y-axis
- Occlusal plane angle
- Interincisal angle
- Lower incisor to mandibular plane angle (IMPA)

INTERPRETATION:
- Assess sagittal skeletal relationship and facial convexity.
- Assess vertical growth tendency from relevant measurements.
- Assess dental/incisor inclination where visible.
- Do not classify a skeletal or dental pattern when required landmarks
  are not reliably identified.

For every unavailable measurement state: "Not reliably assessable."
"""

JARABAK_PROTOCOL = """
JARABAK CEPHALOMETRIC ANALYSIS — CORE

Assess Jarabak analysis only on a true lateral cephalogram. These are measurement targets, not findings that must appear.

LANDMARKS / CONSTRUCTION:
- Sella (S)
- Nasion (N)
- Articulare (Ar)
- Gonion (Go)
- Menton (Me)
- S-N anterior cranial base
- S-Ar posterior cranial base
- Ar-Go ramus height
- Go-Me mandibular body length
- S-Go posterior facial height
- N-Me anterior facial height
- Go-Me mandibular plane

CORE PARAMETERS WHEN RELIABLY MEASURABLE:
- S-N length
- S-Ar length
- Ar-Go length
- Go-Me length
- S-Go posterior facial height
- N-Me anterior facial height
- Jarabak ratio = S-Go / N-Me × 100
- Gonial angle (Ar-Go-Me)

INTERPRETATION:
- Assess facial-height proportions and apparent vertical growth tendency conservatively.
- Consider the overall cephalometric pattern rather than relying on one measurement alone.
- Separate measured values from interpretation.

SAFETY:
- Identify landmarks only when actually visible and sufficiently defined.
- If a landmark or measurement is unclear, state: "Not reliably assessable."
- Never fabricate mm values, angles, ratios, or landmark coordinates.
- Do not infer values from age, sex, or expected norms.
- Norms vary with population, age, sex, growth status, tracing method, and convention.
- Do not provide a definitive orthodontic diagnosis or treatment plan.
"""

OTHER_PROTOCOL = """
OTHER / UNCLASSIFIED RADIOGRAPH

First determine whether the uploaded image appears to be a
dental or maxillofacial radiograph.

State whether the selected type appears compatible.

If uncertain, state:
"Radiograph type cannot be reliably classified."

Then describe only:
- Clearly visible structures
- Actual image-supported findings
- Important limitations

Do not force a diagnosis or invent missing structures.
"""

WITS_PROTOCOL = r"""
WITS APPRAISAL — CORE PROTOCOL

Assess Wits appraisal only on a true lateral cephalogram when A point, B point and the functional occlusal plane are clearly visible.

1. LANDMARKS / CONSTRUCTION
- Identify A point and B point reliably.
- Identify the functional occlusal plane used for Wits appraisal.
- Project perpendiculars from A and B to the occlusal plane to obtain AO and BO.
- Do not invent landmark locations or measurements.

2. MEASUREMENT
- Determine the AO–BO linear relationship along the occlusal plane.
- Report the relationship and direction only when reliably measurable.
- Do not fabricate millimetre values.

3. INTERPRETATION
- Use Wits as a supplementary assessment of anteroposterior/sagittal jaw relationship.
- If adequately measurable, describe whether the relationship is relatively Class II tendency, relatively Class III tendency, or approximately balanced, using appropriate reference context.
- Wits alone must not establish a definitive orthodontic diagnosis.

4. SAFETY / LIMITATIONS
- Wits is sensitive to construction of the occlusal plane and dental factors.
- If A point, B point or the occlusal plane is unclear, state: “Not reliably assessable.”
- Never infer a numeric value from a typical or expected result.
- No definitive diagnosis or treatment plan.

OUTPUT
WITS APPRAISAL
- Landmark/occlusal-plane visibility: Clear / Limited / Poor
- AO: [value/description or Not reliably assessable]
- BO: [value/description or Not reliably assessable]
- AO–BO relationship: [value/description or Not reliably assessable]
- Sagittal implication: [image-supported interpretation or Not reliably assessable]
- Limitations/uncertainty: [brief]
"""



SOFT_TISSUE_PROTOCOL = """
SOFT-TISSUE CEPHALOMETRIC ANALYSIS — CORE

Assess the soft-tissue profile ONLY when the lateral cephalogram clearly
shows the relevant soft-tissue outline and landmarks.

TARGETS TO ASSESS (not findings that must be present):
- Soft-tissue Nasion (N')
- Pronasale (Prn)
- Subnasale (Sn)
- Labrale superius (Ls)
- Labrale inferius (Li)
- Soft-tissue Pogonion (Pog')
- Menton (Me') when visible
- Facial profile / overall convexity
- Lip prominence and lip position relative to the facial reference line
- Nasolabial angle when landmarks are reliably visible
- Mentolabial sulcus when reliably visible

RULES:
- Do not invent landmark positions or numeric measurements.
- Do not estimate measurements from an unclear profile.
- If a soft-tissue landmark is obscured or poorly visualized, state:
  "Not reliably assessable."
- Distinguish direct visual observations from measurements.
- Do not infer skeletal diagnosis from soft-tissue appearance alone.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""
# ------------------------------------------------------------
# CEPHALOMETRIC ANALYSIS LIST
# ------------------------------------------------------------

CEPH_ANALYSES = [
    "Steiner",
    "Downs",
    "McNamara",
    "Tweed",
    "Wits Appraisal",
    "Jarabak",
    "Soft Tissue",
    "Combined / All Analyses",
]


# ------------------------------------------------------------
# STEINER PROTOCOL
# ------------------------------------------------------------

STEINER_PROTOCOL = """
STEINER CEPHALOMETRIC ANALYSIS

Analyze only a true lateral cephalogram.

Assess when reliably visible:
- SNA
- SNB
- ANB
- SN-GoGn
- U1-NA
- L1-NB
- Interincisal angle
- Relevant soft-tissue observations when visible

Use only reliably identified landmarks.

Do not invent landmark positions or numerical measurements.

If a measurement cannot be reliably assessed, state:
"Not reliably assessable."

Separate measured findings from interpretation.

Do not provide definitive orthodontic diagnosis or treatment planning.
"""


# ------------------------------------------------------------
# McNAMARA PROTOCOL
# ------------------------------------------------------------

MCNAMARA_PROTOCOL = """
McNAMARA CEPHALOMETRIC ANALYSIS

Analyze only a true lateral cephalogram.

Assess when reliably visible:
- Maxillary position relative to cranial base
- Mandibular position relative to cranial base
- Effective midface length
- Effective mandibular length
- Maxillomandibular differential
- Lower anterior facial height
- Mandibular plane angle
- Upper and lower incisor position when reliably visible
- Airway-related structures only when clearly visualized

Do not invent landmarks, measurements, or airway findings.

If a parameter cannot be reliably assessed, state:
"Not reliably assessable."

Use conservative interpretation only.

Do not provide definitive orthodontic diagnosis or treatment planning.
"""


# ------------------------------------------------------------
# CEPH PROTOCOL ROUTING
# ------------------------------------------------------------

def get_protocol(selected_type, selected_ceph_analysis=None):

    if selected_type == "Lateral Cephalogram (Ceph)":

        if selected_ceph_analysis == "Steiner":
            return STEINER_PROTOCOL

        if selected_ceph_analysis == "Downs":
            return DOWNS_PROTOCOL

        if selected_ceph_analysis == "McNamara":
            return MCNAMARA_PROTOCOL

        if selected_ceph_analysis == "Tweed":
            return TWEED_PROTOCOL

        if selected_ceph_analysis == "Wits Appraisal":
            return WITS_PROTOCOL

        if selected_ceph_analysis == "Jarabak":
            return JARABAK_PROTOCOL

        if selected_ceph_analysis == "Soft Tissue":
            return SOFT_TISSUE_PROTOCOL

        return (
            STEINER_PROTOCOL
            + "\n\n"
            + DOWNS_PROTOCOL
            + "\n\n"
            + MCNAMARA_PROTOCOL
            + "\n\n"
            + TWEED_PROTOCOL
            + "\n\n"
            + WITS_PROTOCOL
            + "\n\n"
            + JARABAK_PROTOCOL
            + "\n\n"
            + SOFT_TISSUE_PROTOCOL
        )

    if selected_type == "IOPA":
        return IOPA_PROTOCOL

    if selected_type == "OPG":
        return OPG_PROTOCOL

    if selected_type == "Bitewing":
        return BITEWING_PROTOCOL

    if selected_type == "Occlusal":
        return OCCLUSAL_PROTOCOL

    if selected_type == "Facial radiograph":
        return FACIAL_PROTOCOL

    return OTHER_PROTOCOL


# ------------------------------------------------------------
# BUILD PROMPT
# ------------------------------------------------------------

def build_prompt(selected_type, selected_ceph_analysis=None):

    protocol = get_protocol(
        selected_type,
        selected_ceph_analysis,
    )

    selected_analysis_text = ""

    if selected_type == "Lateral Cephalogram (Ceph)":
        selected_analysis_text = f"""

SELECTED CEPHALOMETRIC ANALYSIS:
{selected_ceph_analysis}

Perform ONLY the selected cephalometric analysis.

Do not perform other cephalometric analyses unless
"Combined / All Analyses" is selected.
"""

    return SAFETY_RULES + "\n\n" + protocol + f"""

SELECTED RADIOGRAPH TYPE:
{selected_type}

{selected_analysis_text}

Analyze ONLY the actual uploaded image.

The uploaded image is the ONLY source of radiographic truth.

Do not use patient name, OP number, age, or sex to create
radiographic findings.

Do not invent landmarks, measurements, coordinates,
angles, ratios, or findings.

If something cannot be reliably assessed, state:
"Not reliably assessable."

REPORT FORMAT:

# AMRs Dental X-ray AI

## Provisional Radiographic / Cephalometric Assessment

### 1. Image Quality
State:
- Adequate / Limited / Poor
- Reason
- Important technical limitations

### 2. Selected Analysis
State the selected analysis.

### 3. Landmarks / Structures Actually Visualized
Describe only landmarks and structures genuinely visible.

### 4. Measurements
Report numerical measurements ONLY when reliably measurable.

For unavailable measurements:
"Not reliably assessable."

### 5. Image-Supported Findings
Report only findings supported by the uploaded image.

### 6. Interpretation
Give a conservative provisional interpretation.

Do not convert uncertain findings into a definitive diagnosis.

### 7. Limitations / Uncertainty
Clearly mention unclear landmarks, poor image quality,
superimposition, or other limitations.

### 8. Professional Review
Recommend review by a qualified dental professional.

Do not provide definitive treatment planning.

FINAL STATEMENT:

"This is an AI-assisted provisional assessment and not a
definitive diagnosis. Final interpretation, diagnosis and
treatment decisions must be made by a qualified dental professional."
"""


# ------------------------------------------------------------
# IMAGE + ANALYSIS
# ------------------------------------------------------------

if xray is not None:

    st.success("✅ X-ray uploaded successfully.")

    st.markdown(
        '<div class="section">🖼️ X-ray Preview</div>',
        unsafe_allow_html=True,
    )

    st.image(
        xray,
        caption="Uploaded Dental Radiograph",
        use_container_width=True,
    )

    st.markdown(
        f"""
        <div class="info-box">
        <b>File:</b> {xray.name}<br>
        <b>Type:</b> {xray.type}<br>
        <b>Size:</b> {xray.size / 1024:.1f} KB
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section">🤖 AI Assessment</div>',
        unsafe_allow_html=True,
    )

    analyze = st.button(
        "🔍 Analyze X-ray",
        use_container_width=True,
        disabled=(
            st.session_state.analysis_count
            >= DAILY_ANALYSIS_LIMIT
        ),
    )

    if analyze:

        if st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT:

            st.warning(
                "⏳ Daily AI analysis limit reached. "
                "Please try again tomorrow."
            )

        else:

            api_key = st.secrets.get("GEMINI_API_KEY")

            if not api_key:

                st.error("❌ GEMINI_API_KEY was not found.")

                st.info(
                    "Open Streamlit Secrets and configure "
                    "GEMINI_API_KEY."
                )

            else:

                mime_type = xray.type

                if mime_type not in [
                    "image/jpeg",
                    "image/png",
                ]:

                    st.error(
                        "❌ Unsupported image format."
                    )

                else:

                    try:

                        client = genai.Client(
                            api_key=api_key
                        )

                        image_bytes = xray.getvalue()

                        image_base64 = base64.b64encode(
                            image_bytes
                        ).decode("utf-8")

                        final_prompt = build_prompt(
                            radiograph_type,
                            ceph_analysis,
                        )

                        with st.spinner(
                            "🔬 Analyzing the uploaded radiograph..."
                        ):

                            interaction = client.interactions.create(
                                model=MODEL_NAME,
                                input=[
                                    {
                                        "type": "image",
                                        "mime_type": mime_type,
                                        "data": image_base64,
                                    },
                                    {
                                        "type": "text",
                                        "text": final_prompt,
                                    },
                                ],
                            )

                        result_text = getattr(
                            interaction,
                            "output_text",
                            None,
                        )

                        if result_text:

                            st.session_state.analysis_count += 1

                            st.success(
                                "✅ AI assessment completed."
                            )

                            st.markdown(
                                '<div class="section">'
                                '📋 Assessment Report'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            st.markdown(result_text)

                            st.markdown(
                                '<div class="section">'
                                '📄 Examination Information'
                                '</div>',
                                unsafe_allow_html=True,
                            )

                            st.write(
                                f"**Radiograph:** "
                                f"{radiograph_type}"
                            )

                            if ceph_analysis:
                                st.write(
                                    f"**Cephalometric Analysis:** "
                                    f"{ceph_analysis}"
                                )

                            st.write(
                                f"**Examination Date:** "
                                f"{examination_date}"
                            )

                            if age > 0:
                                st.write(
                                    f"**Age:** {age}"
                                )

                            if sex != "Select":
                                st.write(
                                    f"**Sex:** {sex}"
                                )

                        else:

                            st.warning(
                                "⚠️ The AI returned no readable assessment."
                            )

                            st.info(
                                "Please try again with a clearer radiograph."
                            )

                    except Exception as error:

                        st.error(
                            "❌ AI analysis failed."
                        )

                        with st.expander(
                            "Technical error details"
                        ):
                            st.code(str(error))


# ------------------------------------------------------------
# DISCLAIMER
# ------------------------------------------------------------

st.markdown(
    """
    <div class="disclaimer">
    <b>⚠️ Important Medical Disclaimer</b><br><br>

    AMRs Dental X-ray AI provides an AI-assisted provisional
    radiographic assessment for decision support only.<br><br>

    It does not replace clinical examination, professional
    radiographic interpretation, definitive diagnosis, or
    treatment planning.<br><br>

    The AI may make mistakes or may be unable to reliably
    assess an image.<br><br>

    Final diagnosis and treatment decisions must always be
    made by a qualified dental professional.
    </div>
    """,
    unsafe_allow_html=True,
)
