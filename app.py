import streamlit as st
from datetime import date

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {
    background-color: #f5f8fb;
}

/* HEADER */
.hero {
    background: linear-gradient(135deg, #083b5c, #176b9c);
    padding: 32px 25px;
    border-radius: 20px;
    margin-bottom: 25px;
}

.hero-title {
    color: white !important;
    font-size: 38px;
    font-weight: 800;
}

.hero-subtitle {
    color: white !important;
    font-size: 19px;
    margin-top: 5px;
}

.hero-text {
    color: #eef8ff !important;
    font-size: 15px;
    margin-top: 12px;
}

/* SECTION HEADINGS */
.section-title {
    color: #12344d !important;
    font-size: 26px;
    font-weight: 800;
    margin-top: 15px;
    margin-bottom: 12px;
}

/* WORKFLOW */
.workflow-card {
    background-color: white;
    padding: 18px;
    border-radius: 15px;
    border: 1px solid #d9e5ed;
    min-height: 125px;
}

.workflow-number {
    color: #176b9c !important;
    font-size: 26px;
    font-weight: 800;
}

.workflow-title {
    color: #183b56 !important;
    font-size: 17px;
    font-weight: 700;
}

.workflow-text {
    color: #607080 !important;
    font-size: 14px;
}

/* REPORT */
.report-card {
    background-color: #ffffff !important;
    color: #172b3a !important;
    padding: 22px;
    border-radius: 16px;
    border: 2px solid #d7e3eb;
    box-shadow: 0 4px 15px rgba(0,0,0,0.06);
    line-height: 1.8;
}

.report-heading {
    color: #0b4f71 !important;
    font-size: 21px;
    font-weight: 800;
    margin-bottom: 12px;
}

.report-text {
    color: #172b3a !important;
    font-size: 16px;
}

/* DISCLAIMER */
.disclaimer {
    background-color: #fff8e6 !important;
    color: #4d3d16 !important;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #efd98d;
    line-height: 1.6;
}

/* FOOTER */
.footer {
    text-align: center;
    color: #718096 !important;
    padding: 20px;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- HEADER ----------------
st.markdown("""
<div class="hero">
    <div class="hero-title">🦷 AMRs Dental X-ray AI</div>

    <div class="hero-subtitle">
        AI-Assisted Dental Radiographic Assessment
    </div>

    <div class="hero-text">
        A research-oriented platform for preliminary assessment
        of dental radiographs using artificial intelligence.
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------- WORKFLOW ----------------
st.markdown(
    '<div class="section-title">🔄 Assessment Workflow</div>',
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-number">01</div>
        <div class="workflow-title">👤 Patient Information</div>
        <div class="workflow-text">
        Enter basic patient details.
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-number">02</div>
        <div class="workflow-title">🩻 Upload Radiograph</div>
        <div class="workflow-text">
        Upload the dental X-ray image.
        </div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-number">03</div>
        <div class="workflow-title">🤖 AI Assessment</div>
        <div class="workflow-text">
        Generate an AI-assisted assessment.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ---------------- PATIENT INFORMATION ----------------
st.markdown(
    '<div class="section-title">👤 Patient Information</div>',
    unsafe_allow_html=True
)

c1, c2 = st.columns(2)

with c1:

    st.markdown(
        '<div style="color:#12344d;font-size:17px;font-weight:800;margin-bottom:6px;">Patient Name</div>',
        unsafe_allow_html=True
    )

    name = st.text_input(
        "Patient Name",
        label_visibility="collapsed"
    )

    st.markdown(
        '<div style="color:#12344d;font-size:17px;font-weight:800;margin-top:14px;margin-bottom:6px;">Age</div>',
        unsafe_allow_html=True
    )

    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        step=1,
        label_visibility="collapsed"
    )

    st.markdown(
        '<div style="color:#12344d;font-size:17px;font-weight:800;margin-top:14px;margin-bottom:6px;">Sex</div>',
        unsafe_allow_html=True
    )

    sex = st.selectbox(
        "Sex",
        ["Select", "Male", "Female", "Other"],
        label_visibility="collapsed"
    )


with c2:

    st.markdown(
        '<div style="color:#12344d;font-size:17px;font-weight:800;margin-bottom:6px;">OP Number</div>',
        unsafe_allow_html=True
    )

    op_no = st.text_input(
        "OP Number",
        label_visibility="collapsed"
    )

    st.markdown(
        '<div style="color:#12344d;font-size:17px;font-weight:800;margin-top:14px;margin-bottom:6px;">Examination Date</div>',
        unsafe_allow_html=True
    )

    examination_date = st.date_input(
        "Examination Date",
        value=date.today(),
        label_visibility="collapsed"
    )

st.divider()


# ---------------- X-RAY ----------------
st.markdown(
    '<div class="section-title">🩻 Dental Radiograph</div>',
    unsafe_allow_html=True
)

st.write("Upload the patient's dental radiograph.")

xray = st.file_uploader(
    "Choose X-ray image",
    type=["jpg", "jpeg", "png"]
)


# ---------------- AFTER UPLOAD ----------------
if xray is not None:

    st.success("✅ Dental radiograph uploaded successfully.")

    c1, c2 = st.columns([2, 1])

    with c1:
        st.image(
            xray,
            caption="Uploaded Dental Radiograph",
            use_container_width=True
        )

    with c2:
        st.markdown("### 📋 Image Information")

        st.write("**File:**", xray.name)

        st.write("**Format:**", xray.type)

        st.success("🟢 Image received")


    st.divider()


    # ---------------- AI ASSESSMENT ----------------
    st.markdown(
        '<div class="section-title">🤖 AI-Assisted Provisional Assessment</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="report-card">

    <div class="report-heading">
    🔍 Radiographic Assessment
    </div>

    <div class="report-text">

    <b>Current status:</b><br>
    AI radiographic analysis module is currently under development.

    <br><br>

    The final system will analyse the
    <b>actual uploaded dental radiograph</b>
    and identify selected radiographic findings.

    <br><br>

    <b>Planned assessment areas:</b>

    <ul>
        <li>🦷 Dental caries</li>
        <li>🦴 Alveolar bone loss</li>
        <li>🔬 Periapical radiolucency / lesions</li>
        <li>📍 Location of radiographic findings</li>
        <li>📊 Extent and severity where appropriate</li>
        <li>📄 AI-assisted provisional radiographic report</li>
    </ul>

    </div>
    </div>
    """, unsafe_allow_html=True)


    st.divider()


    # ---------------- PROVISIONAL REPORT ----------------
    st.markdown(
        '<div class="section-title">📄 Provisional Radiographic Report</div>',
        unsafe_allow_html=True
    )

    patient_name = name if name else "Not entered"
    patient_op = op_no if op_no else "Not entered"

    st.markdown(f"""
    <div class="report-card">

    <div class="report-heading">
    🦷 AMRs Dental X-ray AI — Provisional Report
    </div>

    <div class="report-text">

    <b>Patient Name:</b> {patient_name}<br>
    <b>Age:</b> {age}<br>
    <b>Sex:</b> {sex}<br>
    <b>OP Number:</b> {patient_op}<br>
    <b>Examination Date:</b> {examination_date}

    <hr>

    <b>Radiograph:</b> Uploaded successfully.

    <br><br>

    <b>Radiographic Findings:</b><br>
    AI analysis pending.

    <br><br>

    <b>Provisional Interpretation:</b><br>
    The AI analysis module will provide findings after integration
    of a validated radiographic AI model.

    <br><br>

    <b>Recommendation:</b><br>
    Radiographic findings should be correlated with clinical examination
    and other appropriate diagnostic information by a qualified dentist.

    </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------- DISCLAIMER ----------------
st.divider()

st.markdown("""
<div class="disclaimer">

<b>⚠️ Clinical Disclaimer</b>

<br><br>

This platform is intended for AI-assisted radiographic assessment
and educational/research purposes. It does not provide a definitive
clinical diagnosis.

Radiographic findings should be interpreted together with clinical
examination and other appropriate diagnostic information by a
qualified dental professional.

</div>
""", unsafe_allow_html=True)


# ---------------- FOOTER ----------------
st.markdown("""
<div class="footer">
🦷 AMRs Dental X-ray AI
<br>
AI-Assisted Dental Radiographic Assessment • Research & Educational Platform
</div>
""", unsafe_allow_html=True)
