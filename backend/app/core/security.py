from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase import get_supabase_auth_client
from app.services.auth_service import AuthService


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def get_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


def get_authenticated_supabase_user(
    access_token: Annotated[str, Depends(get_access_token)],
) -> Any:
    """
    Validate the access token against Supabase on every request.

    Do not cache successful token validation here.

    A revoked access token must not remain usable for the duration of a
    local cache TTL after a password change or global sign-out.
    """

    try:
        response = get_supabase_auth_client().auth.get_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = getattr(response, "user", None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_authenticated_user(
    access_token: Annotated[str, Depends(get_access_token)],
) -> Any:
    """
    Return the authenticated application user/profile.

    Supabase Auth remains the source of truth for authentication while
    AuthService resolves the application's user profile.
    """

    try:
        response = get_supabase_auth_client().auth.get_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    auth_user = getattr(response, "user", None)

    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        service = AuthService()
        return service.ensure_profile(auth_user)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load authenticated user",
        ) from exc