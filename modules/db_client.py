import os
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid
import json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_to_storage(user_id: str, file_bytes: bytes, file_name: str) -> str:
    \"\"\"Uploads an image to Supabase Storage and returns the public URL.\"\"\"
    try:
        unique_filename = f"{user_id}/{uuid.uuid4()}_{file_name}"
        
        # Upload to 'documents' bucket
        res = supabase.storage.from_('documents').upload(
            file=file_bytes,
            path=unique_filename,
            file_options={"content-type": "image/jpeg"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_('documents').get_public_url(unique_filename)
        return public_url
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

def save_document_record(user_id: str, image_url: str, fields: dict, content_hash: str, signature: str, public_key: str):
    \"\"\"Saves the document metadata and trust chain to the database.\"\"\"
    data = {
        "user_id": user_id,
        "image_url": image_url,
        "extracted_fields": fields, # Supabase handles dict -> JSONB automatically
        "content_hash": content_hash,
        "digital_signature": signature,
        "did_public_key": public_key
    }
    
    response = supabase.table("documents").insert(data).execute()
    return response.data

def get_user_documents(user_id: str):
    \"\"\"Retrieves all documents for a specific user.\"\"\"
    response = supabase.table("documents").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data

def get_document_by_id(doc_id: str):
    \"\"\"Retrieves a single document by its ID for public verification.\"\"\"
    try:
        response = supabase.table("documents").select("*").eq("id", doc_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching document: {e}")
        return None
