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


_ACCOUNT_PUBLIC_COLUMNS = """
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

    def _matching_account_query(
        self,
        *,
        user_id: UUID,
        platform_id: UUID,
        provider_user_id: str | None,
        provider_handle: str | None,
    ):
        query = (
            self.supabase
            .table("connected_accounts")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("platform_id", str(platform_id))
        )

        if provider_user_id:
            query = query.eq("provider_user_id", provider_user_id)
        elif provider_handle:
            query = query.eq("provider_handle", provider_handle)

        return query

    def _attach_platforms(self, accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def _public_account(self, account: dict[str, Any]) -> dict[str, Any]:
        public = {
            key: account.get(key)
            for key in (
                "id",
                "account_name",
                "account_type",
                "provider_user_id",
                "provider_handle",
                "oauth_endpoint",
                "scopes",
                "connected_at",
                "token_expiry",
                "last_synced_at",
                "is_enabled",
                "is_default",
                "platform_id",
            )
        }
        return self._attach_platforms([public])[0]

    def get_enabled_account_for_platform(
        self,
        *,
        user_id: UUID,
        platform_id: UUID,
        exclude_account_id: str | None = None,
    ) -> dict[str, Any] | None:
        response = (
            self.supabase
            .table("connected_accounts")
            .select(_ACCOUNT_PUBLIC_COLUMNS)
            .eq("user_id", str(user_id))
            .eq("platform_id", str(platform_id))
            .eq("is_enabled", True)
            .execute()
        )

        accounts = response.data or []

        if exclude_account_id:
            accounts = [
                account
                for account in accounts
                if account.get("id") != exclude_account_id
            ]

        if not accounts:
            return None

        return self._attach_platforms(accounts)[0]

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

        platform_id = self.get_platform_id(platform_name)
        active_status_id = self.get_status_id("active")

        AuthService().ensure_profile(user_id)

        existing_response = (
            self._matching_account_query(
                user_id=user_id,
                platform_id=platform_id,
                provider_user_id=provider_user_id,
                provider_handle=provider_handle,
            )
            .limit(1)
            .execute()
        )

        existing_id = (
            existing_response.data[0]["id"]
            if existing_response.data
            else None
        )

        enabled_account = self.get_enabled_account_for_platform(
            user_id=user_id,
            platform_id=platform_id,
        )

        should_enable = True
        conflict_account = None

        if enabled_account and enabled_account.get("id") != existing_id:
            should_enable = False
            conflict_account = enabled_account

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
            "is_deleted": None,
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

        if existing_id:
            response = (
                self.supabase
                .table("connected_accounts")
                .update(account_data)
                .eq("id", existing_id)
                .execute()
            )
        else:
            response = (
                self.supabase
                .table("connected_accounts")
                .insert({
                    **account_data,
                    "connected_at": now,
                })
                .execute()
            )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to save connected account",
            )

        saved_account = response.data[0]

        if provider_user_id or provider_handle:
            duplicate_response = (
                self._matching_account_query(
                    user_id=user_id,
                    platform_id=platform_id,
                    provider_user_id=provider_user_id,
                    provider_handle=provider_handle,
                )
                .execute()
            )

            duplicate_ids = [
                row["id"]
                for row in (duplicate_response.data or [])
                if row.get("id") and row["id"] != saved_account["id"]
            ]

            if duplicate_ids:
                dedupe_time = datetime.now(timezone.utc).isoformat()

                for duplicate_id in duplicate_ids:
                    self.supabase.table("connected_accounts").update(
                        {
                            "is_enabled": False,
                            "updated_at": dedupe_time,
                            "deleted_at": None,
                        }
                    ).eq("id", duplicate_id).eq(
                        "user_id",
                        str(user_id),
                    ).execute()

        return {
            "account": self._public_account(saved_account),
            "was_activated": bool(saved_account.get("is_enabled")),
            "active_account": conflict_account,
        }

    def get_user_accounts(
        self,
        user_id: UUID,
    ) -> list[dict[str, Any]]:

        response = (
            self.supabase
            .table("connected_accounts")
            .select(_ACCOUNT_PUBLIC_COLUMNS)
            .eq("user_id", str(user_id))
            .execute()
        )

        accounts = self._attach_platforms(response.data or [])
        accounts.sort(
            key=lambda account: (
                not bool(account.get("is_enabled")),
                (account.get("account_name") or "").lower(),
            )
        )
        return accounts

    def disconnect_account(self, user_id: UUID, account_id: UUID) -> None:
        now = datetime.now(timezone.utc).isoformat()

        response = (
            self.supabase
            .table("connected_accounts")
            .update(
                {
                    "deleted_at": None,
                    "is_enabled": False,
                    "updated_at": now,
                }
            )
            .eq("id", str(account_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected account not found",
            )

    def activate_account(self, user_id: UUID, account_id: UUID) -> dict[str, Any]:
        response = (
            self.supabase
            .table("connected_accounts")
            .select(_ACCOUNT_PUBLIC_COLUMNS)
            .eq("id", str(account_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected account not found",
            )

        account = self._attach_platforms(response.data)[0]
        platform_id = account.get("platform_id")

        if not platform_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account platform is not configured",
            )

        if account.get("is_enabled"):
            return account

        token_expiry = account.get("token_expiry")
        if token_expiry:
            expiry = datetime.fromisoformat(str(token_expiry).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This account needs to be reauthorized before it can be connected.",
                )

        enabled_account = self.get_enabled_account_for_platform(
            user_id=user_id,
            platform_id=UUID(str(platform_id)),
            exclude_account_id=str(account_id),
        )

        if enabled_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "account_already_connected",
                    "message": (
                        "An account is already connected for this platform. "
                        "Please disconnect it first."
                    ),
                    "connected_account": enabled_account,
                },
            )

        now = datetime.now(timezone.utc).isoformat()
        updated = (
            self.supabase
            .table("connected_accounts")
            .update(
                {
                    "is_enabled": True,
                    "deleted_at": None,
                    "updated_at": now,
                }
            )
            .eq("id", str(account_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if not updated.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to connect account",
            )

        return self._public_account(updated.data[0])

    def delete_account(self, user_id: UUID, account_id: UUID) -> None:
        existing = (
            self.supabase
            .table("connected_accounts")
            .select("id")
            .eq("id", str(account_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected account not found",
            )

        self.supabase.table("connected_accounts").delete().eq(
            "id",
            str(account_id),
        ).eq(
            "user_id",
            str(user_id),
        ).execute()
