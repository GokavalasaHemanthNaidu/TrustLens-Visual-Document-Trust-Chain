import streamlit as st
import time
from PIL import Image
from io import BytesIO
from utils import ocr_processor, hashing, crypto_signer, db_client
from models.document import DocumentModel
from components.visual_chain import render_provenance_chart
import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="TrustLens | Secure Upload", page_icon="ðŸ“¤", layout="wide")

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("Please login from the Home page first.")
    st.stop()

st.title("ðŸ“¤ Secure Document Upload")
st.markdown("Upload documents to extract, hash, and anchor them onto the Trust Chain.")

# Batch Processing Upload
uploaded_files = st.file_uploader(
    "Drag and drop documents here", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True,
    help="Maximum 5MB per file."
)

if uploaded_files:
    if st.button("Start Trust Chain Process", type="primary"):
        for uploaded_file in uploaded_files:
            # File size validation
            file_bytes = uploaded_file.getvalue()
            if len(file_bytes) > 5 * 1024 * 1024:
                st.error(f"{uploaded_file.name} exceeds the 5MB limit.")
                continue
                
            st.markdown(f"### Processing: {uploaded_file.name}")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- Phase 1: OCR ---
            status_text.text("Phase 1/4: AI Document Extraction...")
            image = Image.open(BytesIO(file_bytes))
            
            with st.spinner("Extracting text features..."):
                raw_text = ocr_processor.process_image(image)
                extracted_fields = ocr_processor.extract_fields(raw_text)
            progress_bar.progress(25)
            
            # --- Phase 2: Hashing ---
            status_text.text("Phase 2/4: Deterministic Cryptographic Hashing...")
            with st.spinner("Generating SHA-256 Checksum..."):
                content_hash = hashing.create_hash(extracted_fields)
                time.sleep(0.5) # UX delay
            progress_bar.progress(50)
            
            # --- Phase 3: Signing ---
            status_text.text("Phase 3/4: Decentralized Identity (DID) Signing...")
            with st.spinner("Generating ECDSA Signatures..."):
                private_pem, public_pem = crypto_signer.generate_keypair()
                signature = crypto_signer.sign_hash(content_hash, private_pem)
            progress_bar.progress(75)
            
            # --- Phase 4: Anchoring ---
            status_text.text("Phase 4/4: Anchoring to TrustLens Storage...")
            with st.spinner("Uploading artifacts..."):
                image_url = db_client.upload_image_to_storage(st.session_state.user.id, file_bytes, uploaded_file.name)
                if not image_url:
                    st.error("Failed to anchor image to Storage.")
                    continue
                    
                doc_model = DocumentModel(
                    user_id=st.session_state.user.id,
                    image_url=image_url,
                    extracted_fields=extracted_fields,
                    content_hash=content_hash,
                    digital_signature=signature,
                    did_public_key=public_pem
                )
                record = db_client.save_document_record(doc_model)
            
            progress_bar.progress(100)
            status_text.text("Trust Chain established successfully!")
            st.toast(f"{uploaded_file.name} secured!", icon='âœ…')
            
            # Visualization
            with st.expander("View Provenance Visualization", expanded=False):
                render_provenance_chart()
                
            # Proofs
            st.success(f"**Document Secured:** {uploaded_file.name}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Extracted Data:**")
                st.json(extracted_fields)
            with col2:
                st.markdown("**Cryptographic Proof:**")
                st.info(f"**SHA-256:** {content_hash}")
                st.info(f"**Signature:** {signature[:40]}...")
            
            st.divider()
