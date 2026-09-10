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

# ---------- USAGE STATUS ----------
remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count

if remaining > 0:
    st.info(
        f"🧪 AI analyses remaining today: {remaining} / {DAILY_ANALYSIS_LIMIT}"
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
        disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT)
    )

    if analyze:

        if st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT:

            st.warning(
                "⏳ Daily AI analysis limit reached. "
                "Please try again tomorrow."
            )

        else:

            try:

                api_key = st.secrets["GEMINI_API_KEY"]

                client = genai.Client(
                    api_key=api_key
                )

                image_bytes = xray.getvalue()

                image_base64 = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                # ==========================================================
                # COMMON SAFETY RULES
                # ==========================================================

                common_rules = """
You are an AI-assisted dental radiographic assessment system.

Analyze ONLY the actual uploaded radiograph.

CORE SAFETY PRINCIPLE:
Do good for the patient and never cause harm.

STRICT ACCURACY RULES:

1. NEVER invent, hallucinate, or assume a radiographic finding.

2. Report ONLY what is actually visible and reasonably supported
by the uploaded image.

3. If image quality is insufficient, clearly state:
"Not clearly assessable."

4. Do not convert uncertainty into a diagnosis.

5. Do not diagnose solely from the patient's age, sex, name,
OP number, or any other supplied patient information.

6. Do not use patient information to invent radiographic findings.

7. Do not recommend a specific medication or definitive treatment.

8. Do not provide a definitive clinical diagnosis.

9. If several explanations are possible, state the uncertainty.

10. Distinguish between:
- clearly visible finding
- reasonably suspected finding
- uncertain / not assessable finding

11. Never describe a normal structure as a disease.

12. Never describe image artifacts, overlap, projection errors,
or positioning errors as pathology.

13. If a finding cannot be confidently identified, say:
"Doubt / Unclear" or "Not clearly assessable."

14. Final interpretation, diagnosis and treatment planning must be
performed by a qualified dental professional.

IMAGE QUALITY:

First assess:
- resolution
- sharpness
- contrast
- exposure
- positioning
- cropping
- overlap
- artifacts
- visible anatomy

Classify image quality as:
Adequate / Limited / Poor

If quality limits interpretation, explicitly mention it.
"""

                # ==========================================================
                # IOPA PROMPT
                # ==========================================================

                iopa_prompt = """

RADIOGRAPH TYPE:
IOPA (Intraoral Periapical Radiograph)

Perform a cautious IOPA assessment.

TOOTH IDENTIFICATION – FDI SYSTEM:

Before assigning an FDI number determine, where possible:

a. Maxillary or mandibular region.
b. Right or left side using actual anatomical orientation.
c. Incisor, canine, premolar or molar.
d. Position within the quadrant.
e. Tooth morphology, root morphology and neighboring teeth.

DO NOT number teeth simply from left to right.

DO NOT guess an FDI number from image position alone.

Use an FDI number only when anatomical evidence is sufficient.

Permanent teeth:

11–18 = upper right
21–28 = upper left
31–38 = lower left
41–48 = lower right

Primary teeth:

51–55 = upper right
61–65 = upper left
71–75 = lower left
81–85 = lower right

If exact identification is not reliable, write:

"FDI tooth number cannot be reliably determined from this image."

CARIES:

Report caries only when a discrete anatomically plausible
radiolucency is visible.

Do NOT call the following caries:
- cervical burnout
- overlapping teeth
- restorations
- artifacts
- normal anatomy

For each suspected lesion report:

- FDI tooth number or region
- Surface:
  occlusal / proximal / cervical-root / other
- Visible radiolucency:
  Yes / No
- Apparent depth:
  Enamel
  Enamel and dentin
  Deep dentin
  Approaching pulp space
  Not clearly assessable
- Confidence:
  Low / Moderate / High
- Brief radiographic description

Only use "approaching pulp space" when the lesion is visibly
very close to the pulp space.

If there is no definite caries:

"No definite radiographic caries identified."

PERIODONTAL BONE:

Report bone loss only when the alveolar crest relationship
to the CEJ and adjacent teeth is clearly visible.

Do not call bone loss generalized unless multiple regions
clearly demonstrate it.

PERIAPICAL REGION:

Report a periapical abnormality only when actual radiographic
evidence supports it.

Do not diagnose periapical disease from PDL widening alone.

Do not automatically label a radiolucency as:
- cyst
- granuloma
- abscess

unless imaging features strongly support such a description.

OTHER FINDINGS:

Report only clearly visible findings.

OUTPUT:

### IMAGE QUALITY

Adequate / Limited / Poor

Explanation.

### TOOTH IDENTIFICATION

For clearly assessable affected teeth:
- FDI number if reliable
- anatomical reason for identification

### CARIES FINDINGS

List definite or reasonably suspected lesions only.

### OTHER CLEARLY VISIBLE FINDINGS

### PROVISIONAL RADIOGRAPHIC INTERPRETATION

### LIMITATIONS

Mention blur, overlap, cropping, low resolution,
artifacts, missing landmarks or inadequate orientation
when present.
"""

                # ==========================================================
                # OPG PROMPT
                # ==========================================================

                opg_prompt = """

RADIOGRAPH TYPE:
OPG (Orthopantomogram / Panoramic Radiograph)

Perform a comprehensive but cautious panoramic radiographic
assessment.

Assess ONLY structures that are actually visible.

1. DENTITION

Assess, where clearly visible:
- presence or absence of teeth
- missing teeth
- retained teeth
- unerupted teeth
- impacted teeth
- partially erupted teeth
- gross tooth abnormalities
- root abnormalities

Do not guess exact tooth numbers when orientation is uncertain.

Use FDI numbering only when reliably supported by anatomy.

2. CARIES

Look for radiographically visible carious radiolucencies.

Do not call:
- cervical burnout
- overlap
- restoration margins
- artifacts
- normal anatomy

caries.

Report:
- tooth/region
- surface if visible
- apparent depth
- confidence
- radiographic description

If not clearly visible:
"Not clearly assessable."

3. PERIAPICAL REGION

Assess visible apices for:
- clearly visible periapical radiolucency
- other obvious periapical abnormality

Do not diagnose cyst, granuloma or abscess unless imaging
features reasonably support the interpretation.

4. PERIODONTAL SUPPORT

Assess visible alveolar bone levels.

Report:
- localized bone loss
- vertical/angular pattern if clearly visible
- furcation involvement only when actually visible

Do not call generalized bone loss unless multiple regions
clearly demonstrate it.

5. IMPACTED / UNERUPTED TEETH

Report only when clearly visible.

If an impacted tooth is identified, describe:
- region
- orientation
- relationship to adjacent structures if visible

Do not invent exact angulation measurements.

6. JAW BONES

Look for clearly visible:
- radiolucencies
- radiopacities
- mixed-density abnormalities
- cortical changes
- obvious expansion
- other significant abnormalities

Do not automatically label an unknown lesion as a cyst,
tumor or malignancy.

Use descriptive terminology when diagnosis is uncertain.

7. MAXILLARY SINUSES

When adequately visualized, comment on clearly visible:
- gross opacification
- mucosal thickening if clearly appreciable
- other obvious radiographic abnormality

Do not make a definitive ENT diagnosis.

8. TMJ / CONDYLAR REGION

When visible:
- condylar symmetry
- gross morphological asymmetry
- obvious radiographic abnormality

Do not diagnose TMJ disease from panoramic appearance alone.

9. FRACTURES

Report a fracture only if a definite fracture line,
discontinuity or displacement is actually visible.

10. DEVELOPMENTAL / SKELETAL ABNORMALITIES

Report only clearly visible abnormalities.

11. OTHER SIGNIFICANT FINDINGS

Report only findings supported by the actual image.

OUTPUT:

### IMAGE QUALITY

Adequate / Limited / Poor

### DENTITION OVERVIEW

### CARIES FINDINGS

### MISSING / IMPACTED / UNERUPTED TEETH

### PERIAPICAL FINDINGS

### PERIODONTAL / ALVEOLAR BONE FINDINGS

### JAW-BONE FINDINGS

### MAXILLARY SINUS FINDINGS

### TMJ / CONDYLAR FINDINGS

### OTHER CLEARLY VISIBLE FINDINGS

### PROVISIONAL RADIOGRAPHIC INTERPRETATION

### LIMITATIONS

Mention areas obscured by:
- cervical spine
- superimposition
- motion
- positioning
- cropping
- low resolution
- artifacts

when present.
"""

                # ==========================================================
                # BITEWING PROMPT
                # ==========================================================

                bitewing_prompt = """

RADIOGRAPH TYPE:
Bitewing Radiograph

Perform a cautious bitewing assessment.

Focus on structures normally assessable on bitewing images:

1. INTERPROXIMAL CARIES

Look for discrete radiolucencies on proximal surfaces.

Assess:
- tooth/region
- mesial or distal surface when reliable
- enamel involvement
- dentin involvement
- depth when visible
- confidence

Do not call cervical burnout, overlap or artifacts caries.

2. OCCLUSAL CARIES

Report only when radiographic evidence is visible.

3. RESTORATIONS

Mention clearly visible restorations only when relevant.

Do not interpret restoration margins as recurrent caries
unless there is actual supporting radiographic evidence.

4. ALVEOLAR CREST

Assess bone levels where adequately visible.

5. OTHER FINDINGS

Report only clearly visible findings.

OUTPUT:

### IMAGE QUALITY

### TOOTH / REGION IDENTIFICATION

### INTERPROXIMAL CARIES

### OTHER CARIES FINDINGS

### ALVEOLAR BONE FINDINGS

### OTHER CLEARLY VISIBLE FINDINGS

### PROVISIONAL RADIOGRAPHIC INTERPRETATION

### LIMITATIONS
"""

                # ==========================================================
                # OCCLUSAL PROMPT
                # ==========================================================

                occlusal_prompt = """

RADIOGRAPH TYPE:
Occlusal Radiograph

Perform a cautious occlusal radiographic assessment.

Assess only structures actually visible.

Consider:

1. Teeth and dentition
- unerupted teeth
- supernumerary teeth
- gross positional abnormalities
- developmental abnormalities

2. Jaw bones
- radiolucencies
- radiopacities
- cortical expansion
- obvious bone abnormalities

3. Midline structures when visible.

4. Localized lesions when radiographically supported.

5. Foreign bodies or calcifications only when clearly visible.

6. Fracture or displacement only when actual evidence is visible.

Do not label an unknown radiolucency as a cyst or tumor
without sufficient radiographic support.

OUTPUT:

### IMAGE QUALITY

### TEETH / DENTITION

### JAW-BONE FINDINGS

### LESIONS / ABNORMALITIES

### OTHER CLEARLY VISIBLE FINDINGS

### PROVISIONAL RADIOGRAPHIC INTERPRETATION

### LIMITATIONS
"""

                # ==========================================================
                # FACIAL RADIOGRAPH PROMPT
                # ==========================================================

                facial_prompt = """

RADIOGRAPH TYPE:
Facial Radiograph

Perform a comprehensive but cautious radiographic assessment
of the facial skeleton.

This is NOT limited to fracture detection.

Assess only anatomy that is adequately visualized.

1. FRACTURES

Look for actual evidence of:
- fracture lines
- cortical discontinuity
- displacement
- step deformity

Do not report a fracture from vague asymmetry alone.

2. MANDIBLE

Assess visible:
- body
- angle
- ramus
- condylar region
- coronoid region

Report only clear abnormalities.

3. MAXILLA

Assess visible maxillary structures for:
- fracture
- discontinuity
- obvious abnormality

4. ZYGOMATIC / ORBITAL REGION

Assess:
- zygomatic arch
- orbital margins
- obvious discontinuity
- gross asymmetry when radiographically meaningful

5. NASAL REGION

Assess visible nasal bones and surrounding structures
for obvious abnormalities.

6. PARANASAL SINUSES

When adequately visualized, report clearly visible:
- gross opacification
- air-fluid level if clearly visible
- other obvious radiographic abnormality

Do not make a definitive sinus disease diagnosis.

7. FACIAL ALIGNMENT

Report only obvious radiographic displacement or
alignment abnormality.

8. BONE LESIONS

Report clearly visible:
- radiolucent abnormalities
- radiopaque abnormalities
- mixed-density abnormalities
- cortical changes

Do not automatically diagnose cyst, tumor or malignancy.

Use descriptive wording if diagnosis is uncertain.

9. DEVELOPMENTAL / SKELETAL ABNORMALITIES

Report only abnormalities that are clearly visible.

10. OTHER SIGNIFICANT FINDINGS

Report only findings supported by the actual image.

OUTPUT:

### IMAGE QUALITY

### FRACTURE ASSESSMENT

### MANDIBLE

### MAXILLA

### ZYGOMATIC / ORBITAL REGION

### NASAL REGION

### SINUSES

### FACIAL ALIGNMENT

### BONE / SKELETAL FINDINGS

### OTHER CLEARLY VISIBLE FINDINGS

### PROVISIONAL RADIOGRAPHIC INTERPRETATION

### LIMITATIONS
"""

                # ==========================================================
                # OTHER / UNKNOWN PROMPT
                # ==========================================================

                other_prompt = """

RADIOGRAPH TYPE:
Other / Not reliably classifiable

First determine whether the uploaded image can be reasonably
classified as a dental or facial radiograph.

Do NOT force classification.

Assess:
- whether the image is actually a radiograph
- approximate radiographic type if recognizable
- visible anatomical region
- image quality
- obvious abnormalities only

If the radiograph type cannot be reliably determined, state:

"Radiograph type cannot be reliably classified from this image."

Do not perform detailed tooth-specific diagnosis when the
image type or orientation is inadequate.

Report only clearly visible abnormalities.

OUTPUT:

### IMAGE QUALITY

### RADIOGRAPH CLASSIFICATION

### VISIBLE ANATOMICAL REGION

### CLEARLY VISIBLE FINDINGS

### PROVISIONAL RADIOGRAPHIC INTERPRETATION

### LIMITATIONS
"""

                # ==========================================================
                # SELECT PROMPT BASED ON RADIOGRAPH TYPE
                # ==========================================================

                if radiograph_type == "IOPA":
                    specific_prompt = iopa_prompt

                elif radiograph_type == "OPG":
                    specific_prompt = opg_prompt

                elif radiograph_type == "Bitewing":
                    specific_prompt = bitewing_prompt

                elif radiograph_type == "Occlusal":
                    specific_prompt = occlusal_prompt

                elif radiograph_type == "Facial radiograph":
                    specific_prompt = facial_prompt

                else:
                    specific_prompt = other_prompt

                # ==========================================================
                # FINAL PROMPT
                # ==========================================================

                prompt = (
                    common_rules
                    + "\n\n"
                    + specific_prompt
                    + """

FINAL SAFETY REQUIREMENT:

The output is an AI-assisted provisional radiographic assessment.

Do not provide a definitive diagnosis.

Do not recommend a specific treatment.

If clinical correlation or additional imaging is needed,
state that as a cautious next clinical step without prescr
