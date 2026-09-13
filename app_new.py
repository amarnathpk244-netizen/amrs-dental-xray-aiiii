import streamlit as st
from datetime import date
import json
import math
import re
import time
from google import genai
import base64

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
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

# ------------------------------------------------------------
# UI STYLES & MEDICAL THEME
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { padding-top: 1rem; }
    .app-title {
        text-align: center;
        font-size: 28px;
        font-weight: 700;
        color: #1e3d59;
        margin-bottom: 2px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .section {
        font-size: 19px;
        font-weight: 650;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #17b978;
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

st.markdown(
    '<div class="app-title">🦷 AMRs Dental X-ray AI</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">AI-Assisted Dental Radiographic Assessment</div>',
    unsafe_allow_html=True,
)

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
You are AMRs Dental X-ray AI, an expert AI-assisted radiographic assessment system built for qualified dental professionals and orthodontists.
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
- **Crown & Enamel-Dentin Integrity:** Detect interproximal/occlusal caries, defective restorations, and pulp chamber calcifications.
- **Periodontal Status:** Measure alveolar bone crest height relative to cementoenamel junction (CEJ), check lamina dura continuity, and assess periodontal ligament (PDL) space widening.
- **Periapical Pathology:** Scan root apices for periapical radiolucencies (granulomas, cysts, abscesses), root resorption, dilaceration, or hypercementosis.
- **Anatomical Landmarks:** Identify adjacent structures (e.g., mental foramen, maxillary sinus floor, nasal fossa) relative to root tips.
"""

OPG_PROTOCOL = """
[DETAILED OPG PANORAMIC PROTOCOL]
Systematically evaluate across all anatomical domains:
- **Dentition & Occlusion:** Complete tooth count, impacted teeth (e.g., third molars), root convergence/divergence, unerupted supernumeraries, and missing teeth.
- **Maxillofacial Bone Framework:** Mandibular condyles (symmetry, flattening, erosion, osteophyte formation), sigmoid notches, coronoid processes, ramus height, and inferior alveolar nerve canal path.
- **Maxillary Sinuses & Nasal Cavity:** Sinus pneumatization, mucosal thickening, fluid levels, and antral wall integrity.
- **Temporomandibular Joint (TMJ):** Condylar head position within the glenoid fossa during rest, articular eminence slope, and cortical integrity.
- **Pathology Screening:** Cysts, odontogenic tumors, radiolucent/radiopaque jaw lesions, and generalized alveolar bone loss patterns.
"""

BITEWING_PROTOCOL = """
[DETAILED BITEWING PROTOCOL]
Systematically evaluate:
- **Interproximal Contacts & Decay:** Precise inspection of proximal enamel and dentin for early carious lesions (E1, E2, D1, D2, D3) hidden between teeth.
- **Restorative Margins:** Check existing restorations for overhangs, open margins, recurrent/secondary caries beneath fillings.
- **Alveolar Bone Crests:** Measure distance from CEJ to alveolar bone crest (normal ≤ 2 mm) to grade horizontal or vertical bone loss patterns.
"""

OCCLUSAL_PROTOCOL = """
[DETAILED OCCLUSAL RADIOGRAPH PROTOCOL]
Systematically evaluate:
- **Arch Integrity & Expansion:** Maxillary or mandibular midline fractures, palatal expansion status, or cross-arch skeletal symmetry.
- **Impacted / Supernumerary Teeth:** Localization of unerupted canines, mesiodens, odontomas, or embedded third molars using the SLOB rule principles visually.
- **Cortical Bone Plates:** Assessment of buccal and lingual cortical plate expansion, cortical thinning, or localized expansion due to pathology.
"""

PA_CEPH_PROTOCOL = """
[DETAILED PA CEPHALOGRAM / PA SKULL PROTOCOL]
Systematically evaluate:
- **Transverse Skeletal Discrepancies:** Maxillary to mandibular transverse width ratios, crossbites, and skeletal asymmetry.
- **Bilateral Facial Symmetry:** Compare right and left lateral structures (orbits, zygomatic arches, nasal cavity width, ramus height, and menton deviation from midline).
- **Mandibular Deviation:** Quantify skeletal midline shift of Me (Menton) relative to nasal vertical reference line.
"""

WATERS_PROTOCOL = """
[DETAILED WATERS' VIEW / OCCIPITOMENTAL PROTOCOL]
Systematically evaluate:
- **Maxillary Sinuses:** Bilateral antral radiolucency, mucosal thickening, polypoidal changes, fluid levels, and complete opacification.
- **Midface & Orbital Structures:** Integrity of orbital floors (screening for blowout fractures), zygomaticomaxillary (ZM) complexes, zygomatic arches, and infraorbital margins.
- **Nasal Complex:** Deviated nasal septum and inferior/middle turbinate hypertrophy.
"""

SMV_PROTOCOL = """
[DETAILED SUBMENTOVERTEX (SMV) PROTOCOL]
Systematically evaluate:
- **Zygomatic Arches:** Bilateral integrity and projection of zygomatic arches to rule out depressed or 'bucket-handle' fractures.
- **Cranial Base & Sphenoid Sinuses:** Sphenoid sinus radiodensity and symmetry of middle cranial fossae.
- **Mandible Position:** Condylar head angulation and mediolateral positioning relative to the foramen magnum.
"""

TOWNES_PROTOCOL = """
[DETAILED REVERSE TOWNE'S VIEW PROTOCOL]
Systematically evaluate:
- **Condylar Necks & Heads:** Screening for high condylar neck fractures, medial/lateral displacement, and dislocation out of the glenoid fossae.
- **Ramus Height Symmetry:** Vertical height comparison of left and right mandibular rami.
- **Posterior Cranial Fossa:** Structural evaluation of occipital bone and foramen magnum margins.
"""

LATERAL_SKULL_PROTOCOL = """
[DETAILED LATERAL SKULL / PROFILE PROTOCOL]
Systematically evaluate:
- **Cranial Vault & Sella Turcica:** Bone thickness, suture closure status, and size/shape of sella turcica (hypophysis fossa).
- **Frontonasal Structures:** Frontal sinus development, nasal bone fracture lines, and soft tissue facial profile contour.
"""

GENERAL_FACIAL_PROTOCOL = """
[DETAILED GENERAL FACIAL SCREENING PROTOCOL]
Systematically evaluate:
- **Pan-Facial Skeletal Integrity:** Overview of frontal, zygomatic, maxillary, and mandibular bones.
- **Trauma Screening:** Detection of step-deformities, cortical disruptions, radiolucent fracture lines, and soft tissue swelling indicators.
"""

STEINER_PROTOCOL = """
[STEINER CEPHALOMETRIC ANALYSIS]
- Measure and evaluate: SNA angle (Maxillary position), SNB angle (Mandibular position), ANB angle (Skeletal sagittal discrepancy/jaw relationship).
- Dental parameters: Upper Incisor to NA angle/linear, Lower Incisor to NB angle/linear.
- Reference planes: SN plane, Mandibular plane (Go-Gn), Occlusal plane.
"""

DOWNS_PROTOCOL = """
[DOWNS CEPHALOMETRIC ANALYSIS]
- Measure and evaluate: Facial angle, Angle of convexity, A-B plane angle (Skeletal profile).
- Mandibular plane angle, Y-axis (growth pattern).
- Interincisal angle, Lower incisor to mandibular plane angle.
"""

MCNAMARA_PROTOCOL = """
[MCNAMARA CEPHALOMETRIC ANALYSIS]
- Measure and evaluate: Effective midfacial length (Co-A), Effective mandibular length (Co-Gn).
- Maxillary position relative to nasion perpendicular, Mandibular position relative to nasion perpendicular.
- Lower vertical facial height (ANS-Me), Maxillomandibular differential.
"""

TWEED_PROTOCOL = """
[TWEED CEPHALOMETRIC ANALYSIS]
- Measure and evaluate: FMA (Frankfort-Mandibular Plane Angle) - vertical growth indicator.
- IMPA (Incisor-Mandibular Plane Angle) - lower incisor proclination.
- FMIA (Frankfort-Mandibular Incisor Angle). Tweed Diagnostic Triangle evaluation.
"""

WITS_PROTOCOL = """
[WITS APPRAISAL]
- Measure linear distance between perpendicular drops from point A and point B onto the functional occlusal plane.
- Assess true dental/skeletal jaw mismatch independent of cranial reference planes (SNA/SNB).
"""

JARABAK_PROTOCOL = """
[JARABAK CEPHALOMETRIC ANALYSIS]
- Measure facial proportions: Posterior facial height (S-Go) to Anterior facial height (N-Me) percentage ratio (normal ~ 62-65%).
- Assess vertical growth tendencies (hypodivergent/square face vs. hyperdivergent/long-face vertical grower).
- Sum of posterior angles.
"""

SOFT_TISSUE_PROTOCOL = """
[SOFT TISSUE CEPHALOMETRIC ANALYSIS]
- Evaluate Holdaway or Steiner soft tissue profile convexity.
- Nasolabial angle, upper and lower lip thickness, esthetic plane (E-plane) relationship to lips.
"""

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
    elif radiograph_type == "Facial radiograph":
        if "PA Cephalogram" in facial_an:
            protocol += PA_CEPH_PROTOCOL
        elif "Waters'" in facial_an:
            protocol += WATERS_PROTOCOL
        elif "Submentovertex" in facial_an:
            protocol += SMV_PROTOCOL
        elif "Towne's" in facial_an:
            protocol += TOWNES_PROTOCOL
        elif "Lateral Skull" in facial_an:
            protocol += LATERAL_SKULL_PROTOCOL
        else:
            protocol += GENERAL_FACIAL_PROTOCOL
    elif rad_type == "Lateral Cephalogram (Ceph)":
        if ceph_an == "Combined / All Analyses":
            protocol += (
                "COMPREHENSIVE COMBINED CEPHALOMETRIC ANALYSIS:\n"
                + STEINER_PROTOCOL + "\n" + DOWNS_PROTOCOL + "\n"
                + MCNAMARA_PROTOCOL + "\n" + TWEED_PROTOCOL + "\n"
                + WITS_PROTOCOL + "\n" + JARABAK_PROTOCOL + "\n" + SOFT_TISSUE_PROTOCOL
            )
        elif ceph_an == "Steiner":
            protocol += STEINER_PROTOCOL
        elif ceph_an == "Downs":
            protocol += DOWNS_PROTOCOL
        elif ceph_an == "McNamara":
            protocol += MCNAMARA_PROTOCOL
        elif ceph_an == "Tweed":
            protocol += TWEED_PROTOCOL
        elif ceph_an == "Wits Appraisal":
            protocol += WITS_PROTOCOL
        elif ceph_an == "Jarabak":
            protocol += JARABAK_PROTOCOL
        elif ceph_an == "Soft Tissue":
            protocol += SOFT_TISSUE_PROTOCOL
    else:
        protocol += "General radiographic screening and pathology detection protocol."
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
        st.error(f"❌ File size exceeds {MAX_FILE_SIZE_MB}MB limit. Please upload a compressed radiographic image.")
        st.stop()

    st.image(xray, caption="Uploaded radiograph", use_container_width=True)

    analyze = st.button(
        "🔍 Analyze X-ray",
        use_container_width=True,
        disabled=(st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT),
    )

    if analyze:
        if st.session_state.analysis_count >= DAILY_ANALYSIS_LIMIT:
            st.warning("⏳ Daily AI analysis limit reached.")
        else:
            if "GEMINI_API_KEY" not in st.secrets:
                st.error("❌ GEMINI_API_KEY missing from Streamlit secrets. Please configure it to proceed.")
                st.stop()

            api_key = st.secrets["GEMINI_API_KEY"]
            mime_type = xray.type
            if mime_type not in ["image/jpeg", "image/png"]:
                st.error("❌ Unsupported image format.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    image_bytes = xray.getvalue()
                    final_prompt = build_prompt(radiograph_type, ceph_analysis, facial_analysis, scale_factor)

                    response = None
                    with st.spinner("🔬 Analyzing the uploaded radiograph with domain-specific clinical protocols..."):
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
                        st.success("✅ AI assessment completed.")
                    else:
                        st.warning("⚠️ The AI returned no readable assessment.")

                except Exception as error:
                    st.error("❌ AI analysis failed.")
                    with st.expander("Technical error details"):
                        st.write(str(error))

# ------------------------------------------------------------
# RENDER PERSISTED REPORT & EXPORT OPTIONS
# ------------------------------------------------------------
if st.session_state.last_report:
    tab_report, tab_export = st.tabs(["📋 Assessment Report", "📥 Export & Options"])

    with tab_report:
        st.markdown(st.session_state.last_report)

    with tab_export:
        st.markdown("### Export Assessment Report")
        safe_patient_name = st.session_state.last_patient
        
        report_filename = f"Dental_Report_{safe_patient_name}.txt"
        st.download_button(
            label="📥 Dow
