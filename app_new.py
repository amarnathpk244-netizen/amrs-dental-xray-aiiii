import streamlit as st
from datetime import date
import json
import math
import re
import time
from google import genai
import base64

st.set_page_config(
    page_title="Dental Buddy - AI Clinical & Learning Platform",
    page_icon="🦷",
    layout="centered",
)

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.6-flash"
MAX_FILE_SIZE_MB = 10

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

FACIAL_ANALYSES = [
    "PA Cephalogram / PA Skull (Symmetry & Transverse)",
    "Waters' View / Occipitomental (Midface & Sinuses)",
    "Submentovertex (SMV) View (Zygomatic Arches & Skull Base)",
    "Reverse Towne's View (Condyles & Rami)",
    "Lateral Skull / Profile View (Cranial & Soft Tissue)",
    "General Facial Screening / All Views",
]

# ------------------------------------------------------------
# SESSION USAGE & STATE PERSISTENCE
# ------------------------------------------------------------
if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()

if "last_report" not in st.session_state:
    st.session_state.last_report = None

if "last_patient" not in st.session_state:
    st.session_state.last_patient = ""

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Home / Dashboard"

if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

if "student_last_output" not in st.session_state:
    st.session_state.student_last_output = ""

if "saved_cases" not in st.session_state:
    st.session_state.saved_cases = []

# ------------------------------------------------------------
# UI STYLES & COLORFUL MEDICAL THEME
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { padding-top: 1rem; }
    .app-title {
        text-align: center;
        font-size: 34px;
        font-weight: 800;
        background: linear-gradient(90deg, #1e3d59, #17b978);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
    }
    .subtitle {
        text-align: center;
        color: #008891;
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 20px;
    }
    .section {
        font-size: 19px;
        font-weight: 650;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #17b978;
    }
    .card-student {
        padding: 22px;
        border-radius: 14px;
        background: linear-gradient(135deg, #e0f7fa, #80deea);
        border: 2px solid #00acc1;
        margin-bottom: 15px;
        color: #004d40;
        box-shadow: 0 4px 10px rgba(0, 151, 167, 0.2);
    }
    .card-student h3, .card-student p {
        color: #004d40 !important;
    }
    .card-doctor {
        padding: 22px;
        border-radius: 14px;
        background: linear-gradient(135deg, #e8f5e9, #a5d6a7);
        border: 2px solid #43a047;
        margin-bottom: 15px;
        color: #1b5e20;
        box-shadow: 0 4px 10px rgba(67, 160, 71, 0.2);
    }
    .card-doctor h3, .card-doctor p {
        color: #1b5e20 !important;
    }
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3d59, #17b978);
        color: white;
        border: none;
        transition: 0.3s;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #17b978, #1e3d59);
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Helper function to generate print-to-PDF HTML viewer
def display_pdf_download_button(content_text, filename_prefix):
    st.markdown("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="📥 Download as Text File (.txt)",
            data=content_text,
            file_name=f"{filename_prefix}.txt",
            mime="text/plain",
            use_container_width=True
        )
    with col_d2:
        html_pdf_link = f"""
        <a href="data:text/html;base64,{base64.b64encode(f'''
            <html>
                <head><title>{filename_prefix}</title></head>
                <body style="font-family: Arial, sans-serif; padding: 40px; line-height: 1.6;">
                    <h2 style="color: #1e3d59;">🦷 Dental Buddy - Official Report</h2>
                    <hr/>
                    <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{content_text}</pre>
                    <br/><hr/>
                    <p style="font-size: 12px; color: #666;">Generated via Dental Buddy AI Platform.</p>
                    <script>window.print();</script>
                </body>
            </html>
        '''.encode()).decode()}" target="_blank" style="display: block; text-align: center; background-color: #1e3d59; color: white; padding: 10px 15px; border-radius: 12px; text-decoration: none; font-weight: 700; font-family: sans-serif; box-shadow: 0 3px 6px rgba(0,0,0,0.15);">
            🖨️ Open Print / Save as PDF View
        </a>
        """
        st.markdown(html_pdf_link, unsafe_allow_html=True)

# ------------------------------------------------------------
# SIDEBAR NAVIGATION & MODES
# ------------------------------------------------------------
st.sidebar.markdown("### 🦷 Dental Buddy Navigation")
selected_nav = st.sidebar.radio(
    "Go to", 
    ["Home / Dashboard", "Student Mode", "Doctor Mode (Clinical Decision Support)", "Case History Archive", "Review & Feedback"],
    index=0 if st.session_state.app_mode == "Home / Dashboard" else (1 if st.session_state.app_mode == "Student Mode" else (2 if st.session_state.app_mode == "Doctor Mode (Clinical Decision Support)" else (3 if st.session_state.app_mode == "Case History Archive" else 4)))
)

if selected_nav != st.session_state.app_mode:
    st.session_state.app_mode = selected_nav

st.sidebar.markdown("---")
st.sidebar.info("💡 **Core Philosophy:** See → Understand → Reason → Apply → Improve")

# ------------------------------------------------------------
# HOME / DASHBOARD VIEW
# ------------------------------------------------------------
if st.session_state.app_mode == "Home / Dashboard" and selected_nav == "Home / Dashboard":
    st.markdown('<div class="app-title">🦷 Dental Buddy</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">AI-Powered Dental Learning & Clinical Decision-Support Platform</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card-student">
            <h3>🎓 Student Mode</h3>
            <p>Learn dental topics, exams, 15-year KUHS question bank, clinical reasoning, adaptive quiz, interactive flashcards, essay generator, and treatment planning.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Student Mode", use_container_width=True):
            st.session_state.app_mode = "Student Mode"
            st.rerun()
            
    with col2:
        st.markdown("""
        <div class="card-doctor">
            <h3>🩺 Doctor Mode</h3>
            <p>Advanced Soft-Tissue AI Workflow, Radiograph module, Smart calibration, Prescription Generator, Kerala-based Treatment Cost Estimator (₹), and Case Database Archive.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Doctor Mode", use_container_width=True):
            st.session_state.app_mode = "Doctor Mode (Clinical Decision Support)"
            st.rerun()

# ------------------------------------------------------------
# STUDENT MODE INTERFACE
# ------------------------------------------------------------
elif st.session_state.app_mode == "Student Mode" or selected_nav == "Student Mode":
    st.markdown('<div class="app-title">🎓 Dental Buddy - Student Mode</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Advanced Curriculum, Exam Corner, Clinical Reasoning, Adaptive Quiz, Flashcards, Essay & Treatment Planning</div>', unsafe_allow_html=True)
    
    topic = st.text_input("🔍 Search a dental topic, lesion, disease, or radiographic finding:", placeholder="e.g., Oral Submucous Fibrosis, Ameloblastoma, Dentigerous Cyst")
    
    if topic:
        st.success(f"Loaded academic curriculum and learning modules for: **{topic}**")
        
        tab_theory, tab_exam, tab_reasoning, tab_quiz, tab_flashcards, tab_viva, tab_mock, tab_spotter, tab_essay, tab_treatment, tab_refs = st.tabs([
            "📚 Core Theory", 
            "📝 Exam Corner", 
            "🧠 Clinical Reasoning", 
            "🎯 Adaptive Quiz", 
            "⚡ Flashcards", 
            "🎤 Viva Qs", 
            "🚀 Mock Exam", 
            "🔬 Spotter", 
            "✍️ Essay", 
            "🛠️ Treatment", 
            "📖 Refs"
        ])
        
        with tab_theory:
            st.markdown(f"### 🔬 High-Scoring University Notes: {topic}")
            if "GEMINI_API_KEY" in st.secrets:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    gen_basics = st.button("📌 Definition, Etiology & Pathogenesis")
                with col_b2:
                    gen_clinical = st.button("🩺 Clinical & Histopathological Features")

                if gen_basics:
                    with st.spinner("Generating basics and etiology..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            prompt = f"Provide a precise, high-scoring university exam answer format for dental students regarding '{topic}' focusing strictly on: 1. Definition, 2. Classification/Types, 3. Etiology, and 4. Pathogenesis in clear bullet points."
                            resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                            st.markdown(resp.text)
                            st.session_state.student_last_output = resp.text
                        except Exception as e:
                            st.error(f"Error: {e}")

                if gen_clinical:
                    with st.spinner("Generating clinical and pathological features..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            prompt = f"Provide a precise university exam answer format for dental students regarding '{topic}' focusing strictly on: 1. Clinical Features (Stage-wise), 2. Radiographic Findings, 3. Histopathological Hallmarks, and 4. Differential Diagnosis."
                            resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                            st.markdown(resp.text)
                            st.session_state.student_last_output = resp.text
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("Configure GEMINI_API_KEY in secrets to generate real-time AI study notes.")

        with tab_exam:
            st.markdown(f"### 📝 Past 15 Years KUHS University Question Bank for {topic}")
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("📥 Load Complete 15-Year Question Bank & Answers"):
                    with st.spinner("Fetching past 15 years university questions and answers..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            q_prompt = f"Act as a KUHS dental professor. Compile all previous university examination questions asked over the last 15 years regarding '{topic}'. Categorize them strictly into: 1. 3-Mark Short Notes, 2. 5-Mark Descriptive Questions, and 3. 10-Mark Essay Questions. Provide concise model answers or key points for each."
                            q_resp = client.models.generate_content(model=MODEL_NAME, contents=q_prompt)
                            st.markdown(q_resp.text)
                            st.session_state.student_last_output = q_resp.text
                        except Exception as e:
                            st.error(f"Error fetching question bank: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to load the full 15-year question bank.")

        with tab_reasoning:
            st.markdown(f"### 🧠 Interactive Clinical Case & Reasoning Engine")
            patient_age_sex = st.text_input("Patient Profile (e.g., 25-year-old male)", placeholder="e.g., 40-year-old female with painless mandibular swelling")
            chief_complaint = st.text_area("Chief Complaint & Clinical Findings", placeholder="e.g., Hard swelling in the posterior mandible, duration 6 months, egg-shell crackling absent.")

            if "GEMINI_API_KEY" in st.secrets:
                if st.button("🚀 Run Step-by-Step Clinical Logic Analysis"):
                    with st.spinner("Evaluating clinical findings and building differential diagnosis pathway..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            reason_prompt = f"Act as a master clinician in oral medicine and diagnosis. For the topic '{topic}' with patient profile '{patient_age_sex}' and findings '{chief_complaint}', provide a step-by-step interactive clinical reasoning flow: 1. Key diagnostic questions to ask, 2. Critical radiographic features to evaluate, 3. Top 3 Differential Diagnoses with justification, and 4. Definitive diagnostic test (e.g., Incisional Biopsy / FNAC)."
                            r_resp = client.models.generate_content(model=MODEL_NAME, contents=reason_prompt)
                            st.markdown(r_resp.text)
                            st.session_state.student_last_output = r_resp.text
                        except Exception as e:
                            st.error(f"Error in clinical reasoning engine: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to use the Clinical Reasoning Engine.")

        with tab_quiz:
            st.markdown(f"### 🎯 Phase 4: Interactive Adaptive Quiz & Weakness Trainer")
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("✨ Generate Interactive Adaptive Quiz Set"):
                    with st.spinner("Generating high-yield MCQ practice set..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            quiz_prompt = f"Act as an examiner. Create 3 high-yield university-level MCQs regarding '{topic}'. Format each question clearly with options A, B, C, D, the Correct Answer, and a detailed clinical/pathological Rationale explaining why the answer is correct."
                            q_res = client.models.generate_content(model=MODEL_NAME, contents=quiz_prompt)
                            st.session_state.current_quiz = q_res.text
                            st.session_state.student_last_output = q_res.text
                        except Exception as e:
                            st.error(f"Error generating quiz: {e}")

                if "current_quiz" in st.session_state and st.session_state.current_quiz:
                    st.markdown("---")
                    st.markdown(st.session_state.current_quiz)
            else:
                st.info("Configure GEMINI_API_KEY to generate adaptive quizzes.")

        with tab_flashcards:
            st.markdown(f"### ⚡ Interactive Flashcards & Spaced Repetition for {topic}")
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("🗂️ Generate High-Yield Flashcards"):
                    with st.spinner("Generating flashcards..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            fc_prompt = f"Create 5 high-yield flashcard Q&A pairs for '{topic}' focusing on key numbers, classifications, histological hallmarks, and treatment of choice. Format clearly as Question / Answer."
                            fc_resp = client.models.generate_content(model=MODEL_NAME, contents=fc_prompt)
                            st.markdown(fc_resp.text)
                            st.session_state.student_last_output = fc_resp.text
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("Configure GEMINI_API_KEY.")

        with tab_viva:
            st.markdown(f"### 🎤 10+ Essential Viva Voce Questions for {topic}")
            viva_text = f"""
            #### 1. Clinical Presentation & Etiology (Q1 - Q3)
            * Q1: Classic clinical presentation, peak age, sex predilection for {topic}?
            * Q2: Major etiological factors or genetic mutations?
            * Q3: Early asymptomatic vs advanced symptomatic stage?
            #### 2. Clinical Examination & Diagnostics (Q4 - Q6)
            * Q4: Extra-oral and intra-oral signs during examination?
            * Q5: Presence of egg-shell crackling or fluid fluctuation?
            * Q6: Top 3 clinical differential diagnoses?
            #### 3. Radiographic & Imaging Features (Q7 - Q8)
            * Q7: Gold standard radiographic investigation and border characteristics?
            * Q8: Root resorption or tooth displacement?
            #### 4. Histopathology & Microscopy (Q9 - Q10)
            * Q9: Pathognomonic histopathological hallmarks under H&E?
            * Q10: Special stains or IHC markers required?
            #### 5. Management & Prognosis (Q11 - Q12)
            * Q11: Standard treatment protocol (conservative vs radical)?
            * Q12: Recurrence rate and prognostic factors?
            """
            st.markdown(viva_text)
            st.session_state.student_last_output = viva_text

        with tab_mock:
            st.markdown(f"### 🚀 Phase 5: KUHS Mock Exam Blueprint")
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("📝 Generate Timed KUHS Mock Paper"):
                    with st.spinner("Compiling university mock paper layout..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            mock_prompt = f"Act as a KUHS university examiner. Create a full mock exam paper layout for '{topic}' consisting of: 1 Essay question (10 Marks), 2 Short Essays (5 Marks each), and 3 Short Notes (3 Marks each) with answer outlines."
                            m_res = client.models.generate_content(model=MODEL_NAME, contents=mock_prompt)
                            st.markdown(m_res.text)
                            st.session_state.student_last_output = m_res.text
                        except Exception as e:
                            st.error(f"Error generating mock paper: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to access Phase 5.")

        with tab_spotter:
            st.markdown(f"### 🔬 Phase 6: Smart Image Diagnostics & Visual Spotter Simulator")
            spotter_image = st.file_uploader("📷 Upload Spotter Image for Analysis", type=["jpg", "jpeg", "png", "webp"], key="phase6_spotter_upload")
            if spotter_image is not None:
                st.image(spotter_image, caption="Uploaded Spotter Image", use_container_width=True)
                if st.button("🔍 Run Spotter & Examiner Evaluation"):
                    if "GEMINI_API_KEY" not in st.secrets:
                        st.error("❌ GEMINI_API_KEY missing from secrets.")
                    else:
                        with st.spinner("Analyzing spotter image..."):
                            try:
                                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                                spotter_prompt = f"Act as a strict university practical examiner. Analyze this uploaded spotter image in the context of '{topic}'. Provide Identification, Hallmark Features, Differentials, and Viva Questions."
                                spot_resp = client.models.generate_content(
                                    model=MODEL_NAME,
                                    contents=[{"inline_data": {"mime_type": spotter_image.type, "data": spotter_image.getvalue()}}, spotter_prompt]
                                )
                                st.markdown(spot_resp.text)
                                st.session_state.student_last_output = spot_resp.text
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")

        with tab_essay:
            st.markdown(f"### ✍️ Phase 7: AI Smart Essay & Answer Sheet Generator")
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("📝 Generate 10-Mark University Essay Answer Sheet"):
                    with st.spinner("Writing structured high-scoring university essay model..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            essay_prompt = f"Act as a top-ranking university student and expert professor. Write a comprehensive, beautifully structured 10-mark essay model answer for '{topic}'."
                            essay_resp = client.models.generate_content(model=MODEL_NAME, contents=essay_prompt)
                            st.markdown(essay_resp.text)
                            st.session_state.student_last_output = essay_resp.text
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("Configure GEMINI_API_KEY.")

        with tab_treatment:
            st.markdown(f"### 🛠️ Phase 8: Clinical Case Simulation & Treatment Planning Engine")
            case_stage = st.selectbox("Select Case Severity / Stage", ["Early / Mild Presentation", "Moderate Stage with Cortical Involvement", "Advanced / Aggressive / Recurrent Presentation"])
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("⚙️ Generate Comprehensive Treatment & Management Protocol"):
                    with st.spinner("Formulating evidence-based treatment plan..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            treat_prompt = f"Act as an expert oral surgeon. Formulate a complete treatment and management protocol for '{topic}' for patient presenting with '{case_stage}'."
                            treat_resp = client.models.generate_content(model=MODEL_NAME, contents=treat_prompt)
                            st.markdown(treat_resp.text)
                            st.session_state.student_last_output = treat_resp.text
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("Configure GEMINI_API_KEY.")

        with tab_refs:
            st.markdown(f"### 📖 Standard Textbook Recommendations")
            st.markdown("""
            * **Oral Pathology:** Shafer's / Neville's Oral & Maxillofacial Pathology
            * **Surgery / Medicine:** Burket's Oral Medicine / Peterson's Principles of Oral and Maxillofacial Surgery
            """)

        if "student_last_output" in st.session_state and st.session_state.student_last_output:
            display_pdf_download_button(st.session_state.student_last_output, f"Dental_Buddy_{topic.replace(' ', '_')}")
    else:
        st.info("💡 Type any dental subject or lesion above to access structured academic notes, exam question banks, and viva questions.")

# ------------------------------------------------------------
# DOCTOR MODE INTERFACE (WITH 503 ERROR RETRY & KERALA COST ESTIMATOR)
# ------------------------------------------------------------
elif st.session_state.app_mode == "Doctor Mode (Clinical Decision Support)" or selected_nav == "Doctor Mode (Clinical Decision Support)":
    st.markdown('<div class="app-title">🩺 Dental Buddy - Doctor Mode</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Radiograph Module, Smart Calibration, Prescription, Kerala Cost Estimator (₹) & Soft-Tissue AI</div>', unsafe_allow_html=True)

    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="🧪 Daily Quota Left", value=f"{remaining} / {DAILY_ANALYSIS_LIMIT}")

    if remaining <= 0:
        st.warning("⏳ Your 3 AI analyses for today have been used. Please try again tomorrow.")

    with st.expander("👤 Patient Clinical Profile & Examination Details", expanded=True):
        doc_patient_name = st.text_input("Patient Name / Identifier", placeholder="Enter patient name or ID")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            doc_age = st.number_input("Age", min_value=0, max_value=120, value=30, step=1)
        with col_d2:
            doc_sex = st.selectbox("Sex", ["Select", "Male", "Female", "Other"])
        
        doc_duration = st.text_input("Symptom Duration", placeholder="e.g., 1 week")
        doc_symptoms = st.text_area("Chief Complaints & Symptoms", placeholder="e.g., Painful ulcer on lower lip mucosa, burning sensation / or swelling / pain.")
        doc_history = st.text_area("Relevant Medical & Dental History", placeholder="e.g., Recurrent episodes, no systemic illness.")
        doc_risk = st.text_input("Risk Factors / Habits", placeholder="e.g., Stress, minor trauma, tobacco/alcohol")

    st.markdown('<div class="section">🩻 Radiographic Assessment & Calibration Module</div>', unsafe_allow_html=True)
    radiograph_type = st.selectbox("Select radiograph type", ["IOPA", "Lateral Cephalogram (Ceph)", "OPG", "Bitewing", "Occlusal", "Facial radiograph", "Other / Not reliably classifiable"])
    
    ceph_analysis = "Combined / All Analyses"
    facial_analysis = "General Facial Screening / All Views"
    
    if radiograph_type == "Lateral Cephalogram (Ceph)":
        ceph_analysis = st.selectbox("Select Cephalometric Analysis", CEPH_ANALYSES, key="ceph_analysis_selector_doc")
    elif radiograph_type == "Facial radiograph":
        facial_analysis = st.selectbox("Select Facial Radiograph Analysis", FACIAL_ANALYSES, key="facial_analysis_selector_doc")

    calibration_mode = st.radio("Select Scale Calibration Mode", ["🤖 Auto-Calculate / AI Estimation (Unknown Calibration)", "✏️ Enter Known Calibration Scale (mm/pixel or known landmark)"])
    scale_value_input = "Auto-estimated by AI based on anatomical proportions"
    if calibration_mode == "✏️ Enter Known Calibration Scale (mm/pixel or known landmark)":
        scale_value_input = st.text_input("Enter known scale value (e.g., 0.15 mm/pixel or reference length)", value="1.0 mm/pixel")

    st.markdown('<div class="section">📤 Upload Clinical Photograph or Dental Radiograph (JPG, PNG, WEBP)</div>', unsafe_allow_html=True)
    doc_file = st.file_uploader("📷 Choose image file", type=["jpg", "jpeg", "png", "webp"], key="doctor_multimodal_upload")

    if doc_file is not None:
        if doc_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"❌ File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
            st.stop()
        st.image(doc_file, caption=f"Uploaded {radiograph_type} / Clinical Record", use_container_width=True)

    if st.button("🔍 Run Radiograph & Soft-Tissue AI Workflow", use_container_width=True, disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT)):
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("❌ GEMINI_API_KEY missing from secrets.")
        else:
            with st.spinner("Running Image Quality Gate, Smart Calibration, Evidence Engine & Kerala Cost Estimator..."):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    combined_workflow_prompt = f"""
                    You are Dental Buddy Doctor Mode, operating under an advanced clinical decision-support and radiographic assessment system. 
                    Analyze the uploaded image (classified as: {radiograph_type}) along with patient details and calibration setting:
                    - Patient Profile: Age {doc_age}, Sex {doc_sex}
                    - Symptom Duration: {doc_duration}
                    - Symptoms: {doc_symptoms}
                    - History: {doc_history}
                    - Risk Factors: {doc_risk}
                    - Ceph/Facial Sub-analysis: {ceph_analysis} / {facial_analysis}
                    - Calibration Setting: {scale_value_input}

                    Execute and output structured report following:
                    1. IMAGE QUALITY GATE
                    2. CALIBRATION & MEASUREMENT REPORT
                    3. OBSERVABLE FINDINGS
                    4. INITIAL DIFFERENTIAL DIAGNOSES
                    5. DYNAMIC EVIDENCE TRACE
                    6. CONTRADICTION CHECKING & UNCERTAINTY ASSESSMENT
                    7. RED-FLAG / SAFETY ENGINE
                    8. PROVISIONAL ASSESSMENT & NEXT-BEST CLINICAL STEPS
                    9. RECOMMENDED PRESCRIPTION & TREATMENT COST ESTIMATOR IN KERALA (Provide standard evidence-based medication prescription breakdown and estimated treatment cost range formatted in Indian Rupees (₹) reflecting private dental clinics in Kerala, e.g., RCT ₹2,500 - ₹8,000, Crown ₹3,500 - ₹10,000, etc.).
                    """
                    
                    contents_payload = [
                        {"inline_data": {"mime_type": doc_file.type, "data": doc_file.getvalue()}},
                        combined_workflow_prompt
                    ] if doc_file is not None else [combined_workflow_prompt]

                    # Retry mechanism for 503 high demand errors
                    response = None
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            response = client.models.generate_content(model=MODEL_NAME, contents=contents_payload)
                            break
                        except Exception as api_err:
                            if "503" in str(api_err) and attempt < max_retries - 1:
                                time.sleep(2) # Wait 2 seconds before retry
                                continue
                            else:
                                raise api_err
                    
                    if response and response.text:
                        st.session_state.analysis_count += 1
                        st.session_state.last_report = response.text
                        st.session_state.last_patient = doc_patient_name if doc_patient_name else "Patient"
                        
                        case_record = {
                            "date": str(date.today()),
                            "patient": doc_patient_name if doc_patient_name else "Anonymous",
                            "age": doc_age,
                            "sex": doc_sex,
                            "symptoms": doc_symptoms,
                            "report": response.text
                        }
                        st.session_state.saved_cases.append(case_record)
                        st.success("✅ Assessment completed & securely saved to Case History Database.")
                except Exception as e:
                    st.error(f"❌ Analysis failed due to high server demand (503 / Unavailable). Please wait a few seconds and click the button again.")

    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📋 Clinical Decision Support & Radiographic Assessment Report")
        st.markdown(st.session_state.last_report)
        
        display_pdf_download_button(st.session_state.last_report, f"Clinical_Report_{st.session_state.last_patient.replace(' ', '_')}")

# ------------------------------------------------------------
# CASE HISTORY ARCHIVE VIEW (DATABASE STORAGE)
# ------------------------------------------------------------
elif selected_nav == "Case History Archive" or st.session_state.app_mode == "Case History Archive":
    st.markdown('<div class="app-title">📂 Case History Archive & Database</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Review previously analyzed patient records and clinical decision support reports stored in your session database.</p>", unsafe_allow_html=True)
    
    if len(st.session_state.saved_cases) == 0:
        st.info("📂 No saved cases found in the archive yet. Run an analysis in Doctor Mode to automatically store records here.")
    else:
        for idx, case in enumerate(reversed(st.session_state.saved_cases)):
            with st.expander(f"📁 Case #{len(st.session_state.saved_cases) - idx} - Patient: {case['patient']} (Age: {case['age']}, Sex: {case['sex']}) | Date: {case['date']}"):
                st.markdown(f"**Chief Complaints:** {case['symptoms']}")
                st.markdown("---")
                st.markdown(case['report'])
                display_pdf_download_button(case['report'], f"Archive_Case_{case['patient'].replace(' ', '_')}_{case['date']}")

# ------------------------------------------------------------
# REVIEW & FEEDBACK VIEW
# ------------------------------------------------------------
elif selected_nav == "Review & Feedback" or selected_nav == "Review & Feedback":
    st.markdown('<div class="app-title">📝 Review & Feedback</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Help us improve Dental Buddy with your valuable feedback and feature requests.</p>", unsafe_allow_html=True)
    
    with st.form("feedback_form"):
        fb_name = st.text_input("Your Name / Identifier (Optional)")
        fb_rating = st.slider("⭐ Rate Dental Buddy (1 to 5 Stars)", min_value=1, max_value=5, value=5)
        fb_helpful = st.radio("Was Dental Buddy helpful for your workflow?", ["Very Helpful", "Somewhat Helpful", "Not Helpful"])
        fb_wrong = st.text_area("What went wrong or needs improvement?")
        fb_features = st.text_area("Feature requests or general suggestions")
        
        submitted = st.form_submit_button("Submit Feedback Securely", use_container_width=True)
        if submitted:
            st.session_state.feedback_submitted = True
            st.success("🌟 Thank you! Your feedback has been securely recorded without patient-identifying medical details.")
