import logging
from typing import Tuple, Any, Optional
from .db_client import supabase

logger = logging.getLogger(__name__)

def sign_up(email: str, password: str) -> Tuple[Optional[Any], Optional[str]]:
    """Registers a new user."""
    if not supabase: return None, "Supabase client not initialized"
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        logger.info(f"Successfully signed up user: {email}")
        return res, None
    except Exception as e:
        logger.error(f"Sign up error for {email}: {e}")
        return None, str(e)

def sign_in(email: str, password: str) -> Tuple[Optional[Any], Optional[str]]:
    """Logs in an existing user."""
    if not supabase: return None, "Supabase client not initialized"
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        logger.info(f"Successfully signed in user: {email}")
        return res, None
    except Exception as e:
        logger.error(f"Sign in error for {email}: {e}")
        return None, str(e)

def sign_out() -> Tuple[bool, Optional[str]]:
    """Logs out the current user."""
    if not supabase: return False, "Supabase client not initialized"
    try:
        res = supabase.auth.sign_out()
        logger.info("Successfully signed out user.")
        return True, None
    except Exception as e:
        logger.error(f"Sign out error: {e}")
        return False, str(e)

def get_current_session() -> Optional[Any]:
    """Gets the current authenticated session from the global client. Use with caution in multi-user Streamlit apps."""
    if not supabase: return None
    try:
        return supabase.auth.get_session()
    except Exception as e:
        logger.warning(f"Error getting session: {e}")
        return None
