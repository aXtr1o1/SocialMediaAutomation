from __future__ import annotations

import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase import get_supabase_auth_client
from app.services.auth_service import AuthService


bearer_scheme = HTTPBearer(
    auto_error=False,
)

_TOKEN_CACHE: dict[str, tuple[float, object]] = {}
_TOKEN_TTL_SECONDS = 120.0


def get_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
        )

    return credentials.credentials


def get_authenticated_supabase_user(
    access_token: Annotated[
        str,
        Depends(get_access_token),
    ],
):
    cached = _TOKEN_CACHE.get(access_token)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    supabase = get_supabase_auth_client()

    try:
        response = supabase.auth.get_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    try:
        AuthService().ensure_profile(UUID(str(response.user.id)), response.user)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create user profile",
        ) from exc

    _TOKEN_CACHE[access_token] = (time.monotonic() + _TOKEN_TTL_SECONDS, response.user)
    return response.user