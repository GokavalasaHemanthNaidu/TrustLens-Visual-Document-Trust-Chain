import os
import qrcode
from io import BytesIO
from fpdf import FPDF
import logging

logger = logging.getLogger(__name__)

class TrustCertificate(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 20)
        self.cell(0, 15, "Visual Document Trust Certificate", align="C", ln=True)
        self.set_font("helvetica", "I", 12)
        self.cell(0, 10, "Cryptographically Secured Provenance", align="C", ln=True)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_pdf_certificate(doc_model, verification_url: str) -> bytes:
    """
    Generates a PDF certificate containing the document's trust parameters and a QR code.
    
    Args:
        doc_model: The DocumentModel instance containing the data.
        verification_url: The URL to the public verification page.
        
    Returns:
        bytes: The raw PDF bytes for download.
    """
    try:
        pdf = TrustCertificate()
        pdf.add_page()
        
        # Details
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Document Details:", ln=True)
        pdf.set_font("helvetica", "", 10)
        
        for k, v in doc_model.extracted_fields.items():
            pdf.cell(50, 8, f"{k.title()}:")
            pdf.cell(0, 8, str(v), ln=True)
        
        pdf.ln(10)
        
        # Cryptography
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Cryptographic Anchors:", ln=True)
        
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, "SHA-256 Content Hash:", ln=True)
        pdf.set_font("courier", "", 9)
        pdf.multi_cell(0, 6, doc_model.content_hash)
        
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, "ECDSA SECP256R1 Signature:", ln=True)
        pdf.set_font("courier", "", 9)
        pdf.multi_cell(0, 6, doc_model.digital_signature)
        
        pdf.ln(10)
        
        # QR Code Generation
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR to temp memory and embed
        qr_path = "temp_qr.png"
        qr_img.save(qr_path)
        pdf.image(qr_path, x=150, y=pdf.get_y(), w=40)
        os.remove(qr_path)
        
        # Verification Note
        pdf.set_font("helvetica", "I", 10)
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(130, 6, "Scan the QR code or visit the verification link to independently audit this document's integrity against the DID public key.")
        
        pdf_bytes = pdf.output(dest='S')
        logger.info("Successfully generated PDF verification certificate.")
        return pdf_bytes
    except Exception as e:
        logger.error(f"Error generating PDF certificate: {e}")
        return b""
