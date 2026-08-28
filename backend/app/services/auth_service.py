from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_client


class AuthService:

    def __init__(self):
        self.supabase = get_supabase_client()

    @staticmethod
    def normalize_username(username: str) -> str:
        return username.strip().lower()

    @staticmethod
    def _is_unique_violation(exc: Exception) -> bool:
        code = str(getattr(exc, "code", "") or "")
        message = str(exc).lower()
        details = str(getattr(exc, "details", "") or "").lower()
        return (
            code == "23505"
            or "23505" in message
            or "duplicate key" in message
            or "duplicate key" in details
            or "users_username_canonical_uidx" in message
            or "users_username_canonical_uidx" in details
        )

    def resolve_login_email(
        self,
        identifier: str,
    ) -> str:
        value = identifier.strip()
        if not value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
            )

        if "@" in value:
            return value.lower()

        canonical = self.normalize_username(value)
        response = (
            self.supabase
            .table("users")
            .select("email")
            .eq("username", canonical)
            .maybe_single()
            .execute()
        )

        if not response.data or not response.data.get("email"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
            )

        return str(response.data["email"]).strip().lower()

    def find_login_email(self, identifier: str) -> str | None:
        """Resolve username/email to an account email, or None if not found."""
        value = identifier.strip()
        if not value:
            return None

        if "@" in value:
            email = value.lower()
            rows = (
                self.supabase.table("users")
                .select("email")
                .eq("email", email)
                .maybe_single()
                .execute()
            )
            if rows.data and rows.data.get("email"):
                return str(rows.data["email"]).strip().lower()
            return email

        canonical = self.normalize_username(value)
        response = (
            self.supabase.table("users")
            .select("email")
            .eq("username", canonical)
            .maybe_single()
            .execute()
        )
        if not response.data or not response.data.get("email"):
            return None
        return str(response.data["email"]).strip().lower()

    def get_profile(
        self,
        user_id: UUID,
    ) -> dict:
        response = (
            self.supabase
            .table("users")
            .select(
                """
                id,
                email,
                first_name,
                last_name,
                username,
                name,
                sso_provider,
                sso_provider_user_id,
                last_login,
                is_active,
                is_deleted,
                deleted_at,
                created_at,
                updated_at
                """
            )
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        return response.data

    def ensure_profile(
        self,
        user_id: UUID,
        auth_user: Any | None = None,
    ) -> None:
        existing = (
            self.supabase
            .table("users")
            .select("id")
            .eq("id", str(user_id))
            .limit(1)
            .execute()
        )

        if existing.data:
            return

        if auth_user is None:
            admin_response = self.supabase.auth.admin.get_user_by_id(str(user_id))
            auth_user = getattr(admin_response, "user", None)

        if auth_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create user profile",
            )

        metadata = self._user_value(auth_user, "user_metadata") or {}
        app_metadata = self._user_value(auth_user, "app_metadata") or {}
        email = self._user_value(auth_user, "email") or ""
        first_name = metadata.get("first_name") or metadata.get("given_name")
        last_name = metadata.get("last_name") or metadata.get("family_name")
        raw_username = metadata.get("username") or (email.split("@")[0] if email else None)
        username = (
            self.normalize_username(str(raw_username))
            if raw_username
            else None
        )
        name = (
            metadata.get("full_name")
            or metadata.get("name")
            or " ".join(part for part in [first_name, last_name] if part).strip()
            or username
        )
        provider = app_metadata.get("provider")
        sso_provider = None if provider in (None, "email") else provider
        now = datetime.now(timezone.utc).isoformat()

        try:
            response = (
                self.supabase
                .table("users")
                .insert(
                    {
                        "id": str(user_id),
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "username": username,
                        "name": name,
                        "sso_provider": sso_provider,
                        "is_active": True,
                        "is_deleted": False,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                .execute()
            )
        except Exception as exc:
            if self._is_unique_violation(exc) and username:
                # Email-local-part collisions: fall back to a unique suffix.
                fallback = f"{username}_{str(user_id).replace('-', '')[:8]}"
                response = (
                    self.supabase
                    .table("users")
                    .insert(
                        {
                            "id": str(user_id),
                            "email": email,
                            "first_name": first_name,
                            "last_name": last_name,
                            "username": fallback,
                            "name": name,
                            "sso_provider": sso_provider,
                            "is_active": True,
                            "is_deleted": False,
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
                    .execute()
                )
            else:
                raise

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create user profile",
            )

    @staticmethod
    def _user_value(user: Any, key: str) -> Any:
        if isinstance(user, dict):
            return user.get(key)
        return getattr(user, key, None)

    def update_last_login(
        self,
        user_id: UUID,
    ) -> None:
        self.supabase.table("users").update(
            {
                "last_login": datetime.now(timezone.utc).isoformat(),
            }
        ).eq(
            "id",
            str(user_id),
        ).execute()

    def update_profile(
        self,
        user_id: UUID,
        *,
        first_name: str,
        last_name: str,
        username: str,
    ) -> dict:
        self.ensure_profile(user_id)
        first_name = first_name.strip()
        last_name = last_name.strip()
        username = self.normalize_username(username)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is required",
            )
        name = " ".join(part for part in [first_name, last_name] if part).strip() or username
        now = datetime.now(timezone.utc).isoformat()
        try:
            response = (
                self.supabase.table("users")
                .update(
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "username": username,
                        "name": name,
                        "updated_at": now,
                    }
                )
                .eq("id", str(user_id))
                .execute()
            )
        except Exception as exc:
            if self._is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username is already taken",
                ) from exc
            raise

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to update user profile",
            )
        return self.get_profile(user_id)
