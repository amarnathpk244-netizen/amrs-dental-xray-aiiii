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
# GLOBAL CSS (Vibrant, Colorful & Modern Styling)
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        background: radial-gradient(circle at top right, rgba(23,185,120,0.05), transparent 40%),
                    radial-gradient(circle at bottom left, rgba(0,136,145,0.05), transparent 40%);
    }

    h1, h2, h3, h4, h5, h6 {
        background: linear-gradient(90deg, #00b4d8, #17b978, #008891);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }

    .hero-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(90deg, #ff758c, #ff7eb3, #17b978, #00b4d8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        text-shadow: 0 2px 10px rgba(23,185,120,0.2);
    }

    .hero-subtitle {
        text-align: center;
        font-size: 1.15rem;
        background: linear-gradient(90deg, #00b4d8, #90e0ef);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin-bottom: 2rem;
    }

    .mode-card {
        padding: 1.5rem;
        border-radius: 20px;
        border: 2px solid #00acc1;
        background: linear-gradient(135deg, rgba(0,172,193,0.15), rgba(128,222,234,0.1));
        margin-bottom: 1rem;
        box-shadow: 0 8px 20px rgba(0,172,193,0.2);
        transition: transform 0.3s ease;
    }
    
    .mode-card:hover {
        transform: translateY(-3px);
    }

    .mode-card h3, .mode-card p {
        color: #e0f7fa !important;
    }

    .mode-card.doctor {
        border-color: #43a047;
        background: linear-gradient(135deg, rgba(67,160,71,0.15), rgba(165,214,167,0.1));
        box-shadow: 0 8px 20px rgba(67,160,71,0.2);
    }

    .mode-card.doctor h3, .mode-card.doctor p {
        color: #e8f5e9 !important;
    }

    .safety-box {
        padding: 1.2rem;
        border-radius: 15px;
        border-left: 6px solid #17b978;
        background: linear-gradient(135deg, rgba(23,185,120,0.15), rgba(0,136,145,0.05));
        margin-top: 1rem;
        box-shadow: 0 4px 15px rgba(23,185,120,0.1);
    }

    .chapter-card {
        padding: 1rem 1.2rem;
        border-radius: 14px;
        border: 1px solid rgba(0,180,216,0.3);
        background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(0,180,216,0.05));
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    div.stButton > button {
        border-radius: 14px;
        min-height: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #0077b6, #00b4d8, #17b978);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(0,180,216,0.3);
        transition: all 0.3s ease;
    }

    div.stButton > button:hover {
        background: linear-gradient(90deg, #17b978, #00b4d8, #0077b6);
        box-shadow: 0 6px 20px rgba(23,185,120,0.4);
        transform: translateY(-2px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PERSISTENT DATABASE (SQLite)
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
# EXPORT, PRINT & GMAIL UTILITIES
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
<div class="box"><b>Target Subject / Patient:</b> {safe_patient}<br>
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
               Paragraph(f"<b>Target Subject/Patient:</b> {html.escape(patient or 'Not provided')}<br/><b>Report type:</b> {html.escape(report_type)}<br/><b>Date:</b> {date.today()}", body), Spacer(1, 14)]
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
    b64 = base64.b64encode(doc.encode()).decode()
    st.markdown(f'<a href="data:text/html;base64,{b64}" target="_blank">🖨️ Open printable report window</a>', unsafe_allow_html=True)

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
# STUDENT PRACTICALS & MEDIA SECTION
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
# INTRO TO DENTAL FAMILY & BRANCHES OF DENTISTRY (Enhanced)
# ============================================================

def intro_dental_family():
    st.markdown("## 🦷 Intro to Dental Family & Basic Dentistry")
    st.write("Welcome to **Pocket Dentistry & Medical Hub** — the ultimate AI-powered bridge uniting undergraduate dental students, medical trainees, and practicing clinicians.")
    
    st.markdown("### 📖 What is Basic Dentistry?")
    st.write("""
    **Basic Dentistry** encompasses the foundational sciences and clinical practices dedicated to the study, diagnosis, prevention, and treatment of diseases, disorders, and conditions of the oral cavity, maxillofacial area, and adjacent structures. It bridges core medical sciences (Anatomy, Physiology, Pathology, Pharmacology) with specialized dental mechanics and patient care.
    """)
    
    st.markdown("### 🌟 Comprehensive Branches of Dentistry (Specialties)")
    st.write("The dental profession is divided into several recognized clinical and academic specialties:")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        1. **Conservative Dentistry & Endodontics**  
           * Focuses on the preservation of natural teeth, operative restorations (fillings), and root canal treatments (RCT) of diseased pulpal tissues.
        2. **Periodontics (Periodontology)**  
           * Deals with the supporting structures of teeth (gums, alveolar bone, periodontal ligament) and treatment of gum diseases (gingivitis, periodontitis).
        3. **Orthodontics & Dentofacial Orthopedics**  
           * Specializes in the diagnosis, prevention, and correction of malpositioned teeth and jaws (braces, aligners, growth modification).
        4. **Prosthodontics (Prosthetic Dentistry)**  
           * Involves the replacement of missing teeth and jaw structures using artificial devices such as crowns, bridges, dentures, and dental implants.
        5. **Oral & Maxillofacial Surgery**  
           * Surgical treatment of diseases, injuries, and defects in the head, neck, face, jaws, and oral tissues (including tooth extractions and trauma care).
        """)
    with col2:
        st.markdown("""
        6. **Oral Medicine & Radiology**  
           * Focuses on oral mucosal diseases, systemic disease manifestations in the mouth, orofacial pain, and advanced dental imaging/diagnostics (X-rays, OPG, CBCT).
        7. **Pediatric Dentistry (Pedodontics)**  
           * Dedicated to the specialized oral health care of children from infancy through adolescence, including preventive and interceptive orthodontics.
        8. **Oral & Maxillofacial Pathology**  
           * Pathology dealing with the nature, identification, and management of diseases affecting the oral and maxillofacial regions (biopsy analysis).
        9. **Public Health Dentistry**  
           * Focuses on the prevention of dental diseases, dental epidemiology, community oral health programs, indices (CPITN, DMFT), and health education.
        10. **Dental Materials Science**  
           * The study of physical, chemical, and biological properties of materials used in dentistry (composites, cements, gypsum, impression materials).
        """)

    st.markdown("---")
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
        "BD Chaurasia's Human Anatomy (Vol 1-3)": ["General Anatomy & Introduction", "Upper Limb and Thorax", "Abdomen and Pelvis", "Head, Neck and Brain", "Lower Limb", "Embryology & General Histology", "Osteology"]
    },
    "General Human Physiology": {
        "Guyton and Hall Textbook of Medical Physiology": ["General Physiology & Cell Physiology", "Nerve and Muscle", "Heart and Circulation", "The Body Fluids and Kidneys", "Respiration", "Nervous System", "Gastrointestinal Physiology", "Endocrinology"]
    },
    "Biochemistry": {
        "Vasudevan Textbook of Biochemistry": ["Carbohydrate Metabolism", "Lipid Metabolism", "Amino Acids", "Enzymes", "Vitamins", "Clinical Biochemistry"]
    },
    "General Pathology": {
        "Robbins & Cotran Pathologic Basis of Disease": ["Cell Injury", "Inflammation and Repair", "Hemodynamics", "Neoplasia", "Genetic Diseases"]
    },
    "Microbiology": {
        "Ananthanarayan and Paniker's Textbook of Microbiology": ["General Microbiology", "Bacteriology", "Immunology", "Virology", "Mycology"]
    },
    "General Pharmacology": {
        "KD Tripathi Essentials of Medical Pharmacology": ["Pharmacokinetics", "Autonomic Nervous System", "Cardiovascular Drugs", "CNS Drugs", "Chemotherapy"]
    },
    "General Medicine": {
        "Davidson's Principles and Practice of Medicine": ["Cardiovascular Disease", "Respiratory Disease", "Endocrine Disease", "Gastrointestinal Disease", "Neurological Disease"]
    },
    "General Surgery": {
        "Bailey & Love's Short Practice of Surgery": ["Wounds and Scars", "Burns", "Surgical Infection", "Head and Neck Surgery", "Abdominal Surgery"]
    },
    "Oral Pathology": {
        "Shafer's Textbook of Oral Pathology": ["Developmental Disturbances", "Dental Caries", "Pulp Diseases", "Periodontal Diseases", "Cysts", "Odontogenic Tumors"]
    },
    "Oral Medicine & Radiology": {
        "Burket's Oral Medicine": ["Patient Evaluation", "Oral Mucosal Diseases", "Ulcers", "White Lesions", "Salivary Gland Disorders"]
    },
    "Periodontics": {
        "Carranza's Clinical Periodontology": ["Periodontal Anatomy", "Gingivitis", "Periodontitis", "Scaling and Root Planing", "Periodontal Surgery"]
    },
    "Conservative Dentistry & Endodontics": {
        "Cohen's Pathways of the Pulp": ["Pulp Biology", "Diagnosis", "Root Canal Anatomy", "Cleaning and Shaping", "Obturation"]
    },
    "Prosthodontics": {
        "Nallaswamy - Textbook of Prosthodontics": ["Complete Dentures", "Impression Making", "Jaw Relations", "Removable Partial Dentures", "Fixed Prosthodontics"]
    },
    "Orthodontics": {
        "Proffit - Contemporary Orthodontics": ["Growth and Development", "Malocclusion", "Diagnosis", "Fixed Appliances", "Retention"]
    },
    "Pedodontics": {
        "Nikhil Marwah - Textbook of Pediatric Dentistry": ["Preventive Dentistry", "Dental Caries", "Pulp Therapy", "Space Maintainers", "Behavior Management"]
    },
    "Public Health Dentistry": {
        "Soben Peter - Essentials of Preventive and Community Dentistry": ["Epidemiology", "Biostatistics", "Indices (DMFT, OHI-S, CPITN)", "Preventive Dentistry"]
    },
    "Dental Materials": {
        "Phillips' Science of Dental Materials": ["Physical Properties", "Impression Materials", "Gypsum Products", "Resin Composites", "Cements"]
    },
    "Oral Surgery": {
        "Malamed's Handbook of Local Anesthesia": ["Local Anesthetic Drugs", "Maxillary Anesthesia", "Mandibular Anesthesia", "Complications"]
    }
}

REFERENCE_ALIASES = {
    "anatomy": "General Human Anatomy", "physiology": "General Human Physiology", "biochemistry": "Biochemistry",
    "pathology": "General Pathology", "microbiology": "Microbiology", "pharmacology": "General Pharmacology",
    "medicine": "General Medicine", "surgery": "General Surgery", "caries": "Conservative Dentistry & Endodontics",
    "rct": "Conservative Dentistry & Endodontics", "gum disease": "Periodontics", "periodontal": "Periodontics",
    "cpitn": "Public Health Dentistry", "opg": "Oral Medicine & Radiology", "iopa": "Oral Medicine & Radiology", 
    "ceph": "Orthodontics", "pedo": "Pedodontics", "prostho": "Prosthodontics", "ulcer": "Oral Medicine & Radiology"
}

CEPH_ANALYSES = [
    "Steiner Analysis", "Downs Analysis", "McNamara Analysis",
    "Tweed Analysis", "Wits Appraisal", "Jarabak Analysis",
    "Soft Tissue Profile Analysis", "Combined / All Analyses"
]

def find_subject(search_text):
    if not search_text: return "General Human Anatomy"
    search = search_text.strip().lower()
    if search in REFERENCE_ALIASES: return REFERENCE_ALIASES[search]
    for alias, subject in REFERENCE_ALIASES.items():
        if alias in search: return subject
    for subject in TEXTBOOK_LIBRARY:
        if subject.lower() in search: return subject
    return "General Human Anatomy"

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
    st.markdown("### 📚 Comprehensive Medical & Dental Digital Library")
    search = st.text_input("🔎 Search topic", placeholder="Try: Anatomy, Physiology, Pathology, Surgery, Caries...", key="digital_library_search")
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
        st.success(f"Selected: {selected_chapter}")
        question = st.text_area("What do you want to understand?", key=f"question_{selected_book}_{selected_chapter}")
        if st.button("🤖 Ask the Library", type="primary", use_container_width=True) and question.strip():
            with st.spinner("Preparing academic explanation..."):
                try:
                    prompt = f"Subject: {selected_subject}\nTextbook: {selected_book}\nChapter: {selected_chapter}\nQuestion: {question}\nProvide an academic explanation."
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

COMMON_SAFETY_RULES = """
You are Pocket Dentistry & Medical Hub, an AI-assisted clinical decision-support system.
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

def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")
    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    st.caption(f"AI analyses remaining today: {remaining}/{DAILY_ANALYSIS_LIMIT}")
    
    rtype = st.selectbox("Select radiograph type", list(RADIOGRAPH_PROMPTS.keys()) + ["Lateral Cephalogram (Ceph)"])
    ceph = st.selectbox("Cephalometric Analysis Type", CEPH_ANALYSES) if rtype == "Lateral Cephalogram (Ceph)" else ""

    st.markdown("#### 📏 Scale Calibration Settings")
    calibration_mode = st.radio("Select Scale Calibration Mode", ["🤖 Auto-Calculate / AI Estimation", "✏️ Enter Known Calibration Scale (mm/pixel)"])
    scale_val = st.text_input("Enter known scale value", value="1.0 mm/pixel") if "Enter" in calibration_mode else "Auto-estimated"

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
                prompt = COMMON_SAFETY_RULES + f"\nRadiograph: {rtype}\nCeph: {ceph}\nScale: {scale_val}"
                report = run_image_analysis(uploaded, prompt)
                st.session_state.analysis_count += 1
                st.session_state.last_report = report
                st.session_state.last_image_name = uploaded.name
                
                save_case(patient_email, patient_name, rtype, uploaded.name, f"{rtype} Assessment", report)

                st.success("Analysis completed.")
                st.markdown("### 📋 AI Assessment Report")
                st.markdown(report)
                show_export_controls(f"{rtype} Assessment", patient_name, report, "Radiographic AI")
                patient_email_section(report, f"{rtype} Report")
                review_section("radiograph")
            except Exception as exc:
                show_ai_error(exc, "Radiographic AI analysis failed")

def soft_tissue_section():
    st.markdown("### 👄 Advanced Soft-Tissue Clinical Reasoning & Upload")
    st.caption("Upload clinical photographs of oral mucosal lesions for professional reasoning support.")
    
    patient_name = st.text_input("Patient / Case identifier", key="soft_patient_name")
    patient_email = st.text_input("Patient Gmail / email (optional)", key="soft_patient_email", placeholder="patient@gmail.com")
    
    soft_image = st.file_uploader("📷 Upload intraoral/extraoral clinical photograph", type=["png", "jpg", "jpeg", "webp"], key="soft_tissue_file_uploader")
    if soft_image: st.image(soft_image, caption="Uploaded soft-tissue photograph", use_container_width=True)

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
                show_export_controls("Soft-Tissue Clinical Reasoning", patient_name, report, "Clinical Decision Support")
                patient_email_section(report, "Soft-Tissue Clinical Report")
                review_section("soft_tissue")
            except Exception as exc:
                show_ai_error(exc, "Soft-tissue reasoning failed")


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
        student_practicals_section()

    with tabs[3]:
        textbook_library()

def doctor_mode():
    show_mode_header("Doctor Mode", "🩺")
    tabs = st.tabs(["🩻 X-ray AI", "👄 Soft Tissue Reasoning", "📖 Clinical Library", "📜 Case History"])
    with tabs[0]: radiograph_analyzer()
    with tabs[1]: soft_tissue_section()
    with tabs[2]: textbook_library()
    with tabs[3]:
        st.markdown("### 📜 Saved Patient History & Case Records")
        search_email = st.text_input("Search patient email", key="history_email", placeholder="patient@gmail.com")
        rows = get_cases(search_email)
        if not rows:
            st.info("No saved cases found.")
        else:
            for row in rows:
                cid, created, email, name, ctype, img, title, report = row
                with st.expander(f"{created} — {name or 'Case'} — {ctype or 'Report'}"):
                    st.write(f"**Patient:** {name or 'Not provided'}")
                    st.write(f"**Email:** {email or 'Not provided'}")
                    st.markdown(report)
                    show_export_controls(title or "Saved Case", name or "", report, ctype or "Saved report")
                    if email: patient_email_section(report, f"Saved Case {cid}")


# ============================================================
# HOME & ROUTING
# ============================================================

def show_home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry & Medical Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">AI-Powered Dental & Medical Learning & Clinical Decision-Support Platform</div>', unsafe_allow_html=True)
    
    if st.button("🦷 Intro to Dental Family & Branches", use_container_width=True):
        st.session_state.page = "intro"
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="mode-card"><h3>🎓 Student Mode</h3><p>Practicals & animated media upload, KUHS PYQs, Digital Library & Topic Tutor.</p></div>', unsafe_allow_html=True)
        if st.button("🎓 Enter Student Mode", use_container_width=True):
            st.session_state.mode = "student"; st.session_state.page = "student"; st.rerun()
    with c2:
        st.markdown('<div class="mode-card doctor"><h3>🩺 Doctor Mode</h3><p>Radiographic AI with scale calibration, soft-tissue clinical reasoning, and case history.</p></div>', unsafe_allow_html=True)
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
