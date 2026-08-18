from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_client


class AuthService:

    def __init__(self):
        self.supabase = get_supabase_client()

    def get_profile(self, user_id: UUID) -> dict:
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

    def update_last_login(self, user_id: UUID) -> None:
        self.supabase.table("users").update(
            {
                "last_login": datetime.now(timezone.utc).isoformat(),
            }
        ).eq(
            "id",
            str(user_id),
        ).execute()