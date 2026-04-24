# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from utils import db_client
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Auth guard ─────────────────────────────────────────────────────────────────
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔐 Please login first — use the **Log In** page in the sidebar.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    user = st.session_state.user
    st.markdown(f"**👤** `{user.email}`")
    st.markdown("🟢 **Active Session**")
    st.divider()
    with st.expander("ℹ️ Analytics Help", expanded=False):
        st.markdown(f"""
- **Total Secured Docs**: count of all your anchored documents
- **Cryptographic Proofs**: each doc gets a SHA-256 hash + ECDSA signature
- **Audit Log**: searchable table of all your documents
- **Export CSV**: download the full audit log

📧 [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})
        """)
    st.caption(f"{APP_VERSION}")

# ── Page Content ────────────────────────────────────────────────────────────────
st.title("📊 Trust Analytics Dashboard")
st.markdown("Monitor your secured documents and immutable audit trail.")

with st.spinner("Loading ledger from Supabase…"):
    docs = db_client.get_user_documents(user.id)

if not docs:
    st.info("📭 No documents found in your Trust Ledger yet. Upload your first document to get started!")
    st.stop()

# ── Key Metrics ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Total Secured Documents", len(docs))
col2.metric("Cryptographic Proofs Generated", len(docs) * 2)  # hash + signature per doc
col3.metric("Immutable Ledger Uptime", "100%")

st.divider()

# ── Audit Log ──────────────────────────────────────────────────────────────────
st.markdown("### 📜 Document Audit Log")

table_data = []
for doc in docs:
    extracted = doc.get("extracted_fields", {}) or {}
    table_data.append({
        "Document ID":       doc["id"],
        "Secured On":        doc["created_at"][:10],
        "Extracted Name":    extracted.get("name",        "—"),
        "Extracted Amount":  extracted.get("amount",      "—"),
        "Invoice / Doc ID":  extracted.get("document_id", "—"),
        "SHA-256 Hash":      doc["content_hash"][:20] + "…",
    })

df = pd.DataFrame(table_data)

search = st.text_input("🔍 Search Audit Log", placeholder="Filter by name, ID, date…", key="search_log")
if search:
    mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
    df = df[mask]
    if df.empty:
        st.warning("No results match your search.")

st.dataframe(df, use_container_width=True, hide_index=True)

# ── Export ──────────────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Export Audit Log (CSV)",
    data=csv,
    file_name=f"TrustLens_AuditLog_{user.id[:8]}.csv",
    mime="text/csv",
    key="dl_csv",
)

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | <a href='{GITHUB_URL}' target='_blank'>GitHub Repo</a> | {APP_VERSION}</div>",
    unsafe_allow_html=True,
)
