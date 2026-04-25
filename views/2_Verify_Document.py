# -*- coding: utf-8 -*-
import streamlit as st
import graphviz
from components.certificate import generate_pdf_certificate
from utils import crypto_signer, hashing, db_client
from models.document import DocumentModel
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    if st.session_state.get("user"):
        st.markdown(f"**👤** `{st.session_state.user.email}`")
        if st.button("📊 Go to My Vault", use_container_width=True):
            st.switch_page("views/3_Trust_Analytics.py")
    else:
        st.info("🌍 Public verification portal.")
    st.divider()
    st.caption(f"{APP_VERSION}")

# ── Page Content ────────────────────────────────────────────────────────────────
st.title("✅ Universal Document Verification")
st.markdown("Verify a document using its **ID**, **Name**, **Ref ID**, or **Storage URL**.")

search_query = st.text_input(
    "Search by Document ID, Name, or URL:",
    placeholder="Enter UUID, Name (e.g. John Doe), or Image Link...",
    help="We will search the Trust Chain ledger for a matching record.",
    key="universal_search"
)

if st.button("🔍 Verify Integrity", type="primary", use_container_width=True) and search_query:
    with st.spinner("Searching the Trust Chain ledger..."):
        doc_record = None
        
        # 1. Try Direct UUID fetch
        if len(search_query) >= 32:
            doc_record = db_client.get_document_by_id(search_query)
            
        # 2. If not found, search by Name or URL or Category
        if not doc_record:
            try:
                search_term = search_query.strip()
                res = db_client.supabase.table("documents").select("*").or_(
                    f"image_url.ilike.%{search_term}%,"
                    f"extracted_fields->>name.ilike.%{search_term}%,"
                    f"extracted_fields->>document_id.ilike.%{search_term}%,"
                    f"extracted_fields->>doc_type.ilike.%{search_term}%"
                ).execute()
                if res.data:
                    doc_record = res.data[0]
            except Exception as e:
                pass

    if not doc_record:
        st.error("❌ Document not found. Check the ID/Name/URL and try again.")
    else:
        doc_model = DocumentModel(
            user_id=doc_record["user_id"],
            image_url=doc_record["image_url"],
            extracted_fields=doc_record["extracted_fields"],
            content_hash=doc_record["content_hash"],
            digital_signature=doc_record["digital_signature"],
            did_public_key=doc_record["did_public_key"],
            id=doc_record["id"],
            created_at=doc_record["created_at"],
        )

        st.success("✅ Record Successfully Found in Ledger!")
        st.divider()

        # ── Visual Layout Upgrade ─────────────────────────────────────────────
        c1, c2 = st.columns([1.2, 2])
        
        ex = doc_model.extracted_fields or {}
        
        with c1:
            st.image(doc_model.image_url, caption="Secured Document Source", use_column_width=True)
            st.markdown(f"#### 📄 Document Details")
            st.markdown(f"**Category:** `{ex.get('doc_type', 'Document')}`")
            st.markdown(f"**Name:** `{ex.get('name', '—')}`")
            st.markdown(f"**Ref ID:** `{ex.get('document_id', '—')}`")

        with c2:
            st.markdown("### 🔬 Trust Chain Provenance")
            
            # --- 1. Trust Score Badge ---
            recalc_hash = hashing.create_hash(doc_model.extracted_fields)
            hash_valid = (recalc_hash == doc_model.content_hash)
            sig_valid = crypto_signer.verify_signature(recalc_hash, doc_model.digital_signature, doc_model.did_public_key)
            
            if hash_valid and sig_valid:
                st.markdown("""
                <div style='background:rgba(16, 185, 129, 0.1);border:1px solid #10B981;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px'>
                    <h2 style='color:#10B981;margin:0;font-size:32px'>🛡️ 100% Authentic</h2>
                    <p style='color:#A7F3D0;margin:0'>Data integrity and cryptographic signature fully verified.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background:rgba(239, 68, 68, 0.1);border:1px solid #EF4444;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px'>
                    <h2 style='color:#EF4444;margin:0;font-size:32px'>⚠️ TAMPER DETECTED</h2>
                    <p style='color:#FECACA;margin:0'>This document fails cryptographic verification.</p>
                </div>
                """, unsafe_allow_html=True)

            # --- 2. Interactive Trust Graph ---
            st.markdown("**Provenance Flowchart:**")
            graph = graphviz.Digraph(engine='dot')
            graph.attr(rankdir='LR', bgcolor='transparent', size="7,3")
            graph.node('A', 'Physical Doc\n(Source)', shape='note', style='filled', color='#3B82F6', fontcolor='white')
            graph.node('B', 'AI OCR\nExtraction', shape='box', style='filled', color='#10B981', fontcolor='white')
            graph.node('C', 'SHA-256\nHash', shape='box', style='filled', color='#8B5CF6', fontcolor='white')
            graph.node('D', 'ECDSA\nSignature', shape='box', style='filled', color='#F59E0B', fontcolor='white')
            graph.node('E', 'Immutable\nLedger', shape='cylinder', style='filled', color='#EF4444', fontcolor='white')
            graph.edges(['AB', 'BC', 'CD', 'DE'])
            st.graphviz_chart(graph)

            # --- 3. Progressive Disclosure (Details) ---
            with st.expander("Step 1: Recalculate SHA-256", expanded=False):
                if hash_valid:
                    st.success("✅ Content Hash Matches Exactly")
                    st.code(doc_model.content_hash, language="text")
                else:
                    st.error("❌ Content Hash Mismatch")
            
            with st.expander("Step 2: ECDSA Signature Match", expanded=False):
                if sig_valid:
                    st.success("✅ Origin Provenance Authenticated")
                    st.code(doc_model.digital_signature[:80] + "...", language="text")
                else:
                    st.error("❌ Signature Failed")
                    
            with st.expander("Step 3: Verification Timeline", expanded=False):
                st.markdown(f"**🟢 Created & Anchored:** {doc_model.created_at[:19]} UTC")
                st.markdown(f"**🔵 Verified On:** *Live Verification*")
                st.markdown(f"**🔗 Ledger ID:** `{doc_model.id}`")

        # PDF Download
        st.divider()
        cert_bytes = generate_pdf_certificate(doc_model, f"{GITHUB_URL}/verify?doc_id={doc_model.id}")
        st.download_button("📥 Download Official Trust Certificate (PDF)", cert_bytes, f"TrustLens_Certificate_{doc_model.id[:8]}.pdf", "application/pdf")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | {APP_VERSION}</div>",
    unsafe_allow_html=True,
)
