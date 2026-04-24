import streamlit as st
import logging
from utils import auth

# Initialize standard logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Page Config ---
st.set_page_config(page_title="TrustLens | Secure Notary", page_icon="🛡️", layout="wide")

# --- Session State Initialization ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown("<h1 style='text-align: center; color: #0056b3;'>🛡️ TrustLens</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #6c757d;'>Visual Document Trust Chain</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Secure, extract, and cryptographically verify physical documents.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            log_email = st.text_input("Email", key="log_email")
            log_pass = st.text_input("Password", type="password", key="log_pass")
            if st.button("Secure Login", use_container_width=True):
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
            reg_pass = st.text_input("Password", type="password", key="reg_pass", help="Minimum 8 characters")
            reg_pass_confirm = st.text_input("Confirm Password", type="password", key="reg_pass_confirm")
            
            if st.button("Create Trust Account", use_container_width=True):
                if len(reg_pass) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Provisioning Identity..."):
                        res, err = auth.sign_up(reg_email, reg_pass)
                        if err:
                            st.error(f"Registration failed: {err}")
                        else:
                            st.success("Registration successful! Please login.")

def home_dashboard():
    st.markdown("<h2 style='color: #0056b3;'>Welcome to the Trust Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("Your digital notary and immutable provenance engine.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔒 Secure Upload")
        st.markdown("Upload invoices and IDs. Our AI automatically extracts data, hashes it deterministically, and signs it via ECDSA SECP256R1.")
        if st.button("🚀 Upload Document Now", use_container_width=True, type="primary"):
            st.switch_page("views/1_Upload_Document.py")
            
    with col2:
        st.markdown("#### ✅ Instant Verification")
        st.markdown("Verify document integrity globally using zero-knowledge public verification pages and QR-coded trust certificates.")
        if st.button("🔍 Verify a Document", use_container_width=True):
            st.switch_page("views/2_Verify_Document.py")
        
    st.divider()
    if st.button("Sign Out", key="sign_out_home"):
        auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- Navigation Setup ---
login_p = st.Page(login_page, title="Log In", icon="🔐")
verify_p = st.Page("views/2_Verify_Document.py", title="Public Verification", icon="✅")
home_p = st.Page(home_dashboard, title="Home Dashboard", icon="🏠")
upload_p = st.Page("views/1_Upload_Document.py", title="Secure Upload", icon="📤")
analytics_p = st.Page("views/3_Trust_Analytics.py", title="Analytics Dashboard", icon="📊")

if st.session_state.user is None:
    # Public Pages
    pg = st.navigation([login_p, verify_p])
else:
    # Authenticated Pages
    pg = st.navigation([home_p, upload_p, verify_p, analytics_p])

pg.run()

# --- Footer ---
st.markdown("""
    <div style='text-align: center; color: #6c757d; font-size: 12px; margin-top: 50px; padding-top: 20px; border-top: 1px solid #e9ecef;'>
        © 2026 TrustLens | <a href='https://github.com/GokavalasaHemanthNaidu/TrustLens-Visual-Document-Trust-Chain' target='_blank'>GitHub Repo</a> | v1.4.1
    </div>
""", unsafe_allow_html=True)
