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
    if st.button("📤 Secure New Document", use_container_width=True):
        st.switch_page("views/1_Upload_Document.py")
    st.divider()
    st.caption(f"{APP_VERSION}")

# ── Page Content ────────────────────────────────────────────────────────────────
st.title("📊 My Secure Vault")
st.markdown("View, search, and manage your anchored documents.")

# Fetch documents
with st.spinner("Accessing ledger..."):
    docs = db_client.get_user_documents(user.id)

if not docs:
    st.info("📭 Your vault is empty. Secure your first document to see it here!")
    st.stop()

# ── Audit Log Table ────────────────────────────────────────────────────────────
st.markdown("### 📜 Audit Log")

table_data = []
for doc in docs:
    ex = doc.get("extracted_fields", {}) or {}
    table_data.append({
        "ID":                doc["id"][:8] + "...",
        "Date":              doc["created_at"][:10],
        "Category":          ex.get("doc_type", "Document"),
        "Name":              ex.get("name", "—"),
        "Reference ID":      ex.get("document_id", "—"),
        "Full_ID":           doc["id"]
    })

df = pd.DataFrame(table_data)
search = st.text_input("🔍 Search Vault", placeholder="Search by name, category, or ID...", key="search_v")
if search:
    mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
    df = df[mask]

st.dataframe(df.drop(columns=["Full_ID"]), use_container_width=True, hide_index=True)

# ── Document Inspector & Delete Logic ──────────────────────────────────────────
st.divider()
st.markdown("### 🖼️ Document Inspector")

# Formatter for the dropdown
def doc_label(doc_id):
    row = df[df["Full_ID"] == doc_id].iloc[0]
    return f"[{row['Category']}] {row['Name']} — {row['Date']}"

selected_doc_id = st.selectbox("Select document to inspect or manage:", 
                               options=df["Full_ID"].tolist(), 
                               format_func=doc_label)

if selected_doc_id:
    # Find full doc object
    selected_doc = next(d for d in docs if d["id"] == selected_doc_id)
    ex = selected_doc.get("extracted_fields", {}) or {}
    
    with st.container(border=True):
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.image(selected_doc["image_url"], use_column_width=True, caption="Original Anchor")
            st.link_button("🔗 Open Full Image", selected_doc["image_url"], use_container_width=True)
        with c2:
            st.markdown(f"#### 📄 {ex.get('doc_type', 'Document')} Details")
            st.markdown(f"**Name:** `{ex.get('name', '—')}`")
            st.markdown(f"**Ref ID:** `{ex.get('document_id', '—')}`")
            st.markdown(f"**Ledger ID:** `{selected_doc['id']}`")
            st.markdown(f"**Secured On:** {selected_doc['created_at'][:19]}")
            
            st.divider()
            
            # Action Buttons
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Verify Now", use_container_width=True, type="primary"):
                    st.switch_page("views/2_Verify_Document.py")
            with col_b:
                # 🔴 Delete Operation
                if st.button("🗑️ Delete Record", use_container_width=True):
                    with st.spinner("Removing from ledger..."):
                        success = db_client.delete_document_record(selected_doc["id"], selected_doc["image_url"])
                        if success:
                            st.success("Document deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to delete document.")

            st.caption("Warning: Deletion is permanent and removes the cryptographic proof from the ledger.")

# ── Export ──────────────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Export Vault (CSV)", csv, "TrustLens_Vault.csv", "text/csv")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px'>© 2026 {APP_NAME}</div>", unsafe_allow_html=True)
