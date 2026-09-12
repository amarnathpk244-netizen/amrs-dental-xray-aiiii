import streamlit as st
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
MODEL_NAME = "gemini-1.5-flash"  # Updated model name for reliability

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

# --- Session State ---
if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()

# --- UI ---
st.markdown('<div class="app-title">🦷 AMRs Dental X-ray AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-Assisted Dental Radiographic Assessment</div>', unsafe_allow_html=True)

remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
if remaining > 0:
    st.info(f"🧪 AI analyses remaining today: {remaining} / {DAILY_ANALYSIS_LIMIT}")
else:
    st.warning("⏳ Your 3 AI analyses for today have been used. Please try again tomorrow.")

# --- Patient Information ---
st.markdown('<div class="section">👤 Patient Information</div>', unsafe_allow_html=True)
patient_name = st.text_input("Patient Name", placeholder="Enter patient name")
col1, col2 = st.columns(2)
with col1:
    age = st.number_input("Age", min_value=0, max_value=120, value=0, step=1)
with col2:
    sex = st.selectbox("Sex", ["Select", "Male", "Female", "Other"])
op_number = st.text_input("OP Number", placeholder="Enter OP number")
examination_date = st.date_input("Examination Date", value=date.today())

# --- Radiograph Type ---
st.markdown('<div class="section">🩻 Radiograph Type</div>', unsafe_allow_html=True)
radiograph_type = st.selectbox(
    "Select radiograph type",
    ["IOPA", "Lateral Cephalogram (Ceph)", "OPG", "Bitewing", "Occlusal", "Facial radiograph", "Other / Not reliably classifiable"],
)
st.info(f"🩻 Selected radiograph: {radiograph_type}")

ceph_analysis = "Combined / All Analyses"
if radiograph_type == "Lateral Cephalogram (Ceph)":
    st.markdown("### 📐 Cephalometric Analysis")
    ceph_analysis = st.selectbox("Select the analysis you want to perform", CEPH_ANALYSES, key="ceph_analysis_selector")
    st.info(f"📊 Selected Ceph analysis: {ceph_analysis}")

# --- Protocols (Safety, IOPA, OPG, Ceph Analyses) ---
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
STEINER_PROTOCOL = "STEINER CEPHALOMETRIC ANALYSIS - CORE: Assess image quality and landmark visibility. Report SNA, SNB, ANB, Upper incisor to NA, Lower incisor to NB, Occlusal plane to SN, Mandibular plane to SN, and Interincisal angle values only when clearly identifiable. State 'Not reliably assessable' otherwise."
DOWNS_PROTOCOL = "DOWNS CEPHALOMETRIC ANALYSIS - CORE: Analyze image quality and landmark visibility. Report Skeletal Profile (Facial angle, Angle of convexity, A-B plane, Mandibular plane) and Dental Profile (Interincisal angle, Lower incisor to occlusal plane, IMPA) values only when reliably measurable. State 'Not reliably assessable' otherwise."
MCNAMARA_PROTOCOL = "MCNAMARA CEPHALOMETRIC ANALYSIS - CORE: Analyze image quality and landmark visibility. Focus on Maxillary Position, Mandibular Position, Effective Midface Length (Co-A), and Effective Mandibular Length (Co-Gn) values only when reliably measurable."
TWEED_PROTOCOL = "TWEED CEPHALOMETRIC ANALYSIS - CORE: Analyze image quality and landmark visibility. Report FMA, IMPA, and FMIA values only when reliably measurable."
WITS_PROTOCOL = "WITS APPRAISAL - CORE PROTOCOL: Determine the AO-BO linear relationship along the functional occlusal plane."
JARABAK_PROTOCOL = "JARABAK CEPHALOMETRIC ANALYSIS - CORE: Assess polygon proportions and Jarabak ratio (S-Go / N-Me * 100) for vertical growth patterns."
SOFT_TISSUE_PROTOCOL = "SOFT_TISSUE_CEPHALOMETRIC_ANALYSIS - CORE: Assess facial profile convexity, Nasolabial angle, and E-plane/S-line relationships."

# --- Prompt Builder ---
def build_prompt(rad_type, ceph_an):
    protocol = SAFETY_RULES + "\n\n"
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
        else:  # Combined / All Analyses
            protocol += STEINER_PROTOCOL + "\n\n" + DOWNS_PROTOCOL + "\n\n" + TWEED_PROTOCOL
    else:
        protocol += "General radiographic assessment."
    return protocol

# --- Upload & Analyze ---
st.markdown('<div class="section">📤 Upload Dental Radiograph</div>', unsafe_allow_html=True)
st.info("Upload a dental X-ray image in JPG, JPEG or PNG format.")
xray = st.file_uploader("📷 Choose X-ray image", type=["jpg", "jpeg", "png"], accept_multiple_files=False, key="dental_xray_upload")

if xray is not None:
    st.image(xray, caption="Uploaded radiograph", use_container_width=True)
    analyze = st.button("🔍 Analyze X-ray", use_container_width=True, disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT))

    if analyze:
        if st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT:
            st.warning("⏳ Daily AI analysis limit reached. Please try again tomorrow.")
        else:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                st.error("❌ GEMINI_API_KEY was not found.")
                st.info("Open Streamlit Secrets and configure GEMINI_API_KEY.")
            else:
                mime_type = xray.type
                if mime_type not in ["image/jpeg", "image/png"]:
                    st.error("❌ Unsupported image format.")
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        image_bytes = xray.getvalue()

                        final_prompt = build_prompt(radiograph_type, ceph_analysis)

                        with st.spinner("🔬 Analyzing the uploaded radiograph..."):
                            # CORRECTED: Use client.models.generate_content and 'inline_data' for bytes
                            response = client.models.generate_content(
                                model=MODEL_NAME,
                                contents=[
                                    {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
                                    final_prompt
                                ],
                            )

                        result_text = getattr(response, "text", None)

                        if result_text:
                            st.session_state.analysis_count += 1
                            st.success("✅ AI assessment completed.")
                            st.markdown('<div class="section">📋 Assessment Report</div>', unsafe_allow_html=True)
                            st.markdown(result_text)
                        else:
                            st.warning("⚠️ The AI returned no readable assessment.")

                    except Exception as error:
                        st.error("❌ AI analysis failed.")
                        with st.expander("Technical error details"):
                            st.write(str(error))
                            
