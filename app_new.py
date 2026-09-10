import streamlit as st
from datetime import date
from google import genai
import base64

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered"
)

# ---------- DAILY USAGE LIMIT ----------
DAILY_ANALYSIS_LIMIT = 3

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()

# ---------- MOBILE UI ----------
st.markdown("""
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

# ---------- USAGE STATUS ----------
remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count

if remaining > 0:
    st.info(
        f"🧪 AI analyses remaining today: {remaining} / "
        f"{DAILY_ANALYSIS_LIMIT}"
    )
else:
    st.warning(
        "⏳ Your 3 AI analyses for today have been used. "
        "Please try again tomorrow."
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

# ---------- RADIOGRAPH TYPE ----------
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

# ---------- X-RAY UPLOAD ----------
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
    key="dental_xray_upload",
    label_visibility="visible"
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
        use_container_width=True,
        disabled=(
            st.session_state.analysis_count
            >= DAILY_ANALYSIS_LIMIT
        )
    )

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

                # ---------- GEMINI API ----------
                api_key = st.secrets["GEMINI_API_KEY"]

                client = genai.Client(
                    api_key=api_key
                )

                # ---------- IMAGE
