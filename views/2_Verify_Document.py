# -*- coding: utf-8 -*-
import streamlit as st
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
st.markdown("Verify a document using its **ID**, **Name**, or **Storage URL**.")

search_query = st.text_input(
    "Search by Document ID, Name, or URL:",
    placeholder="Enter UUID, Name (e.g. John Doe), or Image Link...",
    help="We will search the Trust Chain ledger for a matching record.",
    key="universal_search"
)

if st.button("🔍 Verify Integrity", type="primary", use_container_width=True) and search_query:
    with st.spinner("Searching the Trust Chain ledger..."):
        # We fetch ALL user documents if logged in, or try a direct ID fetch
        # To support searching by Name/URL globally, we search the DB
        doc_record = None
        
        # 1. Try Direct UUID fetch
        if len(search_query) >= 32:
            doc_record = db_client.get_document_by_id(search_query)
            
        # 2. If not found, search by Name or URL (via the DB client)
        if not doc_record:
            # Note: Adding a helper to db_client for universal search
            try:
                # Search by image_url match
                res = db_client.supabase.table("documents").select("*").or_(f"image_url.eq.{search_query},extracted_fields->>name.ilike.%{search_query}%").execute()
                if res.data:
                    doc_record = res.data[0]
            except:
                pass

    if not doc_record:
        st.error("❌ Document not found. Check the ID/Name/URL and try again.")
    else:
        st.success(f"✅ Record Found! ID: `{doc_record['id']}`")
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

        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(doc_model.image_url, caption="Secured Document", use_column_width=True)
        with c2:
            st.markdown("### 🔬 Trust Verification")
            with st.expander("Step 1: Recalculate SHA-256", expanded=True):
                recalc_hash = hashing.create_hash(doc_model.extracted_fields)
                if recalc_hash == doc_model.content_hash:
                    st.success("✅ Data Integrity Verified")
                else:
                    st.error("⚠️ DATA TAMPERED")
            
            with st.expander("Step 2: ECDSA Signature Match", expanded=True):
                is_valid = crypto_signer.verify_signature(recalc_hash, doc_model.digital_signature, doc_model.did_public_key)
                if is_valid:
                    st.success("✅ Provenance Authenticated")
                else:
                    st.error("❌ Signature Verification Failed")

        # PDF Download
        st.divider()
        cert_bytes = generate_pdf_certificate(doc_model, f"{GITHUB_URL}/verify?doc_id={doc_model.id}")
        st.download_button("📥 Download Trust Certificate", cert_bytes, f"TrustLens_{doc_model.id[:8]}.pdf", "application/pdf")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | {APP_VERSION}</div>",
    unsafe_allow_html=True,
)
