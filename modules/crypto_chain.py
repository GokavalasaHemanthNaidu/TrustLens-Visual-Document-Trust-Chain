import hashlib
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives import serialization

def create_hash(content: dict) -> str:
    \"\"\"
    Creates a SHA-256 hash of the extracted JSON content.
    Sorts keys to ensure consistent hashing.
    \"\"\"
    # Sort keys to guarantee deterministic string representation
    content_str = json.dumps(content, sort_keys=True).encode('utf-8')
    return hashlib.sha256(content_str).hexdigest()

def generate_keypair():
    \"\"\"
    Generates an ECDSA keypair using the SECP256R1 curve.
    Returns standard PEM encoded strings for easy storage.
    \"\"\"
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem

def sign_hash(content_hash: str, private_pem: str) -> str:
    \"\"\"
    Signs a SHA256 hash using the provided ECDSA private key.
    Returns a Base64 encoded signature.
    \"\"\"
    private_key = serialization.load_pem_private_key(
        private_pem.encode('utf-8'),
        password=None
    )
    
    # The content_hash is already a hex string of the sha256 hash.
    # We must convert it to bytes.
    hash_bytes = bytes.fromhex(content_hash)
    
    # Using Prehashed because we already hashed the content externally
    signature = private_key.sign(
        hash_bytes,
        ec.ECDSA(Prehashed(hashes.SHA256()))
    )
    
    return base64.b64encode(signature).decode('utf-8')

def verify_signature(content_hash: str, signature_b64: str, public_pem: str) -> bool:
    \"\"\"
    Verifies that the given base64 signature matches the content hash and public key.
    \"\"\"
    try:
        public_key = serialization.load_pem_public_key(
            public_pem.encode('utf-8')
        )
        
        signature_bytes = base64.b64decode(signature_b64.encode('utf-8'))
        hash_bytes = bytes.fromhex(content_hash)
        
        public_key.verify(
            signature_bytes,
            hash_bytes,
            ec.ECDSA(Prehashed(hashes.SHA256()))
        )
        return True
    except Exception as e:
        print(f"Verification Failed: {e}")
        return False
