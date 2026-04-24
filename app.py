# -*- coding: utf-8 -*-
import streamlit as st
import logging
import re
from utils import auth, db_client
from config import APP_VERSION, APP_NAME, SUPPORT_EMAIL, GITHUB_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ── Page Config (set ONCE — never in view files) ───────────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} | Secure Notary",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Brand primary buttons */
div.stButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #0056b3, #0077e6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.2s ease !important;
}
div.stButton > button[kind="primary"]:hover,
div.stButton > button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #004494, #0056b3) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0,86,179,0.4) !important;
}
/* Top-right profile pill */
.profile-pill {
    position: fixed;
    top: 14px;
    right: 16px;
    z-index: 9999;
    background: linear-gradient(135deg, #0056b3, #0077e6);
    color: white;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 2px 10px rgba(0,86,179,0.4);
    cursor: default;
}
/* Sidebar polish */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
}
/* Metric label */
[data-testid="stMetricLabel"] { font-size: 12px !important; }
/* Tab styling */
[data-testid="stTabs"] button { font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ── Session Init ───────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

# ── Top-Right Profile Pill (shows when logged in) ──────────────────────────────
if st.session_state.user:
    email = st.session_state.user.email
    initials = "".join([p[0].upper() for p in email.split("@")[0].split(".")[:2]])
    st.markdown(
        f"<div class='profile-pill'>👤 {initials} &nbsp;|&nbsp; {email}</div>",
        unsafe_allow_html=True,
    )

# ── Shared Sidebar ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:12px 0'>"
            f"<span style='font-size:36px'>🛡️</span><br>"
            f"<span style='color:#3B82F6;font-size:22px;font-weight:700'>{APP_NAME}</span><br>"
            f"<span style='color:#9CA3AF;font-size:12px'>Visual Document Trust Chain</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        if st.session_state.user:
            user = st.session_state.user
            email = user.email
            initials = "".join([p[0].upper() for p in email.split("@")[0].split(".")[:2]])

            # Profile card
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#1e3a5f,#1a2744);border-radius:12px;"
                f"padding:14px;margin-bottom:12px;border:1px solid #2d4a6e'>"
                f"<div style='display:flex;align-items:center;gap:10px'>"
                f"<div style='width:38px;height:38px;border-radius:50%;background:#3B82F6;"
                f"display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px'>"
                f"{initials}</div>"
                f"<div><div style='font-weight:600;font-size:13px'>{email}</div>"
                f"<div style='color:#10B981;font-size:11px'>🟢 Active Session</div></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            # Live doc count
            try:
                docs = db_client.get_user_documents(user.id)
                doc_count = len(docs)
            except Exception:
                doc_count = 0

            m1, m2 = st.columns(2)
            m1.metric("Vault Docs", doc_count)
            m2.metric("Account ID", str(user.id)[:6] + "…")

            st.divider()

            # Navigation shortcuts
            st.markdown("**Quick Navigate**")
            if st.button("🏠 Dashboard", use_container_width=True, key="nav_home"):
                st.switch_page("app.py")
            if st.button("📤 Upload", use_container_width=True, key="nav_upload"):
                st.switch_page("views/1_Upload_Document.py")
            if st.button("✅ Verify", use_container_width=True, key="nav_verify"):
                st.switch_page("views/2_Verify_Document.py")
            if st.button("📊 Analytics", use_container_width=True, key="nav_analytics"):
                st.switch_page("views/3_Trust_Analytics.py")

            st.divider()
            if st.button("🔓 Sign Out", use_container_width=True, key="sidebar_signout", type="primary"):
                auth.sign_out()
                st.session_state.user = None
                st.rerun()
        else:
            st.info("🔐 Login to access your secure vault.")

        st.divider()
        with st.expander("ℹ️ Help & Support", expanded=False):
            st.markdown(f"""
**How TrustLens Works**
- 📤 **Upload**: PNG/JPG/JPEG · max 200 MB
- 🔐 **Hash**: SHA-256 fingerprint from OCR data
- ✅ **Verify**: Public zero-knowledge audit
- 📊 **Analytics**: Full audit trail + CSV export

📧 [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})
📖 [GitHub Docs]({GITHUB_URL})
            """)
        st.markdown(
            f"<div style='text-align:center;color:#4B5563;font-size:11px;margin-top:8px'>© 2026 {APP_NAME} · {APP_VERSION}</div>",
            unsafe_allow_html=True,
        )

# ── Password Strength ──────────────────────────────────────────────────────────
def render_strength_meter(password: str):
    score = sum([
        len(password) >= 8,
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"[0-9]", password)),
        bool(re.search(r"[!@#$%^&*]", password)),
    ])
    colors = ["#ef4444", "#ef4444", "#f59e0b", "#10b981", "#10b981"]
    labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
    pct = int((score / 4) * 100)
    st.markdown(
        f"<div style='height:5px;background:{colors[score]};width:{pct}%;"
        "border-radius:3px;transition:width .3s;margin-bottom:4px'></div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Strength: **{labels[score]}** — add uppercase, numbers & symbols for a stronger password")

# ── Login Page ─────────────────────────────────────────────────────────────────
def login_page():
    render_sidebar()
    st.markdown(
        "<div style='text-align:center;padding:20px 0'>"
        "<span style='font-size:56px'>🛡️</span><br>"
        "<h1 style='color:#3B82F6;margin:8px 0 4px'>TrustLens</h1>"
        "<p style='color:#9CA3AF;margin:0'>Visual Document Trust Chain — Forensic-grade document notarization</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 2, 1])
    with col:
        tab_login, tab_signup, tab_forgot = st.tabs(["🔐 Login", "✏️ Create Account", "🔑 Reset Password"])

        # ── Login ──────────────────────────────────────────────────────────
        with tab_login:
            email = st.text_input("Email address", key="l_email", placeholder="you@example.com")
            pwd   = st.text_input("Password", type="password", key="l_pwd")
            if st.button("🔐 Secure Login", use_container_width=True, type="primary", key="btn_login"):
                if not email or not pwd:
                    st.error("Please enter your email and password.")
                else:
                    with st.spinner("Authenticating…"):
                        res, err = auth.sign_in(email, pwd)
                        if err:
                            st.error(f"Login failed: {err}")
                        else:
                            st.session_state.user = res.user
                            st.success("✅ Logged in successfully!")
                            st.rerun()

        # ── Sign Up ────────────────────────────────────────────────────────
        with tab_signup:
            st.markdown(
                "<p style='color:#9CA3AF;font-size:13px'>After signing up, you'll receive a "
                "<strong>confirmation email</strong>. Click the link inside to verify your account.</p>",
                unsafe_allow_html=True,
            )
            s_email = st.text_input("Email address", key="s_email", placeholder="you@example.com")
            s_pwd   = st.text_input("Password", type="password", key="s_pwd", help="Min 8 characters")
            if s_pwd:
                render_strength_meter(s_pwd)
            s_pwd2  = st.text_input("Confirm Password", type="password", key="s_pwd2")

            if st.button("🚀 Create Vault Account", use_container_width=True, type="primary", key="btn_signup"):
                if not s_email:
                    st.error("Email is required.")
                elif len(s_pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                elif s_pwd != s_pwd2:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating your secure identity…"):
                        res, err = auth.sign_up(s_email, s_pwd)
                        if err:
                            st.error(f"Registration failed: {err}")
                        else:
                            st.success("🎉 Account created! Check your inbox for a confirmation email.")
                            st.info(
                                "📧 **Next step:** Open the email from Supabase/TrustLens and click "
                                "**Confirm your email** before logging in."
                            )

        # ── Forgot Password ────────────────────────────────────────────────
        with tab_forgot:
            r_email = st.text_input("Enter your account email", key="r_email", placeholder="you@example.com")
            if st.button("📧 Send Reset Link", use_container_width=True, key="btn_reset"):
                if not r_email:
                    st.error("Please enter your email address.")
                else:
                    with st.spinner("Sending reset link…"):
                        ok, err = auth.reset_password(r_email)
                        if ok:
                            st.success("✅ Reset link sent! Check your inbox.")
                            st.info("If you don't see it within 5 minutes, check your spam folder.")
                        else:
                            st.error(f"Could not send reset link: {err}")

# ── Home Dashboard ─────────────────────────────────────────────────────────────
def home_dashboard():
    render_sidebar()
    user = st.session_state.user
    email = user.email
    initials = "".join([p[0].upper() for p in email.split("@")[0].split(".")[:2]])

    st.markdown(
        f"<h1 style='color:#3B82F6'>🏠 Trust Dashboard</h1>"
        f"<p style='color:#9CA3AF'>Welcome back, <strong>{email}</strong></p>",
        unsafe_allow_html=True,
    )

    # ── User Vault Profile card ─────────────────────────────────────────────
    try:
        docs = db_client.get_user_documents(user.id)
        doc_count = len(docs)
    except Exception:
        doc_count = 0

    # Styled profile card
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1e3a5f,#1a2744);border-radius:16px;"
        f"padding:20px 24px;margin-bottom:24px;border:1px solid #2d4a6e;"
        f"display:flex;align-items:center;gap:16px'>"
        f"<div style='width:56px;height:56px;border-radius:50%;background:#3B82F6;"
        f"display:flex;align-items:center;justify-content:center;font-weight:700;font-size:22px;flex-shrink:0'>"
        f"{initials}</div>"
        f"<div>"
        f"<div style='font-size:18px;font-weight:700'>{email}</div>"
        f"<div style='color:#9CA3AF;font-size:13px'>Account ID: <code>{str(user.id)[:12]}…</code></div>"
        f"<div style='color:#10B981;font-size:13px;margin-top:4px'>🟢 Verified & Active</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("📄 Secured Documents", doc_count)
    c2.metric("🔐 Cryptographic Proofs", doc_count * 2)
    c3.metric("⛓️ Ledger Uptime", "100%")

    st.divider()

    # ── Action cards ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "<div style='background:#111827;border-radius:12px;padding:20px;border:1px solid #1F2937'>"
            "<h3>🔒 Secure Upload</h3>"
            "<p style='color:#9CA3AF'>Upload invoices or IDs. AI extracts data, hashes with SHA-256, "
            "and signs via ECDSA SECP256R1.</p></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("🚀 Upload Document Now", use_container_width=True, type="primary", key="go_upload"):
            st.switch_page("views/1_Upload_Document.py")

    with col2:
        st.markdown(
            "<div style='background:#111827;border-radius:12px;padding:20px;border:1px solid #1F2937'>"
            "<h3>✅ Instant Verification</h3>"
            "<p style='color:#9CA3AF'>Anyone can verify a document's hash via our zero-knowledge "
            "public verification portal — no login needed.</p></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("🔍 Verify a Document", use_container_width=True, key="go_verify"):
            st.switch_page("views/2_Verify_Document.py")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(
            "<div style='background:#111827;border-radius:12px;padding:20px;border:1px solid #1F2937'>"
            "<h3>📊 Analytics & Audit Log</h3>"
            "<p style='color:#9CA3AF'>View your full audit trail. Search, filter, and export as CSV.</p></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("📊 View Analytics", use_container_width=True, key="go_analytics"):
            st.switch_page("views/3_Trust_Analytics.py")

    with col4:
        st.markdown(
            "<div style='background:#111827;border-radius:12px;padding:20px;border:1px solid #1F2937'>"
            "<h3>ℹ️ How TrustLens Works</h3>"
            "<p style='color:#9CA3AF'>5-step cryptographic pipeline from image to immutable ledger entry.</p></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        with st.expander("View Pipeline", expanded=False):
            st.markdown("""
| Step | What Happens |
|------|-------------|
| 📤 Upload | Tesseract OCR scans your document |
| 🔐 Hash | SHA-256 generated from extracted fields |
| ✍️ Sign | Hash signed with ECDSA SECP256R1 key |
| 🗄️ Anchor | Record saved to Supabase immutable ledger |
| ✅ Verify | Anyone re-hashes and compares — zero trust |
            """)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='text-align:center;color:#4B5563;font-size:12px;margin-top:40px;"
        f"border-top:1px solid #1F2937;padding-top:16px'>"
        f"© 2026 {APP_NAME} | <a href='{GITHUB_URL}' target='_blank' style='color:#3B82F6'>GitHub Repo</a>"
        f" | {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )

# ── Navigation Router ──────────────────────────────────────────────────────────
login_p     = st.Page(login_page,     title="Log In",             icon="🔐")
verify_p    = st.Page("views/2_Verify_Document.py", title="Public Verification", icon="✅")
home_p      = st.Page(home_dashboard, title="Home Dashboard",    icon="🏠")
upload_p    = st.Page("views/1_Upload_Document.py", title="Secure Upload",       icon="📤")
analytics_p = st.Page("views/3_Trust_Analytics.py", title="Analytics Dashboard", icon="📊")

if st.session_state.user is None:
    pg = st.navigation([login_p, verify_p])
else:
    pg = st.navigation([home_p, upload_p, verify_p, analytics_p])

pg.run()
