from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.security import (
    get_access_token,
    get_authenticated_supabase_user,
)
from app.core.supabase import get_supabase_auth_client, get_supabase_client
from app.models.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()

# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
    )


class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=1,
    )
    password: str


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)


class ResetPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    otp: str = Field(min_length=4, max_length=12)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class ProfileUpdateRequest(BaseModel):
    first_name: str = Field(
        min_length=1,
    )
    last_name: str = Field(
        min_length=1,
    )
    username: str = Field(
        min_length=1,
    )


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

        AuthService().ensure_profile(response.user.id, response.user)

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
    Authenticate a user using username or email via Supabase Auth.
    """

    supabase = get_supabase_auth_client()

    try:
        email = AuthService().resolve_login_email(request.identifier)

        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": request.password,
            }
        )

        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
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
            detail="Invalid username/email or password",
        ) from exc


# ---------------------------------------------------------
# Forgot / reset password (email OTP via Supabase SMTP)
# ---------------------------------------------------------

GENERIC_RESET_MESSAGE = (
    "If an account exists for that username or email, we sent a one-time code."
)


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest):
    """
    Send a recovery OTP to the account email (Supabase Auth + SMTP).

    Always returns a generic message so callers cannot probe for accounts.
    """
    from app.core.config import get_settings

    supabase = get_supabase_auth_client()
    settings = get_settings()
    email = AuthService().find_login_email(request.identifier)

    if email:
        try:
            supabase.auth.reset_password_for_email(
                email,
                {
                    "redirect_to": f"{settings.frontend_url.rstrip('/')}/signin",
                },
            )
            print(f"forgot_password: recovery email requested for {email}")
        except Exception as exc:
            print("forgot_password error:", type(exc).__name__, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Could not send the reset email. Check Supabase Auth SMTP settings "
                    "and the Reset password email template."
                ),
            ) from exc

    return {"message": GENERIC_RESET_MESSAGE}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest):
    """
    Verify the recovery OTP, then set a new password in Supabase Auth.
    """
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    otp = "".join(ch for ch in request.otp.strip() if ch.isalnum())
    if len(otp) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter the one-time code from your email",
        )

    email = AuthService().find_login_email(request.identifier)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code. Request a new one and try again.",
        )

    supabase = get_supabase_auth_client()

    try:
        verified = supabase.auth.verify_otp(
            {
                "email": email,
                "token": otp,
                "type": "recovery",
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code. Request a new one and try again.",
        ) from exc

    if verified.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code. Request a new one and try again.",
        )

    try:
        updated = supabase.auth.update_user({"password": request.password})
        if updated.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not update password. Try again.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update password. Try a different password.",
        ) from exc
    finally:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

    return {"message": "Password updated. You can sign in with your new password."}


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    auth_user=Depends(get_authenticated_supabase_user),
):
    """
    Change password for the signed-in user after verifying the current password.
    Updates Supabase Auth only (not public.users).
    """
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    if request.new_password == request.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    email = str(getattr(auth_user, "email", "") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no email password login.",
        )

    supabase = get_supabase_auth_client()
    try:
        verified = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": request.current_password,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        ) from exc

    if verified.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    try:
        get_supabase_client().auth.admin.update_user_by_id(
            str(auth_user.id),
            {"password": request.new_password},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update password. Try a different password.",
        ) from exc

    return {"message": "Password updated."}


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

    service.ensure_profile(user_id, auth_user)
    try:
        service.update_last_login(user_id)
    except Exception as exc:
        # Last-login timestamp is non-critical; do not fail /auth/me on transient DB errors.
        print("AuthService.update_last_login warning:", exc)
    return service.get_profile(user_id)


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_current_user(
    payload: ProfileUpdateRequest,
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

    return service.update_profile(
        user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
    )


# ---------------------------------------------------------
# Logout
# ----------------------------------------------------- ----

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
