"""
SocialPulse AI - Main Application Entry Point
Social Media Performance Analyzer Dashboard

This is the main Streamlit application that sets up the page configuration,
loads styles, and manages page navigation.
"""
import streamlit as st
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.session_manager import init_session_state, is_data_loaded
from utils.constants import PAGES, PRIMARY, BACKGROUND

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="SocialPulse AI – Social Media Performance Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Initialize Session State ───────────────────────────────────────────────
init_session_state()

# ─── Load Custom CSS ────────────────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(__file__), "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Additional inline styles for Streamlit overrides
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    .stApp {
        background-color: #F9F9FF;
        font-family: 'Inter', 'Plus Jakarta Sans', sans-serif;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E8E8F0;
        min-width: 280px;
        max-width: 280px;
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }
    
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        color: #141B2B;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none !important;}
    div[data-testid="stSidebarNav"] {display: none !important;}
    
    div[data-testid="stDecoration"] {display: none;}
    
    .stDeployButton {display: none;}
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(70, 72, 212, 0.2);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #F0F0FF;
        border-radius: 8px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.85rem;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4648D4 !important;
        color: white !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 0.95rem;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ────────────────────────────────────────────────────────────────
from components.sidebar import render_sidebar
render_sidebar()

# ─── Header ─────────────────────────────────────────────────────────────────
from components.header import render_header
render_header()

# ─── Page Router ─────────────────────────────────────────────────────────────
current_page = st.session_state.get("current_page", "Dashboard Overview")

if current_page == "Dashboard Overview":
    from pages import dashboard_overview
    dashboard_overview.render()

elif current_page == "CSV Upload & Prep":
    from pages import csv_upload
    csv_upload.render()

elif current_page == "Deep Analytics":
    from pages import deep_analytics
    deep_analytics.render()

elif current_page == "Top Posts Explorer":
    from pages import top_posts_explorer
    top_posts_explorer.render()

elif current_page == "AI Insights":
    from pages import ai_insights_page
    ai_insights_page.render()

elif current_page == "Export & PDF Reports":
    from pages import export_pdf
    export_pdf.render()

else:
    from pages import dashboard_overview
    dashboard_overview.render()
