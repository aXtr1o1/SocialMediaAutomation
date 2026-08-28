from typing import Any, Optional
from uuid import UUID

from app.core.supabase import get_supabase_client
from app.models.source import SourceCreate, SourceUpdate


class SourceService:

    def __init__(self):
        self.supabase = get_supabase_client()

    def create_source(
        self,
        source: SourceCreate,
        user_id: UUID,
    ) -> dict[str, Any]:

        data = {
            "url": str(source.url),
            "domain_id": str(source.domain_id),
            "source_type": source.source_type,
            "description": source.description,
            "created_by": str(user_id),
            "updated_by": str(user_id),
        }

        if source.status_id is not None:
            data["status_id"] = str(source.status_id)

        response = (
            self.supabase
            .table("sources")
            .insert(data)
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to create source.")

        return response.data[0]

    def get_sources(
        self,
        user_id: UUID,
    ) -> list[dict[str, Any]]:

        response = (
            self.supabase
            .table("sources")
            .select("*")
            .eq("created_by", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    def get_source(
        self,
        source_id: UUID,
        user_id: UUID,
    ) -> Optional[dict[str, Any]]:

        response = (
            self.supabase
            .table("sources")
            .select("*")
            .eq("id", str(source_id))
            .eq("created_by", str(user_id))
            .maybe_single()
            .execute()
        )

        return response.data

    def update_source(
        self,
        source_id: UUID,
        source: SourceUpdate,
        user_id: UUID,
    ) -> Optional[dict[str, Any]]:

        data = source.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        if "url" in data:
            data["url"] = str(data["url"])

        if "status_id" in data:
            data["status_id"] = str(data["status_id"])

        data["updated_by"] = str(user_id)

        response = (
            self.supabase
            .table("sources")
            .update(data)
            .eq("id", str(source_id))
            .eq("created_by", str(user_id))
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]

    def delete_source(
        self,
        source_id: UUID,
        user_id: UUID,
    ) -> bool:

        response = (
            self.supabase
            .table("sources")
            .delete()
            .eq("id", str(source_id))
            .eq("created_by", str(user_id))
            .execute()
        )

        return bool(response.data)