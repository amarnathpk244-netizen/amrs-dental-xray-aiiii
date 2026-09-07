import streamlit as st
from datetime import date

# ==============================
# PAGE SETTINGS
# ==============================

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="wide"
)

# ==============================
# HEADER
# ==============================

st.title("🦷 AMRs Dental X-ray AI")

st.subheader("AI-Assisted Dental Radiographic Assessment")

st.write(
    "A research-oriented platform for preliminary assessment "
    "of dental radiographs using artificial intelligence."
)

st.divider()

# ==============================
# WORKFLOW
# ==============================

st.header("🔄 Assessment Workflow")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("01 👤 Patient Information")
    st.write("Enter basic patient details.")

with col2:
    st.subheader("02 🩻 Upload Radiograph")
    st.write("Upload the dental X-ray image.")

with col3:
    st.subheader("03 🤖 AI Assessment")
    st.write("Generate an AI-assisted assessment.")

st.divider()

# ==============================
# PATIENT INFORMATION
# ==============================

st.header("👤 Patient Information")

left, right = st.columns(2)

with left:

    patient_name = st.text_input(
        "Patient Name"
    )

    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        value=0,
        step=1
    )

    sex = st.selectbox(
        "Sex",
        ["Select", "Male", "Female", "Other"]
    )

with right:

    op_number = st.text_input(
        "OP Number"
    )

    examination_date = st.date_input(
        "Examination Date",
        value=date.today()
    )

st.divider()

# ==============================
# RADIOGRAPH UPLOAD
# ==============================

st.header("🩻 Dental Radiograph")

st.write(
    "Upload the patient's dental radiograph."
)

xray = st.file_uploader(
    "Choose X-ray image",
    type=["jpg", "jpeg", "png"]
)

# ==============================
# IMAGE DISPLAY
# ==============================

if xray is not None:

    st.success(
        "✅ Dental radiograph uploaded successfully."
    )

    image_col, details_col = st.columns([2, 1])

    with image_col:

        st.image(
            xray,
            caption="Uploaded Dental Radiograph",
            use_container_width=True
        )

    with details_col:

        st.subheader("📋 Image Information")

        st.write(
            "File:",
            xray.name
        )

        st.write(
            "Format:",
            xray.type
        )

        st.success(
            "🟢 Image received"
        )

    st.divider()

    # ==============================
    # AI ASSESSMENT
    # ==============================

    st.header(
        "🤖 AI-Assisted Provisional Assessment"
    )

    st.subheader(
        "🔍 Radiographic Assessment"
    )

    st.info(
        "AI radiographic analysis module is currently "
        "under development."
    )

    st.write(
        "The final system will analyse the actual uploaded "
        "dental radiograph and identify selected radiographic findings."
    )

    st.subheader(
        "Planned Assessment Areas"
    )

    st.write("🦷 Dental caries")
    st.write("🦴 Alveolar bone loss")
    st.write("🔬 Periapical radiolucency / lesions")
    st.write("📍 Location of radiographic findings")
    st.write("📊 Extent and severity where appropriate")
    st.write("📄 AI-assisted provisional radiographic report")

    st.divider()

    # ==============================
    # PROVISIONAL REPORT
    # ==============================

    st.header(
        "📄 Provisional Radiographic Report"
    )

    st.subheader(
        "🦷 AMRs Dental X-ray AI — Provisional Report"
    )

    st.write(
        "**Patient Name:**",
        patient_name if patient_name else "Not entered"
    )

    st.write(
        "**Age:**",
        age
    )

    st.write(
        "**Sex:**",
        sex
    )

    st.write(
        "**OP Number:**",
        op_number if op_number else "Not entered"
    )

    st.write(
        "**Examination Date:**",
        examination_date
    )

    st.divider()

    st.write(
        "**Radiograph:**"
    )

    st.write(
        "Uploaded successfully."
    )

    st.write(
        "**Radiographic Findings:**"
    )

    st.write(
        "AI analysis pending."
    )

    st.write(
        "**Provisional Interpretation:**"
    )

    st.write(
        "The AI analysis module will provide findings after "
        "integration of a validated radiographic AI model."
    )

    st.write(
        "**Recommendation:**"
    )

    st.write(
        "Radiographic findings should be correlated with clinical "
        "examination and other appropriate diagnostic information "
        "by a qualified dentist."
    )

# ==============================
# CLINICAL DISCLAIMER
# ==============================

st.divider()

st.header(
    "⚠️ Clinical Disclaimer"
)

st.warning(
    "This platform is intended for AI-assisted radiographic "
    "assessment and educational/research purposes. "
    "It does not provide a definitive clinical diagnosis."
)

st.write(
    "Radiographic findings should be interpreted together with "
    "clinical examination and other appropriate diagnostic "
    "information by a qualified dental professional."
)

# ==============================
# FOOTER
# ==============================

st.divider()

st.caption(
    "🦷 AMRs Dental X-ray AI | "
    "AI-Assisted Dental Radiographic Assessment | "
    "Research & Educational Platform"
)
