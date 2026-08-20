import base64
import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.services.auth_service import AuthService


class AccountService:

    def __init__(self):
        self.supabase = get_supabase_client()
        secret = get_settings().secret_key.get_secret_value()
        encryption_key = base64.urlsafe_b64encode(
            hashlib.sha256(secret.encode("utf-8")).digest()
        )
        self._token_cipher = Fernet(encryption_key)

    def _encrypt_token(self, token: str) -> str:
        return self._token_cipher.encrypt(
            token.encode("utf-8")
        ).decode("utf-8")

    def _decrypt_token(self, encrypted_token: str) -> str:
        return self._token_cipher.decrypt(
            encrypted_token.encode("utf-8")
        ).decode("utf-8")

    def get_platform_id(self, platform_name: str) -> UUID:

        response = (
            self.supabase
            .table("platforms")
            .select("id")
            .eq("platform_name", platform_name)
            .limit(1)
            .execute()
        )

        print("========== PLATFORM QUERY ==========")
        print("platform_name:", platform_name)
        print("response:", response)
        print("response.data:", response.data)
        print("====================================")

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Platform '{platform_name}' is not configured",
            )

        return UUID(response.data[0]["id"])

    def get_status_id(self, status_name: str) -> UUID:
        response = (
            self.supabase
            .table("statuses")
            .select("id")
            .eq("status_name", status_name)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Connection status '{status_name}' "
                    "is not configured"
                ),
            )

        return UUID(response.data[0]["id"])

    def save_connected_account(
        self,
        user_id: UUID,
        platform_name: str,
        account_name: str,
        access_token: str,
        refresh_token: str | None,
        token_expiry,
        provider_user_id: str | None = None,
        provider_handle: str | None = None,
        oauth_endpoint: str | None = None,
        scopes: str | None = None,
        account_type: str = "oauth",
    ) -> dict[str, Any]:

        # ---------------------------------------------------------
        # 1. Get LinkedIn platform ID
        # ---------------------------------------------------------

        platform_id = self.get_platform_id(platform_name)
        active_status_id = self.get_status_id("active")

        AuthService().ensure_profile(user_id)

        print("========== PLATFORM ID ==========")
        print("platform_name:", platform_name)
        print("platform_id:", platform_id)
        print("=================================")

        # ---------------------------------------------------------
        # 2. Check whether account already exists
        # ---------------------------------------------------------

        existing_response = (
            self.supabase
            .table("connected_accounts")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("platform_id", str(platform_id))
            .limit(1)
            .execute()
        )

        print("========== EXISTING ACCOUNT QUERY ==========")
        print("response:", existing_response)
        print("response.data:", existing_response.data)
        print("============================================")

        now = datetime.now(timezone.utc).isoformat()

        account_data = {
            "user_id": str(user_id),
            "platform_id": str(platform_id),
            "connection_status_id": str(active_status_id),
            "account_name": account_name,
            "access_token_encrypted": self._encrypt_token(access_token),
            "refresh_token": (
                self._encrypt_token(refresh_token)
                if refresh_token
                else None
            ),
            "token_expiry": token_expiry,
            "provider_user_id": provider_user_id,
            "provider_handle": provider_handle,
            "oauth_endpoint": oauth_endpoint,
            "scopes": scopes,
            "account_type": account_type,
            "updated_at": now,
            "is_enabled": True,
        }

        print("========== ACCOUNT DATA ==========")
        print({
            **account_data,
            "access_token_encrypted": "***",
            "refresh_token": "***",
        })
        print("==================================")

        # ---------------------------------------------------------
        # 3. Update existing account
        # ---------------------------------------------------------

        if existing_response.data:

            existing_id = existing_response.data[0]["id"]

            print("Updating existing account:", existing_id)

            response = (
                self.supabase
                .table("connected_accounts")
                .update(account_data)
                .eq("id", existing_id)
                .execute()
            )

        # ---------------------------------------------------------
        # 4. Insert new account
        # ---------------------------------------------------------

        else:

            print("No existing account found.")
            print("Inserting new connected account...")

            response = (
                self.supabase
                .table("connected_accounts")
                .insert({
                    **account_data,
                    "connected_at": now,
                })
                .execute()
            )

        print("========== SAVE RESPONSE ==========")
        print("response:", response)
        print("response.data:", response.data)
        print("===================================")

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to save connected account",
            )

        return response.data[0]

    def get_user_accounts(
        self,
        user_id: UUID,
    ) -> list[dict[str, Any]]:

        response = (
            self.supabase
            .table("connected_accounts")
            .select(
                """
                id,
                account_name,
                account_type,
                provider_user_id,
                provider_handle,
                oauth_endpoint,
                scopes,
                connected_at,
                token_expiry,
                last_synced_at,
                is_enabled,
                is_default,
                platform_id
                """
            )
            .eq("user_id", str(user_id))
            .is_("deleted_at", "null")
            .execute()
        )

        accounts = response.data or []
        platform_ids = [
            account["platform_id"]
            for account in accounts
            if account.get("platform_id")
        ]

        platform_names: dict[str, str] = {}

        if platform_ids:
            platforms_response = (
                self.supabase
                .table("platforms")
                .select("id, platform_name")
                .in_("id", platform_ids)
                .execute()
            )

            platform_names = {
                platform["id"]: platform["platform_name"]
                for platform in (platforms_response.data or [])
            }

        for account in accounts:
            platform_name = platform_names.get(account.get("platform_id"))
            account["platform"] = (
                {"platform_name": platform_name}
                if platform_name
                else None
            )

        return accounts

    def disconnect_account(self, user_id: UUID, account_id: UUID) -> None:
        now = datetime.now(timezone.utc).isoformat()

        response = (
            self.supabase
            .table("connected_accounts")
            .update(
                {
                    "deleted_at": now,
                    "is_enabled": False,
                    "updated_at": now,
                }
            )
            .eq("id", str(account_id))
            .eq("user_id", str(user_id))
            .is_("deleted_at", "null")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected account not found",
            )
