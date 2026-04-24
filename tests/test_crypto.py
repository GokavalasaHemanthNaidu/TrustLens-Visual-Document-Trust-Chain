import pytest
from utils import crypto_signer, hashing

def test_deterministic_hashing():
    # Two identical dicts with different key insertion orders
    dict1 = {"amount": "100", "name": "John", "date": "2026-04-24"}
    dict2 = {"date": "2026-04-24", "amount": "100", "name": "John"}
    
    hash1 = hashing.create_hash(dict1)
    hash2 = hashing.create_hash(dict2)
    
    assert hash1 == hash2, "Hashing must be deterministic regardless of dict order"

def test_ecdsa_signing_and_verification():
    content = {"id": "12345", "verified": True}
    content_hash = hashing.create_hash(content)
    
    private_pem, public_pem = crypto_signer.generate_keypair()
    signature = crypto_signer.sign_hash(content_hash, private_pem)
    
    is_valid = crypto_signer.verify_signature(content_hash, signature, public_pem)
    assert is_valid is True, "Signature verification should pass for correct keys and hash"

def test_ecdsa_tamper_detection():
    content = {"id": "12345", "verified": True}
    content_hash = hashing.create_hash(content)
    
    private_pem, public_pem = crypto_signer.generate_keypair()
    signature = crypto_signer.sign_hash(content_hash, private_pem)
    
    # Simulate an attacker changing the hash (Tampering the document data)
    tampered_content = {"id": "12345", "verified": False}
    tampered_hash = hashing.create_hash(tampered_content)
    
    is_valid = crypto_signer.verify_signature(tampered_hash, signature, public_pem)
    assert is_valid is False, "Signature verification MUST fail for tampered hashes"
