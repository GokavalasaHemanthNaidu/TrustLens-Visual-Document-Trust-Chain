# -*- coding: utf-8 -*-
import streamlit as st
import time
import requests
import validators
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
    if st.button("📊 My Vault", use_container_width=True):
        st.switch_page("views/3_Trust_Analytics.py")
    st.divider()
    st.caption(f"{APP_VERSION}")

# ── Page Content ───────────────────────────────────────────────────────────────
st.title("📤 Secure New Document")
st.markdown("Secure an image by uploading a file or providing a public link.")

tab_file, tab_link = st.tabs(["📁 Local File", "🔗 Public Link (Drive/Web)"])

processed_images = [] # List of (image, filename) tuples

with tab_file:
    uploaded_files = st.file_uploader(
        "Choose images...", type=["png", "jpg", "jpeg"], accept_multiple_files=True
    )
    if uploaded_files:
        for f in uploaded_files:
            processed_images.append((Image.open(f), f.name, f.getvalue()))

with tab_link:
    st.info("💡 Ensure the link is direct (ends in .jpg/.png) or a shared Google Drive link.")
    url = st.text_input("Paste Image URL:", placeholder="https://example.com/document.jpg")
    if url and st.button("📥 Fetch from Link"):
        if not validators.url(url):
            st.error("Invalid URL format.")
        else:
            try:
                with st.spinner("Downloading image..."):
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    img = Image.open(BytesIO(resp.content))
                    processed_images.append((img, url.split("/")[-1] or "remote_doc.jpg", resp.content))
                    st.success("Image fetched successfully!")
            except Exception as e:
                st.error(f"Failed to fetch image: {e}")

if processed_images:
    if st.button("🔐 Anchor to Trust Chain", type="primary", use_container_width=True):
        for img, name, bytes_data in processed_images:
            st.markdown(f"---\n### ⚙️ Processing: `{name}`")
            progress = st.progress(0, text="Starting...")

            # 1. AI Extraction
            progress.progress(20, text="AI: Extracting text & patterns...")
            raw_text = ocr_processor.process_image(img)
            extracted = ocr_processor.extract_fields(raw_text)
            
            # Fallback: If AI finds nothing (like in a photo), use the filename
            if not any(extracted.values()):
                extracted["name"] = name.split(".")[0].replace("_", " ").title()
                extracted["document_id"] = "GEN-" + str(int(time.time()))[-6:]

            # 2. Hashing
            progress.progress(50, text="Crypto: Generating SHA-256 fingerprint...")
            content_hash = hashing.create_hash(extracted)
            
            # 3. Signing
            progress.progress(80, text="Identity: Signing with ECDSA SECP256R1...")
            priv, pub = crypto_signer.generate_keypair()
            sig = crypto_signer.sign_hash(content_hash, priv)
            
            # 4. Anchoring
            image_url = db_client.upload_image_to_storage(user.id, bytes_data, name)
            if image_url:
                doc_model = DocumentModel(
                    user_id=user.id, image_url=image_url, extracted_fields=extracted,
                    content_hash=content_hash, digital_signature=sig, did_public_key=pub
                )
                db_client.save_document_record(doc_model)
                st.success(f"✅ Secured! Name: **{extracted.get('name')}**")
            
            progress.progress(100, text="Complete!")
            time.sleep(0.5)
            progress.empty()

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | {APP_VERSION}</div>",
    unsafe_allow_html=True,
)
