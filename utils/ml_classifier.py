# -*- coding: utf-8 -*-
"""
Universal AI Document Intelligence Module
Architecture: Donut (Document Understanding Transformer) via HuggingFace API
Fallback:     Keyword/layout heuristic classifier + Tesseract OCR
Output:       Structured JSON with per-field confidence scores
"""
import io
import re
import time
import logging
import requests
import pytesseract
from PIL import Image
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# ── HuggingFace Endpoints ──────────────────────────────────────────────────────
# Donut: zero-shot document understanding (no OCR needed)
DONUT_API  = "https://api-inference.huggingface.co/models/naver-clova-ix/donut-base-finetuned-docvqa"
# CORD receipt model (good for invoices)
CORD_API   = "https://api-inference.huggingface.co/models/naver-clova-ix/donut-base-finetuned-cord-v2"
# Custom trained model (LayoutLMv3 fine-tuned)
ID_API     = "https://api-inference.huggingface.co/models/hemanthnaidug/my-trustlens-model"

def _get_hf_token() -> str:
    try:
        import streamlit as st
        token = st.secrets.get("HF_TOKEN", "")
        if token and token != "hf_REPLACE_WITH_YOUR_HUGGINGFACE_TOKEN":
            return token
    except Exception:
        pass
    import os
    return os.getenv("HF_TOKEN", "")

def _img_to_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf.read()

def _hf_post(api_url: str, image_bytes: bytes, token: str,
             payload: Optional[Dict] = None, timeout: int = 40) -> Optional[Any]:
    """POST to any HuggingFace Inference API endpoint."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if payload:
            import json
            resp = requests.post(api_url, headers=headers,
                                 data=json.dumps(payload), timeout=timeout)
        else:
            resp = requests.post(api_url, headers=headers,
                                 data=image_bytes, timeout=timeout)

        if resp.status_code == 503:          # Model cold-starting
            logger.info("Model loading, waiting 15s...")
            time.sleep(15)
            resp = requests.post(api_url, headers=headers,
                                 data=image_bytes, timeout=timeout)

        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"HF API {api_url} → {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        logger.error(f"HF POST error: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — ML Classification (Indian IDs: Aadhaar, PAN, Passport, Voter, DL)
# ══════════════════════════════════════════════════════════════════════════════
_ID_MAP = {
    "aadhaar": "Aadhaar Card", "aadhar": "Aadhaar Card",
    "pan":     "PAN Card",     "pan_card": "PAN Card",
    "passport":"Passport",
    "voter":   "Voter ID",     "voter_id":  "Voter ID",
    "driving": "Driving License", "dl": "Driving License",
}

def _classify_indian_id(image_bytes: bytes, token: str) -> Tuple[str, float]:
    result = _hf_post(ID_API, image_bytes, token)
    if result and isinstance(result, list):
        top = result[0]
        raw   = top.get("label", "").lower()
        score = round(top.get("score", 0.0) * 100, 1)
        for k, v in _ID_MAP.items():
            if k in raw:
                return v, score
    return "", 0.0


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — Donut VQA (ask the document direct questions)
# ══════════════════════════════════════════════════════════════════════════════
def _donut_ask(image_bytes: bytes, token: str, question: str) -> Tuple[str, float]:
    """Ask Donut a natural-language question about the document."""
    payload = {"inputs": {"image": image_bytes.hex(), "question": question}}
    # DocVQA API takes image + question as multipart — use raw bytes + param
    headers = {"Authorization": f"Bearer {token}"}
    try:
        files = {"file": ("doc.jpg", image_bytes, "image/jpeg")}
        data  = {"question": question}
        resp  = requests.post(DONUT_API, headers=headers,
                              files=files, data=data, timeout=40)
        if resp.status_code == 503:
            time.sleep(15)
            resp = requests.post(DONUT_API, headers=headers,
                                 files=files, data=data, timeout=40)
        if resp.status_code == 200:
            j = resp.json()
            if isinstance(j, list) and j:
                answer = j[0].get("answer", "")
                score  = round(j[0].get("score", 0.0) * 100, 1)
                return answer, score
    except Exception as e:
        logger.warning(f"Donut VQA error: {e}")
    return "", 0.0


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — Keyword / Layout heuristic fallback (works without API)
# ══════════════════════════════════════════════════════════════════════════════
_KEYWORD_RULES = [
    (["aadhaar", "unique identification", "uidai"],          "Aadhaar Card"),
    (["permanent account number", "income tax department"],  "PAN Card"),
    (["passport", "republic of india", "nationality"],       "Passport"),
    (["election commission", "voter", "epic"],               "Voter ID"),
    (["driving licence", "transport", "motor vehicle"],      "Driving License"),
    (["invoice", "invoice no", "gst", "bill to", "hsn"],     "Invoice / Receipt"),
    (["marksheet", "mark sheet", "examination", "result",
      "grade", "cgpa", "sgpa"],                              "Marksheet / Result"),
    (["bank statement", "account no", "ifsc", "debit",
      "credit", "balance", "transaction"],                   "Bank Statement"),
    (["resume", "curriculum vitae", "objective", "skills",
      "experience", "education", "projects"],                "Resume / CV"),
    (["certificate", "awarded", "completion", "participation",
      "this is to certify"],                                 "Certificate"),
    (["admit card", "hall ticket", "roll number",
      "examination centre"],                                 "Admit Card"),
    (["legal", "affidavit", "notary", "whereby",
      "hereinafter"],                                        "Legal Document"),
    (["identity card", "id card", "reg no", "roll no"],      "Identity Card"),
]

def _keyword_classify(text: str) -> Tuple[str, float]:
    tl = text.lower()
    for keywords, label in _KEYWORD_RULES:
        hits = sum(1 for kw in keywords if kw in tl)
        if hits >= 2:
            conf = min(60 + hits * 8, 88)
            return label, float(conf)
        if hits == 1 and len(keywords) == 1:
            return label, 70.0
    return "Document", 40.0


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — Dynamic NER-style field extraction (doc-type-aware)
# ══════════════════════════════════════════════════════════════════════════════
def _extract_name(text: str) -> Tuple[str, float]:
    patterns = [
        r'(?im)^(?:Name|Student Name|Applicant|Customer|Patient|Employee)'
        r'[^a-zA-Z\n]{0,5}([A-Za-z][A-Za-z\s\.]{2,40})$',
        r'(?i)(?:Name|Surname(?:\s*/\s*Given Name)?)[\s:\-]+([A-Z][A-Za-z\s\.]{2,35})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            val = m.group(1).strip()
            if len(val.split()) >= 2:
                return val.title(), 88.0
    # ALL-CAPS line fallback (Aadhaar style)
    m = re.search(r'\n([A-Z]{2}[A-Z\s]{3,30})\n', text)
    if m:
        skip = {"GOVERNMENT OF INDIA", "INCOME TAX DEPARTMENT",
                "ELECTION COMMISSION", "UNIQUE IDENTIFICATION",
                "REPUBLIC OF INDIA", "NATIONAL INSTITUTE"}
        candidate = m.group(1).strip()
        if candidate not in skip and len(candidate.split()) >= 2:
            return candidate.title(), 75.0
    return "", 0.0

def _extract_id(text: str, doc_type: str) -> Tuple[str, float]:
    dt = doc_type.lower()
    patterns = []
    if "aadhaar" in dt or "aadhar" in dt:
        patterns = [(r'\b(\d{4}\s?\d{4}\s?\d{4})\b', 95.0)]
    elif "pan" in dt:
        patterns = [(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', 97.0)]
    elif "passport" in dt:
        patterns = [(r'\b([A-Z][0-9]{7})\b', 94.0)]
    elif "voter" in dt:
        patterns = [(r'\b([A-Z]{3}[0-9]{7})\b', 92.0)]
    elif "driving" in dt:
        patterns = [(r'\b([A-Z]{2}[0-9]{2}\s?[0-9]{11})\b', 90.0)]
    else:
        patterns = [
            (r'(?i)(?:Roll\s*No|Reg(?:istration)?\s*No|ID\s*No'
             r'|Invoice\s*No|Account\s*No)[^\w\n]{0,5}([A-Za-z0-9\-\/]+)', 78.0),
            (r'(?i)(?:No\.|Number|Roll|ID)[\s:\-]+([A-Za-z0-9\-]{4,20})', 65.0),
        ]
    for pat, conf in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).replace(" ", ""), conf
    return "", 0.0

def _extract_date(text: str) -> Tuple[str, float]:
    m = re.search(
        r'(?i)(?:D\.?O\.?B\.?|Date\s*of\s*Birth|Born|Date|Valid\s*Till)'
        r'[^\d]{0,8}(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})',
        text
    )
    if m:
        return m.group(1), 85.0
    return "", 0.0

def _extract_amount(text: str) -> Tuple[str, float]:
    m = re.search(
        r'(?i)(?:Total|Grand Total|Amount\s*Due|Rs\.?|INR|₹)\s*[:\-]?\s*([\d,]+\.?\d{0,2})',
        text
    )
    if m:
        return m.group(1).strip(), 82.0
    return "", 0.0

def _extract_address(text: str) -> Tuple[str, float]:
    m = re.search(
        r'(?i)(?:Address|Addr\.?)[:\-\s]+([A-Za-z0-9\s,\.\-\/]+(?:\n[A-Za-z0-9\s,\.\-\/]+)?)',
        text
    )
    if m:
        return m.group(1).strip()[:120], 72.0
    return "", 0.0


# ══════════════════════════════════════════════════════════════════════════════
# MASTER PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def analyze_document(image: Image.Image, filename: str = "") -> Dict[str, Any]:
    """
    Universal Document Intelligence Pipeline.

    Returns:
    {
      "document_type": "Aadhaar Card",
      "confidence":    96.3,
      "ml_used":       True,
      "entities": {
        "name":        {"value": "Hemanth Naidu",  "confidence": 88.0},
        "document_id": {"value": "225300234512",   "confidence": 95.0},
        "date":        {"value": "05-05-2005",      "confidence": 85.0},
        "amount":      {"value": "",               "confidence": 0.0},
        "address":     {"value": "",               "confidence": 0.0},
      }
    }
    """
    result: Dict[str, Any] = {
        "document_type": "Document",
        "confidence":    0.0,
        "ml_used":       False,
        "entities":      {
            "name":        {"value": "", "confidence": 0.0},
            "document_id": {"value": "", "confidence": 0.0},
            "date":        {"value": "", "confidence": 0.0},
            "amount":      {"value": "", "confidence": 0.0},
            "address":     {"value": "", "confidence": 0.0},
        }
    }

    token       = _get_hf_token()
    image_bytes = _img_to_bytes(image)

    # ── Stage 1: ML classification (Indian IDs) ────────────────────────────
    if token:
        ml_type, ml_conf = _classify_indian_id(image_bytes, token)
        if ml_type and ml_conf >= 50.0:
            result["document_type"] = ml_type
            result["confidence"]    = ml_conf
            result["ml_used"]       = True

    # ── Stage 2: OCR (always run) ──────────────────────────────────────────
    try:
        raw_text = pytesseract.image_to_string(image)
    except Exception:
        raw_text = ""

    # ── Stage 3: Keyword fallback if ML didn't fire ────────────────────────
    if not result["ml_used"] and raw_text.strip():
        kw_type, kw_conf = _keyword_classify(raw_text)
        result["document_type"] = kw_type
        result["confidence"]    = kw_conf

    # ── Stage 4: Donut VQA for name (if ML is available) ──────────────────
    name_val, name_conf = "", 0.0
    if token:
        name_val, name_conf = _donut_ask(image_bytes, token, "What is the name of the person?")
    if not name_val:
        name_val, name_conf = _extract_name(raw_text)

    # ── Stage 5: Dynamic entity extraction ────────────────────────────────
    id_val,   id_conf   = _extract_id(raw_text, result["document_type"])
    date_val, date_conf = _extract_date(raw_text)
    amt_val,  amt_conf  = _extract_amount(raw_text)
    addr_val, addr_conf = _extract_address(raw_text)

    # ── Stage 6: Fallbacks ─────────────────────────────────────────────────
    if not name_val and filename:
        name_val  = filename.split(".")[0].replace("_", " ").title()
        name_conf = 30.0
    if not id_val:
        id_val    = "TRU-" + str(int(time.time()))[-6:]
        id_conf   = 0.0

    # ── Assemble output ────────────────────────────────────────────────────
    result["entities"] = {
        "name":        {"value": name_val,  "confidence": name_conf},
        "document_id": {"value": id_val,    "confidence": id_conf},
        "date":        {"value": date_val,  "confidence": date_conf},
        "amount":      {"value": amt_val,   "confidence": amt_conf},
        "address":     {"value": addr_val,  "confidence": addr_conf},
    }

    return result


def flatten_for_db(result: Dict[str, Any], manual_override: str = "") -> Dict[str, Any]:
    """
    Converts the rich result dict into a flat dict for DB storage.
    """
    e = result.get("entities", {})
    return {
        "doc_type":    manual_override if manual_override else result.get("document_type", "Document"),
        "name":        e.get("name",        {}).get("value", ""),
        "document_id": e.get("document_id", {}).get("value", ""),
        "date":        e.get("date",        {}).get("value", ""),
        "amount":      e.get("amount",      {}).get("value", ""),
        "address":     e.get("address",     {}).get("value", ""),
        "ml_confidence": result.get("confidence", 0.0),
        "ml_used":       result.get("ml_used", False),
    }
