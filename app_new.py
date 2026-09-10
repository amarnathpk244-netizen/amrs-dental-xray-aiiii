import streamlit as st
from datetime import date
from google import genai
from google.genai import types


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AMRs Dental X-ray AI",
    page_icon="🦷",
    layout="centered"
)


# ============================================================
# CONSTANTS
# ============================================================

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# SESSION / DAILY USAGE
# ============================================================

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "usage_date" not in st.session_state:
    st.session_state.usage_date = date.today()

if st.session_state.usage_date != date.today():
    st.session_state.analysis_count = 0
    st.session_state.usage_date = date.today()


# ============================================================
# MOBILE UI
# ============================================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 1rem;
    }

    .app-title {
        text-align: center;
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .subtitle {
        text-align: center;
        color: #666;
        font-size: 15px;
        margin-bottom: 25px;
    }

    .section {
        font-size: 21px;
        font-weight: 650;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .info-box {
        padding: 15px;
        border-radius: 12px;
        background: #f5f7fa;
        margin-top: 10px;
        margin-bottom: 15px;
    }

    .disclaimer {
        font-size: 12px;
        color: #666;
        padding: 12px;
        border-radius: 10px;
        background: #f7f7f7;
        margin-top: 20px;
    }

    .result-box {
        padding: 16px;
        border-radius: 12px;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        margin-top: 15px;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="app-title">🦷 AMRs Dental X-ray AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-Assisted Dental Radiographic Assessment'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# USAGE STATUS
# ============================================================

remaining = (
    DAILY_ANALYSIS_LIMIT
    - st.session_state.analysis_count
)

if remaining > 0:

    st.info(
        f"🧪 AI analyses remaining today: "
        f"{remaining} / {DAILY_ANALYSIS_LIMIT}"
    )

else:

    st.warning(
        "⏳ Your 3 AI analyses for today have been used. "
        "Please try again tomorrow."
    )


# ============================================================
# PATIENT INFORMATION
# ============================================================

st.markdown(
    '<div class="section">👤 Patient Information</div>',
    unsafe_allow_html=True
)

patient_name = st.text_input(
    "Patient Name",
    placeholder="Enter patient name"
)

col1, col2 = st.columns(2)

with col1:

    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        value=0,
        step=1
    )

with col2:

    sex = st.selectbox(
        "Sex",
        [
            "Select",
            "Male",
            "Female",
            "Other"
        ]
