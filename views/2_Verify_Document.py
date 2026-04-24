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
        user = st.session_state.user
        st.markdown(f"**👤** `{user.email}`")
        st.markdown("🟢 **Active Session**")
    else:
        st.info("🌍 Public verification — no login required.")
    st.divider()
    with st.expander("ℹ️ Verify Help", expanded=False):
        st.markdown(f"""
**How verification works:**
1. Enter the Document ID from a trust certificate
2. TrustLens fetches the anchored record from the ledger
3. Extracted data is re-hashed with SHA-256
4. Hash is compared against the stored value
5. ECDSA signature is mathematically validated

If hashes match and signature is valid → **Document is authentic**.

📧 [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})
        """)
    st.caption(f"{APP_VERSION}")

# ── Page Content ────────────────────────────────────────────────────────────────
st.title("✅ Verify Document Integrity")
st.markdown(
    "🌍 **Anyone** can verify a document's cryptographic provenance here — no login required. "
    "This is TrustLens's zero-knowledge public audit portal."
)

# Auto-fill doc_id from QR code / URL query params
initial_doc_id = st.query_params.get("doc_id", "")
doc_id = st.text_input(
    "Enter Document ID:",
    value=initial_doc_id,
    placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000",
    help="Find this ID in your Trust Certificate PDF or Analytics dashboard.",
    key="verify_doc_id",
)

if st.button("🔍 Verify Provenance", type="primary", use_container_width=True, key="btn_verify") and doc_id:
    with st.spinner("Fetching immutable record from ledger…"):
        doc_record = db_client.get_document_by_id(doc_id)

    if not doc_record:
        st.error("❌ Document not found. Please check the ID and try again.")
    else:
        st.success("✅ Document found in TrustLens Ledger!")
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

        col_img, col_verify = st.columns([1, 2])
        with col_img:
            st.image(doc_model.image_url, caption="Anchored Document", use_column_width=True)
            st.caption(f"Anchored: {doc_record['created_at'][:10]}")

        with col_verify:
            st.markdown("### 🔬 Zero-Knowledge Verification Steps")

            # Step 1: Re-hash
            with st.expander("Step 1 — Re-calculate Hash from Stored Data", expanded=True):
                st.json(doc_model.extracted_fields)
                recalc_hash = hashing.create_hash(doc_model.extracted_fields)
                st.code(f"Re-calculated SHA-256:\n{recalc_hash}", language="text")
                st.code(f"Stored SHA-256:\n{doc_model.content_hash}", language="text")
                if recalc_hash == doc_model.content_hash:
                    st.success("✅ Hash Match — Data integrity confirmed.")
                else:
                    st.error("⚠️ TAMPERING DETECTED — Hash mismatch!")

            # Step 2: Validate Signature
            with st.expander("Step 2 — Validate ECDSA Cryptographic Signature", expanded=True):
                pub_key_preview = doc_model.did_public_key.strip()[:60]
                st.code(f"Public Key (preview):\n{pub_key_preview}…", language="text")
                is_valid = crypto_signer.verify_signature(
                    content_hash=recalc_hash,
                    signature_b64=doc_model.digital_signature,
                    public_pem=doc_model.did_public_key,
                )
                if is_valid:
                    st.success("✅ ECDSA Signature Valid — Provenance mathematically proven.")
                else:
                    st.error("❌ Signature INVALID — Document may have been forged or tampered with.")

        # Certificate Download
        st.divider()
        st.markdown("### 📄 Export Trust Certificate")
        st.markdown("Download a cryptographically-backed PDF certificate for this document.")
        verification_url = f"https://trustlens-visual-document-trust-chain.streamlit.app/?doc_id={doc_id}"
        pdf_bytes = generate_pdf_certificate(doc_model, verification_url)
        if pdf_bytes:
            st.download_button(
                label="📥 Download PDF Certificate",
                data=pdf_bytes,
                file_name=f"TrustCertificate_{doc_id[:8]}.pdf",
                mime="application/pdf",
                type="primary",
                key="dl_cert",
            )

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | <a href='{GITHUB_URL}' target='_blank'>GitHub Repo</a> | {APP_VERSION}</div>",
    unsafe_allow_html=True,
)
