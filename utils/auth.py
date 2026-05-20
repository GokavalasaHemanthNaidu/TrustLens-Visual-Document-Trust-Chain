# -*- coding: utf-8 -*-
"""
auth.py  ─  MongoDB-based authentication (replaces Supabase Auth)
Uses bcrypt for password hashing. No email verification required.
User object mimics Supabase user shape so app.py needs zero changes.
"""
import logging
import uuid
from typing import Tuple, Any, Optional
from dataclasses import dataclass

import bcrypt
from .db_client import find_user_by_email, create_user

logger = logging.getLogger(__name__)

# ── User object (same shape as Supabase user — keeps app.py unchanged) ─────────
@dataclass
class UserInfo:
    id:    str
    email: str

# ── AuthResult mimics Supabase auth response shape ─────────────────────────────
@dataclass
class AuthResult:
    user: UserInfo

# ── Helpers ────────────────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

# ── Public API (same signatures as old auth.py) ────────────────────────────────
def sign_up(email: str, password: str) -> Tuple[Optional[AuthResult], Optional[str]]:
    """Register a new user. Returns (AuthResult, None) or (None, error_str)."""
    email = email.strip().lower()
    if not email or not password:
        return None, "Email and password are required."
    if len(password) < 6:
        return None, "Password must be at least 6 characters."

    # Check if user already exists
    if find_user_by_email(email):
        return None, "An account with this email already exists. Please log in."

    pw_hash = _hash_password(password)
    user_doc = create_user(email, pw_hash)
    if not user_doc:
        return None, "Failed to create account. Please try again."

    logger.info(f"New user registered: {email}")
    return AuthResult(user=UserInfo(id=user_doc["id"], email=email)), None


def sign_in(email: str, password: str) -> Tuple[Optional[AuthResult], Optional[str]]:
    """Authenticate user. Returns (AuthResult, None) or (None, error_str)."""
    email = email.strip().lower()
    if not email or not password:
        return None, "Email and password are required."

    user_doc = find_user_by_email(email)
    if not user_doc:
        return None, "No account found with this email. Please sign up first."

    if not _check_password(password, user_doc.get("password_hash", "")):
        return None, "Incorrect password. Please try again."

    logger.info(f"User signed in: {email}")
    return AuthResult(user=UserInfo(id=user_doc["id"], email=email)), None


def reset_password(email: str) -> Tuple[bool, str]:
    """
    Password reset without email infrastructure.
    Prompts user to contact admin or set a new password directly.
    (Full email-reset requires an SMTP service — can be added later.)
    """
    email = email.strip().lower()
    user_doc = find_user_by_email(email)
    if not user_doc:
        return False, "No account found with this email."
    # NOTE: without SMTP, we just confirm the account exists.
    # To implement full reset: integrate SendGrid/Mailgun free tier.
    return True, ""


def sign_out() -> Tuple[bool, Optional[str]]:
    """Sign out — just clears session state (handled in app.py)."""
    logger.info("User signed out.")
    return True, None


def get_current_session() -> None:
    """Compatibility stub — session is stored in st.session_state.user."""
    return None
