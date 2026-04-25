# -*- coding: utf-8 -*-
"""
ML Document Intelligence Module
Uses HuggingFace Inference API for Indian document classification.
Falls back to Tesseract OCR if API is unavailable.
"""
import io
import re
import base64
import logging
import requests
import pytesseract
from PIL import Image
from typing import Dict, Any, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

# ── HuggingFace API Config ─────────────────────────────────────────────────────
HF_API_URL = "https://api-inference.huggingface.co/models/logasanjeev/indian-id-validator"

def _get_hf_token():
    try:
        return st.secrets.get("HF_TOKEN", "")
    except:
        import os
        return os.getenv("HF_TOKEN", "")

# ── Document type label map ────────────────────────────────────────────────────
DOC_LABEL_MAP = {
    "aadhaar":        "Aadhaar Card",
    "aadhar":         "Aadhaar Card",
    "pan":            "PAN Card",
    "pan_card":       "PAN Card",
    "passport":       "Passport",
    "voter":          "Voter ID",
    "voter_id":       "Voter ID",
    "driving":        "Driving License",
    "dl":             "Driving License",
    "driving_license":"Driving License",
}

def _normalize_label(raw: str) -> str:
    key = raw.lower().strip().replace(" ", "_")
    for k, v in DOC_LABEL_MAP.items():
        if k in key:
            return v
    return raw.title()

# ── Step 1: Classify document type via HuggingFace API ────────────────────────
def classify_document(image: Image.Image) -> Tuple[str, float]:
    """
    Calls the HuggingFace image-classification API.
    Returns (doc_type_label, confidence_score).
    Falls back to 'Unknown' if API fails.
    """
    token = _get_hf_token()
    if not token:
        logger.warning("No HF_TOKEN found. Skipping ML classification.")
        return "Unknown", 0.0

    try:
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            HF_API_URL,
            headers=headers,
            data=buf.read(),
            timeout=30
        )

        if response.status_code == 503:
            # Model loading — wait and retry once
            logger.info("HuggingFace model loading, retrying in 10s...")
            import time; time.sleep(10)
            buf.seek(0)
            response = requests.post(HF_API_URL, headers=headers, data=buf.read(), timeout=30)

        if response.status_code == 200:
            results = response.json()
            if isinstance(results, list) and len(results) > 0:
                top = results[0]
                label = _normalize_label(top.get("label", "Unknown"))
                score = round(top.get("score", 0.0) * 100, 1)
                logger.info(f"ML Classification: {label} ({score}%)")
                return label, score

        logger.warning(f"HF API error {response.status_code}: {response.text[:200]}")
        return "Unknown", 0.0

    except Exception as e:
        logger.error(f"ML classify error: {e}")
        return "Unknown", 0.0

# ── Step 2: Tesseract OCR ──────────────────────────────────────────────────────
def process_image(image: Image.Image) -> str:
    """Extracts raw text using Tesseract OCR."""
    try:
        return pytesseract.image_to_string(image)
    except Exception as e:
        logger.warning(f"OCR Failed: {e}")
        return ""

# ── Step 3: Smart field extraction ────────────────────────────────────────────
def extract_fields(text: str, doc_type: str = "") -> Dict[str, Any]:
    """
    Extracts structured fields from OCR text.
    doc_type helps select the right patterns (Aadhaar vs PAN etc).
    """
    fields = {}
    if not text.strip():
        return fields

    dt = doc_type.lower()

    # ── Name ─────────────────────────────────────────────────────────────────
    # Priority 1: Specific label before name
    name_match = re.search(
        r'(?im)^(?:Name|Student Name|Customer|Patient|Employee|Applicant)[^a-zA-Z\n]+([A-Za-z][\w\s\.]{2,40})$',
        text
    )
    if name_match:
        fields["name"] = name_match.group(1).strip()
    else:
        # Priority 2: ALL CAPS name line (common on Aadhaar)
        caps_match = re.search(r'\n([A-Z][A-Z\s]{3,30})\n', text)
        if caps_match:
            candidate = caps_match.group(1).strip()
            # Filter out known non-name all-caps words
            skip = {"GOVERNMENT", "INDIA", "IDENTITY", "CARD", "DEPARTMENT", "AUTHORITY"}
            if candidate not in skip and len(candidate.split()) >= 2:
                fields["name"] = candidate.title()

    # ── Document-specific ID extraction ──────────────────────────────────────
    if "aadhaar" in dt or "aadhar" in dt:
        # Aadhaar: 12-digit number (often formatted as 4-4-4)
        m = re.search(r'\b(\d{4}\s?\d{4}\s?\d{4})\b', text)
        if m:
            fields["document_id"] = m.group(1).replace(" ", "")

    elif "pan" in dt:
        # PAN: 5 letters + 4 digits + 1 letter
        m = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
        if m:
            fields["document_id"] = m.group(1)

    elif "passport" in dt:
        # Passport: Letter + 7 digits
        m = re.search(r'\b([A-Z][0-9]{7})\b', text)
        if m:
            fields["document_id"] = m.group(1)

    elif "voter" in dt:
        m = re.search(r'\b([A-Z]{3}[0-9]{7})\b', text)
        if m:
            fields["document_id"] = m.group(1)

    else:
        # Generic: Roll No, Reg No, ID No, Invoice No
        id_patterns = [
            r'(?i)(?:Roll\s*No|Reg(?:istration)?\s*No|ID\s*No|Invoice\s*No)[^\w\n]*([A-Za-z0-9\-]+)',
            r'(?i)(?:No\.|Number|Roll|ID)[\s:\-]+([A-Za-z0-9\-]{4,15})',
        ]
        for p in id_patterns:
            m = re.search(p, text)
            if m:
                fields["document_id"] = m.group(1).strip()
                break

    # ── DOB ──────────────────────────────────────────────────────────────────
    dob_match = re.search(
        r'(?i)(?:D\.?O\.?B\.?|Date\s*of\s*Birth|Born)[^\d]*(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})',
        text
    )
    if dob_match:
        fields["date"] = dob_match.group(1).strip()

    # ── Amount (for invoices/receipts) ────────────────────────────────────────
    amount_match = re.search(
        r'(?i)(?:Total|Amount|Due|Balance|Rs\.?|INR|₹)\s*[:\-]?\s*([\d,]+\.?\d{0,2})',
        text
    )
    if amount_match:
        fields["amount"] = amount_match.group(1).strip()

    # ── Cleanup ──────────────────────────────────────────────────────────────
    garbage = {"ENTITY", "U", "THE", "AND", "TOTAL", "OF", "IN", "IS"}
    cleaned = {}
    for k, v in fields.items():
        if isinstance(v, str) and v.upper().strip() not in garbage and len(v.strip()) > 1:
            cleaned[k] = v.strip()
    return cleaned


# ── Master function: Full ML + OCR Pipeline ───────────────────────────────────
def analyze_document(image: Image.Image, filename: str = "") -> Dict[str, Any]:
    """
    Full pipeline:
    1. Classify document type via ML API
    2. Run OCR
    3. Extract fields using doc-type-aware patterns
    Returns a result dict with all metadata including confidence.
    """
    result = {
        "doc_type":   "Unknown",
        "confidence": 0.0,
        "name":       "",
        "document_id":"",
        "date":       "",
        "amount":     "",
        "ml_used":    False,
    }

    # Step 1: ML Classification
    doc_type, confidence = classify_document(image)
    if doc_type != "Unknown" and confidence > 30.0:
        result["doc_type"]   = doc_type
        result["confidence"] = confidence
        result["ml_used"]    = True
    else:
        result["doc_type"] = "Document"

    # Step 2: OCR
    raw_text = process_image(image)

    # Step 3: Smart field extraction
    extracted = extract_fields(raw_text, result["doc_type"])

    # Step 4: Merge
    result["name"]        = extracted.get("name", "")
    result["document_id"] = extracted.get("document_id", "")
    result["date"]        = extracted.get("date", "")
    result["amount"]      = extracted.get("amount", "")

    # Step 5: Fallback for name
    if not result["name"] and filename:
        result["name"] = filename.split(".")[0].replace("_", " ").title()

    # Step 6: Fallback for ID
    if not result["document_id"]:
        import time
        result["document_id"] = "TRU-" + str(int(time.time()))[-6:]

    return result
