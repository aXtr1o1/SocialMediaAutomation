from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.services.bluesky_service import (
    BlueskyOAuthSession,
    BlueskyService,
    OAUTH_SESSION_TTL_MINUTES,
)

TTL_MINUTES = OAUTH_SESSION_TTL_MINUTES


class OAuthStateService:
    """Persist OAuth connect→callback state in Supabase (multi-worker safe)."""

    def __init__(self) -> None:
        self.db = get_supabase_client()
        settings = get_settings()

        primary = settings.oauth_token_encryption_key.get_secret_value().strip()
        if not primary:
            raise RuntimeError("OAUTH_TOKEN_ENCRYPTION_KEY is not configured")

        self._cipher = Fernet(primary.encode("utf-8"))

        previous: list[Fernet] = []
        for key in settings.oauth_token_encryption_previous_keys.split(","):
            cleaned = key.strip()
            if cleaned:
                previous.append(Fernet(cleaned.encode("utf-8")))

        self._decrypt_ciphers = [self._cipher, *previous]

    def save_linkedin_state(self, *, state: str, user_id: UUID, intent: str) -> None:
        self._save(
            state=state,
            platform="linkedin",
            user_id=user_id,
            intent=intent,
            session_payload=None,
        )

    def save_bluesky_state(
        self,
        *,
        state: str,
        user_id: UUID,
        intent: str,
        session: BlueskyOAuthSession,
    ) -> None:
        self._save(
            state=state,
            platform="bluesky",
            user_id=user_id,
            intent=intent,
            session_payload=self._session_to_payload(session),
        )

    def consume_linkedin_state(self, state: str) -> tuple[UUID, str] | None:
        self.cleanup_expired()
        row = self._consume(state=state, platform="linkedin")
        if row is None:
            return None
        return UUID(str(row["user_id"])), str(row.get("intent") or "add")

    def consume_bluesky_state(self, state: str) -> tuple[UUID, BlueskyOAuthSession, str] | None:
        self.cleanup_expired()
        row = self._consume(state=state, platform="bluesky")
        if row is None:
            return None
        payload = row.get("session_payload")
        if not isinstance(payload, dict):
            return None
        try:
            session = self._payload_to_session(payload)
        except (KeyError, TypeError, ValueError, InvalidToken):
            return None
        if BlueskyService.is_session_expired(session):
            return None
        return UUID(str(row["user_id"])), session, str(row.get("intent") or "add")

    def cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.table("oauth_pending_states").delete().lt("expires_at", now).execute()

    def _encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode("utf-8")).decode("utf-8")

    def _decrypt(self, value: str) -> str:
        raw = value.encode("utf-8")
        last_error: Exception | None = None
        for cipher in self._decrypt_ciphers:
            try:
                return cipher.decrypt(raw).decode("utf-8")
            except InvalidToken as exc:
                last_error = exc
        raise InvalidToken("Unable to decrypt OAuth session secret") from last_error

    def _save(
        self,
        *,
        state: str,
        platform: str,
        user_id: UUID,
        intent: str,
        session_payload: dict[str, Any] | None,
    ) -> None:
        self.cleanup_expired()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=TTL_MINUTES)).isoformat()
        self.db.table("oauth_pending_states").upsert(
            {
                "state": state,
                "platform": platform,
                "user_id": str(user_id),
                "intent": intent,
                "session_payload": session_payload,
                "expires_at": expires_at,
            }
        ).execute()

    def _consume(self, *, state: str, platform: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc).isoformat()
        rows = (
            self.db.table("oauth_pending_states")
            .select("*")
            .eq("state", state)
            .eq("platform", platform)
            .gt("expires_at", now)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            # Drop stale/unknown row if present so memory does not accumulate.
            self.db.table("oauth_pending_states").delete().eq("state", state).eq("platform", platform).execute()
            return None

        row = rows[0]
        self.db.table("oauth_pending_states").delete().eq("state", state).eq("platform", platform).execute()
        return row

    def _session_to_payload(self, session: BlueskyOAuthSession) -> dict[str, Any]:
        return {
            "state": session.state,
            "code_verifier": self._encrypt(session.code_verifier),
            "dpop_private_key_pem": self._encrypt(session.dpop_private_key_pem),
            "issuer": session.issuer,
            "authorization_endpoint": session.authorization_endpoint,
            "token_endpoint": session.token_endpoint,
            "par_endpoint": session.par_endpoint,
            "resource_server": session.resource_server,
            "dpop_nonce": session.dpop_nonce,
            "resource_dpop_nonce": session.resource_dpop_nonce,
            "created_at": session.created_at,
        }

    def _payload_to_session(self, payload: dict[str, Any]) -> BlueskyOAuthSession:
        return BlueskyOAuthSession(
            state=str(payload["state"]),
            code_verifier=self._decrypt(str(payload["code_verifier"])),
            dpop_private_key_pem=self._decrypt(str(payload["dpop_private_key_pem"])),
            issuer=str(payload["issuer"]),
            authorization_endpoint=str(payload["authorization_endpoint"]),
            token_endpoint=str(payload["token_endpoint"]),
            par_endpoint=str(payload["par_endpoint"]),
            resource_server=str(payload["resource_server"]),
            dpop_nonce=payload.get("dpop_nonce"),
            resource_dpop_nonce=payload.get("resource_dpop_nonce"),
            created_at=int(payload.get("created_at") or 0),
        )
