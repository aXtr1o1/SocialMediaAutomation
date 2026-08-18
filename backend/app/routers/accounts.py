from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.security import get_authenticated_supabase_user
from app.services.account_service import AccountService
from app.services.linkedin_service import LinkedInService
from app.services.bluesky_service import (
    BlueskyService,
    BlueskyOAuthSession,
)


router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


_pending_linkedin_states: dict[str, UUID] = {}
_pending_bluesky_states: dict[
    str,
    tuple[UUID, BlueskyOAuthSession],
] = {}


# ============================================================
# LinkedIn
# ============================================================

@router.get("/linkedin/connect")
async def connect_linkedin(
    current_user=Depends(get_authenticated_supabase_user),
):
    linkedin_service = LinkedInService()

    state = linkedin_service.create_state()

    _pending_linkedin_states[state] = UUID(current_user.id)

    authorization_url = (
        linkedin_service.build_authorization_url(state)
    )

    return {
        "authorization_url": authorization_url,
        "state": state,
    }


@router.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    state: str,
):
    user_id = _pending_linkedin_states.pop(state, None)

    if user_id is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state",
        )

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
        saved_account = account_service.save_connected_account(
            user_id=user_id,
            platform_name=settings.linkedin_platform_name,
            account_name=account_name,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=token_data.get("expires_at"),
            provider_user_id=provider_user_id,
            provider_handle=None,
            oauth_endpoint=LinkedInService.USERINFO_URL,
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

    return {
        "message": "LinkedIn account connected successfully",
        "account": {
            "id": saved_account.get("id"),
            "platform_id": saved_account.get("platform_id"),
            "account_name": saved_account.get("account_name"),
            "provider_user_id": saved_account.get("provider_user_id"),
            "provider_handle": saved_account.get("provider_handle"),
            "token_expiry": saved_account.get("token_expiry"),
            "is_enabled": saved_account.get("is_enabled"),
        },
    }


# ============================================================
# Bluesky
# ============================================================

@router.get("/bluesky/connect")
async def connect_bluesky(
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

        _pending_bluesky_states[oauth_session.state] = (
            UUID(current_user.id),
            oauth_session,
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

    # ---------------------------------------------------------
    # 1. Retrieve pending OAuth session
    # ---------------------------------------------------------

    pending = _pending_bluesky_states.pop(state, None)

    if pending is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired Bluesky OAuth state",
        )

    user_id, oauth_session = pending

    # ---------------------------------------------------------
    # 2. Handle OAuth failure
    # ---------------------------------------------------------

    if error:
        detail = error_description or error

        raise HTTPException(
            status_code=400,
            detail=f"Bluesky OAuth authorization failed: {detail}",
        )

    # ---------------------------------------------------------
    # 3. Validate authorization code
    # ---------------------------------------------------------

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
        # -----------------------------------------------------
        # 4. Exchange authorization code for tokens
        # -----------------------------------------------------

        token_data = await bluesky_service.exchange_code(
            code=code,
            session=oauth_session,
            issuer=iss,
        )

        # -----------------------------------------------------
        # 5. Get Bluesky account information
        # -----------------------------------------------------

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

    # ---------------------------------------------------------
    # 6. Extract Bluesky account information
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 7. Save connected account
    # ---------------------------------------------------------

    account_service = AccountService()

    try:
        saved_account = account_service.save_connected_account(
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

    # ---------------------------------------------------------
    # 8. Successful response
    # ---------------------------------------------------------

    return {
        "message": "Bluesky account connected successfully",
        "account": {
            "id": saved_account.get("id"),
            "platform_id": saved_account.get("platform_id"),
            "account_name": saved_account.get("account_name"),
            "provider_user_id": saved_account.get("provider_user_id"),
            "provider_handle": saved_account.get("provider_handle"),
            "token_expiry": saved_account.get("token_expiry"),
            "is_enabled": saved_account.get("is_enabled"),
        },
    }

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

    accounts = service.get_user_accounts(
        UUID(current_user.id)
    )

    return accounts
