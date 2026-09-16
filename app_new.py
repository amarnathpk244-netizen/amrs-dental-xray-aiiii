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
            <p>Learn dental topics, lesions, and radiographs. Features step-by-step clinical reasoning, adaptive learning, and exam preparation (2, 5, 10-mark questions & viva).</p>
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
# STUDENT MODE INTERFACE
# ------------------------------------------------------------
elif st.session_state.app_mode == "Student Mode" or selected_nav == "Student Mode":
    st.markdown('<div class="app-title">🎓 Dental Buddy - Student Mode</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Learn, Understand, Reason & Practice</div>', unsafe_allow_html=True)
    
    topic = st.text_input("🔍 Search a dental topic, lesion, disease, or radiographic finding:", placeholder="e.g., Oral Submucous Fibrosis, Ameloblastoma")
    if topic:
        st.success(f"Loading structured curriculum, textbook references, and previous year questions for: **{topic}**...")
        st.markdown("""
        * **Basic Explanation & Theory** (Definition, etiology, risk factors)
        * **Clinical & Radiographic Features**
        * **Differential Diagnosis & Distinguishing Features**
        * **Exam Corner:** 2-mark, 5-mark, 10-mark answers & Viva questions
        """)
    else:
        st.info("💡 Type any dental topic above to start learning with structured academic insights and clinical reasoning guides.")

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

    # ------------------------------------------------------------
    # PATIENT INFORMATION
    # ------------------------------------------------------------
    with st.expander("👤 Patient Information & Record Details", expanded=True):
        patient_name = st.text_input("Patient Name", placeholder="Enter patient name")
        
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, value=0, step=1)
        with col2:
            sex = st.selectbox("Sex", ["Select", "Male", "Female", "Other"])

        op_number = st.text_input("OP Number", placeholder="Enter OP number")
        examination_date = st.date_input("Examination Date", value=date.today())

    # ------------------------------------------------------------
    # RADIOGRAPH TYPE & CALIBRATION
    # ------------------------------------------------------------
    st.markdown('<div class="section">🩻 Radiograph & Calibration</div>', unsafe_allow_html=True)

    radiograph_type = st.selectbox(
        "Select radiograph type",
        [
            "IOPA",
            "Lateral Cephalogram (Ceph)",
            "OPG",
            "Bitewing",
            "Occlusal",
            "Facial radiograph",
            "Other / Not reliably classifiable",
        ],
    )

    ceph_analysis = "Combined / All Analyses"
    facial_analysis = "General Facial Screening / All Views"
    scale_factor = 1.0

    if radiograph_type == "Lateral Cephalogram (Ceph)":
        ceph_analysis = st.selectbox(
            "Select Cephalometric Analysis",
            CEPH_ANALYSES,
            key="ceph_analysis_selector",
        )

        with st.expander("📏 Scale Calibration Settings", expanded=False):
            use_calibration = st.checkbox("Enable custom pixel-to-mm scale calibration")
            if use_calibration:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    known_mm = st.number_input("Known Ruler Length (mm)", min_value=1.0, value=50.0, step=1.0)
                with col_c2:
                    measured_pixels = st.number_input("Measured Length (pixels)", min_value=1.0, value=250.0, step=1.0)
                
                if measured_pixels > 0:
                    scale_factor = known_mm / measured_pixels
                    st.metric(label="Calculated Scale Factor", value=f"{scale_factor:.4f} mm/pixel")

    elif radiograph_type == "Facial radiograph":
        facial_analysis = st.selectbox(
            "Select Facial Radiograph Analysis",
            FACIAL_ANALYSES,
            key="facial_analysis_selector",
        )

    # ------------------------------------------------------------
    # HIGH-PRECISION CLINICAL PROTOCOLS & DOMAIN KNOWLEDGE
    # ------------------------------------------------------------
    SAFETY_RULES = """
    You are Dental Buddy (incorporating AMRs Dental X-ray AI), an expert AI-assisted radiographic assessment system built for qualified dental professionals and orthodontists.
    CORE PRINCIPLE: The actual uploaded radiograph is the absolute source of truth. Analyze ONLY visible structures. Never fabricate or hallucinate landmarks. If obscured or unreadable, explicitly state "Not reliably assessable."

    MANDATORY REPORT STRUCTURE:
    1. **Image Quality & Technical Evaluation** (Contrast, positioning, artifacts, distortion).
    2. **Detailed Anatomical & Pathological Findings** (Structured in clean markdown tables with Confidence Flagging: High / Medium / Low).
    3. **Growth, Biotype & Morphological Tendency Summary** (Where applicable based on view).
    4. **Clinical Treatment Considerations** (Biomechanical, surgical, growth-modification, or therapeutic options suited to findings; non-prescriptive).
    """

    IOPA_PROTOCOL = """
    [DETAILED IOPA PROTOCOL]
    Systematically evaluate:
    - Crown & Enamel-Dentin Integrity, Periodontal Status, Periapical Pathology, and Anatomical Landmarks.
    """
    OPG_PROTOCOL = """
    [DETAILED OPG PANORAMIC PROTOCOL]
    Systematically evaluate:
    - Dentition & Occlusion, Maxillofacial Bone Framework, Maxillary Sinuses, TMJ, and Pathology Screening.
    """
    BITEWING_PROTOCOL = """
    [DETAILED BITEWING PROTOCOL]
    Systematically evaluate: Interproximal Contacts & Decay, Restorative Margins, and Alveolar Bone Crests.
    """
    OCCLUSAL_PROTOCOL = """
    [DETAILED OCCLUSAL PROTOCOL]
    Systematically evaluate: Arch Integrity, Impacted/Supernumerary Teeth, and Cortical Bone Plates.
    """
    PA_CEPH_PROTOCOL = """
    [DETAILED PA CEPH PROTOCOL]
    Systematically evaluate: Transverse Skeletal Discrepancies, Bilateral Facial Symmetry, and Mandibular Deviation.
    """
    WATERS_PROTOCOL = """
    [DETAILED WATERS' VIEW PROTOCOL]
    Systematically evaluate: Maxillary Sinuses, Midface & Orbital Structures, and Nasal Complex.
    """
    SMV_PROTOCOL = """
    [DETAILED SMV PROTOCOL]
    Systematically evaluate: Zygomatic Arches, Cranial Base, and Mandible Position.
    """
    TOWNES_PROTOCOL = """
    [DETAILED REVERSE TOWNE'S PROTOCOL]
    Systematically evaluate: Condylar Necks & Heads, Ramus Height Symmetry, and Posterior Cranial Fossa.
    """
    LATERAL_SKULL_PROTOCOL = """
    [DETAILED LATERAL SKULL PROTOCOL]
    Systematically evaluate: Cranial Vault & Sella Turcica, Frontonasal Structures, and Profile Contour.
    """
    GENERAL_FACIAL_PROTOCOL = """
    [DETAILED GENERAL FACIAL PROTOCOL]
    Systematically evaluate: Pan-Facial Skeletal Integrity and Trauma Screening.
    """
    STEINER_PROTOCOL = "[STEINER ANALYSIS] SNA, SNB, ANB, Upper/Lower Incisor parameters."
    DOWNS_PROTOCOL = "[DOWNS ANALYSIS] Facial angle, Convexity, Y-axis, Mandibular plane."
    MCNAMARA_PROTOCOL = "[MCNAMARA ANALYSIS] Co-A, Co-Gn, Maxillomandibular differential."
    Tweed_PROTOCOL = "[TWEED ANALYSIS] FMA, IMPA, FMIA diagnostic triangle."
    WITS_PROTOCOL = "[WITS APPRAISAL] Functional occlusal plane linear discrepancy."
    JARABAK_PROTOCOL = "[JARABAK ANALYSIS] Posterior-to-anterior facial height ratio."
    SOFT_TISSUE_PROTOCOL = "[SOFT TISSUE ANALYSIS] Profile convexity and esthetic plane."

    def build_prompt(rad_type, ceph_an, facial_an, scale_fac):
        protocol = SAFETY_RULES + f"\n\n[IMAGE CALIBRATION SCALE: {scale_fac:.4f} mm/pixel]\n\n"
        if rad_type == "IOPA":
            protocol += IOPA_PROTOCOL
        elif rad_type == "OPG":
            protocol += OPG_PROTOCOL
        elif rad_type == "Bitewing":
            protocol += BITEWING_PROTOCOL
        elif rad_type == "Occlusal":
            protocol += OCCLUSAL_PROTOCOL
        elif rad_type == "Facial radiograph":
            protocol += GENERAL_FACIAL_PROTOCOL
        elif rad_type == "Lateral Cephalogram (Ceph)":
            protocol += STEINER_PROTOCOL + "\n" + DOWNS_PROTOCOL + "\n" + MCNAMARA_PROTOCOL
        else:
            protocol += "General radiographic screening protocol."
        return protocol

    # ------------------------------------------------------------
    # UPLOAD & FILE GUARDRAILS
    # ------------------------------------------------------------
    st.markdown('<div class="section">📤 Upload Dental Radiograph</div>', unsafe_allow_html=True)

    xray = st.file_uploader(
        "📷 Choose X-ray image",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        key="dental_xray_upload",
    )

    if xray is not None:
        if xray.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"❌ File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
            st.stop()

        st.image(xray, caption="Uploaded radiograph", use_container_width=True)

        analyze = st.button(
            "🔍 Analyze X-ray with Dental Buddy",
            use_container_width=True,
            disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT),
        )

        if analyze:
            if st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT:
                st.warning("⏳ Daily AI analysis limit reached.")
            else:
                if "GEMINI_API_KEY" not in st.secrets:
                    st.error("❌ GEMINI_API_KEY missing from Streamlit secrets.")
                    st.stop()

                api_key = st.secrets["GEMINI_API_KEY"]
                mime_type = xray.type
                try:
                    client = genai.Client(api_key=api_key)
                    image_bytes = xray.getvalue()
                    final_prompt = build_prompt(radiograph_type, ceph_analysis, facial_analysis, scale_factor)

                    response = None
                    with st.spinner("🔬 Dental Buddy is assessing the radiograph..."):
                        for attempt in range(3):
                            try:
                                response = client.models.generate_content(
                                    model=MODEL_NAME,
                                    contents=[
                                        {
                                            "inline_data": {
                                                "mime_type": mime_type,
                                                "data": image_bytes,
                                            }
                                        },
                                        final_prompt,
                                    ],
                                )
                                break
                            except Exception as error:
                                if "503" in str(error) and attempt < 2:
                                    time.sleep(5 * (2 ** attempt))
                                    continue
                                raise error

                    result_text = getattr(response, "text", None)
                    if result_text:
                        st.session_state.analysis_count += 1
                        st.session_state.last_report = result_text
                        st.session_state.last_patient = patient_name if patient_name else "Patient"
                        st.success("✅ Assessment completed.")
                    else:
                        st.warning("⚠️ The AI returned no readable assessment.")

                except Exception as error:
                    st.error("❌ AI analysis failed.")
                    with st.expander("Technical error details"):
                        st.write(str(error))

    # Render Persisted Report
    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📋 Clinical Assessment Report")
        st.markdown(st.session_state.last_report)

# ------------------------------------------------------------
# REVIEW & FEEDBACK VIEW
# ------------------------------------------------------------
elif st.selected_nav == "Review & Feedback" if 'selected_nav' in locals() else st.session_state.app_mode == "Review & Feedback":
    st.markdown('<div class="app-title">📝 Review & Feedback</div>', unsafe_allow_html=True)
    st.text_area("Help us improve Dental Buddy. What went wrong or what feature should be added?")
    if st.button("Submit Feedback"):
        st.success("Thank you! Your feedback has been recorded.")
