Import streamlit as st
from datetime import date
import json
import math
import re
from google import genai
import base64

# --- Setup ---
st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.8-flash"
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
scale_factor = 1.0

if radiograph_type == "Lateral Cephalogram (Ceph)":
    st.markdown("### 📐 Cephalometric Analysis")
    ceph_analysis = st.selectbox(
        "Select the analysis you want to perform",
        CEPH_ANALYSES,
        key="ceph_analysis_selector",
    )
    st.info(f"📊 Selected Ceph analysis: {ceph_analysis}")

    # --- PIXEL-TO-MM CALIBRATION SETTINGS ---
    st.markdown('<div class="section">📏 Scale Calibration</div>', unsafe_allow_html=True)
    use_calibration = st.checkbox("Enable custom pixel-to-mm scale calibration")

    if use_calibration:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            known_mm = st.number_input("Known Ruler Length (mm)", min_value=1.0, value=10.0, step=1.0)
        with col_c2:
            measured_pixels = st.number_input("Measured Length in Image (pixels)", min_value=1.0, value=50.0, step=1.0)
        
        if measured_pixels > 0:
            scale_factor = known_mm / measured_pixels
            st.info(f"📐 Calculated Scale Factor: {scale_factor:.4f} mm/pixel")

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

IOPA_PROTOCOL = "IOPA SYSTEMATIC ASSESSMENT: Assess image quality, dental, periodontal, and periapical structures systematically."
OPG_PROTOCOL = "OPG SYSTEMATIC PANORAMIC ASSESSMENT: Perform a systematic panoramic assessment covering all visible structures."
BITEWING_PROTOCOL = "BITEWING SYSTEMATIC ASSESSMENT: Inspect interproximal surfaces and bone levels."
OCCLUSAL_PROTOCOL = "OCCLUSAL RADIOGRAPH SYSTEMATIC ASSESSMENT: Inspect teeth, jaw structures, and obvious abnormalities."
FACIAL_PROTOCOL = "FACIAL BONE / TRAUMA SYSTEMATIC ASSESSMENT: Conservative assessment of visible facial bones and fracture screening."

STEINER_PROTOCOL = """
STEINER CEPHALOMETRIC ANALYSIS - CORE
Analyze only a true lateral cephalogram. Assess image quality and landmark visibility before attempting measurements. Never invent a landmark or numerical value.
CORE STEINER PARAMETERS:
- SNA Angle
- SNB Angle
- ANB Angle
- Upper Incisor to NA
- Lower Incisor to NB
- Occlusal Plane to SN Angle
- Mandibular Plane to SN Angle
- Interincisal Angle
REPORTING: Give numerical values using the provided image scale calibration if available. State "Not reliably assessable" otherwise.
"""

DOWNS_PROTOCOL = """
DOWNS CEPHALOMETRIC ANALYSIS - CORE
Analyze only a true lateral cephalogram. Assess image quality and landmark visibility before attempting measurements. Never invent a landmark or numerical value.
CORE DOWNS PARAMETERS:
- Facial Angle
- Angle of Convexity
- A-B Plane Angle
- Mandibular Plane Angle
- Interincisal Angle
- Lower Incisor to Occlusal Plane Angle
- IMPA
REPORTING: Give numerical values using the provided scale calibration if available. State "Not reliably assessable" otherwise.
"""

MCNAMARA_PROTOCOL = "MCNAMARA CEPHALOMETRIC ANALYSIS - CORE: Focus on Maxillary Position, Mandibular Position, Effective Midface Length (Co-A), and Effective Mandibular Length (Co-Gn)."
TWEED_PROTOCOL = "TWEED CEPHALOMETRIC ANALYSIS - CORE: Assess FMA, IMPA, and FMIA values."
WITS_PROTOCOL = "WITS APPRAISAL - CORE PROTOCOL: Determine the AO-BO linear relationship along the functional occlusal plane."
JARABAK_PROTOCOL = "JARABAK CEPHALOMETRIC ANALYSIS - CORE: Assess polygon proportions and Jarabak ratio (S-Go / N-Me * 100)."
SOFT_TISSUE_PROTOCOL = "SOFT TISSUE CEPHALOMETRIC ANALYSIS - CORE: Assess facial profile convexity, Nasolabial angle, and E-plane/S-line relationships."

# ------------------------------------------------------------
# PROMPT BUILDER FUNCTION WITH CALIBRATION
# ------------------------------------------------------------
def build_prompt(rad_type, ceph_an, scale_fac):
    protocol = SAFETY_RULES + f"\n\n[IMAGE CALIBRATION SCALE: {scale_fac:.4f} mm/pixel]\n\n"
    if rad_type == "IOPA":
        protocol += IOPA_PROTOCOL
    elif rad_type == "OPG":
        protocol += OPG_PROTOCOL
    elif rad_type == "Bitewing":
        protocol += BITEWING_PROTOCOL
    elif rad_type == "Occlusal":
        protocol += OCCLUSAL_PROTOCOL
    elif rad_type == "Facial radiograph":
        protocol += FACIAL_PROTOCOL
    elif rad_type == "Lateral Cephalogram (Ceph)":
        if ceph_an == "Steiner":
            protocol += STEINER_PROTOCOL
        elif ceph_an == "Downs":
            protocol += DOWNS_PROTOCOL
        elif ceph_an == "McNamara":
            protocol += MCNAMARA_PROTOCOL
        elif ceph_an == "Tweed":
            protocol += TWEED_PROTOCOL
        elif ceph_an == "Wits Appraisal":
            protocol += WITS_PROTOCOL
        elif ceph_an == "Jarabak":
            protocol += JARABAK_PROTOCOL
        elif ceph_an == "Soft Tissue":
            protocol += SOFT_TISSUE_PROTOCOL
        else:
            protocol += STEINER_PROTOCOL + "\n\n" + DOWNS_PROTOCOL + "\n\n" + TWEED_PROTOCOL
    else:
        protocol += "General radiographic assessment."
    return protocol

# ------------------------------------------------------------
# UPLOAD & ANALYZE
# ------------------------------------------------------------
st.markdown('<div class="section">📤 Upload Dental Radiograph</div>', unsafe_allow_html=True)
st.info("Upload a dental X-ray image in JPG, JPEG or PNG format.")

xray = st.file_uploader(
    "📷 Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
    key="dental_xray_upload",
)

if xray is not None:

    st.image(
        xray,
        caption="Uploaded radiograph",
        use_container_width=True,
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

                if mime_type not in ["image/jpeg", "image/png"]:
                    st.error("❌ Unsupported image format.")

                else:

                    try:

                        client = genai.Client(api_key=api_key)

                        image_bytes = xray.getvalue()

                        final_prompt = build_prompt(
                            radiograph_type,
                            ceph_analysis,
                            scale_factor,
                        )

                        with st.spinner(
                            "🔬 Analyzing the uploaded radiograph..."
                        ):
                            response = client.models.generate_content(
                                model=MODEL_NAME,
                                contents=[
                                    {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
                                    final_prompt
                                ],
                            )

                        result_text = getattr(
                            response,
                            "text",
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

                        else:

                            st.warning(
                                "⚠️ The AI returned no readable assessment."
                            )

                    except Exception as error:

                        st.error(
                            "❌ AI analysis failed."
                        )

                        with st.expander(
                            "Technical error details"
                        ):
                            st.write(str(error))
