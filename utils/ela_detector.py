# -*- coding: utf-8 -*-
"""
utils/ela_detector.py — Forgery and Deepfake Detection Suite
Performs Error Level Analysis (ELA) and EXIF metadata auditing to identify
tampered, double-compressed, edited, or AI-synthesized documents.
"""
import io
import logging
import numpy as np
from PIL import Image, ImageChops
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)

# Try to import cv2 for premium color heatmap mapping
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV is not available — falling back to standard RGB ELA visualization.")


def calculate_ela(image: Image.Image, quality: int = 90, scale: int = 15) -> Tuple[Image.Image, float, Image.Image]:
    """
    Perform Error Level Analysis (ELA) on an image.
    Saves the image at a known lossy compression quality, computes the difference,
    and returns:
      1. Enhanced grayscale/RGB difference image
      2. The mean error level (indicates compression discrepancy/tampering)
      3. A premium pseudo-color heatmap (hot/inferno style) showing anomalies
    """
    # 1. Standardize image to RGB
    orig = image.convert("RGB")
    
    # 2. Resave image at a specific quality in memory
    buf = io.BytesIO()
    orig.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    resaved = Image.open(buf)
    resaved.load()  # Force load
    
    # 3. Calculate absolute difference
    diff = ImageChops.difference(orig, resaved)
    
    # Calculate statistics on the raw difference
    diff_arr = np.array(diff)
    mean_error = float(np.mean(diff_arr))
    
    # 4. Enhance difference for visualization (scale pixel values)
    enhanced = ImageChops.multiply(diff, Image.new("RGB", diff.size, (scale, scale, scale)))
    
    # 5. Generate a premium pseudo-color heatmap
    heatmap = None
    if OPENCV_AVAILABLE:
        try:
            # Convert to grayscale array
            gray_diff = np.array(enhanced.convert("L"))
            # Apply COLORMAP_HOT or COLORMAP_JET for high-contrast thermal-like heatmap
            # Jet color map makes edits stand out brilliantly
            color_mapped = cv2.applyColorMap(gray_diff, cv2.COLORMAP_HOT)
            # OpenCV is BGR, convert to RGB for PIL
            color_mapped_rgb = cv2.cvtColor(color_mapped, cv2.COLOR_BGR2RGB)
            heatmap = Image.fromarray(color_mapped_rgb)
        except Exception as e:
            logger.warning(f"Failed to generate cv2 color heatmap: {e}")
            
    if heatmap is None:
        # Fallback to standard RGB ELA representation (looks decent, but not as premium)
        heatmap = enhanced
        
    return enhanced, mean_error, heatmap


def audit_metadata(image: Image.Image) -> Dict[str, Any]:
    """
    Audits EXIF metadata to detect capture hardware, editing softwares,
    and missing metadata profiles typical of downloaded or AI-generated fakes.
    """
    audit = {
        "has_exif": False,
        "device_make": "",
        "device_model": "",
        "software": "",
        "capture_date": "",
        "is_stripped": True,
        "warnings": []
    }
    
    try:
        from PIL.ExifTags import TAGS
        exif = image._getexif()
        if exif:
            audit["has_exif"] = True
            audit["is_stripped"] = False
            
            # Map tag IDs to human-readable labels
            exif_data = {}
            for tag, val in exif.items():
                decoded = TAGS.get(tag, tag)
                exif_data[decoded] = val
                
            audit["device_make"] = str(exif_data.get("Make", "")).strip()
            audit["device_model"] = str(exif_data.get("Model", "")).strip()
            audit["software"] = str(exif_data.get("Software", "")).strip()
            audit["capture_date"] = str(exif_data.get("DateTimeOriginal", "")) or str(exif_data.get("DateTime", ""))
            
            # Check for known editing tools in the software field
            soft = audit["software"].lower()
            known_editors = ["photoshop", "gimp", "canva", "picsart", "snapseed", "lightroom", "pixlr", "fotor", "acorn"]
            for editor in known_editors:
                if editor in soft:
                    audit["warnings"].append(f"Document edited using '{audit['software']}'")
                    
            if not audit["device_make"] and not audit["device_model"]:
                audit["warnings"].append("No camera hardware info found in EXIF.")
        else:
            audit["warnings"].append("EXIF metadata is completely missing/stripped.")
    except Exception as e:
        logger.warning(f"Error reading EXIF metadata: {e}")
        audit["warnings"].append("Metadata could not be parsed.")
        
    return audit


def assess_forgery_risk(mean_error: float, metadata: Dict[str, Any], filename: str = "") -> Dict[str, Any]:
    """
    Computes a Forgery Risk Index using a fuzzy logic combination of
    ELA mean error density and Metadata auditing findings.
    
    Returns a dictionary:
    {
      "risk_level": "LOW" | "MEDIUM" | "HIGH",
      "risk_score": 0.0 - 100.0,
      "details": ["warning 1", "warning 2", ...]
    }
    """
    score = 10.0  # Base line risk score (10%)
    details = []
    
    # 1. ELA Mean Error Assessment
    # Unmodified pictures: usually 0.5 - 5.0
    # Edited JPEGs: elevated to 10.0 - 45.0 because of inconsistent high-frequency edges
    if mean_error > 25.0:
        score += 45.0
        details.append(f"Critically high compression mismatch (ELA Index: {mean_error:.1f})")
    elif mean_error > 12.0:
        score += 25.0
        details.append(f"Elevated compression error level (ELA Index: {mean_error:.1f})")
    elif mean_error > 6.0:
        score += 10.0
        details.append(f"Mild compression variance (ELA Index: {mean_error:.1f})")
    else:
        details.append(f"Clean compression profile (ELA Index: {mean_error:.1f})")

    # 2. Metadata Audit Assessment
    if metadata["software"]:
        score += 40.0
        details.append(f"Explicit editing software signature found: {metadata['software']}")
    elif metadata["is_stripped"]:
        score += 15.0
        # If it's a screenshot or web-saved doc, EXIF is stripped
        details.append("Image is stripped of standard camera metadata (EXIF).")
    else:
        # Has EXIF
        if metadata["device_make"] or metadata["device_model"]:
            score -= 10.0  # Reward legitimate capture evidence
            details.append(f"Captured via camera: {metadata['device_make']} {metadata['device_model']}")
            
    # 3. Check filename indicators (e.g. screenshot, edit)
    fn = filename.lower()
    if any(k in fn for k in ["screenshot", "whatsapp", "tele", "fb_", "edited", "crop", "modified"]):
        score += 10.0
        details.append("Filename suggests secondary source or screenshot transfer.")

    # Bound the score
    score = max(5.0, min(99.0, score))
    
    # Determine risk level category
    if score >= 65.0:
        risk_level = "HIGH"
    elif score >= 35.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
        
    return {
        "risk_level": risk_level,
        "risk_score": round(score, 1),
        "details": details
    }
