import hashlib
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def create_hash(content: Dict[str, Any]) -> str:
    """
    Creates a SHA-256 hash of the extracted JSON content.
    Sorts keys to ensure consistent, deterministic hashing.
    
    Args:
        content (Dict[str, Any]): The extracted document fields.
        
    Returns:
        str: Hexadecimal representation of the SHA-256 hash.
    """
    try:
        # Sort keys to guarantee deterministic string representation
        content_str = json.dumps(content, sort_keys=True).encode('utf-8')
        doc_hash = hashlib.sha256(content_str).hexdigest()
        logger.info(f"Successfully generated deterministic SHA-256 hash: {doc_hash[:10]}...")
        return doc_hash
    except Exception as e:
        logger.error(f"Failed to generate content hash: {e}")
        raise
