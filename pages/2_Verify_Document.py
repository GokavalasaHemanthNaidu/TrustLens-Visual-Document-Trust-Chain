import streamlit as st
import json
from components.certificate import generate_pdf_certificate
from utils import crypto_signer, hashing, db_client
from models.document import DocumentModel

st.set_page_config(page_title="TrustLens | Verify", page_icon="âœ…", layout="wide")

st.title("âœ… Verify Document Integrity")

doc_id = st.text_input("Enter Document ID to verify:", placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000")

if st.button("Verify Provenance") and doc_id:
    with st.spinner("Fetching Immutable Record..."):
        doc_record = db_client.get_document_by_id(doc_id)
        
    if doc_record:
        st.success("Document Found in TrustLens Ledger!")
        
        # Instantiate Model
        doc_model = DocumentModel(
            user_id=doc_record['user_id'],
            image_url=doc_record['image_url'],
            extracted_fields=doc_record['extracted_fields'],
            content_hash=doc_record['content_hash'],
            digital_signature=doc_record['digital_signature'],
            did_public_key=doc_record['did_public_key'],
            id=doc_record['id'],
            created_at=doc_record['created_at']
        )
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(doc_model.image_url, caption="Stored Document", use_column_width=True)
            
        with col2:
            st.markdown("### Zero-Knowledge Verification")
            
            # Step 1: Re-hash
            with st.expander("1. Re-calculate Hash from Extracted Data", expanded=True):
                st.json(doc_model.extracted_fields)
                recalc_hash = hashing.create_hash(doc_model.extracted_fields)
                st.code(f"Recalculated Hash: {recalc_hash}")
                if recalc_hash == doc_model.content_hash:
                    st.success("Data Hash matches Ledger Hash.")
                else:
                    st.error("TAMPERING DETECTED: Data Hash mismatch.")
            
            # Step 2: Validate Signature
            with st.expander("2. Validate Cryptographic Signature", expanded=True):
                pub_key_lines = doc_model.did_public_key.strip().split('\\n')
                pub_key_preview = pub_key_lines[1][:40] if len(pub_key_lines) > 1 else doc_model.did_public_key[:40]
                st.code(f"Public Key: {pub_key_preview}...")
                
                is_valid = crypto_signer.verify_signature(
                    content_hash=recalc_hash,
                    signature_b64=doc_model.digital_signature,
                    public_pem=doc_model.did_public_key
                )
                
                if is_valid:
                    st.success("âœ… ECDSA Signature Valid. Provenance mathematically proven.")
                else:
                    st.error("âŒ Signature INVALID. Document was forged or tampered with.")
                    
        # Certificate Download
        st.divider()
        st.markdown("### Export Trust Certificate")
        st.markdown("Download a PDF certificate proving the cryptographic integrity of this document.")
        
        # Use st.query_params or window origin to construct the verification URL
        verification_url = f"https://trustlens-visual-document-trust-chain.streamlit.app/?doc_id={doc_id}"
        
        pdf_bytes = generate_pdf_certificate(doc_model, verification_url)
        if pdf_bytes:
            st.download_button(
                label="ðŸ“¥ Download PDF Certificate",
                data=pdf_bytes,
                file_name=f"TrustCertificate_{doc_id}.pdf",
                mime="application/pdf",
                type="primary"
            )
            
    else:
        st.error("Document not found or Invalid ID.")
