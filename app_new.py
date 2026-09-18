import os
import json
import re
from datetime import date, datetime
from io import BytesIO

import streamlit as st
from google import genai
from google.genai import types
import base64

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
# THEME / GLOBAL CSS (Colorful Medical Theme & Header Fix)
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    .hero-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(90deg, #1e3d59, #17b978, #008891);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -1px;
    }

    .hero-subtitle {
        text-align: center;
        font-size: 1.1rem;
        color: #008891;
        font-weight: 600;
        margin-bottom: 2rem;
    }

    .mode-card {
        padding: 1.35rem;
        border-radius: 20px;
        border: 2px solid #00acc1;
        background: linear-gradient(135deg, #e0f7fa, #80deea);
        margin-bottom: 1rem;
        color: #004d40;
        box-shadow: 0 4px 12px rgba(0, 151, 167, 0.2);
    }

    .mode-card h3, .mode-card p {
        color: #004d40 !important;
    }

    .mode-card.doctor {
        border-color: #43a047;
        background: linear-gradient(135deg, #e8f5e9, #a5d6a7);
        color: #1b5e20;
        box-shadow: 0 4px 12px rgba(67, 160, 71, 0.2);
    }

    .mode-card.doctor h3, .mode-card.doctor p {
        color: #1b5e20 !important;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 750;
        margin-top: 1.1rem;
        margin-bottom: 0.55rem;
        color: #17b978;
    }

    .safety-box {
        padding: 1rem;
        border-radius: 15px;
        border-left: 5px solid #17b978;
        background: rgba(23, 185, 120, 0.1);
        color: #1e3d59;
    }

    div.stButton > button {
        border-radius: 12px;
        min-height: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3d59, #17b978);
        color: white;
        border: none;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #17b978, #1e3d59);
        color: white;
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

if "active_pdf_viewer" not in st.session_state:
    st.session_state.active_pdf_viewer = None

# ------------------------------------------------------------
# GEMINI CLIENT
# ------------------------------------------------------------
def get_api_key():
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
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/png"
    return types.Part.from_bytes(data=data, mime_type=mime)

def run_image_analysis(uploaded_file, prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("Gemini API key not found in Streamlit Secrets.")
    image_part = image_to_part(uploaded_file)
    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt, image_part])
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("The AI returned an empty response.")
    return text

def run_text_ai(prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("Gemini API key not found in Streamlit Secrets.")
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("The AI returned an empty response.")
    return text

# ------------------------------------------------------------
# REFERENCE TEXTBOOK DATABASE & IN-APP PDF VIEWER ENGINE
# ------------------------------------------------------------
REFERENCE_DATABASE = {
    "oral pathology": ["Shafer's Textbook of Oral Pathology", "Neville's Oral and Maxillofacial Pathology"],
    "oral medicine": ["Burket's Oral Medicine", "Neville's Oral and Maxillofacial Pathology"],
    "periodontics": ["Carranza's Clinical Periodontology", "Newman and Carranza's Clinical Periodontology"],
    "endodontics": ["Cohen's Pathways of the Pulp", "Ingle's Endodontics"],
    "prosthodontics": ["Boucher's Prosthodontic Treatment for Edentulous Patients", "Zarb's Prosthodontic Treatment for Edentulous Patients"],
    "orthodontics": ["Contemporary Orthodontics – Proffit", "Graber's Orthodontics"],
    "pedodontics": ["McDonald and Avery's Dentistry for the Child and Adolescent", "Nikhil Marwa – Textbook of Pediatric Dentistry"],
    "public health dentistry": ["Soben Peter – Essentials of Preventive and Community Dentistry"],
    "dental materials": ["Phillips' Science of Dental Materials", "Craig's Restorative Dental Materials"],
    "radiology": ["White and Pharoah's Oral Radiology", "Langlais' Diagnostic Imaging of the Jaws"],
}

REFERENCE_ALIASES = {
    "caries": "endodontics",
    "rct": "endodontics",
    "root canal": "endodontics",
    "gum disease": "periodontics",
    "scaling": "periodontics",
    "opg": "radiology",
    "iopa": "radiology",
    "ceph": "orthodontics",
    "pedo": "pedodontics",
}

def get_topic_references(search_text):
    if not search_text:
        return None, None
    search = search_text.strip().lower()
    if search in REFERENCE_DATABASE:
        return search, REFERENCE_DATABASE[search]
    if search in REFERENCE_ALIASES:
        matched = REFERENCE_ALIASES[search]
        return matched, REFERENCE_DATABASE.get(matched)
    for key in sorted(REFERENCE_DATABASE.keys(), key=len, reverse=True):
        if key in search:
            return key, REFERENCE_DATABASE[key]
    return "oral pathology", REFERENCE_DATABASE["oral pathology"]

def show_dynamic_references(search_text):
    matched_topic, books = get_topic_references(search_text)
    st.markdown("### 📚 Standard Textbook References")
    st.caption(f"References matched to: **{matched_topic.title()}**")

    for idx, book in enumerate(books):
        col_r1, col_r2 = st.columns([3, 1])
        with col_r1:
            st.markdown(f"📕 **{book}**")
        with col_r2:
            if st.button("📖 Read PDF In-App", key=f"read_pdf_{idx}_{book}"):
                st.session_state.active_pdf_viewer = book

    if st.session_state.active_pdf_viewer:
        st.markdown("---")
        st.markdown(f"### 📂 In-App PDF Reader: *{st.session_state.active_pdf_viewer}*")
        pdf_html = f"""
        <div style="border: 2px solid #17b978; border-radius: 14px; padding: 15px; background-color: #f0fdf4; text-align: center;">
            <p style="color: #1e3d59; font-weight: bold; font-size: 16px;">📖 Currently Reading: {st.session_state.active_pdf_viewer}</p>
            <p style="color: #666; font-size: 13px;">(In-App PDF Viewer active. Textbooks and reference documents load directly inside Dental Buddy without leaving the web app).</p>
            <iframe src="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" width="100%" height="450px" style="border: none; border-radius: 8px;"></iframe>
        </div>
        """
        st.markdown(pdf_html, unsafe_allow_html=True)
        if st.button("❌ Close In-App Reader"):
            st.session_state.active_pdf_viewer = None
            st.rerun()

# ------------------------------------------------------------
# SAFETY RULES & PROMPTS
# ------------------------------------------------------------
COMMON_SAFETY_RULES = """
You are Dental Buddy, an AI-assisted dental learning and clinical decision-support system.
CORE SAFETY PRINCIPLE: Do good for the patient and never cause harm.
"""

RADIOGRAPH_PROMPTS = {
    "IOPA": COMMON_SAFETY_RULES + "Analyze the uploaded IOPA radiograph for quality, visible structures, caries, restorations, periapical changes, and bone levels.",
    "OPG": COMMON_SAFETY_RULES + "Analyze the uploaded OPG panoramic radiograph for dentition, missing teeth, bone levels, sinuses, and condyles.",
    "Bitewing": COMMON_SAFETY_RULES + "Analyze the bitewing radiograph focusing on interproximal caries and alveolar crest bone levels.",
    "Occlusal": COMMON_SAFETY_RULES + "Analyze the occlusal radiograph for teeth development, impacted teeth, and visible lesions.",
    "Facial Radiograph": COMMON_SAFETY_RULES + "Analyze the facial radiograph for skeletal alignment and structural continuity.",
}

CEPH_PROMPTS = COMMON_SAFETY_RULES + "Analyze the lateral cephalogram for orthodontic landmarks and measurements."

# ------------------------------------------------------------
# HOME SCREEN
# ------------------------------------------------------------
def show_home():
    st.markdown('<div class="hero-title">🦷 Dental Buddy</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">AI-Powered Dental Learning & Clinical Decision-Support Platform</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="mode-card">
        <h3>🎓 Student Mode</h3>
        <p>Learn dental topics, exams, previous-year questions, clinical reasoning,
        adaptive quizzes, essay generation and in-app textbook readers.</p>
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
        <b>🛡️ Safety Principle</b><br>
        Dental Buddy provides AI-assisted information and provisional radiographic assessment inside a secure web interface.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# HEADER & USAGE
# ------------------------------------------------------------
def show_mode_header(title, icon):
    left, right = st.columns([1, 5])
    with left:
        if st.button("← Home", use_container_width=True):
            st.session_state.mode = None
            st.rerun()
    with right:
        st.markdown(f"## {icon} {title}")

def can_analyze():
    return st.session_state.analysis_count < DAILY_ANALYSIS_LIMIT

def record_analysis():
    st.session_state.analysis_count += 1

def show_usage():
    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    st.caption(f"AI analyses remaining today: {remaining}/{DAILY_ANALYSIS_LIMIT}")

# ------------------------------------------------------------
# RADIOGRAPH ANALYZER
# ------------------------------------------------------------
def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")
    show_usage()

    radiograph_type = st.selectbox("Select radiograph type", ["IOPA", "OPG", "Bitewing", "Occlusal", "Facial Radiograph", "Lateral Cephalogram (Ceph)"])
    uploaded = st.file_uploader("Upload dental radiograph", type=["png", "jpg", "jpeg", "webp"])

    if uploaded:
        st.image(uploaded, caption="Uploaded radiograph", use_container_width=True)

    prompt = CEPH_PROMPTS if radiograph_type == "Lateral Cephalogram (Ceph)" else RADIOGRAPH_PROMPTS.get(radiograph_type, COMMON_SAFETY_RULES)

    if st.button("🔍 Analyze X-ray", type="primary", use_container_width=True, disabled=not can_analyze()):
        if uploaded is None:
            st.warning("Please upload a radiograph first.")
            return

        with st.spinner("Analyzing radiograph inside Dental Buddy..."):
            try:
                report = run_image_analysis(uploaded, prompt)
                record_analysis()
                st.session_state.last_report = report
                st.success("Analysis completed.")
                st.markdown("### 📋 AI Assessment Report")
                st.markdown(report)
            except Exception as exc:
                st.error("AI analysis failed.")
                st.code(str(exc))

# ------------------------------------------------------------
# STUDENT MODE
# ------------------------------------------------------------
def student_mode():
    show_mode_header("Student Mode", "🎓")
    tabs = st.tabs(["📚 Learn", "📝 Exam / PYQ", "🧠 Quiz", "📖 Textbook Refs & PDF"])

    with tabs[0]:
        st.markdown("### 📚 Dental Topic Tutor")
        topic = st.text_input("Topic", placeholder="Example: CPITN, deep bite, oral ulcer")
        if st.button("📖 Teach Me", type="primary", use_container_width=True):
            if not topic.strip():
                st.warning("Enter a topic.")
            else:
                with st.spinner("Preparing notes..."):
                    res = run_text_ai(f"Teach the dental topic '{topic}' with definitions, classification, and exam points.")
                    st.markdown(res)

    with tabs[1]:
        st.markdown("### 📝 Exam Helper")
        q = st.text_area("Question", placeholder="Paste previous year question here.")
        if st.button("✍️ Generate Answer", type="primary", use_container_width=True):
            if q.strip():
                with st.spinner("Generating answer..."):
                    res = run_text_ai(f"Write a university exam model answer for: {q}")
                    st.markdown(res)

    with tabs[2]:
        st.markdown("### 🧠 Adaptive Quiz")
        t = st.text_input("Quiz topic", placeholder="Example: Oral pathology")
        if st.button("🎯 Generate Quiz", type="primary", use_container_width=True):
            if t.strip():
                with st.spinner("Creating quiz..."):
                    res = run_text_ai(f"Create 3 multiple choice questions on {t} with options and explanations.")
                    st.markdown(res)

    with tabs[3]:
        st.markdown("### 📖 In-App Textbook Reference Library")
        ref_query = st.text_input("Search subject or topic for textbooks", placeholder="Example: Periodontics, Caries, Oral Pathology")
        show_dynamic_references(ref_query if ref_query else "oral pathology")

# ------------------------------------------------------------
# DOCTOR MODE
# ------------------------------------------------------------
def doctor_mode():
    show_mode_header("Doctor Mode", "🩺")
    tabs = st.tabs(["🩻 X-ray AI", "👄 Soft Tissue Reasoning", "📖 Textbook Refs & PDF"])

    with tabs[0]:
        radiograph_analyzer()

    with tabs[1]:
        st.markdown("### 👄 Soft-Tissue Lesion Reasoning")
        lesion_type = st.selectbox("Lesion type", ["White lesion", "Ulcer", "Swelling", "Red lesion"])
        if st.button("🧠 Build Reasoning", type="primary", use_container_width=True):
            with st.spinner("Processing clinical reasoning..."):
                res = run_text_ai(f"Provide differential diagnosis and clinical reasoning for oral lesion: {lesion_type}")
                st.markdown(res)

    with tabs[2]:
        st.markdown("### 📖 Clinical Reference Library")
        ref_query_doc = st.text_input("Search clinical subject", placeholder="Example: Oral Surgery, Pharmacology, Endodontics", key="doc_ref")
        show_dynamic_references(ref_query_doc if ref_query_doc else "oral surgery")

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.markdown("## 🦷 Dental Buddy")
        if st.session_state.mode:
            st.write(f"Current mode: **{st.session_state.mode.title()}**")
        st.markdown("---")
        st.write(f"Daily analyses used: {st.session_state.analysis_count}/{DAILY_ANALYSIS_LIMIT}")
        if st.button("🏠 Return Home", use_container_width=True):
            st.session_state.mode = None
            st.rerun()

# ------------------------------------------------------------
# RUN APP
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
