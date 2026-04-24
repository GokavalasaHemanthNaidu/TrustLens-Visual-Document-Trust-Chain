# -*- coding: utf-8 -*-
import pytesseract
import re
import logging
from PIL import Image
from typing import Dict, Any

logger = logging.getLogger(__name__)

def process_image(image: Image.Image) -> str:
    """Extracts raw text using Tesseract."""
    try:
        extracted_text = pytesseract.image_to_string(image)
        return extracted_text
    except Exception as e:
        logger.warning(f"OCR Failed: {e}")
        return ""

def extract_fields(text: str) -> Dict[str, Any]:
    """Smarter field extraction with more patterns."""
    fields = {}
    if not text.strip():
        return fields

    # 1. Name Patterns (Extended)
    name_patterns = [
        r'(?i)(?:Name|Customer|Bill To|Billed To|Patient|User|Employee)[:\s]+([A-Za-z\s]+)(?:\n|$)',
        r'(?i)^([A-Z][a-z]+ [A-Z][a-z]+)' # Matches "John Doe" at the start of a line
    ]
    for p in name_patterns:
        m = re.search(p, text)
        if m:
            fields['name'] = m.group(1).strip()
            break

    # 2. Amount Patterns
    amount_patterns = [
        r'(?i)(?:Total|Amount|Due|Balance|Price|INR|Rs\.?|\$|₹)[:\s]*([\d,]+\.?\d*)',
        r'([\d,]+\.\d{2})' # Matches any decimal like 450.00
    ]
    for p in amount_patterns:
        m = re.search(p, text)
        if m:
            fields['amount'] = m.group(1).strip()
            break

    # 3. ID Patterns
    id_patterns = [
        r'(?i)(?:Invoice No|ID|Aadhaar|Reg|No\.?|Number|Roll|PAN|Voter|License)[\s\:\-]+([A-Za-z0-9-]+)',
        r'(?i)\b(?:ID)\s*([A-Za-z0-9-]+)\b'
    ]
    for p in id_patterns:
        m = re.search(p, text)
        if m:
            fields['document_id'] = m.group(1).strip()
            break

    # 4. Date Patterns
    date_match = re.search(r'(?i)(?:Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', text)
    if date_match:
        fields['date'] = date_match.group(1).strip()

    # Final cleanup: Remove garbage words like 'ENTITY' or 'U'
    garbage = ["ENTITY", "U", "THE", "AND", "TOTAL"]
    for k, v in fields.items():
        if v.upper() in garbage:
            fields[k] = ""
            
    return {k: v for k, v in fields.items() if v}
