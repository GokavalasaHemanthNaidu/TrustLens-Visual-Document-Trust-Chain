# -*- coding: utf-8 -*-
"""
ocr_processor.py — Multi-language OCR engine
Primary:  EasyOCR  (English + Hindi + Telugu + Tamil + Kannada)
Fallback: Tesseract (English only, if EasyOCR unavailable)
"""
import re
import logging
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Language sets ──────────────────────────────────────────────────────────────
# EasyOCR language codes
_LANG_SETS = {
    "english":  ["en"],
    "hindi":    ["en", "hi"],
    "telugu":   ["en", "te"],
    "tamil":    ["en", "ta"],
    "kannada":  ["en", "kn"],
    "auto":     ["en", "hi", "te", "ta"],   # detect all Indian scripts
}

# Cached EasyOCR readers (expensive to init — cache per language set)
_readers: Dict[str, Any] = {}

def _get_reader(lang_key: str = "auto"):
    """Return a cached EasyOCR reader for the given language set."""
    if lang_key not in _readers:
        try:
            import easyocr
            langs = _LANG_SETS.get(lang_key, ["en", "hi", "te", "ta"])
            logger.info(f"Initialising EasyOCR for languages: {langs}")
            _readers[lang_key] = easyocr.Reader(langs, gpu=False, verbose=False)
        except Exception as e:
            logger.warning(f"EasyOCR init failed ({e}) — will use Tesseract fallback")
            _readers[lang_key] = None
    return _readers[lang_key]


def _detect_script(image: Image.Image) -> str:
    """
    Lightweight heuristic: scan pixel patterns to guess script family.
    Returns a lang_key for _get_reader().
    In practice, running 'auto' (all 4 scripts) is safe and only ~0.5s slower.
    """
    # For now always return 'auto' — covers all Indian scripts
    return "auto"


def _preprocess(image: Image.Image) -> Image.Image:
    """Standardise image for OCR: greyscale → sharpen → contrast boost."""
    img = image.convert("L")                          # greyscale
    img = img.filter(ImageFilter.SHARPEN)             # sharpening kernel
    img = ImageEnhance.Contrast(img).enhance(2.0)    # 2× contrast
    return img


# ── Primary: EasyOCR ──────────────────────────────────────────────────────────
def _easyocr_extract(image: Image.Image) -> str:
    """Run EasyOCR and return concatenated text."""
    lang_key = _detect_script(image)
    reader   = _get_reader(lang_key)
    if reader is None:
        return ""
    try:
        processed = _preprocess(image)
        img_array = np.array(processed)
        results   = reader.readtext(img_array, detail=1, paragraph=False)
        # Sort results top-to-bottom (by y-coordinate of bounding box)
        results.sort(key=lambda r: r[0][0][1])   # r[0] = bbox, [0][1] = top-left y
        lines = [r[1] for r in results if r[2] >= 0.1]   # filter conf < 10%
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"EasyOCR extraction failed: {e}")
        return ""


# ── Fallback: Tesseract ───────────────────────────────────────────────────────
def _tesseract_extract(image: Image.Image) -> str:
    """Fallback OCR using Tesseract (English only)."""
    try:
        import pytesseract
        processed = _preprocess(image)
        return pytesseract.image_to_string(processed, config="--oem 3 --psm 3")
    except Exception as e:
        logger.warning(f"Tesseract fallback also failed: {e}")
        return ""


# ── Public API ────────────────────────────────────────────────────────────────
def process_image(image: Image.Image) -> str:
    """
    Extract text from a document image.
    Tries EasyOCR first (multi-language), falls back to Tesseract.
    Returns a single string of extracted text.
    """
    text = _easyocr_extract(image)
    if not text.strip():
        logger.info("EasyOCR returned empty — trying Tesseract fallback")
        text = _tesseract_extract(image)
    return text


def detect_language(text: str) -> str:
    """
    Detect the primary script in extracted text.
    Returns: 'hindi' | 'telugu' | 'tamil' | 'kannada' | 'english'
    """
    if not text:
        return "english"
    # Unicode block ranges
    devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097F")   # Hindi
    telugu     = sum(1 for c in text if "\u0C00" <= c <= "\u0C7F")   # Telugu
    tamil      = sum(1 for c in text if "\u0B80" <= c <= "\u0BFF")   # Tamil
    kannada    = sum(1 for c in text if "\u0C80" <= c <= "\u0CFF")   # Kannada

    scores = {"hindi": devanagari, "telugu": telugu,
              "tamil": tamil, "kannada": kannada}
    best   = max(scores, key=scores.get)
    return best if scores[best] > 3 else "english"


# ── Field extraction (unchanged from original) ────────────────────────────────
def extract_fields(text: str) -> Dict[str, Any]:
    """Extract structured fields from raw OCR text."""
    fields = {}
    if not text.strip():
        return fields

    # 1. Name patterns
    name_patterns = [
        r"(?im)^(?:Name|Student Name|Customer|Patient|User|Employee)[^\w\n]+([A-Za-z\s\.]+)(?:\n|$)",
        r"(?i)(?:Name|Customer|Bill To|Billed To)[:\-\s]+([A-Za-z\s\.]+)(?:\n|$)",
        r"(?i)^([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    for p in name_patterns:
        m = re.search(p, text)
        if m:
            fields["name"] = m.group(1).strip()
            break

    # 2. Amount patterns
    amount_patterns = [
        r"(?i)(?:Total|Amount|Due|Balance|Price|INR|Rs\.?|\$|₹)[:\s]*([\d,]+\.?\d*)",
        r"([\d,]+\.\d{2})",
    ]
    for p in amount_patterns:
        m = re.search(p, text)
        if m:
            fields["amount"] = m.group(1).strip()
            break

    # 3. ID patterns
    id_patterns = [
        r"(?i)(?:Roll\s*No|Invoice\s*No|ID\s*No|Reg\s*No|Aadhaar|PAN|Voter|License)[^\w\n]*([A-Za-z0-9-]+)",
        r"(?i)(?:ID|No\.?|Number|Roll)[\s:\-]+([A-Za-z0-9-]+)",
    ]
    for p in id_patterns:
        m = re.search(p, text)
        if m:
            fields["document_id"] = m.group(1).strip()
            break

    # 4. Date patterns
    date_match = re.search(
        r"(?i)(?:Date|D\.?O\.?B\.?)[^\w\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        text,
    )
    if date_match:
        fields["date"] = date_match.group(1).strip()

    # Cleanup garbage tokens
    garbage = {"ENTITY", "U", "THE", "AND", "TOTAL"}
    for k, v in fields.items():
        if v.upper() in garbage:
            fields[k] = ""

    return {k: v for k, v in fields.items() if v}
