# Visual Document Trust Chain - Technical Documentation

## 1. Abstract
The "Visual Document Trust Chain" is a robust, AI-powered decentralised identity application designed to combat physical document forgery. By leveraging Optical Character Recognition (OCR) combined with spatial layout awareness (LayoutParser), the system accurately digitises text from physical documents such as invoices or ID cards. The extracted structured data is subjected to a cryptographic pipeline: it is hashed using SHA-256 and signed via an Elliptic Curve Digital Signature Algorithm (ECDSA) to generate a Verifiable Credential. This process anchors physical documents to mathematical proofs, essentially functioning as an automated "Digital Notary". The architecture guarantees that even a single-character alteration in the physical or digital document will invalidate the signature, ensuring absolute trust, transparency, and data integrity in remote verification scenarios.

## 2. Problem Statement
In the modern digital economy, the submission of physical documents (like ID cards, invoices, and certificates) via digital mediums (photos/scans) is ubiquitous. However, manual verification is highly susceptible to sophisticated photo-editing forgery. Current systems lack a mathematical guarantee that the data presented in a digital image matches the exact data intended at the time of issuance or upload. There is an urgent need for a system that can automatically read physical documents and cryptographically bind them to a verifiable, untampered identity.

## 3. Solution: The Visual Chain
The system solves this via a deterministic pipeline:
1. **OCR & Extraction:** AI parses the uploaded image and extracts exact textual fields.
2. **Deterministic Hashing:** The JSON fields are alphabetically sorted and hashed (SHA-256) to create a unique digital fingerprint.
3. **Digital Identity (DID):** A unique Elliptic Curve keypair is generated for the document.
4. **Signature:** The private key signs the hash.
5. **Verification:** A public portal allows anyone to fetch the document data, re-hash it, and use the public key to mathematically verify the signature.

## 4. Architecture

```text
[ Physical Document ]
        │
        ▼
[ Streamlit UI Frontend ] ──────────────────────┐
        │                                       │
        ▼ (Image Upload)                        │
[ OCR Engine (pytesseract + LayoutParser) ]     │ (Save JSON + Proofs)
        │                                       │
        ▼ (Structured Fields: Name, Date...)    │
[ Crypto Chain Module ]                         │
  ├─ SHA256 Hash Generation                     │
  ├─ ECDSA Key Generation                       ▼
  └─ Hash Signing ─────────────────────> [ Supabase ] (PostgreSQL + Blob Storage)
                                                │
                                                ▼
                                   [ Public Verification Portal ]
```

## 5. Tech Stack & Justification
*   **Streamlit:** Facilitates rapid UI development with native Python integration, ideal for ML-heavy prototypes.
*   **Supabase (PostgreSQL):** Serves as an open-source Firebase alternative, providing robust Row Level Security (RLS) for user data and integrated Blob Storage for images.
*   **PyTesseract:** The industry standard for OCR, capable of handling over 100 languages with high accuracy.
*   **LayoutParser (Detectron2):** Adds spatial awareness. Instead of reading left-to-right blindly, it understands document structures (tables, lists, titles).
*   **Cryptography (Python):** Provides robust, low-level implementations of ECDSA and SHA256, ensuring standard compliance without compiling C/Rust toolchains like some DID libraries.

## 6. Database Schema
**Table: `public.documents`**
*   `id` (uuid, PK): Unique document identifier.
*   `user_id` (uuid, FK): Reference to the `auth.users` table.
*   `image_url` (text): Public URL pointing to the Supabase Storage bucket.
*   `extracted_fields` (jsonb): The structured data extracted from the document.
*   `content_hash` (text): SHA-256 hex digest of the JSON.
*   `digital_signature` (text): Base64 encoded ECDSA signature.
*   `did_public_key` (text): PEM formatted Public Key.
*   `created_at` (timestamp): Insertion time.

## 7. Modules
*   **`auth.py`**: Wraps the Supabase authentication client for Sign In, Sign Up, and Session State management.
*   **`db_client.py`**: Manages CRUD operations to PostgreSQL and handles image uploads to Supabase Storage.
*   **`ocr_engine.py`**: Instantiates the ML models. Includes a fail-safe mechanism: it attempts to load LayoutParser's Detectron2 models, and falls back to pure Tesseract if dependencies are missing, guaranteeing stability.
*   **`crypto_chain.py`**: Handles all cryptographic primitives (SHA-256, SECP256R1 ECDSA) ensuring deterministic outputs.

## 8. Crypto & DID Deep Dive
The system acts as a decentralized identity (DID) provider for documents. Instead of relying on a centralized authority to say "this document is valid", the mathematics prove it. 
1. We use the **SECP256R1** elliptic curve, which offers strong security with small key sizes.
2. The extracted data is serialized to JSON. Crucially, `sort_keys=True` is used. This ensures that `{"a": 1, "b": 2}` and `{"b": 2, "a": 1}` produce the exact same byte sequence, preventing false-positive tampering alerts.
3. The JSON bytes are hashed using **SHA-256**.
4. The hash is signed with the Private Key. The Public Key is published. 
If an attacker alters the `extracted_fields` in the database, the re-computed hash will change, and the Public Key will fail to verify the signature, exposing the tamper attempt.

## 9. Security
*   **Row Level Security (RLS):** Supabase RLS is configured so users can only `INSERT` and `SELECT` their own documents via their JWT.
*   **Immutability:** The crypto-chain prevents internal database tampering.
*   **Collision Resistance:** SHA-256 makes it mathematically infeasible for an attacker to alter the document text while keeping the same hash.

## 10. Deployment
The application is designed to be deployed on Hugging Face Spaces using the Streamlit SDK. Hugging Face provides a free Linux container environment. The application pulls environment variables (`SUPABASE_URL`, `SUPABASE_KEY`) securely via HF Secrets.

## 11. Future Scope
*   **Blockchain Anchoring:** Store the Document Hash on a public blockchain (like Ethereum or Polygon) instead of Supabase to achieve absolute decentralization.
*   **Mobile App:** Re-write the frontend in Flutter or React Native to allow users to scan documents directly using their smartphone cameras.
*   **Advanced NLP:** Use LLMs (like Gemini or Llama) instead of Regex to intelligently extract fields from unstructured documents.

---

## 12. Viva Q&A (25 Detailed Questions for Presentation)

**1. What is the main objective of this project?**
To create an automated system that extracts text from physical documents and cryptographically signs it, proving that the digital representation hasn't been tampered with.

**2. Why use Streamlit instead of React or Angular?**
Streamlit allows rapid prototyping directly in Python, which is essential since our core logic (OCR, ML models, Cryptography) is all Python-native. It reduces the overhead of building a separate REST API backend.

**3. What does PyTesseract do?**
It's a Python wrapper for Google's Tesseract OCR Engine, which converts images of text into machine-readable string data.

**4. Why did you include LayoutParser if Tesseract already reads text?**
Tesseract reads left-to-right. For complex documents like invoices with tables and columns, it jumbles the text. LayoutParser uses AI (Detectron2) to identify structural blocks (titles, lists) so we can OCR them in logical order.

**5. How does the fallback mechanism in your OCR engine work?**
If the heavy Detectron2 AI models fail to load (due to hardware or OS limitations), a `try/except` block catches the `ImportError` and seamlessly routes the image directly to pure Tesseract.

**6. What database are you using and why?**
Supabase (PostgreSQL). It's a scalable, open-source alternative to Firebase that provides a relational database, authentication, and file storage in one SDK.

**7. How do you extract specific fields like Name and Date?**
I implemented Regular Expressions (Regex) in `extract_fields()` to pattern-match common keywords (e.g., "Invoice No:", "Date:") and extract the adjacent values.

**8. What hashing algorithm did you use?**
SHA-256 (Secure Hash Algorithm 256-bit).

**9. Why is hashing necessary?**
It acts as a digital fingerprint. Any tiny change in the document's text will completely change the resulting hash.

**10. Why do you use `sort_keys=True` when dumping the JSON for hashing?**
Dictionaries in Python don't guarantee key order. If the order changes, the string changes, and the hash changes. Sorting keys ensures deterministic hashing so verification works consistently.

**11. What is ECDSA?**
Elliptic Curve Digital Signature Algorithm. It's used to generate key pairs and digital signatures, offering high security with smaller key sizes compared to RSA.

**12. Which Elliptic Curve did you use?**
SECP256R1, a standard curve widely supported by cryptographic libraries.

**13. What is a Digital Identity (DID) in the context of your project?**
It's a decentralized identifier. Here, the generated Public Key acts as the DID for the document, proving the origin and integrity of the data without relying on a central authority.

**14. Explain the difference between Hashing and Encryption.**
Hashing is a one-way mathematical function (you can't reverse it to get the original data). Encryption is two-way (you can decrypt it if you have the key). We use hashing for integrity, not encryption.

**15. How does the verification process work?**
The system takes the stored text, hashes it again, and uses the stored Public Key to verify if the stored Signature matches this new hash. If yes, it's valid.

**16. What happens if someone edits the database manually?**
The verification will fail. The re-computed hash will not match the hash signed by the Private Key, and the UI will show a "Tampered" badge.

**17. What is Supabase Storage used for?**
It acts as an AWS S3 alternative to store the actual physical image files uploaded by the user, while the DB stores the URLs and metadata.

**18. What is RLS in Supabase?**
Row Level Security. It ensures that users can only interact with database rows that belong to their specific `user_id`, preventing unauthorized access.

**19. How did you handle user authentication?**
Using the Supabase Auth client, which provides secure email/password registration and issues JWT (JSON Web Tokens) for session management.

**20. What is a JWT?**
A JSON Web Token. It's a standard used to securely transmit information between parties as a JSON object, used here by Supabase to maintain login sessions.

**21. Where is the private key stored?**
In this prototype architecture, keys are generated on-the-fly and signatures are created immediately. In a production system, private keys would be stored in a secure Hardware Security Module (HSM) or the user's local wallet.

**22. How are you deploying this project?**
Using Hugging Face Spaces, which provides a free Linux container ideal for Python ML applications.

**23. What are environment variables used for?**
To store sensitive information like the `SUPABASE_URL` and `SUPABASE_KEY` outside of the source code, preventing security leaks if the code is made public.

**24. Could this system be used for fake physical documents?**
If a physically forged document is scanned, the OCR will read the forged text. This system guarantees the *digital chain of custody* from the moment of upload, not the physical authenticity of the paper itself.

**25. How could you improve the OCR extraction in the future?**
By replacing standard Regex with a Large Language Model (LLM) prompt, which can intelligently understand context and extract fields even from highly unstructured or messy documents.
