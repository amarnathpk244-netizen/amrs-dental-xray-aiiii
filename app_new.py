import streamlit as st
from datetime import date
import json
import math
import re
from google import genai
import base64

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.6-flash"

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
# UI STYLES
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
        "Lateral Cephalogram (Ceph)",
        "OPG",
        "Bitewing",
        "Occlusal",
        "Facial radiograph",
        "Other / Not reliably classifiable",
    ],
)

st.info(f"🩻 Selected radiograph: {radiograph_type}")

ceph_analysis = "Combined / All Analyses"
if radiograph_type == "Lateral Cephalogram (Ceph)":
    st.markdown("### 📐 Cephalometric Analysis")
    ceph_analysis = st.selectbox(
        "Select the analysis you want to perform",
        CEPH_ANALYSES,
        key="ceph_analysis_selector",
    )
    st.info(f"📊 Selected Ceph analysis: {ceph_analysis}")

# ------------------------------------------------------------
# PROTOCOLS & SAFETY PROMPTS
# ------------------------------------------------------------
SAFETY_RULES = """
You are AMRs Dental X-ray AI.
You are an AI-assisted radiographic assessment system for qualified dental professionals.
CORE PRINCIPLE: The actual uploaded radiograph is the source of truth.
SAFETY RULES:
1. Analyze ONLY the actual uploaded image.
2. Never invent, hallucinate, or fabricate findings.
3. Report only findings supported by visible image evidence.
4. If something cannot be assessed reliably, say: "Not clearly assessable."
5. Do not provide a definitive diagnosis or treatment plan.
"""

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
"Possible fracture - requires professional radiographic and clinical correlation."

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

STEINER_PROTOCOL = """
STEINER CEPHALOMETRIC ANALYSIS - CORE

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE STEINER PARAMETERS WHEN RELIABLY MEASURABLE:
- SNA Angle: Maxillary position relative to cranial base
- SNB Angle: Mandibular position relative to cranial base
- ANB Angle: Relative anteroposterior skeletal jaw relationship
- Upper Incisor to NA (Angle and Linear distance)
- Lower Incisor to NB (Angle and Linear distance)
- Occlusal Plane to SN Angle
- Mandibular Plane to SN Angle (Go-Gn to SN)
- Interincisal Angle

REPORTING:
- Give numerical values only when landmarks can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

DOWNS_PROTOCOL = """
DOWNS CEPHALOMETRIC ANALYSIS - CORE

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE DOWNS PARAMETERS WHEN RELIABLY MEASURABLE:
Skeletal Profile:
- Facial Angle: Frankfort horizontal to facial plane (N-Pog)
- Angle of Convexity: Nasion to Point A, and Point A to Pogonion
- A-B Plane Angle: A-B line relative to facial plane (N-Pog)
- Mandibular Plane Angle: Frankfort horizontal to mandibular plane (Go-Me)

Dental Profile:
- Interincisal Angle: Long axes of maxillary and mandibular central incisors
- Lower Incisor to Occlusal Plane Angle
- Lower Incisor to Mandibular Plane Angle (IMPA)
- Occlusal Plane to Frankfort Horizontal Angle
- Y-Axis (Growth pattern): S-Gn to Frankfort Horizontal

REPORTING:
- Give numerical values only when landmarks can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

MCNAMARA_PROTOCOL = """
MCNAMARA CEPHALOMETRIC ANALYSIS - CORE

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE MCNAMARA PARAMETERS WHEN RELIABLY MEASURABLE:
- Maxillary Position: Maxilla relative to nasion perpendicular
- Mandibular Position: Mandible relative to nasion perpendicular
- Effective Midface Length: Condylion to Point A (Co-A)
- Effective Mandibular Length: Condylion to Gnathion (Co-Gn)
- Mandibular Difference: Effective mandibular length minus midface length
- Vertical Pterygoid Vertical (PTV) analysis and lower facial height proportions

REPORTING:
- Give numerical values only when landmarks can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

TWEED_PROTOCOL = """
TWEED CEPHALOMETRIC ANALYSIS - CORE

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE TWEED PARAMETERS WHEN RELIABLY MEASURABLE:
- FMA: Frankfort horizontal to mandibular plane angle
- IMPA: Long axis of mandibular central incisor to mandibular plane
- FMIA: Long axis of mandibular central incisor to Frankfort horizontal
- Tweed Triangle relationship assessment (FMA, IMPA, FMIA balance)

REPORTING:
- Give numerical values only when landmarks can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

WITS_PROTOCOL = """
WITS APPRAISAL - CORE PROTOCOL

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE WITS PARAMETERS WHEN RELIABLY MEASURABLE:
- Functional Occlusal Plane (FOP) determination
- Point A Perpendicular (AO) projection onto FOP
- Point B Perpendicular (BO) projection onto FOP
- AO-BO linear relationship and jaw discrepancy categorization (Class I, II, or III tendency)

REPORTING:
- Give numerical values only when landmarks can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

JARABAK_PROTOCOL = """
JARABAK CEPHALOMETRIC ANALYSIS - CORE

Analyze only a true lateral cephalogram. Assess image quality and
landmark visibility before attempting measurements. Never invent a
landmark or numerical value.

CORE JARABAK PARAMETERS WHEN RELIABLY MEASURABLE:
- Polygon proportions and cranial base relationships
- Sum of posterior angles (Saddle angle, Articular angle, Gonial angle) for growth pattern assessment
- Jarabak Ratio: (S-Go / N-Me) * 100 for vertical growth proportion evaluation (divergent vs counter-divergent)

REPORTING:
- Give numerical values only when landmarks can be identified with adequate confidence.
- State "Not reliably assessable" for an unavailable measurement.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

SOFT_TISSUE_PROTOCOL = """
SOFT TISSUE CEPHALOMETRIC ANALYSIS - CORE

Analyze only a true lateral cephalogram. Assess image quality and soft tissue profile visibility before attempting evaluations. Never invent a value.

CORE SOFT TISSUE PARAMETERS WHEN RELIABLY MEASURABLE:
- Facial Profile Convexity (Soft tissue Nasion, Subnasale, Soft tissue Pogonion)
- Nasolabial Angle
- Upper and Lower Lip Thickness and Protrusion relative to Ricketts E-plane or Steiner S-line
- Mentolabial sulcus depth

REPORTING:
- Give numerical values or descriptive findings only when reliable.
- State "Not reliably assessable" for unavailable evaluations.
- Separate measured findings from interpretation.
- Do not provide definitive orthodontic diagnosis or treatment planning.
"""

# ------------------------------------------------------------
# PROMPT BUILDER FUNCTION
# ------------------------------------------------------------
def build_prompt(rad_type, ceph_an):
    if rad_type == "IOPA":
        return SAFETY_RULES + "\n\n" + IOPA_PROTOCOL
    elif rad_type == "OPG":
        return SAFETY_RULES + "\n\n" + OPG_PROTOCOL
    elif rad_type == "Bitewing":
        return SAFETY_RULES + "\n\n" + BITEWING_PROTOCOL
    elif rad_type == "Occlusal":
        return SAFETY_RULES + "\n\n" + OCCLUSAL_PROTOCOL
    elif rad_type == "Facial radiograph":
        return SAFETY_RULES + "\n\n" + FACIAL_PROTOCOL
    elif rad_type == "Lateral Cephalogram (Ceph)":
        if ceph_an == "Steiner":
            return SAFETY_RULES + "\n\n" + STEINER_PROTOCOL
        elif ceph_an == "Downs":
            return SAFETY_RULES + "\n\n" + DOWNS_PROTOCOL
        elif ceph_an == "McNamara":
            return SAFETY_RULES + "\n\n" + MCNAMARA_PROTOCOL
        elif ceph_an == "Tweed":
            return SAFETY_RULES + "\n\n" + TWEED_PROTOCOL
        elif ceph_an == "Wits Appraisal":
            return SAFETY_RULES + "\n\n" + WITS_PROTOCOL
        elif ceph_an == "Jarabak":
            return SAFETY_RULES + "\n\n" + JARABAK_PROTOCOL
        elif ceph_an == "Soft Tissue":
            return SAFETY_RULES + "\n\n" + SOFT_TISSUE_PROTOCOL
        else:
            return SAFETY_RULES + "\n\n" + STEINER_PROTOCOL + "\n\n" + DOWNS_PROTOCOL + "\n\n" + MCNAMARA_PROTOCOL + "\n\n" + TWEED_PROTOCOL + "\n\n" + WITS_PROTOCOL + "\n\n" + JARABAK_PROTOCOL + "\n\n" + SOFT_TISSUE_PROTOCOL
    else:
        return SAFETY_RULES

# ------------------------------------------------------------
# UPLOAD & ANALYZE
# ------------------------------------------------------------
st.mar
