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
    file_id_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if file_id_match: return f"https://drive.google.com/uc?export=download&id={file_id_match.group(1)}"
    id_param_match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if id_param_match: return f"https://drive.google.com/uc?export=download&id={id_param_match.group(1)}"
    return url

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    user = st.session_state.user
    st.markdown(f"**👤** `{user.email}`")
    if st.button("📊 My Vault", use_container_width=True): st.switch_page("views/3_Trust_Analytics.py")
    st.divider()
    st.caption(f"{APP_VERSION}")

# ── Page Content ───────────────────────────────────────────────────────────────
st.title("📤 Secure New Document")
st.markdown("Secure a document to the Trust Chain by uploading or linking.")

# 1. Document Type Selector
doc_type_choice = st.selectbox(
    "Select Document Category:",
    ["Aadhaar Card", "PAN Card", "Passport", "Resume / CV", "Invoice / Receipt", "Other Certificate"],
    index=4,
    help="Select 'Other' to provide a custom name."
)

# 2. Custom Category Input (Only if 'Other' selected)
final_doc_type = doc_type_choice
if doc_type_choice == "Other Certificate":
    custom_type = st.text_input("Enter Custom Document Type:", placeholder="e.g. Birth Certificate, Degree, etc.")
    if custom_type:
        final_doc_type = custom_type

tab_file, tab_link = st.tabs(["📁 Local File", "🔗 Public Link"])

processed_images = []

with tab_file:
    uploaded_files = st.file_uploader("Images...", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files: processed_images.append((Image.open(f), f.name, f.getvalue()))

with tab_link:
    url_input = st.text_input("Paste Image URL:", placeholder="Google Drive or direct link...")
    if url_input and st.button("📥 Fetch Image"):
        if "drive.google.com/drive/folders" in url_input: st.error("Link is a Folder. Provide a single file link.")
        elif not validators.url(url_input): st.error("Invalid URL.")
        else:
            try:
                with st.spinner("Fetching..."):
                    direct_url = convert_drive_url(url_input)
                    resp = requests.get(direct_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                    resp.raise_for_status()
                    img = Image.open(BytesIO(resp.content))
                    processed_images.append((img, url_input.split("/")[-1][:20] or "remote_doc.jpg", resp.content))
                    st.success("✅ Fetched!")
            except Exception as e: st.error(f"Error: {e}")

if processed_images:
    if st.button("🔐 Anchor to Trust Chain", type="primary", use_container_width=True):
        for img, name, bytes_data in processed_images:
            status_container = st.empty()
            with status_container.container():
                st.markdown(f"---\n### ⚙️ Processing: `{name}`")
                progress = st.progress(0, text="AI Scanning...")

                # 1. AI Extraction
                raw_text = ocr_processor.process_image(img)
                extracted = ocr_processor.extract_fields(raw_text)
                
                # Save the final category (either selected or custom)
                extracted["doc_type"] = final_doc_type
                
                # Fallback for Name
                if not extracted.get("name"):
                    extracted["name"] = name.split(".")[0].replace("_", " ").title()
                
                # Ensure unique internal ID
                if not extracted.get("document_id"):
                    extracted["document_id"] = "TRU-" + str(int(time.time()))[-5:]

                # 2. Hashing
                progress.progress(40, text="Hashing Data...")
                content_hash = hashing.create_hash(extracted)
                
                # 3. Signing
                progress.progress(70, text="Digital Signature...")
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
                
                progress.progress(100, text="Success!")
                time.sleep(0.5)

            status_container.empty()
            st.success(f"✅ Secured! [{final_doc_type}] — {extracted.get('name')} (ID: {extracted.get('document_id')})")
