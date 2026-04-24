from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class DocumentModel:
    """
    Represents a verified document inside the TrustLens system.
    Provides strict type hinting for the entire cryptographic pipeline.
    """
    user_id: str
    image_url: str
    extracted_fields: Dict[str, Any]
    content_hash: str
    digital_signature: str
    did_public_key: str
    id: Optional[str] = None
    created_at: Optional[str] = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary for Supabase insertion."""
        return {
            "user_id": self.user_id,
            "image_url": self.image_url,
            "extracted_fields": self.extracted_fields,
            "content_hash": self.content_hash,
            "digital_signature": self.digital_signature,
            "did_public_key": self.did_public_key
        }
