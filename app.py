import streamlit as st

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷"
)

st.title("🦷 AMRs Dental X-ray AI")
st.write("AI-assisted dental radiograph assessment")

st.subheader("Patient Details")

name = st.text_input("Patient Name")
age = st.number_input("Age", min_value=1, max_value=120, step=1)
sex = st.selectbox("Sex", ["Male", "Female", "Other"])
op_no = st.text_input("OP Number")

st.subheader("Upload Dental X-ray")

xray = st.file_uploader(
    "Upload your dental radiograph",
    type=["jpg", "jpeg", "png"]
)

if xray is not None:
    st.image(xray, caption="Uploaded X-ray", use_container_width=True)

    st.success("X-ray uploaded successfully.")

    st.subheader("AI-Assisted Provisional Assessment")

    st.info(
        "This is a demonstration version. "
        "AI analysis will be added in the next step."
    )

    st.warning(
        "This assessment is not a diagnosis. "
        "Please consult a qualified dentist for clinical confirmation."
    )
