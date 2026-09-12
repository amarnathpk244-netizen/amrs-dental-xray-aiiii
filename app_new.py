import streamlit as st
from datetime import date
import json
import math
import re
import time
from google import genai
import base64

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
# UI STYLES & MEDICAL THEME
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { padding-top: 1rem; }
    .app-title {
        text-align: center;
        font-size: 28px;
        font-weight: 700;
        color: #1e3d59;
        margin-bottom: 2px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .section {
        font-size: 19px;
        font-weight: 650;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #17b978;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        background-color: #1e3d59;
        color: white;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #17b978;
        color: white;
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
col_m1, col_m2 = st.columns(2)
with col_m1:
    st.metric(label="🧪 Daily Quota Left", value=f"{remaining} / {DAILY_ANALYSIS_LIMIT}")

if remaining <= 0:
    st.warning("⏳ Your 3 AI analyses for today have been used. Please try again tomorrow.")

# ------------------------------------------------------------
# PATIENT INFORMATION
# ------------------------------------------------------------
with st.expander("👤 Patient Information & Record Details", expanded=True):
    patient_name = st.text_input("Patient Name", placeholder="Enter patient name")
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", min_value=0, max_value=120, value=0, step=1)
    with col2:
        sex = st.selectbox("Sex", ["Select", "Male", "Female", "Other"])

    op_number = st.text_input("OP Number", placeholder="Enter OP number")
    examination_date = st.date_input("Examination Date", value=date.today())

# ------------------------------------------------------------
# RADIOGRAPH TYPE & CALIBRATION
# ------------------------------------------------------------
st.markdown('<div class="section">🩻 Radiograph & Calibration</div>', unsafe_allow_html=True)

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

ceph_analysis = "Combined / All Analyses"
scale_factor = 1.0

if radiograph_type == "Lateral Cephalogram (Ceph)":
    ceph_analysis = st.selectbox(
        "Select Cephalometric Analysis",
        CEPH_ANALYSES,
        key="ceph_analysis_selector",
    )

    with st.expander("📏 Scale Calibration Settings", expanded=False):
        use_calibration = st.checkbox("Enable custom pixel-to-mm scale calibration")
        if use_calibration:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                known_mm = st.number_input("Known Ruler Length (mm)", min_value=1.0, value=50.0, step=1.0)
            with col_c2:
                measured_pixels = st.number_input("Measured Length (pixels)", min_value=1.0, value=250.0, step=1.0)
            
            if measured_pixels > 0:
                scale_factor = known_mm / measured_pixels
                st.metric(label="Calculated Scale Factor", value=f"{scale_factor:.4f} mm/pixel")


# ------------------------------------------------------------
# PROMPTS & SAFETY RULES WITH TREATMENT CONSIDERATIONS
# ------------------------------------------------------------
SAFETY_RULES = """
You are AMRs Dental X-ray AI.
You are an AI-assisted radiographic assessment system for qualified dental professionals.
CORE PRINCIPLE: The actual uploaded radiograph is the source of truth.

ENHANCED REPORTING REQUIREMENTS:
1. Include Confidence Flagging (High / Medium / Low) for each reported parameter value in tables.
2. Provide a dedicated Growth, Biotype & Growth Tendency Summary section based on visible morphology.
3. Include a dedicated **Treatment Considerations** section covering biomechanical, skeletal anchorage, or growth-modification options suited to the findings (avoiding definitive prescriptive diagnoses).
4. If "Combined / All Analyses" is selected, synthesize Steiner, Downs, McNamara, Tweed, Wits, Jarabak, and Soft Tissue assessments into one comprehensive structured report.
5. Analyze ONLY the actual uploaded image. Never invent or fabricate findings. If unclear, state "Not reliably assessable."
"""

IOPA_PROTOCOL = "IOPA SYSTEMATIC ASSESSMENT: Assess image quality, dental, periodontal, and periapical structures systematically."
OPG_PROTOCOL = "OPG SYSTEMATIC PANORAMIC ASSESSMENT: Perform a comprehensive panoramic overview covering all structural domains."
BITEWING_PROTOCOL = "BITEWING SYSTEMATIC ASSESSMENT: Inspect interproximal contacts, bone crests, and decay status."
OCCLUSAL_PROTOCOL = "OCCLUSAL RADIOGRAPH SYSTEMATIC ASSESSMENT: Inspect jaw arches and developmental dental structures."
FACIAL_PROTOCOL = "FACIAL BONE / TRAUMA SYSTEMATIC ASSESSMENT: Screen facial bones for structural integrity."

STEINER_PROTOCOL = "STEINER CEPHALOMETRIC ANALYSIS: Assess SNA, SNB, ANB, Incisor positions, and plane angles."
DOWNS_PROTOCOL = "DOWNS CEPHALOMETRIC ANALYSIS: Assess facial angle, convexity, A-B plane, and dental parameters."
MCNAMARA_PROTOCOL = "MCNAMARA CEPHALOMETRIC ANALYSIS: Assess maxilla/mandible positions and effective lengths."
TWEED_PROTOCOL = "TWEED CEPHALOMETRIC ANALYSIS: Assess FMA, IMPA, and FMIA parameters."
WITS_PROTOCOL = "WITS APPRAISAL: Assess AO-BO linear relationship."
JARABAK_PROTOCOL = "JARABAK CEPHALOMETRIC ANALYSIS: Assess facial proportions and vertical growth patterns."
SOFT_TISSUE_PROTOCOL = "SOFT TISSUE CEPHALOMETRIC ANALYSIS: Assess profile convexity and nasolabial angle."

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
        if ceph_an == "Combined / All Analyses":
            protocol += (
                "COMPREHENSIVE COMBINED CEPHALOMETRIC ANALYSIS:\n"
                + STEINER_PROTOCOL + "\n" + DOWNS_PROTOCOL + "\n"
                + MCNAMARA_PROTOCOL + "\n" + TWEED_PROTOCOL + "\n"
                + WITS_PROTOCOL + "\n" + JARABAK_PROTOCOL + "\n" + SOFT_TISSUE_PROTOCOL
            )
        else:
            protocol += f"{ceph_an} CEPHALOMETRIC ANALYSIS."
    else:
        protocol += "General radiographic screening."
    return protocol


# ------------------------------------------------------------
# UPLOAD & ANALYZE
# ------------------------------------------------------------
st.markdown('<div class="section">📤 Upload Dental Radiograph</div>', unsafe_allow_html=True)

xray = st.file_uploader(
    "📷 Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
    key="dental_xray_upload",
)

if xray is not None:
    st.image(xray, caption="Uploaded radiograph", use_container_width=True)

    analyze = st.button(
        "🔍 Analyze X-ray",
        use_container_width=True,
        disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT),
    )

    if analyze:
        if st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT:
            st.warning("⏳ Daily AI analysis limit reached.")
        else:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                st.error("❌ GEMINI_API_KEY was not found in Streamlit Secrets.")
            else:
                mime_type = xray.type
                if mime_type not in ["image/jpeg", "image/png"]:
                    st.error("❌ Unsupported image format.")
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        image_bytes = xray.getvalue()
                        final_prompt = build_prompt(radiograph_type, ceph_analysis, scale_factor)

                        response = None
                        with st.spinner("🔬 Analyzing the uploaded radiograph..."):
                            for attempt in range(3):
                                try:
                                    response = client.models.generate_content(
                                        model=MODEL_NAME,
                                        contents=[
                                            {
                                                "inline_data": {
                                                    "mime_type": mime_type,
                                                    "data": image_bytes,
                                                }
                                            },
                                            final_prompt,
                                        ],
                                    )
                                    break
                                except Exception as error:
                                    if "503" in str(error) and attempt < 2:
                                        time.sleep(5 * (2 ** attempt))
                                        continue
                                    raise error

                        result_text = getattr(response, "text", None)

                        if result_text:
                            st.session_state.analysis_count += 1
                            st.success("✅ AI assessment completed.")

                            # Tabbed Output View
                            tab_report, tab_export = st.tabs(["📋 Assessment Report", "📥 Export & Options"])

                            with tab_report:
                                st.markdown(result_text)

                            with tab_export:
                                st.markdown("### Export Assessment Report")
                                safe_patient_name = patient_name if patient_name else "Patient"
                                
                                report_filename = f"Dental_Report_{safe_patient_name}.txt"
                                st.download_button(
                                    label="📥 Download Report as Text (.txt)",
                                    data=result_text,
                                    file_name=report_filename,
                                    mime="text/plain",
                                    use_container_width=True,
                                )
                                
                                formatted_html = f"""
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <title>AMRs Dental Report - {safe_patient_name}</title>
                                    <style>
                                        body {{ font-family: Arial, sans-serif; padding: 30px; color: #333; line-height: 1.6; }}
                                        h2 {{ color: #1e3d59; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
                                        .meta {{ background: #f9f9f9; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                                        pre {{ white-space: pre-wrap; font-family: Arial, sans-serif; font-size: 14px; }}
                                    </style>
                                </head>
                                <body>
                                    <h2>AMRs Dental X-ray AI - Assessment Report</h2>
                                    <div class="meta">
                                        <p><b>Patient Name:</b> {safe_patient_name}</p>
                                        <p><b>Date:</b> {date.today()}</p>
                                    </div>
                                    <pre>{result_text}</pre>
                                </body>
                                </html>
                                """
                                b64 = base64.b64encode(formatted_html.encode()).decode()
                                href = f'<a href="data:text/html;base64,{b64}" download="Dental_Report_{safe_patient_name}.html" target="_blank" style="display: block; text-align: center; background: #17b978; color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 15px;">🌐 Open Printable Web Report / Save as PDF</a>'
                                st.markdown(href, unsafe_allow_html=True)

                        else:
                            st.warning("⚠️ The AI returned no readable assessment.")

                    except Exception as error:
                        st.error("❌ AI analysis failed.")
                        with st.expander("Technical error details"):
                            st.write(str(error))
                            
