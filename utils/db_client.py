# -*- coding: utf-8 -*-
"""
db_client.py  ─  MongoDB Atlas backend (replaces Supabase)
Collections:
  documents  ─ document records + trust chain
  users      ─ registered accounts (email + bcrypt hash)

Image storage: Cloudinary free tier (25 GB, never pauses)
"""
import os
import re
import uuid
import logging
import datetime
from typing import Dict, Any, Optional, List

import streamlit as st
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)

# ── Secrets helper ─────────────────────────────────────────────────────────────
def _secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ── MongoDB connection (cached per session) ────────────────────────────────────
@st.cache_resource
def _get_mongo():
    uri = _secret("MONGO_URI", "")
    if not uri:
        logger.error("MONGO_URI not set in secrets.")
        return None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")          # verify connection
        return client
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def _db():
    client = _get_mongo()
    if client is None:
        return None
    db_name = _secret("MONGO_DB", "trustlens")
    return client[db_name]

def _docs() -> Optional[Collection]:
    db = _db()
    return db["documents"] if db is not None else None

def _users() -> Optional[Collection]:
    db = _db()
    return db["users"] if db is not None else None

# ── Cloudinary setup ───────────────────────────────────────────────────────────
def _init_cloudinary():
    cloudinary.config(
        cloud_name = _secret("CLOUDINARY_CLOUD_NAME", ""),
        api_key    = _secret("CLOUDINARY_API_KEY",    ""),
        api_secret = _secret("CLOUDINARY_API_SECRET", ""),
        secure     = True,
    )

# ── DOCUMENT: upload image ─────────────────────────────────────────────────────
def upload_image_to_storage(user_id: str, file_bytes: bytes, file_name: str) -> Optional[str]:
    """Upload image to Cloudinary and return the secure public URL."""
    try:
        _init_cloudinary()
        public_id = f"trustlens/{user_id}/{uuid.uuid4().hex}"
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id   = public_id,
            resource_type = "image",
            overwrite   = True,
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        return None

# ── DOCUMENT: save record ──────────────────────────────────────────────────────
def save_document_record(document_model) -> Optional[Dict[str, Any]]:
    """Insert a document record into MongoDB."""
    col = _docs()
    if col is None:
        return None
    try:
        data = document_model.to_dict()
        # Ensure 'id' field is a string UUID; use it as the unique key
        if "id" not in data or not data["id"]:
            data["id"] = str(uuid.uuid4())
        data["created_at"] = data.get("created_at") or \
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        col.insert_one(data)
        return data
    except Exception as e:
        logger.error(f"Error saving document: {e}")
        return None

# ── DOCUMENT: get all for user ─────────────────────────────────────────────────
def get_user_documents(user_id: str) -> List[Dict[str, Any]]:
    """Return all documents belonging to user_id, newest first."""
    col = _docs()
    if col is None:
        return []
    try:
        docs = list(col.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", DESCENDING))
        return docs
    except Exception as e:
        logger.error(f"Error fetching user documents: {e}")
        return []

# ── DOCUMENT: get by id ────────────────────────────────────────────────────────
def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single document by its UUID string id."""
    col = _docs()
    if col is None:
        return None
    try:
        doc = col.find_one({"id": doc_id}, {"_id": 0})
        return doc
    except Exception as e:
        logger.error(f"Error fetching document {doc_id}: {e}")
        return None

# ── DOCUMENT: delete ───────────────────────────────────────────────────────────
def delete_document_record(doc_id: str, image_url: Optional[str] = None) -> bool:
    """Delete document from MongoDB and optionally remove Cloudinary image."""
    col = _docs()
    if col is None:
        return False
    try:
        col.delete_one({"id": doc_id})

        # Delete from Cloudinary if URL present
        if image_url and "cloudinary" in image_url:
            try:
                _init_cloudinary()
                # Extract public_id from URL
                # URL format: https://res.cloudinary.com/<cloud>/image/upload/v.../trustlens/...
                match = re.search(r"/upload/(?:v\d+/)?(trustlens/.+?)(?:\.\w+)?$", image_url)
                if match:
                    cloudinary.uploader.destroy(match.group(1))
            except Exception:
                pass   # secondary — don't fail the whole delete

        logger.info(f"Deleted document: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        return False

# ── SEARCH: unified search for verify page ─────────────────────────────────────
def search_documents(
    search_term: str = "",
    doc_type_filter: str = "all",
    limit: int = 1
) -> List[Dict[str, Any]]:
    """
    Search documents across name, document_id, doc_type, address.
    Returns list of matching raw dicts (MongoDB documents, _id excluded).
    """
    col = _docs()
    if col is None:
        return []
    try:
        query: Dict[str, Any] = {}

        # Type filter
        if doc_type_filter and doc_type_filter != "all":
            TYPE_KEYWORDS = {
                "id card": "id", "Invoice / Receipt": "invoice",
                "Marksheet / Result": "marksheet", "10th Marksheet": "10th",
                "12th Marksheet": "12th", "Semester Grade Card": "semester",
                "Bank Statement": "bank", "Resume / CV": "resume",
                "Legal Document": "legal", "Document": "",
            }
            kw = TYPE_KEYWORDS.get(doc_type_filter, doc_type_filter)
            if kw:
                query["extracted_fields.doc_type"] = {"$regex": kw, "$options": "i"}

        # Text search
        if search_term:
            s = re.escape(search_term)
            text_query = {"$or": [
                {"extracted_fields.name":        {"$regex": s, "$options": "i"}},
                {"extracted_fields.document_id": {"$regex": s, "$options": "i"}},
                {"extracted_fields.doc_type":    {"$regex": s, "$options": "i"}},
                {"extracted_fields.address":     {"$regex": s, "$options": "i"}},
                {"image_url":                    {"$regex": s, "$options": "i"}},
            ]}
            if query:
                query = {"$and": [query, text_query]}
            else:
                query = text_query

        results = list(col.find(query, {"_id": 0}).limit(limit))
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def search_by_document_id(doc_id_value: str) -> Optional[Dict[str, Any]]:
    """Exact search by document_id field (for fake detection)."""
    col = _docs()
    if col is None:
        return None
    try:
        doc = col.find_one(
            {"extracted_fields.document_id": {"$regex": f"^{re.escape(doc_id_value)}$", "$options": "i"}},
            {"_id": 0}
        )
        return doc
    except Exception as e:
        logger.error(f"search_by_document_id error: {e}")
        return None

def search_by_doc_type(doc_type_kw: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Return all documents of a given type (keyword search)."""
    col = _docs()
    if col is None:
        return []
    try:
        query = {}
        if doc_type_kw:
            query["extracted_fields.doc_type"] = {"$regex": re.escape(doc_type_kw), "$options": "i"}
        return list(col.find(query, {"_id": 0}).limit(limit))
    except Exception as e:
        logger.error(f"search_by_doc_type error: {e}")
        return []

def get_all_documents(limit: int = 500) -> List[Dict[str, Any]]:
    """Return all documents (for fuzzy fallback search)."""
    col = _docs()
    if col is None:
        return []
    try:
        return list(col.find({}, {"_id": 0}).sort("created_at", DESCENDING).limit(limit))
    except Exception as e:
        logger.error(f"get_all_documents error: {e}")
        return []

# ── USER AUTH helpers (used by auth.py) ────────────────────────────────────────
def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    col = _users()
    if col is None:
        return None
    try:
        return col.find_one({"email": email.lower()}, {"_id": 0})
    except Exception as e:
        logger.error(f"find_user_by_email error: {e}")
        return None

def create_user(email: str, password_hash: str) -> Optional[Dict[str, Any]]:
    col = _users()
    if col is None:
        return None
    try:
        user = {
            "id":            str(uuid.uuid4()),
            "email":         email.lower(),
            "password_hash": password_hash,
            "created_at":    datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        col.insert_one(user)
        col.create_index("email", unique=True)
        return user
    except Exception as e:
        logger.error(f"create_user error: {e}")
        return None
