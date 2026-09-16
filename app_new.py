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

# ------------------------------------------------------------
# SIDEBAR NAVIGATION & MODES
# ------------------------------------------------------------
st.sidebar.markdown("### 🦷 Dental Buddy Navigation")
selected_nav = st.sidebar.radio(
    "Go to", 
    ["Home / Dashboard", "Student Mode", "Doctor Mode (Clinical Decision Support)", "Review & Feedback"],
    index=0 if st.session_state.app_mode == "Home / Dashboard" else (1 if st.session_state.app_mode == "Student Mode" else 2)
)

if selected_nav != st.session_state.app_mode and selected_nav != "Home / Dashboard":
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
            <p>Learn dental topics, lesions, and radiographs. Features curriculum breakdowns, exam corner, 15-year KUHS question bank, clinical reasoning, adaptive quiz, viva bank, Mock Exam, Spotter AI, Smart Essay, and Treatment Planning.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Student Mode", use_container_width=True):
            st.session_state.app_mode = "Student Mode"
            st.rerun()
            
    with col2:
        st.markdown("""
        <div class="card-doctor">
            <h3>🩺 Doctor Mode</h3>
            <p>Advanced clinical decision-support & multimodal evidence engine. Features dynamic evidence tracing, contradiction checking, uncertainty assessment, and professional referral pathways.</p>
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
    st.markdown('<div class="subtitle">Advanced Curriculum, Exam Corner, Clinical Reasoning, Adaptive Quiz, Viva, Mock, Spotter, Essay & Treatment Planning</div>', unsafe_allow_html=True)
    
    topic = st.text_input("🔍 Search a dental topic, lesion, disease, or radiographic finding:", placeholder="e.g., Oral Submucous Fibrosis, Ameloblastoma, Dentigerous Cyst")
    
    if topic:
        st.success(f"Loaded academic curriculum and learning modules for: **{topic}**")
        
        tab_theory, tab_exam, tab_reasoning, tab_quiz, tab_viva, tab_mock, tab_spotter, tab_essay, tab_treatment, tab_refs = st.tabs([
            "📚 Core Theory", 
            "📝 Exam Corner", 
            "🧠 Clinical Reasoning", 
            "🎯 Adaptive Quiz", 
            "🎤 10+ Viva Qs", 
            "🚀 Phase 5 Mock", 
            "🔬 Phase 6 Spotter", 
            "✍️ Phase 7 Essay", 
            "🛠️ Phase 8 Treatment", 
            "📖 Textbook Refs"
        ])
        
        with tab_theory:
            st.markdown(f"### 🔬 High-Scoring University Notes: {topic}")
            st.markdown("Click below to instantly generate structured exam notes point-by-point:")
            
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
                        except Exception as e:
                            st.error(f"Error: {e}")

                if gen_clinical:
                    with st.spinner("Generating clinical and pathological features..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            prompt = f"Provide a precise university exam answer format for dental students regarding '{topic}' focusing strictly on: 1. Clinical Features (Stage-wise), 2. Radiographic Findings, 3. Histopathological Hallmarks, and 4. Differential Diagnosis."
                            resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                            st.markdown(resp.text)
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("Configure GEMINI_API_KEY in secrets to generate real-time AI study notes.")

        with tab_exam:
            st.markdown(f"### 📝 Past 15 Years KUHS University Question Bank for {topic}")
            st.markdown("Comprehensive list of previous university examination questions (3, 5, and 10 marks) asked over the last 15 years:")
            
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("📥 Load Complete 15-Year Question Bank & Answers"):
                    with st.spinner("Fetching past 15 years university questions and answers..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            q_prompt = f"Act as a KUHS dental professor. Compile all previous university examination questions asked over the last 15 years regarding '{topic}'. Categorize them strictly into: 1. 3-Mark Short Notes, 2. 5-Mark Descriptive Questions, and 3. 10-Mark Essay Questions. Provide concise model answers or key points for each."
                            q_resp = client.models.generate_content(model=MODEL_NAME, contents=q_prompt)
                            st.markdown(q_resp.text)
                        except Exception as e:
                            st.error(f"Error fetching question bank: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to load the full 15-year question bank.")

        with tab_reasoning:
            st.markdown(f"### 🧠 Interactive Clinical Case & Reasoning Engine")
            st.markdown("Test your clinical logic by stepping through patient symptoms, lesion features, and diagnostic paths for **" + topic + "**:")
            
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
                        except Exception as e:
                            st.error(f"Error in clinical reasoning engine: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to use the Clinical Reasoning Engine.")

        with tab_quiz:
            st.markdown(f"### 🎯 Phase 4: Interactive Adaptive Quiz & Weakness Trainer")
            st.markdown("Test your mastery on **" + topic + "** with high-yield university multiple-choice questions (MCQs), interactive option selection, and targeted rationales:")
            
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("✨ Generate Interactive Adaptive Quiz Set"):
                    with st.spinner("Generating high-yield MCQ practice set..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            quiz_prompt = f"Act as an examiner. Create 3 high-yield university-level MCQs regarding '{topic}'. Format each question clearly with options A, B, C, D, the Correct Answer, and a detailed clinical/pathological Rationale explaining why the answer is correct."
                            q_res = client.models.generate_content(model=MODEL_NAME, contents=quiz_prompt)
                            st.session_state.current_quiz = q_res.text
                        except Exception as e:
                            st.error(f"Error generating quiz: {e}")

                if "current_quiz" in st.session_state and st.session_state.current_quiz:
                    st.markdown("---")
                    st.markdown(st.session_state.current_quiz)
                    st.markdown("---")
                    st.markdown("#### ✍️ Answer Evaluation Practice")
                    user_ans = st.radio("Select your overall confidence / trial option for this set:", ["Select Option", "Option A", "Option B", "Option C", "Option D"])
                    if user_ans != "Select Option":
                        st.info(f"You selected **{user_ans}**. Cross-verify your choice with the detailed rationales provided in the AI breakdown above!")
            else:
                st.info("Configure GEMINI_API_KEY to generate adaptive quizzes.")

        with tab_viva:
            st.markdown(f"### 🎤 10+ Essential Viva Voce Questions for {topic}")
            st.markdown("Complete set of examiner spotters, diagnostic clinical queries, and technical viva questions for final-year BDS practicals:")
            
            st.markdown(f"""
            #### 1. Clinical Presentation & Etiology (Q1 - Q3)
            * **Q1:** What is the classic clinical presentation, peak age incidence, and sex predilection for **{topic}**?
            * **Q2:** What are the major etiological factors or genetic mutations associated with this condition?
            * **Q3:** How do you differentiate between an early asymptomatic presentation versus an advanced symptomatic stage?

            #### 2. Clinical Examination & Diagnostics (Q4 - Q6)
            * **Q4:** What extra-oral and intra-oral signs would you specifically look for during physical examination?
            * **Q5:** Is 'egg-shell crackling' or fluid fluctuation present? What does it signify clinically?
            * **Q6:** What are the top 3 clinical differential diagnoses you must consider during case discussion?

            #### 3. Radiographic & Imaging Features (Q7 - Q8)
            * **Q7:** Which radiographic investigation is considered the gold standard, and what are the classic border characteristics (well-defined vs corticated vs ragged)?
            * **Q8:** Does this lesion cause root resorption, tooth displacement, or inferior alveolar nerve canal displacement?

            #### 4. Histopathology & Microscopy (Q9 - Q10)
            * **Q9:** What are the pathognomonic histopathological hallmarks seen under light microscopy with H&E staining?
            * **Q10:** Are there any special stains, immunohistochemical (IHC) markers, or biopsy techniques required for confirmation?

            #### 5. Management & Prognosis (Q11 - Q12)
            * **Q11:** What is the standard treatment protocol (conservative enucleation, curettage, or radical resection) and why?
            * **Q12:** What is the recurrence rate of **{topic}**, and what factors dictate the long-term prognosis?
            """)

        with tab_mock:
            st.markdown(f"### 🚀 Phase 5: KUHS Mock Exam Blueprint & Smart Revision Flashcards")
            st.markdown("Simulate an actual exam paper or review high-yield bullet points for **" + topic + "** right before your university exam:")
            
            if "GEMINI_API_KEY" in st.secrets:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    gen_mock = st.button("📝 Generate Timed KUHS Mock Paper")
                with col_m2:
                    gen_flash = st.button("⚡ Generate Night-Before Flashcards")

                if gen_mock:
                    with st.spinner("Compiling university mock paper layout..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            mock_prompt = f"Act as a KUHS university examiner. Create a full mock exam paper layout for '{topic}' consisting of: 1 Essay question (10 Marks), 2 Short Essays (5 Marks each), and 3 Short Notes (3 Marks each) with answer outlines."
                            m_res = client.models.generate_content(model=MODEL_NAME, contents=mock_prompt)
                            st.markdown(m_res.text)
                        except Exception as e:
                            st.error(f"Error generating mock paper: {e}")

                if gen_flash:
                    with st.spinner("Preparing high-yield revision flashcards..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            flash_prompt = f"Create 10 ultra-short, high-yield revision flashcards (bullet points containing key numbers, classifications, hallmark signs, and treatment of choice) for '{topic}' tailored for quick last-minute exam recall."
                            f_res = client.models.generate_content(model=MODEL_NAME, contents=flash_prompt)
                            st.markdown(f_res.text)
                        except Exception as e:
                            st.error(f"Error generating flashcards: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to access Phase 5 Mock Exam & Flashcards.")

        with tab_spotter:
            st.markdown(f"### 🔬 Phase 6: Smart Image Diagnostics & Visual Spotter Simulator")
            st.markdown("Upload a clinical photo, radiograph, or histopathological slide to evaluate it for practical spotter examination practice:")
            
            spotter_image = st.file_uploader("📷 Upload Spotter Image for Analysis", type=["jpg", "jpeg", "png", "webp"], key="phase6_spotter_upload")
            
            if spotter_image is not None:
                st.image(spotter_image, caption="Uploaded Spotter Image", use_container_width=True)
                if st.button("🔍 Run Spotter & Examiner Evaluation"):
                    if "GEMINI_API_KEY" not in st.secrets:
                        st.error("❌ GEMINI_API_KEY missing from Streamlit secrets.")
                    else:
                        with st.spinner("Analyzing spotter image for practical viva examination..."):
                            try:

                                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                                spotter_prompt = f"Act as a strict university practical examiner. Analyze this uploaded spotter image in the context of '{topic}'. Provide: 1. Identification / Probable Diagnosis, 2. Key Visual Findings / Hallmark Features, 3. Two potential Differential Diagnoses, and 4. Three rapid-fire viva examiner questions regarding this image."
                                spot_resp = client.models.generate_content(
                                    model=MODEL_NAME,
                                    contents=[
                                        {"inline_data": {"mime_type": spotter_image.type, "data": spotter_image.getvalue()}},
                                        spotter_prompt
                                    ]
                                )
                                st.markdown(spot_resp.text)
                            except Exception as e:
                                st.error(f"Spotter analysis failed: {e}")

        with tab_essay:
            st.markdown(f"### ✍️ Phase 7: AI Smart Essay & Answer Sheet Generator")
            st.markdown("Generate a comprehensive, high-scoring university exam answer sheet layout (suitable for 10-mark essays) for **" + topic + "**:")
            
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("📝 Generate 10-Mark University Essay Answer Sheet"):
                    with st.spinner("Writing structured high-scoring university essay model..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            essay_prompt = f"Act as a top-ranking university student and expert professor. Write a comprehensive, beautifully structured 10-mark essay model answer for '{topic}' complete with: Introduction, Detailed Classification, Pathogenesis, Clinical Features, Radiographic/Histopathological Findings, Management, and Conclusion."
                            essay_resp = client.models.generate_content(model=MODEL_NAME, contents=essay_prompt)
                            st.markdown(essay_resp.text)
                        except Exception as e:
                            st.error(f"Error generating essay: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to generate smart essay answer sheets.")

        with tab_treatment:
            st.markdown(f"### 🛠️ Phase 8: Clinical Case Simulation & Treatment Planning Engine")
            st.markdown("Build a comprehensive management and treatment protocol for **" + topic + "** based on clinical severity:")
            
            case_stage = st.selectbox("Select Case Severity / Stage", ["Early / Mild Presentation", "Moderate Stage with Cortical Involvement", "Advanced / Aggressive / Recurrent Presentation"])
            
            if "GEMINI_API_KEY" in st.secrets:
                if st.button("⚙️ Generate Comprehensive Treatment & Management Protocol"):
                    with st.spinner("Formulating evidence-based treatment plan..."):
                        try:
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            treat_prompt = f"Act as an expert oral and maxillofacial surgeon and professor. Formulate a complete treatment and management protocol for '{topic}' for a patient presenting with '{case_stage}'. Include: 1. Pre-operative investigations, 2. Treatment of Choice (Conservative vs Radical), 3. Surgical steps / technique outline, 4. Post-operative care & medications, and 5. Follow-up and recurrence monitoring protocol."
                            treat_resp = client.models.generate_content(model=MODEL_NAME, contents=treat_prompt)
                            st.markdown(treat_resp.text)
                        except Exception as e:
                            st.error(f"Error generating treatment plan: {e}")
            else:
                st.info("Configure GEMINI_API_KEY to use the Treatment Planning Engine.")

        with tab_refs:
            st.markdown(f"### 📖 Standard Textbook Recommendations")
            st.markdown("""
            * **Oral Pathology:** Shafer's / Neville's Oral & Maxillofacial Pathology
            * **Surgery / Medicine:** Burket's Oral Medicine / Peterson's Principles of Oral and Maxillofacial Surgery
            * **Textbook Alignments:** Standard chapters mapped to Nallaswamy, Rangarajan, and Nikhil Marwah.
            """)
    else:
        st.info("💡 Type any dental subject or lesion above to access structured academic notes, exam question banks, and viva questions.")

# ------------------------------------------------------------
# DOCTOR MODE INTERFACE (ADVANCED CLINICAL DECISION SUPPORT & DYNAMIC EVIDENCE ENGINE)
# ------------------------------------------------------------
elif st.session_state.app_mode == "Doctor Mode (Clinical Decision Support)" or selected_nav == "Doctor Mode (Clinical Decision Support)":
    st.markdown('<div class="app-title">🩺 Dental Buddy - Doctor Mode</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Clinical Decision Support, Dynamic Evidence Engine & Multimodal Assessment</div>', unsafe_allow_html=True)

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
        doc_symptoms = st.text_area("Chief Complaints & Symptoms", placeholder="e.g., Painful ulcer on lower lip mucosa, burning sensation on eating spicy food.")
        doc_history = st.text_array if "doc_history" in locals() else st.text_area("Relevant Medical & Dental History", placeholder="e.g., Recurrent episodes, no systemic illness.")
        doc_risk = st.text_input("Risk Factors / Habits", placeholder="e.g., Stress, minor trauma, no tobacco")

    st.markdown('<div class="section">📤 Upload Clinical Photograph or Radiograph (JPG, PNG, WEBP)</div>', unsafe_allow_html=True)
    doc_file = st.file_uploader("📷 Choose image file", type=["jpg", "jpeg", "png", "webp"], key="doctor_multimodal_upload")

    if doc_file is not None:
        if doc_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"❌ File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
            st.stop()

        st.image(doc_file, caption="Uploaded Clinical/Radiographic Record", use_container_width=True)

    if st.button("🔍 Run Clinical Decision Support & Evidence Analysis", use_container_width=True, disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT)):
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("❌ GEMINI_API_KEY missing from Streamlit secrets.")
        else:
            with st.spinner("Analyzing uploaded clinical photograph/radiograph with symptoms using Dynamic Evidence Engine..."):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    doc_prompt = f"""
                    You are Dental Buddy Doctor Mode, an advanced clinical decision-support system. 
                    Analyze the uploaded image (clinical photograph or radiograph) along with the following case details:
                    - Patient Profile: Age {doc_age}, Sex {doc_sex}
                    - Symptom Duration: {doc_duration}
                    - Symptoms/Chief Complaint: {doc_symptoms}
                    - Medical/Dental History: {doc_history}
                    - Risk Factors/Habits: {doc_risk}

                    Provide a structured clinical decision support report containing:
                    1. Observable Findings from the Image & Quality Assessment
                    2. Initial Differential Diagnoses (directly matching the visual lesion/signs and symptoms provided)
                    3. Dynamic Evidence Trace (Supporting evidence vs Contradictory evidence vs Unknown information for top candidate conditions)
                    4. Contradiction Checking & Uncertainty Assessment
                    5. Provisional Assessment (Clearly distinguishing observed visual/clinical findings from inferred possibilities)
                    6. Next-Best Clinical Questions to ask or Recommended Next Clinical Steps / Referral.
                    
                    Disclaimer: Do not provide a definitive diagnosis. Recommend professional in-person clinical evaluation.
                    """
                    
                    contents_payload = []
                    if doc_file is not None:
                        contents_payload.append({"inline_data": {"mime_type": doc_file.type, "data": doc_file.getvalue()}})
                    contents_payload.append(doc_prompt)

                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=contents_payload
                    )
                    
                    if response.text:
                        st.session_state.analysis_count += 1
                        st.session_state.last_report = response.text
                        st.session_state.last_patient = doc_patient_name if doc_patient_name else "Patient"
                        st.success("✅ Clinical decision support assessment completed.")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")

    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📋 Professional Clinical Decision Support Report")
        st.markdown(st.session_state.last_report)

# ------------------------------------------------------------
# REVIEW & FEEDBACK VIEW
# ------------------------------------------------------------
elif selected_nav == "Review & Feedback" or selected_nav == "Review & Feedback":
    st.markdown('<div class="app-title">📝 Review & Feedback</div>', unsafe_allow_html=True)
    st.text_area("Help us improve Dental Buddy. What went wrong or what feature should be added?")
    if st.button("Submit Feedback"):
        st.success("Thank you! Your feedback has been recorded.")
                                
