# TrustLens - Visual Document Trust Chain 🔐

![Streamlit](https://img.shields.io/badge/Streamlit-1.33-FF4B4B.svg?style=flat&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?style=flat&logo=python)
![Cryptography](https://img.shields.io/badge/Security-ECDSA_SECP256R1-green.svg)

TrustLens is a production-grade digital notary and immutable provenance engine. It uses AI (OCR) to extract physical document data, hashes it deterministically (SHA-256), and cryptographically signs it using ECDSA. The resulting Trust Chain is anchored into Supabase, allowing anyone to verify a document's integrity globally with zero-knowledge proofs.

## 🌟 Live Demo
**[Launch TrustLens on Streamlit Community Cloud](https://trustlens-visual-document-trust-chain.streamlit.app)**

## 🏗️ Architecture

```text
trustlens/
├── app.py                 # Multi-Page Router & Login
├── components/            # UI widgets (Upload Zone, Certificate, Provenance Chart)
├── utils/                 # Business Logic
│   ├── hashing.py         # Deterministic JSON SHA-256
│   ├── ocr_processor.py   # AI Text Extraction
│   ├── crypto_signer.py   # ECDSA Keypair & Signatures
│   └── db_client.py       # Supabase Database/Storage
├── models/                # Document Data Models (Dataclasses)
├── pages/                 # Streamlit Native Routing Pages
├── tests/                 # Pytest Verification Suites
└── .streamlit/            # Deep Blue / Emerald Theme Configuration
```

## ✨ Core Features
- **Batch Processing:** Upload multiple documents simultaneously.
- **Visual Provenance:** Interactive lifecycle timeline charting.
- **Verification Certificates:** Downloadable PDF certificates with embedded QR codes linking to public validation.
- **Trust Analytics:** Searchable immutable audit logs with CSV export capabilities.
- **Zero-Knowledge Verification:** Recalculates hashes and validates ECDSA signatures mathematically entirely in-browser.

## 🚀 Local Installation

1. **Clone the repository**
```bash
git clone https://github.com/GokavalasaHemanthNaidu/TrustLens-Visual-Document-Trust-Chain.git
cd TrustLens-Visual-Document-Trust-Chain
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Secrets**
Create a `.streamlit/secrets.toml` file (or `.env`):
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

4. **Run the Application**
```bash
streamlit run app.py
```

## 🛡️ Security Notes
- This application uses strict `st.session_state` management to prevent Cross-Tab leakage.
- Max file upload size is hard-capped at 5MB to prevent DoS attacks on the OCR engine.
- Supabase requires **Leaked Password Protection** and properly configured **Storage RLS Policies (INSERT allowed)**.
