# Visual Document Trust Chain 🔗

A complete, production-ready final year CSE project that acts as a Digital Notary. It takes a photo document (like an Aadhaar card or Invoice), extracts the text using AI OCR (Tesseract + LayoutParser), hashes the content, and cryptographically signs it to create a verifiable, untampered Digital Identity (DID) standard credential.

## Features

* **Authentication:** Secure user login via Supabase.
* **AI OCR Engine:** Uses PyTesseract and LayoutParser for intelligent document parsing.
* **Trust Chain (Cryptography):** Generates SHA-256 hashes and ECDSA digital signatures to guarantee document integrity.
* **Digital Identity (DID):** Employs standard Elliptic Curve cryptography to anchor public keys to documents.
* **Public Verification:** Share a document ID to mathematically prove it hasn't been altered.
* **Cloud Storage:** Images and structured JSON data are stored immutably in Supabase PostgreSQL.

---

## Local Setup Instructions

### 1. Prerequisites
- **Python 3.9+** installed on your system.
- **Tesseract OCR Engine:**
  - **Windows:** Download the installer from [UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki). Install it, and ensure `C:\\Program Files\\Tesseract-OCR` is added to your System PATH environment variable.
  - **Mac/Linux:** Use `brew install tesseract` or `sudo apt-get install tesseract-ocr`.

### 2. Installation
Clone the project, open a terminal, and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and add your Supabase credentials (this project is already pre-configured with yours):

```env
SUPABASE_URL=https://[your-project-id].supabase.co
SUPABASE_KEY=[your-anon-key]
```

### 4. Run the Application
Start the Streamlit development server:

```bash
streamlit run app.py
```
The app will open automatically in your browser at `http://localhost:8501`.

---

## Hugging Face Spaces Deployment

Deploying this app globally for free is incredibly easy using Hugging Face Spaces:

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and create an account.
2. Click **Create new Space**.
3. **Space Name:** `Visual-Document-Trust-Chain`
4. **License:** MIT
5. **Select the Space SDK:** Choose **Streamlit**.
6. **Space Hardware:** Select the Free Tier (CPU). 
7. Click **Create Space**.
8. In the Space settings, go to **Settings -> Variables and secrets**. Add your `SUPABASE_URL` and `SUPABASE_KEY` as Secrets.
9. Finally, upload all the files from this folder (`app.py`, `requirements.txt`, `modules/`, etc.) directly into the Hugging Face Space repository. 
10. Hugging Face will automatically build and deploy your app. It will run 24/7 globally for your professors to see!
