from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.security import get_authenticated_supabase_user
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.bluesky_service import BlueskyService
from app.services.linkedin_service import LinkedInService
from app.services.oauth_state_service import OAuthStateService


# ---------------------------------------------------------------------------
# Router configuration
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _normalize_oauth_intent(intent: str | None) -> str:
    """
    Normalize the OAuth connection intent.

    Supported values:
        - add
        - reconnect

    Invalid or missing values default to add.
    """

    normalized_intent = (
        intent.strip().lower()
        if isinstance(intent, str)
        else "add"
    )

    if normalized_intent not in {"add", "reconnect"}:
        return "add"

    return normalized_intent


def _get_current_user_id(current_user: Any) -> UUID:
    """Convert the authenticated Supabase user ID to UUID."""

    try:
        return UUID(str(current_user.id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Invalid authenticated user ID",
        ) from exc


def _frontend_accounts_redirect(
    *,
    connected: str | None = None,
    saved: str | None = None,
    conflict: bool = False,
    error: str | None = None,
) -> RedirectResponse:
    """
    Redirect the browser back to the connected accounts page.

    Optional query parameters are included to communicate the OAuth result
    to the frontend.
    """

    settings = get_settings()

    frontend_url = (
        f"{settings.frontend_url.rstrip('/')}/connected-accounts"
    )

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
        frontend_url = (
            f"{frontend_url}?{urlencode(params)}"
        )

    return RedirectResponse(
        url=frontend_url,
    )


def _oauth_save_redirect(
    platform: str,
    save_result: dict[str, Any],
) -> RedirectResponse:
    """
    Build the frontend redirect after saving a connected account.
    """

    if save_result.get("was_activated"):
        return _frontend_accounts_redirect(
            connected=platform,
        )

    return _frontend_accounts_redirect(
        saved=platform,
        conflict=True,
    )


def _oauth_error_detail(exc: HTTPException) -> str:
    """Extract a safe string error message from an HTTPException."""

    if isinstance(exc.detail, str):
        return exc.detail

    return "Account connection failed"


# ---------------------------------------------------------------------------
# LinkedIn OAuth
# ---------------------------------------------------------------------------

@router.get("/linkedin/connect")
async def connect_linkedin(
    intent: str = "add",
    current_user=Depends(get_authenticated_supabase_user),
) -> dict[str, str]:
    """
    Start the LinkedIn OAuth connection flow.
    """

    user_id = _get_current_user_id(current_user)
    normalized_intent = _normalize_oauth_intent(intent)

    linkedin_service = LinkedInService()

    state = linkedin_service.create_state()

    OAuthStateService().save_linkedin_state(
        state=state,
        user_id=user_id,
        intent=normalized_intent,
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
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """
    Handle the LinkedIn OAuth callback.
    """

    try:
        # ---------------------------------------------------------------
        # Validate OAuth callback
        # ---------------------------------------------------------------

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

        # ---------------------------------------------------------------
        # Retrieve and consume OAuth state
        # ---------------------------------------------------------------

        pending = OAuthStateService().consume_linkedin_state(state)

        if pending is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state",
            )

        user_id, _intent = pending

        # ---------------------------------------------------------------
        # Exchange authorization code
        # ---------------------------------------------------------------

        linkedin_service = LinkedInService()
        settings = get_settings()

        try:
            token_data = await linkedin_service.exchange_code(
                code,
            )

            user_info = await linkedin_service.get_user_info(
                token_data["access_token"],
            )

        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="LinkedIn OAuth failed",
            ) from exc

        # ---------------------------------------------------------------
        # Validate LinkedIn user information
        # ---------------------------------------------------------------

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

        # ---------------------------------------------------------------
        # Save connected account
        # ---------------------------------------------------------------

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
            raise HTTPException(
                status_code=500,
                detail="Unable to save LinkedIn connected account",
            ) from exc

        return _oauth_save_redirect(
            "linkedin",
            save_result,
        )

    except HTTPException as exc:
        return _frontend_accounts_redirect(
            error=_oauth_error_detail(exc),
        )


# ---------------------------------------------------------------------------
# Bluesky OAuth
# ---------------------------------------------------------------------------

@router.get("/bluesky/connect")
async def connect_bluesky(
    intent: str = "add",
    current_user=Depends(get_authenticated_supabase_user),
) -> dict[str, str]:
    """
    Start the Bluesky OAuth connection flow.
    """

    user_id = _get_current_user_id(current_user)
    normalized_intent = _normalize_oauth_intent(intent)

    bluesky_service = BlueskyService()

    try:
        authorization_url, oauth_session = (
            await bluesky_service.create_authorization_request()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to start Bluesky OAuth",
        ) from exc

    OAuthStateService().save_bluesky_state(
        state=oauth_session.state,
        user_id=user_id,
        intent=normalized_intent,
        session=oauth_session,
    )

    return {
        "authorization_url": authorization_url,
        "state": oauth_session.state,
    }


@router.get("/bluesky/callback")
async def bluesky_callback(
    state: str,
    code: str | None = None,
    iss: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """
    Handle the Bluesky OAuth callback.
    """

    try:
        # ---------------------------------------------------------------
        # Retrieve and consume OAuth state
        # ---------------------------------------------------------------

        pending = OAuthStateService().consume_bluesky_state(state)

        if pending is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired Bluesky OAuth state",
            )

        user_id, oauth_session, _intent = pending

        # ---------------------------------------------------------------
        # Validate OAuth callback
        # ---------------------------------------------------------------

        if error:
            detail = error_description or error

            raise HTTPException(
                status_code=400,
                detail=(
                    "Bluesky OAuth authorization failed: "
                    f"{detail}"
                ),
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

        # ---------------------------------------------------------------
        # Exchange authorization code
        # ---------------------------------------------------------------

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
            raise HTTPException(
                status_code=502,
                detail="Bluesky OAuth token exchange failed",
            ) from exc

        # ---------------------------------------------------------------
        # Validate Bluesky user information
        # ---------------------------------------------------------------

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

        # ---------------------------------------------------------------
        # Save connected account
        # ---------------------------------------------------------------

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
                drop_private_key_pem=oauth_session.dpop_private_key_pem
            )

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to save Bluesky connected account",
            ) from exc

        return _oauth_save_redirect(
            "bluesky",
            save_result,
        )

    except HTTPException as exc:
        return _frontend_accounts_redirect(
            error=_oauth_error_detail(exc),
        )


# ---------------------------------------------------------------------------
# Connected accounts
# ---------------------------------------------------------------------------

@router.get("")
async def get_connected_accounts(
    current_user=Depends(get_authenticated_supabase_user),
):
    """
    Return all connected accounts for the authenticated user.
    """

    user_id = _get_current_user_id(current_user)

    # Authentication normally ensures the profile already exists.
    # Keep this explicit because the existing Account/Auth workflow
    # currently relies on profile synchronization here as well.
    AuthService().ensure_profile(
        user_id,
        current_user,
    )

    service = AccountService()

    return service.get_user_accounts(user_id)


@router.post("/{account_id}/activate")
async def activate_connected_account(
    account_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    """
    Activate a connected social media account.
    """

    user_id = _get_current_user_id(current_user)

    service = AccountService()

    return service.activate_account(
        user_id,
        account_id,
    )


@router.delete("/{account_id}/permanent")
async def permanently_delete_connected_account(
    account_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    """
    Permanently delete a connected social media account.
    """

    user_id = _get_current_user_id(current_user)

    service = AccountService()

    service.delete_account(
        user_id,
        account_id,
    )

    return {
        "message": "Account deleted",
    }


@router.delete("/{account_id}")
async def disconnect_connected_account(
    account_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    """
    Disconnect a social media account without permanently deleting it.
    """

    user_id = _get_current_user_id(current_user)

    service = AccountService()

    service.disconnect_account(
        user_id,
        account_id,
    )

    return {
        "message": "Account disconnected",
    }