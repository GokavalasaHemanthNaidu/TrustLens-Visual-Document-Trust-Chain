# -*- coding: utf-8 -*-
import streamlit as st
import logging
import re
import hashlib
from utils import auth, db_client
from config import APP_VERSION, APP_NAME, SUPPORT_EMAIL, GITHUB_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} | Secure Notary",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dynamic Profile Color Logic ────────────────────────────────────────────────
def get_user_color(email):
    """Generates a stable, vibrant HSL color based on the email string."""
    hash_obj = hashlib.md5(email.lower().encode())
    hue = int(hash_obj.hexdigest(), 16) % 360
    return f"hsl({hue}, 70%, 45%)"

# ── Global CSS ─────────────────────────────────────────────────────────────────
user_color = "#0056b3" # Default
if st.session_state.get("user"):
    user_color = get_user_color(st.session_state.user.email)

st.markdown(f"""
<style>
/* Brand primary buttons */
div.stButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"] {{
    background: linear-gradient(135deg, {user_color}, #0077e6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}}
/* Top-right profile pill */
.profile-pill {{
    position: fixed;
    top: 14px;
    right: 16px;
    z-index: 9999;
    background: {user_color};
    color: white;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.2);
    text-decoration: none !important;
}}
.profile-pill:hover {{
    filter: brightness(1.2);
    transform: translateY(-1px);
}}
.avatar-circle {{
    width: 24px;
    height: 24px;
    background: rgba(255,255,255,0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    text-transform: uppercase;
}}
/* Sidebar polish */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
}}
</style>
""", unsafe_allow_html=True)

# ── Session Init ───────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

# ── Top-Right Profile Pill ─────────────────────────────────────────────────────
if st.session_state.user:
    email = st.session_state.user.email
    initial = email[0].upper()
    st.markdown(
        f'<a href="/?page=analytics" class="profile-pill" target="_self">'
        f'<div class="avatar-circle">{initial}</div>'
        f'<div>{email}</div>'
        f'</a>',
        unsafe_allow_html=True,
    )

# ── Shared Sidebar ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:12px 0'>"
            f"<span style='font-size:36px'>🛡️</span><br>"
            f"<span style='color:#3B82F6;font-size:22px;font-weight:700'>{APP_NAME}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        # Always re-read user from session_state fresh
        user = st.session_state.get("user")

        if user:
            u_color = get_user_color(user.email)
            initial = user.email[0].upper()
            st.markdown(
                f"<div style='background:{u_color};border-radius:12px;padding:14px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.1)'>"
                f"<div style='display:flex;align-items:center;gap:12px'>"
                f"<div style='width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,0.25);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:18px;color:white'>{initial}</div>"
                f"<div><div style='font-weight:700;font-size:14px;color:white'>{user.email}</div>"
                f"<div style='font-size:11px;opacity:0.85;color:white'>🟢 Secure Session Active</div></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown("**Navigate:**")
            if st.button("🏠 Home", use_container_width=True):
                st.switch_page("app.py")
            if st.button("📤 Secure Upload", use_container_width=True):
                st.switch_page("views/1_Upload_Document.py")
            if st.button("🔍 Verify Document", use_container_width=True):
                st.switch_page("views/2_Verify_Document.py")
            if st.button("📊 My Vault", use_container_width=True):
                st.switch_page("views/3_Trust_Analytics.py")
            st.divider()
            if st.button("🔓 Logout", use_container_width=True, type="primary"):
                auth.sign_out()
                st.session_state.user = None
                st.rerun()
        else:
            st.info("🔐 Login to access your secure vault.")

        st.divider()
        st.caption(f"© 2026 {APP_NAME} · {APP_VERSION}")

# ── Pages ──────────────────────────────────────────────────────────────────────
def login_page():
    render_sidebar()
    st.markdown("<h1 style='text-align:center;color:#3B82F6'>🛡️ TrustLens</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        tab1, tab2, tab3 = st.tabs(["🔐 Login", "✏️ Sign Up", "🔑 Forgot Password"])
        with tab1:
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("Login", type="primary", use_container_width=True):
                res, err = auth.sign_in(e, p)
                if not err:
                    st.session_state.user = res.user
                    st.rerun()
                else: st.error(err)
        with tab2:
            st.info("Check your inbox for a confirmation email after signing up.")
            se = st.text_input("Email", key="se")
            sp = st.text_input("Password", type="password", key="sp")
            if st.button("Create Account", type="primary", use_container_width=True):
                res, err = auth.sign_up(se, sp)
                if not err: st.success("Verify your email!")
                else: st.error(err)
        with tab3:
            st.info("Enter your email to receive a secure password reset link.")
            fe = st.text_input("Account Email", key="fe")
            if st.button("Send Reset Link", type="primary", use_container_width=True):
                if not fe:
                    st.warning("Please enter your email.")
                else:
                    success, err = auth.reset_password(fe)
                    if success:
                        st.success("✅ Reset link sent! Please check your inbox.")
                    else:
                        st.error(err)

def home_dashboard():
    render_sidebar()
    st.markdown(f"## 🏠 Welcome to the Trust Chain")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Secure New Document", use_container_width=True, type="primary"):
            st.switch_page("views/1_Upload_Document.py")
    with col2:
        if st.button("🔍 Verify Provenance", use_container_width=True):
            st.switch_page("views/2_Verify_Document.py")

# ── Navigation ─────────────────────────────────────────────────────────────────
login_p     = st.Page(login_page,     title="Log In",             icon="🔐")
verify_p    = st.Page("views/2_Verify_Document.py", title="Public Verification", icon="✅")
home_p      = st.Page(home_dashboard, title="Home Dashboard",    icon="🏠")
upload_p    = st.Page("views/1_Upload_Document.py", title="Secure Upload",       icon="📤")
analytics_p = st.Page("views/3_Trust_Analytics.py", title="My Vault",           icon="📊")

if st.session_state.user is None:
    pg = st.navigation([login_p, verify_p])
else:
    pg = st.navigation([home_p, upload_p, verify_p, analytics_p])

pg.run()
