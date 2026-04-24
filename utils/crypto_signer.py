import base64
import logging
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

def generate_keypair() -> Tuple[str, str]:
    """
    Generates an ECDSA keypair using the SECP256R1 curve.
    
    Returns:
        Tuple[str, str]: Standard PEM encoded strings (private_pem, public_pem).
    """
    try:
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
        
        logger.info("Successfully generated new ECDSA SECP256R1 keypair.")
        return private_pem, public_pem
    except Exception as e:
        logger.error(f"Error generating keypair: {e}")
        raise

def sign_hash(content_hash: str, private_pem: str) -> str:
    """
    Signs a SHA-256 hash using the provided ECDSA private key.
    
    Args:
        content_hash (str): The hex string of the SHA-256 hash.
        private_pem (str): The PEM encoded private key.
        
    Returns:
        str: Base64 encoded signature.
    """
    try:
        private_key = serialization.load_pem_private_key(
            private_pem.encode('utf-8'),
            password=None
        )
        
        # Convert hex string to bytes
        hash_bytes = bytes.fromhex(content_hash)
        
        signature = private_key.sign(
            hash_bytes,
            ec.ECDSA(Prehashed(hashes.SHA256()))
        )
        
        logger.info("Successfully signed document hash.")
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        logger.error(f"Error signing hash: {e}")
        raise

def verify_signature(content_hash: str, signature_b64: str, public_pem: str) -> bool:
    """
    Verifies that the base64 signature matches the content hash and public key.
    
    Args:
        content_hash (str): The original document hash.
        signature_b64 (str): The base64 encoded ECDSA signature.
        public_pem (str): The PEM encoded public key string.
        
    Returns:
        bool: True if signature is cryptographically valid, False otherwise.
    """
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
        logger.info(f"Signature verification passed for hash {content_hash[:10]}...")
        return True
    except Exception as e:
        logger.warning(f"Signature Verification Failed: {e}")
        return False
