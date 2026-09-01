
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_client
from app.services.account_service import AccountService
from app.services.bluesky_service import BlueskyService
from app.services.linkedin_service import LinkedInService
from app.services.generation_service import GenerationService

class PublicationServices:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.account_service = AccountService()
        self.linkedin_service = LinkedInService()
        self.generation_service = GenerationService()
        self.bluesky_services = BlueskyService()

    async def publish(self, *,  user_id: UUID, draft_id: UUID, connected_account_id: UUID) -> dict[str, Any]:
        draft = self.generation_service.get_draft(user_id=user_id, draft_id=draft_id)
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation Draft not found",
            )
        
        version_id  = draft.get("current_version_id")

        if not version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generation Draft has no current version",
            )
        
        version = next((
            item for item in draft.get("versions", []) if item.get("id") == str(version_id)
            ), None,
        )

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation Version not found",
            )

        content = str( version.get("full_post") or "").strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generation Version has no content to publish",
            )
        
        account = self._get_owned_account(user_id=user_id, connected_account_id=connected_account_id)
        self._validate_connected_account(account=account)

        platform_id = account.get("platform_id")
        if not platform_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connected account has no platform_id",
            )
        
        platform_name = self._get_platform_name (platform_id=UUID(platform_id))

        draft_platform = str(draft.get("platform", "")).lower()

        if platform_name != draft_platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Draft platform ({draft_platform}) does not match connected account platform ({platform_name})",
            )

        existing_publication = self._find_existing_publication(
            user_id=user_id,
            draft_id=draft_id,
            version_id=version_id,
            connected_account_id=connected_account_id,
        )
        if existing_publication:
            self._validated_existing_publication(publication=existing_publication)

        publication = self._create_publication(
            user_id=user_id,
            draft_id=draft_id,
            version_id=version_id,
            platform_id=UUID(platform_id),
            connected_account_id=connected_account_id,
        )
        publcation_id = UUID(str(publication.get("id")))

        self._create_event(
            publication_id=publcation_id,
            event_type="ppublish_requested",
            event_status="queued",
            message=f"Publication created for draft {draft_id} and version {version_id}",
        )

        try:
            self._set_publication_status(publication_id=publcation_id, status_name="running")

            self._create_event(
                publication_id=publcation_id,
                event_type="publishing",
                event_status="running",
                message=f"Publishing draft {draft_id} and version {version_id} to platform {platform_name}",
            )

            platform_response = (
                await self._publish_to_platform(
                    platform_name=platform_name,
                    content=content,
                    account=account,
                )
            )

            paltform_post_id = platform_response.get("platform_post_id")
            self._update_publication(
                values={
                    "status_id": str(self._get_status_id("completed")),
                    "platform_post_id": paltform_post_id,
                    "platform_response": str(platform_response),
                    "published_at": self._now(),
                    "updated_at": self._now(),
                }
            )

            self._create_event(
                publication_id=publcation_id,
                event_type="published",
                event_status="completed",
                message=f"Draft {draft_id} and version {version_id} published to platform {platform_name} with post ID {paltform_post_id}",
            )

        except Exception as e:
            self._mark_publication_failed(publication_id=publcation_id, error_message=str(e))
            return self._get_publication(user_id=user_id, publication_id=publcation_id)



    async def publish_multiple(self, *, user_id: UUID, publications: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for item in publications:
            try:
                result = await self.publish(
                    user_id=user_id,
                    draft_id=UUID(item.get("draft_id")),
                    connected_account_id=UUID(item.get("connected_account_id")),
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "draft_id": item.get("draft_id"),
                    "connected_account_id": item.get("connected_account_id"),
                    "status": "failed",
                    "error": str(e),
                })

        return results


    ## HELPER METHODS -----------------------------------------------

    def _get_owned_account(self, *, user_id: UUID, connected_account_id: UUID) -> dict[str, Any]:
        account = (
            self.db
            .table("connected_accounts")
            .select("*")
            .eq("id", connected_account_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected account not found",
            )
        return account[0]

    def _validate_connected_account(self, account: dict[str, Any],) -> None:
        if not account.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connected account is not active",
            )
        connection_status_id = (account.get("connection_status_id"))
        if connection_status_id:
            connection_status = ( self._get_status_name(connection_status_id) )

            if connection_status != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Connected account is not connected (status: {connection_status})",
                )

    def _get_status_name(self, status_id: UUID) -> str:
        response = (
            self.db
            .table("statuses")
            .select("status_name")
            .eq("id", status_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Status not found",
            )
        return str(response[0].get("status_name", "")).lower()

    def _get_platform_name(self, platform_id: UUID) -> str:
        response = (
            self.db
            .table("platforms")
            .select("platform_name")
            .eq("id", platform_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform not found",
            )
        return str(response[0].get("platform_name", "")).lower()

    def _find_existing_publication(self, *, user_id: UUID, draft_id: UUID, version_id: UUID, connected_account_id: UUID) -> dict[str, Any] | None:
        publication = (
            self.db
            .table("published_posts")
            .select("*")
            .eq("user_id", user_id)
            .eq("version_id", version_id)
            .eq("draft_id", draft_id)
            .eq("connected_account_id", connected_account_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        return publication[0] if publication else None

    def _validated_existing_publication(self, publication: dict[str, Any]) -> None:
        status_name = self._get_status_name(publication.get("status_id"))
        if status_name in ["queued", "running", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Publication already exists with status: {status_name}",
            )




    def _set_publication_status(self, publication_id: UUID,status_name: str) -> None:
        status_id = self._get_status_id(status_name)
        self._update_publication(
            publication_id=publication_id,
            values={
                "status_id": str(status_id),  
            }
        )


    def _create_publication(self, *, user_id: UUID, draft_id: UUID, version_id: UUID, platform_id: UUID, connected_account_id: UUID) -> dict[str, Any]:
        queued_status_id = self._get_status_id("queued")
        now  = self._now()

        response = (
            self.db
            .table("published_posts")
            .insert({
                "user_id": str(user_id),
                "draft_id": str(draft_id),
                "version_id": str(version_id),
                "platform_id": str(platform_id),
                "connected_account_id": str(connected_account_id),
                "status_id": str(queued_status_id),
                "retry_count": 0,
                "created_at": now,
                "updated_at": now,
            }).execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create publication",
            )
        return response.data[0]

    def _update_publication(self, *, publication_id: UUID, values: dict[str, Any]) -> dict[str, Any]:
        now  = self._now()
        values["updated_at"] = now
        response = (
            self.db
            .table("published_posts")
            .update(values)
            .eq("id", str(publication_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update publication",
            )
        return response.data[0]

    def _get_publication(self, *, user_id: UUID, publication_id: UUID) -> dict[str, Any]:
        response = (
            self.db
            .table("published_posts")
            .select("*")
            .eq("id", str(publication_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
            .data
            or []
        )
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found",
            )
        publication = response[0]
        publication["status_name"] = self._get_status_name(publication.get("status_id"))
        return publication


    def _create_event(self, *, publication_id: UUID, event_type: str, event_status: str, message: str) -> dict[str, Any]:
        now  = self._now()
        response = (
            self.db
            .table("publication_events")
            .insert({
                "publication_id": str(publication_id),
                "event_type": event_type,
                "event_status": event_status,
                "message": message,
                "created_at": now,
                "updated_at": now,
            }).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create publication event",
            )
        return response.data[0]

    def _mark_publication_failed(self, *, publication_id: UUID, error_message: str) -> dict[str, Any]:
        self._update_publication(
            publication_id=publication_id,
            values={
                "status_id": str(self._get_status_id("failed")),
                "error_message": error_message,
                "updated_at": self._now(),
            }
        )
        self._create_event(
            publication_id=publication_id,
            event_type="publish_failed",
            event_status="failed",
            message=error_message,
        )



    async def _publish_to_platform(self, *, platform_name: str, content: str, account: dict[str, Any]) -> dict[str, Any]:
        if not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content to publish",
            )

        encrypted_token = account.get("access_token_encrypted")
        if not encrypted_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connected account has no access token",
            )

        access_token = self.account_service._decrypt_token(encrypted_token=encrypted_token)

        provider_user_id = account.get("provider_user_id")
        if not provider_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connected account has no provider user ID",
            )


        if platform_name == "linkedin":
            return await (
                self.linkedin_service.publish_post(
                    access_token=access_token,
                    author_id=provider_user_id,
                    content=content,
                )
            )

        if platform_name == "bluesky":
            encrypted_dpop_key = account.get("dpop_private_key_encrypted")
            if not encrypted_dpop_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Connected account has no DPoP private key",
                )
            dpop_private_key_pem = self.account_service._decrypt_token(encrypted_token=encrypted_dpop_key)

            return await (
                self.bluesky_services.publish_post(
                    access_token=access_token,
                    repo=provider_user_id,
                    content=content,
                    dpop_private_key_pem=dpop_private_key_pem,
                )
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Publishing to platform '{platform_name}' is not supported",
        )
            

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()