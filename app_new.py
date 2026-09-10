import streamlit as st
from datetime import date
from google import genai
from google.genai import types

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered"
)

# ============================================================
# SETTINGS
# ============================================================

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-2.5-flash"

# ============================================================
# DAILY USAGE
# ============================================================

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()

# ============================================================
# MOBILE UI
# ============================================================

st.markdown(
    """
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
    """,
    unsafe_allow_html=True
)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="app-title">🦷 AMRs Dental X-ray AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">AI-Assisted Dental Radiographic Assessment</div>',
    unsafe_allow_html=True
)

# ============================================================
# USAGE STATUS
# ============================================================

remaining = (
    DAILY_ANALYSIS_LIMIT
    - st.session_state.analysis_count
)

if remaining > 0:
    st.info(
        f"🧪 AI analyses remaining today: "
        f"{remaining} / {DAILY_ANALYSIS_LIMIT}"
    )
else:
    st.warning(
        "⏳ Your 3 AI analyses for today have been used. "
        "Please try again tomorrow."
    )

# ============================================================
# PATIENT INFORMATION
# ============================================================

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
        [
            "Select",
            "Male",
            "Female",
            "Other"
        ]
    )

op_number = st.text_input(
    "OP Number",
    placeholder="Enter OP number"
)

examination_date = st.date_input(
    "Examination Date",
    value=date.today()
)

# ============================================================
# RADIOGRAPH TYPE
# ============================================================

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

# ============================================================
# X-RAY UPLOAD
# ============================================================

st.markdown(
    '<div class="section">📤 Upload Dental Radiograph</div>',
    unsafe_allow_html=True
)

st.info(
    "Upload a dental X-ray image in JPG, JPEG or PNG format."
)

xray = st.file_uploader(
    "📷 Choose X-ray image",
    type=[
        "jpg",
        "jpeg",
        "png"
    ],
    accept_multiple_files=False,
    key="dental_xray_upload",
    label_visibility="visible"
)

# ============================================================
# IMAGE PREVIEW
# ============================================================

if xray is not None:

    st.success(
        "✅ X-ray uploaded successfully."
    )

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

    # ========================================================
    # AI ANALYSIS
    # ========================================================

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

                # ====================================================
                # GEMINI API
                # ====================================================

                api_key = st.secrets["GEMINI_API_KEY"]

                client = genai.Client(
                    api_key=api_key
                )

                # ====================================================
                # IMAGE DATA
                # ====================================================

                image_bytes = xray.getvalue()

                mime_type = xray.type

                if mime_type not in [
                    "image/jpeg",
                    "image/png"
                ]:

                    st.error(
                        "❌ Unsupported image format."
                    )

                    st.stop()

                # ====================================================
                # SAFETY INSTRUCTIONS
                # ====================================================

                safety_rules = """
You are AMRs Dental X-ray AI.

You are an AI-assisted radiographic assessment system
for qualified dental professionals.

IMPORTANT SAFETY RULES:

1. Analyze ONLY the actual uploaded X-ray image.

2. NEVER invent or hallucinate radiographic findings.

3. NEVER use random or fixed findings.

4. If a finding is not clearly visible, say:
   "Not clearly assessable."

5. If image quality is poor, blurred, cropped,
   distorted, overexposed, underexposed, or otherwise
   inadequate, clearly state this.

6. Do not diagnose something simply because it is common.

7. Do not assign an FDI tooth number unless the tooth
   can be reliably identified from the visible anatomy.

8. Never assign a tooth number merely based on image
   position.

9. Clearly distinguish:
   - Clearly visible
   - Possible
   - Unclear

10. Do not provide a definitive diagnosis.

11. Do not prescribe medication.

12. Do not provide definitive treatment planning.

13. Do not use patient information to invent findings.

14. If the image does not provide enough information,
    say so.

15. When uncertain, choose uncertainty rather than guessing.

16. The final diagnosis and treatment decision must be
    made by a qualified dental professional.

17. Only report findings that have actual visual evidence
    in the uploaded image.
"""

                # ====================================================
                # RADIOGRAPH-SPECIFIC PROMPT
                # ====================================================

                if radiograph_type == "IOPA":

                    radiograph_instructions = """
The selected radiograph is IOPA.

Assess only visible structures such as:

- Teeth
- Crowns
- Roots
- Lamina dura
- Periodontal ligament space
- Alveolar bone
- Periapical region
- Obvious caries
- Obvious restorations
- Impacted teeth when clearly visible
- Periapical radiolucency/radiopacity
- Other clearly visible abnormalities

Do not diagnose subtle changes without adequate evidence.
"""

                elif radiograph_type == "OPG":

                    radiograph_instructions = """
The selected radiograph is OPG.

Assess only visible structures such as:

- Overall dentition
- Missing teeth when clearly visible
- Impacted/unerupted teeth
- Obvious caries
- Obvious periapical abnormalities
- Alveolar bone
- Gross periodontal bone loss when assessable
- Condyles when adequately visible
- Maxillary structures
- Mandibular structures
- Other obvious abnormalities

Be cautious about panoramic distortion and superimposition.
"""

                elif radiograph_type == "Bitewing":

                    radiograph_instructions = """
The selected radiograph is Bitewing.

Assess only visible findings such as:

- Interproximal caries
- Occlusal caries when clearly visible
- Alveolar crest
- Existing restorations
- Obvious calculus when visible
- Other clearly visible findings

Do not label subtle changes as caries without evidence.
"""

                elif radiograph_type == "Occlusal":

                    radiograph_instructions = """
The selected radiograph is Occlusal.

Assess only visible:

- Teeth
- Unerupted/developing teeth
- Jaw structures
- Gross bony abnormalities
- Obvious radiolucencies
- Obvious radiopacities
- Other clearly visible abnormalities
"""

                elif radiograph_type == "Facial radiograph":

                    radiograph_instructions = """
The selected radiograph is a facial radiograph.

Assess only structures that are actually visible.

Do not provide definitive orthodontic,
skeletal, maxillofacial, or medical diagnosis.
"""

                else:

                    radiograph_instructions = """
The radiograph type may not be reliably classifiable.

First determine whether the uploaded image is actually
a dental radiograph.

If the type cannot be confidently determined,
state:

"Radiograph type cannot be reliably classified."

Then describe only clearly visible findings.
"""

                # ====================================================
                # FINAL AI PROMPT
                # ====================================================

                final_prompt = f"""
{safety_rules}

{radiograph_instructions}

Selected radiograph type:
{radiograph_type}

Analyze the actual uploaded image.

The image is the source of truth.

Do not use patient name, OP number, age, sex,
or assumptions to create radiographic findings.

If something cannot be determined from the image,
write "Not clearly assessable."

Return the report using this structure:

# AMRs Dental X-ray AI

## Provisional Radiographic Assessment

### 1. Image Quality

State:
- Adequate / Limited / Poor
- Reason

### 2. Radiograph Type

State whether the selected type appears compatible
with the actual image.

If uncertain, say so.

### 3. Visible Structures

Describe only structures actually visible.

### 4. Teeth / Dentition

Describe visible dental findings.

Use FDI tooth number ONLY when reliably identifiable.

If not reliably identifiable, do not give a number.

### 5. Radiographic Findings

For each actual finding provide:

- Finding:
- Location:
- Confidence: High / Moderate / Low
- Evidence visible on image:

If there are no definite abnormal findings AND
the image is adequately assessable, state:

"No definite abnormal radiographic finding is identified
from the uploaded image."

If the image is inadequate, do not use that statement.

### 6. Possible Findings

Only include findings supported by actual visual evidence.

For uncertain findings write:

"Possible — requires professional correlation."

### 7. Areas Not Reliably Assessable

List areas that cannot be evaluated because of:

- Image quality
- Positioning
- Cropping
- Superimposition
- Other limitations

### 8. Provisional Impression

Give a short conservative summary based ONLY on the image.

### 9. Suggested Professional Review

Mention what should be reviewed by the dentist/radiologist
when appropriate.

Do not provide definitive diagnosis.

Do not provide definitive treatment.

FINAL STATEMENT:

"This is an AI-assisted provisional radiographic
assessment and not a definitive diagnosis. Final
interpretation, diagnosis and treatment decisions must
be made by a qualified dental professional."
"""

                # ====================================================
                # SEND IMAGE TO GEMINI
                # ====================================================

                with st.spinner(
                    "🔬 Analyzing the uploaded radiograph..."
                ):

                    image_part = types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    )

                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[
                            image_part,
                            final_prompt
                        ]
                    )

                # ====================================================
                # RESPONSE
                # ====================================================

                result_text = getattr(
                    response,
                    "text",
                    None
                )

                if result_text:

                    st.session_state.analysis_count += 1

                    st.success(
                        "✅ AI assessment completed."
                    )

                    st.markdown(
                        '<div class="section">'
                        '📋 Assessment Report'
                        '</div>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        result_text
                    )

                    # =================================================
                    # EXAMINATION INFORMATION
                    # =================================================

                    st.markdown(
                        '<div class="section">'
                        '📄 Examination Information'
                        '</div>',
                        unsafe_allow_html=True
                    )

                    st.write(
                        f"**Radiograph:** {radiograph_type}"
                    )

                    st.write(
                        f"**Examination Date:** "
                        f"{examination_date}"
                    )

                    if age > 0:
                        st.write(
                            f"**Age:** {age}"
                        )

                    if sex != "Select":
                        st.write(
                            f"**Sex:** {sex}"
                        )

                else:

                    st.warning(
                        "⚠️ The AI returned no readable assessment."
                    )

                    st.info(
                        "Please try again with a clearer "
                        "radiograph."
                    )

            # ========================================================
            # ERROR HANDLING
            # ========================================================

            except KeyError:

                st.error(
                    "❌ GEMINI_API_KEY was not found."
                )

                st.info(
                    "Check Streamlit Secrets and make sure "
                    "GEMINI_API_KEY is configured."
                )

            except Exception as e:

                st.error(
                    "❌ AI analysis failed."
                )

                with st.expander(
                    "Technical error details"
                ):

                    st.code(
                        str(e)
                    )

# ============================================================
# DISCLAIMER
# ============================================================

st.markdown(
    """
    <div class="disclaimer">

    <b>⚠️ Important Medical Disclaimer</b><br><br>

    AMRs Dental X-ray AI provides an AI-assisted
    provisional radiographic assessment for
    decision support only.

    It does not replace clinical examination,
    professional radiographic interpretation,
    definitive diagnosis, or treatment planning.

    The AI may make mistakes or may be unable to
    reliably assess an image.

    Final diagnosis and treatment decisions must
    always be made by a qualified dental professional.

    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div style="
        text-align:center;
        margin-top:20px;
        margin-bottom:10px;
        color:#888;
        font-size:12px;
    ">
    AMRs Dental X-ray AI
    </div>
    """,
    unsafe_allow_html=True
)
