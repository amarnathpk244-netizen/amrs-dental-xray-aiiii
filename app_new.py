import os
import json
import re
from datetime import date, datetime
from io import BytesIO
import base64
import html
import sqlite3

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Pocket Dentistry",
    page_icon="🦷",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-2.5-flash"

# ============================================================
# STYLE
# ============================================================
st.markdown("""
<style>
.block-container{max-width:900px;padding-top:2rem;padding-bottom:3rem}
.hero-title{text-align:center;font-size:3rem;font-weight:900;
background:linear-gradient(90deg,#1e3d59,#17b978,#008891);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-subtitle{text-align:center;color:#008891;font-weight:600;margin-bottom:2rem}
.mode-card,.feature-card{padding:1.2rem;border-radius:18px;border:1px solid #d0d7de;
background:#f8fafb;margin-bottom:1rem}
.safety-box{padding:1rem;border-radius:15px;border-left:5px solid #17b978;
background:rgba(23,185,120,.1);margin-top:1rem}
div.stButton>button{border-radius:12px;min-height:2.7rem;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ============================================================
# STATE
# ============================================================
DEFAULT_STATE = {
    "mode": None,
    "page": "home",
    "analysis_date": str(date.today()),
    "analysis_count": 0,
    "last_report": "",
    "last_image_name": "",
    "last_report_title": "",
    "patient_history": [],
    "review": [],
    "intro_page": False,
}
for k,v in DEFAULT_STATE.items():
    if k not in st.session_state: st.session_state[k]=v

if st.session_state.analysis_date != str(date.today()):
    st.session_state.analysis_date=str(date.today())
    st.session_state.analysis_count=0

# ============================================================
# PERSISTENT CASE DATABASE
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
    conn=db_connect()
    conn.execute("INSERT INTO cases(created_at,patient_email,patient_name,case_type,image_name,report_title,report) VALUES(?,?,?,?,?,?,?)",
                 (str(datetime.now()),patient_email,patient_name,case_type,image_name,report_title,report))
    conn.commit(); conn.close()

def get_cases(patient_email=""):
    conn=db_connect()
    if patient_email.strip():
        rows=conn.execute("SELECT id,created_at,patient_email,patient_name,case_type,image_name,report_title,report FROM cases WHERE patient_email=? ORDER BY id DESC",(patient_email.strip(),)).fetchall()
    else:
        rows=conn.execute("SELECT id,created_at,patient_email,patient_name,case_type,image_name,report_title,report FROM cases ORDER BY id DESC LIMIT 50").fetchall()
    conn.close(); return rows

def save_review_db(context,rating,suggestion):
    conn=db_connect()
    conn.execute("INSERT INTO reviews(created_at,context,rating,suggestion) VALUES(?,?,?,?)",(str(datetime.now()),context,rating,suggestion))
    conn.commit(); conn.close()

# ============================================================
# GEMINI
# ============================================================
def get_api_key():
    try: key=st.secrets.get("GEMINI_API_KEY","")
    except Exception: key=""
    return str(key or os.getenv("GEMINI_API_KEY","")).strip()

def get_client():
    key=get_api_key()
    if not key: return None
    try: return genai.Client(api_key=key)
    except Exception: return None

def friendly_ai_error(exc):
    t=str(exc).upper()
    if "401" in t or "UNAUTHENTICATED" in t: return "🔐 Gemini authentication failed. Check GEMINI_API_KEY."
    if "403" in t or "PERMISSION_DENIED" in t: return "🚫 Gemini permission denied. Check API access."
    if "404" in t or "NOT_FOUND" in t: return f"🔎 Gemini model `{MODEL_NAME}` was not found or is unavailable."
    if "429" in t or "QUOTA" in t or "RESOURCE_EXHAUSTED" in t: return "⏳ Gemini quota/rate limit reached."
    if "503" in t or "UNAVAILABLE" in t: return "🔄 Gemini is temporarily unavailable. Try again shortly."
    return "⚠️ AI service error. Please try again."

def run_text_ai(prompt):
    c=get_client()
    if c is None: raise RuntimeError("Gemini API key not configured.")
    r=c.models.generate_content(model=MODEL_NAME, contents=prompt)
    text=getattr(r,"text",None)
    if not text: raise RuntimeError("AI returned an empty response.")
    return text

def run_image_analysis(uploaded,prompt):
    c=get_client()
    if c is None: raise RuntimeError("Gemini API key not configured.")
    part=types.Part.from_bytes(data=uploaded.getvalue(),mime_type=uploaded.type or "image/png")
    r=c.models.generate_content(model=MODEL_NAME,contents=[prompt,part])
    text=getattr(r,"text",None)
    if not text: raise RuntimeError("AI returned an empty response.")
    return text

# ============================================================
# REPORT / EXPORT
# ============================================================
def make_report_html(title, patient, report, image_name="", report_type="AI Report"):
    safe_report=html.escape(report or "").replace("\n","<br>")
    safe_patient=html.escape(patient or "Not provided")
    safe_img=html.escape(image_name or "Not provided")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:850px;margin:40px auto;padding:20px;color:#17202a}}
h1{{color:#1e3d59}} .box{{padding:15px;border:1px solid #ddd;border-radius:10px;margin:12px 0}}
.disclaimer{{background:#fff8e1;padding:15px;border-left:5px solid #f0ad00}}
@media print{{.no-print{{display:none}}}}
</style></head><body>
<h1>🦷 Pocket Dentistry</h1><h2>{html.escape(title)}</h2>
<div class="box"><b>Patient / Case:</b> {safe_patient}<br>
<b>Report type:</b> {html.escape(report_type)}<br>
<b>Image:</b> {safe_img}<br><b>Date:</b> {date.today()}</div>
<div class="box"><h3>Report</h3>{safe_report}</div>
<div class="disclaimer"><b>Safety notice:</b> AI output is decision-support information and is not a definitive diagnosis. Final diagnosis and treatment decisions require qualified dental professional assessment.</div>
<button class="no-print" onclick="window.print()">🖨️ Print</button>
</body></html>"""

def pdf_bytes(title, patient, report, image_name="", report_type="AI Report"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        buf=BytesIO()
        doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)
        styles=getSampleStyleSheet()
        title_style=ParagraphStyle("PDTitle",parent=styles["Title"],alignment=TA_CENTER,fontSize=18)
        body=ParagraphStyle("PDBody",parent=styles["BodyText"],fontSize=9.5,leading=14)
        story=[Paragraph("Pocket Dentistry",title_style),Spacer(1,12),Paragraph(html.escape(title or "Dental Report"),styles["Heading2"]),
               Paragraph(f"<b>Patient/Case:</b> {html.escape(patient or 'Not provided')}<br/><b>Report type:</b> {html.escape(report_type)}<br/><b>Image:</b> {html.escape(image_name or 'Not provided')}<br/><b>Date:</b> {date.today()}",body),Spacer(1,14)]
        for line in (report or "").split("\n"):
            if line.strip(): story += [Paragraph(html.escape(line.strip()),body),Spacer(1,4)]
        story += [Spacer(1,10),Paragraph("<b>Safety notice:</b> AI-assisted information only. Final diagnosis and treatment decisions require qualified dental professional assessment.",body)]
        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None

def show_export_controls(title,patient,report,image_name="",report_type="AI Report"):
    if not report: return
    st.markdown("### 📄 Save / Print Result")
    doc=make_report_html(title,patient,report,image_name,report_type)
    st.download_button("🌐 Download HTML",doc,file_name="pocket_dentistry_report.html",mime="text/html",use_container_width=True)
    pdf=pdf_bytes(title,patient,report,image_name,report_type)
    if pdf:
        st.download_button("📄 Download PDF",pdf,file_name="pocket_dentistry_report.pdf",mime="application/pdf",use_container_width=True)
    else:
        st.info("PDF package is unavailable in this deployment. Use HTML → Print → Save as PDF.")
    b64=base64.b64encode(doc.encode()).decode()
    st.markdown(f'<a href="data:text/html;base64,{b64}" target="_blank">🖨️ Open printable report</a>',unsafe_allow_html=True)

# ============================================================
# EMAIL
# ============================================================
def email_configured():
    return bool(st.secrets.get("SMTP_HOST","") if hasattr(st,"secrets") else False)

def send_report_email(patient_email,subject,body):
    import smtplib
    from email.message import EmailMessage
    host=st.secrets.get("SMTP_HOST","")
    port=int(st.secrets.get("SMTP_PORT",587))
    user=st.secrets.get("SMTP_USERNAME","")
    password=st.secrets.get("SMTP_PASSWORD","")
    sender=st.secrets.get("SMTP_FROM",user)
    if not all([host,user,password,sender]): raise RuntimeError("SMTP email settings are not configured.")
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=sender; msg["To"]=patient_email
    msg.set_content(body)
    with smtplib.SMTP(host,port) as s:
        s.starttls(); s.login(user,password); s.send_message(msg)

def patient_email_section(report,title="Dental Buddy Report",patient_name=""):
    with st.expander("📧 Send report to patient Gmail"):
        email=st.text_input("Patient Gmail address",key=f"mail_{title}")
        consent=st.checkbox("I confirm that the patient has consented to receiving this report by email.",key=f"consent_{title}")
        if st.button("📨 Send report",use_container_width=True,key=f"send_{title}"):
            if not email or "@" not in email: st.warning("Enter a valid email address.")
            elif not consent: st.warning("Patient consent is required.")
            else:
                try:
                    send_report_email(email,title,report)
                    st.success("Report sent successfully.")
                except Exception as e:
                    st.error(f"Email could not be sent: {friendly_ai_error(e)}")

# ============================================================
# REVIEW
# ============================================================
def review_section(context="report"):
    st.markdown("### ⭐ Review & Suggestions")
    rating=st.radio("How useful was this result?",["👍 Useful","😐 Partly useful","👎 Not useful"],horizontal=True,key=f"rating_{context}")
    suggestion=st.text_area("Suggestion / correction",key=f"suggestion_{context}",placeholder="Tell us what should be improved.")
    if st.button("Submit review",key=f"reviewbtn_{context}",use_container_width=True):
        st.session_state.review.append({"date":str(datetime.now()),"context":context,"rating":rating,"suggestion":suggestion})
        save_review_db(context,rating,suggestion)
        st.success("Thank you. Your feedback has been recorded for this session.")

# ============================================================
# KUHS PYQ
# ============================================================
KUHS_SUBJECTS=[
"Oral Pathology","Oral Medicine & Radiology","Periodontics","Prosthodontics",
"Conservative Dentistry & Endodontics","Orthodontics","Pedodontics",
"Public Health Dentistry","Oral Surgery","Dental Materials"
]
def kuhs_pyq():
    st.markdown("### 📝 KUHS Previous-Year Question Papers")
    st.caption("Add verified KUHS papers here; the app should not fabricate past papers.")
    subject=st.selectbox("Subject",KUHS_SUBJECTS,key="kuhs_subject")
    year=st.selectbox("Year",["All","2026","2025","2024","2023","2022","2021","2020","2019","2018"],key="kuhs_year")
    uploaded=st.file_uploader("📤 Upload verified KUHS question paper (PDF/image)",type=["pdf","png","jpg","jpeg"],key="kuhs_upload")
    if uploaded:
        st.success(f"Loaded: {uploaded.name}")
        st.download_button("⬇️ Download paper",uploaded.getvalue(),file_name=uploaded.name)
    st.info("For a public library, place verified KUHS question-paper files/links in the app's PYQ data folder and map them by subject/year.")

# ============================================================
# INTRO TO DENTAL FAMILY
# ============================================================
def intro_dental_family():
    st.markdown("## 🦷 Intro to Dental Family")
    st.write("Welcome to Pocket Dentistry — one platform for learning and clinical decision-support.")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("### 🎓 Student")
        st.write("Learn topics • Exam preparation • KUHS PYQs • Quiz • Digital Library • Case learning")
        if st.button("Enter Student Mode",use_container_width=True,key="intro_student"):
            st.session_state.mode="student"; st.session_state.page="student"; st.rerun()
    with c2:
        st.markdown("### 🩺 Doctor")
        st.write("Radiographic assessment • Soft-tissue reasoning • Clinical decision support • Reports")
        if st.button("Enter Doctor Mode",use_container_width=True,key="intro_doctor"):
            st.session_state.mode="doctor"; st.session_state.page="doctor"; st.rerun()
    st.markdown("### 🌱 Dental Family")
    st.write("Students learn, clinicians assess, and both can use the platform as an AI-assisted educational/clinical support tool.")

# ============================================================
# SIMPLE TEXTBOOK LIBRARY
# ============================================================
TEXTBOOK_LIBRARY={
"Oral Pathology":["Shafer's Textbook of Oral Pathology","Neville's Oral and Maxillofacial Pathology"],
"Oral Medicine":["Burket's Oral Medicine"],
"Periodontics":["Carranza's Clinical Periodontology"],
"Endodontics":["Cohen's Pathways of the Pulp"],
"Prosthodontics":["Nallaswamy - Textbook of Prosthodontics"],
"Orthodontics":["Proffit - Contemporary Orthodontics","S.I. Bhalajhi - Orthodontics"],
"Pedodontics":["Nikhil Marwah - Textbook of Pediatric Dentistry"],
"Public Health Dentistry":["Soben Peter - Essentials of Preventive and Community Dentistry"],
"Radiology":["White and Pharoah's Oral Radiology"]
}
def textbook_library():
    st.markdown("### 📚 Pocket Dentistry Digital Library")
    subject=st.selectbox("Subject",list(TEXTBOOK_LIBRARY),key="lib_subject")
    book=st.selectbox("Textbook",TEXTBOOK_LIBRARY[subject],key="lib_book")
    q=st.text_area("Ask about this textbook/topic",key="lib_q")
    if st.button("🤖 Ask the Textbook",use_container_width=True,key="lib_ask"):
        if not q.strip(): st.warning("Enter a question.")
        else:
            try:
                res=run_text_ai(f"""You are Pocket Dentistry, a BDS educational assistant.
Subject: {subject}
Textbook: {book}
Question: {q}
Give an exam-oriented explanation using established dental knowledge.
Do not claim direct access to copyrighted text or reproduce it.""")
                st.markdown(res)
            except Exception as e: st.error(friendly_ai_error(e))

# ============================================================
# RADIOGRAPH
# ============================================================
RADIOGRAPH_PROMPTS={
"IOPA":"Assess image quality, visible teeth, caries, restorations, periodontal bone levels, periapical region and other visible findings.",
"OPG":"Assess image quality, dentition, missing/impacted teeth, periodontal bone levels, periapical regions, jaws, sinuses/condyles where visible and obvious lesions.",
"Bitewing":"Assess image quality, interproximal/occlusal caries, restorations, recurrent caries and alveolar crest.",
"Occlusal":"Assess teeth, development, impacted teeth, jaw structures and obvious radiopaque/radiolucent abnormalities.",
"Facial Radiograph":"Assess skeletal alignment, continuity, cortical disruption and obvious fracture-related findings only when visible."
}
CEPH=["Steiner Analysis","Downs Analysis","McNamara Analysis","Tweed Analysis","Wits Appraisal","Jarabak Analysis","Soft Tissue Profile Analysis","Combined / All Analyses"]

COMMON="""You are Pocket Dentistry. Analyze only supplied information. Never invent findings, tooth numbers, landmarks or measurements. Clearly state uncertainty. Do not provide a definitive diagnosis. Final diagnosis and treatment require a qualified dental professional."""

def radiograph_analyzer():
    st.markdown("### 🩻 AI Radiographic Assessment")
    st.caption(f"AI analyses remaining today: {DAILY_ANALYSIS_LIMIT-st.session_state.analysis_count}/{DAILY_ANALYSIS_LIMIT}")
    rtype=st.selectbox("Radiograph type",list(RADIOGRAPH_PROMPTS)+["Lateral Cephalogram (Ceph)"],key="rtype")
    ceph=st.selectbox("Cephalometric analysis",CEPH,key="ceph") if rtype.startswith("Lateral") else ""
    uploaded=st.file_uploader("📤 Upload dental radiograph",type=["png","jpg","jpeg","webp"],key="xray_upload")
    if uploaded: st.image(uploaded,caption="Uploaded radiograph",use_container_width=True)
    patient=st.text_input("Patient / Case identifier (avoid unnecessary personal data)",key="xray_patient")
    patient_email=st.text_input("Patient Gmail / email (optional)",key="xray_patient_email",placeholder="patient@gmail.com")
    if st.button("🔍 Analyze X-ray",type="primary",use_container_width=True,disabled=st.session_state.analysis_count>=DAILY_ANALYSIS_LIMIT):
        if not uploaded: st.warning("Upload a radiograph first."); return
        prompt=COMMON+f"\nRadiograph: {rtype}\nAnalysis: {ceph}\n"+RADIOGRAPH_PROMPTS.get(rtype,"Analyze the lateral cephalogram and selected analysis.")
        try:
            with st.spinner("Analyzing radiograph..."):
                report=run_image_analysis(uploaded,prompt)
            st.session_state.analysis_count+=1
            st.session_state.last_report=report
            st.session_state.last_image_name=uploaded.name
            st.session_state.last_report_title=f"{rtype} AI Assessment"
            st.session_state.patient_history.append({"date":str(datetime.now()),"patient":patient,"email":patient_email,"type":rtype,"image":uploaded.name,"report":report})
            save_case(patient_email,patient,rtype,uploaded.name,f"{rtype} AI Assessment",report)
            st.success("Analysis completed.")
            st.markdown("### 📋 AI Assessment Report"); st.markdown(report)
            show_export_controls(f"{rtype} AI Assessment",patient,report,uploaded.name,"Radiographic AI")
            patient_email_section(report,f"{rtype} Dental Report",patient)
            review_section("radiograph")
        except Exception as e: st.error(f"❌ Analysis failed\n\n{friendly_ai_error(e)}")

# ============================================================
# SOFT TISSUE
# ============================================================
def soft_tissue():
    st.markdown("### 👄 Soft-Tissue Clinical Reasoning")
    patient=st.text_input("Patient / Case identifier (optional)",key="soft_patient")
    patient_email=st.text_input("Patient Gmail / email (optional)",key="soft_patient_email",placeholder="patient@gmail.com")
    image=st.file_uploader("📷 Upload intraoral/extraoral clinical photograph",type=["png","jpg","jpeg","webp"],key="soft_image")
    if image: st.image(image,use_container_width=True)
    lesion=st.selectbox("Primary appearance",["White lesion","Red lesion","Red-white lesion","Ulcer","Pigmented lesion","Swelling / mass","Vesicle / blister","Other / unclear"])
    site=st.text_input("Anatomical location")
    duration=st.text_input("Duration & progression")
    pain=st.selectbox("Pain",["Painless","Mild discomfort","Painful / burning"])
    scrap=st.selectbox("Scrapable?",["Not applicable","Scrapable","Non-scrapable"])
    bleed=st.selectbox("Bleeding on manipulation",["No","Yes","Not tested"])
    ind=st.selectbox("Induration",["Soft/fluctuant","Firm/indurated","Not assessed"])
    extra=st.text_area("Other history / findings")
    if st.button("🧠 Build Clinical Reasoning",type="primary",use_container_width=True):
        try:
            prompt=f"""{COMMON}
Analyze this oral lesion as clinical decision support.
Appearance: {lesion}
Site: {site}
Duration: {duration}
Pain: {pain}
Scrapability: {scrap}
Bleeding: {bleed}
Induration: {ind}
Other: {extra}
Provide:
1 Problem representation
2 Differential diagnoses with supporting features
3 Evidence Ledger: supporting/opposing/unknown
4 Critical missing information
5 ONE highest-value next clinical question
6 Appropriate diagnostic test when indicated
7 Broad management considerations
8 Red flags / urgent referral considerations
Do not give a definitive diagnosis."""
            with st.spinner("Building reasoning..."): report=run_text_ai(prompt)
            st.session_state.last_report=report
            st.session_state.last_report_title="Soft-Tissue Clinical Reasoning"
            st.session_state.patient_history.append({"date":str(datetime.now()),"patient":patient,"email":patient_email,"type":"Soft Tissue","image":image.name if image else "None","report":report})
            save_case(patient_email,patient,"Soft Tissue",image.name if image else "","Soft-Tissue Clinical Reasoning",report)
            st.markdown("### 📋 Clinical Decision Support Report"); st.markdown(report)
            show_export_controls("Soft-Tissue Clinical Reasoning",patient,report,image.name if image else "","Clinical decision support")
            patient_email_section(report,"Soft Tissue Clinical Report",patient)
            review_section("soft_tissue")
        except Exception as e: st.error(friendly_ai_error(e))

# ============================================================
# STUDENT / DOCTOR
# ============================================================
def header(title,icon):
    a,b=st.columns([1,5])
    with a:
        if st.button("← Home",use_container_width=True): st.session_state.mode=None; st.session_state.page="home"; st.rerun()
    with b: st.markdown(f"## {icon} {title}")

def student_mode():
    header("Student Mode","🎓")
    tabs=st.tabs(["📚 Learn","📝 Exam / PYQ","🧠 Quiz","📖 Digital Library","📜 History"])
    with tabs[0]:
        topic=st.text_input("Topic",placeholder="e.g. Lichen planus, CPITN, deep bite")
        if st.button("📖 Teach Me",use_container_width=True):
            if topic:
                try: st.markdown(run_text_ai(f"""Teach BDS topic: {topic}. Give definition, etiology, classification, pathogenesis, clinical features, diagnosis, management principles, exam points and viva."""))
                except Exception as e: st.error(friendly_ai_error(e))
            else: st.warning("Enter a topic.")
    with tabs[1]:
        kuhs_pyq()
        q=st.text_area("Paste a question for an answer",key="student_q")
        if st.button("✍️ Generate Answer",use_container_width=True):
            if q:
                try: st.markdown(run_text_ai(f"""Write a structured BDS university answer for:\n{q}\nUse headings, definition, classification, clinical features, diagnosis, management and viva where relevant."""))
                except Exception as e: st.error(friendly_ai_error(e))
            else: st.warning("Enter a question.")
    with tabs[2]:
        topic=st.text_input("Quiz topic",key="quiz")
        if st.button("🎯 Generate Quiz",use_container_width=True) and topic:
            try: st.markdown(run_text_ai(f"Create 5 BDS MCQs on {topic}, with options, answer and explanation."))
            except Exception as e: st.error(friendly_ai_error(e))
    with tabs[3]: textbook_library()
    with tabs[4]:
        st.markdown("### 📜 Saved Patient / Case History")
        search_email=st.text_input("Patient email (optional)",key="student_history_email")
        rows=get_cases(search_email)
        if not rows: st.info("No saved cases found.")
        for row in rows[:20]:
            cid,created,email,name,ctype,img,title,report=row
            with st.expander(f"{created} — {name or 'Case'} — {ctype or 'Report'}"):
                st.markdown(report)
                show_export_controls(title or "Saved Case",name or "",report,img or "",ctype or "Saved report")

def doctor_mode():
    header("Doctor Mode","🩺")
    tabs=st.tabs(["🩻 X-ray AI","👄 Soft Tissue","📖 Clinical Library","📜 Patient/Case History"])
    with tabs[0]: radiograph_analyzer()
    with tabs[1]: soft_tissue()
    with tabs[2]: textbook_library()
    with tabs[3]:
        st.markdown("### 📜 Patient / Case History")
        search_email=st.text_input("Search patient email",key="history_email",placeholder="patient@gmail.com")
        rows=get_cases(search_email)
        if not rows:
            st.info("No saved cases found.")
        else:
            st.success(f"{len(rows)} saved case(s) found.")
            for row in rows:
                cid,created,email,name,ctype,img,title,report=row
                with st.expander(f"{created} — {name or 'Case'} — {ctype or 'Report'}"):
                    st.write(f"**Patient:** {name or 'Not provided'}")
                    st.write(f"**Email:** {email or 'Not provided'}")
                    st.write(f"**Image:** {img or 'Not provided'}")
                    st.markdown(report)
                    show_export_controls(title or "Saved Case",name or "",report,img or "",ctype or "Saved report")
                    if email: patient_email_section(report,f"Saved Case {cid}",name or "")

# ============================================================
# HOME
# ============================================================
def home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry</div>',unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">AI-Powered Dental Learning & Clinical Decision-Support Platform</div>',unsafe_allow_html=True)
    if st.button("🦷 Intro to Dental Family",use_container_width=True):
        st.session_state.page="intro"
        st.rerun()
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="mode-card"><h3>🎓 Student Mode</h3><p>Learn, prepare for KUHS exams, use PYQs, quizzes and digital library.</p></div>',unsafe_allow_html=True)
        if st.button("🎓 Enter Student Mode",use_container_width=True): st.session_state.mode="student"; st.session_state.page="student"; st.rerun()
    with c2:
        st.markdown('<div class="mode-card"><h3>🩺 Doctor Mode</h3><p>Radiographic AI, soft-tissue reasoning, clinical support and reports.</p></div>',unsafe_allow_html=True)
        if st.button("🩺 Enter Doctor Mode",use_container_width=True): st.session_state.mode="doctor"; st.session_state.page="doctor"; st.rerun()
    st.markdown('<div class="safety-box"><b>🛡️ Safety Principle</b><br>AI-assisted information only. Final diagnosis and treatment decisions require qualified dental professional assessment.</div>',unsafe_allow_html=True)

def sidebar():
    with st.sidebar:
        st.markdown("## 🦷 Pocket Dentistry")
        if st.session_state.mode: st.write(f"Mode: **{st.session_state.mode.title()}**")
        st.write(f"AI analyses today: {st.session_state.analysis_count}/{DAILY_ANALYSIS_LIMIT}")
        if st.button("🏠 Home",use_container_width=True): st.session_state.mode=None; st.session_state.page="home"; st.rerun()
        if st.button("🦷 Intro to Dental Family",use_container_width=True): st.session_state.page="intro"; st.rerun()
        if st.button("📜 Patient/Case History",use_container_width=True): st.session_state.mode="doctor"; st.session_state.page="history"; st.rerun()

sidebar()
if st.session_state.get("page") == "intro":
    intro_dental_family()
elif st.session_state.get("page") == "history":
    st.session_state.mode = "doctor"
    doctor_mode()
elif st.session_state.mode is None: home()
elif st.session_state.mode=="student": student_mode()
elif st.session_state.mode=="doctor": doctor_mode()
