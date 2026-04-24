# TrustLens Transformation Changelog

## 1. Bugs Resolved
- **Cross-Tab Session Leakage:** `app.py` previously fetched the global `supabase.auth.get_session()` outside of `st.session_state`. This caused the global Python process to leak the authenticated state across browser tabs. Refactored to strictly rely on `st.session_state`.
- **List Index Out of Range:** Fixed a bug in the verify screen where splitting the public key by `\\n` failed if actual newline characters were present. Replaced with safe `.split('\n')` and length validation.
- **NameError 'model' is not defined:** Moved `model = None` outside the `try/except` block in `ocr_engine.py` so the fallback logic triggers safely without crashing when `layoutparser` is not installed.
- **Streamlit Cloud OOM Installer Crash:** Removed heavy dependencies (`layoutparser`, `detectron2`, `torch`) from `requirements.txt` to prevent free-tier RAM limits from killing the deployment.

## 2. Architectural Refactoring
- Transitioned from a monolithic script to a professional `pages/` Multi-Page App structure.
- Created `utils/` for reusable logic (`crypto_signer.py`, `ocr_processor.py`, `hashing.py`).
- Created `components/` for UI widgets.
- Created `models/document.py` using `dataclasses` to enforce strict typing across the trust chain pipeline.
- Added Python 3.9+ type hints and Google-style docstrings globally.
- Replaced `print()` with standard Python `logging`.

## 3. UI/UX Enhancements
- Added `.streamlit/config.toml` for a cohesive Deep Blue & Emerald (Trust) color palette.
- Replaced standard buttons with custom CSS responsive cards and hover effects.
- Added animated `st.progress` indicators for the multi-phase processing pipeline.
- Implemented `st.toast` for non-intrusive success notifications.
- Professionalized typography and spacing globally.

## 4. Feature Additions
- **Batch Processing:** The upload zone now accepts multiple files simultaneously, processing them in a loop with individual progress tracking.
- **Verification Certificates:** Implemented `fpdf2` to dynamically generate downloadable PDF certificates containing cryptographic anchors and an embedded QR code linking back to the verification page.
- **Trust Analytics Dashboard:** Added a searchable, filterable table showing an immutable audit log of all secured documents with CSV export capability.
- **Provenance Visualization:** Added an interactive Altair timeline chart simulating the blockchain/provenance lifecycle of the document.
- **Security Validation:** Implemented strict 5MB file size limits prior to AI processing to prevent Denial of Service on the OCR engine.
