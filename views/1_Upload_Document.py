# -*- coding: utf-8 -*-
import streamlit as st
import time
import requests
import validators
import re
from PIL import Image
from io import BytesIO
from utils import hashing, crypto_signer, db_client
from utils.ml_classifier import analyze_document
from models.document import DocumentModel
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Auth guard ─────────────────────────────────────────────────────────────────
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔐 Please login first.")
    st.stop()

# ── Google Drive URL Helper ────────────────────────────────────────────────────
def convert_drive_url(url: str) -> str:
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m2: return f"https://drive.google.com/uc?export=download&id={m2.group(1)}"
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

# ── Page Header ────────────────────────────────────────────────────────────────
st.title("📤 Secure New Document")
st.markdown("Upload or link a document. Our **AI will auto-classify** the document type.")

# ── Manual Category (fallback only) ───────────────────────────────────────────
with st.expander("⚙️ Override Document Category (Optional)", expanded=False):
    doc_type_choice = st.selectbox(
        "Select category manually (AI will auto-detect if left as Auto):",
        ["🤖 Auto-detect (Recommended)", "Aadhaar Card", "PAN Card", "Passport",
         "Voter ID", "Driving License", "Resume / CV", "Invoice / Receipt", "Other Certificate"],
        index=0
    )
    custom_type = ""
    if doc_type_choice == "Other Certificate":
        custom_type = st.text_input("Enter custom document type:", placeholder="e.g. Birth Certificate")

# ── Upload Tabs ────────────────────────────────────────────────────────────────
tab_file, tab_link = st.tabs(["📁 Local File", "🔗 Public / Drive Link"])
processed_images = []

with tab_file:
    uploaded_files = st.file_uploader(
        "Upload document image(s):", type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    if uploaded_files:
        for f in uploaded_files:
            processed_images.append((Image.open(f), f.name, f.getvalue()))

with tab_link:
    url_input = st.text_input("Paste URL:", placeholder="Google Drive share link or any direct image URL...")
    if url_input and st.button("📥 Fetch Image"):
        if "drive.google.com/drive/folders" in url_input:
            st.error("❌ This is a folder link. Please share a single file link.")
        elif not validators.url(url_input):
            st.error("❌ Invalid URL format.")
        else:
            try:
                with st.spinner("Fetching image..."):
                    direct = convert_drive_url(url_input)
                    resp = requests.get(direct, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                    resp.raise_for_status()
                    img = Image.open(BytesIO(resp.content))
                    fname = url_input.split("/")[-1][:30] or "remote_doc.jpg"
                    processed_images.append((img, fname, resp.content))
                    st.success(f"✅ Fetched: `{fname}`")
            except Exception as e:
                st.error(f"Error fetching image: {e}")

# ── Anchor Button ──────────────────────────────────────────────────────────────
if processed_images:
    st.divider()
    if st.button("🔐 Anchor to Trust Chain", type="primary", use_container_width=True):
        for img, name, bytes_data in processed_images:
            status_box = st.empty()

            with status_box.container():
                st.markdown(f"### ⚙️ Processing: `{name}`")
                progress = st.progress(0, text="Starting...")

                # ── Step 1: ML Classification ──────────────────────────────
                progress.progress(15, text="🧠 AI classifying document type...")
                result = analyze_document(img, name)

                # Determine final doc_type
                if doc_type_choice == "🤖 Auto-detect (Recommended)":
                    final_type = result["doc_type"]
                elif doc_type_choice == "Other Certificate" and custom_type:
                    final_type = custom_type
                else:
                    final_type = doc_type_choice

                # ── Step 2: Show ML result ─────────────────────────────────
                progress.progress(35, text="✅ Classification complete...")
                confidence = result.get("confidence", 0.0)
                ml_used    = result.get("ml_used", False)

                # ── Step 3: Build extracted fields ─────────────────────────
                progress.progress(50, text="📝 Extracting document fields...")
                extracted = {
                    "doc_type":    final_type,
                    "name":        result.get("name", ""),
                    "document_id": result.get("document_id", ""),
                    "date":        result.get("date", ""),
                    "amount":      result.get("amount", ""),
                }
                # Ensure name fallback
                if not extracted["name"]:
                    extracted["name"] = name.split(".")[0].replace("_", " ").title()

                # ── Step 4: Hashing ────────────────────────────────────────
                progress.progress(65, text="🔒 Generating SHA-256 fingerprint...")
                content_hash = hashing.create_hash(extracted)

                # ── Step 5: ECDSA Signing ──────────────────────────────────
                progress.progress(80, text="✍️ Signing with ECDSA...")
                priv, pub = crypto_signer.generate_keypair()
                sig = crypto_signer.sign_hash(content_hash, priv)

                # ── Step 6: Upload + Save ──────────────────────────────────
                progress.progress(92, text="☁️ Uploading to secure ledger...")
                image_url = db_client.upload_image_to_storage(user.id, bytes_data, name)

                if image_url:
                    doc_model = DocumentModel(
                        user_id=user.id,
                        image_url=image_url,
                        extracted_fields=extracted,
                        content_hash=content_hash,
                        digital_signature=sig,
                        did_public_key=pub
                    )
                    db_client.save_document_record(doc_model)

                progress.progress(100, text="Done!")
                time.sleep(0.5)

            # Clear spinner area
            status_box.empty()

            # ── Success Card ───────────────────────────────────────────────
            if ml_used and confidence > 0:
                badge_color = "#10B981" if confidence >= 80 else "#F59E0B"
                st.markdown(f"""
                <div style='background:rgba(16,185,129,0.08);border:1px solid {badge_color};
                     border-radius:12px;padding:16px;margin:8px 0'>
                  <div style='font-size:18px;font-weight:700;color:{badge_color}'>
                    ✅ Secured — {final_type}
                  </div>
                  <div style='margin-top:6px;color:#ccc;font-size:13px'>
                    🧠 <b>AI Confidence:</b> {confidence}% &nbsp;|&nbsp;
                    🙍 <b>Name:</b> {extracted.get('name','—')} &nbsp;|&nbsp;
                    🆔 <b>Ref ID:</b> {extracted.get('document_id','—')} &nbsp;|&nbsp;
                    📅 <b>DOB:</b> {extracted.get('date','—')}
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.success(
                    f"✅ Secured — [{final_type}] | "
                    f"Name: {extracted.get('name','—')} | "
                    f"Ref ID: {extracted.get('document_id','—')}"
                )
