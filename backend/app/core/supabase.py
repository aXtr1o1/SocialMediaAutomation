import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    httpx_client = httpx.Client(
        http2=False,
        timeout=httpx.Timeout(30.0),
    )

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
        options=SyncClientOptions(
            postgrest_client_timeout=30,
            httpx_client=httpx_client,
        ),
    )


def get_supabase_auth_client() -> Client:
    """Client used for login/signup only; never reuse it for backend DB writes."""
    settings = get_settings()
    httpx_client = httpx.Client(
        http2=False,
        timeout=httpx.Timeout(30.0),
    )
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key.get_secret_value(),
        options=SyncClientOptions(
            postgrest_client_timeout=30,
            httpx_client=httpx_client,
        ),
    )
