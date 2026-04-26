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

# ── Document Gallery & Bulk Management ─────────────────────────────────────────
st.divider()
st.markdown("### 🖼️ Document Gallery")
st.caption("View, select, and manage your secured documents.")

# 1. Initialize native session state for checkboxes
for d in docs:
    key = f"select_{d['id']}"
    if key not in st.session_state:
        st.session_state[key] = False

# 2. Action Bar
col_a, col_b, col_c, col_d = st.columns([1.5, 1.5, 2, 2])
with col_a:
    if st.button("☑️ Select All", use_container_width=True):
        for d in docs: st.session_state[f"select_{d['id']}"] = True
        st.rerun()
with col_b:
    if st.button("☐ Deselect All", use_container_width=True):
        for d in docs: st.session_state[f"select_{d['id']}"] = False
        st.rerun()

# 3. Get currently selected documents
selected_docs = [d for d in docs if st.session_state.get(f"select_{d['id']}", False)]

with col_d:
    if selected_docs:
        if st.button(f"🗑️ Delete Selected ({len(selected_docs)})", type="primary", use_container_width=True):
            with st.spinner("Erasing from immutable ledger..."):
                for doc_to_delete in selected_docs:
                    db_client.delete_document_record(doc_to_delete["id"], doc_to_delete["image_url"])
                    # Clean up state
                    st.session_state.pop(f"select_{doc_to_delete['id']}", None)
            st.success(f"Deleted {len(selected_docs)} documents!")
            time.sleep(1)
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# 4. Create the 3-column Grid
cols = st.columns(3)
for idx, doc in enumerate(docs):
    ex = doc.get("extracted_fields", {}) or {}
    doc_id = doc["id"]
    with cols[idx % 3]:
        with st.container(border=True):
            # Native checkbox
            st.checkbox("Select Document", key=f"select_{doc_id}")
            
            st.image(doc["image_url"], use_container_width=True)
            st.markdown(f"**{ex.get('doc_type', 'Document')}**")
            
            # Show details cleanly
            name_val = ex.get("name") or "—"
            id_val = ex.get("document_id") or "—"
            st.caption(f"**Name:** {name_val[:25] + '...' if len(name_val) > 25 else name_val}")
            st.caption(f"**Ref ID:** {id_val}")
            
            st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
            
            # Action Buttons per card
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                st.link_button("🔗", doc["image_url"], use_container_width=True, help="View Original")
            with c2:
                if st.button("✅", key=f"verify_{doc_id}", use_container_width=True, help="Verify"):
                    st.switch_page("views/2_Verify_Document.py")
            with c3:
                if st.button("🗑️", key=f"del_{doc_id}", use_container_width=True, help="Delete"):
                    db_client.delete_document_record(doc_id, doc["image_url"])
                    st.session_state.pop(f"select_{doc_id}", None)
                    st.rerun()

# ── Export ──────────────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Export Vault (CSV)", csv, "TrustLens_Vault.csv", "text/csv")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px'>© 2026 {APP_NAME}</div>", unsafe_allow_html=True)
