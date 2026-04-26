# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import time
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
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
                padding: 15px; border-radius: 10px; margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center;'>
        <div style='font-size: 32px; margin-bottom: 5px;'>👨‍🎓</div>
        <div style='color: white; font-weight: bold; font-size: 15px; word-break: break-all;'>
            {user.email.split('@')[0].replace('.', ' ').title()}
        </div>
        <div style='color: #93C5FD; font-size: 12px; margin-top: 3px;'>Verified Account</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📤 Secure New Document", use_container_width=True):
        st.switch_page("views/1_Upload_Document.py")
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
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

# ── Bulk Management ──────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 🗃️ Bulk Management")
st.caption("Select documents below to perform bulk actions.")

# Add a boolean 'Select' column for bulk actions
df_bulk = df.copy()
df_bulk.insert(0, "Select", False)

edited_df = st.data_editor(
    df_bulk,
    column_config={"Select": st.column_config.CheckboxColumn("Select", help="Select rows to delete", default=False)},
    hide_index=True,
    disabled=["ID", "Date", "Category", "Name", "Reference ID", "Full_ID"],
    use_container_width=True
)

selected_rows = edited_df[edited_df["Select"]]
if not selected_rows.empty:
    if st.button(f"🗑️ Delete Selected ({len(selected_rows)})", type="primary", use_container_width=True):
        with st.spinner("Deleting selected documents from immutable ledger..."):
            for _, row in selected_rows.iterrows():
                doc_to_delete = next((d for d in docs if d["id"] == row["Full_ID"]), None)
                if doc_to_delete:
                    db_client.delete_document_record(doc_to_delete["id"], doc_to_delete["image_url"])
            st.success(f"Successfully deleted {len(selected_rows)} documents.")
            time.sleep(1)
            st.rerun()

# ── Document Gallery (Grid View) ───────────────────────────────────────────────
st.divider()
st.markdown("### 🖼️ Document Gallery")
st.caption("View all secured documents at a glance.")

# Create a 3-column grid
cols = st.columns(3)
for idx, doc in enumerate(docs):
    ex = doc.get("extracted_fields", {}) or {}
    with cols[idx % 3]:
        with st.container(border=True):
            st.image(doc["image_url"], use_container_width=True)
            st.markdown(f"**{ex.get('doc_type', 'Document')}**")
            
            # Show name and Ref ID cleanly
            name_val = ex.get("name") or "—"
            id_val = ex.get("document_id") or "—"
            st.caption(f"**Name:** {name_val[:25] + '...' if len(name_val) > 25 else name_val}")
            st.caption(f"**Ref ID:** {id_val}")
            
            st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
            
            # Action Buttons per card
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                st.link_button("🔗", doc["image_url"], use_container_width=True, help="View Original Image")
            with c2:
                if st.button("✅", key=f"verify_{doc['id']}", use_container_width=True, help="Go to Verify"):
                    st.switch_page("views/2_Verify_Document.py")
            with c3:
                if st.button("🗑️", key=f"del_{doc['id']}", use_container_width=True, help="Delete Document"):
                    db_client.delete_document_record(doc["id"], doc["image_url"])
                    st.rerun()

# ── Export ──────────────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Export Vault (CSV)", csv, "TrustLens_Vault.csv", "text/csv")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px'>© 2026 {APP_NAME}</div>", unsafe_allow_html=True)
