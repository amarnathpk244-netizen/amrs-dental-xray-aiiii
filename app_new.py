import streamlit as st
from datetime import date
from google import genai
import base64

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered"
)

# ============================================================
# SETTINGS
# ============================================================

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.6-flash"

# ============================================================
# DAILY USAGE
# ============================================================

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()

# ============================================================
# MOBILE UI
# ============================================================

st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }

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
    unsafe_allow_html=True
)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="app-title">🦷 AMRs Dental X-ray AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-Assisted Dental Radiographic Assessment'
    '</div>',
    unsafe_allow_html=True
)

# ============================================================
# USAGE STATUS
# ============================================================

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

# ============================================================
# PATIENT INFORMATION
# ============================================================

st.markdown(
    '<div class="section">👤 Patient Information</div>',
    unsafe_allow_html=True
)

patient_name = st.text_input(
    "Patient Name",
    placeholder="Enter patient name"
)

col1, col2 = st.columns(2)

with col1:
    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        value=0,
        step=1
    )

with col2:
    sex = st.selectbox(
        "Sex",
        [
            "Select",
            "Male",
            "Female",
            "Other"
        ]
    )

op_number = st.text_input(
    "OP Number",
    placeholder="Enter OP number"
)

examination_date = st.date_input(
    "Examination Date",
    value=date.today()
)

# ============================================================
# RADIOGRAPH TYPE
# ============================================================

st.markdown(
    '<div class="section">🩻 Radiograph Type</div>',
    unsafe_allow_html=True
)

radiograph_type = st.selectbox(
    "Select radiograph type",
    [
        "IOPA",
        "OPG",
        "Bitewing",
        "Occlusal",
        "Facial radiograph",
        "Other / Not reliably classifiable"
    ]
)

st.info(
    f"🩻 Selected radiograph: {radiograph_type}"
)

# ============================================================
# X-RAY UPLOAD
# ============================================================

st.markdown(
    '<div class="section">📤 Upload Dental Radiograph</div>',
    unsafe_allow_html=True
)

st.info(
    "Upload a dental X-ray image in JPG, JPEG or PNG format."
)

xray = st.file_uploader(
    "📷 Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
    key="dental_xray_upload"
)

# ============================================================
# IMAGE PREVIEW
# ============================================================

if xray is not None:

    st.success(
        "✅ X-ray uploaded successfully."
    )

    st.markdown(
        '<div class="section">🖼️ X-ray Preview</div>',
        unsafe_allow_html=True
    )

    st.image(
        xray,
        caption="Uploaded Dental Radiograph",
        use_container_width=True
    )

    st.markdown(
        f"""
        <div class="info-box">
        <b>File:</b> {xray.name}<br>
        <b>Type:</b> {xray.type}<br>
        <b>Size:</b> {xray.size / 1024:.1f} KB
        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # AI ANALYSIS
    # ========================================================

    st.markdown(
        '<div class="section">🤖 AI Assessment</div>',
        unsafe_allow_html=True
    )

    analyze = st.button(
        "🔍 Analyze X-ray",
        use_container_width=True,
        disabled=(
            st.session_state.analysis_count
            >= DAILY_ANALYSIS_LIMIT
        )
    )

    # ========================================================
    # ANALYZE
    # ========================================================

    if analyze:

        if (
            st.session_state.analysis_count
            >= DAILY_ANALYSIS_LIMIT
        ):

            st.warning(
                "⏳ Daily AI analysis limit reached. "
                "Please try again tomorrow."
            )

        else:

            try:

                # ====================================================
                # GEMINI API
                # ====================================================

                api_key = st.secrets["GEMINI_API_KEY"]

                client = genai.Client(
                    api_key=api_key
                )

                # ====================================================
                # IMAGE DATA
                # ====================================================

                image_bytes = xray.getvalue()
                mime_type = xray.type

                if mime_type not in [
                    "image/jpeg",
                    "image/png"
                ]:

                    st.error(
                        "❌ Unsupported image format."
                    )

                    st.stop()

                image_base64 = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                # ====================================================
                # GLOBAL SAFETY RULES
                # ====================================================

                safety_rules = """
You are AMRs Dental X-ray AI.

You are an AI-assisted radiographic assessment system
for qualified dental professionals.

CORE PRINCIPLE:
The actual uploaded radiograph is the source of truth.

Analyze only what is visually supported by the uploaded
image.

SAFETY RULES:

1. Never invent or hallucinate findings.

2. Never use random, fixed, default, or predetermined
radiographic findings.

3. Report only findings supported by actual image evidence.

4. If something cannot be assessed reliably, say:
"Not clearly assessable."

5. Do not diagnose something merely because it is common.

6. Do not force every item in a checklist into the report.

7. Normal anatomy may be described only when it is actually
visible and adequately assessable.

8. Pathology should be reported only when actual visual
evidence supports it.

9. Do not create a list of diseases simply to say they are
absent.

10. Clearly distinguish:
- Clearly visible
- Possible
- Unclear

11. Use FDI tooth numbers only when the tooth can be
reliably identified from anatomy.

12. Never assign FDI numbers from image position alone.

13. Do not provide definitive diagnosis.

14. Do not prescribe medication.

15. Do not provide definitive treatment planning.

16. Do not use patient information to create radiographic
findings.

17. When uncertain, choose uncertainty rather than guessing.

18. Final diagnosis and treatment decisions must be made by
a qualified dental professional.
"""

                # ====================================================
                # IOPA PROTOCOL
                # ====================================================

                if radiograph_type == "IOPA":

                    radiograph_instructions = """
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
- Lamina dura
- Periodontal ligament space
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
granuloma, or cyst unless the image provides sufficient
evidence. Describe the radiographic appearance when exact
diagnosis is uncertain.
"""

                # ====================================================
                # OPG PROTOCOL
                # ====================================================

                elif radiograph_type == "OPG":

                    radiograph_instructions = """
OPG SYSTEMATIC PANORAMIC ASSESSMENT

Perform a systematic panoramic assessment from one side
to the other and then review the whole image.

IMPORTANT:
The following are TARGETS TO INSPECT, not findings that
must appear in the report.

Report only what is actually visible.

--------------------------------------------------
1. IMAGE QUALITY AND ARTIFACTS
--------------------------------------------------

Assess:
- Patient positioning
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

Ghost images are artifacts, not pathology.

Report a ghost image only when an actual artifact is visible.

--------------------------------------------------
2. ANATOMICAL LANDMARKS
--------------------------------------------------

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

Do not force identification of a landmark that is not
adequately visualized.

--------------------------------------------------
3. DENTITION
--------------------------------------------------

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

--------------------------------------------------
4. PERIODONTAL STRUCTURES
--------------------------------------------------

Inspect:

- Alveolar crest
- General alveolar bone level
- Obvious horizontal bone loss
- Obvious vertical/angular bone loss
- Other clearly visible periodontal changes

Do not overcall subtle bone-level changes.

--------------------------------------------------
5. PERIAPICAL / DENTOALVEOLAR FINDINGS
--------------------------------------------------

Look for actual visual evidence of:

- Periapical radiolucency
- Periapical radiopacity
- Inflammatory-looking periapical changes
- Root abnormalities
- Other dentoalveolar abnormalities

Do not automatically call a lesion:
- Abscess
- Granuloma
- Radicular cyst

If exact diagnosis is uncertain, describe the radiographic
appearance and location conservatively.

--------------------------------------------------
6. ODONTOGENIC CYSTS / TUMORS / LESIONS
--------------------------------------------------

Inspect for actual image-supported evidence of:

- Dentigerous cyst
- Radicular cyst
- Odontogenic keratocyst (OKC)
- Ameloblastoma
- Odontome
- Other odontogenic lesions

These are screening targets only.

Do not report them merely because they are listed here.

If a lesion is visible but exact diagnosis is uncertain,
describe:

- Radiolucent / radiopaque / mixed appearance
- Location
- Relationship to teeth
- Borders
- Effect on surrounding structures
- Confidence

--------------------------------------------------
7. MAXILLA AND MAXILLARY SINUSES
--------------------------------------------------

When visible, inspect:

- Maxillary bone
- Maxillary sinus
- Sinus outline
- Obvious opacification
- Air-fluid level
- Gross mucosal thickening
- Other obvious abnormalities

Do not provide a definitive medical sinus diagnosis.

--------------------------------------------------
8. MANDIBLE
--------------------------------------------------

Inspect when visible:

- Body
- Inferior border
- Ramus
- Angle
- Alveolar process
- Cortical outline
- Inferior alveolar canal
- Mental foramina
- Other obvious abnormalities

--------------------------------------------------
9. TMJ / CONDYLES
--------------------------------------------------

When adequately visualized, inspect:

- Condylar size
- Condylar shape
- Gross asymmetry
- Gross deformity
- Obvious enlargement
- Obvious reduction in size

Do not definitively diagnose condylar hyperplasia or
hypoplasia from an OPG alone.

--------------------------------------------------
10. BONY ABNORMALITIES
--------------------------------------------------

Inspect for actual visual evidence of:

- Osteomyelitis-related changes
- Fibrous-dysplasia-like changes
- Other radiolucent lesions
- Other radiopaque lesions
- Cortical expansion
- Cortical destruction
- Other gross bony abnormalities

Do not diagnose from vague density changes alone.

--------------------------------------------------
OPG REPORTING RULE
--------------------------------------------------

Do NOT output a huge checklist of diseases with "absent".

Instead:

1. Describe relevant normal anatomy that is actually visible.
2. Report abnormalities only when visually supported.
3. Do not invent missing teeth.
4. Do not invent impacted teeth.
5. Do not invent lesions.
6. If a region cannot be evaluated, state the limitation.
7. Choose uncertainty instead of guessing.
"""

                # ====================================================
                # BITEWING PROTOCOL
                # ====================================================

                elif radiograph_type == "Bitewing":

                    radiograph_instructions = """
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

Do not label subtle radiolucencies as caries without
adequate visual evidence.
"""

                # ====================================================
                # OCCLUSAL PROTOCOL
                # ====================================================

                elif radiograph_type == "Occlusal":

                    radiograph_instructions = """
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

                # ====================================================
                # FACIAL BONE / FRACTURE PROTOCOL
                # ====================================================

                elif radiograph_type == "Facial radiograph":

                    radiograph_instructions = """
FACIAL BONE / TRAUMA SYSTEMATIC ASSESSMENT

The main purpose is conservative assessment of facial
bones and screening for obvious traumatic bony abnormalities.

--------------------------------------------------
1. IMAGE QUALITY
--------------------------------------------------

Assess:

- Positioning
- Rotation
- Exposure
- Sharpness
- Motion
- Cropping
- Superimposition

State whether the relevant facial bones are adequately
visualized.

--------------------------------------------------
2. FACIAL BONES
--------------------------------------------------

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

--------------------------------------------------
3. FRACTURE SCREENING
--------------------------------------------------

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

"Possible fracture — requires professional radiographic
and clinical correlation."

Never call an uncertain fracture confirmed.

--------------------------------------------------
4. ASSOCIATED FINDINGS
--------------------------------------------------

When actually visible, inspect for:

- Maxillary sinus opacification
- Air-fluid level
- Radiographically visible soft-tissue swelling
- Other associated abnormalities

Do not automatically attribute these findings to trauma.

--------------------------------------------------
5. LIMITATIONS
--------------------------------------------------

If a facial region is not adequately visualized, state:

"Not reliably assessable on this radiograph."

Do not assume that a fracture is absent merely because
the region cannot be evaluated.

Do not provide definitive fracture treatment or management.
"""

                # ====================================================
                # OTHER PROTOCOL
                # ====================================================

                else:

                    radiograph_instructions = """
OTHER / UNCLASSIFIED RADIOGRAPH

First determine whether the uploaded image appears to be
a dental or maxillofacial radiograph.

State whether the selected type appears compatible.

If uncertain, state:

"Radiograph type cannot be reliably classified."

Then describe only:

- Clearly visible structures
- Actual image-supported findings
- Important limitations

Do not force a diagnosis.
Do not invent missing structures.
"""

         
