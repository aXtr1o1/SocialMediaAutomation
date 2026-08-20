from typing import Optional
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.security import get_authenticated_supabase_user
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.linkedin_service import LinkedInService
from app.services.bluesky_service import (
    BlueskyService,
    BlueskyOAuthSession,
)

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)

_pending_linkedin_states: dict[str, tuple[UUID, str]] = {}
_pending_bluesky_states: dict[
    str,
    tuple[UUID, BlueskyOAuthSession, str],
] = {}


def _frontend_accounts_redirect(
    *,
    connected: str | None = None,
    saved: str | None = None,
    conflict: bool = False,
    error: str | None = None,
) -> RedirectResponse:
    settings = get_settings()
    url = f"{settings.frontend_url.rstrip('/')}/connected-accounts"
    params: dict[str, str] = {}

    if connected:
        params["connected"] = connected
    if saved:
        params["saved"] = saved
    if conflict:
        params["conflict"] = "1"
    if error:
        params["error"] = error[:200]

    if params:
        return RedirectResponse(f"{url}?{urlencode(params)}")

    return RedirectResponse(url)


def _oauth_save_redirect(platform: str, save_result: dict) -> RedirectResponse:
    if save_result.get("was_activated"):
        return _frontend_accounts_redirect(connected=platform)

    return _frontend_accounts_redirect(saved=platform, conflict=True)


def _oauth_error_detail(exc: HTTPException) -> str:
    if isinstance(exc.detail, str):
        return exc.detail
    return "Account connection failed"


# ============================================================
# LinkedIn
# ============================================================

@router.get("/linkedin/connect")
async def connect_linkedin(
    intent: str = "add",
    current_user=Depends(get_authenticated_supabase_user),
):
    linkedin_service = LinkedInService()

    state = linkedin_service.create_state()

    normalized_intent = (
        intent.strip().lower()
        if isinstance(intent, str)
        else "add"
    )
    if normalized_intent not in {"add", "reconnect"}:
        normalized_intent = "add"

    _pending_linkedin_states[state] = (
        UUID(current_user.id),
        normalized_intent,
    )

    authorization_url = (
        linkedin_service.build_authorization_url(state)
    )

    return {
        "authorization_url": authorization_url,
        "state": state,
    }


@router.get("/linkedin/callback")
async def linkedin_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    try:
        if error:
            raise HTTPException(
                status_code=400,
                detail=error_description or error,
            )

        if not state:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state",
            )

        if not code:
            raise HTTPException(
                status_code=400,
                detail="LinkedIn authorization code was not returned",
            )

        pending = _pending_linkedin_states.pop(state, None)

        if pending is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state",
            )
        user_id, intent = pending

        linkedin_service = LinkedInService()
        settings = get_settings()

        try:
            token_data = await linkedin_service.exchange_code(code)

            user_info = await linkedin_service.get_user_info(
                token_data["access_token"]
            )

        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="LinkedIn OAuth failed",
            ) from exc

        provider_user_id = user_info.get("sub")
        account_name = user_info.get("name")

        if not provider_user_id:
            raise HTTPException(
                status_code=502,
                detail="LinkedIn user ID was not returned",
            )

        if not account_name:
            raise HTTPException(
                status_code=502,
                detail="LinkedIn account name was not returned",
            )

        account_service = AccountService()

        try:
            save_result = account_service.save_connected_account(
                user_id=user_id,
                platform_name=settings.linkedin_platform_name,
                account_name=account_name,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expiry=token_data.get("expires_at"),
                provider_user_id=provider_user_id,
                provider_handle=None,
                oauth_endpoint=settings.linkedin_userinfo_url,
                scopes=token_data.get("scope"),
            )

        except Exception as exc:
            print("========== LINKEDIN SAVE ERROR ==========")
            print(type(exc).__name__)
            print(str(exc))
            print("==========================================")

            raise HTTPException(
                status_code=500,
                detail="Unable to save LinkedIn connected account",
            ) from exc

        return _oauth_save_redirect("linkedin", save_result)

    except HTTPException as exc:
        return _frontend_accounts_redirect(error=_oauth_error_detail(exc))


# ============================================================
# Bluesky
# ============================================================

@router.get("/bluesky/connect")
async def connect_bluesky(
    intent: str = "add",
    current_user=Depends(get_authenticated_supabase_user),
):
    """
    Start Bluesky OAuth connection for the authenticated
    application user.
    """

    bluesky_service = BlueskyService()

    try:
        # -----------------------------------------------------
        # Create Bluesky OAuth authorization request
        # -----------------------------------------------------

        authorization_url, oauth_session = (
            await bluesky_service.create_authorization_request()
        )

        # -----------------------------------------------------
        # Store user + OAuth session
        # -----------------------------------------------------

        normalized_intent = (
            intent.strip().lower()
            if isinstance(intent, str)
            else "add"
        )
        if normalized_intent not in {"add", "reconnect"}:
            normalized_intent = "add"

        _pending_bluesky_states[oauth_session.state] = (
            UUID(current_user.id),
            oauth_session,
            normalized_intent,
        )

    except Exception as exc:
        print("========== BLUESKY CONNECT ERROR ==========")
        print(type(exc).__name__)
        print(str(exc))
        print("============================================")

        raise HTTPException(
            status_code=502,
            detail="Unable to start Bluesky OAuth",
        ) from exc

    return {
        "authorization_url": authorization_url,
        "state": oauth_session.state,
    }


@router.get("/bluesky/callback")
async def bluesky_callback(
    state: str,
    code: Optional[str] = None,
    iss: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Handle Bluesky OAuth callback.
    """

    try:
        pending = _pending_bluesky_states.pop(state, None)

        if pending is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired Bluesky OAuth state",
            )

        user_id, oauth_session, intent = pending

        if error:
            detail = error_description or error

            raise HTTPException(
                status_code=400,
                detail=f"Bluesky OAuth authorization failed: {detail}",
            )

        if not code:
            raise HTTPException(
                status_code=400,
                detail="Bluesky authorization code was not returned",
            )

        if not iss:
            raise HTTPException(
                status_code=400,
                detail="Bluesky OAuth issuer was not returned",
            )

        bluesky_service = BlueskyService()
        settings = get_settings()

        try:
            token_data = await bluesky_service.exchange_code(
                code=code,
                session=oauth_session,
                issuer=iss,
            )

            user_info = await bluesky_service.get_user_info(
                did=token_data["sub"],
            )

        except Exception as exc:
            print("========== BLUESKY CALLBACK ERROR ==========")
            print(type(exc).__name__)
            print(str(exc))
            print("=============================================")

            raise HTTPException(
                status_code=502,
                detail="Bluesky OAuth token exchange failed",
            ) from exc

        provider_user_id = user_info.get("did")
        account_name = (
            user_info.get("display_name")
            or user_info.get("handle")
        )
        provider_handle = user_info.get("handle")

        if not provider_user_id:
            raise HTTPException(
                status_code=502,
                detail="Bluesky user DID was not returned",
            )

        if not account_name:
            raise HTTPException(
                status_code=502,
                detail="Bluesky account name was not returned",
            )

        account_service = AccountService()

        try:
            save_result = account_service.save_connected_account(
                user_id=user_id,
                platform_name=settings.bluesky_platform_name,
                account_name=account_name,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expiry=token_data.get("expires_at"),
                provider_user_id=provider_user_id,
                provider_handle=provider_handle,
                oauth_endpoint=oauth_session.issuer,
                scopes=token_data.get("scope"),
            )

        except Exception as exc:
            print("========== BLUESKY SAVE ERROR ==========")
            print(type(exc).__name__)
            print(str(exc))
            print("=========================================")

            raise HTTPException(
                status_code=500,
                detail="Unable to save Bluesky connected account",
            ) from exc

        return _oauth_save_redirect("bluesky", save_result)

    except HTTPException as exc:
        return _frontend_accounts_redirect(error=_oauth_error_detail(exc))

# ============================================================
# Connected accounts
# ============================================================

@router.get("")
async def get_connected_accounts(
    current_user=Depends(get_authenticated_supabase_user),
):
    """
    Get all connected social media accounts belonging
    to the authenticated application user.
    """

    service = AccountService()
    AuthService().ensure_profile(UUID(current_user.id), current_user)

    accounts = service.get_user_accounts(
        UUID(current_user.id)
    )

    return accounts


@router.post("/{account_id}/activate")
async def activate_connected_account(
    account_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    service = AccountService()
    account = service.activate_account(UUID(current_user.id), account_id)

    return account


@router.delete("/{account_id}/permanent")
async def permanently_delete_connected_account(
    account_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    service = AccountService()
    service.delete_account(UUID(current_user.id), account_id)

    return {
        "message": "Account deleted",
    }


@router.delete("/{account_id}")
async def disconnect_connected_account(
    account_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    service = AccountService()
    service.disconnect_account(UUID(current_user.id), account_id)

    return {
        "message": "Account disconnected",
    }
