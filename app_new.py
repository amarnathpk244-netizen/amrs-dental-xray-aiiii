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

remaining = (
    DAILY_ANALYSIS_LIMIT
    - st.session_state.analysis_count
)

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
    type=[
        "jpg",
        "jpeg",
        "png"
    ],
    accept_multiple_files=False,
    key="dental_xray_upload",
    label_visibility="visible"
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


                # ====================================================
                # BASE64 IMAGE
                # ====================================================

                image_base64 = base64.b64encode(
                    image_bytes
                ).decode("utf-8")


                # ====================================================
                # GLOBAL SAFETY INSTRUCTIONS
                # ====================================================

                safety_rules = """
You are AMRs Dental X-ray AI.

You are an AI-assisted radiographic assessment system
for qualified dental professionals.

CORE PRINCIPLE:

Analyze the actual uploaded radiograph carefully and
systematically, but report ONLY findings supported by
visual evidence in the uploaded image.

IMPORTANT SAFETY RULES:

1. Analyze ONLY the actual uploaded X-ray image.

2. NEVER invent or hallucinate radiographic findings.

3. NEVER use random, fixed, default, or predetermined
findings.

4. The image is the source of truth.

5. Do not use patient name, OP number, age, sex, or
other patient information to create radiographic findings.

6. If a structure or finding is not visible or cannot
be assessed reliably, say:
"Not clearly assessable."

7. If image quality is poor, blurred, cropped, distorted,
overexposed, underexposed, or otherwise inadequate,
clearly state the limitation.

8. Do not diagnose something simply because it is common.

9. Do not force every item in a checklist into the report.

10. A normal anatomical structure may be described only
when it is actually visible and adequately assessable.

11. A pathology should be reported ONLY when there is
actual visual evidence supporting that finding.

12. Do NOT create a list of absent pathologies simply
because they were included in the assessment protocol.

13. If no convincing evidence of a particular pathology
is present, do not invent or imply that pathology.

14. Clearly distinguish:
- Clearly visible
- Possible
- Unclear / Not reliably assessable

15. Do not assign an FDI tooth number unless the tooth
can be reliably identified from visible anatomy.

16. Never assign an FDI tooth number merely from the
position of a tooth in the image.

17. Do not provide a definitive diagnosis.

18. Do not prescribe medication.

19. Do not provide definitive treatment planning.

20. When uncertain, choose uncertainty rather than guessing.

21. Final diagnosis and treatment decisions must be made
by a qualified dental professional.

22. Only report findings that have actual visual evidence
in the uploaded image.
"""


                # ====================================================
                # RADIOGRAPH-SPECIFIC PROTOCOLS
                # ====================================================

                if radiograph_type == "IOPA":

                    radiograph_instructions = """
IOPA SYSTEMATIC PROTOCOL

The selected radiograph is IOPA.

Systematically inspect the actual image.

Assess, when visible and adequately assessable:

1. Image quality
- Exposure
- Contrast
- Sharpness
- Positioning
- Cropping
- Cone cut
- Distortion
- Other technical limitations

2. Teeth
- Crown
- Root
- Number of visible teeth
- Obvious caries
- Obvious restorations
- Gross tooth abnormalities

3. Periodontal structures
- Lamina dura when visible
- Periodontal ligament space when visible
- Alveolar crest
- Obvious periodontal bone loss

4. Periapical region
- Periapical radiolucency
- Periapical radiopacity
- Root abnormalities
- Other clearly visible periapical findings

5. Other structures
- Impacted or unerupted teeth when clearly visible
- Other obvious radiographic abnormalities

IMPORTANT:

Report only findings actually demonstrated by the image.

If a finding is uncertain, clearly label it as possible
or not clearly assessable.

Use FDI tooth numbers only when reliably identifiable.
"""


                elif radiograph_type == "OPG":

                    radiograph_instructions = """
OPG SYSTEMATIC PANORAMIC PROTOCOL

The selected radiograph is an OPG.

Perform a systematic assessment from one side of the
image to the other, while also reviewing the image as
a whole.

IMPORTANT:

The following are TARGET STRUCTURES and TARGET
ABNORMALITIES to inspect for.

They are NOT a list of findings that must be reported.

Report a structure only when actually visible.

Report a pathology only when actual visual evidence
supports it.

Do NOT write a long list saying every pathology is absent.

------------------------------------------------------------
A. IMAGE QUALITY AND PANORAMIC ARTIFACTS
------------------------------------------------------------

Assess:

- Patient positioning
- Midline alignment
- Rotation
- Head tilt
- Anteroposterior positioning
- Magnification
- Geometric distortion
- Motion blur
- Exposure
- Cropping
- Ghost images
- Other panoramic artifacts
- Superimposition

Ghost images are ARTIFACTS, not diagnoses.

Report a ghost image only if an actual ghost image or
panoramic artifact is visible.

------------------------------------------------------------
B. MAXILLOFACIAL ANATOMICAL STRUCTURES
------------------------------------------------------------

Inspect the following structures when visible:

- Incisive foramen
- Median palatal suture
- Nasal fossa
- Nasal septum
- Maxillary sinuses
- Zygomatic process of maxilla
- Zygomatic arches
- Pterygoid plates
- Pterygoid hamulus / hamulus
- Coronoid processes
- Mandibular condyles
- Mandibular ramus
- Mandibular angle
- Inferior border of mandible
- Mental foramina
- Inferior alveolar canal
- Mylohyoid ridge
- External oblique ridge
- Lingual foramen when visible
- Genial tubercles when visible
- Glossopalatal air space
- Nasopharyngeal air space

Do NOT force identification of a structure if it is not
adequately visualized.

If a structure is visible and relevant, describe its
appearance conservatively.

------------------------------------------------------------
C. DENTITION
------------------------------------------------------------

Systematically inspect:

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
- Obvious periapical abnormalities

Use FDI numbering ONLY when the tooth can be reliably
identified anatomically.

Never infer an FDI number only from image position.

------------------------------------------------------------
D. PERIODONTAL STRUCTURES
------------------------------------------------------------

Inspect:

- Alveolar crest
- General alveolar bone level
- Obvious horizontal bone loss
- Obvious vertical/angular bone loss
- Other clearly visible periodontal changes

Do not overcall mild or subtle bone-level changes.

------------------------------------------------------------
E. PERIAPICAL AND DENTOALVEOLAR ABNORMALITIES
------------------------------------------------------------

Look for actual visual evidence of:

- Periapical radiolucency
- Periapical radiopacity
- Obvious inflammatory-looking periapical changes
- Root abnormalities
- Other dentoalveolar abnormalities

Do NOT automatically label a radiolucency as:
- Abscess
- Granuloma
- Radicular cyst

If the image does not allow reliable differentiation,
describe the radiographic appearance and uncertainty.

------------------------------------------------------------
F. ODONTOGENIC CYSTS / TUMORS / LESIONS
------------------------------------------------------------

Inspect for actual visual evidence of:

- Dentigerous cyst
- Radicular cyst
- Odontogenic keratocyst (OKC)
- Ameloblastoma
- Odontomes
- Other odontogenic lesions

These diagnoses must NOT be generated merely because
they are listed here.

If an actual lesion is visible but its exact diagnosis
cannot be established from the image, describe:

- Radiolucent / radiopaque / mixed appearance
- Location
- Approximate relationship to teeth or anatomical structures
- Borders if visible
- Effect on surrounding structures if visible
- Confidence

Use conservative language.

------------------------------------------------------------
G. JAW AND OTHER BONY ABNORMALITIES
------------------------------------------------------------

Inspect for actual visual evidence of:

- Osteomyelitis-related changes
- Fibrous dysplasia-like osseous changes
- Other obvious radiopaque lesions
- Other obvious radiolucent lesions
- Cortical expansion or destruction when clearly visible
- Gross bone abnormalities

Do NOT diagnose these conditions solely from vague
or nonspecific density changes.

------------------------------------------------------------
H. TMJ / CONDYLES
------------------------------------------------------------

When adequately visualized, inspect:

- Condylar shape
- Condylar size
- Gross asymmetry
- Gross deformity
- Obvious hyperplasia-like enlargement
- Obvious hypoplasia-like reduction

Do not definitively diagnose condylar hyperplasia or
hypoplasia from OPG appearance alone.

If asymmetry is visible, describe the observed asymmetry
and recommend professional correlation.

------------------------------------------------------------
I. MAXILLARY SINUSES
------------------------------------------------------------

When adequately visualized, inspect:

- General aeration
- Obvious opacification
- Obvious air-fluid level
- Gross mucosal thickening when clearly visible
- Cortical outline
- Other obvious abnormalities

Do not provide a definitive medical sinus diagnosis.

------------------------------------------------------------
J. MANDIBLE
------------------------------------------------------------

Inspect:

- Body
- Inferior border
- Ramus
- Angle
- Alveolar process
- Cortical outline
- Inferior alveolar canal
- Mental foramina
- Other visible structures

Report only actual visible abnormalities.

------------------------------------------------------------
OPG REPORTING RULE

DO NOT produce a checklist containing every possible
disease with "absent" beside it.

Instead:

1. Identify what is actually visible.
2. Identify genuine abnormalities supported by the image.
3. Describe normal anatomical landmarks only when useful
   and actually visible.
4. If no definite abnormality is visible and the image is
   adequately assessable, say so.
5. If an area cannot be reliably assessed, state the limitation.
6. Never guess.
"""


                elif radiograph_type == "Bitewing":

                    radiograph_instructions = """
BITEWING SYSTEMATIC PROTOCOL

Assess only structures actually visible.

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


                elif radiograph_type == "Occlusal":

                    radiograph_instructions = """
OCCLUSAL RADIOGRAPH SYSTEMATIC PROTOCOL

Assess only visible structures.

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

Do not provide a definitive diagnosis from nonspecific
radiographic appearances.
"""


                elif radiograph_type == "Facial radiograph":

                    radiograph_instructions = """
FACIAL BONE / TRAUMA SYSTEMATIC PROTOCOL

The selected radiograph is a facial radiograph.

The primary purpose of this protocol is conservative
radiographic assessment of visible facial bones and
possible traumatic bony abnormalities.

IMPORTANT:

This is a screening/assessment protocol.

A suspected fracture must NOT be presented as a confirmed
fracture unless the radiographic evidence is sufficiently
clear.

------------------------------------------------------------
A. IMAGE QUALITY
------------------------------------------------------------

Assess:

- Positioning
- Rotation
- Exposure
- Sharpness
- Motion
- Cropping
- Superimposition
- Whether the relevant facial bones are adequately included

------------------------------------------------------------
B. FACIAL BONY STRUCTURES
------------------------------------------------------------

Inspect only where adequately visualized:

- Nasal bones
- Nasal septum
- Orbital margins
- Orbital walls when visible
- Zygomatic bones
- Zygomatic arches
- Zygomaticomaxillary region
- Maxillary bones
- Maxillary sinus walls
- Frontal facial bone regions when included
- Alveolar processes when included
- Mandible when included

----------------------------------------------
