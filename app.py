import streamlit as st
import logging
from utils import auth

# Initialize standard logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Page Config ---
st.set_page_config(page_title="TrustLens | Document Trust Chain", page_icon="🔐", layout="wide")

# --- Premium Global CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #0056b3;
        color: white;
        font-weight: 600;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #003d82;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    .card {
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 24px;
        border-top: 4px solid #0056b3;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #ffffff;
        color: #6c757d;
        text-align: center;
        padding: 10px 0;
        font-size: 12px;
        border-top: 1px solid #e9ecef;
        z-index: 1000;
    }
    </style>
    <div class="footer">
        TrustLens © 2026 | Visual Document Trust Chain | <a href="https://github.com/GokavalasaHemanthNaidu/TrustLens-Visual-Document-Trust-Chain" target="_blank">GitHub Repo</a>
    </div>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'user' not in st.session_state:
    st.session_state.user = None

def render_login():
    st.markdown("<h1 style='text-align: center; color: #0056b3;'>TrustLens</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #6c757d;'>Visual Document Trust Chain</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Secure, extract, and cryptographically verify physical documents.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            log_email = st.text_input("Email", key="log_email")
            log_pass = st.text_input("Password", type="password", key="log_pass")
            if st.button("Secure Login"):
                with st.spinner("Authenticating..."):
                    res, err = auth.sign_in(log_email, log_pass)
                    if err:
                        st.error(f"Login failed: {err}")
                    else:
                        st.session_state.user = res.user
                        st.success("Successfully logged in!")
                        st.rerun()
                        
        with tab2:
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Create Trust Account"):
                with st.spinner("Provisioning Identity..."):
                    res, err = auth.sign_up(reg_email, reg_pass)
                    if err:
                        st.error(f"Registration failed: {err}")
                    else:
                        st.success("Registration successful! Please login.")
        st.markdown("</div>", unsafe_allow_html=True)

def render_home():
    st.markdown(f"<h2 style='color: #0056b3;'>Welcome back to TrustLens</h2>", unsafe_allow_html=True)
    st.markdown("Your digital notary and immutable provenance engine.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class='card'>
            <h4>🔒 Secure Upload</h4>
            <p>Upload invoices and IDs. Our AI automatically extracts data, hashes it deterministically, and signs it via ECDSA SECP256R1.</p>
            <p><i>Navigate to <b>1_Upload Document</b> in the sidebar.</i></p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='card'>
            <h4>✅ Instant Verification</h4>
            <p>Verify document integrity globally using zero-knowledge public verification pages and QR-coded trust certificates.</p>
            <p><i>Navigate to <b>2_Verify Document</b> in the sidebar.</i></p>
        </div>
        """, unsafe_allow_html=True)
        
    if st.button("Sign Out", key="sign_out_home"):
        auth.sign_out()
        st.session_state.user = None
        st.rerun()

if st.session_state.user is None:
    render_login()
else:
    render_home()
