import os
import json
import re
import sqlite3
from datetime import date, datetime
from io import BytesIO
import base64
import html

import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# POCKET DENTISTRY V2
# Phase 1:
# Evidence Ledger + Diagnostic Information Gain +
# Next-Best Clinical Question
# ============================================================

st.set_page_config(
    page_title="Pocket Dentistry V2",
    page_icon="🦷",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DB_FILE = "pocket_dentistry.db"


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 920px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero-title {
        text-align:center;
        font-size:2.7rem;
        font-weight:900;
        background:linear-gradient(90deg,#1e3d59,#17b978,#008891);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
    }
    .hero-subtitle {
        text-align:center;
        color:#008891;
        font-weight:600;
        margin-bottom:1.5rem;
    }
    .reason-card {
        padding:1rem;
        border-radius:15px;
        border:1px solid #d0d7de;
        background:#f8fafb;
        margin:.5rem 0;
    }
    .ledger-support {
        border-left:5px solid #17b978;
        padding:.7rem 1rem;
        background:#eefaf5;
        border-radius:10px;
        margin:.4rem 0;
    }
    .ledger-against {
        border-left:5px solid #e67e22;
        padding:.7rem 1rem;
        background:#fff7ed;
        border-radius:10px;
        margin:.4rem 0;
    }
    .ledger-unknown {
        border-left:5px solid #7f8c8d;
        padding:.7rem 1rem;
        background:#f4f6f7;
        border-radius:10px;
        margin:.4rem 0;
    }
    .question-box {
        padding:1.2rem;
        border-radius:18px;
        border:2px solid #008891;
        background:#e8fbfc;
        margin:1rem 0;
    }
    div.stButton > button {
        border-radius:12px;
        min-height:2.7rem;
        font-weight:700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

def db_connect():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            patient_email TEXT,
            patient_name TEXT,
            case_type TEXT,
            image_name TEXT,
            report_title TEXT,
            report TEXT
        )
    """)
    conn.commit()
    return conn


def save_case(patient_email, patient_name, case_type, image_name, title, report):
    conn = db_connect()
    conn.execute(
        """INSERT INTO cases
        (created_at,patient_email,patient_name,case_type,image_name,report_title,report)
        VALUES(?,?,?,?,?,?,?)""",
        (
            str(datetime.now()),
            patient_email,
            patient_name,
            case_type,
            image_name,
            title,
            report,
        ),
    )
    conn.commit()
    conn.close()


def get_cases(patient_email=""):
    conn = db_connect()
    if patient_email.strip():
        rows = conn.execute(
            """SELECT id,created_at,patient_email,patient_name,case_type,
               image_name,report_title,report
               FROM cases WHERE patient_email=? ORDER BY id DESC""",
            (patient_email.strip(),),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id,created_at,patient_email,patient_name,case_type,
               image_name,report_title,report
               FROM cases ORDER BY id DESC LIMIT 50"""
        ).fetchall()
    conn.close()
    return rows


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "mode": None,
    "page": "home",
    "analysis_date": str(date.today()),
    "analysis_count": 0,
    "last_reasoning": "",
    "reasoning_case": {},
    "reasoning_history": [],
    "reasoning_question": "",
    "reasoning_differentials": [],
    "reasoning_complete": False,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.analysis_date != str(date.today()):
    st.session_state.analysis_date = str(date.today())
    st.session_state.analysis_count = 0


# ============================================================
# GEMINI
# ============================================================

def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""
    return str(key or os.getenv("GEMINI_API_KEY", "")).strip()


def get_client():
    key = get_api_key()
    if not key:
        return None
    return genai.Client(api_key=key)


def friendly_ai_error(exc):
    text = str(exc).upper()
    if "401" in text or "UNAUTHENTICATED" in text:
        return "🔐 Gemini authentication failed. Check GEMINI_API_KEY."
    if "403" in text or "PERMISSION_DENIED" in text:
        return "🚫 Gemini API permission denied."
    if "404" in text or "NOT_FOUND" in text:
        return f"🔎 Model `{MODEL_NAME}` was not found or is unavailable."
    if "429" in text or "QUOTA" in text or "RESOURCE_EXHAUSTED" in text:
        return "⏳ Gemini quota/rate limit reached."
    if "503" in text or "UNAVAILABLE" in text:
        return "🔄 Gemini is temporarily unavailable."
    return "⚠️ AI service error. Please try again."


def run_text_ai(prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is missing.")
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("AI returned an empty response.")
    return text


def run_image_ai(uploaded_file, prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    part = types.Part.from_bytes(
        data=uploaded_file.getvalue(),
        mime_type=uploaded_file.type or "image/png",
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, part],
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("AI returned an empty response.")
    return text


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):
    if not text:
        return None

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    return None


# ============================================================
# CLINICAL REASONING ENGINE
# ============================================================

REASONING_SAFETY = """
You are an AI-assisted dental clinical decision-support system.

SAFETY:
- Do not claim certainty when evidence is incomplete.
- Do not invent patient findings.
- Separate observed/provided information from inference.
- A differential diagnosis is a possibility list, not a definitive diagnosis.
- If an important feature is unknown, mark it UNKNOWN.
- Do not recommend a specific irreversible treatment solely from AI output.
- Highlight urgent red flags when appropriate.
- Ask ONE highest-value next clinical question at a time.
"""


def reasoning_prompt(case):
    return f"""
{REASONING_SAFETY}

Build a structured clinical reasoning state for this dental/oral case.

CASE TYPE:
{case.get("case_type", "")}

PATIENT/CASE:
{case.get("patient_identifier", "")}

SITE:
{case.get("site", "")}

DURATION:
{case.get("duration", "")}

PRIMARY APPEARANCE:
{case.get("appearance", "")}

PAIN:
{case.get("pain", "")}

SCRAPABILITY:
{case.get("scrapability", "")}

BLEEDING:
{case.get("bleeding", "")}

ADDITIONAL HISTORY:
{case.get("history", "")}

IMAGE INFORMATION:
{case.get("image_summary", "No image supplied.")}

Return ONLY valid JSON in this schema:

{{
  "problem_representation": "short clinical summary",
  "differentials": [
    {{
      "name": "possibility",
      "supporting_evidence": ["..."],
      "opposing_evidence": ["..."],
      "unknown_evidence": ["..."],
      "status": "consider"
    }}
  ],
  "global_unknowns": ["..."],
  "red_flags": ["..."],
  "next_best_question": {{
      "question": "ONE question only",
      "why_it_matters": "why this question separates possibilities",
      "answer_options": ["option 1", "option 2", "option 3"]
  }},
  "suggested_next_step": "appropriate non-irreversible clinical next step",
  "uncertainty": "brief uncertainty statement"
}}

The next_best_question must target a missing feature with high discriminatory value.
Do not ask multiple questions in one question.
"""


def update_reasoning_prompt(case, previous_state, answer):
    return f"""
{REASONING_SAFETY}

You are updating an existing clinical reasoning state after receiving ONE new answer.

CASE:
{json.dumps(case, ensure_ascii=False)}

PREVIOUS REASONING:
{json.dumps(previous_state, ensure_ascii=False)}

NEW ANSWER:
{answer}

Re-evaluate the differential using the new information.

Return ONLY valid JSON:

{{
  "problem_representation": "updated summary",
  "differentials": [
    {{
      "name": "possibility",
      "supporting_evidence": ["..."],
      "opposing_evidence": ["..."],
      "unknown_evidence": ["..."],
      "status": "consider"
    }}
  ],
  "global_unknowns": ["..."],
  "red_flags": ["..."],
  "next_best_question": {{
      "question": "ONE highest-value unanswered question, or empty string if enough information is available",
      "why_it_matters": "reason",
      "answer_options": ["option 1", "option 2", "option 3"]
  }},
  "suggested_next_step": "next appropriate clinical step",
  "uncertainty": "uncertainty statement",
  "reasoning_status": "continue OR sufficient_information"
}}
"""


def start_reasoning(case, image=None):
    case = dict(case)

    if image:
        prompt = reasoning_prompt(case) + """
The uploaded image is available.
Use it only for visible findings.
Do not infer hidden clinical facts.
"""
        # We first obtain structured text from image + case.
        raw = run_image_ai(image, prompt)
    else:
        raw = run_text_ai(reasoning_prompt(case))

    parsed = extract_json(raw)
    if not parsed:
        raise RuntimeError("The AI did not return valid structured reasoning JSON.")

    return parsed


def continue_reasoning(case, previous_state, answer):
    raw = run_text_ai(
        update_reasoning_prompt(case, previous_state, answer)
    )
    parsed = extract_json(raw)
    if not parsed:
        raise RuntimeError("The AI did not return valid updated reasoning JSON.")
    return parsed


def reset_reasoning():
    st.session_state.reasoning_case = {}
    st.session_state.reasoning_history = []
    st.session_state.reasoning_question = ""
    st.session_state.reasoning_differentials = []
    st.session_state.reasoning_complete = False
    st.session_state.last_reasoning = ""


# ============================================================
# EVIDENCE LEDGER UI
# ============================================================

def evidence_ledger(state):
    st.markdown("### 📒 Evidence Ledger")

    differentials = state.get("differentials", [])

    if not differentials:
        st.info("No structured differential information returned.")
        return

    for item in differentials:
        name = item.get("name", "Unspecified possibility")
        status = item.get("status", "consider")

        with st.expander(f"🔎 {name} — {status}", expanded=True):
            supporting = item.get("supporting_evidence", [])
            opposing = item.get("opposing_evidence", [])
            unknown = item.get("unknown_evidence", [])

            st.markdown("**🟢 Supporting evidence**")
            if supporting:
                for x in supporting:
                    st.markdown(
                        f'<div class="ledger-support">✓ {html.escape(str(x))}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("None identified.")

            st.markdown("**🟠 Opposing evidence**")
            if opposing:
                for x in opposing:
                    st.markdown(
                        f'<div class="ledger-against">⚠ {html.escape(str(x))}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("None identified.")

            st.markdown("**⚪ Unknown / missing evidence**")
            if unknown:
                for x in unknown:
                    st.markdown(
                        f'<div class="ledger-unknown">? {html.escape(str(x))}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("None identified.")

    unknowns = state.get("global_unknowns", [])
    if unknowns:
        st.markdown("### ❓ Global Unknowns")
        for x in unknowns:
            st.markdown(f"- {x}")


# ============================================================
# NEXT-BEST QUESTION UI
# ============================================================

def next_best_question_ui(state, case):
    q = state.get("next_best_question", {}) or {}
    question = q.get("question", "").strip()

    if not question:
        st.success("✅ The engine considers the current information sufficient for the next clinical step.")
        return

    st.markdown(
        f"""
        <div class="question-box">
        <h3>🎯 Next-Best Clinical Question</h3>
        <p><b>{html.escape(question)}</b></p>
        <p><small>Why it matters: {html.escape(str(q.get("why_it_matters", "")))}</small></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    options = q.get("answer_options", [])
    if options:
        answer = st.radio(
            "Select / provide the answer",
            options + ["Other / not known"],
            key=f"nbq_{len(st.session_state.reasoning_history)}",
        )
    else:
        answer = st.text_input(
            "Answer",
            key=f"nbq_text_{len(st.session_state.reasoning_history)}",
        )

    if answer:
        if st.button(
            "🔄 Update Clinical Reasoning",
            type="primary",
            use_container_width=True,
            key=f"update_reasoning_{len(st.session_state.reasoning_history)}",
        ):
            with st.spinner("Updating evidence and selecting the next information-rich question..."):
                try:
                    new_state = continue_reasoning(
                        case,
                        state,
                        answer,
                    )

                    st.session_state.reasoning_history.append(
                        {
                            "question": question,
                            "answer": answer,
                        }
                    )
                    st.session_state.last_reasoning = json.dumps(
                        new_state,
                        ensure_ascii=False,
                        indent=2,
                    )
                    st.session_state.reasoning_differentials = new_state.get(
                        "differentials", []
                    )
                    st.session_state.reasoning_complete = (
                        new_state.get("reasoning_status") == "sufficient_information"
                    )

                    st.rerun()

                except Exception as exc:
                    st.error(f"❌ Reasoning update failed: {friendly_ai_error(exc)}")


# ============================================================
# CLINICAL REASONING WORKSPACE
# ============================================================

def clinical_reasoning_workspace():
    st.markdown("## 🧠 Adaptive Clinical Reasoning Engine")
    st.caption(
        "Phase 1: Evidence Ledger + Diagnostic Information Gain + Next-Best Clinical Question"
    )

    if st.button("🆕 Start New Case", use_container_width=True):
        reset_reasoning()
        st.rerun()

    st.markdown("---")

    case_type = st.selectbox(
        "Case type",
        [
            "Oral mucosal lesion",
            "Dental pain",
            "Radiographic finding",
            "Swelling / mass",
            "Ulcer",
            "White lesion",
            "Red / red-white lesion",
            "Other dental case",
        ],
    )

    patient_identifier = st.text_input(
        "Case identifier",
        placeholder="Use a case ID rather than unnecessary personal information",
    )

    site = st.text_input(
        "Anatomical site",
        placeholder="e.g. left buccal mucosa",
    )

    appearance = st.text_area(
        "Primary appearance / finding",
        placeholder="Describe what is actually observed.",
    )

    duration = st.text_input(
        "Duration / progression",
        placeholder="e.g. 2 weeks, increasing, intermittent",
    )

    pain = st.selectbox(
        "Pain",
        ["Unknown", "Painless", "Mild discomfort", "Painful", "Burning"],
    )

    scrapability = st.selectbox(
        "Scrapability",
        ["Unknown / not tested", "Scrapable", "Non-scrapable", "Not applicable"],
    )

    bleeding = st.selectbox(
        "Bleeding",
        ["Unknown", "Absent", "Present", "Only on manipulation"],
    )

    history = st.text_area(
        "Additional history / clinical findings",
        placeholder="Relevant history already known. Do not guess missing information.",
    )

    image = st.file_uploader(
        "Optional clinical image",
        type=["png", "jpg", "jpeg", "webp"],
        key="reasoning_image",
    )

    if image:
        st.image(image, caption="Clinical image", use_container_width=True)

    if st.button(
        "🧠 Build Evidence Ledger & Find Next-Best Question",
        type="primary",
        use_container_width=True,
    ):
        if not any([appearance.strip(), image]):
            st.warning("Provide at least an observed finding or an image.")
        else:
            case = {
                "case_type": case_type,
                "patient_identifier": patient_identifier,
                "site": site,
                "appearance": appearance,
                "duration": duration,
                "pain": pain,
                "scrapability": scrapability,
                "bleeding": bleeding,
                "history": history,
                "image_summary": "Clinical image supplied." if image else "No image supplied.",
            }

            with st.spinner(
                "Building differential, evidence ledger and information-gain question..."
            ):
                try:
                    state = start_reasoning(case, image)

                    st.session_state.reasoning_case = case
                    st.session_state.reasoning_history = []
                    st.session_state.last_reasoning = json.dumps(
                        state,
                        ensure_ascii=False,
                        indent=2,
                    )
                    st.session_state.reasoning_differentials = state.get(
                        "differentials", []
                    )
                    st.session_state.reasoning_complete = False
                    st.rerun()

                except Exception as exc:
                    st.error(f"❌ Clinical reasoning failed: {friendly_ai_error(exc)}")

    state_text = st.session_state.get("last_reasoning", "")
    if not state_text:
        return

    state = extract_json(state_text)
    if not state:
        st.error("Stored reasoning state is invalid.")
        return

    st.markdown("---")
    st.markdown("## 📋 Current Clinical Reasoning State")

    if state.get("problem_representation"):
        st.markdown("### 🧩 Problem Representation")
        st.info(state["problem_representation"])

    evidence_ledger(state)

    red_flags = state.get("red_flags", [])
    if red_flags:
        st.markdown("### 🚩 Red Flags")
        for flag in red_flags:
            st.warning(flag)

    st.markdown("### 🎯 Information-Gain Decision")
    next_q = state.get("next_best_question", {}) or {}
    if next_q.get("question"):
        st.write(
            "The engine selected the question below because its answer may "
            "help distinguish between the current possibilities."
        )

    next_best_question_ui(state, st.session_state.reasoning_case)

    if state.get("suggested_next_step"):
        st.markdown("### 🩺 Suggested Next Clinical Step")
        st.info(state["suggested_next_step"])

    if state.get("uncertainty"):
        st.markdown("### ⚠️ Uncertainty")
        st.warning(state["uncertainty"])

    if st.session_state.reasoning_history:
        st.markdown("### 🔄 Reasoning History")
        for i, item in enumerate(st.session_state.reasoning_history, 1):
            st.markdown(
                f"**Step {i} — Question:** {item['question']}  \n"
                f"**Answer:** {item['answer']}"
            )

    st.markdown(
        """
        <div class="reason-card">
        <b>Safety:</b> This is AI-assisted clinical decision support.
        It does not replace examination, diagnostic testing, professional
        judgement, or definitive diagnosis.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# BASIC RADIOGRAPH MODULE
# ============================================================

RADIOGRAPH_TYPES = [
    "IOPA",
    "OPG",
    "Bitewing",
    "Occlusal",
    "Facial Radiograph",
    "Lateral Cephalogram (Ceph)",
]


def radiograph_analyzer():
    st.markdown("## 🩻 AI Radiographic Assessment")

    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    st.caption(f"AI analyses remaining today: {remaining}/{DAILY_ANALYSIS_LIMIT}")

    rtype = st.selectbox("Radiograph type", RADIOGRAPH_TYPES)

    ceph_type = ""
    if rtype == "Lateral Cephalogram (Ceph)":
        ceph_type = st.selectbox(
            "Cephalometric analysis",
            [
                "Steiner",
                "Downs",
                "McNamara",
                "Tweed",
                "Wits Appraisal",
                "Jarabak",
                "Soft Tissue Profile",
                "Combined / All",
            ],
        )

    uploaded = st.file_uploader(
        "Upload radiograph",
        type=["png", "jpg", "jpeg", "webp"],
        key="xray_upload_v2",
    )

    if uploaded:
        st.image(uploaded, caption="Uploaded radiograph", use_container_width=True)

    patient_name = st.text_input("Case identifier", key="xray_case_v2")

    if st.button(
        "🔍 Analyze X-ray",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT,
    ):
        if not uploaded:
            st.warning("Upload a radiograph first.")
            return

        prompt = f"""
You are an AI-assisted dental radiographic assessment system.

Radiograph type: {rtype}
Cephalometric analysis: {ceph_type}

Rules:
- Analyze only visible information.
- Never invent findings or tooth numbers.
- State image quality.
- Separate observed findings from interpretation.
- Clearly state uncertainty.
- Do not provide a definitive diagnosis.
- If a measurement cannot be reliably obtained from the image, say so.
- For cephalometry, do not invent landmark coordinates.

Return:
1. Image quality
2. Observed findings
3. Tooth/region where supported
4. Possible radiographic interpretation
5. Uncertainties
6. Suggested next clinical step
7. Safety note
"""

        with st.spinner("Analyzing radiograph..."):
            try:
                report = run_image_ai(uploaded, prompt)
                st.session_state.analysis_count += 1

                save_case(
                    "",
                    patient_name,
                    rtype,
                    uploaded.name,
                    f"{rtype} Assessment",
                    report,
                )

                st.success("Analysis completed.")
                st.markdown("### 📋 AI Assessment")
                st.markdown(report)

            except Exception as exc:
                st.error(f"❌ Radiographic AI failed: {friendly_ai_error(exc)}")


# ============================================================
# STUDENT MODE
# ============================================================

def student_mode():
    st.markdown("## 🎓 Student Mode")

    tabs = st.tabs(
        [
            "📚 Topic Tutor",
            "📝 Exam / PYQ",
            "🧠 Clinical Reasoning Practice",
        ]
    )

    with tabs[0]:
        topic = st.text_input("Topic", key="student_topic")
        if st.button("📖 Teach Me", use_container_width=True):
            if topic.strip():
                with st.spinner("Preparing notes..."):
                    try:
                        result = run_text_ai(
                            f"""
Teach {topic} to a BDS student.

Include:
- Definition
- Etiology
- Clinical features
- Diagnosis
- Management principles
- Important exam points
- Viva questions

Avoid inventing textbook-specific quotations.
"""
                        )
                        st.markdown(result)
                    except Exception as exc:
                        st.error(friendly_ai_error(exc))

    with tabs[1]:
        topic = st.text_input("Subject/topic for PYQ-style study", key="pyq_topic")
        if st.button("📝 Generate Question Bank", use_container_width=True):
            if topic.strip():
                with st.spinner("Generating..."):
                    try:
                        result = run_text_ai(
                            f"""
Create a BDS/KUHS-oriented study question bank for:
{topic}

Separate into:
- Long essays
- Short essays
- Short notes
- Viva
- High-yield concepts

Do not claim a question was asked in a specific year unless verified.
"""
                        )
                        st.markdown(result)
                    except Exception as exc:
                        st.error(friendly_ai_error(exc))

    with tabs[2]:
        clinical_reasoning_workspace()


# ============================================================
# DOCTOR MODE
# ============================================================

def doctor_mode():
    st.markdown("## 🩺 Doctor Mode")

    tabs = st.tabs(
        [
            "🧠 Clinical Reasoning",
            "🩻 X-ray AI",
            "📜 Case History",
        ]
    )

    with tabs[0]:
        clinical_reasoning_workspace()

    with tabs[1]:
        radiograph_analyzer()

    with tabs[2]:
        st.markdown("### 📜 Saved Cases")
        email = st.text_input(
            "Search by patient/case email",
            key="history_search",
        )

        rows = get_cases(email)

        if not rows:
            st.info("No saved cases found.")
        else:
            for row in rows:
                (
                    cid,
                    created,
                    patient_email,
                    patient_name,
                    case_type,
                    image_name,
                    title,
                    report,
                ) = row

                with st.expander(
                    f"{created[:19]} — {patient_name or 'Case'} — {case_type}"
                ):
                    st.write(f"**Case:** {patient_name or 'Not provided'}")
                    st.write(f"**Type:** {case_type}")
                    st.markdown(report)


# ============================================================
# HOME
# ============================================================

def show_home():
    st.markdown(
        '<div class="hero-title">🦷 Pocket Dentistry V2</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">'
        "AI-Powered Dental Learning & Adaptive Clinical Decision Support"
        "</div>",
        unsafe_allow_html=True,
    )

    st.info(
        "Phase 1 introduces the Evidence Ledger, Diagnostic Information-Gain "
        "workflow and Next-Best Clinical Question."
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 🎓 Student Mode")
        st.write(
            "Study tools, exam preparation and clinical reasoning practice."
        )
        if st.button("Enter Student Mode", use_container_width=True):
            st.session_state.mode = "student"
            st.rerun()

    with c2:
        st.markdown("### 🩺 Doctor Mode")
        st.write(
            "Clinical reasoning workspace and radiographic AI."
        )
        if st.button("Enter Doctor Mode", use_container_width=True):
            st.session_state.mode = "doctor"
            st.rerun()

    st.markdown("---")
    st.markdown("### 🧠 What is new in V2?")

    st.markdown(
        """
        **Evidence Ledger**
        - Supporting evidence
        - Opposing evidence
        - Unknown evidence

        **Diagnostic Information Gain**
        - Finds important missing information
        - Selects a high-value question

        **Next-Best Clinical Question**
        - One question at a time
        - Answer updates the reasoning state
        - Differential and evidence are recalculated
        """
    )


# ============================================================
# SIDEBAR + ROUTING
# ============================================================

with st.sidebar:
    st.markdown("## 🦷 Pocket Dentistry V2")

    if st.button("🏠 Home", use_container_width=True):
        st.session_state.mode = None
        st.rerun()

    if st.button("🧠 Clinical Reasoning", use_container_width=True):
        st.session_state.mode = "doctor"
        st.session_state.page = "reasoning"
        st.rerun()

    st.caption(f"AI model: {MODEL_NAME}")
    st.caption("Phase 1 — Adaptive Clinical Reasoning")


if st.session_state.mode is None:
    show_home()
elif st.session_state.mode == "student":
    student_mode()
elif st.session_state.mode == "doctor":
    doctor_mode()
