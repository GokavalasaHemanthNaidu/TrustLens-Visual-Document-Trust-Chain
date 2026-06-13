<div align="center">

<img src="https://img.shields.io/badge/TrustLens-AI%20Document%20Trust%20Chain-3B82F6?style=for-the-badge&logo=shield&logoColor=white" alt="TrustLens"/>

# 🛡️ TrustLens — Visual Document Trust Chain

### *A Proof-of-Concept Document Verification Prototype*

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://trustlens-visual-document-trust-chain.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20NoSQL-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Image%20Storage-3448C5?style=flat-square&logo=cloudinary&logoColor=white)](https://cloudinary.com)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Donut%20%2B%20YOLO-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**[🚀 Live Demo](https://trustlens-visual-document-trust-chain.streamlit.app/) · [🐛 Report Bug](https://github.com/GokavalasaHemanthNaidu/TrustLens-Visual-Document-Trust-Chain/issues)**

</div>

---

## 🌟 What is TrustLens?

TrustLens is a **proof-of-concept document verification prototype** that explores combining Vision-Language AI extraction with ECDSA digital signatures to create verifiable document records — with a documented roadmap to production security hardening.

This project demonstrates an end-to-end understanding of AI pipelines, cryptography, and cloud deployment, exploring how automated document verification could reduce manual review overhead.

> 💡 **Core Experiment:** Explores the integration of VLM-based extraction with cryptographic signatures in a single deployable prototype, deployed on Streamlit Community Cloud.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🧠 **Multi-Layer AI Classification** | Identifies documents using a pipeline of object detection (YOLO), OCR, and rule-based extraction. |
| 🔒 **SHA-256 Fingerprinting** | Creates a unique cryptographic hash of extracted data (any tampering changes the hash). |
| ✍️ **Standard ECDSA Digital Signature** | Signs each document's hash (SECP256R1). *Note: Keys are generated per-session in memory for prototype purposes.* |
| 📊 **MongoDB Atlas Ledger** | Stores records in a MongoDB Atlas database. |
| ☁️ **Cloudinary Storage** | Securely stores document images via Cloudinary. |
| 🌐 **Public Verification Portal** | Allows verification using Name, ID, or Category without login. |
| 📥 **Trust Certificate PDF** | Downloads a certificate with embedded document photo + QR code. |
| 🗑️ **Full Data Control** | Users can delete their documents from the ledger and cloud storage. |

---

## 🏗️ Architecture: Blueprint vs. Current Implementation

### Target Architecture (v2.0)
```text
[Next.js Frontend] → [FastAPI Gateway] → [PostgreSQL/MongoDB + AWS S3]
```

### Current Implementation (v1.0 — Learning Prototype)
```text
[Streamlit App] → [MongoDB Atlas + Cloudinary]
```

**Rationale:** The Streamlit prototype validates the core concept (document → AI extraction → cryptographic signature → verification) with minimal infrastructure. The FastAPI/Next.js architecture is the production target for v2.0, which allows async ML workers, proper rate limiting, and a decoupled frontend.

---

## 🧠 AI Model Architecture

The extraction pipeline consists of the following heuristic and AI layers:
1. **Layer 1: YOLO Classification** — Attempts basic document detection.
2. **Layer 2: Tesseract OCR** — Extracts raw text for rule-based heuristics.
3. **Layers 3-5: Rule-Based Extraction and Validation** — Uses Regex and keyword matching.
4. **VLM Experimentation** — Integrates Donut VQA (naver-clova-ix) for exploring template-free extraction. *Donut VQA requires no OCR templates, enabling rapid adaptation to new document types.*

---

## 📊 Accuracy Benchmarks (HONEST VERSION)

| Document Type | Classification | Field Extraction | Notes |
|---|---|---|---|
| **Aadhaar Card** | 92-96%* | 85-90%* | Based on ~20 test samples |
| **PAN Card** | 90-94%* | 88-92%* | Based on ~15 test samples |
| **Passport** | 88-92%* | 80-85%* | Based on ~10 test samples |
| **Invoice/Receipt** | 70-80% | 60-70% | Keyword-based fallback |
| **Resume/CV** | 65-75% | 55-65% | Keyword-based fallback |

*\*Accuracy figures are preliminary and based on limited offline test datasets. Rigorous benchmarking with 100+ samples per type is planned for v1.5.*

---

## 🔒 Security & Limitations

This is a proof-of-concept for learning purposes. The following production-grade security measures are not yet implemented but identified as critical next steps:

| Security Control | Status | Notes |
|---|---|---|
| **Data Isolation** | Partial | Application-level filtering isolates user data, but database-level roles (like RLS) would be stricter in production. |
| **Rate Limiting** | Planned | No built-in rate limiting in Streamlit; would need FastAPI gateway. |
| **HSM Key Storage** | Planned | ECDSA keys are generated in-memory per session; production would use AWS KMS or HashiCorp Vault. |
| **Input Validation** | Partial | Upload file size/MIME limits implemented; needs deeper content scanning. |
| **Audit Logging** | Not implemented | Would need immutable append-only log (e.g., AWS QLDB or blockchain). |
| **ELA/Deepfake Detection** | Not implemented | Planned for v2.0 with OpenCV Error Level Analysis. |
| **Hash Scope** | Partial | Prototype hashes extracted text fields. Production should hash raw image bytes alongside text. |

*Why this matters: Being transparent about limitations shows an understanding of what production systems require. These gaps validate the need for the v2.0 microservices architecture.*

---

## 🛡️ Known Issues & Future Roadmap

**v1.0 (Current):**
- ✅ Core upload → extract → sign → verify flow
- ✅ MongoDB database and Cloudinary storage integration
- ✅ Public verification portal
- ⚠️ No network-level rate limiting
- ⚠️ Keys in memory

**v1.5 (Next):**
- [ ] Implement robust input validation (file size, type, content)
- [ ] Add basic rate limiting via Streamlit caching
- [ ] Benchmark with 100+ samples per document type

**v2.0 (Production Target):**
- [ ] Migrate to FastAPI + Next.js architecture
- [ ] Add OpenCV ELA for tamper detection
- [ ] Implement Celery async workers for ML inference
- [ ] Add AWS KMS for key management
- [ ] Add comprehensive audit logging
- [ ] Dockerize for reproducible deployment

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/GokavalasaHemanthNaidu/TrustLens-Visual-Document-Trust-Chain.git
cd TrustLens-Visual-Document-Trust-Chain
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# Also install Tesseract OCR:
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# Linux:   sudo apt install tesseract-ocr
```

### 3. Configure Secrets
Create `.streamlit/secrets.toml`:
```toml
MONGO_URI             = "your_mongo_connection_string"
MONGO_DB              = "trustlens"
CLOUDINARY_CLOUD_NAME = "your_cloud_name"
CLOUDINARY_API_KEY    = "your_api_key"
CLOUDINARY_API_SECRET = "your_api_secret"
HF_TOKEN              = "your_huggingface_token"
```

### 4. Run Locally
```bash
streamlit run app.py
```

### ⚠️ Deployment Note
This project is currently deployed on Streamlit Community Cloud. Free-tier apps go to "sleep" after 7 days of inactivity. If visiting the live demo, you may need to click "Wake App" and wait 2-3 minutes for the environment to boot and HuggingFace API endpoints to perform cold starts.

---

## 🤝 Contributing
Contributions are welcome for educational purposes! Please open a Pull Request for any of the roadmap items.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

---

## 👨‍💻 Author
**Gokavalasa Hemanth Naidu**
- GitHub: [@GokavalasaHemanthNaidu](https://github.com/GokavalasaHemanthNaidu)
- Email: anthnaidu2022.18@gmail.com
