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

Analyze ONLY the actual uploaded dental X-ray image.

STRICT ACCURACY RULES:

1. NEVER invent or hallucinate caries or any other finding.

2. NEVER guess an exact tooth number.
   Do NOT assign FDI numbers or numbers based on left-to-right position.
   Only provide a tooth number when reliable anatomical landmarks clearly
   establish the tooth identity.
   Otherwise use terms such as:
   "upper right posterior region",
   "lower left posterior region",
   "anterior region",
   or "tooth/region not reliably identifiable."

3. NEVER call cervical burnout, overlapping teeth, image artifacts,
   restorations, or normal anatomical structures caries.

4. A carious lesion should be reported only when there is a discrete,
   anatomically plausible radiolucency consistent with caries.

5. If the image quality is poor, blurred, cropped, overlapped, or too small
   to confidently assess a suspected lesion, state:
   "Not clearly assessable."

6. Use HIGH confidence only when the radiographic appearance is clearly
   characteristic of caries and image quality is adequate.

7. Use MODERATE confidence when caries is reasonably suspected but some
   uncertainty remains.

8. Use LOW confidence when the finding is subtle or could reasonably be
   explained by an artifact, overlap, burnout, or another non-carious cause.

9. Do not diagnose pulpal necrosis, pulp vitality, or definite pulpal disease.

10. Do not diagnose periapical disease from periodontal ligament widening alone.

11. Do not recommend a specific treatment.

CARIES ASSESSMENT:

For each suspected lesion report:

- Tooth/region: only if reliably identifiable
- Surface: occlusal / proximal / cervical-root / other
- Visible radiolucency: Yes / No
- Apparent depth:
  - Enamel
  - Enamel and dentin
  - Deep dentin
  - Approaching pulp space
  - Not clearly assessable
- Confidence: Low / Moderate / High
- Brief description of the actual visible radiographic evidence

Only use "approaching pulp space" when the radiolucency is visibly very close
to the pulp space.

If there is no definite caries, state:

"No definite radiographic caries identified."

OTHER FINDINGS:

Report only clearly visible findings.

For periodontal bone loss, report it only when the reduction in alveolar
crest height is clearly visible relative to the CEJ and adjacent teeth.

Do NOT use the word "generalized" unless clear bone loss is visible in
multiple regions of the image.

OUTPUT:

### IMAGE QUALITY
Adequate / Limited / Poor, with a short explanation.

### CARIES FINDINGS
List only definite or reasonably suspected lesions.

### OTHER CLEARLY VISIBLE FINDINGS
List only clearly visible findings.

### PROVISIONAL RADIOGRAPHIC INTERPRETATION
Give a cautious interpretation based only on visible evidence.

### LIMITATIONS
Mention blur, overlap, cropping, low resolution, artifacts, or other
limitations.

This is an AI-assisted provisional radiographic assessment for educational
and research purposes. It is not a definitive diagnosis. Final
interpretation must be performed by a qualified dental professional.
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
