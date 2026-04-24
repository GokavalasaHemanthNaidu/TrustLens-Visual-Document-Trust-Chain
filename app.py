# -*- coding: utf-8 -*-
import streamlit as st
import logging
import re
from utils import auth, db_client
from config import APP_VERSION, APP_NAME, SUPPORT_EMAIL, GITHUB_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ── Page Config (set ONCE here, never in view files) ──────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} | Secure Notary",
    page_icon="🛡️",
    layout="wide",
)

# ── Brand CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Primary buttons → brand blue */
div.stButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"] {
    background-color: #0056b3 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
div.stButton > button[kind="primary"]:hover,
div.stButton > button[data-testid="baseButton-primary"]:hover {
    background-color: #003d82 !important;
}
/* Sidebar polish */
[data-testid="stSidebar"] { background-color: #0d1117; }
</style>
""", unsafe_allow_html=True)

# ── Session Init ──────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

# ── Shared Sidebar ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
        st.caption("Visual Document Trust Chain")
        st.divider()

        if st.session_state.user:
            user = st.session_state.user
            st.markdown("### 👤 Vault Profile")
            st.markdown(f"**📧** `{user.email}`")
            st.markdown(f"**🆔** `{str(user.id)[:8]}…`")
            try:
                docs = db_client.get_user_documents(user.id)
                st.metric("Secured Documents", len(docs))
            except Exception:
                pass
            st.markdown("🟢 **Active Session**")
            st.divider()
            if st.button("🔓 Sign Out", key="sidebar_signout", use_container_width=True):
                auth.sign_out()
                st.session_state.user = None
                st.rerun()
        else:
            st.info("🔐 Login to access your vault.")

        st.divider()
        # Help expander in sidebar
        with st.expander("ℹ️ Help & Support", expanded=False):
            st.markdown(f"""
**TrustLens Help Center**
- 📤 **Upload**: PNG/JPG/JPEG · max 200 MB
- 🔐 **Hashing**: SHA-256 fingerprint auto-generated
- ✅ **Verify**: Compare hash against Trust Chain
- 📊 **Analytics**: View audit log, export CSV

📧 [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})
📖 [GitHub Docs]({GITHUB_URL})
            """)
        st.caption(f"© 2026 {APP_NAME} · {APP_VERSION}")

# ── Password Strength Meter ────────────────────────────────────────────────────
def render_strength_meter(password: str):
    score = 0
    if len(password) >= 8:          score += 1
    if re.search(r"[A-Z]", password): score += 1
    if re.search(r"[0-9]", password): score += 1
    if re.search(r"[!@#$%^&*]", password): score += 1
    colors = ["#ef4444", "#ef4444", "#f59e0b", "#10b981", "#10b981"]
    labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
    pct = int((score / 4) * 100)
    st.markdown(
        f"<div style='height:5px;background:{colors[score]};width:{pct}%;"
        f"border-radius:3px;transition:width .3s;margin-bottom:4px'></div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Strength: **{labels[score]}** — add uppercase, numbers & symbols")

# ── Pages ──────────────────────────────────────────────────────────────────────
def login_page():
    render_sidebar()
    st.markdown(
        "<h1 style='text-align:center;color:#3B82F6'>🛡️ TrustLens</h1>"
        "<h3 style='text-align:center;color:#9CA3AF'>Visual Document Trust Chain</h3>"
        "<p style='text-align:center;margin-bottom:32px'>Secure, extract, and cryptographically verify physical documents.</p>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 2, 1])
    with col:
        tab_login, tab_signup, tab_forgot = st.tabs(["🔐 Login", "✏️ Sign Up", "🔑 Forgot Password"])

        with tab_login:
            email = st.text_input("Email", key="l_email")
            pwd   = st.text_input("Password", type="password", key="l_pwd")
            if st.button("Secure Login", use_container_width=True, type="primary", key="btn_login"):
                with st.spinner("Authenticating…"):
                    res, err = auth.sign_in(email, pwd)
                    if err:
                        st.error(f"Login failed: {err}")
                    else:
                        st.session_state.user = res.user
                        st.success("Logged in!")
                        st.rerun()

        with tab_signup:
            s_email   = st.text_input("Email", key="s_email")
            s_pwd     = st.text_input("Password", type="password", key="s_pwd", help="Min 8 chars")
            if s_pwd:
                render_strength_meter(s_pwd)
            s_pwd2    = st.text_input("Confirm Password", type="password", key="s_pwd2")
            if st.button("Create Vault Account", use_container_width=True, type="primary", key="btn_signup"):
                if len(s_pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                elif s_pwd != s_pwd2:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Provisioning identity…"):
                        res, err = auth.sign_up(s_email, s_pwd)
                        if err:
                            st.error(f"Registration failed: {err}")
                        else:
                            st.success("Account created! Please login.")

        with tab_forgot:
            r_email = st.text_input("Your account email", key="r_email")
            if st.button("Send Reset Link", use_container_width=True, key="btn_reset"):
                with st.spinner("Sending link…"):
                    ok, err = auth.reset_password(r_email)
                    if ok:
                        st.success("If that email exists, a reset link has been sent.")
                    else:
                        st.error(f"Could not send reset link: {err}")


def home_dashboard():
    render_sidebar()
    user = st.session_state.user

    st.markdown("<h2 style='color:#3B82F6'>🏠 Trust Dashboard</h2>", unsafe_allow_html=True)
    st.caption("Your digital notary and immutable provenance engine.")

    # ── User Vault Profile card ─────────────────────────────────────────────
    with st.container():
        st.markdown("#### 👤 User Vault Profile")
        try:
            docs = db_client.get_user_documents(user.id)
            doc_count = len(docs)
        except Exception:
            doc_count = 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Email", user.email)
        c2.metric("Account ID", str(user.id)[:8] + "…")
        c3.metric("Secured Documents", doc_count)

    st.divider()

    # ── Action cards ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔒 Secure Upload")
        st.markdown("Upload invoices or IDs. AI extracts data, hashes with SHA-256, and signs via ECDSA SECP256R1.")
        if st.button("🚀 Upload Document Now", use_container_width=True, type="primary", key="go_upload"):
            st.switch_page("views/1_Upload_Document.py")
    with col2:
        st.markdown("#### ✅ Instant Verification")
        st.markdown("Anyone can verify a document's hash via our zero-knowledge public verification portal.")
        if st.button("🔍 Verify a Document", use_container_width=True, key="go_verify"):
            st.switch_page("views/2_Verify_Document.py")

    # ── Help expander ────────────────────────────────────────────────────────
    st.divider()
    with st.expander("ℹ️ How Does TrustLens Work?", expanded=False):
        st.markdown(f"""
| Step | What Happens |
|------|-------------|
| 📤 Upload | Your document is scanned via Tesseract OCR |
| 🔐 Hash | Extracted data is hashed with SHA-256 |
| ✍️ Sign | Hash is signed with your unique ECDSA private key |
| 🗄️ Anchor | Record is saved to Supabase ledger |
| ✅ Verify | Anyone can re-hash and compare — zero trust required |

📧 [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL}) · 📖 [GitHub Docs]({GITHUB_URL})
        """)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
        f"© 2026 {APP_NAME} | <a href='{GITHUB_URL}' target='_blank'>GitHub Repo</a> | {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )


# ── Navigation ─────────────────────────────────────────────────────────────────
login_p    = st.Page(login_page,    title="Log In",            icon="🔐")
verify_p   = st.Page("views/2_Verify_Document.py",  title="Public Verification", icon="✅")
home_p     = st.Page(home_dashboard, title="Home Dashboard",   icon="🏠")
upload_p   = st.Page("views/1_Upload_Document.py",  title="Secure Upload",       icon="📤")
analytics_p = st.Page("views/3_Trust_Analytics.py", title="Analytics Dashboard", icon="📊")

if st.session_state.user is None:
    pg = st.navigation([login_p, verify_p])
else:
    pg = st.navigation([home_p, upload_p, verify_p, analytics_p])

pg.run()
