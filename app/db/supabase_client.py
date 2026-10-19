import os
from supabase import create_client, Client

def get_supabase() -> Client:
    """Return a Supabase client configured from environment variables.
    Requires SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase environment variables not set (SUPABASE_URL and key)")
    return create_client(url, key)
