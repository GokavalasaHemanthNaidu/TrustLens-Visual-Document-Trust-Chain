# -*- coding: utf-8 -*-
import streamlit as st
import time
import requests
import validators
import re
from PIL import Image
from io import BytesIO
from utils import ocr_processor, hashing, crypto_signer, db_client
from models.document import DocumentModel
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Auth guard ─────────────────────────────────────────────────────────────────
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔐 Please login first — use the **Log In** page in the sidebar.")
    st.stop()

# ── Google Drive URL Helper ────────────────────────────────────────────────────
def convert_drive_url(url: str) -> str:
    """Converts a standard Google Drive share link to a direct download link."""
    # Pattern for /file/d/ID/
    file_id_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if file_id_match:
        return f"https://drive.google.com/uc?export=download&id={file_id_match.group(1)}"
    
    # Pattern for ?id=ID
    id_param_match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if id_param_match:
        return f"https://drive.google.com/uc?export=download&id={id_param_match.group(1)}"
        
    return url

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

processed_images = [] # List of (image, filename, bytes)

with tab_file:
    uploaded_files = st.file_uploader(
        "Choose images...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="file_up"
    )
    if uploaded_files:
        for f in uploaded_files:
            processed_images.append((Image.open(f), f.name, f.getvalue()))

with tab_link:
    st.info("💡 Paste a shared **Google Drive File** link or a direct image URL.")
    url_input = st.text_input("Paste Image URL:", placeholder="https://drive.google.com/file/d/.../view", key="url_in")
    
    if url_input and st.button("📥 Fetch from Link", key="btn_fetch"):
        if "drive.google.com/drive/folders" in url_input:
            st.error("❌ Link is a **Folder**. Please provide a link to a **single image file**.")
        elif not validators.url(url_input):
            st.error("❌ Invalid URL format.")
        else:
            try:
                with st.spinner("Transforming link and fetching image..."):
                    direct_url = convert_drive_url(url_input)
                    headers = {'User-Agent': 'Mozilla/5.0'} # Avoid some bot blocks
                    resp = requests.get(direct_url, timeout=15, headers=headers)
                    resp.raise_for_status()
                    
                    # Verify content type
                    ctype = resp.headers.get('Content-Type', '')
                    if 'text/html' in ctype:
                        st.error("❌ The link returned a webpage, not an image. Ensure the Google Drive file is shared with **'Anyone with the link'**.")
                    else:
                        img = Image.open(BytesIO(resp.content))
                        processed_images.append((img, url_input.split("/")[-1][:20] or "remote_doc.jpg", resp.content))
                        st.success("✅ Image fetched successfully!")
            except Exception as e:
                st.error(f"❌ Failed to fetch image: {e}")

if processed_images:
    if st.button("🔐 Anchor to Trust Chain", type="primary", use_container_width=True, key="btn_anchor"):
        for img, name, bytes_data in processed_images:
            st.markdown(f"---\n### ⚙️ Processing: `{name}`")
            progress = st.progress(0, text="Starting...")

            # 1. AI Extraction
            progress.progress(20, text="AI: Extracting text & patterns...")
            raw_text = ocr_processor.process_image(img)
            extracted = ocr_processor.extract_fields(raw_text)
            
            # Fallback
            if not any(extracted.values()):
                extracted["name"] = name.split(".")[0].replace("_", " ").replace("-", " ").title()
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
