# -*- coding: utf-8 -*-
import qrcode
import requests
from io import BytesIO
from fpdf import FPDF
import logging

logger = logging.getLogger(__name__)

class TrustCertificate(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 20)
        self.set_text_color(0, 86, 179)
        self.cell(0, 15, "Visual Document Trust Certificate", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("helvetica", "I", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "Cryptographically Secured Provenance | TrustLens v1.5.0", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Verified by TrustLens Immutable Ledger | Page {self.page_no()}", align="C")

def generate_pdf_certificate(doc_model, verification_url: str) -> bytes:
    """Generates a rich PDF certificate with QR code and original document image."""
    try:
        pdf = TrustCertificate()
        pdf.add_page()

        # ── 1. Document Metadata ─────────────────────────────────────────────
        pdf.set_fill_color(245, 247, 250)
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 12, "  Certificate Metadata", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(2)

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(50, 8, "Document ID:")
        pdf.set_font("courier", "", 10)
        pdf.cell(0, 8, str(doc_model.id), new_x="LMARGIN", new_y="NEXT")

        extracted = doc_model.extracted_fields or {}
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(50, 8, "Subject Name:")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 8, str(extracted.get('name', 'N/A')), new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(50, 8, "Doc Type / Ref:")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 8, str(extracted.get('document_id', 'N/A')), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

        # ── 2. Original Document Image ───────────────────────────────────────
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 12, "  Original Document Proof", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(5)
        
        try:
            # Download image from Supabase URL to embed in PDF
            img_resp = requests.get(doc_model.image_url, timeout=10)
            img_resp.raise_for_status()
            img_data = BytesIO(img_resp.content)
            # Center the image
            pdf.image(img_data, x=45, y=pdf.get_y(), w=120)
            pdf.set_y(pdf.get_y() + 90) # Adjust Y after image (approx 90mm height)
        except Exception as img_err:
            logger.error(f"Could not embed image in PDF: {img_err}")
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, "[Image could not be retrieved for embedding]", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        pdf.ln(10)

        # ── 3. Cryptographic Anchors ─────────────────────────────────────────
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 12, "  Cryptographic Security", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(2)
        
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(0, 8, "SHA-256 Content Fingerprint:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("courier", "", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.multi_cell(0, 6, doc_model.content_hash, fill=True)
        
        pdf.ln(4)

        # ── 4. QR Code & Public Audit URL ────────────────────────────────────
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buf = BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)

        y_pos = pdf.get_y()
        pdf.image(qr_buf, x=150, y=y_pos, w=45)

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, "Verification Link:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(0, 86, 179)
        pdf.multi_cell(135, 5, verification_url)
        pdf.ln(5)
        pdf.set_text_color(0, 120, 0)
        pdf.set_font("helvetica", "B", 10)
        pdf.multi_cell(135, 6, "✔ Scan QR or visit link to confirm this document matches the ledger exactly.")

        return bytes(pdf.output())
    except Exception as e:
        logger.error(f"PDF Error: {e}", exc_info=True)
        return b""
