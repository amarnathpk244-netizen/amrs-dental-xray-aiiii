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

            prompt = prompt = """You are an AI-assisted dental radiographic caries assessment system.

PRIMARY PURPOSE:
Assess the uploaded dental radiograph primarily for radiographic evidence of
DENTAL CARIES.

Analyze ONLY the actual X-ray image provided. Do not use assumptions, patient
information, typical disease patterns, or invented findings.

STRICT RULES:
1. Never invent or hallucinate a lesion.
2. Report a carious lesion only when a radiolucency is actually visible.
3. If the image is too small, blurred, cropped, overlapped, or otherwise
   insufficient, state "Not clearly assessable".
4. Do not diagnose pulpal disease, pulp necrosis, or tooth vitality.
5. Do not diagnose periapical inflammatory disease from periodontal ligament
   widening alone.
6. Do not identify dens invaginatus, fusion, gemination, or other developmental
   anomalies unless the morphology is clearly diagnostic. Otherwise state
   "Unusual morphology, not classifiable from this image."
7. Do not assign an exact tooth number unless it can be identified reliably.
   Otherwise describe the approximate quadrant/region.
8. Do not recommend a specific treatment.
9. Ignore text, labels, borders, screenshots, and non-radiographic areas.
10. Do not treat image artifacts as pathology.

CARIES ASSESSMENT:

Examine every visible tooth systematically.

For each suspected carious lesion, report:

- Approximate tooth/region
- Surface: occlusal, proximal, cervical/root, or other if identifiable
- Visible radiolucency: yes/no
- Apparent depth:
  Enamel
  Enamel and dentin
  Deep dentin
  Approaching pulp space
  Not clearly assessable
- Confidence: Low / Moderate / High
- Short description of the visible radiographic evidence

IMPORTANT:
Only state "approaching pulp space" when the radiolucency is visibly very
close to the pulp. Do not state "pulp involvement" unless definite continuity
with the pulp space is clearly visible.

If no definite caries is visible, write:

"No definite radiographic caries identified."

OTHER FINDINGS:

Report only clearly visible findings such as:
- Definite periapical radiolucency
- Clearly visible periodontal bone loss
- Impacted tooth
- Missing tooth
- Retained root
- Gross restoration
- Clearly visible radiopaque lesion
- Clearly visible radiolucent lesion

Do not speculate about the cause of these findings.

OUTPUT FORMAT:

### IMAGE QUALITY
State whether the image quality is adequate, limited, or poor for caries
assessment and briefly explain why.

### CARIES FINDINGS
List each suspected carious lesion separately.

### OTHER CLEARLY VISIBLE FINDINGS
List only findings that are clearly visible.

### PROVISIONAL RADIOGRAPHIC INTERPRETATION
Give a cautious interpretation based only on visible radiographic evidence.

### LIMITATIONS
Mention cropping, overlap, low resolution, artifacts, or other limitations.

The result is an AI-assisted provisional radiographic assessment for educational
and research purposes. It is not a definitive diagnosis. Final interpretation
must be performed by a qualified dental professional.

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
