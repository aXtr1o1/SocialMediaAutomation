from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.security import (
    get_access_token,
    get_authenticated_supabase_user,
)
from app.core.supabase import get_supabase_auth_client
from app.models.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()

# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------
# Signup
# ---------------------------------------------------------

@router.post("/signup")
def signup(request: SignupRequest):
    """
    Create a new application user using Supabase Auth.
    """

    supabase = get_supabase_auth_client()

    try:
        response = supabase.auth.sign_up(
            {
                "email": request.email,
                "password": request.password,
            }
        )

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to create user",
            )

        return {
            "message": "User created successfully",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
            "session": response.session,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------
# Login
# ---------------------------------------------------------

@router.post("/login")
def login(request: LoginRequest):
    """
    Authenticate a user using Supabase Auth.
    """

    supabase = get_supabase_auth_client()

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": request.email,
                "password": request.password,
            }
        )

        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        return {
            "message": "Login successful",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": response.session.expires_in,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc


# ---------------------------------------------------------
# Current authenticated user
# ---------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user(
    auth_user=Depends(get_authenticated_supabase_user),
):
    service = AuthService()

    try:
        user_id = auth_user.id
    except AttributeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user",
        ) from exc

    return service.get_profile(user_id)


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------

@router.post("/logout")
def logout(
    access_token: Annotated[str, Depends(get_access_token)],
):
    """
    Revoke the caller's current Supabase session.

    The access token remains valid until its configured expiry, but the
    refresh token for this session is revoked immediately.
    """

    supabase = get_supabase_auth_client()

    try:
        supabase.auth.admin.sign_out(
            access_token,
            scope="local",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to sign out from Supabase",
        ) from exc

    return {
        "message": "Signed out successfully"
    }
