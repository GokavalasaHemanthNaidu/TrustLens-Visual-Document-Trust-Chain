# -*- coding: utf-8 -*-
import streamlit as st
import time
from PIL import Image
from io import BytesIO
from utils import ocr_processor, hashing, crypto_signer, db_client
from models.document import DocumentModel
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
    with st.expander("ℹ️ Upload Help", expanded=False):
        st.markdown(f"""
- Accepted: **PNG, JPG, JPEG** · Max **200 MB**
- AI OCR scans for Name, Date, Amount, Invoice No
- SHA-256 hash generated from extracted fields
- Signed with ECDSA SECP256R1 private key
- Anchored to Supabase immutable ledger

📧 [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})
        """)
    st.caption(f"{APP_VERSION}")

# ── Page Content ───────────────────────────────────────────────────────────────
st.title("📤 Secure Document Upload")
st.markdown("Upload documents to extract, hash, and anchor them onto the Trust Chain.")

uploaded_files = st.file_uploader(
    "Drag and drop documents here",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="200 MB per file · PNG, JPG, JPEG",
    key="upload_files",
)

if uploaded_files:
    if st.button("🔐 Anchor to Trust Chain", type="primary", use_container_width=True, key="btn_anchor"):
        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.getvalue()
            if len(file_bytes) > 200 * 1024 * 1024:
                st.error(f"❌ {uploaded_file.name} exceeds the 200 MB limit.")
                continue

            st.markdown(f"---\n### ⚙️ Processing: `{uploaded_file.name}`")
            progress = st.progress(0, text="Starting…")

            # Phase 1: OCR
            progress.progress(15, text="Phase 1: AI Extraction — scanning document…")
            image = Image.open(BytesIO(file_bytes))
            raw_text = ocr_processor.process_image(image)
            extracted_fields = ocr_processor.extract_fields(raw_text)
            time.sleep(0.4)

            # Phase 2: Hashing
            progress.progress(40, text="Phase 2: Deterministic Hashing — generating SHA-256…")
            content_hash = hashing.create_hash(extracted_fields)
            time.sleep(0.4)

            # Phase 3: Signing
            progress.progress(65, text="Phase 3: Digital Signature — applying ECDSA keypair…")
            private_pem, public_pem = crypto_signer.generate_keypair()
            signature = crypto_signer.sign_hash(content_hash, private_pem)
            time.sleep(0.4)

            # Phase 4: Anchoring
            progress.progress(85, text="Phase 4: Ledger Anchoring — uploading to encrypted storage…")
            image_url = db_client.upload_image_to_storage(
                st.session_state.user.id, file_bytes, uploaded_file.name
            )
            if image_url:
                doc_model = DocumentModel(
                    user_id=st.session_state.user.id,
                    image_url=image_url,
                    extracted_fields=extracted_fields,
                    content_hash=content_hash,
                    digital_signature=signature,
                    did_public_key=public_pem,
                )
                db_client.save_document_record(doc_model)

            progress.progress(100, text="✅ Complete!")
            time.sleep(0.3)
            progress.empty()

            st.success(f"✅ **{uploaded_file.name}** secured on the Trust Chain!")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(image, caption=uploaded_file.name, use_column_width=True)
            with c2:
                st.markdown("**Extracted Fields:**")
                st.json(extracted_fields if extracted_fields else {"status": "No fields extracted — check OCR"})
                st.code(f"SHA-256: {content_hash}", language="text")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | <a href='{GITHUB_URL}' target='_blank'>GitHub Repo</a> | {APP_VERSION}</div>",
    unsafe_allow_html=True,
)
