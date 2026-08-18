from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
    )


@lru_cache
def get_supabase_auth_client() -> Client:
    """Client used for login/signup only; never reuse it for backend DB writes."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key.get_secret_value(),
    )
