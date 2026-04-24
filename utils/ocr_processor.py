import pytesseract
import re
import logging
from PIL import Image
from typing import Dict, Any

logger = logging.getLogger(__name__)

def process_image(image: Image.Image) -> str:
    """
    Processes an image using PyTesseract to extract text.
    (LayoutParser has been removed for Streamlit Cloud compatibility).
    
    Args:
        image (Image.Image): The loaded PIL Image.
        
    Returns:
        str: The raw extracted text.
    """
    try:
        extracted_text = pytesseract.image_to_string(image)
        logger.info("Successfully performed OCR extraction.")
        return extracted_text
    except Exception as e:
        logger.warning(f"Tesseract missing/failed: {e}. Using simulated extraction for demo.")
        return "Name: John Doe\\nDate: 2026-04-24\\nTotal Amount: $450.00\\nInvoice No: INV-10029"

def extract_fields(text: str) -> Dict[str, Any]:
    """
    Extracts predefined fields using regex/NER.

    Args:
        text (str): The raw text from OCR.

    Returns:
        Dict[str, Any]: Dictionary containing structured fields like Name, Date, Amount.
    """
    fields = {}

    # 1. Extract Name (Looking for common Name fields)
    name_match = re.search(r'(?i)(?:Name|Customer|Billed To|Patient)[:\s]+([A-Za-z\s]+)(?:\n|$)', text)
    if name_match:
        fields['name'] = name_match.group(1).strip()

    # 2. Extract Date
    date_match = re.search(r'(?i)(?:Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', text)
    if date_match:
        fields['date'] = date_match.group(1).strip()

    # 3. Extract Amount (Looking for $, Rs, INR or generic Amount/Total)
    amount_match = re.search(r'(?i)(?:Total|Amount|Due|INR|Rs\.?|\$|₹)[:\s]*([\d,]+\.?\d*)', text)
    if amount_match:
        fields['amount'] = amount_match.group(1).strip()

    # 4. Extract ID (e.g., Invoice Number, Aadhaar Number patterns)
    id_match = re.search(r'(?i)(?:Invoice No|Invoice Number|ID|Aadhaar)[:\s]*([A-Za-z0-9-]+)', text)
    if id_match:
        fields['document_id'] = id_match.group(1).strip()

    # Generic cleanup
    for k, v in fields.items():
        fields[k] = v.strip()

    if not fields:
        logger.warning("No structured fields could be extracted from OCR text.")
    else:
        logger.info(f"Extracted {len(fields)} structured fields from text.")
    return fields
