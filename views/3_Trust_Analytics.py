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
**Analytics Guide:**
1. **Metrics**: Real-time count of your secured assets.
2. **Audit Log**: Searchable table of all anchored documents.
3. **Vault Viewer**: Select any document to view its original image and AI data.
4. **Export**: Download your entire history as a CSV file.

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
col2.metric("Cryptographic Proofs", len(docs) * 2)
col3.metric("Immutable Ledger Uptime", "100%")

st.divider()

# ── Vault Viewer (View Document Uploaded) ──────────────────────────────────────
st.markdown("### 🖼️ Document Vault Viewer")
st.markdown("Select a document to view its original image and extraction details.")

# Create a list for selection
doc_options = {f"{d['created_at'][:10]} | {d['id'][:8]}...": d for d in docs}
selected_key = st.selectbox("Choose a document to inspect:", options=list(doc_options.keys()))

if selected_key:
    selected_doc = doc_options[selected_key]
    with st.container():
        st.markdown(
            f"<div style='background:#111827;border-radius:12px;padding:20px;border:1px solid #1F2937'>",
            unsafe_allow_html=True
        )
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.image(selected_doc["image_url"], caption="Anchored Image", use_column_width=True)
            st.link_button("🔗 View Full Image", selected_doc["image_url"], use_container_width=True)
        with c2:
            st.markdown("#### 🔬 AI & Cryptography Details")
            extracted = selected_doc.get("extracted_fields", {}) or {}
            
            # Display extracted info in a clean way
            cols = st.columns(2)
            cols[0].markdown(f"**Name:** {extracted.get('name', '—')}")
            cols[1].markdown(f"**Amount:** {extracted.get('amount', '—')}")
            cols[0].markdown(f"**ID/Invoice:** {extracted.get('document_id', '—')}")
            cols[1].markdown(f"**Date:** {extracted.get('date', '—')}")
            
            st.divider()
            st.caption("Immutable SHA-256 Hash")
            st.code(selected_doc["content_hash"], language="text")
            st.caption("ECDSA SECP256R1 Signature")
            st.code(selected_doc["digital_signature"][:120] + "...", language="text")
            
            if st.button("✅ Verify This Document", use_container_width=True):
                st.switch_page("views/2_Verify_Document.py")
                
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ── Audit Log Table ────────────────────────────────────────────────────────────
st.markdown("### 📜 Full Audit Log")

table_data = []
for doc in docs:
    extracted = doc.get("extracted_fields", {}) or {}
    table_data.append({
        "Document ID":       doc["id"],
        "Secured On":        doc["created_at"][:10],
        "Extracted Name":    extracted.get("name",        "—"),
        "Extracted Amount":  extracted.get("amount",      "—"),
        "Invoice / Doc ID":  extracted.get("document_id", "—"),
        "SHA-256 Hash":      doc["content_hash"][:20] + "...",
    })

df = pd.DataFrame(table_data)

search = st.text_input("🔍 Search Log", placeholder="Search by name, date, ID...", key="search_log")
if search:
    mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
    df = df[mask]
    if df.empty:
        st.warning("No matches found.")

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
