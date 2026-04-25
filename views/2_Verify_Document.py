# -*- coding: utf-8 -*-
import streamlit as st
import graphviz
from components.certificate import generate_pdf_certificate
from utils import crypto_signer, hashing, db_client
from models.document import DocumentModel
from config import APP_VERSION, APP_NAME, GITHUB_URL, SUPPORT_EMAIL

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:#3B82F6;margin-bottom:0'>🛡️ {APP_NAME}</h2>", unsafe_allow_html=True)
    if st.session_state.get("user"):
        st.markdown(f"**👤** `{st.session_state.user.email}`")
        if st.button("📊 Go to My Vault", use_container_width=True):
            st.switch_page("views/3_Trust_Analytics.py")
        if st.button("📤 Upload Document", use_container_width=True):
            st.switch_page("views/1_Upload_Document.py")
    else:
        st.info("🌍 Public verification — no login needed.")
    st.divider()
    st.caption(f"{APP_VERSION}")

# ── Page Content ────────────────────────────────────────────────────────────────
st.title("🔍 Universal Document Verification")

st.markdown("""
<div style='background:rgba(59,130,246,0.08);border:1px solid #3B82F6;border-radius:10px;padding:14px;margin-bottom:16px'>
<strong>Search by ANY of the following:</strong><br>
📌 <b>Ledger ID</b> (the full UUID) &nbsp;|&nbsp;
🙍 <b>Person's Name</b> (e.g. <i>Hemanth Naidu</i>) &nbsp;|&nbsp;
🆔 <b>Ref ID / Roll No</b> (e.g. <i>2253002</i>) &nbsp;|&nbsp;
📂 <b>Category</b> (e.g. <i>Aadhaar Card</i>) &nbsp;|&nbsp;
🔗 <b>Image URL</b>
</div>
""", unsafe_allow_html=True)

search_query = st.text_input(
    "Enter any detail to search:",
    placeholder="Try: Hemanth Naidu   OR   2253002   OR   COLLEGE ID CARD ...",
    key="universal_search"
)

if st.button("🔍 Verify Now", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("Please enter a search term.")
        st.stop()

    with st.spinner("🔎 Searching the immutable Trust Chain ledger..."):
        doc_record = None
        search_term = search_query.strip()

        # Step 1: Direct UUID match
        try:
            if len(search_term) >= 32:
                doc_record = db_client.get_document_by_id(search_term)
        except Exception:
            pass

        # Step 2: Exact DB search across all extracted fields
        if not doc_record:
            try:
                res = db_client.supabase.table("documents").select("*").or_(
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

        # Step 3: Fuzzy search fallback (find closest match)
        if not doc_record:
            try:
                import difflib
                all_docs = db_client.supabase.table("documents").select("*").execute()
                best_ratio = 0.0
                best_doc   = None
                for d in (all_docs.data or []):
                    ex = d.get("extracted_fields") or {}
                    candidates = [
                        ex.get("name", ""),
                        ex.get("document_id", ""),
                        ex.get("doc_type", ""),
                    ]
                    for cand in candidates:
                        if not cand: continue
                        ratio = difflib.SequenceMatcher(
                            None, search_term.lower(), cand.lower()
                        ).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_doc   = d
                if best_ratio >= 0.6:
                    doc_record = best_doc
                    st.info(f"🔍 Fuzzy match found (similarity: {best_ratio*100:.0f}%)")
            except Exception:
                pass

    # ── RESULT DISPLAY ─────────────────────────────────────────────────────────
    if not doc_record:
        st.error("❌ No matching document found. Try a different name, ID, or category.")
        st.stop()

    # Build model
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

    # Cryptographic checks
    recalc_hash = hashing.create_hash(doc_model.extracted_fields)
    hash_valid = (recalc_hash == doc_model.content_hash)
    sig_valid = crypto_signer.verify_signature(recalc_hash, doc_model.digital_signature, doc_model.did_public_key)
    fully_valid = hash_valid and sig_valid

    # ── Trust Score Badge ──────────────────────────────────────────────────────
    if fully_valid:
        st.markdown("""
        <div style='background:rgba(16,185,129,0.12);border:2px solid #10B981;border-radius:14px;padding:22px;text-align:center;margin-bottom:20px'>
            <span style='font-size:40px'>🛡️</span>
            <h2 style='color:#10B981;margin:4px 0'>100% AUTHENTIC</h2>
            <p style='color:#A7F3D0;margin:0;font-size:14px'>Cryptographic integrity verified. This document has not been tampered with.</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:rgba(239,68,68,0.12);border:2px solid #EF4444;border-radius:14px;padding:22px;text-align:center;margin-bottom:20px'>
            <span style='font-size:40px'>⚠️</span>
            <h2 style='color:#EF4444;margin:4px 0'>TAMPER DETECTED</h2>
            <p style='color:#FECACA;margin:0;font-size:14px'>This document fails cryptographic verification. It may have been modified.</p>
        </div>""", unsafe_allow_html=True)

    # ── Main Layout ────────────────────────────────────────────────────────────
    c1, c2 = st.columns([1.2, 2])

    with c1:
        st.image(doc_model.image_url, use_column_width=True, caption="📎 Original Anchored Document")
        st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

        # All Document Details
        st.markdown("#### 📋 Document Information")
        fields = [
            ("📂 Category",    ex.get("doc_type", "—")),
            ("🙍 Name",        ex.get("name", "—")),
            ("🆔 Ref ID",      ex.get("document_id", "—")),
            ("📅 Date / DOB",  ex.get("date", "—")),
            ("💰 Amount",      ex.get("amount", "—")),
            ("🗓️ Anchored On", doc_model.created_at[:10] if doc_model.created_at else "—"),
        ]
        for label, value in fields:
            if value and value != "—":
                st.markdown(f"**{label}:** `{value}`")

        st.markdown(f"**🔗 Ledger ID:** `{doc_model.id[:16]}...`")

    with c2:
        st.markdown("### 🔬 Trust Chain Provenance")

        # Interactive Trust Graph
        graph = graphviz.Digraph(engine="dot")
        graph.attr(rankdir="LR", bgcolor="transparent", size="7,2.5")
        node_style = dict(style="filled", fontcolor="white", fontsize="11")
        graph.node("A", "Physical\nDocument",  shape="note",     color="#3B82F6", **node_style)
        graph.node("B", "AI OCR\nExtraction",  shape="box",      color="#10B981", **node_style)
        graph.node("C", "SHA-256\nHash",        shape="box",      color="#8B5CF6", **node_style)
        graph.node("D", "ECDSA\nSignature",     shape="box",      color="#F59E0B", **node_style)
        graph.node("E", "Immutable\nLedger",    shape="cylinder", color="#EF4444", **node_style)
        graph.edges(["AB", "BC", "CD", "DE"])
        st.graphviz_chart(graph)

        # Progressive disclosure tabs
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
            st.markdown(f"- 🟢 **Document Uploaded & Anchored:** `{doc_record.get('created_at','—')[:19]} UTC`")
            st.markdown(f"- 🔵 **Public Verification:** Live (right now)")
            st.markdown(f"- 🔗 **Full Ledger ID:** `{doc_model.id}`")

    # ── Certificate Download ───────────────────────────────────────────────────
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

st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:12px;margin-top:40px;border-top:1px solid #2d3748;padding-top:16px'>"
    f"© 2026 {APP_NAME} | {APP_VERSION} | Public Verification Portal</div>",
    unsafe_allow_html=True,
)
