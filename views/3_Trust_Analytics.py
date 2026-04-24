# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from utils import db_client
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Auth guard ─────────────────────────────────────────────────────────────────
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔐 Please login first.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    user = st.session_state.user
    st.markdown(f"**👤** `{user.email}`")
    st.divider()
    st.caption(f"{APP_VERSION}")

# ── Page Content ────────────────────────────────────────────────────────────────
st.title("📊 My Secure Vault")
st.markdown("Search and inspect your anchored documents.")

with st.spinner("Loading ledger..."):
    docs = db_client.get_user_documents(user.id)

if not docs:
    st.info("📭 Vault is empty.")
    st.stop()

# ── Audit Log Table ────────────────────────────────────────────────────────────
st.markdown("### 📜 Audit Log")

table_data = []
for doc in docs:
    ex = doc.get("extracted_fields", {}) or {}
    table_data.append({
        "ID":                doc["id"][:8] + "...",
        "Date":              doc["created_at"][:10],
        "Category":          ex.get("doc_type", "Document"), # New field
        "Name":              ex.get("name", "—"),
        "Reference ID":      ex.get("document_id", "—"),
        "Full_ID":           doc["id"] # Hidden for selection
    })

df = pd.DataFrame(table_data)
search = st.text_input("🔍 Search Vault", placeholder="Search by name, category, or ID...", key="search_v")
if search:
    mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
    df = df[mask]

st.dataframe(df.drop(columns=["Full_ID"]), use_container_width=True, hide_index=True)

# ── Vault Viewer ───────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 🖼️ Document Inspector")
selected_row = st.selectbox("Select document to inspect:", options=df["Full_ID"].tolist(), 
                            format_func=lambda x: f"{df[df['Full_ID']==x]['Category'].values[0]} | {df[df['Full_ID']==x]['Name'].values[0]} ({df[df['Full_ID']==x]['Date'].values[0]})")

if selected_row:
    # Find doc by full ID
    selected_doc = next(d for d in docs if d["id"] == selected_row)
    ex = selected_doc.get("extracted_fields", {}) or {}
    
    with st.container(border=True):
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.image(selected_doc["image_url"], use_column_width=True)
            st.link_button("🔗 Open Original Image", selected_doc["image_url"], use_container_width=True)
        with c2:
            st.markdown(f"#### 📄 {ex.get('doc_type', 'Document')} Details")
            st.markdown(f"**Subject:** {ex.get('name', '—')}")
            st.markdown(f"**Ref ID:** `{ex.get('document_id', '—')}`")
            st.markdown(f"**Secured On:** {selected_doc['created_at'][:19]}")
            st.divider()
            st.caption("Cryptographic Hash")
            st.code(selected_doc["content_hash"], language="text")
            if st.button("✅ Run Verification Page", use_container_width=True):
                st.switch_page("views/2_Verify_Document.py")

# ── Export ──────────────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Export Vault (CSV)", csv, "TrustLens_Vault.csv", "text/csv")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px'>© 2026 {APP_NAME}</div>", unsafe_allow_html=True)
