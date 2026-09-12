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
            known_mm = st.number_input("Known Ruler Length (mm)", min_value=1.0, value=50.0, step=1.0)
        with col_c2:
            measured_pixels = st.number_input("Measured Length in Image (pixels)", min_value=1.0, value=250.0, step=1.0)
        
        if measured_pixels > 0:
            scale_factor = known_mm / measured_pixels
            st.info(f"📐 Calculated Scale Factor: {scale_factor:.4f} mm/pixel")


# ------------------------------------------------------------
# COMMON SAFETY & ADVANCED REPORTING PROMPT
# ------------------------------------------------------------
SAFETY_RULES = """
You are AMRs Dental X-ray AI.
You are an AI-assisted radiographic assessment system for qualified dental professionals.
CORE PRINCIPLE: The actual uploaded radiograph is the source of truth.

ENHANCED REPORTING REQUIREMENTS:
1. Include Confidence Flagging (High / Medium / Low) for each reported parameter value in tables.
2. Provide a dedicated Growth, Biotype & Growth Tendency Summary section based on visible morphology (e.g., CVM stages and vertical/horizontal skeletal divergence patterns).
3. If "Combined / All Analyses" is selected, synthesize Steiner, Downs, McNamara, Tweed, Wits, Jarabak, and Soft Tissue assessments into one comprehensive structured report.
4. Analyze ONLY the actual uploaded image. Never invent or fabricate findings. If unclear, state "Not reliably assessable."
5. Do not provide a definitive diagnosis or definitive treatment plan.
"""

IOPA_PROTOCOL = "IOPA SYSTEMATIC ASSESSMENT: Assess image quality, dental, periodontal, and periapical structures systematically with confidence indicators."
OPG_PROTOCOL = "OPG SYSTEMATIC PANORAMIC ASSESSMENT: Perform a comprehensive panoramic overview covering all structural domains."
BITEWING_PROTOCOL = "BITEWING SYSTEMATIC ASSESSMENT: Inspect interproximal contacts, bone crests, and decay status."
OCCLUSAL_PROTOCOL = "OCCLUSAL RADIOGRAPH SYSTEMATIC ASSESSMENT: Inspect jaw arches and developmental dental structures."
FACIAL_PROTOCOL = "FACIAL BONE / TRAUMA SYSTEMATIC ASSESSMENT: Screen facial bones for structural integrity and trauma indicators."

STEINER_PROTOCOL = "STEINER CEPHALOMETRIC ANALYSIS: Assess SNA, SNB, ANB, Incisor positions, and plane angles with explicit confidence levels."
DOWNS_PROTOCOL = "DOWNS CEPHALOMETRIC ANALYSIS: Assess facial angle, convexity, A-B plane, and dental parameters with confidence flags."
MCNAMARA_PROTOCOL = "MCNAMARA CEPHALOMETRIC ANALYSIS: Assess maxilla/mandible positions and effective midface/mandibular lengths."
TWEED_PROTOCOL = "TWEED CEPHALOMETRIC ANALYSIS: Assess FMA, IMPA, and FMIA parameters."
WITS_PROTOCOL = "WITS APPRAISAL: Assess AO-BO linear relationship along the functional occlusal plane."
JARABAK_PROTOCOL = "JARABAK CEPHALOMETRIC ANALYSIS: Assess facial proportions and Jarabak ratio for vertical growth patterns."
SOFT_TISSUE_PROTOCOL = "SOFT TISSUE CEPHALOMETRIC ANALYSIS: Assess profile convexity, nasolabial angle, and lip posture."

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
                + STEINER_PROTOCOL + "\n"
                + DOWNS_PROTOCOL + "\n"
                + MCNAMARA_PROTOCOL + "\n"
                + TWEED_PROTOCOL + "\n"
                + WITS_PROTOCOL + "\n"
                + JARABAK_PROTOCOL + "\n"
                + SOFT_TISSUE_PROTOCOL
            )
        elif ceph_an == "Steiner":
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
            protocol += STEINER_PROTOCOL
    else:
        protocol += "General radiographic screening."
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

                        response = None
                        last_error = None

                        with st.spinner(
                            "🔬 Analyzing the uploaded radiograph..."
                        ):
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
                                    last_error = error
                                    error_text = str(error)

                                    if "503" in error_text or "UNAVAILABLE" in error_text:
                                        if attempt < 2:
                                            wait_time = 5 * (2 ** attempt)
                                            time.sleep(wait_time)
                                            continue

                                    raise error

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

                            # --- EXPORT REPORT OPTIONS (PDF & Text Selection) ---
                            st.markdown("---")
                            st.markdown("### 📥 Export Assessment Report")
                            
                            export_format = st.radio(
                                "Select Export Format:",
                                ("PDF Document (.pdf)", "Text File (.txt)"),
                                horizontal=True
                            )

                            safe_patient_name = patient_name if patient_name else "Patient"

                            if export_format == "PDF Document (.pdf)":
                                try:
                                    from fpdf import FPDF
                                    
                                    def generate_pdf(text, p_name):
                                        pdf = FPDF()
                                        pdf.add_page()
                                        pdf.set_font("Arial", size=11)
                                        pdf.cell(200, 10, txt="AMRs Dental X-ray AI - Assessment Report", ln=True, align="C")
                                        pdf.cell(200, 8, txt=f"Patient Name: {p_name}", ln=True, align="L")
                                        pdf.ln(5)
                                        clean_text = text.replace("**", "").replace("#", "")
                                        for line in clean_text.split('\n'):
                                            pdf.multi_cell(0, 6, txt=line)
                                        return pdf.output(dest='S').encode('latin1', 'replace')
                                        
                                    pdf_data = generate_pdf(result_text, safe_patient_name)
                                    st.download_button(
                                        label="📥 Download Report as PDF (.pdf)",
                                        data=pdf_data,
                                        file_name=f"Dental_Report_{safe_patient_name}.pdf",
                                        mime="application/pdf",
                                        use_container_width=True,
                                    )
                                except ImportError:
                                    st.error("`fpdf2` package missing aanu. Terminal-il `pip install fpdf2` run cheyyuka.")
                            else:
                                report_filename = f"Dental_Report_{safe_patient_name}.txt"
                                st.download_button(
                                    label="📥 Download Report as Text File (.txt)",
                                    data=result_text,
                                    file_name=report_filename,
                                    mime="text/plain",
                                    use_container_width=True,
                                )

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
        
