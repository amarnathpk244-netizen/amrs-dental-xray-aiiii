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
# POCKET DENTISTRY & MEDICAL HUB
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
    .safety-box {
        padding: 1rem;
        border-radius: 15px;
        border-left: 5px solid #17b978;
        background: rgba(23,185,120,0.1);
        color: #1e3d59;
        margin-top: 1rem;
    }
    .chapter-card {
        padding: 0.8rem 1rem;
        border-radius: 12px;
        border: 1px solid #d0d7de;
        background: #f8fafb;
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
# PERSISTENT DATABASE (SQLite for Cases, Reviews & Practicals)
# ============================================================
DB_FILE = "pocket_dentistry.db"

def db_connect():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, patient_email TEXT,
        patient_name TEXT, case_type TEXT, image_name TEXT, report_title TEXT, report TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, context TEXT, rating TEXT, suggestion TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS practicals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, title TEXT, subject TEXT, description TEXT, file_name TEXT, file_type TEXT)""")
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

def save_practical_db(title, subject, description, file_name, file_type):
    conn = db_connect()
    conn.execute("INSERT INTO practicals(created_at,title,subject,description,file_name,file_type) VALUES(?,?,?,?,?,?)",
                 (str(datetime.now()), title, subject, description, file_name, file_type))
    conn.commit()
    conn.close()

def get_practicals():
    conn = db_connect()
    rows = conn.execute("SELECT id,created_at,title,subject,description,file_name,file_type FROM practicals ORDER BY id DESC").fetchall()
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
# REPORT / EXPORT & EMAIL UTILITIES
# ============================================================

def make_report_html(title, patient, report, report_type="AI Report"):
    safe_report = html.escape(report or "").replace("\n", "<br>")
    safe_patient = html.escape(patient or "Not provided")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:850px;margin:40px auto;padding:20px;color:#17202a}}
h1{{color:#1e3d59}} .box{{padding:15px;border:1px solid #ddd;border-radius:10px;margin:12px 0}}
@media print{{.no-print{{display:none}}}}
</style></head><body>
<h1>🦷 Pocket Dentistry & Medical Hub</h1><h2>{html.escape(title)}</h2>
<div class="box"><b>Target Subject / Topic:</b> {safe_patient}<br>
<b>Report type:</b> {html.escape(report_type)}<br>
<b>Date:</b> {date.today()}</div>
<div class="box"><h3>Content</h3>{safe_report}</div>
<button class="no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
</body></html>"""

def pdf_bytes(title, patient, report, report_type="AI Report"):
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
        story = [Paragraph("Pocket Dentistry", title_style), Spacer(1, 12), Paragraph(html.escape(title or "Report"), styles["Heading2"]),
               Paragraph(f"<b>Target Subject/Topic:</b> {html.escape(patient or 'Not provided')}<br/><b>Report type:</b> {html.escape(report_type)}<br/><b>Date:</b> {date.today()}", body), Spacer(1, 14)]
        for line in (report or "").split("\n"):
            if line.strip(): story += [Paragraph(html.escape(line.strip()), body), Spacer(1, 4)]
        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None

def show_export_controls(title, patient, report, report_type="AI Report"):
    if not report: return
    st.markdown("### 📄 Save / Download / Print Options")
    doc = make_report_html(title, patient, report, report_type)
    st.download_button("🌐 Download HTML", doc, file_name="document.html", mime="text/html", use_container_width=True)
    pdf = pdf_bytes(title, patient, report, report_type)
    if pdf:
        st.download_button("📄 Download PDF", pdf, file_name="document.pdf", mime="application/pdf", use_container_width=True)

def send_report_email(patient_email, subject, body):
    import smtplib
    from email.message import EmailMessage
    host = st.secrets.get("SMTP_HOST", "")
    port = int(st.secrets.get("SMTP_PORT", 587))
    user = st.secrets.get("SMTP_USERNAME", "")
    password = st.secrets.get("SMTP_PASSWORD", "")
    sender = st.secrets.get("SMTP_FROM", user)
    if not all([host, user, password, sender]): 
        raise RuntimeError("SMTP settings not configured.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = patient_email
    msg.set_content(body)
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)

def patient_email_section(report, title="Report"):
    with st.expander("📧 Send report to Gmail"):
        email = st.text_input("Gmail address", key=f"mail_{title}")
        if st.button("📨 Send", use_container_width=True, key=f"send_{title}"):
            if not email or "@" not in email: st.warning("Enter valid email.")
            else:
                try:
                    send_report_email(email, title, report)
                    st.success("Sent successfully!")
                except Exception as e:
                    st.error(f"Failed: {friendly_ai_error(e)}")

def review_section(context="report"):
    st.markdown("### ⭐ Review & Suggestions")
    rating = st.radio("How useful was this?", ["👍 Useful", "😐 Partly useful", "👎 Not useful"], horizontal=True, key=f"rating_{context}")
    suggestion = st.text_area("Suggestion / improvement idea", key=f"suggestion_{context}", placeholder="What should be added?")
    if st.button("Submit review", key=f"reviewbtn_{context}", use_container_width=True):
        save_review_db(context, rating, suggestion)
        st.success("Thank you for your feedback!")


# ============================================================
# NEW FEATURE: STUDENT PRACTICALS SECTION (Animated Photos, Videos & Notes)
# ============================================================

def student_practicals_section():
    st.markdown("### 🧪 Student Practicals & Lab Demonstration Hub")
    st.caption("Upload your practical notes, animated clinical procedures, instructional videos, and step-by-step images.")

    with st.form("practical_upload_form"):
        p_title = st.text_input("Practical Title / Procedure Name", placeholder="e.g. Class II Cavity Preparation, Mandibular Block Technique")
        p_subject = st.selectbox("Subject", [
            "Conservative Dentistry & Endodontics", "Prosthodontics", "Orthodontics", 
            "Periodontics", "Pedodontics", "Oral Surgery", "Oral Pathology", "General Human Anatomy"
        ])
        p_desc = st.text_area("Description / Practical Steps / Notes", placeholder="Write your clinical steps, observations, or instructions here...")
        
        uploaded_media = st.file_uploader(
            "📤 Upload Animated Photos, Videos or Images (MP4, GIF, PNG, JPG, WEBP)", 
            type=["mp4", "mov", "gif", "png", "jpg", "jpeg", "webp"]
        )
        
        submit_btn = st.form_submit_button("💾 Save Practical Record & Media", use_container_width=True)
        
        if submit_btn:
            if not p_title.strip():
                st.warning("Please enter a practical title.")
            else:
                file_name = uploaded_media.name if uploaded_media else "No Media"
                file_type = uploaded_media.type if uploaded_media else "None"
                
                # If media file is uploaded, save it locally in an uploads folder
                if uploaded_media:
                    os.makedirs("uploads/practicals", exist_ok=True)
                    file_path = os.path.join("uploads/practicals", uploaded_media.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_media.getbuffer())

                save_practical_db(p_title, p_subject, p_desc, file_name, file_type)
                st.success(f"Practical record '{p_title}' saved successfully!")

    st.markdown("---")
    st.markdown("### 📂 Saved Practical Records & Media Gallery")
    
    saved_records = get_practicals()
    if not saved_records:
        st.info("No practical records uploaded yet. Use the form above to add notes, photos, or videos.")
    else:
        for rec in saved_records:
            rid, created, title, subject, desc, fname, ftype = rec
            with st.expander(f"📌 {title} ({subject}) — {created[:10]}"):
                st.write(f"**Subject:** {subject}")
                st.write(f"**Description / Notes:**")
                st.markdown(desc or "No description provided.")
                
                if fname != "No Media":
                    st.write(f"**Attached File:** {fname}")
                    media_path = os.path.join("uploads/practicals", fname)
                    if os.path.exists(media_path):
                        if "video" in ftype.lower():
                            st.video(media_path)
                        elif "image" in ftype.lower() or "gif" in ftype.lower() or "webp" in ftype.lower():
                            st.image(media_path, caption=title, use_container_width=True)


# ============================================================
# KUHS PREVIOUS YEAR QUESTION BANK ON SEARCHED TOPIC
# ============================================================

def kuhs_searched_topic_pyq_bank():
    st.markdown("### 📝 Previous Year Question Bank on Searched Topic")
    search_topic = st.text_input("Enter topic or subject", value=st.session_state.get("library_search", "General Human Anatomy"), key="pyq_bank_topic")
    
    if st.button("🔨 Generate Question Bank", type="primary", use_container_width=True):
        if not search_topic.strip():
            st.warning("Please enter a topic.")
        else:
            with st.spinner("Compiling university question bank..."):
                try:
                    prompt = f"""
You are Pocket Dentistry academic assistant specialized in KUHS and Medical/Dental examinations (2012–2025).
Topic: {search_topic}
Generate a comprehensive Previous Year Question Bank layout containing Long Essays, Short Notes, Viva Voce, and High-Yield study focus areas.
"""
                    res = run_text_ai(prompt)
                    st.session_state.pyq_bank_result = res
                except Exception as exc:
                    show_ai_error(exc, "Question bank generation failed")

    if st.session_state.pyq_bank_result:
        st.markdown("---")
        st.markdown(f"### 📋 KUHS Question Bank: {search_topic}")
        st.markdown(st.session_state.pyq_bank_result)
        show_export_controls(f"KUHS Question Bank - {search_topic}", search_topic, st.session_state.pyq_bank_result, "Question Bank")
        patient_email_section(st.session_state.pyq_bank_result, f"Question Bank - {search_topic}")
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
        st.write("• Practical records, animated photos & videos upload\n• KUHS exam preparation & question banks\n• Digital library & topic tutor")
        if st.button("Enter Student Mode", use_container_width=True, key="intro_student_btn"):
            st.session_state.mode = "student"
            st.session_state.page = "student"
            st.rerun()
    with c2:
        st.markdown("### 🩺 Doctor Hub")
        st.write("• Radiographic AI with scale calibration\n• Soft-tissue professional clinical reasoning workflow\n• Patient history & secure Gmail reporting")
        if st.button("Enter Doctor Mode", use_container_width=True, key="intro_doctor_btn"):
            st.session_state.mode = "doctor"
            st.rerun()


# ============================================================
# COMPREHENSIVE TEXTBOOK LIBRARY
# ============================================================

TEXTBOOK_LIBRARY = {
    "General Human Anatomy": {
        "BD Chaurasia's Human Anatomy": ["Upper Limb", "Thorax", "Abdomen", "Head & Neck", "Embryology"]
    },
    "General Human Physiology": {
        "Guyton and Hall Physiology": ["Nerve & Muscle", "Heart & Circulation", "Renal System", "Nervous System"]
    },
    "Oral Pathology": {
        "Shafer's Textbook of Oral Pathology": ["Dental Caries", "Pulp Diseases", "Cysts", "Odontogenic Tumors"]
    },
    "Conservative Dentistry & Endodontics": {
        "Cohen's Pathways of the Pulp": ["Pulp Biology", "Access Cavity", "Cleaning & Shaping", "Obturation"]
    }
}

def textbook_library():
    st.markdown("### 📚 Comprehensive Digital Library")
    search = st.text_input("🔎 Search topic", placeholder="Try: Anatomy, Caries, Root Canal...", key="digital_library_search")
    st.session_state.library_search = search
    
    selected_subject = st.selectbox("📚 Select subject", list(TEXTBOOK_LIBRARY.keys()), key="digital_library_subject")
    books = TEXTBOOK_LIBRARY[selected_subject]
    selected_book = st.selectbox("Select textbook", list(books.keys()), key="digital_library_book")
    selected_chapter = st.selectbox("Choose chapter", ["Select a chapter"] + books[selected_book], key=f"chapter_{selected_book}")

    if selected_chapter != "Select a chapter":
        st.success(f"Selected: {selected_chapter}")
        question = st.text_area("What do you want to understand?", key=f"q_{selected_book}")
        if st.button("🤖 Ask the Library", type="primary", use_container_width=True) and question.strip():
            with st.spinner("Preparing explanation..."):
                try:
                    prompt = f"Subject: {selected_subject}\nChapter: {selected_chapter}\nQuestion: {question}\nProvide an academic explanation."
                    st.session_state.library_answer = run_text_ai(prompt)
                except Exception as exc:
                    show_ai_error(exc, "Failed")

        if st.session_state.library_answer:
            st.markdown("---")
            st.markdown("### 📚 Explanation")
            st.markdown(st.session_state.library_answer)
            show_export_controls(f"Explanation - {selected_chapter}", selected_subject, st.session_state.library_answer, "Explanation")
            review_section("library")


# ============================================================
# RADIOGRAPH & SOFT TISSUE
# ============================================================

COMMON_SAFETY_RULES = "You are Pocket Dentistry. Do no harm. Do not provide definitive diagnosis."

def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")
    rtype = st.selectbox("Type", ["IOPA", "OPG", "Bitewing"])
    uploaded = st.file_uploader("Upload X-ray", type=["png", "jpg", "jpeg", "webp"])
    if uploaded: st.image(uploaded, use_container_width=True)
    if st.button("🔍 Analyze X-ray", type="primary", use_container_width=True):
        if uploaded:
            with st.spinner("Analyzing..."):
                try:
                    rep = run_image_analysis(uploaded, COMMON_SAFETY_RULES + f"\nAnalyze {rtype}")
                    st.markdown(rep)
                    show_export_controls(f"{rtype} Report", "", rep, "Radiograph")
                except Exception as exc: show_ai_error(exc)

def soft_tissue_section():
    st.markdown("### 👄 Soft-Tissue Clinical Reasoning & Upload")
    img = st.file_uploader("Upload clinical photo", type=["png", "jpg", "jpeg", "webp"])
    if img: st.image(img, use_container_width=True)
    site = st.text_input("Anatomical Location")
    if st.button("🧠 Build Reasoning", type="primary", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                rep = run_text_ai(COMMON_SAFETY_RULES + f"\nAnalyze soft tissue lesion at site: {site}")
                st.markdown(rep)
                show_export_controls("Soft Tissue Report", site, rep, "Soft Tissue")
            except Exception as exc: show_ai_error(exc)


# ============================================================
# STUDENT & DOCTOR MODES
# ============================================================

def student_mode():
    show_mode_header("Student Mode", "🎓")
    tabs = st.tabs(["📚 Learn", "📝 Exam / PYQ Bank", "🧪 Practicals & Media", "📖 Digital Library"])

    with tabs[0]:
        st.markdown("### 📚 Topic Tutor")
        top = st.text_input("Topic", key="learn_topic")
        if st.button("📖 Teach Me", type="primary", use_container_width=True) and top.strip():
            with st.spinner("Generating notes..."):
                try:
                    res = run_text_ai(f"Teach topic: {top} with definition, features, and viva questions.")
                    st.markdown(res)
                    show_export_controls(f"Notes - {top}", top, res, "Notes")
                except Exception as exc: show_ai_error(exc)

    with tabs[1]:
        kuhs_searched_topic_pyq_bank()

    with tabs[2]:
        student_practicals_section()  # <-- PRACTICALS & ANIMATED MEDIA SECTION HERE!

    with tabs[3]:
        textbook_library()

def doctor_mode():
    show_mode_header("Doctor Mode", "🩺")
    tabs = st.tabs(["🩻 X-ray AI", "👄 Soft Tissue", "📜 Case History"])
    with tabs[0]: radiograph_analyzer()
    with tabs[1]: soft_tissue_section()
    with tabs[2]:
        st.markdown("### 📜 Saved Patient History")
        for row in get_cases():
            with st.expander(f"{row[1]} — {row[3] or 'Case'}"):
                st.markdown(row[7])


# ============================================================
# HOME & ROUTING
# ============================================================

def show_home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry & Medical Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">AI-Powered Dental & Medical Learning & Clinical Decision-Support Platform</div>', unsafe_allow_html=True)
    
    if st.button("🦷 Intro to Dental Family", use_container_width=True):
        st.session_state.page = "intro"
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="mode-card"><h3>🎓 Student Mode</h3><p>Practicals & animated media upload, KUHS PYQs, Digital Library & Topic Tutor.</p></div>', unsafe_allow_html=True)
        if st.button("🎓 Enter Student Mode", use_container_width=True):
            st.session_state.mode = "student"; st.session_state.page = "student"; st.rerun()
    with c2:
        st.markdown('<div class="mode-card doctor"><h3>🩺 Doctor Mode</h3><p>Radiographic AI, soft-tissue reasoning, and case records.</p></div>', unsafe_allow_html=True)
        if st.button("🩺 Enter Doctor Mode", use_container_width=True):
            st.session_state.mode = "doctor"; st.rerun()

def show_mode_header(title, icon):
    left, right = st.columns([1, 5])
    with left:
        if st.button("← Home", use_container_width=True):
            st.session_state.mode = None; st.session_state.page = "home"; st.rerun()
    with right: st.markdown(f"## {icon} {title}")

def sidebar():
    with st.sidebar:
        st.markdown("## 🦷 Pocket Dentistry")
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.mode = None; st.session_state.page = "home"; st.rerun()
        if st.button("🦷 Intro to Dental Family", use_container_width=True):
            st.session_state.page = "intro"; st.rerun()

sidebar()

if st.session_state.get("page") == "intro": intro_dental_family()
elif st.session_state.mode is None: show_home()
elif st.session_state.mode == "student": student_mode()
elif st.session_state.mode == "doctor": doctor_mode()
