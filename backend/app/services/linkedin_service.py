import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

class LinkedInService:

    def __init__(self):
        self.settings = get_settings()

    def create_state(self) -> str:
        return secrets.token_urlsafe(32)

    def build_authorization_url(self, state: str) -> str:

        params = {
            "response_type": "code",
            "client_id": self.settings.linkedin_client_id,
            "redirect_uri": self.settings.linkedin_redirect_uri,
            "state": state,
            "scope": self.settings.linkedin_scopes,
        }

        return (
            f"{self.settings.linkedin_authorization_url}"
            f"?{urlencode(params)}"
        )

    async def exchange_code(self, code: str) -> dict:

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.settings.linkedin_client_id,
            "client_secret": (
                self.settings.linkedin_client_secret.get_secret_value()
            ),
            "redirect_uri": self.settings.linkedin_redirect_uri,
        }

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                self.settings.linkedin_token_url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        if response.is_error:
            raise RuntimeError(
                f"LinkedIn token exchange failed: {response.text}"
            )

        token_data = response.json()

        expires_in = token_data.get("expires_in")

        expires_at = None

        if expires_in:
            expires_at = (
                datetime.now(timezone.utc)
                + timedelta(seconds=int(expires_in))
            ).isoformat()

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,
            "scope": token_data.get("scope"),
        }

    async def get_user_info(self, access_token: str) -> dict:

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.get(
                self.settings.linkedin_userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        if response.is_error:
            raise RuntimeError(
                f"Unable to retrieve LinkedIn user: {response.text}"
            )

        return response.json()