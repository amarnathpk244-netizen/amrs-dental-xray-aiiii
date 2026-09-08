import streamlit as st
from datetime import date
from google import genai
import base64

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered"
)

# ---------- MOBILE UI ----------
st.markdown("""
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
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown(
    '<div class="app-title">🦷 AMRs Dental X-ray AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">AI-Assisted Dental Radiographic Assessment</div>',
    unsafe_allow_html=True
)

# ---------- PATIENT INFORMATION ----------
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
        ["Select", "Male", "Female", "Other"]
    )

op_number = st.text_input(
    "OP Number",
    placeholder="Enter OP number"
)

examination_date = st.date_input(
    "Examination Date",
    value=date.today()
)

# ---------- X-RAY UPLOAD ----------
st.markdown(
    '<div class="section">📤 Upload Dental Radiograph</div>',
    unsafe_allow_html=True
)

st.info("Upload a dental X-ray image in JPG, JPEG or PNG format.")

xray = st.file_uploader(
    "Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False
)

# ---------- IMAGE PREVIEW ----------
if xray is not None:

    st.success("✅ X-ray uploaded successfully.")

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

    # ---------- AI ANALYSIS ----------
    st.markdown(
        '<div class="section">🤖 AI Assessment</div>',
        unsafe_allow_html=True
    )

    analyze = st.button(
        "🔍 Analyze X-ray",
        use_container_width=True
    )

    if analyze:

        try:
            api_key = st.secrets["GEMINI_API_KEY"]

            client = genai.Client(api_key=api_key)

            image_bytes = xray.getvalue()

            image_base64 = base64.b64encode(
                image_bytes
            ).decode("utf-8")

            prompt = """
You are an AI-assisted dental radiographic assessment system.

Analyze ONLY the uploaded dental radiograph.

Do NOT invent findings.
Do NOT assume findings that cannot be reasonably seen.
If image quality is insufficient, clearly state that.

Provide a cautious provisional radiographic assessment.

Look for visible radiographic features such as:
- dental caries
- periapical radiolucency
- periodontal bone loss
- impacted teeth
- missing teeth
- retained roots
- gross restorations
- obvious radiopaque lesions
- obvious radiolucent lesions
- other clearly visible abnormalities

For every finding:
1. Describe what is actually visible.
2. Mention the approximate tooth/region if identifiable.
3. Give a confidence level: Low, Moderate, or High.

Separate:
VISIBLE FINDINGS
POSSIBLE INTERPRETATION
LIMITATIONS

Do not provide a definitive diagnosis.
Do not recommend treatment as if diagnosis is confirmed.

This is an AI-assisted provisional radiographic assessment
and must be confirmed by a qualified dental professional.
"""

            response = client.interactions.create(
                model="gemini-3.7-flash",
                input=[
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image",
                        "data": image_base64,
                        "mime_type": xray.type
                    }
                ]
            )

            result = response.output_text

            st.success("✅ AI analysis completed.")

            st.markdown("### 📋 Provisional Radiographic Report")

            st.markdown(
                f"""
**Patient:** {patient_name if patient_name else "Not provided"}

**Age:** {age if age else "Not provided"}

**Sex:** {sex if sex != "Select" else "Not provided"}

**OP Number:** {op_number if op_number else "Not provided"}

**Examination Date:** {examination_date}
"""
            )

            st.markdown("### 🦷 AI Radiographic Assessment")

            st.write(result)

        except Exception as e:

            st.error(
                "AI analysis could not be completed."
            )

            st.warning(
                "Please check the Gemini API configuration "
                "and try again."
            )

            st.caption(f"Technical error: {e}")

else:

    st.caption("No X-ray uploaded yet.")

# ---------- DISCLAIMER ----------
st.markdown(
    """
    <div class="disclaimer">
    ⚠️ <b>Clinical Disclaimer:</b><br>
    This application provides AI-assisted provisional
    radiographic assessment for educational and research
    purposes. It is not a substitute for clinical examination,
    professional radiographic interpretation, or definitive
    diagnosis. Final diagnosis and treatment decisions must be
    made by a qualified dental professional.
    </div>
    """,
    unsafe_allow_html=True
            )
