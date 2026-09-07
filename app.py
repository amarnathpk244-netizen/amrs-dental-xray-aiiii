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
    .stApp {
        background: #f5f8fb;
    }

    .hero {
        background: linear-gradient(135deg, #0b3d62, #176b9c);
        padding: 38px 30px;
        border-radius: 22px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }

    .hero-title {
        font-size: 42px;
        font-weight: 800;
        line-height: 1.15;
        color: white;
    }

    .hero-subtitle {
        font-size: 20px;
        margin-top: 8px;
        color: #e9f5ff;
    }

    .hero-text {
        font-size: 16px;
        margin-top: 14px;
        color: #f4fbff;
    }

    .section-title {
        font-size: 27px;
        font-weight: 750;
        color: #12344d;
        margin-top: 15px;
        margin-bottom: 12px;
    }

    .workflow-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #dce6ee;
        min-height: 135px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.05);
    }

    .workflow-number {
        font-size: 28px;
        font-weight: 800;
        color: #176b9c;
    }

    .workflow-title {
        font-size: 18px;
        font-weight: 700;
        color: #183b56;
        margin-top: 5px;
    }

    .workflow-text {
        color: #617384;
        font-size: 14px;
    }

    .info-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #dce6ee;
        box-shadow: 0 3px 12px rgba(0,0,0,0.05);
    }

    .disclaimer {
        background: #fff8e6;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #f0d98c;
        color: #5d4a16;
    }

    .footer {
        text-align: center;
        color: #718096;
        padding: 25px 0 10px 0;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- HERO HEADER ----------------
st.markdown("""
<div class="hero">
    <div class="hero-title">🦷 AMRs Dental X-ray AI</div>
    <div class="hero-subtitle">
        AI-Assisted Dental Radiographic Assessment
    </div>
    <div class="hero-text">
        A research-oriented digital platform designed to support
        preliminary assessment of dental radiographs using artificial intelligence.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- WORKFLOW ----------------
st.markdown(
    '<div class="section-title">🔄 Assessment Workflow</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-number">01</div>
        <div class="workflow-title">👤 Patient Information</div>
        <div class="workflow-text">
            Enter basic patient and examination details.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-number">02</div>
        <div class="workflow-title">🩻 Upload Radiograph</div>
        <div class="workflow-text">
            Upload a dental X-ray image for assessment.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-number">03</div>
        <div class="workflow-title">🤖 AI Assessment</div>
        <div class="workflow-text">
            Generate an AI-assisted provisional radiographic assessment.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ---------------- PATIENT DETAILS ----------------
st.markdown(
    '<div class="section-title">👤 Patient Information</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col1:
    name = st.text_input("Patient Name")
    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        step=1
    )
    sex = st.selectbox(
        "Sex",
        ["Select", "Male", "Female", "Other"]
    )

with col2:
    op_no = st.text_input("OP Number")
    examination_date = st.date_input(
        "Examination Date",
        value=date.today()
    )

st.divider()

# ---------------- RADIOGRAPH ----------------
st.markdown(
    '<div class="section-title">🩻 Dental Radiograph</div>',
    unsafe_allow_html=True
)

st.write(
    "Upload the patient's dental radiograph for AI-assisted assessment."
)

xray = st.file_uploader(
    "Choose X-ray image",
    type=["jpg", "jpeg", "png"],
    help="Supported formats: JPG, JPEG and PNG"
)

if xray is not None:

    st.success("✅ Radiograph uploaded successfully.")

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
        st.write("**Format:**", xray.type)

        st.markdown("### 🔍 Status")

        st.success("Radiograph received.")

        st.caption(
            "The image is ready for the AI assessment module."
        )

    st.divider()

    # ---------------- AI ASSESSMENT ----------------
    st.markdown(
        '<div class="section-title">🤖 AI-Assisted Provisional Assessment</div>',
        unsafe_allow_html=True
    )

    st.info(
        "The AI radiographic analysis module is currently under development. "
        "This section will analyse the actual uploaded radiograph once the "
        "validated AI model is integrated."
    )

    st.markdown("""
    **Planned assessment areas**

    🦷 **Dental caries**  
    🦴 **Alveolar bone loss**  
    🔬 **Periapical radiolucency / lesions**  
    📍 **Location and radiographic description**  
    📊 **Extent / severity where appropriate**  
    📄 **AI-assisted provisional radiographic report**
    """)

    st.divider()

    # ---------------- REPORT ----------------
    st.markdown(
        '<div class="section-title">📄 Provisional Report</div>',
        unsafe_allow_html=True
    )

    st.markdown(f"""
    <div class="info-card">
        <b>Patient:</b> {name if name else "Not entered"}<br><br>
        <b>OP Number:</b> {op_no if op_no else "Not entered"}<br><br>
        <b>Examination Date:</b> {examination_date}<br><br>
        <b>Radiograph:</b> Uploaded successfully<br><br>
        <b>Radiographic findings:</b> AI analysis pending<br><br>
        <b>Provisional interpretation:</b> AI model integration pending
    </div>
    """, unsafe_allow_html=True)

# ---------------- DISCLAIMER ----------------
st.divider()

st.markdown("""
<div class="disclaimer">
    <b>⚠️ Clinical Disclaimer</b><br><br>
    This platform is intended for AI-assisted radiographic assessment
    and educational/research purposes. It does not provide a definitive
    clinical diagnosis. Radiographic findings must be interpreted together
    with clinical examination and other appropriate diagnostic information
    by a qualified dental professional.
</div>
""", unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown("""
<div class="footer">
    🦷 AMRs Dental X-ray AI &nbsp;•&nbsp; AI-Assisted Dental Radiographic Assessment
    <br>
    Research & Educational Prototype
</div>
""", unsafe_allow_html=True)
