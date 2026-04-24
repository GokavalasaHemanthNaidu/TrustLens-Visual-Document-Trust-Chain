from .db_client import supabase

def sign_up(email: str, password: str):
    """Registers a new user."""
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        return res, None
    except Exception as e:
        return None, str(e)

def sign_in(email: str, password: str):
    """Logs in an existing user."""
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception as e:
        return None, str(e)

def sign_out():
    """Logs out the current user."""
    try:
        res = supabase.auth.sign_out()
        return True, None
    except Exception as e:
        return False, str(e)

def get_current_session():
    """Gets the current authenticated session."""
    try:
        return supabase.auth.get_session()
    except:
        return None
