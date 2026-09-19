import os
import json
import re
from datetime import date, datetime
from io import BytesIO
import base64
import html
import sqlite3
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
MODEL_NAME = "gemini-3.6-flash"


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
    .mode-card h3, .mode-card p {
        color: #004d40 !important;
    }
    .mode-card.doctor {
        border-color: #43a047;
        background: linear-gradient(135deg, #e8f5e9, #a5d6a7);
        color: #1b5e20;
    }
    .mode-card.doctor h3, .mode-card.doctor p {
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
# PERSISTENT CASE DATABASE (SQLite)
# ============================================================
DB_FILE = "pocket_dentistry.db"

def db_connect():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, patient_email TEXT,
        patient_name TEXT, case_type TEXT, image_name TEXT, report_title TEXT, report TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, context TEXT, rating TEXT, suggestion TEXT)""")
    conn.commit()
    return conn

def save_case(patient_email, patient_name, case_type, image_name, report_title, report):
    conn = db_connect()
    conn.execute("INSERT INTO cases(created_at,patient_email,patient_name,case_type,image_name,report_title,report) VALUES(?,?,?,?,?,?,?)",
                 (str(datetime.now()), patient_email, patient_name, case_type, image_name, report_title, report))
    conn.commit()
    conn.close()

def get_cases(patient_email=""):
    conn = db_connect()
    if patient_email.strip():
        rows = conn.execute("SELECT id,created_at,patient_email,patient_name,case_type,image_name,report_title,report FROM cases WHERE patient_email=? ORDER BY id DESC", (patient_email.strip(),)).fetchall()
    else:
        rows = conn.execute("SELECT id,created_at,patient_email,patient_name,case_type,image_name,report_title,report FROM cases ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return rows

def save_review_db(context, rating, suggestion):
    conn = db_connect()
    conn.execute("INSERT INTO reviews(created_at,context,rating,suggestion) VALUES(?,?,?,?)", (str(datetime.now()), context, rating, suggestion))
    conn.commit()
    conn.close()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "mode": None,
    "page": "home",
    "analysis_date": str(date.today()),
    "analysis_count": 0,
    "last_report": "",
    "last_image_name": "",
    "selected_book": None,
    "selected_subject": None,
    "selected_chapter": None,
    "library_search": "",
    "library_answer": "",
    "pyq_bank_result": "",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.analysis_date != str(date.today()):
    st.session_state.analysis_date = str(date.today())
    st.session_state.analysis_count = 0


# ============================================================
# GEMINI CLIENT & ERROR HANDLING
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
    try:
        return genai.Client(api_key=key)
    except Exception:
        return None

def friendly_ai_error(exc):
    error_text = str(exc).upper()
    if "401" in error_text or "UNAUTHENTICATED" in error_text:
        return "🔐 **Gemini authentication failed.** Please check `GEMINI_API_KEY`."
    if "403" in error_text or "PERMISSION_DENIED" in error_text:
        return "🚫 **Gemini API permission denied.** Check API access."
    if "404" in error_text or "NOT_FOUND" in error_text:
        return f"🔎 **Gemini model `{MODEL_NAME}` was not found or is unavailable.**"
    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text or "QUOTA" in error_text:
        return "⏳ **Gemini API quota or rate limit reached.** Please try again shortly."
    if "503" in error_text or "UNAVAILABLE" in error_text:
        return "🔄 **Gemini is temporarily unavailable.**"
    return "⚠️ **AI service error.** Please try again."

def show_ai_error(exc, title="AI request failed"):
    st.error(f"❌ {title}")
    st.markdown(friendly_ai_error(exc))

def image_to_part(uploaded_file):
    data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/png"
    return types.Part.from_bytes(data=data, mime_type=mime)

def run_image_analysis(uploaded_file, prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("Gemini API key not found or client could not be created.")
    image_part = image_to_part(uploaded_file)
    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt, image_part])
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("The AI returned an empty response.")
    return text

def run_text_ai(prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("Gemini API key not found or client could not be created.")
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("The AI returned an empty response.")
    return text


# ============================================================
# REPORT / EXPORT UTILITIES (Feature 4)
# ============================================================

def make_report_html(title, patient, report, image_name="", report_type="AI Report"):
    safe_report = html.escape(report or "").replace("\n", "<br>")
    safe_patient = html.escape(patient or "Not provided")
    safe_img = html.escape(image_name or "Not provided")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:850px;margin:40px auto;padding:20px;color:#17202a}}
h1{{color:#1e3d59}} .box{{padding:15px;border:1px solid #ddd;border-radius:10px;margin:12px 0}}
.disclaimer{{background:#fff8e1;padding:15px;border-left:5px solid #f0ad00}}
@media print{{.no-print{{display:none}}}}
</style></head><body>
<h1>🦷 Pocket Dentistry</h1><h2>{html.escape(title)}</h2>
<div class="box"><b>Target Subject / Topic:</b> {safe_patient}<br>
<b>Report type:</b> {html.escape(report_type)}<br>
<b>Date:</b> {date.today()}</div>
<div class="box"><h3>Content</h3>{safe_report}</div>
<button class="no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
</body></html>"""

def pdf_bytes(title, patient, report, image_name="", report_type="AI Report"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("PDTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=18)
        body = ParagraphStyle("PDBody", parent=styles["BodyText"], fontSize=9.5, leading=14)
        story = [Paragraph("Pocket Dentistry", title_style), Spacer(1, 12), Paragraph(html.escape(title or "Dental Report"), styles["Heading2"]),
               Paragraph(f"<b>Target Subject/Topic:</b> {html.escape(patient or 'Not provided')}<br/><b>Report type:</b> {html.escape(report_type)}<br/><b>Date:</b> {date.today()}", body), Spacer(1, 14)]
        for line in (report or "").split("\n"):
            if line.strip(): story += [Paragraph(html.escape(line.strip()), body), Spacer(1, 4)]
        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None

def show_export_controls(title, patient, report, image_name="", report_type="AI Report"):
    if not report: return
    st.markdown("### 📄 Save / Download / Print Options")
    doc = make_report_html(title, patient, report, image_name, report_type)
    st.download_button("🌐 Download HTML", doc, file_name="pocket_dentistry_document.html", mime="text/html", use_container_width=True)
    pdf = pdf_bytes(title, patient, report, image_name, report_type)
    if pdf:
        st.download_button("📄 Download PDF", pdf, file_name="pocket_dentistry_document.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.info("PDF engine unavailable; use HTML → Print → Save as PDF.")
    b64 = base64.b64encode(doc.encode()).decode()
    st.markdown(f'<a href="data:text/html;base64,{b64}" target="_blank">🖨️ Open printable report window</a>', unsafe_allow_html=True)


# ============================================================
# PATIENT GMAIL EXPORT (Feature 2)
# ============================================================

def send_report_email(patient_email, subject, body):
    import smtplib
    from email.message import EmailMessage
    host = st.secrets.get("SMTP_HOST", "")
    port = int(st.secrets.get("SMTP_PORT", 587))
    user = st.secrets.get("SMTP_USERNAME", "")
    password = st.secrets.get("SMTP_PASSWORD", "")
    sender = st.secrets.get("SMTP_FROM", user)
    if not all([host, user, password, sender]): 
        raise RuntimeError("SMTP email settings are not configured in st.secrets.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = patient_email
    msg.set_content(body)
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)

def patient_email_section(report, title="Dental Report", patient_name=""):
    with st.expander("📧 Send report to patient Gmail"):
        email = st.text_input("Patient Gmail address", key=f"mail_{title}")
        consent = st.checkbox("I confirm that the patient has consented to receiving this report by email.", key=f"consent_{title}")
        if st.button("📨 Send report", use_container_width=True, key=f"send_{title}"):
            if not email or "@" not in email: 
                st.warning("Enter a valid email address.")
            elif not consent: 
                st.warning("Patient consent is required.")
            else:
                try:
                    send_report_email(email, title, report)
                    st.success("Report successfully sent to patient Gmail.")
                except Exception as e:
                    st.error(f"Email could not be sent: {friendly_ai_error(e)}")


# ============================================================
# REVIEW & SUGGESTIONS SECTION (Feature 1)
# ============================================================

def review_section(context="report"):
    st.markdown("### ⭐ Review & Suggestions")
    rating = st.radio("How useful was this content/result?", ["👍 Useful", "😐 Partly useful", "👎 Not useful"], horizontal=True, key=f"rating_{context}")
    suggestion = st.text_area("Suggestion / improvement idea", key=f"suggestion_{context}", placeholder="Tell us what should be added or enhanced.")
    if st.button("Submit review & suggestions", key=f"reviewbtn_{context}", use_container_width=True):
        save_review_db(context, rating, suggestion)
        st.success("Thank you! Your review and suggestions have been successfully recorded.")


# ============================================================
# KUHS PREVIOUS YEAR QUESTION BANK ON SEARCHED TOPIC (New Feature)
# ============================================================

def kuhs_searched_topic_pyq_bank():
    st.markdown("### 📝 Previous Year Question Bank on Searched Topic")
    st.caption("Generate targeted Kerala University of Health Sciences (KUHS) past essay questions, short notes, and viva prompts mapped to your searched topic or digital library selection.")

    search_topic = st.text_input("Enter topic or subject for Question Bank generation", value=st.session_state.get("library_search", "Oral Pathology"), key="pyq_bank_topic")
    
    if st.button("🔨 Generate Previous Year Question Bank", type="primary", use_container_width=True):
        if not search_topic.strip():
            st.warning("Please enter a topic.")
        else:
            with st.spinner("Compiling KUHS university question bank and model answers..."):
                try:
                    prompt = f"""
You are Pocket Dentistry academic assistant specialized in Kerala University of Health Sciences (KUHS) BDS examinations (2012–2025).
Topic / Subject: {search_topic}

Generate a comprehensive Previous Year Question Bank layout containing:
1. Long Essay Questions (10 Marks) asked or expected in past university examinations.
2. Short Essay / Short Note Questions (5 Marks) with frequency indicators (e.g., repeated in 2021, 2023, 2025).
3. Viva Voce / Rapid-Fire Question Bank.
4. Strategic student suggestions and high-yield study focus areas for this topic.
"""
                    res = run_text_ai(prompt)
                    st.session_state.pyq_bank_result = res
                except Exception as exc:
                    show_ai_error(exc, "Question bank generation failed")

    if st.session_state.pyq_bank_result:
        st.markdown("---")
        st.markdown(f"### 📋 KUHS Question Bank: {search_topic}")
        st.markdown(st.session_state.pyq_bank_result)
        show_export_controls(f"KUHS Question Bank - {search_topic}", search_topic, st.session_state.pyq_bank_result, "", "Question Bank")
        patient_email_section(st.session_state.pyq_bank_result, f"Question Bank - {search_topic}", search_topic)
        review_section("pyq_bank")


# ============================================================
# INTRO TO DENTAL FAMILY (Feature 6)
# ============================================================

def intro_dental_family():
    st.markdown("## 🦷 Intro to Dental Family")
    st.write("Welcome to Pocket Dentistry — bridging undergraduate students and practicing clinicians.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎓 Student Hub")
        st.write("• KUHS University exam preparation & past questions\n• Targeted topic question banks & digital library\n• Case logs & quizzes")
        if st.button("Enter Student Mode", use_container_width=True, key="intro_student_btn"):
            st.session_state.mode = "student"
            st.session_state.page = "student"
            st.rerun()
    with c2:
        st.markdown("### 🩺 Doctor / Clinician Hub")
        st.write("• Radiographic AI with scale calibration & cephalometric analysis\n• Soft-tissue professional clinical reasoning workflow\n• Patient history & secure Gmail reporting")
        if st.button("Enter Doctor Mode", use_container_width=True, key="intro_doctor_btn"):
            st.session_state.mode = "doctor"
            st.rerun()
    st.markdown("### 🌱 Community Mission")
    st.write("Empowering dental learners and professionals with accurate decision-support tools.")


# ============================================================
# BDS DIGITAL TEXTBOOK DATABASE (All Subjects Included)
# ============================================================

TEXTBOOK_LIBRARY = {
    "Oral Pathology": {
        "Shafer's Textbook of Oral Pathology": [
            "Introduction to Oral Pathology", "Developmental Disturbances", "Dental Caries",
            "Pulp and Periapical Diseases", "Periodontal Diseases", "Cysts of the Oral Region",
            "Odontogenic Tumors", "Benign Tumors", "Malignant Tumors", "Diseases of Bone",
            "Diseases of Salivary Glands", "Oral Mucosal Diseases", "White Lesions",
            "Red and Pigmented Lesions", "Ulcers", "Infections"
        ],
        "Neville's Oral and Maxillofacial Pathology": [
            "Developmental Disorders", "Dental Caries", "Pulpal and Periapical Disease",
            "Periodontal Disease", "Cysts", "Odontogenic Tumors", "Bone Pathology",
            "Salivary Gland Pathology", "Oral Mucosal Disease", "White Lesions", "Ulcers", "Oral Cancer"
        ],
    },
    "Oral Medicine": {
        "Burket's Oral Medicine": [
            "Patient Evaluation", "Systemic Disease", "Oral Manifestations of Systemic Disease",
            "Ulcers", "White Lesions", "Red Lesions", "Pigmented Lesions", "Vesiculobullous Disorders",
            "Salivary Gland Disorders", "Temporomandibular Disorders", "Oral Cancer"
        ],
    },
    "Periodontics": {
        "Carranza's Clinical Periodontology": [
            "Periodontal Anatomy", "Periodontal Examination", "Classification of Periodontal Diseases",
            "Gingivitis", "Periodontitis", "Periodontal Pocket", "Bone Loss", "Plaque and Calculus",
            "Periodontal Instrumentation", "Scaling and Root Planing", "Periodontal Surgery", "Maintenance Therapy"
        ],
    },
    "Endodontics": {
        "Cohen's Pathways of the Pulp": [
            "Pulp Biology", "Diagnosis", "Pulpal Disease", "Periapical Disease", "Root Canal Anatomy",
            "Access Cavity", "Cleaning and Shaping", "Obturation", "Endodontic Emergencies", "Trauma", "Endodontic Surgery"
        ],
    },
    "Prosthodontics": {
        "Nallaswamy - Textbook of Prosthodontics": [
            "Diagnosis and Treatment Planning", "Complete Dentures", "Impression Making",
            "Jaw Relations", "Tooth Selection", "Denture Try-in", "Denture Processing",
            "Removable Partial Dentures", "Fixed Prosthodontics"
        ],
    },
    "Orthodontics": {
        "Proffit - Contemporary Orthodontics": [
            "Growth and Development", "Development of Dentition", "Malocclusion", "Diagnosis",
            "Treatment Planning", "Biomechanics", "Fixed Appliances", "Functional Appliances",
            "Orthodontic Retention", "Deep Bite", "Open Bite", "Class II Malocclusion", "Class III Malocclusion"
        ],
    },
    "Pedodontics": {
        "Nikhil Marwah - Textbook of Pediatric Dentistry": [
            "Growth and Development", "Preventive Dentistry", "Dental Caries", "Pulp Therapy",
            "Trauma", "Space Maintainers", "Behavior Management", "Interceptive Orthodontics"
        ],
    },
    "Public Health Dentistry": {
        "Soben Peter - Essentials of Preventive and Community Dentistry": [
            "Introduction to Public Health", "Health and Disease", "Epidemiology", "Study Designs",
            "Bias", "Screening", "Biostatistics", "Indices", "DMFT", "OHI-S", "CPITN",
            "Preventive Dentistry", "Community Dental Programs", "Health Education"
        ],
    },
    "Dental Materials": {
        "Phillips' Science of Dental Materials": [
            "Structure of Matter", "Physical Properties", "Biocompatibility", "Impression Materials",
            "Gypsum Products", "Dental Waxes", "Resin-Based Composites", "Dental Cements", "Dental Amalgam"
        ],
    },
    "Oral Surgery": {
        "Malamed's Handbook of Local Anesthesia": [
            "Pain and Anxiety", "Local Anesthetic Drugs", "Syringes and Needles",
            "Maxillary Anesthesia", "Mandibular Anesthesia", "Complications", "Special Patients"
        ],
    },
    "Radiology": {
        "White and Pharoah's Oral Radiology": [
            "Radiographic Principles", "Intraoral Radiography", "Panoramic Radiography",
            "Digital Imaging", "Radiographic Anatomy", "Caries", "Periodontal Disease",
            "Periapical Lesions", "Cysts", "Tumors", "CBCT"
        ],
    },
}

REFERENCE_ALIASES = {
    "caries": "Endodontics", "rct": "Endodontics", "pulp": "Endodontics",
    "gum disease": "Periodontics", "periodontal": "Periodontics", "periodontitis": "Periodontics",
    "cpitn": "Public Health Dentistry", "dmft": "Public Health Dentistry",
    "opg": "Radiology", "iopa": "Radiology", "bitewing": "Radiology", "ceph": "Orthodontics",
    "pedo": "Pedodontics", "prostho": "Prosthodontics", "surgery": "Oral Surgery",
    "ulcer": "Oral Medicine", "pathology": "Oral Pathology"
}

CEPH_ANALYSES = [
    "Steiner Analysis", "Downs Analysis", "McNamara Analysis",
    "Tweed Analysis", "Wits Appraisal", "Jarabak Analysis",
    "Soft Tissue Profile Analysis", "Combined / All Analyses"
]

def find_subject(search_text):
    if not search_text: return "Oral Pathology"
    search = search_text.strip().lower()
    if search in REFERENCE_ALIASES: return REFERENCE_ALIASES[search]
    for alias, subject in REFERENCE_ALIASES.items():
        if alias in search: return subject
    for subject in TEXTBOOK_LIBRARY:
        if subject.lower() in search: return subject
    return "Oral Pathology"

def find_relevant_chapters(search_text, subject):
    results = []
    if not search_text: return results
    query = search_text.lower().strip()
    books = TEXTBOOK_LIBRARY.get(subject, {})
    for book, chapters in books.items():
        for chapter in chapters:
            if query in chapter.lower():
                results.append((book, chapter))
    return results

def textbook_library():
    st.markdown("### 📚 Pocket Dentistry Digital Library")
    search = st.text_input("🔎 Search topic", placeholder="Try: Deep bite, CPITN, caries, oral ulcer...", key="digital_library_search")
    st.session_state.library_search = search
    
    default_subject = find_subject(search)
    subjects = list(TEXTBOOK_LIBRARY.keys())
    default_index = subjects.index(default_subject) if default_subject in subjects else 0
    selected_subject = st.selectbox("📚 Select subject", subjects, index=default_index, key="digital_library_subject")
    books = TEXTBOOK_LIBRARY[selected_subject]

    if search.strip():
        st.markdown(f"#### 🔍 Search results for: **{search}**")
        relevant = find_relevant_chapters(search, selected_subject)
        if relevant:
            for book, chapter in relevant[:10]:
                st.markdown(f'<div class="chapter-card">📑 <b>{chapter}</b><br><small>📕 {book}</small></div>', unsafe_allow_html=True)

    st.markdown("#### 📕 Available Textbooks")
    selected_book = st.selectbox("Select textbook", list(books.keys()), key="digital_library_book")
    chapters = books[selected_book]
    selected_chapter = st.selectbox("Choose chapter", ["Select a chapter"] + chapters, key=f"chapter_{selected_book}")

    if selected_chapter != "Select a chapter":
        st.success(f"Selected chapter: {selected_chapter}")
        question = st.text_area("What do you want to understand?", key=f"question_{selected_book}_{selected_chapter}")
        if st.button("🤖 Ask the Textbook", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("Enter a question first.")
            else:
                with st.spinner("Preparing textbook-oriented explanation..."):
                    try:
                        prompt = f"""You are Pocket Dentistry, a BDS educational assistant.
Subject: {selected_subject}
Textbook: {selected_book}
Chapter/topic: {selected_chapter}
Student question: {question}
Provide a clear BDS-level exam-oriented explanation with definition, etiology, classification, clinical features, and viva points."""
                        st.session_state.library_answer = run_text_ai(prompt)
                    except Exception as exc:
                        st.session_state.library_answer = ""
                        show_ai_error(exc, "Textbook AI response failed")

        if st.session_state.library_answer:
            st.markdown("---")
            st.markdown("### 📚 Pocket Dentistry Explanation")
            st.markdown(st.session_state.library_answer)
            show_export_controls(f"Explanation - {selected_chapter}", selected_subject, st.session_state.library_answer, "", "Library Explanation")
            patient_email_section(st.session_state.library_answer, f"Explanation - {selected_chapter}", selected_subject)
            review_section("library")


# ============================================================
# SAFETY RULES & RADIOGRAPH PROMPTS
# ============================================================

COMMON_SAFETY_RULES = """
You are Pocket Dentistry, an AI-assisted dental learning and clinical decision-support system.
CORE SAFETY PRINCIPLE: Do good for the patient and never cause harm.
- Analyze only information provided.
- Never invent radiographic findings or tooth numbers.
- Clearly state uncertainty. Do not provide a definitive diagnosis.
"""

RADIOGRAPH_PROMPTS = {
    "IOPA": COMMON_SAFETY_RULES + "\nAnalyze IOPA radiograph for image quality, caries, restorations, bone levels, and periapical status.",
    "OPG": COMMON_SAFETY_RULES + "\nAnalyze OPG panoramic radiograph for dentition, missing/impacted teeth, bone levels, sinuses, and condyles.",
    "Bitewing": COMMON_SAFETY_RULES + "\nAnalyze bitewing radiograph for interproximal caries, restorations, and alveolar crest levels.",
    "Occlusal": COMMON_SAFETY_RULES + "\nAnalyze occlusal radiograph for teeth, development, impacted teeth, and jaw structures.",
    "Facial Radiograph": COMMON_SAFETY_RULES + "\nAnalyze facial radiograph for skeletal alignment, continuity, and obvious fracture findings.",
}


# ============================================================
# RADIOGRAPH ANALYZER
# ============================================================

def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")
    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    st.caption(f"AI analyses remaining today: {remaining}/{DAILY_ANALYSIS_LIMIT}")
    
    radiograph_type = st.selectbox("Select radiograph type", ["IOPA", "OPG", "Bitewing", "Occlusal", "Facial Radiograph", "Lateral Cephalogram (Ceph)"])
    ceph_analysis_type = st.selectbox("Select Cephalometric Analysis Type", CEPH_ANALYSES) if radiograph_type == "Lateral Cephalogram (Ceph)" else ""

    st.markdown("#### 📏 Scale Calibration Settings")
    calibration_mode = st.radio("Select Scale Calibration Mode", ["🤖 Auto-Calculate / AI Estimation", "✏️ Enter Known Calibration Scale (mm/pixel)"])
    scale_value_input = st.text_input("Enter known scale value", value="1.0 mm/pixel") if "Enter" in calibration_mode else "Auto-estimated"

    uploaded = st.file_uploader("📤 Upload dental radiograph", type=["png", "jpg", "jpeg", "webp"])
    if uploaded: st.image(uploaded, caption="Uploaded radiograph", use_container_width=True)

    patient_name = st.text_input("Patient / Case identifier", key="xray_patient_name")
    patient_email = st.text_input("Patient Gmail / email (optional)", key="xray_patient_email", placeholder="patient@gmail.com")

    if st.button("🔍 Analyze X-ray", type="primary", use_container_width=True, disabled=st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT):
        if uploaded is None:
            st.warning("Please upload a radiograph first.")
            return
        with st.spinner("Analyzing radiograph..."):
            try:
                prompt = COMMON_SAFETY_RULES + f"\nRadiograph: {radiograph_type}\nCeph: {ceph_analysis_type}\nScale: {scale_value_input}"
                report = run_image_analysis(uploaded, prompt)
                st.session_state.analysis_count += 1
                st.session_state.last_report = report
                st.session_state.last_image_name = uploaded.name
                
                save_case(patient_email, patient_name, radiograph_type, uploaded.name, f"{radiograph_type} Assessment", report)

                st.success("Analysis completed.")
                st.markdown("### 📋 AI Assessment Report")
                st.markdown(report)
                show_export_controls(f"{radiograph_type} Assessment", patient_name, report, uploaded.name, "Radiographic AI")
                patient_email_section(report, f"{radiograph_type} Report", patient_name)
                review_section("radiograph")
            except Exception as exc:
                show_ai_error(exc, "Radiographic AI analysis failed")


# ============================================================
# SOFT TISSUE UPLOAD & CLINICAL REASONING (Feature 5)
# ============================================================

def soft_tissue_section():
    st.markdown("### 👄 Soft-Tissue Clinical Reasoning & Image Upload")
    st.caption("Upload clinical photographs of oral mucosal lesions for professional reasoning support.")
    
    patient_name = st.text_input("Patient / Case identifier", key="soft_patient_name")
    patient_email = st.text_input("Patient Gmail / email (optional)", key="soft_patient_email", placeholder="patient@gmail.com")
    
    soft_image = st.file_uploader("📷 Upload intraoral/extraoral clinical photograph", type=["png", "jpg", "jpeg", "webp"], key="soft_tissue_file_uploader")
    if soft_image:
        st.image(soft_image, caption="Uploaded soft-tissue photograph", use_container_width=True)

    lesion_type = st.selectbox("Primary Lesion Appearance", ["White lesion", "Red lesion", "Red-white lesion", "Ulcer", "Pigmented lesion", "Swelling / mass", "Vesicle / blister", "Other / unclear"])
    lesion_site = st.text_input("Anatomical Location", placeholder="e.g., Left buccal mucosa")
    lesion_duration = st.text_input("Duration & Progression", placeholder="e.g., 2 weeks")
    lesion_pain = st.selectbox("Pain Status", ["Painless", "Mild discomfort", "Painful / Burning"])
    lesion_scrapable = st.selectbox("Scrapability", ["Not applicable", "Scrapable", "Non-scrapable"])
    additional_features = st.text_area("Additional Clinical Findings & History")

    if st.button("🧠 Build Professional Clinical Reasoning", type="primary", use_container_width=True):
        with st.spinner("Processing clinical reasoning..."):
            try:
                prompt = f"""{COMMON_SAFETY_RULES}
Analyze this oral mucosal lesion case:
Appearance: {lesion_type}
Site: {lesion_site}
Duration: {lesion_duration}
Pain: {lesion_pain}
Scrapability: {lesion_scrapable}
Additional History: {additional_features}
Provide: Problem representation, Differential diagnoses, Evidence ledger, Critical missing info, Next clinical question, Diagnostic test, Management considerations, Red flags."""
                
                if soft_image:
                    report = run_image_analysis(soft_image, prompt)
                    img_name = soft_image.name
                else:
                    report = run_text_ai(prompt)
                    img_name = "None"

                save_case(patient_email, patient_name, "Soft Tissue", img_name, "Soft-Tissue Clinical Reasoning", report)

                st.markdown("### 📋 Clinical Decision Support Report")
                st.markdown(report)
                show_export_controls("Soft-Tissue Clinical Reasoning", patient_name, report, img_name, "Clinical Decision Support")
                patient_email_section(report, "Soft-Tissue Clinical Report", patient_name)
                review_section("soft_tissue")
            except Exception as exc:
                show_ai_error(exc, "Soft-tissue reasoning failed")


# ============================================================
# STUDENT MODE
# ============================================================

def student_mode():
    show_mode_header("Student Mode", "🎓")
    tabs = st.tabs(["📚 Learn", "📝 Exam / PYQ Bank", "🧠 Quiz", "📖 Digital Library"])

    with tabs[0]:
        st.markdown("### 📚 Dental Topic Tutor")
        topic = st.text_input("Topic", placeholder="Example: CPITN, deep bite, oral ulcer", key="learn_topic")
        if st.button("📖 Teach Me", type="primary", use_container_width=True):
            if not topic.strip():
                st.warning("Enter a topic.")
            else:
                with st.spinner("Preparing BDS notes..."):
                    try:
                        prompt = f"You are Pocket Dentistry, a BDS education assistant. Teach BDS topic: {topic}. Give definition, etiology, classification, clinical features, diagnosis, management, and viva questions."
                        res = run_text_ai(prompt)
                        st.markdown("### 📖 BDS Topic Notes")
                        st.markdown(res)
                        show_export_controls(f"Topic Notes - {topic}", topic, res, "", "Topic Notes")
                        patient_email_section(res, f"Notes - {topic}", topic)
                        review_section("topic_tutor")
                    except Exception as exc:
                        show_ai_error(exc, "Dental Topic Tutor failed")

    with tabs[1]:
        kuhs_searched_topic_pyq_bank()
        st.markdown("---")
        st.markdown("### 📝 University Exam Helper")
        q = st.text_area("Question", placeholder="Paste previous year question here.", key="exam_q")
        if st.button("✍️ Generate Answer", type="primary", use_container_width=True):
            if not q.strip():
                st.warning("Enter the examination question first.")
            else:
                with st.spinner("Generating BDS examination answer..."):
                    try:
                        prompt = f"You are Pocket Dentistry, a BDS university examination assistant. Write a structured BDS model answer for:\n{q}"
                        res = run_text_ai(prompt)
                        st.markdown("### 📝 Model Answer")
                        st.markdown(res)
                        show_export_controls("BDS Exam Model Answer", "", res, "", "Exam Answer")
                        patient_email_section(res, "Model Answer", "")
                        review_section("exam_answer")
                    except Exception as exc:
                        show_ai_error(exc, "Exam Answer Generator failed")

    with tabs[2]:
        st.markdown("### 🧠 Dental Quiz")
        quiz_topic = st.text_input("Quiz topic", placeholder="Example: Oral pathology", key="quiz_topic")
        if st.button("🎯 Generate Quiz", type="primary", use_container_width=True) and quiz_topic.strip():
            with st.spinner("Creating BDS quiz..."):
                try:
                    res = run_text_ai(f"Create 5 BDS-level MCQs on {quiz_topic} with options, correct answer, and explanation.")
                    st.markdown("### 🎯 BDS Quiz")
                    st.markdown(res)
                    show_export_controls(f"Quiz - {quiz_topic}", quiz_topic, res, "", "Quiz")
                    review_section("quiz")
                except Exception as exc:
                    show_ai_error(exc, "Quiz Generator failed")

    with tabs[3]:
        textbook_library()


# ============================================================
# DOCTOR MODE
# ============================================================

def doctor_mode():
    show_mode_header("Doctor Mode", "🩺")
    tabs = st.tabs(["🩻 X-ray AI", "👄 Soft Tissue Reasoning", "📖 Clinical Library", "📜 Patient History & Saved Cases"])

    with tabs[0]:
        radiograph_analyzer()

    with tabs[1]:
        soft_tissue_section()

    with tabs[2]:
        textbook_library()

    with tabs[3]:
        st.markdown("### 📜 Saved Patient / Case History")
        search_email = st.text_input("Search patient email", key="history_email", placeholder="patient@gmail.com")
        rows = get_cases(search_email)
        if not rows:
            st.info("No saved cases found.")
        else:
            st.success(f"{len(rows)} saved case(s) found.")
            for row in rows:
                cid, created, email, name, ctype, img, title, report = row
                with st.expander(f"{created} — {name or 'Case'} — {ctype or 'Report'}"):
                    st.write(f"**Patient:** {name or 'Not provided'}")
                    st.write(f"**Email:** {email or 'Not provided'}")
                    st.write(f"**Image:** {img or 'Not provided'}")
                    st.markdown(report)
                    show_export_controls(title or "Saved Case", name or "", report, img or "", ctype or "Saved report")
                    if email: 
                        patient_email_section(report, f"Saved Case {cid}", name or "")


# ============================================================
# HOME SCREEN
# ============================================================

def show_home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">AI-Powered Dental Learning & Clinical Decision-Support Platform</div>', unsafe_allow_html=True)
    
    if st.button("🦷 Intro to Dental Family", use_container_width=True):
        st.session_state.page = "intro"
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="mode-card"><h3>🎓 Student Mode</h3><p>Learn dental topics, prepare university answers, practice quizzes, KUHS PYQs and Digital Library.</p></div>', unsafe_allow_html=True)
        if st.button("🎓 Enter Student Mode", use_container_width=True):
            st.session_state.mode = "student"
            st.session_state.page = "student"
            st.rerun()
    with c2:
        st.markdown('<div class="mode-card doctor"><h3>🩺 Doctor Mode</h3><p>Radiographic AI, soft-tissue reasoning with uploads, case history and secure patient Gmail reports.</p></div>', unsafe_allow_html=True)
        if st.button("🩺 Enter Doctor Mode", use_container_width=True):
            st.session_state.mode = "doctor"
            st.session_state.page = "doctor"
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="safety-box"><b>🛡️ Safety Principle</b><br>Pocket Dentistry provides AI-assisted educational information and clinical decision support.</div>', unsafe_allow_html=True)


# ============================================================
# MODE HEADER & SIDEBAR
# ============================================================

def show_mode_header(title, icon):
    left, right = st.columns([1, 5])
    with left:
        if st.button("← Home", use_container_width=True):
            st.session_state.mode = None
            st.session_state.page = "home"
            st.rerun()
    with right:
        st.markdown(f"## {icon} {title}")

def sidebar():
    with st.sidebar:
        st.markdown("## 🦷 Pocket Dentistry")
        if st.session_state.mode:
            st.write(f"Current mode: **{st.session_state.mode.title()}**")
        st.markdown("---")
        st.write(f"Daily analyses used: {st.session_state.analysis_count}/{DAILY_ANALYSIS_LIMIT}")
        if st.button("🏠 Return Home", use_container_width=True):
            st.session_state.mode = None
            st.session_state.page = "home"
            st.rerun()
        if st.button("🦷 Intro to Dental Family", use_container_width=True):
            st.session_state.page = "intro"
            st.rerun()
        if st.button("📜 Patient History", use_container_width=True):
            st.session_state.mode = "doctor"
            st.session_state.page = "history"
            st.rerun()


# ============================================================
# RUN APP ROUTING
# ============================================================

sidebar()

if st.session_state.get("page") == "intro":
    intro_dental_family()
elif st.session_state.get("page") == "history":
    st.session_state.mode = "doctor"
    doctor_mode()
elif st.session_state.mode is None:
    show_home()
elif st.session_state.mode == "student":
    student_mode()
elif st.session_state.mode == "doctor":
    doctor_mode()
