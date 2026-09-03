from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from redis import Redis


class RedisStateService:
    """
    Stores workflow/session state in Redis.

    Redis contains transient workflow/session state while durable
    generated content, drafts, and version history remain in the
    database.

    Important concepts:

    1. User workflow state
       workflow:<user_id>

    2. Active workflow
       Stored inside the user's workflow state as workflow_run_id.

    3. Selection -> workflow mapping
       workflow:selection:<user_id>:<domain>:<sorted_subdomains>

       This allows the frontend to leave Sources and later return
       without automatically starting a new crawl.

    4. User workflow session
       workflow:<user_id>

       The workflow state and session state intentionally live in
       the same Redis document in this implementation.

    5. Active generation
       Stored inside the workflow state as active_generation_id.

    Redis is NOT the permanent source of truth for generated
    content/version history. That information must remain in the
    database.
    """

    WORKFLOW_PREFIX = "workflow:"
    SELECTION_WORKFLOW_PREFIX = "workflow:selection:"
    WORKFLOW_LOCK_PREFIX = "workflow:lock:"

    def __init__(self) -> None:
        settings = get_settings()

        redis_url = getattr(settings, "redis_url", None)

        if not redis_url:
            redis_url = getattr(settings, "REDIS_URL", None)

        if not redis_url:
            raise RuntimeError("Redis URL is not configured")

        self.redis: Redis = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        workflow_ttl = getattr(
            settings,
            "workflow_state_ttl_seconds",
            None,
        )

        if workflow_ttl is None:
            workflow_ttl = getattr(
                settings,
                "WORKFLOW_STATE_TTL_SECONDS",
                86400,
            )

        self.workflow_ttl = int(workflow_ttl)

    # ------------------------------------------------------------------
    # Keys
    # ------------------------------------------------------------------

    def workflow_key(
        self,
        user_id: str | UUID,
    ) -> str:
        return f"{self.WORKFLOW_PREFIX}{user_id}"

    def selection_workflow_key(
        self,
        user_id: str | UUID,
        domain_id: str | UUID,
        subdomain_ids: list[str | UUID],
    ) -> str:
        normalized_subdomains = sorted(
            str(value)
            for value in subdomain_ids
            if value
        )

        selection = "|".join(
            [
                str(domain_id),
                *normalized_subdomains,
            ]
        )

        return (
            f"{self.SELECTION_WORKFLOW_PREFIX}"
            f"{user_id}:"
            f"{selection}"
        )

    def workflow_lock_key(
        self,
        user_id: str | UUID,
    ) -> str:
        return f"{self.WORKFLOW_LOCK_PREFIX}{user_id}"

    # ------------------------------------------------------------------
    # Generic JSON helpers
    # ------------------------------------------------------------------

    def _set_json(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        payload = json.dumps(
            value,
            default=str,
            ensure_ascii=False,
        )

        if ttl_seconds is None:
            self.redis.set(
                key,
                payload,
            )
        else:
            self.redis.setex(
                key,
                int(ttl_seconds),
                payload,
            )

    def _get_json(
        self,
        key: str,
    ) -> Any | None:
        raw = self.redis.get(key)

        if raw is None:
            return None

        try:
            return json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Workflow state
    # ------------------------------------------------------------------

    def set_workflow(
        self,
        user_id: str | UUID,
        state: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        if ttl_seconds is None:
            ttl_seconds = self.workflow_ttl

        state = {
            **state,
            "last_activity_at": datetime.now(
                timezone.utc,
            ).isoformat(),
        }

        self._set_json(
            self.workflow_key(user_id),
            state,
            ttl_seconds,
        )

    def get_workflow(
        self,
        user_id: str | UUID,
    ) -> dict[str, Any] | None:
        value = self._get_json(
            self.workflow_key(user_id),
        )

        if not isinstance(value, dict):
            return None

        return value

    def update_workflow(
        self,
        user_id: str | UUID,
        updates: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_workflow(user_id) or {}

        current.update(updates)

        self.set_workflow(
            user_id,
            current,
            ttl_seconds,
        )

        return current

    def clear_workflow(
        self,
        user_id: str | UUID,
    ) -> None:
        self.redis.delete(
            self.workflow_key(user_id),
        )

    # ------------------------------------------------------------------
    # Active workflow
    # ------------------------------------------------------------------

    def get_active_workflow(
        self,
        user_id: str | UUID,
    ) -> str | None:
        workflow = self.get_workflow(user_id)

        if not workflow:
            return None

        workflow_run_id = workflow.get(
            "workflow_run_id",
        )

        if not workflow_run_id:
            return None

        return str(workflow_run_id)

    def set_active_workflow(
        self,
        user_id: str | UUID,
        workflow_run_id: str | UUID,
    ) -> None:
        self.update_workflow(
            user_id,
            {
                "workflow_run_id": str(
                    workflow_run_id,
                ),
            },
        )

    def clear_active_workflow(
        self,
        user_id: str | UUID,
        workflow_run_id: str | UUID | None = None,
    ) -> None:
        """
        Clear the active workflow.

        When workflow_run_id is supplied, only clear the active
        workflow if it is still the same workflow. This prevents
        an older workflow from clearing a newer workflow.
        """

        if workflow_run_id is not None:
            current = self.get_active_workflow(
                user_id,
            )

            if current != str(workflow_run_id):
                return

        self.update_workflow(
            user_id,
            {
                "workflow_run_id": None,
            },
        )

    # ------------------------------------------------------------------
    # Selection-specific workflow mapping
    # ------------------------------------------------------------------

    def set_selection_workflow(
        self,
        user_id: str | UUID,
        domain_id: str | UUID,
        subdomain_ids: list[str | UUID],
        workflow_run_id: str | UUID,
        ttl_seconds: int | None = None,
    ) -> None:
        if ttl_seconds is None:
            ttl_seconds = self.workflow_ttl

        self._set_json(
            self.selection_workflow_key(
                user_id,
                domain_id,
                subdomain_ids,
            ),
            {
                "workflow_run_id": str(
                    workflow_run_id,
                ),
                "domain_id": str(
                    domain_id,
                ),
                "subdomain_ids": [
                    str(value)
                    for value in subdomain_ids
                    if value
                ],
            },
            ttl_seconds,
        )

    def get_selection_workflow(
        self,
        user_id: str | UUID,
        domain_id: str | UUID,
        subdomain_ids: list[str | UUID],
    ) -> str | None:
        value = self._get_json(
            self.selection_workflow_key(
                user_id,
                domain_id,
                subdomain_ids,
            ),
        )

        if not isinstance(value, dict):
            return None

        workflow_run_id = value.get(
            "workflow_run_id",
        )

        if not workflow_run_id:
            return None

        return str(workflow_run_id)

    def clear_selection_workflow(
        self,
        user_id: str | UUID,
        domain_id: str | UUID,
        subdomain_ids: list[str | UUID],
    ) -> None:
        self.redis.delete(
            self.selection_workflow_key(
                user_id,
                domain_id,
                subdomain_ids,
            ),
        )

    # ------------------------------------------------------------------
    # User workflow/session state
    # ------------------------------------------------------------------

    def get_session(
        self,
        user_id: str | UUID,
    ) -> dict[str, Any]:
        workflow = self.get_workflow(
            user_id,
        )

        if workflow:
            return workflow

        return {
            "user_id": str(user_id),
            "workflow_run_id": None,
            "active_workflow_id": None,
            "active_project_id": None,
            "current_workflow": None,
            "current_step": None,
            "selected_source_posts": [],
            "generated_article": None,
            "generated_content": [],
            "generation_drafts": [],
            "target_platforms": [],
            "filters": {},
            "draft_changes": {},
            "generation_status": "IDLE",
            "active_generation_id": None,
            "last_activity_at": datetime.now(
                timezone.utc,
            ).isoformat(),
        }

    def update_session(
        self,
        user_id: str | UUID,
        **updates: Any,
    ) -> dict[str, Any]:
        """
        Update the user's workflow/session state.

        None values are intentionally preserved. This is important
        for clearing active_generation_id, workflow_run_id, etc.
        """

        current = self.get_session(
            user_id,
        )

        current.update(
            updates,
        )

        current["user_id"] = str(
            user_id,
        )

        current["last_activity_at"] = datetime.now(
            timezone.utc,
        ).isoformat()

        self.set_workflow(
            user_id,
            current,
        )

        return current

    def clear_session(
        self,
        user_id: str | UUID,
    ) -> None:
        self.clear_workflow(
            user_id,
        )

    # ------------------------------------------------------------------
    # Active generation
    # ------------------------------------------------------------------

    def get_active_generation_id(
        self,
        user_id: str | UUID,
    ) -> str | None:
        workflow = self.get_workflow(
            user_id,
        )

        if not workflow:
            return None

        generation_id = workflow.get(
            "active_generation_id",
        )

        if not generation_id:
            return None

        return str(
            generation_id,
        )

    def set_active_generation_id(
        self,
        user_id: str | UUID,
        generation_id: str | UUID,
    ) -> None:
        self.update_workflow(
            user_id,
            {
                "active_generation_id": str(
                    generation_id,
                ),
            },
        )

    def clear_active_generation_id(
        self,
        user_id: str | UUID,
    ) -> None:
        self.update_workflow(
            user_id,
            {
                "active_generation_id": None,
            },
        )

    # ------------------------------------------------------------------
    # Locks
    # ------------------------------------------------------------------

    def acquire_workflow_lock(
        self,
        user_id: str | UUID,
        ttl_seconds: int = 30,
    ) -> bool:
        return bool(
            self.redis.set(
                self.workflow_lock_key(
                    user_id,
                ),
                "1",
                nx=True,
                ex=ttl_seconds,
            )
        )

    def release_workflow_lock(
        self,
        user_id: str | UUID,
    ) -> None:
        self.redis.delete(
            self.workflow_lock_key(
                user_id,
            ),
        )