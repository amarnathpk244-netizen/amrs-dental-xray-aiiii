 import streamlit as st
from datetime import date

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
    .main {
        background-color: #f7fafc;
    }

    .hero {
        padding: 35px 25px;
        border-radius: 20px;
        background: linear-gradient(135deg, #e8f4ff, #ffffff);
        border: 1px solid #d9eaf7;
        margin-bottom: 25px;
    }

    .hero-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        font-size: 19px;
        color: #52606d;
    }

    .section-title {
        font-size: 25px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    .info-card {
        padding: 18px;
        border-radius: 15px;
        background: white;
        border: 1px solid #e1e8ed;
        margin-bottom: 15px;
    }

    .disclaimer {
        padding: 15px;
        border-radius: 12px;
        background: #fff8e6;
        border: 1px solid #f0d98c;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- HERO ----------------
st.markdown("""
<div class="hero">
    <div class="hero-title">🦷 AMRs Dental X-ray AI</div>
    <div class="hero-subtitle">
        AI-Assisted Dental Radiographic Assessment
    </div>
    <p>
        A digital platform designed to support preliminary assessment
        of dental radiographs using artificial intelligence.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------- WORKFLOW ----------------
st.markdown("### 🔄 Assessment Workflow")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ① 👤")
    st.write("**Patient Information**")
    st.caption("Enter basic patient details.")

with col2:
    st.markdown("### ② 🩻")
    st.write("**Upload Radiograph**")
    st.caption("Upload a dental X-ray image.")

with col3:
    st.markdown("### ③ 🤖")
    st.write("**AI Assessment**")
    st.caption("AI-assisted findings and report.")

st.divider()

# ---------------- PATIENT DETAILS ----------------
st.markdown(
    '<div class="section-title">👤 Patient Information</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col1:
    name = st.text_input("Patient Name")
    age = st.number_input("Age", min_value=0, max_value=120, step=1)
    sex = st.selectbox("Sex", ["Select", "Male", "Female", "Other"])

with col2:
    op_no = st.text_input("OP Number")
    examination_date = st.date_input(
        "Examination Date",
        value=date.today()
    )

st.divider()

# ---------------- X-RAY UPLOAD ----------------
st.markdown(
    '<div class="section-title">🩻 Dental Radiograph</div>',
    unsafe_allow_html=True
)

st.write("Upload the patient's dental radiograph for assessment.")

xray = st.file_uploader(
    "Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    help="Supported formats: JPG, JPEG and PNG"
)

if xray is not None:

    st.success("✅ X-ray uploaded successfully.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.image(
            xray,
            caption="Uploaded Dental Radiograph",
            use_container_width=True
        )

    with col2:
        st.markdown("### 📋 Image Information")
        st.write("**File:**", xray.name)
        st.write("**Type:**", xray.type)

        st.markdown("### 🔍 Image Status")
        st.info("Radiograph received and ready for assessment.")

    st.divider()

    # ---------------- AI SECTION ----------------
    st.markdown(
        '<div class="section-title">🤖 AI-Assisted Provisional Assessment</div>',
        unsafe_allow_html=True
    )

    st.info(
        "AI radiographic analysis module is currently under development. "
        "The uploaded radiograph will be analysed by the AI model in a future version."
    )

    st.markdown("""
    **Planned AI assessment areas:**

    - 🦷 Dental caries
    - 🦴 Alveolar bone loss
    - 🔬 Periapical radiolucency / lesions
    - 🩻 Other selected radiographic findings
    - 📍 Finding location and description
    - 📋 AI-assisted provisional report
    """)

    st.divider()

    # ---------------- REPORT PREVIEW ----------------
    st.markdown(
        '<div class="section-title">📄 Provisional Report</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="info-card">
        <b>Patient:</b> Awaiting AI assessment<br>
        <b>Radiograph:</b> Uploaded successfully<br>
        <b>Radiographic findings:</b> AI analysis pending<br>
        <b>Provisional interpretation:</b> AI module under development
    </div>
    """, unsafe_allow_html=True)

# ---------------- DISCLAIMER ----------------
st.divider()

st.markdown("""
<div class="disclaimer">
<b>⚠️ Clinical Disclaimer</b><br><br>
This platform is intended for AI-assisted radiographic assessment
and educational/research purposes. It does not provide a definitive
clinical diagnosis. Radiographic findings should be interpreted
along with appropriate clinical examination and other diagnostic
information by a qualified dental professional.
</div>
""", unsafe_allow_html=True)

st.caption(
    "AMRs Dental X-ray AI • Research Prototype"
)
