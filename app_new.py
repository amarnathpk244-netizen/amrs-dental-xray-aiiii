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

# Stable Gemini model
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


# Reset daily analysis count
if st.session_state.analysis_date != str(date.today()):
    st.session_state.analysis_date = str(date.today())
    st.session_state.analysis_count = 0


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_api_key():
    """
    Read Gemini API key from:
    1. Streamlit Secrets
    2. Environment variable
    """

    key = ""

    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""

    if not key:
        key = os.getenv("GEMINI_API_KEY", "")

    return str(key).strip()


def get_client():
    api_key = get_api_key()

    if not api_key:
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


# ============================================================
# GEMINI ERROR HANDLING
# ============================================================

def friendly_ai_error(exc):
    """
    Converts Gemini/API errors into a safe user-friendly message.

    We intentionally do NOT display the complete exception because
    API errors can contain technical information that should not be
    exposed to normal users.
    """

    error_text = str(exc).upper()

    if "401" in error_text or "UNAUTHENTICATED" in error_text:
        return (
            "🔐 **Gemini authentication failed.**\n\n"
            "Please check the `GEMINI_API_KEY` in Streamlit Secrets."
        )

    if "403" in error_text or "PERMISSION_DENIED" in error_text:
        return (
            "🚫 **Gemini API permission denied.**\n\n"
            "Please check that the API key is active and has access "
            "to the selected Gemini model."
        )

    if "404" in error_text or "NOT_FOUND" in error_text:
        return (
            f"🔎 **Gemini model `{MODEL_NAME}` was not found or is "
            "not available for this API project.**\n\n"
            "Check the model name and API access."
        )

    if (
        "429" in error_text
        or "RESOURCE_EXHAUSTED" in error_text
        or "QUOTA" in error_text
    ):
        return (
            "⏳ **Gemini API quota or rate limit reached.**\n\n"
            "Please wait a little and try again."
        )

    if "503" in error_text or "UNAVAILABLE" in error_text:
        return (
            "🔄 **Gemini is temporarily unavailable.**\n\n"
            "The AI service may be busy. Please try again shortly."
        )

    if "400" in error_text or "INVALID_ARGUMENT" in error_text:
        return (
            "⚠️ **Gemini rejected the request.**\n\n"
            "The request or model configuration may be invalid."
        )

    if "SAFETY" in error_text or "BLOCKED" in error_text:
        return (
            "🛡️ **The AI could not provide a response to this request.**\n\n"
            "Please rephrase the question and try again."
        )

    return (
        "⚠️ **AI service error.**\n\n"
        "Pocket Dentistry could not complete the AI request. "
        "Please try again."
    )


def show_ai_error(exc, title="AI request failed"):
    """
    Display a clean error instead of allowing Streamlit to crash.
    """

    st.error(f"❌ {title}")
    st.markdown(friendly_ai_error(exc))


# ============================================================
# IMAGE CONVERSION
# ============================================================

def image_to_part(uploaded_file):
    data = uploaded_file.getvalue()

    mime = uploaded_file.type or "image/png"

    return types.Part.from_bytes(
        data=data,
        mime_type=mime,
    )


# ============================================================
# IMAGE AI
# ============================================================

def run_image_analysis(uploaded_file, prompt):
    client = get_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key not found or Gemini client could not be created."
        )

    image_part = image_to_part(uploaded_file)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            image_part,
        ],
    )

    text = getattr(response, "text", None)

    if not text:
        raise RuntimeError(
            "The AI returned an empty response."
        )

    return text


# ============================================================
# TEXT AI — FIXED
# ============================================================

def run_text_ai(prompt):
    """
    Safe Gemini text-generation wrapper.

    IMPORTANT:
    This function raises exceptions intentionally.
    The calling UI sections catch them and show a clean message.
    This prevents the raw Streamlit traceback from being shown.
    """

    client = get_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key not found or Gemini client could not be created."
        )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    text = getattr(response, "text", None)

    if not text:
        raise RuntimeError(
            "The AI returned an empty response."
        )

    return text


# ============================================================
# BDS DIGITAL TEXTBOOK DATABASE
# ============================================================

TEXTBOOK_LIBRARY = {
    "Oral Pathology": {
        "Shafer's Textbook of Oral Pathology": [
            "Introduction to Oral Pathology",
            "Developmental Disturbances",
            "Dental Caries",
            "Pulp and Periapical Diseases",
            "Periodontal Diseases",
            "Cysts of the Oral Region",
            "Odontogenic Tumors",
            "Benign Tumors",
            "Malignant Tumors",
            "Diseases of Bone",
            "Diseases of Salivary Glands",
            "Oral Mucosal Diseases",
            "White Lesions",
            "Red and Pigmented Lesions",
            "Ulcers",
            "Infections",
        ],
        "Neville's Oral and Maxillofacial Pathology": [
            "Developmental Disorders",
            "Dental Caries",
            "Pulpal and Periapical Disease",
            "Periodontal Disease",
            "Cysts",
            "Odontogenic Tumors",
            "Bone Pathology",
            "Salivary Gland Pathology",
            "Oral Mucosal Disease",
            "White Lesions",
            "Ulcers",
            "Oral Cancer",
        ],
        "Soames & Southam - Oral Pathology": [
            "Developmental Disorders",
            "Caries",
            "Pulpal Disease",
            "Periodontal Disease",
            "Cysts",
            "Odontogenic Tumors",
            "Bone Diseases",
            "Salivary Gland Disease",
            "Mucosal Disease",
            "Oral Cancer",
        ],
    },

    "Oral Medicine": {
        "Burket's Oral Medicine": [
            "Patient Evaluation",
            "Systemic Disease",
            "Oral Manifestations of Systemic Disease",
            "Ulcers",
            "White Lesions",
            "Red Lesions",
            "Pigmented Lesions",
            "Vesiculobullous Disorders",
            "Salivary Gland Disorders",
            "Temporomandibular Disorders",
            "Oral Cancer",
        ],
        "Greenberg and Glick - Burket's Oral Medicine": [
            "Patient Assessment",
            "Diagnostic Procedures",
            "Oral Mucosal Diseases",
            "Ulcers",
            "White Lesions",
            "Salivary Gland Disease",
            "Orofacial Pain",
            "Systemic Disease",
            "Oral Cancer",
        ],
    },

    "Periodontics": {
        "Carranza's Clinical Periodontology": [
            "Periodontal Anatomy",
            "Periodontal Examination",
            "Classification of Periodontal Diseases",
            "Gingivitis",
            "Periodontitis",
            "Periodontal Pocket",
            "Bone Loss",
            "Plaque and Calculus",
            "Periodontal Instrumentation",
            "Scaling and Root Planing",
            "Periodontal Surgery",
            "Maintenance Therapy",
        ],
        "Newman and Carranza's Clinical Periodontology": [
            "Periodontal Anatomy",
            "Periodontal Examination",
            "Plaque Biofilm",
            "Gingival Diseases",
            "Periodontitis",
            "Risk Factors",
            "Bone Destruction",
            "Non-Surgical Therapy",
            "Periodontal Surgery",
            "Maintenance",
        ],
        "Shantipriya Reddy - Essentials of Periodontology": [
            "Periodontal Anatomy",
            "Gingivitis",
            "Periodontitis",
            "Periodontal Indices",
            "Plaque Control",
            "Scaling",
            "Root Planing",
            "Periodontal Surgery",
        ],
    },

    "Endodontics": {
        "Cohen's Pathways of the Pulp": [
            "Pulp Biology",
            "Diagnosis",
            "Pulpal Disease",
            "Periapical Disease",
            "Root Canal Anatomy",
            "Access Cavity",
            "Cleaning and Shaping",
            "Obturation",
            "Endodontic Emergencies",
            "Trauma",
            "Endodontic Surgery",
        ],
        "Ingle's Endodontics": [
            "Diagnosis",
            "Pulpal Pathology",
            "Periapical Pathology",
            "Instrumentation",
            "Irrigation",
            "Obturation",
            "Endodontic Failures",
            "Trauma",
            "Surgery",
        ],
        "Nisha Garg - Textbook of Operative Dentistry": [
            "Dental Caries",
            "Cavity Preparation",
            "Composite Restorations",
            "Amalgam",
            "Glass Ionomer Cement",
            "Bonding",
            "Matrix Systems",
            "Finishing and Polishing",
        ],
    },

    "Prosthodontics": {
        "Nallaswamy - Textbook of Prosthodontics": [
            "Diagnosis and Treatment Planning",
            "Complete Dentures",
            "Impression Making",
            "Jaw Relations",
            "Tooth Selection",
            "Denture Try-in",
            "Denture Processing",
            "Removable Partial Dentures",
            "Fixed Prosthodontics",
        ],
        "Boucher's Prosthodontic Treatment for Edentulous Patients": [
            "Edentulous Patient",
            "Treatment Planning",
            "Impressions",
            "Maxillomandibular Relations",
            "Artificial Teeth",
            "Denture Occlusion",
            "Denture Insertion",
            "Denture Problems",
        ],
        "McCracken's Removable Partial Prosthodontics": [
            "Diagnosis",
            "Treatment Planning",
            "Kennedy Classification",
            "Surveying",
            "Major Connectors",
            "Minor Connectors",
            "Direct Retainers",
            "Indirect Retainers",
            "RPD Design",
        ],
        "Rosenstiel - Contemporary Fixed Prosthodontics": [
            "Treatment Planning",
            "Tooth Preparation",
            "Impression Materials",
            "Provisional Restorations",
            "Crowns",
            "Bridges",
            "Cementation",
            "Esthetics",
        ],
    },

    "Orthodontics": {
        "Proffit - Contemporary Orthodontics": [
            "Growth and Development",
            "Development of Dentition",
            "Malocclusion",
            "Diagnosis",
            "Treatment Planning",
            "Biomechanics",
            "Fixed Appliances",
            "Functional Appliances",
            "Orthodontic Retention",
            "Deep Bite",
            "Open Bite",
            "Class II Malocclusion",
            "Class III Malocclusion",
        ],
        "S.I. Bhalajhi - Orthodontics: The Art and Science": [
            "Growth and Development",
            "Normal Occlusion",
            "Malocclusion",
            "Etiology",
            "Diagnosis",
            "Cephalometrics",
            "Functional Appliances",
            "Fixed Appliances",
            "Retention",
        ],
        "Graber's Orthodontics": [
            "Growth",
            "Diagnosis",
            "Cephalometric Analysis",
            "Biomechanics",
            "Orthodontic Appliances",
            "Treatment Planning",
            "Retention",
        ],
    },

    "Pedodontics": {
        "McDonald and Avery's Dentistry for the Child and Adolescent": [
            "Child Development",
            "Preventive Dentistry",
            "Caries",
            "Pulp Therapy",
            "Trauma",
            "Space Management",
            "Mixed Dentition",
            "Special Care",
        ],
        "Nikhil Marwah - Textbook of Pediatric Dentistry": [
            "Growth and Development",
            "Preventive Dentistry",
            "Dental Caries",
            "Pulp Therapy",
            "Trauma",
            "Space Maintainers",
            "Behavior Management",
            "Interceptive Orthodontics",
        ],
        "Shobha Tandon - Textbook of Pedodontics": [
            "Child Psychology",
            "Growth and Development",
            "Preventive Dentistry",
            "Caries",
            "Pulp Therapy",
            "Trauma",
            "Space Management",
        ],
    },

    "Public Health Dentistry": {
        "Soben Peter - Essentials of Preventive and Community Dentistry": [
            "Introduction to Public Health",
            "Health and Disease",
            "Epidemiology",
            "Study Designs",
            "Bias",
            "Screening",
            "Biostatistics",
            "Indices",
            "DMFT",
            "OHI-S",
            "CPITN",
            "Preventive Dentistry",
            "Community Dental Programs",
            "Health Education",
        ],
        "Hiremath - Textbook of Public Health Dentistry": [
            "Public Health",
            "Epidemiology",
            "Biostatistics",
            "Indices",
            "Preventive Dentistry",
            "Health Education",
            "School Dental Health",
            "Community Programs",
        ],
    },

    "Dental Materials": {
        "Phillips' Science of Dental Materials": [
            "Structure of Matter",
            "Physical Properties",
            "Biocompatibility",
            "Impression Materials",
            "Gypsum Products",
            "Dental Waxes",
            "Resin-Based Composites",
            "Dental Cements",
            "Dental Amalgam",
        ],
        "Craig's Restorative Dental Materials": [
            "Mechanical Properties",
            "Impression Materials",
            "Resins",
            "Composites",
            "Cements",
            "Metals",
            "Ceramics",
        ],
    },

    "Oral Surgery": {
        "Peterson's Principles of Oral and Maxillofacial Surgery": [
            "Patient Evaluation",
            "Exodontia",
            "Impacted Teeth",
            "Infections",
            "Cysts",
            "Trauma",
            "Preprosthetic Surgery",
            "Implant Surgery",
        ],
        "Malamed's Handbook of Local Anesthesia": [
            "Pain and Anxiety",
            "Local Anesthetic Drugs",
            "Syringes and Needles",
            "Maxillary Anesthesia",
            "Mandibular Anesthesia",
            "Complications",
            "Special Patients",
        ],
    },

    "Radiology": {
        "White and Pharoah's Oral Radiology": [
            "Radiographic Principles",
            "Intraoral Radiography",
            "Panoramic Radiography",
            "Digital Imaging",
            "Radiographic Anatomy",
            "Caries",
            "Periodontal Disease",
            "Periapical Lesions",
            "Cysts",
            "Tumors",
            "CBCT",
        ],
        "Langlais' Diagnostic Imaging of the Jaws": [
            "Radiographic Anatomy",
            "Radiolucent Lesions",
            "Radiopaque Lesions",
            "Mixed Lesions",
            "Cysts",
            "Tumors",
            "Jaw Diseases",
        ],
    },
}


# ============================================================
# SEARCH ALIASES & CEPH TYPES
# ============================================================

REFERENCE_ALIASES = {
    "caries": "Endodontics",
    "dental caries": "Endodontics",
    "rct": "Endodontics",
    "root canal": "Endodontics",
    "pulp": "Endodontics",

    "gum disease": "Periodontics",
    "periodontal": "Periodontics",
    "periodontitis": "Periodontics",
    "gingivitis": "Periodontics",
    "scaling": "Periodontics",

    "cpitn": "Public Health Dentistry",

    "opg": "Radiology",
    "iopa": "Radiology",
    "bitewing": "Radiology",
    "occlusal": "Radiology",
    "radiograph": "Radiology",
    "cbct": "Radiology",

    "ceph": "Orthodontics",
    "cephalometric": "Orthodontics",
    "deep bite": "Orthodontics",
    "open bite": "Orthodontics",
    "malocclusion": "Orthodontics",
    "leeway space": "Orthodontics",
    "functional appliance": "Orthodontics",

    "pedo": "Pedodontics",
    "paedo": "Pedodontics",
    "pediatric": "Pedodontics",
    "child dentistry": "Pedodontics",

    "prostho": "Prosthodontics",
    "denture": "Prosthodontics",
    "complete denture": "Prosthodontics",
    "partial denture": "Prosthodontics",

    "surgery": "Oral Surgery",
    "extraction": "Oral Surgery",
    "impacted tooth": "Oral Surgery",
    "local anesthesia": "Oral Surgery",

    "oral ulcer": "Oral Medicine",
    "white lesion": "Oral Medicine",
    "red lesion": "Oral Medicine",

    "oral pathology": "Oral Pathology",
    "pathology": "Oral Pathology",

    "dmft": "Public Health Dentistry",
    "ohis": "Public Health Dentistry",
    "epidemiology": "Public Health Dentistry",
    "bias": "Public Health Dentistry",
    "randomized controlled trial": "Public Health Dentistry",
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
            if any(
                search in chapter.lower()
                for chapter in chapters
            ):
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

            if query in chapter.lower():
                results.append((book, chapter))
                continue

            words = [
                word
                for word in query.split()
                if len(word) > 3
            ]

            if any(
                word in chapter.lower()
                for word in words
            ):
                results.append((book, chapter))

    return results


# ============================================================
# DIGITAL TEXTBOOK LIBRARY
# ============================================================

def textbook_library():

    st.markdown("### 📚 Pocket Dentistry Digital Library")

    st.caption(
        "Find the relevant BDS subject, textbook and chapter instantly."
    )

    search = st.text_input(
        "🔎 Search topic",
        placeholder=(
            "Try: Deep bite, CPITN, caries, oral ulcer, "
            "periapical lesion, complete denture..."
        ),
        key="digital_library_search",
    )

    default_subject = find_subject(search)

    subjects = list(TEXTBOOK_LIBRARY.keys())

    default_index = (
        subjects.index(default_subject)
        if default_subject in subjects
        else 0
    )

    selected_subject = st.selectbox(
        "📚 Select subject",
        subjects,
        index=default_index,
        key="digital_library_subject",
    )

    st.session_state.selected_subject = selected_subject

    books = TEXTBOOK_LIBRARY[selected_subject]

    # --------------------------------------------------------
    # SEARCH RESULTS
    # --------------------------------------------------------

    if search.strip():

        st.markdown(
            f"#### 🔍 Search results for: **{search}**"
        )

        relevant = find_relevant_chapters(
            search,
            selected_subject,
        )

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

            st.info(
                "No exact chapter match found. "
                "You can still ask Pocket Dentistry about the topic."
            )

    # --------------------------------------------------------
    # TEXTBOOK
    # --------------------------------------------------------

    st.markdown("#### 📕 Available Textbooks")

    selected_book = st.selectbox(
        "Select textbook",
        list(books.keys()),
        key="digital_library_book",
    )

    st.session_state.selected_book = selected_book

    st.markdown(
        f"""
        <div class="book-card">
        <div class="library-title">📕 {selected_book}</div>
        <small>
        Use the chapter list below for quick topic navigation.
        </small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # CHAPTER
    # --------------------------------------------------------

    st.markdown("#### 📑 Chapters / Topics")

    chapters = books[selected_book]

    chapter_options = ["Select a chapter"] + chapters

    selected_chapter = st.selectbox(
        "Choose chapter",
        chapter_options,
        key=f"chapter_{selected_book}",
    )

    if selected_chapter != "Select a chapter":

        st.session_state.selected_chapter = selected_chapter

        st.success(
            f"Selected chapter: {selected_chapter}"
        )

        # ----------------------------------------------------
        # ASK TEXTBOOK
        # ----------------------------------------------------

        st.markdown("#### 🤖 Ask About This Chapter")

        question = st.text_area(
            "What do you want to understand?",
            placeholder=(
                "Example: Explain this chapter in simple "
                "BDS exam-oriented language."
            ),
            key=f"question_{selected_book}_{selected_chapter}",
        )

        if st.button(
            "🤖 Ask the Textbook",
            type="primary",
            use_container_width=True,
        ):

            if not question.strip():

                st.warning(
                    "Enter a question first."
                )

            else:

                with st.spinner(
                    "Preparing textbook-oriented explanation..."
                ):

                    try:

                        prompt = f"""
You are Pocket Dentistry, a BDS educational assistant.

The student is referring to:

Subject:
{selected_subject}

Textbook:
{selected_book}

Chapter/topic:
{selected_chapter}

Student question:
{question}

Provide a clear BDS-level educational explanation.

Use this structure where appropriate:

1. Definition
2. Etiology / causes
3. Classification
4. Pathogenesis
5. Clinical features
6. Diagnosis / important diagnostic points
7. Management principles
8. Important examination points
9. Viva questions and answers

Keep the explanation educational and exam-oriented.

Do not claim that you directly accessed the copyrighted textbook.
Summarize established dental knowledge instead.
"""

                        answer = run_text_ai(prompt)

                        st.session_state.library_answer = answer

                    except Exception as exc:

                        st.session_state.library_answer = ""

                        show_ai_error(
                            exc,
                            "Textbook AI response failed",
                        )

        if st.session_state.library_answer:

            st.markdown("---")

            st.markdown(
                "### 📚 Pocket Dentistry Explanation"
            )

            st.markdown(
                st.session_state.library_answer
            )


# ============================================================
# SAFETY RULES & RADIOGRAPH PROMPTS
# ============================================================

COMMON_SAFETY_RULES = """
You are Pocket Dentistry, an AI-assisted dental learning and
clinical decision-support system.

CORE SAFETY PRINCIPLE:
Do good for the patient and never cause harm.

Important rules:
- Analyze only information actually provided.
- Never invent radiographic findings.
- Never invent tooth numbers.
- Clearly state uncertainty.
- If an image or feature cannot be assessed, say so.
- Do not present AI output as a definitive diagnosis.
- Final diagnosis and treatment decisions must be made by a
  qualified dental professional.
"""


RADIOGRAPH_PROMPTS = {

    "IOPA":
        COMMON_SAFETY_RULES +
        """
Analyze the uploaded IOPA radiograph for:

1. Image quality
2. Visible teeth and supporting structures
3. Dental caries
4. Restorations
5. Periodontal bone levels
6. Periapical region
7. Root morphology where visible
8. Other obvious radiographic findings
9. Provisional radiographic impression
10. Uncertainty / limitations

Only report findings that are actually visible.
""",

    "OPG":
        COMMON_SAFETY_RULES +
        """
Analyze the uploaded OPG panoramic radiograph for:

1. Image quality
2. Dentition
3. Missing teeth
4. Impacted teeth
5. Erupting teeth
6. Periodontal bone levels
7. Periapical regions
8. Mandible and maxilla
9. Maxillary sinuses where visible
10. Condyles where visible
11. Obvious radiographic lesions
12. Provisional radiographic impression
13. Uncertainty / limitations
""",

    "Bitewing":
        COMMON_SAFETY_RULES +
        """
Analyze the uploaded bitewing radiograph focusing on:

1. Image quality
2. Interproximal caries
3. Occlusal caries where visible
4. Restorations
5. Recurrent caries where visible
6. Alveolar crest bone levels
7. Other visible findings
8. Provisional radiographic impression
9. Uncertainty / limitations
""",

    "Occlusal":
        COMMON_SAFETY_RULES +
        """
Analyze the uploaded occlusal radiograph for:

1. Image quality
2. Teeth
3. Tooth development
4. Impacted teeth
5. Jaw structures
6. Cortical boundaries where visible
7. Obvious radiopaque/radiolucent abnormalities
8. Provisional radiographic impression
9. Uncertainty / limitations
""",

    "Facial Radiograph":
        COMMON_SAFETY_RULES +
        """
Analyze the uploaded facial radiograph for:

1. Image quality
2. Skeletal alignment
3. Structural continuity
4. Obvious cortical disruption
5. Obvious fracture-related findings if visible
6. Other significant visible abnormalities
7. Provisional radiographic impression
8. Uncertainty / limitations

Do not diagnose a fracture unless supported by visible findings.
""",
}


# ============================================================
# HOME SCREEN
# ============================================================

def show_home():

    st.markdown(
        '<div class="hero-title">🦷 Pocket Dentistry</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="hero-subtitle">'
        'AI-Powered Dental Learning & Clinical Decision-Support Platform'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="mode-card">
        <h3>🎓 Student Mode</h3>
        <p>
        Learn dental topics, prepare university answers,
        practice quizzes and access the Pocket Dentistry
        Digital Textbook Library.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🎓 Enter Student Mode",
        use_container_width=True,
    ):

        st.session_state.mode = "student"
        st.rerun()

    st.markdown(
        """
        <div class="mode-card doctor">
        <h3>🩺 Doctor Mode</h3>
        <p>
        Radiographic AI with Scale Calibration,
        Cephalometric Analysis selection, professional
        Soft-Tissue clinical reasoning workflow and
        clinical decision support.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🩺 Enter Doctor Mode",
        use_container_width=True,
    ):

        st.session_state.mode = "doctor"
        st.rerun()

    st.markdown("---")

    st.markdown(
        """
        <div class="safety-box">
        <b>🛡️ Safety Principle</b><br>
        Pocket Dentistry provides AI-assisted educational
        information and provisional radiographic assessment
        inside a secure web interface.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MODE HEADER
# ============================================================

def show_mode_header(title, icon):

    left, right = st.columns([1, 5])

    with left:

        if st.button(
            "← Home",
            use_container_width=True,
        ):

            st.session_state.mode = None
            st.rerun()

    with right:

        st.markdown(
            f"## {icon} {title}"
        )


# ============================================================
# DAILY ANALYSIS LIMIT
# ============================================================

def can_analyze():

    return (
        st.session_state.analysis_count
        < DAILY_ANALYSIS_LIMIT
    )


def record_analysis():

    st.session_state.analysis_count += 1


def show_usage():

    remaining = (
        DAILY_ANALYSIS_LIMIT
        - st.session_state.analysis_count
    )

    st.caption(
        f"AI analyses remaining today: "
        f"{remaining}/{DAILY_ANALYSIS_LIMIT}"
    )


# ============================================================
# RADIOGRAPH ANALYZER
# ============================================================

def radiograph_analyzer():

    st.markdown(
        "### 🩻 AI Radiographic Assessment"
    )

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

    # --------------------------------------------------------
    # CEPH
    # --------------------------------------------------------

    ceph_analysis_type = "Combined / All Analyses"

    if radiograph_type == "Lateral Cephalogram (Ceph)":

        ceph_analysis_type = st.selectbox(
            "Select Cephalometric Analysis Type",
            CEPH_ANALYSES,
        )

    # --------------------------------------------------------
    # CALIBRATION
    # --------------------------------------------------------

    st.markdown(
        "#### 📏 Scale Calibration Settings"
    )

    calibration_mode = st.radio(
        "Select Scale Calibration Mode",
        [
            "🤖 Auto-Calculate / AI Estimation",
            "✏️ Enter Known Calibration Scale (mm/pixel)",
        ],
        key="calibration_mode_selector",
    )

    scale_value_input = (
        "Auto-estimated by AI based on anatomical proportions"
    )

    if (
        calibration_mode
        == "✏️ Enter Known Calibration Scale (mm/pixel)"
    ):

        scale_value_input = st.text_input(
            "Enter known scale value",
            value="1.0 mm/pixel",
            key="known_scale_val",
        )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    uploaded = st.file_uploader(
        "📤 Upload dental radiograph",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
    )

    if uploaded:

        st.image(
            uploaded,
            caption="Uploaded radiograph",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    if radiograph_type == "Lateral Cephalogram (Ceph)":

        prompt = COMMON_SAFETY_RULES + f"""

Analyze the uploaded lateral cephalogram.

Selected cephalometric analysis:
{ceph_analysis_type}

Calibration Mode:
{calibration_mode}

Scale Setting:
{scale_value_input}

Provide:

1. Image Quality & Landmark Visibility
2. Skeletal Relationship
3. Dental Relationship
4. Vertical Pattern
5. Soft Tissue Profile
6. Relevant Cephalometric Measurements
7. Interpretation
8. Clinical Significance
9. Uncertainty & Limitations

Important:
Do not invent landmark positions or measurements.
If a landmark cannot be confidently identified,
state that it is unclear.
"""

    else:

        prompt = (
            RADIOGRAPH_PROMPTS.get(
                radiograph_type,
                COMMON_SAFETY_RULES,
            )
            + f"""

Calibration Mode:
{calibration_mode}

Scale Setting:
{scale_value_input}

If reliable scale information is unavailable,
clearly state that measurements are approximate
or cannot be reliably calculated.
"""
        )

    # --------------------------------------------------------
    # ANALYZE
    # --------------------------------------------------------

    if st.button(
        "🔍 Analyze X-ray",
        type="primary",
        use_container_width=True,
        disabled=not can_analyze(),
    ):

        if uploaded is None:

            st.warning(
                "Please upload a radiograph first."
            )

            return

        with st.spinner(
            "Analyzing radiograph..."
        ):

            try:

                report = run_image_analysis(
                    uploaded,
                    prompt,
                )

                record_analysis()

                st.session_state.last_report = report
                st.session_state.last_image_name = uploaded.name

                st.success(
                    "Analysis completed."
                )

                st.markdown(
                    "### 📋 AI Assessment Report"
                )

                st.markdown(report)

            except Exception as exc:

                show_ai_error(
                    exc,
                    "Radiographic AI analysis failed",
                )


# ============================================================
# STUDENT MODE
# ============================================================

def student_mode():

    show_mode_header(
        "Student Mode",
        "🎓",
    )

    tabs = st.tabs(
        [
            "📚 Learn",
            "📝 Exam / PYQ",
            "🧠 Quiz",
            "📖 Digital Library",
        ]
    )

    # ========================================================
    # LEARN
    # ========================================================

    with tabs[0]:

        st.markdown(
            "### 📚 Dental Topic Tutor"
        )

        topic = st.text_input(
            "Topic",
            placeholder=(
                "Example: CPITN, deep bite, oral ulcer"
            ),
            key="learn_topic",
        )

        if st.button(
            "📖 Teach Me",
            type="primary",
            use_container_width=True,
        ):

            if not topic.strip():

                st.warning(
                    "Enter a topic."
                )

            else:

                with st.spinner(
                    "Preparing BDS notes..."
                ):

                    try:

                        prompt = f"""
You are Pocket Dentistry,
a BDS dental education assistant.

Teach the following BDS topic:

TOPIC:
{topic}

Create an exam-oriented explanation suitable
for a BDS dental student.

Use this structure:

1. Definition
2. Introduction
3. Etiology / Causes
4. Classification
5. Pathogenesis / Mechanism
6. Clinical Features
7. Diagnosis
8. Important Investigations
9. Management principles
10. Important examination points
11. Short note points
12. Viva Questions and Answers

Use clear headings and bullet points.

If the topic is CPITN or another Public Health Dentistry
topic, include the important index components, criteria,
scoring/codes, uses, advantages, limitations and
important viva points.

Do not fabricate textbook quotations.
"""

                        res = run_text_ai(prompt)

                        st.markdown(
                            "### 📖 BDS Topic Notes"
                        )

                        st.markdown(res)

                    except Exception as exc:

                        show_ai_error(
                            exc,
                            "Dental Topic Tutor failed",
                        )

    # ========================================================
    # EXAM / PYQ
    # ========================================================

    with tabs[1]:

        st.markdown(
            "### 📝 University Exam Helper"
        )

        q = st.text_area(
            "Question",
            placeholder=(
                "Paste previous year question here."
            ),
            key="exam_q",
        )

        if st.button(
            "✍️ Generate Answer",
            type="primary",
            use_container_width=True,
        ):

            if not q.strip():

                st.warning(
                    "Enter the examination question first."
                )

            else:

                with st.spinner(
                    "Generating BDS examination answer..."
                ):

                    try:

                        prompt = f"""
You are Pocket Dentistry,
a BDS university examination assistant.

Question:
{q}

Write a structured BDS university examination
model answer.

Requirements:

- Start with a definition where appropriate.
- Use proper headings.
- Include classification where relevant.
- Include important clinical points.
- Include investigations where relevant.
- Include management principles where relevant.
- Highlight important points for scoring.
- Add a short viva section at the end.
- Keep terminology appropriate for BDS level.
- Avoid unsupported claims.
"""

                        res = run_text_ai(prompt)

                        st.markdown(
                            "### 📝 Model Answer"
                        )

                        st.markdown(res)

                    except Exception as exc:

                        show_ai_error(
                            exc,
                            "Exam Answer Generator failed",
                        )

    # ========================================================
    # QUIZ
    # ========================================================

    with tabs[2]:

        st.markdown(
            "### 🧠 Dental Quiz"
        )

        quiz_topic = st.text_input(
            "Quiz topic",
            placeholder=(
                "Example: Oral pathology"
            ),
            key="quiz_topic",
        )

        if st.button(
            "🎯 Generate Quiz",
            type="primary",
            use_container_width=True,
        ):

            if not quiz_topic.strip():

                st.warning(
                    "Enter a quiz topic."
                )

            else:

                with st.spinner(
                    "Creating BDS quiz..."
                ):

                    try:

                        prompt = f"""
You are Pocket Dentistry,
a BDS dental education assistant.

Create 5 BDS-level MCQs on:

{quiz_topic}

For every question provide:

A. Option
B. Option
C. Option
D. Option

Then provide:

Correct Answer:
Explanation:

Questions should test important
BDS examination concepts.
"""

                        res = run_text_ai(prompt)

                        st.markdown(
                            "### 🎯 BDS Quiz"
                        )

                        st.markdown(res)

                    except Exception as exc:

                        show_ai_error(
                            exc,
                            "Quiz Generator failed",
                        )

    # ========================================================
    # DIGITAL LIBRARY
    # ========================================================

    with tabs[3]:

        textbook_library()


# ============================================================
# DOCTOR MODE
# ============================================================

def doctor_mode():

    show_mode_header(
        "Doctor Mode",
        "🩺",
    )

    tabs = st.tabs(
        [
            "🩻 X-ray AI",
            "👄 Soft Tissue Reasoning",
            "📖 Clinical Library",
        ]
    )

    # ========================================================
    # X-RAY AI
    # ========================================================

    with tabs[0]:

        radiograph_analyzer()

    # ========================================================
    # SOFT TISSUE
    # ========================================================

    with tabs[1]:

        st.markdown(
            "### 👄 Advanced Professional Soft-Tissue Lesion Reasoning"
        )

        st.caption(
            "Provide comprehensive clinical parameters "
            "for professional diagnostic decision-support."
        )

        lesion_type = st.selectbox(
            "Primary Lesion Appearance",
            [
                "White lesion",
                "Red lesion",
                "Red-white lesion",
                "Ulcer",
                "Pigmented lesion",
                "Swelling / mass",
                "Vesicle / blister",
                "Other / unclear",
            ],
            key="doc_lesion_type",
        )

        col_st1, col_st2 = st.columns(2)

        with col_st1:

            lesion_duration = st.text_input(
                "Duration & Progression",
                placeholder=(
                    "e.g., 2 weeks, growing rapidly"
                ),
            )

            lesion_pain = st.selectbox(
                "Pain Status",
                [
                    "Painless",
                    "Mild discomfort",
                    "Painful / Burning",
                ],
            )

            lesion_scrapable = st.selectbox(
                "Scrapability (for white/red plaques)",
                [
                    "Not applicable",
                    "Scrapable (leaves erythematous base)",
                    "Non-scrapable",
                ],
            )

        with col_st2:

            lesion_site = st.text_input(
                "Anatomical Location",
                placeholder=(
                    "e.g., Left buccal mucosa, lateral tongue"
                ),
            )

            lesion_bleeding = st.selectbox(
                "Bleeding on Gentle Manipulation",
                [
                    "No",
                    "Yes",
                    "Not tested",
                ],
            )

            lesion_induration = st.selectbox(
                "Induration / Firmness on Palpation",
                [
                    "Soft / Fluctuant",
                    "Firm / Indurated",
                    "Not assessed",
                ],
            )

        additional_features = st.text_area(
            "Additional Clinical Findings & History",
            placeholder=(
                "Include habits, local trauma, medical history, "
                "lymphadenopathy, etc."
            ),
        )

        if st.button(
            "🧠 Build Professional Clinical Reasoning",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner(
                "Processing clinical reasoning..."
            ):

                try:

                    prompt = f"""
You are Pocket Dentistry Doctor Mode,
an advanced clinical decision-support system.

Analyze the following oral mucosal lesion case.

Lesion Type:
{lesion_type}

Anatomical Site:
{lesion_site}

Duration & Progression:
{lesion_duration}

Pain Status:
{lesion_pain}

Scrapability:
{lesion_scrapable}

Bleeding on Manipulation:
{lesion_bleeding}

Induration:
{lesion_induration}

Additional History / Findings:
{additional_features}

Provide a structured clinical decision-support report:

1. Problem Representation Summary

2. Differential Diagnoses
List reasonable differentials and explain
which clinical features support each.

3. Evidence Ledger
Supporting features:
Opposing / contradictory features:
Unknown / missing information:

4. Critical Missing Information

5. Highest-Value Next Clinical Question
Ask ONE clinical question that would most
help distinguish between the leading possibilities.

6. Potential Diagnostic Test
Mention an appropriate next diagnostic step
when clinically indicated.

7. Broad Management Considerations

8. Red Flags / Urgent Referral Considerations

Important:
Do not present the result as a definitive diagnosis.
Clinical examination and appropriate diagnostic
investigations are required.
"""

                    res = run_text_ai(prompt)

                    st.markdown(
                        "### 📋 Clinical Decision Support Report"
                    )

                    st.markdown(res)

                except Exception as exc:

                    show_ai_error(
                        exc,
                        "Clinical reasoning failed",
                    )

    # ========================================================
    # CLINICAL LIBRARY
    # ========================================================

    with tabs[2]:

        textbook_library()


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():

    with st.sidebar:

        st.markdown(
            "## 🦷 Pocket Dentistry"
        )

        if st.session_state.mode:

            st.write(
                f"Current mode: "
                f"**{st.session_state.mode.title()}**"
            )

        st.markdown("---")

        st.write(
            f"Daily analyses used: "
            f"{st.session_state.analysis_count}/"
            f"{DAILY_ANALYSIS_LIMIT}"
        )

        if st.button(
            "🏠 Return Home",
            use_container_width=True,
        ):

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
