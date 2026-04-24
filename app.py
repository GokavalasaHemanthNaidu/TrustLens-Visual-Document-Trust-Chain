import streamlit as st
import time
from PIL import Image
import json
import uuid
import qrcode
from io import BytesIO

# Import project modules
from modules import auth, db_client, ocr_engine, crypto_chain

# --- Page Config ---
st.set_page_config(page_title="Visual Document Trust Chain", page_icon="🔗", layout="wide")

# --- Custom CSS for Premium Look ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #2b6cb0;
        color: white;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #2c5282; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .card {
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 24px;
    }
    .hash-box {
        font-family: monospace;
        background-color: #edf2f7;
        padding: 12px;
        border-radius: 6px;
        word-break: break-all;
        font-size: 14px;
        border-left: 4px solid #4299e1;
    }
    .valid-badge {
        background-color: #c6f6d5;
        color: #22543d;
        padding: 8px 16px;
        border-radius: 999px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# --- Check Authentication ---
session = auth.get_current_session()
if session and getattr(session, 'user', None):
    st.session_state.user = session.user
else:
    st.session_state.user = None

# --- Routing ---
def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("🔗 Trust Chain")
    st.markdown("---")
    
    # Public Verify Search
    st.markdown("### Public Verification")
    verify_id = st.text_input("Enter Document ID to Verify", placeholder="UUID...")
    if st.button("Verify Document", key="btn_verify_search"):
        if verify_id:
            st.session_state.verify_id = verify_id
            navigate_to("verify")
    
    st.markdown("---")
    
    if st.session_state.user:
        st.write(f"Logged in as: **{st.session_state.user.email}**")
        if st.button("Upload New Document"): navigate_to("upload")
        if st.button("My Documents"): navigate_to("mydocs")
        if st.button("Logout"):
            auth.sign_out()
            st.session_state.user = None
            navigate_to("login")
    else:
        if st.button("Login / Signup"): navigate_to("login")

# --- Page: Login / Signup ---
if st.session_state.page == 'login':
    st.markdown("<h1 style='text-align: center;'>Welcome to Visual Document Trust Chain</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #4a5568;'>Securely digitize, hash, and sign your documents into verifiable assets.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            log_email = st.text_input("Email", key="log_email")
            log_pass = st.text_input("Password", type="password", key="log_pass")
            if st.button("Login", key="btn_login"):
                with st.spinner("Authenticating..."):
                    res, err = auth.sign_in(log_email, log_pass)
                    if err:
                        st.error(f"Login failed: {err}")
                    else:
                        st.success("Logged in successfully!")
                        st.session_state.user = res.user
                        time.sleep(1)
                        navigate_to("mydocs")
        
        with tab2:
            sig_email = st.text_input("Email", key="sig_email")
            sig_pass = st.text_input("Password", type="password", key="sig_pass")
            if st.button("Sign Up", key="btn_signup"):
                with st.spinner("Creating account..."):
                    res, err = auth.sign_up(sig_email, sig_pass)
                    if err:
                        st.error(f"Signup failed: {err}")
                    else:
                        st.success("Account created! Please check your email to verify (or just try logging in if auto-confirm is enabled in Supabase).")
        st.markdown("</div>", unsafe_allow_html=True)

# --- Page: Upload & Process ---
elif st.session_state.page == 'upload':
    if not st.session_state.user:
        st.warning("Please login first.")
        st.stop()
        
    st.title("Upload & Securify Document")
    
    uploaded_file = st.file_uploader("Choose an image (Invoice, ID, Receipt...)", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Document", use_column_width=True)
        
        if st.button("Start Trust Chain Process", key="btn_process"):
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 1. OCR
                status_text.text("Phase 1: Running OCR & Layout Detection...")
                extracted_text = ocr_engine.process_image(image)
                progress_bar.progress(30)
                
                # 2. Extract Fields
                status_text.text("Phase 2: Extracting Structured Fields...")
                fields = ocr_engine.extract_fields(extracted_text)
                # If fields are empty, just store raw text as fallback
                if not fields:
                    fields = {"raw_text": extracted_text[:500] + "..."}
                progress_bar.progress(50)
                
                # 3. Cryptography (Hash & Sign)
                status_text.text("Phase 3: Cryptographic Hashing & Signing...")
                content_hash = crypto_chain.create_hash(fields)
                private_pem, public_pem = crypto_chain.generate_keypair()
                signature = crypto_chain.sign_hash(content_hash, private_pem)
                progress_bar.progress(75)
                
                # 4. Upload to DB
                status_text.text("Phase 4: Anchoring to Supabase...")
                # Reset stream pointer
                uploaded_file.seek(0)
                image_url = db_client.upload_image_to_storage(st.session_state.user.id, uploaded_file.read(), uploaded_file.name)
                
                if not image_url:
                    st.error("Failed to upload image to Supabase Storage. Ensure 'documents' bucket is public.")
                    st.stop()
                    
                record = db_client.save_document_record(
                    st.session_state.user.id,
                    image_url,
                    fields,
                    content_hash,
                    signature,
                    public_pem
                )
                progress_bar.progress(100)
                status_text.text("Complete! Document is now a Verifiable Credential.")
                
                st.success("Trust Chain established successfully!")
                
                # Visual Feedback
                st.markdown("### 🔗 The Visual Trust Chain")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Extracted Data (JSON):**")
                    st.json(fields)
                with col2:
                    st.markdown("**Cryptographic Proof:**")
                    st.markdown(f"**SHA256 Hash:** <div class='hash-box'>{content_hash}</div>", unsafe_allow_html=True)
                    st.markdown(f"**ECDSA Signature:** <div class='hash-box'>{signature}</div>", unsafe_allow_html=True)
                    pub_key_str = public_pem.split('\\n')[1][:40]
                    st.markdown(f"**DID Public Key:** <div class='hash-box'>{pub_key_str}...</div>", unsafe_allow_html=True)
                
                if record and len(record) > 0:
                    doc_id = record[0]['id']
                    st.info(f"Your Document ID is: **{doc_id}**")
                    if st.button("Go to My Documents"):
                        navigate_to("mydocs")
            except Exception as e:
                st.error(f"An error occurred during processing: {e}")

# --- Page: My Documents ---
elif st.session_state.page == 'mydocs':
    if not st.session_state.user:
        st.warning("Please login first.")
        st.stop()
        
    st.title("My Verified Documents")
    
    with st.spinner("Fetching documents..."):
        docs = db_client.get_user_documents(st.session_state.user.id)
        
    if not docs:
        st.info("You haven't secured any documents yet.")
        if st.button("Securify First Document"): navigate_to("upload")
    else:
        for doc in docs:
            with st.container():
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    st.image(doc['image_url'], use_column_width=True)
                
                with col2:
                    st.markdown(f"**Document ID:** `{doc['id']}`")
                    st.markdown(f"**Created:** {doc['created_at'][:10]}")
                    
                    # Display summary of fields
                    keys = list(doc['extracted_fields'].keys())
                    summary = ", ".join([f"{k}: {doc['extracted_fields'][k]}" for k in keys[:2]])
                    st.write(f"**Data:** {summary}...")
                    
                with col3:
                    if st.button("Verify Integrity", key=f"verify_{doc['id']}"):
                        st.session_state.verify_id = doc['id']
                        navigate_to("verify")
                st.markdown("</div>", unsafe_allow_html=True)

# --- Page: Public Verification ---
elif st.session_state.page == 'verify':
    st.title("Public Verification Portal")
    
    doc_id = st.session_state.get('verify_id', None)
    
    if not doc_id:
        st.warning("No Document ID specified.")
        st.stop()
        
    st.write(f"Verifying Document ID: **{doc_id}**")
    
    with st.spinner("Fetching blockchain-like record..."):
        doc = db_client.get_document_by_id(doc_id)
        
    if not doc:
        st.error("Document not found. It may be invalid or the ID is incorrect.")
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.image(doc['image_url'], caption="Original Image via IPFS/Supabase Storage")
            
            # Generate QR Code for sharing
            verify_url = f"https://[your-app-url]/verify/{doc['id']}" # Replace with actual Streamlit cloud/HF URL
            qr = qrcode.QRCode(version=1, box_size=5, border=2)
            qr.add_data(verify_url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            
            # Convert Pil Image to BytesIO for Streamlit
            buf = BytesIO()
            img_qr.save(buf, format="PNG")
            st.image(buf, caption="Scan to Verify Publicly", width=150)

        with col2:
            st.markdown("### Verification Checks")
            
            # 1. Re-compute Hash
            current_hash = crypto_chain.create_hash(doc['extracted_fields'])
            hash_match = current_hash == doc['content_hash']
            
            # 2. Verify Cryptographic Signature
            is_valid_sig = crypto_chain.verify_signature(
                doc['content_hash'], 
                doc['digital_signature'], 
                doc['did_public_key']
            )
            
            if hash_match and is_valid_sig:
                st.markdown("<div class='valid-badge'>✅ VALID & UNTAMPERED</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color:#fed7d7; color:#9b2c2c; padding:8px 16px; border-radius:999px; font-weight:bold; display:inline-block;'>❌ TAMPERED OR INVALID</div>", unsafe_allow_html=True)
            
            st.markdown("#### Proof Breakdown")
            st.write(f"✅ **Hash Integrity:** {'Match' if hash_match else 'Mismatch'}")
            st.write(f"✅ **DID Signature:** {'Verified (ECDSA)' if is_valid_sig else 'Failed'}")
            
            st.markdown("**Original Extracted Data:**")
            st.json(doc['extracted_fields'])
            
            with st.expander("View Raw Cryptographic Data"):
                st.markdown(f"**Hash:** `{doc['content_hash']}`")
                st.markdown(f"**Signature:** `{doc['digital_signature']}`")
                st.text("Public Key (PEM):")
                st.code(doc['did_public_key'])
        
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("Back"):
            if st.session_state.user:
                navigate_to("mydocs")
            else:
                navigate_to("login")
