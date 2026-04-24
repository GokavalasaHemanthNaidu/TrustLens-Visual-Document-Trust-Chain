# -*- coding: utf-8 -*-
import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
import streamlit as st

logger = logging.getLogger(__name__)

# ── Safe Secrets Access ────────────────────────────────────────────────────────
# Using a helper to avoid KeyError on different Streamlit versions
def get_secret(key, default=None):
    try:
        # Try Streamlit Secrets first
        return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError, TypeError):
        # Fallback to Environment Variables
        return os.getenv(key, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing Supabase credentials. Ensure Streamlit Secrets or .env are configured.")

# Initialize Supabase Client
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        supabase = None
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    supabase = None

# ── DB Functions ───────────────────────────────────────────────────────────────
def upload_image_to_storage(user_id: str, file_bytes: bytes, file_name: str) -> Optional[str]:
    """Uploads an image to Supabase Storage and returns the public URL."""
    if not supabase: return None
    try:
        unique_filename = f"{user_id}/{uuid.uuid4()}_{file_name}"
        res = supabase.storage.from_('documents').upload(
            file=file_bytes,
            path=unique_filename,
            file_options={"content-type": "image/jpeg"}
        )
        public_url = supabase.storage.from_('documents').get_public_url(unique_filename)
        return public_url
    except Exception as e:
        logger.error(f"Error uploading image to storage: {e}")
        return None

def save_document_record(document_model) -> Optional[Dict[str, Any]]:
    """Saves the document metadata and trust chain to the database."""
    if not supabase: return None
    try:
        data = document_model.to_dict()
        response = supabase.table("documents").insert(data).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error saving document record: {e}")
        return None

def get_user_documents(user_id: str) -> List[Dict[str, Any]]:
    """Retrieves all documents for a specific user."""
    if not supabase: return []
    try:
        response = supabase.table("documents").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching user documents: {e}")
        return []

def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single document by its ID for public verification."""
    if not supabase: return None
    try:
        response = supabase.table("documents").select("*").eq("id", doc_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching document by ID {doc_id}: {e}")
        return None
