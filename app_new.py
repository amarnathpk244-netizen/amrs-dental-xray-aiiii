import streamlit as st
from datetime import date

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered"
)

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

    # ---------- ANALYZE ----------
    st.markdown(
        '<div class="section">🤖 AI Assessment</div>',
        unsafe_allow_html=True
    )

    analyze = st.button(
        "🔍 Analyze X-ray",
        use_container_width=True
    )

    if analyze:
        st.warning(
            "AI analysis is not connected yet. "
            "The uploaded image has been received successfully. "
            "No artificial or random findings are generated."
        )

else:
    st.caption("No X-ray uploaded yet.")


# ---------- REPORT ----------
st.markdown(
    '<div class="section">📋 Provisional Radiographic Report</div>',
    unsafe_allow_html=True
)

if xray is None:
    st.info("Upload an X-ray to begin the assessment.")

else:
    st.markdown(
        """
        **Patient:** {}
        
        **Age:** {}
        
        **Sex:** {}
        
        **OP Number:** {}
        
        **Examination Date:** {}
        """.format(
            patient_name if patient_name else "Not provided",
            age if age else "Not provided",
            sex if sex != "Select" else "Not provided",
            op_number if op_number else "Not provided",
            examination_date
        )
    )

    st.markdown(
        """
        ### AI Findings

        **Status:** Awaiting AI image-analysis connection.

        The system will only report findings after the uploaded
        radiograph has been processed by the AI model.
        """
    )


# ---------- DISCLAIMER ----------
st.markdown(
    """
    <div class="disclaimer">
    ⚠️ <b>Clinical Disclaimer:</b><br>
    This application is intended for AI-assisted radiographic
    assessment, educational and research purposes. It is not a
    substitute for examination by a qualified dental professional.
    Final diagnosis and treatment decisions must be made by a
    qualified clinician using appropriate clinical and radiographic
    information.
    </div>
    """,
    unsafe_allow_html=True
)
