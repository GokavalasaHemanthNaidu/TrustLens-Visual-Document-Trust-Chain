# -*- coding: utf-8 -*-
import streamlit as st
import time
import requests
import validators
import re
from PIL import Image
from io import BytesIO
from utils import hashing, crypto_signer, db_client
from utils.ml_classifier import analyze_document, flatten_for_db
from models.document import DocumentModel
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Auth guard ─────────────────────────────────────────────────────────────────
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔐 Please login first.")
    st.stop()

user = st.session_state.user

# ── Google Drive URL Helper ────────────────────────────────────────────────────
def convert_drive_url(url: str) -> str:
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m2: return f"https://drive.google.com/uc?export=download&id={m2.group(1)}"
    return url

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
                padding: 15px; border-radius: 10px; margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center;'>
        <div style='font-size: 32px; margin-bottom: 5px;'>👨‍🎓</div>
        <div style='color: white; font-weight: bold; font-size: 15px; word-break: break-all;'>
            {user.email.split('@')[0].replace('.', ' ').title()}
        </div>
        <div style='color: #93C5FD; font-size: 12px; margin-top: 3px;'>Verified Account</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📊 My Vault", use_container_width=True):
        st.switch_page("views/3_Trust_Analytics.py")
    st.divider()
    st.caption(APP_VERSION)

# ── Page Header ────────────────────────────────────────────────────────────────
st.title("📤 Secure New Document")
st.markdown("""
<div style='background:rgba(59,130,246,0.08);border:1px solid #3B82F6;
border-radius:10px;padding:12px;margin-bottom:16px;font-size:14px'>
🧠 <b>Universal AI Analysis:</b> Our multi-layer AI automatically identifies <i>any</i> document —
Aadhaar, PAN, Passport, Invoice, Resume, Certificate, and more — with confidence scoring.
No manual selection needed.
</div>
""", unsafe_allow_html=True)

# ── Optional override ──────────────────────────────────────────────────────────
with st.expander("⚙️ Override Category (Optional — AI auto-detects)", expanded=False):
    doc_type_override = st.text_input(
        "Force a category label:",
        placeholder="Leave blank for AI auto-detection"
    )

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
    url_input = st.text_input("Paste URL:", placeholder="Google Drive link or direct image URL...")
    if url_input and st.button("📥 Fetch Image"):
        if "drive.google.com/drive/folders" in url_input:
            st.error("❌ Folder link detected. Share a single file instead.")
        elif not validators.url(url_input):
            st.error("❌ Invalid URL.")
        else:
            try:
                with st.spinner("Fetching..."):
                    direct = convert_drive_url(url_input)
                    resp = requests.get(direct, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                    resp.raise_for_status()
                    img  = Image.open(BytesIO(resp.content))
                    fname = url_input.split("/")[-1][:40] or "remote_doc.jpg"
                    processed_images.append((img, fname, resp.content))
                    st.success(f"✅ Fetched: `{fname}`")
            except Exception as e:
                st.error(f"Fetch error: {e}")

# ── Anchor Button ──────────────────────────────────────────────────────────────
if processed_images:
    st.divider()
    if st.button("🔐 Anchor to Trust Chain", type="primary", use_container_width=True):
        for img, name, bytes_data in processed_images:
            status_box = st.empty()
            with status_box.container():
                st.markdown(f"### ⚙️ Processing: `{name}`")
                progress = st.progress(0, text="Initializing AI pipeline...")

                # ── Stage 1–5: Universal AI Analysis ──────────────────────
                progress.progress(20, text="🧠 AI analyzing document type & fields...")
                ai_result = analyze_document(img, name)
                flat      = flatten_for_db(ai_result, doc_type_override.strip() if doc_type_override else "")

                # ── Stage 6: Hashing ───────────────────────────────────────
                progress.progress(55, text="🔒 SHA-256 fingerprinting...")
                content_hash = hashing.create_hash(flat)

                # ── Stage 7: ECDSA Signing ─────────────────────────────────
                progress.progress(72, text="✍️ ECDSA signing...")
                priv, pub = crypto_signer.generate_keypair()
                sig = crypto_signer.sign_hash(content_hash, priv)

                # ── Stage 8: Upload & Save ─────────────────────────────────
                progress.progress(88, text="☁️ Uploading to immutable ledger...")
                image_url = db_client.upload_image_to_storage(user.id, bytes_data, name)
                if image_url:
                    doc_model = DocumentModel(
                        user_id=user.id, image_url=image_url,
                        extracted_fields=flat,
                        content_hash=content_hash,
                        digital_signature=sig, did_public_key=pub
                    )
                    db_client.save_document_record(doc_model)

                progress.progress(100, text="✅ Complete!")
                time.sleep(0.5)

            status_box.empty()

            # ── Rich Success Card ──────────────────────────────────────────
            doc_type   = flat.get("doc_type", "Document")
            confidence = flat.get("ml_confidence", 0.0)
            ml_used    = flat.get("ml_used", False)
            entities   = ai_result.get("entities", {})

            badge_color = "#10B981" if confidence >= 80 else \
                          "#F59E0B" if confidence >= 50 else "#6B7280"

            st.markdown(f"""
<div style='border:1px solid {badge_color};border-radius:14px;
     padding:18px;margin:10px 0;background:rgba(0,0,0,0.2)'>
  <div style='font-size:20px;font-weight:700;color:{badge_color};margin-bottom:10px'>
    ✅ {doc_type}
    {"&nbsp;<span style='font-size:13px;background:" + badge_color +
     ";color:white;padding:3px 10px;border-radius:20px'>🧠 " + str(confidence) + "% AI Confidence</span>"
     if ml_used else ""}
  </div>
  <table style='width:100%;border-collapse:collapse;font-size:13px'>
    <tr>
      <td style='padding:4px 8px;color:#9CA3AF'>🙍 Name</td>
      <td style='padding:4px 8px;color:white;font-weight:600'>
        {entities.get('name',{}).get('value','—')}
        <span style='color:#6B7280;font-size:11px'>
          ({entities.get('name',{}).get('confidence',0):.0f}% conf)
        </span>
      </td>
      <td style='padding:4px 8px;color:#9CA3AF'>🆔 Ref ID</td>
      <td style='padding:4px 8px;color:white;font-weight:600'>
        {entities.get('document_id',{}).get('value','—')}
        <span style='color:#6B7280;font-size:11px'>
          ({entities.get('document_id',{}).get('confidence',0):.0f}% conf)
        </span>
      </td>
    </tr>
    <tr>
      <td style='padding:4px 8px;color:#9CA3AF'>📅 Date / DOB</td>
      <td style='padding:4px 8px;color:white'>
        {entities.get('date',{}).get('value','—')}
      </td>
      <td style='padding:4px 8px;color:#9CA3AF'>💰 Amount</td>
      <td style='padding:4px 8px;color:white'>
        {entities.get('amount',{}).get('value','—') or '—'}
      </td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)
