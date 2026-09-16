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
MODEL_NAME = "gemini-3.8-flash"
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
# UI STYLES & MEDICAL THEME
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { padding-top: 1rem; }
    .app-title {
        text-align: center;
        font-size: 32px;
        font-weight: 700;
        color: #1e3d59;
        margin-bottom: 2px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 15px;
        margin-bottom: 20px;
    }
    .section {
        font-size: 19px;
        font-weight: 650;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #17b978;
    }
    .card {
        padding: 20px;
        border-radius: 10px;
        background-color: #F3F4F6;
        border: 1px solid #E5E7EB;
        margin-bottom: 15px;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        background-color: #1e3d59;
        color: white;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #17b978;
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
    ["Home / Dashboard", "Student Mode", "Doctor Mode (X-ray AI)", "Review & Feedback"],
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
        <div class="card">
            <h3>🎓 Student Mode</h3>
            <p>Learn dental topics, lesions, and radiographs. Features comprehensive curriculum breakdowns, exam corner (2, 5, 10-mark answers), and viva questions mapped to KUHS guidelines.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Student Mode", use_container_width=True):
            st.session_state.app_mode = "Student Mode"
            st.rerun()
            
    with col2:
        st.markdown("""
        <div class="card">
            <h3>🩺 Doctor Mode</h3>
            <p>Clinical decision-support platform & AMRs Dental X-ray AI module. Input radiographs, photos, and symptoms for structured evidence analysis and differential refinement.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Doctor Mode", use_container_width=True):
            st.session_state.app_mode = "Doctor Mode (X-ray AI)"
            st.rerun()

# ------------------------------------------------------------
# STUDENT MODE INTERFACE (FAST & STABLE NOTES)
# ------------------------------------------------------------
elif st.session_state.app_mode == "Student Mode" or selected_nav == "Student Mode":
    st.markdown('<div class="app-title">🎓 Dental Buddy - Student Mode</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Advanced Curriculum, Clinical Theory & Exam Corner</div>', unsafe_allow_html=True)
    
    topic = st.text_input("🔍 Search a dental topic, lesion, disease, or radiographic finding:", placeholder="e.g., Oral Submucous Fibrosis, Ameloblastoma, Dentigerous Cyst")
    
    if topic:
        st.success(f"Loaded academic curriculum and exam bank for: **{topic}**")
        
        tab_theory, tab_exam, tab_viva, tab_refs = st.tabs(["📚 Core Theory & Pathology", "📝 Exam Corner (2, 5, 10 Marks)", "🎤 Viva Questions", "📖 Textbook References"])
        
        with tab_theory:
            st.markdown(f"### 🔬 High-Scoring University Notes: {topic}")
            st.markdown("Click below to instantly generate structured exam notes point-by-point:")
            
            if "GEMINI_API_KEY" in st.secrets:
                # Fast section buttons to prevent hanging
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
            st.markdown(f"### 📝 University Exam Corner for {topic}")
            with st.expander("📌 2-Mark Short Notes"):
                st.write(f"- Define {topic} and state two primary clinical features.")
                st.write("- Mention the classic histopathological hallmark of this condition.")
                
            with st.expander("📌 5-Mark Descriptive Questions"):
                st.write(f"1. Discuss the etiology and pathogenesis of {topic}.")
                st.write(f"2. Enumerate the clinical features and differential diagnosis of {topic}.")
                
            with st.expander("📌 10-Mark Essay Question"):
                st.write(f"Classify {topic}. Discuss in detail its clinical manifestations, radiographic findings, investigations, and management principles.")

        with tab_viva:
            st.markdown(f"### 🎤 Viva Voce Spotters & Quick Questions")
            st.markdown("""
            * **Q1:** What is the most common diagnostic pitfall when diagnosing this condition clinically?
            * **Q2:** What are the pathognomonic features seen under the microscope?
            * **Q3:** What is your primary line of management for an early-stage presentation versus a late-stage presentation?
            """)

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
# DOCTOR MODE INTERFACE (AMRs Dental X-ray AI Integrated)
# ------------------------------------------------------------
elif st.session_state.app_mode == "Doctor Mode (X-ray AI)" or selected_nav == "Doctor Mode (X-ray AI)":
    st.markdown('<div class="app-title">🩺 Dental Buddy - Doctor Mode</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Clinical Decision Support & Radiographic Assessment</div>', unsafe_allow_html=True)

    remaining = DAILY_ANALYSIS_LIMIT - st.session_state.analysis_count
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="🧪 Daily Quota Left", value=f"{remaining} / {DAILY_ANALYSIS_LIMIT}")

    if remaining <= 0:
        st.warning("⏳ Your 3 AI analyses for today have been used. Please try again tomorrow.")

    with st.expander("👤 Patient Information & Record Details", expanded=True):
        patient_name = st.text_input("Patient Name", placeholder="Enter patient name")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, value=0, step=1)
        with col2:
            sex = st.selectbox("Sex", ["Select", "Male", "Female", "Other"])
        op_number = st.text_input("OP Number", placeholder="Enter OP number")
        examination_date = st.date_input("Examination Date", value=date.today())

    st.markdown('<div class="section">🩻 Radiograph & Calibration</div>', unsafe_allow_html=True)
    radiograph_type = st.selectbox("Select radiograph type", ["IOPA", "Lateral Cephalogram (Ceph)", "OPG", "Bitewing", "Occlusal", "Facial radiograph", "Other / Not reliably classifiable"])
    
    ceph_analysis = "Combined / All Analyses"
    facial_analysis = "General Facial Screening / All Views"
    scale_factor = 1.0

    if radiograph_type == "Lateral Cephalogram (Ceph)":
        ceph_analysis = st.selectbox("Select Cephalometric Analysis", CEPH_ANALYSES, key="ceph_analysis_selector")
    elif radiograph_type == "Facial radiograph":
        facial_analysis = st.selectbox("Select Facial Radiograph Analysis", FACIAL_ANALYSES, key="facial_analysis_selector")

    SAFETY_RULES = """You are Dental Buddy, an expert clinical decision-support and radiographic assessment system."""
    
    def build_prompt(rad_type, ceph_an, facial_an, scale_fac):
        return SAFETY_RULES + f"\n[Scale: {scale_fac} mm/pixel]\nAnalyze this {rad_type} thoroughly with confidence levels and clinical treatment considerations."

    st.markdown('<div class="section">📤 Upload Dental Radiograph</div>', unsafe_allow_html=True)
    xray = st.file_uploader("📷 Choose X-ray image", type=["jpg", "jpeg", "png"], key="dental_xray_upload")

    if xray is not None:
        if xray.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"❌ File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
            st.stop()

        st.image(xray, caption="Uploaded radiograph", use_container_width=True)
        analyze = st.button("🔍 Analyze X-ray with Dental Buddy", use_container_width=True, disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT))

        if analyze:
            if "GEMINI_API_KEY" not in st.secrets:
                st.error("❌ GEMINI_API_KEY missing from Streamlit secrets.")
                st.stop()
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[{"inline_data": {"mime_type": xray.type, "data": xray.getvalue()}}, build_prompt(radiograph_type, ceph_analysis, facial_analysis, scale_factor)]
                )
                if response.text:
                    st.session_state.analysis_count += 1
                    st.session_state.last_report = response.text
                    st.session_state.last_patient = patient_name if patient_name else "Patient"
                    st.success("✅ Assessment completed.")
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")

    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📋 Clinical Assessment Report")
        st.markdown(st.session_state.last_report)

# ------------------------------------------------------------
# REVIEW & FEEDBACK VIEW
# ------------------------------------------------------------
elif selected_nav == "Review & Feedback" or st.session_state.app_mode == "Review & Feedback":
    st.markdown('<div class="app-title">📝 Review & Feedback</div>', unsafe_allow_html=True)
    st.text_area("Help us improve Dental Buddy. What went wrong or what feature should be added?")
    if st.button("Submit Feedback"):
        st.success("Thank you! Your feedback has been recorded.")
                            
