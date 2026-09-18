import os
import json
import re
from datetime import date, datetime
from io import BytesIO

import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# DENTAL BUDDY
# AI-Powered Dental Learning & Clinical Decision-Support
# ============================================================

st.set_page_config(
    page_title="Dental Buddy",
    page_icon="🦷",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.6-flash"

# ------------------------------------------------------------
# THEME / GLOBAL CSS
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .hero-title {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        letter-spacing: -1px;
    }

    .hero-subtitle {
        text-align: center;
        font-size: 1.05rem;
        opacity: 0.82;
        margin-bottom: 1.8rem;
    }

    .mode-card {
        padding: 1.25rem 1.25rem 0.9rem 1.25rem;
        border-radius: 22px;
        border: 1px solid rgba(80, 200, 200, 0.45);
        background: rgba(30, 150, 160, 0.08);
        margin-bottom: 0.7rem;
    }

    .mode-card.doctor {
        border-color: rgba(100, 190, 110, 0.55);
        background: rgba(100, 190, 110, 0.08);
    }

    .small-muted {
        opacity: 0.72;
        font-size: 0.9rem;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 750;
        margin-top: 1.1rem;
        margin-bottom: 0.55rem;
    }

    .report-box {
        padding: 1rem;
        border-radius: 15px;
        border: 1px solid rgba(128, 128, 128, 0.35);
        background: rgba(128, 128, 128, 0.07);
    }

    .safety-box {
        padding: 1rem;
        border-radius: 15px;
        border-left: 5px solid #16a6a6;
        background: rgba(22, 166, 166, 0.08);
    }

    div.stButton > button {
        border-radius: 12px;
        min-height: 2.7rem;
        font-weight: 650;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
if "mode" not in st.session_state:
    st.session_state.mode = None

if "analysis_date" not in st.session_state:
    st.session_state.analysis_date = str(date.today())

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if st.session_state.analysis_date != str(date.today()):
    st.session_state.analysis_date = str(date.today())
    st.session_state.analysis_count = 0

if "last_report" not in st.session_state:
    st.session_state.last_report = ""

if "last_image_name" not in st.session_state:
    st.session_state.last_image_name = ""

# ------------------------------------------------------------
# GEMINI CLIENT
# ------------------------------------------------------------
def get_api_key():
    """Read Gemini API key from Streamlit secrets or environment."""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""

    if not key:
        key = os.getenv("GEMINI_API_KEY", "")

    return key.strip()


def get_client():
    api_key = get_api_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def image_to_part(uploaded_file):
    """Convert Streamlit upload to a Gemini image Part."""
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/png"

    return types.Part.from_bytes(
        data=data,
        mime_type=mime,
    )


def run_image_analysis(uploaded_file, prompt):
    client = get_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key not found. Add GEMINI_API_KEY to Streamlit Secrets."
        )

    image_part = image_to_part(uploaded_file)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, image_part],
    )

    text = getattr(response, "text", None)

    if not text:
        raise RuntimeError("The AI returned an empty response.")

    return text


def run_text_ai(prompt):
    client = get_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key not found. Add GEMINI_API_KEY to Streamlit Secrets."
        )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    text = getattr(response, "text", None)

    if not text:
        raise RuntimeError("The AI returned an empty response.")

    return text


# ------------------------------------------------------------
# SAFETY RULES
# ------------------------------------------------------------
COMMON_SAFETY_RULES = """
You are Dental Buddy, an AI-assisted dental learning and clinical
decision-support system.

CORE SAFETY PRINCIPLE:
Do good for the patient and never cause harm.

For radiographic analysis:
1. Analyze ONLY the uploaded radiograph.
2. Do not invent teeth, lesions, measurements, fractures, pathology,
   restorations, or other findings that are not visible.
3. If something cannot be assessed reliably, say "Unclear / not assessable".
4. Do not guess an FDI tooth number when the image does not support it.
5. Distinguish visible radiographic findings from interpretation.
6. Do not present an AI impression as a definitive clinical diagnosis.
7. Mention image-quality limitations when relevant.
8. Recommend clinical correlation and appropriate professional assessment.
9. Do not prescribe a specific drug dose or definitive treatment from
   an image alone.
10. Be concise but clinically useful.
"""

# ------------------------------------------------------------
# RADIOGRAPH PROMPTS
# ------------------------------------------------------------
RADIOGRAPH_PROMPTS = {
    "IOPA": COMMON_SAFETY_RULES
    + """
Analyze the uploaded IOPA radiograph.

Report:
A. IMAGE QUALITY
- Adequate / Limited / Poor
- Brief reason

B. RADIOGRAPHIC FINDINGS
- Teeth/regions that are actually visible
- Caries only if radiographically visible
- Existing restorations if visible
- Periapical changes if visible
- Periodontal bone-level changes if visible
- Other clearly visible abnormalities

C. TOOTH IDENTIFICATION
- Use FDI numbering only when supported by the image.
- If uncertain, state that the exact tooth number is unclear.

D. PROVISIONAL RADIOGRAPHIC IMPRESSION
- Describe what the image suggests.
- Use "suggestive of" or "consistent with" rather than a definitive
  diagnosis when appropriate.

E. NEXT CLINICAL STEP
- Suggest a broad next step such as clinical examination,
  vitality testing, periodontal evaluation, or additional imaging
  when justified.

F. UNCERTAINTY
- Explicitly list important limitations or doubtful findings.
""",

    "OPG": COMMON_SAFETY_RULES
    + """
Analyze the uploaded panoramic radiograph (OPG).

Assess only what is visible:
- Image quality and positioning limitations
- Dentition and missing teeth when clearly visible
- Gross caries/restorations when visible
- Periodontal bone-level changes
- Periapical regions when adequately visualized
- Impacted/unerupted teeth
- Jaw lesions or radiolucencies/radiopacities
- Condyles and mandibular regions when visible
- Maxillary sinus regions when visible
- Other obvious radiographic findings

Use FDI numbering only when supported.
Do not invent measurements or pathology.
Provide a provisional radiographic impression, uncertainty,
and suggested clinical correlation.
""",

    "Bitewing": COMMON_SAFETY_RULES
    + """
Analyze the uploaded bitewing radiograph.

Focus on:
- Interproximal caries that are actually visible
- Occlusal caries only when visible
- Existing restorations
- Alveolar crest / periodontal bone levels
- Calculus if clearly visible
- Other obvious findings

Identify the tooth/region only when supported.
Do not infer a lesion merely because a tooth is present.
State image limitations and uncertainty.
""",

    "Occlusal": COMMON_SAFETY_RULES
    + """
Analyze the uploaded occlusal radiograph.

Assess visible:
- Teeth and eruption/development
- Impacted or supernumerary teeth
- Radiolucent/radiopaque lesions
- Cortical expansion or displacement if visible
- Foreign bodies or calcifications if clearly visible
- Other obvious abnormalities

Do not infer findings outside the visible field.
Give a provisional radiographic impression and uncertainty.
""",

    "Facial Radiograph": COMMON_SAFETY_RULES
    + """
Analyze the uploaded facial radiograph.

Assess only clearly visible:
- Facial skeletal alignment
- Obvious fractures or discontinuity
- Gross asymmetry
- Jaw/maxillofacial radiographic abnormalities
- Other visible findings

Do not diagnose a fracture if the image quality or projection is
insufficient. Clearly state when additional imaging such as CT/CBCT
may be needed for clinical evaluation, without prescribing a specific
test unless justified by the visible limitation.
""",
}

# ------------------------------------------------------------
# CEPH PROTOCOLS
# ------------------------------------------------------------
CEPH_ANALYSES = [
    "Steiner",
    "Downs",
    "McNamara",
    "Tweed",
    "Wits Appraisal",
    "Jarabak",
    "Soft Tissue",
    "Combined / All Analyses",
]

CEPH_PROMPT = COMMON_SAFETY_RULES + """
Analyze the uploaded lateral cephalogram for orthodontic learning /
clinical decision support.

Selected analysis: {analysis}

Important:
- Do NOT fabricate landmarks or numerical measurements.
- If a landmark is not clearly visible, mark it as uncertain.
- Measurements may be estimated only when the image genuinely permits
  a reasonable radiographic estimate; clearly label estimates.
- Explain that cephalometric analysis is dependent on image quality,
  landmark identification, tracing method, magnification and clinical
  context.

For the selected analysis provide:
1. Image quality
2. Relevant landmarks/measurements that can actually be assessed
3. Interpretation of the available measurements
4. Important limitations
5. Educational clinical significance
6. Statement that final orthodontic diagnosis/planning requires
   professional assessment and complete clinical records.
"""

# ------------------------------------------------------------
# SOFT TISSUE LESION WORKFLOW
# ------------------------------------------------------------
LESION_OPTIONS = [
    "White lesion",
    "Red lesion",
    "Red-white lesion",
    "Ulcer",
    "Pigmented lesion",
    "Swelling / mass",
    "Vesicle / blister",
    "Other / unclear",
]

LESION_QUESTIONS = [
    "Is the lesion scrapable?",
    "Does it bleed on gentle manipulation?",
    "Is it painful?",
    "Is there ulceration?",
    "Is there induration?",
    "Is there exudation?",
    "Is there a history of trauma or irritation?",
    "How long has it been present?",
    "Is it increasing, decreasing, or unchanged?",
    "Is there cervical lymphadenopathy?",
]

# ------------------------------------------------------------
# HOME SCREEN
# ------------------------------------------------------------
def show_home():
    st.markdown('<div class="hero-title">🦷 Dental Buddy</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">AI-Powered Dental Learning & Clinical Decision-Support Platform</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="mode-card">
        <h3>🎓 Student Mode</h3>
        <p>Learn dental topics, exams, previous-year questions, clinical reasoning,
        adaptive quizzes, essay generation and treatment-planning concepts.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🎓 Enter Student Mode", use_container_width=True):
        st.session_state.mode = "student"
        st.rerun()

    st.markdown(
        """
        <div class="mode-card doctor">
        <h3>🩺 Doctor Mode</h3>
        <p>Radiographic AI workflow, soft-tissue reasoning, cephalometric analysis,
        clinical decision support and structured case reasoning.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🩺 Enter Doctor Mode", use_container_width=True):
        st.session_state.mode = "doctor"
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div class="safety-box">
        <b>🛡️ Safety principle</b><br>
        Dental Buddy provides AI-assisted information and provisional
        radiographic assessment. It does not replace a qualified dental
        professional or definitive clinical diagnosis.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# HEADER / BACK BUTTON
# ------------------------------------------------------------
def show_mode_header(title, icon):
    left, right = st.columns([1, 5])

    with left:
        if st.button("← Home", use_container_width=True):
            st.session_state.mode = None
            st.rerun()

    with right:
        st.markdown(f"## {icon} {title}")


# ------------------------------------------------------------
# USAGE LIMIT
# ------------------------------------------------------------
def can_analyze():
    return st.session_state.analysis_count < DAILY_ANALYSIS_LIMIT


def record_analysis():
    st.session_state.analysis_count += 1


def show_usage():
    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    st.caption(
        f"AI analyses remaining today: {remaining}/{DAILY_ANALYSIS_LIMIT}"
    )


# ------------------------------------------------------------
# RADIOGRAPH ANALYSIS UI
# ------------------------------------------------------------
def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")

    show_usage()

    radiograph_type = st.selectbox(
        "Select radiograph type",
        [
            "IOPA",
            "OPG",
            "Bitewing",
            "Occlusal",
            "Facial Radiograph",
            "Lateral Cephalogram (Ceph)",
        ],
    )

    ceph_analysis = None

    if radiograph_type == "Lateral Cephalogram (Ceph)":
        ceph_analysis = st.selectbox(
            "Select cephalometric analysis",
            CEPH_ANALYSES,
        )

    st.markdown("#### Case information")

    col1, col2 = st.columns(2)

    with col1:
        patient_id = st.text_input(
            "Patient / Case ID",
            placeholder="Optional",
        )

    with col2:
        age = st.text_input(
            "Age",
            placeholder="Optional",
        )

    uploaded = st.file_uploader(
        "Upload dental radiograph",
        type=["png", "jpg", "jpeg", "webp"],
        help="Upload a clear radiograph for AI-assisted assessment.",
    )

    if uploaded:
        st.image(
            uploaded,
            caption="Uploaded radiograph",
            use_container_width=True,
        )

    if radiograph_type == "Lateral Cephalogram (Ceph)":
        prompt = CEPH_PROMPT.format(analysis=ceph_analysis)
    else:
        prompt = RADIOGRAPH_PROMPTS[radiograph_type]

    if st.button(
        "🔍 Analyze X-ray",
        type="primary",
        use_container_width=True,
        disabled=not can_analyze(),
    ):
        if uploaded is None:
            st.warning("Please upload a radiograph first.")
            return

        with st.spinner("Analyzing radiograph..."):
            try:
                report = run_image_analysis(uploaded, prompt)

                record_analysis()

                st.session_state.last_report = report
                st.session_state.last_image_name = uploaded.name

                st.success("Analysis completed.")
                st.markdown("### 📋 AI Radiographic Assessment")
                st.markdown(report)

                st.markdown("---")
                st.markdown(
                    """
                    **Important:** This is an AI-assisted radiographic
                    assessment. Correlate with clinical examination,
                    history and appropriate investigations. Do not use
                    the AI output alone to make a definitive diagnosis
                    or treatment decision.
                    """
                )

            except Exception as exc:
                st.error("AI analysis failed.")
                st.code(str(exc))


# ------------------------------------------------------------
# SOFT-TISSUE REASONING
# ------------------------------------------------------------
def soft_tissue_workflow():
    st.markdown("### 👄 Soft-Tissue Lesion Reasoning")

    lesion = st.selectbox(
        "Primary lesion appearance",
        LESION_OPTIONS,
    )

    st.write("Answer the clinical questions that are available.")

    answers = {}

    for question in LESION_QUESTIONS:
        answers[question] = st.radio(
            question,
            ["Yes", "No", "Unknown"],
            horizontal=True,
            key=f"lesion_{question}",
        )

    duration = st.text_input(
        "Duration / history",
        placeholder="Example: 2 weeks, recurrent, unknown",
    )

    additional = st.text_area(
        "Additional clinical information",
        placeholder="Site, size, patient symptoms, habits, trauma, etc.",
    )

    if st.button(
        "🧠 Generate Differential Reasoning",
        type="primary",
        use_container_width=True,
    ):
        prompt = f"""
You are Dental Buddy helping with structured oral medicine learning
and clinical decision support.

Lesion type: {lesion}

Clinical answers:
{json.dumps(answers, indent=2)}

Duration/history:
{duration}

Additional information:
{additional}

Provide:
1. Key observed/entered clinical features
2. Differential diagnostic categories, not a definitive diagnosis
3. Supporting evidence for each category
4. Contradictory evidence
5. Unknown / missing evidence
6. One highest-value next clinical question that would most help
   discriminate between the important possibilities
7. Suggested broad next clinical step
8. Red flags that warrant prompt professional assessment

Do not invent patient findings.
Do not provide a definitive diagnosis from incomplete information.
"""
        try:
            with st.spinner("Building clinical reasoning..."):
                result = run_text_ai(prompt)

            st.markdown("### 🧾 Clinical Reasoning")
            st.markdown(result)

        except Exception as exc:
            st.error("Clinical reasoning failed.")
            st.code(str(exc))


# ------------------------------------------------------------
# ADAPTIVE NEXT-BEST QUESTION
# ------------------------------------------------------------
def information_gain_workflow():
    st.markdown("### 🧠 Diagnostic Information-Gain Engine")

    st.caption(
        "The engine identifies the most useful unanswered clinical feature "
        "instead of asking many low-value questions at once."
    )

    case = st.text_area(
        "Enter the case / current findings",
        height=150,
        placeholder="Describe symptoms, site, examination findings and available investigations.",
    )

    known = st.text_area(
        "Known evidence",
        height=120,
        placeholder="Positive findings, negative findings and investigations already available.",
    )

    differentials = st.text_area(
        "Initial differential possibilities",
        height=120,
        placeholder="Enter possible diagnoses/categories separated by commas.",
    )

    if st.button(
        "🎯 Find Next-Best Clinical Question",
        type="primary",
        use_container_width=True,
    ):
        if not case.strip():
            st.warning("Enter the case first.")
            return

        prompt = f"""
You are the adaptive reasoning engine of Dental Buddy.

CASE:
{case}

KNOWN EVIDENCE:
{known}

INITIAL DIFFERENTIAL:
{differentials}

Construct an Evidence Ledger with:
- Supporting evidence
- Opposing evidence
- Unknown evidence

Then detect contradictions or important gaps.

Choose ONE next clinical question with the highest expected
discriminatory / information value.

Output:
1. Evidence Ledger
2. Important contradiction or gap
3. NEXT-BEST CLINICAL QUESTION
4. Why this question has high information value
5. How possible answers would change the differential

Do not invent facts and do not give a definitive diagnosis.
"""
        try:
            with st.spinner("Calculating the next-best question..."):
                result = run_text_ai(prompt)

            st.markdown("### 📒 Evidence Ledger & Next Question")
            st.markdown(result)

        except Exception as exc:
            st.error("Reasoning engine failed.")
            st.code(str(exc))


# ------------------------------------------------------------
# STUDENT MODE
# ------------------------------------------------------------
def student_mode():
    show_mode_header("Student Mode", "🎓")

    tabs = st.tabs(
        [
            "📚 Learn",
            "📝 Exam / PYQ",
            "🧠 Quiz",
            "🩺 Clinical Case",
            "✍️ Essay",
        ]
    )

    # ---------------- LEARN ----------------
    with tabs[0]:
        st.markdown("### 📚 Dental Topic Tutor")

        topic = st.text_input(
            "Topic",
            placeholder="Example: CPITN, deep bite, OPG, oral ulcer",
        )

        level = st.selectbox(
            "Level",
            [
                "Quick revision",
                "University exam",
                "Final-year BDS",
                "Clinical reasoning",
            ],
        )

        if st.button(
            "📖 Teach Me",
            type="primary",
            use_container_width=True,
        ):
            if not topic.strip():
                st.warning("Enter a topic.")
            else:
                prompt = f"""
Teach the dental topic "{topic}" at the level "{level}".

Use a clear exam-friendly structure:
- Definition
- Classification
- Etiology / causes
- Clinical features
- Investigations
- Diagnosis / differential where relevant
- Management principles
- Important exam points
- Viva questions

Avoid unsupported claims.
If textbook-specific wording is requested, clearly distinguish
general knowledge from textbook quotations.
"""
                try:
                    with st.spinner("Preparing study notes..."):
                        result = run_text_ai(prompt)
                    st.markdown(result)
                except Exception as exc:
                    st.error("Tutor failed.")
                    st.code(str(exc))

    # ---------------- EXAM ----------------
    with tabs[1]:
        st.markdown("### 📝 Exam & Previous-Year Question Helper")

        subject = st.text_input(
            "Subject",
            placeholder="Example: Public Health Dentistry",
            key="pyq_subject",
        )

        question = st.text_area(
            "Question",
            placeholder="Paste a previous-year question here.",
            key="pyq_question",
        )

        marks = st.selectbox(
            "Marks",
            ["2 marks", "5 marks", "10 marks", "Long essay"],
            key="pyq_marks",
        )

        if st.button(
            "✍️ Generate Exam Answer",
            type="primary",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning("Paste a question first.")
            else:
                prompt = f"""
Create an exam-oriented answer for this dental question.

Subject: {subject}
Marks: {marks}
Question: {question}

Use headings, bullet points, classifications and important details.
Keep the answer appropriate for a BDS university examination.
Do not fabricate citations or textbook page numbers.
"""
                try:
                    with st.spinner("Generating answer..."):
                        result = run_text_ai(prompt)
                    st.markdown(result)
                except Exception as exc:
                    st.error("Answer generation failed.")
                    st.code(str(exc))

    # ---------------- QUIZ ----------------
    with tabs[2]:
        st.markdown("### 🧠 Adaptive Quiz")

        quiz_topic = st.text_input(
            "Quiz topic",
            placeholder="Example: Oral radiology",
        )

        count = st.slider(
            "Number of questions",
            3,
            10,
            5,
        )

        if st.button(
            "🎯 Generate Quiz",
            type="primary",
            use_container_width=True,
        ):
            if not quiz_topic.strip():
                st.warning("Enter a topic.")
            else:
                prompt = f"""
Create {count} BDS-level multiple-choice questions on:
{quiz_topic}

For each:
- Question
- Four options
- Correct answer
- Brief explanation
- One common mistake

Make questions clinically relevant and factually careful.
"""
                try:
                    with st.spinner("Creating quiz..."):
                        result = run_text_ai(prompt)
                    st.markdown(result)
                except Exception as exc:
                    st.error("Quiz generation failed.")
                    st.code(str(exc))

    # ---------------- CLINICAL CASE ----------------
    with tabs[3]:
        st.markdown("### 🩺 Clinical Reasoning Case")

        case_topic = st.text_input(
            "Case topic",
            placeholder="Example: periapical lesion",
        )

        if st.button(
            "🧩 Generate Case",
            type="primary",
            use_container_width=True,
        ):
            if not case_topic.strip():
                st.warning("Enter a case topic.")
            else:
                prompt = f"""
Create a BDS-level dental clinical reasoning case on {case_topic}.

Give:
1. Case presentation
2. History
3. Examination findings
4. Investigation findings
5. Questions for the student
6. Differential diagnosis
7. Reasoning explanation
8. Broad management principles

Do not make the case unnecessarily ambiguous.
"""
                try:
                    with st.spinner("Building case..."):
                        result = run_text_ai(prompt)
                    st.markdown(result)
                except Exception as exc:
                    st.error("Case generation failed.")
                    st.code(str(exc))

    # ---------------- ESSAY ----------------
    with tabs[4]:
        st.markdown("### ✍️ Essay Generator")

        essay_topic = st.text_input(
            "Essay topic",
            placeholder="Example: Epidemiology of dental caries",
        )

        style = st.selectbox(
            "Answer style",
            [
                "10-mark university answer",
                "Short note",
                "Revision notes",
                "Viva answer",
            ],
        )

        if st.button(
            "📝 Generate",
            type="primary",
            use_container_width=True,
        ):
            if not essay_topic.strip():
                st.warning("Enter a topic.")
            else:
                prompt = f"""
Generate a {style} for the BDS topic:
{essay_topic}

Use clear headings and clinically/exam relevant points.
Do not invent references.
"""
                try:
                    with st.spinner("Writing..."):
                        result = run_text_ai(prompt)
                    st.markdown(result)
                except Exception as exc:
                    st.error("Essay generation failed.")
                    st.code(str(exc))


# ------------------------------------------------------------
# DOCTOR MODE
# ------------------------------------------------------------
def doctor_mode():
    show_mode_header("Doctor Mode", "🩺")

    tabs = st.tabs(
        [
            "🩻 X-ray AI",
            "👄 Soft Tissue",
            "🧠 Next-Best Question",
            "📋 Case Reasoning",
        ]
    )

    with tabs[0]:
        radiograph_analyzer()

    with tabs[1]:
        soft_tissue_workflow()

    with tabs[2]:
        information_gain_workflow()

    with tabs[3]:
        st.markdown("### 📋 Structured Clinical Case")

        case_text = st.text_area(
            "Enter clinical case",
            height=220,
            placeholder=(
                "History, symptoms, clinical findings, radiographic findings, "
                "investigations and relevant negatives."
            ),
        )

        if st.button(
            "🔎 Analyze Case Structure",
            type="primary",
            use_container_width=True,
        ):
            if not case_text.strip():
                st.warning("Enter a case.")
                return

            prompt = f"""
Analyze this dental case using a structured evidence framework.

CASE:
{case_text}

Return:
1. Problem representation
2. Key positive findings
3. Key negative findings
4. Differential categories
5. Supporting evidence
6. Contradictory evidence
7. Unknown evidence
8. Important missing clinical information
9. One next-best question
10. Suggested broad next clinical step

Do not invent findings.
Do not provide a definitive diagnosis from incomplete information.
"""
            try:
                with st.spinner("Structuring case..."):
                    result = run_text_ai(prompt)
                st.markdown(result)
            except Exception as exc:
                st.error("Case analysis failed.")
                st.code(str(exc))


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.markdown("## 🦷 Dental Buddy")

        if st.session_state.mode:
            st.write(f"Current mode: **{st.session_state.mode.title()}**")

        st.markdown("---")
        st.markdown("### AI Safety")
        st.caption(
            "Radiographic analysis is limited to the uploaded image. "
            "Unclear findings should remain uncertain."
        )

        st.markdown("---")
        st.markdown("### Daily AI usage")
        st.write(
            f"{st.session_state.analysis_count}/"
            f"{DAILY_ANALYSIS_LIMIT} radiographic analyses used"
        )

        if st.button("🏠 Return Home", use_container_width=True):
            st.session_state.mode = None
            st.rerun()


# ------------------------------------------------------------
# APP
# ------------------------------------------------------------
sidebar()

if st.session_state.mode is None:
    show_home()
elif st.session_state.mode == "student":
    student_mode()
elif st.session_state.mode == "doctor":
    doctor_mode()
else:
    st.session_state.mode = None
    st.rerun()
