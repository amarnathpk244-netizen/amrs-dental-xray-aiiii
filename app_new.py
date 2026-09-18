import os
import json
import re
from datetime import date, datetime
import time

import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# POCKET DENTISTRY
# AI-Powered Dental Learning & Clinical Decision-Support
# ============================================================

st.set_page_config(
    page_title="Pocket Dentistry",
    page_icon="🦷",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# GLOBAL CSS
# ============================================================

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
        box-shadow: 0 4px 12px rgba(0,151,167,0.2);
    }

    .mode-card h3,
    .mode-card p {
        color: #004d40 !important;
    }

    .mode-card.doctor {
        border-color: #43a047;
        background: linear-gradient(135deg, #e8f5e9, #a5d6a7);
        color: #1b5e20;
    }

    .mode-card.doctor h3,
    .mode-card.doctor p {
        color: #1b5e20 !important;
    }

    .safety-box {
        padding: 1rem;
        border-radius: 15px;
        border-left: 5px solid #17b978;
        background: rgba(23,185,120,0.1);
        color: #1e3d59;
        margin-top: 1rem;
    }

    .book-card {
        padding: 1rem;
        border-radius: 16px;
        border: 1px solid #d0d7de;
        background: rgba(255,255,255,0.8);
        margin-bottom: 0.8rem;
    }

    .chapter-card {
        padding: 0.8rem 1rem;
        border-radius: 12px;
        border: 1px solid #d0d7de;
        background: #f8fafb;
        margin-bottom: 0.5rem;
    }

    .library-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }

    div.stButton > button {
        border-radius: 12px;
        min-height: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg,#1e3d59,#17b978);
        color: white;
        border: none;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }

    div.stButton > button:hover {
        background: linear-gradient(90deg,#17b978,#1e3d59);
        color: white;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "mode": None,
    "analysis_date": str(date.today()),
    "analysis_count": 0,
    "last_report": "",
    "last_image_name": "",
    "selected_book": None,
    "selected_subject": None,
    "selected_chapter": None,
    "library_search": "",
    "library_answer": "",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


if st.session_state.analysis_date != str(date.today()):
    st.session_state.analysis_date = str(date.today())
    st.session_state.analysis_count = 0


# ============================================================
# GEMINI CLIENT (CLEAN SDK CALL)
# ============================================================

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
        raise RuntimeError("Gemini API key not found in Streamlit Secrets.")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("The AI returned an empty response.")
    return text


# ============================================================
# BDS DIGITAL TEXTBOOK DATABASE
# ============================================================

TEXTBOOK_LIBRARY = {
    "Oral Pathology": {
        "Shafer's Textbook of Oral Pathology": [
            "Introduction to Oral Pathology", "Developmental Disturbances", "Dental Caries",
            "Pulp and Periapical Diseases", "Periodontal Diseases", "Cysts of the Oral Region",
            "Odontogenic Tumors", "Benign Tumors", "Malignant Tumors", "Diseases of Bone",
            "Diseases of Salivary Glands", "Oral Mucosal Diseases", "White Lesions",
            "Red and Pigmented Lesions", "Ulcers", "Infections",
        ],
        "Neville's Oral and Maxillofacial Pathology": [
            "Developmental Disorders", "Dental Caries", "Pulpal and Periapical Disease",
            "Periodontal Disease", "Cysts", "Odontogenic Tumors", "Bone Pathology",
            "Salivary Gland Pathology", "Oral Mucosal Disease", "White Lesions", "Ulcers", "Oral Cancer",
        ],
        "Soames & Southam - Oral Pathology": [
            "Developmental Disorders", "Caries", "Pulpal Disease", "Periodontal Disease",
            "Cysts", "Odontogenic Tumors", "Bone Diseases", "Salivary Gland Disease",
            "Mucosal Disease", "Oral Cancer",
        ],
    },
    "Oral Medicine": {
        "Burket's Oral Medicine": [
            "Patient Evaluation", "Systemic Disease", "Oral Manifestations of Systemic Disease",
            "Ulcers", "White Lesions", "Red Lesions", "Pigmented Lesions", "Vesiculobullous Disorders",
            "Salivary Gland Disorders", "Temporomandibular Disorders", "Oral Cancer",
        ],
        "Greenberg and Glick - Burket's Oral Medicine": [
            "Patient Assessment", "Diagnostic Procedures", "Oral Mucosal Diseases",
            "Ulcers", "White Lesions", "Salivary Gland Disease", "Orofacial Pain",
            "Systemic Disease", "Oral Cancer",
        ],
    },
    "Periodontics": {
        "Carranza's Clinical Periodontology": [
            "Periodontal Anatomy", "Periodontal Examination", "Classification of Periodontal Diseases",
            "Gingivitis", "Periodontitis", "Periodontal Pocket", "Bone Loss", "Plaque and Calculus",
            "Periodontal Instrumentation", "Scaling and Root Planing", "Periodontal Surgery", "Maintenance Therapy",
        ],
        "Newman and Carranza's Clinical Periodontology": [
            "Periodontal Anatomy", "Periodontal Examination", "Plaque Biofilm", "Gingival Diseases",
            "Periodontitis", "Risk Factors", "Bone Destruction", "Non-Surgical Therapy",
            "Periodontal Surgery", "Maintenance",
        ],
        "Shantipriya Reddy - Essentials of Periodontology": [
            "Periodontal Anatomy", "Gingivitis", "Periodontitis", "Periodontal Indices",
            "Plaque Control", "Scaling", "Root Planing", "Periodontal Surgery",
        ],
    },
    "Endodontics": {
        "Cohen's Pathways of the Pulp": [
            "Pulp Biology", "Diagnosis", "Pulpal Disease", "Periapical Disease",
            "Root Canal Anatomy", "Access Cavity", "Cleaning and Shaping", "Obturation",
            "Endodontic Emergencies", "Trauma", "Endodontic Surgery",
        ],
        "Ingle's Endodontics": [
            "Diagnosis", "Pulpal Pathology", "Periapical Pathology", "Instrumentation",
            "Irrigation", "Obturation", "Endodontic Failures", "Trauma", "Surgery",
        ],
        "Nisha Garg - Textbook of Operative Dentistry": [
            "Dental Caries", "Cavity Preparation", "Composite Restorations", "Amalgam",
            "Glass Ionomer Cement", "Bonding", "Matrix Systems", "Finishing and Polishing",
        ],
    },
    "Prosthodontics": {
        "Nallaswamy - Textbook of Prosthodontics": [
            "Diagnosis and Treatment Planning", "Complete Dentures", "Impression Making",
            "Jaw Relations", "Tooth Selection", "Denture Try-in", "Denture Processing",
            "Removable Partial Dentures", "Fixed Prosthodontics",
        ],
        "Boucher's Prosthodontic Treatment for Edentulous Patients": [
            "Edentulous Patient", "Treatment Planning", "Impressions", "Maxillomandibular Relations",
            "Artificial Teeth", "Denture Occlusion", "Denture Insertion", "Denture Problems",
        ],
        "McCracken's Removable Partial Prosthodontics": [
            "Diagnosis", "Treatment Planning", "Kennedy Classification", "Surveying",
            "Major Connectors", "Minor Connectors", "Direct Retainers", "Indirect Retainers", "RPD Design",
        ],
        "Rosenstiel - Contemporary Fixed Prosthodontics": [
            "Treatment Planning", "Tooth Preparation", "Impression Materials",
            "Provisional Restorations", "Crowns", "Bridges", "Cementation", "Esthetics",
        ],
    },
    "Orthodontics": {
        "Proffit - Contemporary Orthodontics": [
            "Growth and Development", "Development of Dentition", "Malocclusion", "Diagnosis",
            "Treatment Planning", "Biomechanics", "Fixed Appliances", "Functional Appliances",
            "Orthodontic Retention", "Deep Bite", "Open Bite", "Class II Malocclusion", "Class III Malocclusion",
        ],
        "S.I. Bhalajhi - Orthodontics: The Art and Science": [
            "Growth and Development", "Normal Occlusion", "Malocclusion", "Etiology",
            "Diagnosis", "Cephalometrics", "Functional Appliances", "Fixed Appliances", "Retention",
        ],
        "Graber's Orthodontics": [
            "Growth", "Diagnosis", "Cephalometric Analysis", "Biomechanics",
            "Orthodontic Appliances", "Treatment Planning", "Retention",
        ],
    },
    "Pedodontics": {
        "McDonald and Avery's Dentistry for the Child and Adolescent": [
            "Child Development", "Preventive Dentistry", "Caries", "Pulp Therapy",
            "Trauma", "Space Management", "Mixed Dentition", "Special Care",
        ],
        "Nikhil Marwah - Textbook of Pediatric Dentistry": [
            "Growth and Development", "Preventive Dentistry", "Dental Caries", "Pulp Therapy",
            "Trauma", "Space Maintainers", "Behavior Management", "Interceptive Orthodontics",
        ],
        "Shobha Tandon - Textbook of Pedodontics": [
            "Child Psychology", "Growth and Development", "Preventive Dentistry",
            "Caries", "Pulp Therapy", "Trauma", "Space Management",
        ],
    },
    "Public Health Dentistry": {
        "Soben Peter - Essentials of Preventive and Community Dentistry": [
            "Introduction to Public Health", "Health and Disease", "Epidemiology", "Study Designs",
            "Bias", "Screening", "Biostatistics", "Indices", "DMFT", "OHI-S", "CPITN",
            "Preventive Dentistry", "Community Dental Programs", "Health Education",
        ],
        "Hiremath - Textbook of Public Health Dentistry": [
            "Public Health", "Epidemiology", "Biostatistics", "Indices", "Preventive Dentistry",
            "Health Education", "School Dental Health", "Community Programs",
        ],
    },
    "Dental Materials": {
        "Phillips' Science of Dental Materials": [
            "Structure of Matter", "Physical Properties", "Biocompatibility", "Impression Materials",
            "Gypsum Products", "Dental Waxes", "Resin-Based Composites", "Dental Cements", "Dental Amalgam",
        ],
        "Craig's Restorative Dental Materials": [
            "Mechanical Properties", "Impression Materials", "Resins", "Composites", "Cements", "Metals", "Ceramics",
        ],
    },
    "Oral Surgery": {
        "Peterson's Principles of Oral and Maxillofacial Surgery": [
            "Patient Evaluation", "Exodontia", "Impacted Teeth", "Infections", "Cysts",
            "Trauma", "Preprosthetic Surgery", "Implant Surgery",
        ],
        "Malamed's Handbook of Local Anesthesia": [
            "Pain and Anxiety", "Local Anesthetic Drugs", "Syringes and Needles",
            "Maxillary Anesthesia", "Mandibular Anesthesia", "Complications", "Special Patients",
        ],
    },
    "Radiology": {
        "White and Pharoah's Oral Radiology": [
            "Radiographic Principles", "Intraoral Radiography", "Panoramic Radiography",
            "Digital Imaging", "Radiographic Anatomy", "Caries", "Periodontal Disease",
            "Periapical Lesions", "Cysts", "Tumors", "CBCT",
        ],
        "Langlais' Diagnostic Imaging of the Jaws": [
            "Radiographic Anatomy", "Radiolucent Lesions", "Radiopaque Lesions",
            "Mixed Lesions", "Cysts", "Tumors", "Jaw Diseases",
        ],
    },
}


# ============================================================
# SEARCH ALIASES & CEPH TYPES
# ============================================================

REFERENCE_ALIASES = {
    "caries": "Endodontics", "dental caries": "Endodontics", "rct": "Endodontics", "root canal": "Endodontics", "pulp": "Endodontics",
    "gum disease": "Periodontics", "periodontal": "Periodontics", "periodontitis": "Periodontics", "gingivitis": "Periodontics", "scaling": "Periodontics", "cpitn": "Public Health Dentistry",
    "opg": "Radiology", "iopa": "Radiology", "bitewing": "Radiology", "occlusal": "Radiology", "radiograph": "Radiology", "cbct": "Radiology",
    "ceph": "Orthodontics", "cephalometric": "Orthodontics", "deep bite": "Orthodontics", "open bite": "Orthodontics", "malocclusion": "Orthodontics", "leeway space": "Orthodontics", "functional appliance": "Orthodontics",
    "pedo": "Pedodontics", "paedo": "Pedodontics", "pediatric": "Pedodontics", "child dentistry": "Pedodontics",
    "prostho": "Prosthodontics", "denture": "Prosthodontics", "complete denture": "Prosthodontics", "partial denture": "Prosthodontics",
    "surgery": "Oral Surgery", "extraction": "Oral Surgery", "impacted tooth": "Oral Surgery", "local anesthesia": "Oral Surgery",
    "oral ulcer": "Oral Medicine", "white lesion": "Oral Medicine", "red lesion": "Oral Medicine",
    "oral pathology": "Oral Pathology", "pathology": "Oral Pathology",
    "dmft": "Public Health Dentistry", "ohis": "Public Health Dentistry", "epidemiology": "Public Health Dentistry", "bias": "Public Health Dentistry", "randomized controlled trial": "Public Health Dentistry",
}

CEPH_ANALYSES = [
    "Steiner Analysis",
    "Downs Analysis",
    "McNamara Analysis",
    "Tweed Analysis",
    "Wits Appraisal",
    "Jarabak Analysis",
    "Soft Tissue Profile Analysis",
    "Combined / All Analyses",
]


# ============================================================
# FIND SUBJECT & CHAPTERS
# ============================================================

def find_subject(search_text):
    if not search_text:
        return "Oral Pathology"
    search = search_text.strip().lower()
    if search in REFERENCE_ALIASES:
        return REFERENCE_ALIASES[search]
    for alias, subject in REFERENCE_ALIASES.items():
        if alias in search:
            return subject
    for subject in TEXTBOOK_LIBRARY:
        if subject.lower() in search:
            return subject
    for subject, books in TEXTBOOK_LIBRARY.items():
        for book, chapters in books.items():
            if any(search in chapter.lower() for chapter in chapters):
                return subject
    return "Oral Pathology"


def find_relevant_chapters(search_text, subject):
    results = []
    if not search_text:
        return results
    query = search_text.lower().strip()
    books = TEXTBOOK_LIBRARY.get(subject, {})
    for book, chapters in books.items():
        for chapter in chapters:
            if query in chapter.lower() or any(word in chapter.lower() for word in query.split() if len(word) > 3):
                results.append((book, chapter))
    return results


# ============================================================
# DIGITAL TEXTBOOK LIBRARY
# ============================================================

def textbook_library():
    st.markdown("### 📚 Pocket Dentistry Digital Library")
    st.caption("Find the relevant BDS subject, textbook and chapter instantly.")

    search = st.text_input(
        "🔎 Search topic",
        placeholder="Try: Deep bite, CPITN, caries, oral ulcer, periapical lesion, complete denture...",
        key="digital_library_search",
    )

    default_subject = find_subject(search)
    subjects = list(TEXTBOOK_LIBRARY.keys())
    default_index = subjects.index(default_subject) if default_subject in subjects else 0

    selected_subject = st.selectbox("📚 Select subject", subjects, index=default_index, key="digital_library_subject")
    st.session_state.selected_subject = selected_subject
    books = TEXTBOOK_LIBRARY[selected_subject]

    if search.strip():
        st.markdown(f"#### 🔍 Search results for: **{search}**")
        relevant = find_relevant_chapters(search, selected_subject)
        if relevant:
            for book, chapter in relevant[:15]:
                st.markdown(
                    f"""
                    <div class="chapter-card">
                    📑 <b>{chapter}</b><br>
                    <small>📕 {book}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No exact chapter match found. You can still ask Pocket Dentistry about the topic.")

    st.markdown("#### 📕 Available Textbooks")
    selected_book = st.selectbox("Select textbook", list(books.keys()), key="digital_library_book")
    st.session_state.selected_book = selected_book

    st.markdown(
        f"""
        <div class="book-card">
        <div class="library-title">📕 {selected_book}</div>
        <small>Use the chapter list below for quick topic navigation.</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 📑 Chapters / Topics")
    chapters = books[selected_book]
    chapter_options = ["Select a chapter"] + chapters
    selected_chapter = st.selectbox("Choose chapter", chapter_options, key=f"chapter_{selected_book}")

    if selected_chapter != "Select a chapter":
        st.session_state.selected_chapter = selected_chapter
        st.success(f"Selected chapter: {selected_chapter}")

        st.markdown("#### 🤖 Ask About This Chapter")
        question = st.text_area(
            "What do you want to understand?",
            placeholder="Example: Explain this chapter in simple BDS exam-oriented language.",
            key=f"question_{selected_book}_{selected_chapter}",
        )

        if st.button("🤖 Ask the Textbook", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("Enter a question first.")
            else:
                with st.spinner("Preparing textbook-oriented explanation..."):
                    try:
                        prompt = f"""
You are Pocket Dentistry, a BDS educational assistant.
The student is referring to:
Subject: {selected_subject}
Textbook: {selected_book}
Chapter/topic: {selected_chapter}
Student question: {question}

Provide a clear BDS-level educational explanation.
Format with definitions, classifications, clinical points, and exam-oriented viva points.
"""
                        answer = run_text_ai(prompt)
                        st.session_state.library_answer = answer
                    except Exception as exc:
                        st.error("Textbook AI response failed.")
                        st.code(str(exc))

        if st.session_state.library_answer:
            st.markdown("---")
            st.markdown("### 📚 Pocket Dentistry Explanation")
            st.markdown(st.session_state.library_answer)


# ============================================================
# SAFETY RULES & PROMPTS
# ============================================================

COMMON_SAFETY_RULES = """
You are Pocket Dentistry, an AI-assisted dental learning and clinical decision-support system.
CORE SAFETY PRINCIPLE: Do good for the patient and never cause harm.
"""

RADIOGRAPH_PROMPTS = {
    "IOPA": COMMON_SAFETY_RULES + "Analyze the uploaded IOPA radiograph for image quality, visible structures, caries, restorations, periapical findings, periodontal changes, and provisional radiographic impression.",
    "OPG": COMMON_SAFETY_RULES + "Analyze the uploaded OPG panoramic radiograph for image quality, dentition, missing/impacted teeth, periodontal bone levels, periapical regions, jaws, sinuses, condyles, and provisional impression.",
    "Bitewing": COMMON_SAFETY_RULES + "Analyze the bitewing radiograph focusing on interproximal caries, restorations, and alveolar crest bone levels.",
    "Occlusal": COMMON_SAFETY_RULES + "Analyze the occlusal radiograph for teeth development, impacted teeth, and visible pathological lesions.",
    "Facial Radiograph": COMMON_SAFETY_RULES + "Analyze the facial radiograph for skeletal alignment, structural continuity, and any obvious fractures.",
}


# ============================================================
# HOME SCREEN & HEADERS
# ============================================================

def show_home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">AI-Powered Dental Learning & Clinical Decision-Support Platform</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="mode-card">
        <h3>🎓 Student Mode</h3>
        <p>Learn dental topics, prepare university answers, practice quizzes and access the Pocket Dentistry Digital Textbook Library.</p>
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
        <p>Radiographic AI with Scale Calibration, Cephalometric Analysis selection, professional Soft-Tissue clinical reasoning workflow and clinical decision support.</p>
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
        Pocket Dentistry provides AI-assisted educational information and provisional radiographic assessment inside a secure web interface.
        </div>
        """,
        unsafe_allow_html=True,
    )


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


# ============================================================
# RADIOGRAPH ANALYZER (WITH CALIBRATION & CEPH TYPES)
# ============================================================

def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")
    show_usage()

    radiograph_type = st.selectbox(
        "Select radiograph type",
        ["IOPA", "OPG", "Bitewing", "Occlusal", "Facial Radiograph", "Lateral Cephalogram (Ceph)"],
    )

    ceph_analysis_type = "Combined / All Analyses"
    if radiograph_type == "Lateral Cephalogram (Ceph)":
        ceph_analysis_type = st.selectbox("Select Cephalometric Analysis Type", CEPH_ANALYSES)

    st.markdown("#### 📏 Scale Calibration Settings")
    calibration_mode = st.radio(
        "Select Scale Calibration Mode",
        [
            "🤖 Auto-Calculate / AI Estimation",
            "✏️ Enter Known Calibration Scale (mm/pixel)"
        ],
        key="calibration_mode_selector"
    )
    scale_value_input = "Auto-estimated by AI based on anatomical proportions"
    if calibration_mode == "✏️ Enter Known Calibration Scale (mm/pixel)":
        scale_value_input = st.text_input("Enter known scale value", value="1.0 mm/pixel", key="known_scale_val")

    uploaded = st.file_uploader("📤 Upload dental radiograph", type=["png", "jpg", "jpeg", "webp"])

    if uploaded:
        st.image(uploaded, caption="Uploaded radiograph", use_container_width=True)

    if radiograph_type == "Lateral Cephalogram (Ceph)":
        prompt = COMMON_SAFETY_RULES + f"""
Analyze the uploaded lateral cephalogram specifically focusing on: {ceph_analysis_type}.
Calibration Mode: {calibration_mode} (Scale Setting: {scale_value_input}).
Provide:
1. Image Quality & Landmark Visibility
2. Skeletal & Dental Relationship Measurements (scaled with calibration)
3. Vertical & Soft Tissue Profile Findings
4. Cephalometric Interpretation & Clinical Significance
5. Uncertainty & Limitations
"""
    else:
        prompt = RADIOGRAPH_PROMPTS.get(radiograph_type, COMMON_SAFETY_RULES) + f"""
Calibration Mode: {calibration_mode} (Scale Setting: {scale_value_input}).
Ensure spatial/measurement estimates incorporate this scale setting.
"""

    if st.button("🔍 Analyze X-ray", type="primary", use_container_width=True, disabled=not can_analyze()):
        if uploaded is None:
            st.warning("Please upload a radiograph first.")
            return

        with st.spinner("Analyzing radiograph with calibration..."):
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


# ============================================================
# STUDENT MODE
# ============================================================

def student_mode():
    show_mode_header("Student Mode", "🎓")
    tabs = st.tabs(["📚 Learn", "📝 Exam / PYQ", "🧠 Quiz", "📖 Digital Library"])

    with tabs[0]:
        st.markdown("### 📚 Dental Topic Tutor")
        topic = st.text_input("Topic", placeholder="Example: CPITN, deep bite, oral ulcer", key="learn_topic")
        if st.button("📖 Teach Me", type="primary", use_container_width=True):
            if not topic.strip():
                st.warning("Enter a topic.")
            else:
                with st.spinner("Preparing notes..."):
                    res = run_text_ai(f"Teach the BDS topic '{topic}' with definitions, etiology, classification, clinical features, and viva questions.")
                    st.markdown(res)

    with tabs[1]:
        st.markdown("### 📝 University Exam Helper")
        q = st.text_area("Question", placeholder="Paste previous year question here.", key="exam_q")
        if st.button("✍️ Generate Answer", type="primary", use_container_width=True):
            if q.strip():
                with st.spinner("Generating answer..."):
                    res = run_text_ai(f"Write a BDS university examination model answer for: {q}")
                    st.markdown(res)

    with tabs[2]:
        st.markdown("### 🧠 Dental Quiz")
        quiz_topic = st.text_input("Quiz topic", placeholder="Example: Oral pathology", key="quiz_topic")
        if st.button("🎯 Generate Quiz", type="primary", use_container_width=True):
            if quiz_topic.strip():
                with st.spinner("Creating quiz..."):
                    res = run_text_ai(f"Create 5 BDS-level MCQs on '{quiz_topic}' with options A, B, C, D and explanations.")
                    st.markdown(res)

    with tabs[3]:
        textbook_library()


# ============================================================
# DOCTOR MODE (PROFESSIONAL SOFT TISSUE WORKFLOW)
# ============================================================

def doctor_mode():
    show_mode_header("Doctor Mode", "🩺")
    tabs = st.tabs(["🩻 X-ray AI", "👄 Soft Tissue Reasoning", "📖 Clinical Library"])

    with tabs[0]:
        radiograph_analyzer()

    with tabs[1]:
        st.markdown("### 👄 Advanced Professional Soft-Tissue Lesion Reasoning")
        st.caption("Provide comprehensive clinical parameters for professional diagnostic decision-support.")

        lesion_type = st.selectbox(
            "Primary Lesion Appearance",
            ["White lesion", "Red lesion", "Red-white lesion", "Ulcer", "Pigmented lesion", "Swelling / mass", "Vesicle / blister", "Other / unclear"],
            key="doc_lesion_type",
        )

        col_st1, col_st2 = st.columns(2)
        with col_st1:
            lesion_duration = st.text_input("Duration & Progression", placeholder="e.g., 2 weeks, growing rapidly")
            lesion_pain = st.selectbox("Pain Status", ["Painless", "Mild discomfort", "Painful / Burning"])
            lesion_scrapable = st.selectbox("Scrapability (for white/red plaques)", ["Not applicable", "Scrapable (leaves erythematous base)", "Non-scrapable"])
        with col_st2:
            lesion_site = st.text_input("Anatomical Location", placeholder="e.g., Left buccal mucosa, lateral tongue")
            lesion_bleeding = st.selectbox("Bleeding on Gentle Manipulation", ["No", "Yes", "Not tested"])
            lesion_induration = st.selectbox("Induration / Firmness on Palpation", ["Soft / Fluctuant", "Firm / Indurated", "Not assessed"])

        additional_features = st.text_area(
            "Additional Clinical Findings & History",
            placeholder="Include habits (tobacco/betel nut), local trauma, medical history, lymphadenopathy, etc.",
        )

        if st.button("🧠 Build Professional Clinical Reasoning", type="primary", use_container_width=True):
            with st.spinner("Processing advanced clinical reasoning..."):
                try:
                    prompt = f"""
You are Pocket Dentistry Doctor Mode, an advanced clinical decision-support system.
Analyze the following oral mucosal lesion case:
- Lesion Type: {lesion_type}
- Anatomical Site: {lesion_site}
- Duration & Progression: {lesion_duration}
- Pain Status: {lesion_pain}
- Scrapability: {lesion_scrapable}
- Bleeding on Manipulation: {lesion_bleeding}
- Induration: {lesion_induration}
- Additional History/Findings: {additional_features}

Provide a structured clinical decision support report:
1. Problem Representation Summary
2. Top Differential Diagnoses (with justification)
3. Supporting vs. Contradictory Clinical Features
4. Critical Missing Information / Unknowns
5. One Highest-Value Next Clinical Question or Diagnostic Test (e.g., biopsy indication)
6. Broad Clinical Management & Red Flags Warranting Urgent Referral
"""
                    res = run_text_ai(prompt)
                    st.markdown("### 📋 Clinical Decision Support Report")
                    st.markdown(res)
                except Exception as exc:
                    st.error("Clinical reasoning failed.")
                    st.code(str(exc))

    with tabs[2]:
        textbook_library()


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():
    with st.sidebar:
        st.markdown("## 🦷 Pocket Dentistry")
        if st.session_state.mode:
            st.write(f"Current mode: **{st.session_state.mode.title()}**")
        st.markdown("---")
        st.write(f"Daily analyses used: {st.session_state.analysis_count}/{DAILY_ANALYSIS_LIMIT}")
        if st.button("🏠 Return Home", use_container_width=True):
            st.session_state.mode = None
            st.rerun()


# ============================================================
# RUN APP
# ============================================================

sidebar()

if st.session_state.mode is None:
    show_home()
elif st.session_state.mode == "student":
    student_mode()
elif st.session_state.mode == "doctor":
    doctor_mode()
