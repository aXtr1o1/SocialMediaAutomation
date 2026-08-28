import httpx
from functools import lru_cache

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import get_settings

_POSTGREST_TIMEOUT_SECONDS = 30.0


def _build_httpx_client() -> httpx.Client:
    return httpx.Client(
        http2=False,
        timeout=httpx.Timeout(_POSTGREST_TIMEOUT_SECONDS),
    )


def _build_client_options() -> SyncClientOptions:
    return SyncClientOptions(
        postgrest_client_timeout=_POSTGREST_TIMEOUT_SECONDS,
        httpx_client=_build_httpx_client(),
    )


@lru_cache
def get_supabase_client() -> Client:
    """Service-role client for backend DB writes / admin Auth."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
        options=_build_client_options(),
    )


@lru_cache
def get_supabase_auth_client() -> Client:
    """Anon client for login/signup/OTP only; never reuse for backend DB writes."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key.get_secret_value(),
        options=_build_client_options(),
    )
