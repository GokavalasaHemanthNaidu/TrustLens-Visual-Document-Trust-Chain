# -*- coding: utf-8 -*-
import streamlit as st
import graphviz
import difflib
from PIL import Image
from components.certificate import generate_pdf_certificate
from utils import crypto_signer, hashing, db_client, ml_classifier
from models.document import DocumentModel
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    if st.session_state.get("user"):
        user = st.session_state.user
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#1E3A8A,#3B82F6);padding:15px;
                    border-radius:10px;margin-bottom:20px;text-align:center'>
            <div style='font-size:32px'>👨‍🎓</div>
            <div style='color:white;font-weight:bold;font-size:15px'>
                {user.email.split('@')[0].replace('.', ' ').title()}
            </div>
            <div style='color:#93C5FD;font-size:12px'>Verified Account</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📊 Go to My Vault", use_container_width=True):
            st.switch_page("views/3_Trust_Analytics.py")
        if st.button("📤 Upload Document", use_container_width=True):
            st.switch_page("views/1_Upload_Document.py")
    else:
        st.info("🌍 Public verification — no login needed.")
    st.divider()
    if st.session_state.get("user"):
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    st.caption(f"{APP_VERSION}")

# ── Page Header ─────────────────────────────────────────────────────────────
st.title("🔍 Universal Document Verification")
st.markdown("Verify any document — search by name/ID **or upload a document to detect if it's fake**.")

# ═══════════════════════════════════════════════════════════════════════════
# SHARED HELPER: render a verified/tampered record
# ═══════════════════════════════════════════════════════════════════════════
def _render_result(doc_record, extra_warning=None):
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
    ex = doc_model.extracted_fields or {}

    recalc_hash = hashing.create_hash(doc_model.extracted_fields)
    hash_valid  = (recalc_hash == doc_model.content_hash)
    sig_valid   = crypto_signer.verify_signature(
        recalc_hash, doc_model.digital_signature, doc_model.did_public_key
    )
    fully_valid = hash_valid and sig_valid

    if extra_warning:
        st.markdown(extra_warning, unsafe_allow_html=True)
    elif fully_valid:
        st.markdown("""
        <div style='background:rgba(16,185,129,0.12);border:2px solid #10B981;
                    border-radius:14px;padding:22px;text-align:center;margin-bottom:20px'>
            <span style='font-size:40px'>🛡️</span>
            <h2 style='color:#10B981;margin:4px 0'>100% AUTHENTIC</h2>
            <p style='color:#A7F3D0;margin:0;font-size:14px'>
                Cryptographic integrity verified. This document has not been tampered with.
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:rgba(239,68,68,0.12);border:2px solid #EF4444;
                    border-radius:14px;padding:22px;text-align:center;margin-bottom:20px'>
            <span style='font-size:40px'>⚠️</span>
            <h2 style='color:#EF4444;margin:4px 0'>TAMPER DETECTED</h2>
            <p style='color:#FECACA;margin:0;font-size:14px'>
                This document fails cryptographic verification. It may have been modified.
            </p>
        </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 2])
    with c1:
        st.image(doc_model.image_url, use_column_width=True, caption="📎 Original Anchored Document")
        st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
        st.markdown("#### 📋 Document Information")
        fields = [
            ("📂 Category",      ex.get("doc_type",      "—")),
            ("🙍 Name",          ex.get("name",          "—")),
            ("🆔 Ref ID",        ex.get("document_id",   "—")),
            ("📅 Date of Issue", ex.get("date_of_issue", "") or ex.get("date", "—")),
            ("🎂 Date of Birth", ex.get("dob",           "—")),
            ("⏳ Validity",      ex.get("validity",      "—")),
            ("💰 Amount",        ex.get("amount",        "—")),
            ("🗓️ Anchored On",  doc_model.created_at[:10] if doc_model.created_at else "—"),
        ]
        for label, value in fields:
            if value and value != "—":
                st.markdown(f"**{label}:** `{value}`")
        st.markdown(f"**🔗 Ledger ID:** `{doc_model.id[:16]}...`")

    with c2:
        st.markdown("### 🔬 Trust Chain Provenance")
        g = graphviz.Digraph(engine="dot")
        g.attr(rankdir="LR", bgcolor="transparent", size="7,2.5")
        ns = dict(style="filled", fontcolor="white", fontsize="11")
        g.node("A", "Physical\nDocument",  shape="note",     color="#3B82F6", **ns)
        g.node("B", "AI OCR\nExtraction",  shape="box",      color="#10B981", **ns)
        g.node("C", "SHA-256\nHash",       shape="box",      color="#8B5CF6", **ns)
        g.node("D", "ECDSA\nSignature",    shape="box",      color="#F59E0B", **ns)
        g.node("E", "Immutable\nLedger",   shape="cylinder", color="#EF4444", **ns)
        g.edges(["AB", "BC", "CD", "DE"])
        st.graphviz_chart(g)

        with st.expander("✅ Step 1 — SHA-256 Content Fingerprint", expanded=True):
            if hash_valid:
                st.success("Content hash matches exactly — data is intact.")
            else:
                st.error("Hash mismatch — data may have been altered.")
            st.code(doc_model.content_hash, language="text")

        with st.expander("✅ Step 2 — ECDSA Signature Verification", expanded=True):
            if sig_valid:
                st.success("Signature verified — origin is authentic.")
            else:
                st.error("Signature invalid — cannot confirm origin.")

        with st.expander("🕐 Step 3 — Verification Timeline"):
            st.markdown(f"- 🟢 **Anchored:** `{doc_record.get('created_at','—')[:19]} UTC`")
            st.markdown(f"- 🔵 **Public Verification:** Live (right now)")
            st.markdown(f"- 🔗 **Full Ledger ID:** `{doc_model.id}`")

    st.divider()
    cert_bytes = generate_pdf_certificate(doc_model, f"{GITHUB_URL}/verify?doc_id={doc_model.id}")
    if cert_bytes:
        st.download_button(
            "📥 Download Official Trust Certificate (PDF)",
            cert_bytes,
            f"TrustLens_Certificate_{doc_model.id[:8]}.pdf",
            "application/pdf",
            use_container_width=True,
            type="primary"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TWO TABS
# ═══════════════════════════════════════════════════════════════════════════
tab_search, tab_upload = st.tabs([
    "🔍 Search Ledger (Name / ID)",
    "📤 Upload Document — Detect Fake"
])

# ─────────────────────────────────────────────────────────────────────────
# TAB 1: SEARCH
# ─────────────────────────────────────────────────────────────────────────
with tab_search:
    st.divider()
    st.markdown("#### Step 1 — What type of document do you want to verify?")

    DOC_TYPES = [
        ("🔍 All Documents",       "all"),
        ("🪪 Aadhaar Card",        "Aadhaar Card"),
        ("💳 PAN Card",            "PAN Card"),
        ("📘 Passport",            "Passport"),
        ("🗳️ Voter ID",           "Voter ID"),
        ("🚗 Driving License",     "Driving License"),
        ("🎓 College / School ID", "id card"),
        ("🏫 10th Marksheet",      "10th Marksheet"),
        ("🏫 12th Marksheet",      "12th Marksheet"),
        ("🎓 Semester Grade Card", "Semester Grade Card"),
        ("📜 Certificate",         "Certificate"),
        ("🧾 Invoice / Receipt",   "Invoice / Receipt"),
        ("📊 Marksheet / Result",  "Marksheet / Result"),
        ("🏦 Bank Statement",      "Bank Statement"),
        ("📄 Resume / CV",         "Resume / CV"),
        ("📑 Legal Document",      "Legal Document"),
        ("📋 Other",               "Document"),
    ]
    doc_labels = [d[0] for d in DOC_TYPES]
    doc_values = [d[1] for d in DOC_TYPES]

    selected_type_label = st.radio(
        "Select document category:",
        options=doc_labels, horizontal=True, index=0,
        key="doc_type_filter", label_visibility="collapsed"
    )
    selected_type = doc_values[doc_labels.index(selected_type_label)]
    st.divider()

    st.markdown("#### Step 2 — Enter any identifying detail")
    if selected_type == "Aadhaar Card":
        placeholder = "Enter Name OR 12-digit Aadhaar Number..."
    elif selected_type == "PAN Card":
        placeholder = "Enter Name OR PAN number (e.g. ABCDE1234F)..."
    elif selected_type == "Passport":
        placeholder = "Enter Name OR Passport number (e.g. P1234567)..."
    elif selected_type == "all":
        placeholder = "Enter Name, ID, Category, URL — search everything..."
    else:
        placeholder = f"Enter Name, ID, or any detail from the {selected_type}..."

    with st.form(key="verify_form", border=False):
        search_query = st.text_input(
            "Search detail:", placeholder=placeholder,
            key="universal_search", label_visibility="collapsed"
        )
        submitted = st.form_submit_button("🔍 Verify Now", type="primary", use_container_width=True)

    if submitted:
        if not search_query.strip():
            st.warning("⚠️ Please enter a name, ID, or any detail to search.")
            st.stop()

        with st.spinner("🔎 Searching the immutable Trust Chain ledger..."):
            doc_record  = None
            search_term = search_query.strip().lower()

            try:
                if len(search_term) >= 32:
                    doc_record = db_client.get_document_by_id(search_query.strip())
            except Exception:
                pass

            if not doc_record:
                try:
                    query = db_client.supabase.table("documents").select("*")
                    TYPE_KEYWORDS = {
                        "id card": "id", "Invoice / Receipt": "invoice",
                        "Marksheet / Result": "marksheet", "10th Marksheet": "10th",
                        "12th Marksheet": "12th", "Semester Grade Card": "semester",
                        "Bank Statement": "bank", "Resume / CV": "resume",
                        "Legal Document": "legal", "Document": "",
                    }
                    filter_kw = TYPE_KEYWORDS.get(selected_type, selected_type)
                    if selected_type != "all" and filter_kw:
                        query = query.filter("extracted_fields->>doc_type", "ilike", f"%{filter_kw}%")
                    res = query.or_(
                        f"extracted_fields->>name.ilike.%{search_term}%,"
                        f"extracted_fields->>document_id.ilike.%{search_term}%,"
                        f"extracted_fields->>doc_type.ilike.%{search_term}%,"
                        f"extracted_fields->>address.ilike.%{search_term}%,"
                        f"image_url.ilike.%{search_term}%"
                    ).execute()
                    if res.data:
                        doc_record = res.data[0]
                except Exception as e:
                    st.error(f"Search error: {e}")
                    st.stop()

            if not doc_record:
                try:
                    all_q = db_client.supabase.table("documents").select("*")
                    if selected_type != "all":
                        all_q = all_q.ilike("extracted_fields->>doc_type", f"%{selected_type}%")
                    all_docs   = all_q.execute()
                    best_ratio = 0.0
                    best_doc   = None
                    for d in (all_docs.data or []):
                        ex = d.get("extracted_fields") or {}
                        for cand in [ex.get("name",""), ex.get("document_id",""), ex.get("doc_type","")]:
                            if not cand: continue
                            r = difflib.SequenceMatcher(None, search_term, cand.lower()).ratio()
                            if r > best_ratio:
                                best_ratio = r
                                best_doc   = d
                    if best_ratio >= 0.6:
                        doc_record = best_doc
                        st.info(f"🔍 Fuzzy match (similarity: {best_ratio*100:.0f}%)")
                except Exception:
                    pass

        if not doc_record:
            st.error("❌ No matching document found. Try a different name, ID, or category.")
            st.stop()

        _render_result(doc_record)


# ─────────────────────────────────────────────────────────────────────────
# TAB 2: UPLOAD → FAKE DETECTION
# ─────────────────────────────────────────────────────────────────────────
with tab_upload:
    st.divider()
    st.markdown("""
    <div style='background:rgba(59,130,246,0.10);border:1px solid #3B82F6;
                border-radius:12px;padding:18px;margin-bottom:20px'>
        <b>🕵️ How fake detection works:</b><br>
        <ol style='margin:8px 0 0 0;padding-left:20px;color:#CBD5E1'>
            <li>Upload any document (real, suspected fake, or edited).</li>
            <li>AI pipeline extracts name, ID number, and document type.</li>
            <li>We search the verified ledger for a matching anchored record.</li>
            <li>If <b>no record found</b> → 🚨 <b>FAKE / NOT VERIFIED</b></li>
            <li>If found but <b>fields differ</b> → ⚠️ <b>TAMPERED</b> — shows comparison table</li>
            <li>If found and <b>fields match</b> → ✅ <b>100% AUTHENTIC</b></li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload a document image to check authenticity:",
        type=["jpg", "jpeg", "png"],
        key="fake_detect_uploader"
    )

    if uploaded:
        col_prev, col_info = st.columns([1, 2])
        with col_prev:
            image = Image.open(uploaded).convert("RGB")
            st.image(image, caption="📄 Uploaded Document", use_column_width=True)

        with col_info:
            st.markdown("#### 🤖 AI Analysis")
            with st.spinner("Extracting document fields..."):
                try:
                    result = ml_classifier.analyze_document(image, uploaded.name)
                except Exception as e:
                    st.error(f"AI pipeline error: {e}")
                    st.stop()

            entities    = result.get("entities", {})
            doc_type_up = result.get("document_type", "Document")
            confidence  = result.get("confidence", 0.0)
            ml_used     = result.get("ml_used", False)

            # entities values can be dicts {"value":..., "confidence":...} or plain strings
            def _val(field):
                v = entities.get(field, "")
                return v.get("value", "") if isinstance(v, dict) else (v or "")

            name_up = _val("name")
            id_up   = _val("document_id")

            st.markdown(f"**📂 Detected Type:** `{doc_type_up}` ({confidence:.1f}%)")
            st.markdown(f"**🙍 Name:** `{name_up or '— not detected'}`")
            st.markdown(f"**🆔 ID:** `{id_up or '— not detected'}`")
            st.markdown(f"**🤖 Model:** {'✅ YOLO11 + Donut' if ml_used else '⚙️ Heuristic'}")

        st.divider()

        with st.spinner("🔎 Searching ledger for a matching record..."):
            doc_record = None
            best_ratio = 0.0

            if id_up:
                try:
                    res = db_client.supabase.table("documents").select("*")\
                        .filter("extracted_fields->>document_id", "ilike", f"%{id_up}%")\
                        .execute()
                    if res.data:
                        doc_record = res.data[0]
                        best_ratio = 1.0
                except Exception:
                    pass

            if not doc_record and name_up:
                try:
                    kw = doc_type_up.split()[0] if doc_type_up else ""
                    all_res = db_client.supabase.table("documents").select("*")\
                        .filter("extracted_fields->>doc_type", "ilike", f"%{kw}%")\
                        .execute()
                    for d in (all_res.data or []):
                        sname = (d.get("extracted_fields") or {}).get("name", "")
                        r = difflib.SequenceMatcher(None, name_up.lower(), sname.lower()).ratio()
                        if r > best_ratio:
                            best_ratio = r
                            doc_record = d
                    if best_ratio < 0.55:
                        doc_record = None
                except Exception:
                    pass

        # ── Verdict ──────────────────────────────────────────────────────
        if not doc_record:
            st.markdown("""
            <div style='background:rgba(239,68,68,0.15);border:2px solid #EF4444;
                        border-radius:14px;padding:28px;text-align:center;margin:20px 0'>
                <span style='font-size:48px'>🚨</span>
                <h2 style='color:#EF4444;margin:8px 0'>DOCUMENT NOT VERIFIED — LIKELY FAKE</h2>
                <p style='color:#FECACA;font-size:15px;margin:0'>
                    No matching record found in the TrustLens verified ledger.<br>
                    This document was <b>never anchored</b> or was <b>edited before upload</b>.
                </p>
            </div>""", unsafe_allow_html=True)
            st.markdown("""
**What this means:**
- The name / ID on this document **do not exist** in our verified database.
- Either it was **never registered** in TrustLens, **OR**
- Someone **edited the name / ID / photo** on a real document.
- Do **not** trust this document without verifying with the issuing authority.
            """)
        else:
            stored_ex   = doc_record.get("extracted_fields") or {}
            stored_name = stored_ex.get("name", "")
            stored_id   = stored_ex.get("document_id", "")
            stored_type = stored_ex.get("doc_type", "")

            name_match = difflib.SequenceMatcher(
                None, name_up.lower(), stored_name.lower()).ratio() >= 0.75
            id_match   = (id_up.replace(" ","") == stored_id.replace(" ","")) \
                         if (id_up and stored_id) else True
            type_match = doc_type_up.lower().split()[0] in stored_type.lower() \
                         if doc_type_up else True
            fields_ok  = name_match and id_match

            if fields_ok:
                _render_result(doc_record)
            else:
                st.markdown("""
                <div style='background:rgba(245,158,11,0.15);border:2px solid #F59E0B;
                            border-radius:14px;padding:28px;text-align:center;margin:20px 0'>
                    <span style='font-size:48px'>⚠️</span>
                    <h2 style='color:#F59E0B;margin:8px 0'>TAMPERED / FAKE DOCUMENT DETECTED</h2>
                    <p style='color:#FDE68A;font-size:15px;margin:0'>
                        A record exists but the details <b>do not match</b> the anchored original.
                        This document has been <b>edited</b>.
                    </p>
                </div>""", unsafe_allow_html=True)

                import pandas as pd
                def status(ok): return "✅ Match" if ok else "❌ MISMATCH"
                st.markdown("#### 🔬 Field Comparison: Uploaded vs. Original")
                st.table(pd.DataFrame({
                    "Field":          ["Document Type", "Name",        "Reference ID"],
                    "Uploaded Value": [doc_type_up,     name_up,       id_up or "—"],
                    "Anchored Value": [stored_type,      stored_name,   stored_id or "—"],
                    "Status":         [status(type_match), status(name_match), status(id_match)],
                }))
                st.error("🚨 This document has been **tampered with or forged**.")

                with st.expander("📄 View the original anchored record"):
                    _render_result(doc_record, extra_warning="""
                    <div style='background:rgba(239,68,68,0.1);border:1px solid #EF4444;
                                border-radius:10px;padding:12px;margin-bottom:12px;text-align:center'>
                        <b style='color:#EF4444'>⚠️ ORIGINAL anchored record — uploaded image does NOT match.</b>
                    </div>""")
    else:
        st.markdown("""
        <div style='text-align:center;padding:40px;color:#6B7280'>
            <span style='font-size:56px'>📤</span><br><br>
            <b style='font-size:18px;color:#9CA3AF'>Upload any document above</b><br>
            <span style='font-size:14px'>Supported: JPG, PNG</span><br><br>
            <span style='font-size:13px;color:#4B5563'>
                Real document, suspected fake, or edited image — we'll tell you if it's genuine.
            </span>
        </div>
        """, unsafe_allow_html=True)

st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;"
    f"margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | {APP_VERSION} | Public Verification Portal</div>",
    unsafe_allow_html=True,
)
