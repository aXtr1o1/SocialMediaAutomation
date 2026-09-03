from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import get_settings

# Must stay in sync with oauth_pending_states expires_at TTL.
OAUTH_SESSION_TTL_MINUTES = 15
OAUTH_SESSION_TTL_SECONDS = OAUTH_SESSION_TTL_MINUTES * 60


@dataclass
class BlueskyOAuthSession:
    """
    Temporary server-side information required between
    the /connect request and the OAuth callback.
    """

    state: str
    code_verifier: str
    dpop_private_key_pem: str
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    par_endpoint: str
    resource_server: str
    dpop_nonce: str | None = None
    resource_dpop_nonce: str | None = None
    created_at: int = 0


class BlueskyService:
    """
    Bluesky / AT Protocol OAuth service.

    Local development uses the Bluesky localhost
    public-client OAuth flow.

    Implements:
        - OAuth metadata discovery
        - PKCE
        - PAR
        - DPoP
        - Authorization URL generation
        - Authorization-code exchange
        - Public profile lookup
    """

    def __init__(self) -> None:
        self.settings = get_settings()

        self.client_id = self.settings.bluesky_client_id
        self.redirect_uri = self.settings.bluesky_redirect_uri

        self.scope = getattr(
            self.settings,
            "bluesky_oauth_scope",
            "atproto",
        )

        self.timeout = httpx.Timeout(
            connect=10.0,
            read=20.0,
            write=20.0,
            pool=20.0,
        )

    # =========================================================
    # General helpers
    # =========================================================

    @staticmethod
    def _require_https_url(
        url: str,
        name: str,
    ) -> None:

        parsed = urlparse(url)

        if parsed.scheme != "https":
            raise ValueError(
                f"{name} must use HTTPS"
            )

        if not parsed.netloc:
            raise ValueError(
                f"{name} must be a valid URL"
            )

    @staticmethod
    def _base64url(data: bytes) -> str:
        return (
            base64.urlsafe_b64encode(data)
            .rstrip(b"=")
            .decode("ascii")
        )

    @classmethod
    def _create_pkce_verifier(cls) -> str:
        """
        RFC 7636 PKCE verifier.
        """

        return cls._base64url(
            secrets.token_bytes(48)
        )

    @classmethod
    def _create_pkce_challenge(
        cls,
        verifier: str,
    ) -> str:

        digest = hashlib.sha256(
            verifier.encode("ascii")
        ).digest()

        return cls._base64url(digest)

    # =========================================================
    # OAuth state
    # =========================================================

    @staticmethod
    def create_state() -> str:
        return secrets.token_urlsafe(32)

    # =========================================================
    # DPoP
    # =========================================================

    @staticmethod
    def _generate_dpop_private_key(
    ) -> ec.EllipticCurvePrivateKey:

        return ec.generate_private_key(
            ec.SECP256R1()
        )

    @staticmethod
    def _private_key_to_pem(
        private_key: ec.EllipticCurvePrivateKey,
    ) -> str:

        return (
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            .decode("utf-8")
        )

    @staticmethod
    def _load_private_key(
        private_key_pem: str,
    ) -> ec.EllipticCurvePrivateKey:

        key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )

        if not isinstance(
            key,
            ec.EllipticCurvePrivateKey,
        ):
            raise ValueError(
                "DPoP private key must be an EC private key"
            )

        return key

    @staticmethod
    def _public_jwk(
        private_key: ec.EllipticCurvePrivateKey,
    ) -> dict[str, str]:

        public_key = private_key.public_key()
        numbers = public_key.public_numbers()

        return {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(
                numbers.x.to_bytes(32, "big")
            )
            .rstrip(b"=")
            .decode("ascii"),
            "y": base64.urlsafe_b64encode(
                numbers.y.to_bytes(32, "big")
            )
            .rstrip(b"=")
            .decode("ascii"),
        }

    @classmethod
    def _jwk_thumbprint(
        cls,
        jwk: dict[str, str],
    ) -> str:

        canonical = json.dumps(
            {
                "crv": jwk["crv"],
                "kty": jwk["kty"],
                "x": jwk["x"],
                "y": jwk["y"],
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        digest = hashlib.sha256(
            canonical
        ).digest()

        return cls._base64url(digest)

    @classmethod
    def _normalize_dpop_htu(cls, url: str) -> str:
        """
        RFC 9449 htu: absolute request URI without query/fragment,
        with basic syntax/scheme-based normalization (lowercase
        scheme/host, omit default ports).
        """
        parsed = urlparse(url.strip())
        scheme = (parsed.scheme or "").lower()
        host = (parsed.hostname or "").lower()
        if scheme not in {"http", "https"} or not host:
            raise ValueError(f"Invalid DPoP htu URL: {url}")

        port = parsed.port
        if port is not None and not (
            (scheme == "https" and port == 443)
            or (scheme == "http" and port == 80)
        ):
            netloc = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
        else:
            netloc = f"[{host}]" if ":" in host else host

        path = parsed.path or "/"
        return urlunparse((scheme, netloc, path, "", "", ""))

    @classmethod
    def _create_dpop_proof(
        cls,
        private_key_pem: str,
        method: str,
        url: str,
        nonce: str | None = None,
        access_token: str | None = None,
    ) -> str:

        private_key = cls._load_private_key(
            private_key_pem
        )

        public_jwk = cls._public_jwk(
            private_key
        )

        htu = cls._normalize_dpop_htu(url)

        payload: dict[str, Any] = {
            "jti": secrets.token_urlsafe(24),
            "htm": method.upper(),
            "htu": htu,
            "iat": int(time.time()),
        }

        if nonce:
            payload["nonce"] = nonce

        if access_token:
            token_hash = hashlib.sha256(
                access_token.encode("ascii")
            ).digest()

            payload["ath"] = cls._base64url(
                token_hash
            )

        return jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers={
                "typ": "dpop+jwt",
                "alg": "ES256",
                "jwk": public_jwk,
            },
        )

    # =========================================================
    # OAuth metadata discovery
    # =========================================================

    async def discover_authorization_server(
        self,
        resource_server: str,
    ) -> dict[str, Any]:

        self._require_https_url(
            resource_server,
            "resource_server",
        )

        resource_metadata_url = (
            resource_server.rstrip("/")
            + "/.well-known/oauth-protected-resource"
        )

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:

            response = await client.get(
                resource_metadata_url
            )

            if response.status_code == 200:

                metadata = response.json()

                authorization_servers = metadata.get(
                    "authorization_servers"
                )

                if not authorization_servers:
                    raise RuntimeError(
                        "Bluesky resource metadata did not "
                        "contain authorization_servers"
                    )

                issuer = authorization_servers[0]

            else:
                issuer = resource_server

            self._require_https_url(
                issuer,
                "authorization server",
            )

            auth_metadata_url = (
                issuer.rstrip("/")
                + "/.well-known/oauth-authorization-server"
            )

            metadata_response = await client.get(
                auth_metadata_url
            )

            metadata_response.raise_for_status()

            auth_metadata = metadata_response.json()

        discovered_issuer = auth_metadata.get(
            "issuer"
        )

        if discovered_issuer != issuer:
            raise RuntimeError(
                "Authorization server issuer mismatch"
            )

        required_fields = (
            "authorization_endpoint",
            "token_endpoint",
            "pushed_authorization_request_endpoint",
        )

        for field in required_fields:

            if not auth_metadata.get(field):
                raise RuntimeError(
                    f"Authorization server metadata "
                    f"missing '{field}'"
                )

        supported_scopes = auth_metadata.get(
            "scopes_supported",
            [],
        )

        if isinstance(
            supported_scopes,
            str,
        ):
            supported_scopes = (
                supported_scopes.split()
            )

        if "atproto" not in supported_scopes:
            raise RuntimeError(
                "Authorization server does not support "
                "the required 'atproto' scope"
            )

        return {
            "issuer": issuer,
            "authorization_endpoint": (
                auth_metadata[
                    "authorization_endpoint"
                ]
            ),
            "token_endpoint": (
                auth_metadata["token_endpoint"]
            ),
            "par_endpoint": (
                auth_metadata[
                    "pushed_authorization_request_endpoint"
                ]
            ),
        }

    # =========================================================
    # Start OAuth
    # =========================================================

    async def create_authorization_request(
        self,
    ) -> tuple[str, BlueskyOAuthSession]:

        resource_server = (
            self.settings.bluesky_pds_url
        )

        metadata = (
            await self.discover_authorization_server(
                resource_server
            )
        )

        state = self.create_state()

        code_verifier = (
            self._create_pkce_verifier()
        )

        code_challenge = (
            self._create_pkce_challenge(
                code_verifier
            )
        )

        # -----------------------------------------------------
        # Generate a unique DPoP key for this OAuth session.
        # This is NOT the confidential client signing key.
        # -----------------------------------------------------

        dpop_private_key = (
            self._generate_dpop_private_key()
        )

        dpop_private_key_pem = (
            self._private_key_to_pem(
                dpop_private_key
            )
        )

        dpop_jwk = self._public_jwk(
            dpop_private_key
        )

        dpop_jkt = self._jwk_thumbprint(
            dpop_jwk
        )

        # -----------------------------------------------------
        # Public localhost client
        #
        # IMPORTANT:
        # Do NOT send client_assertion.
        # -----------------------------------------------------

        form_data = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "dpop_jkt": dpop_jkt,
        }

        par_endpoint = self._normalize_dpop_htu(
            metadata["par_endpoint"]
        )

        dpop_proof = self._create_dpop_proof(
            private_key_pem=dpop_private_key_pem,
            method="POST",
            url=par_endpoint,
        )

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:

            response = await client.post(
                par_endpoint,
                data=form_data,
                headers={
                    "Content-Type": (
                        "application/x-www-form-urlencoded"
                    ),
                    "DPoP": dpop_proof,
                },
            )

            nonce = response.headers.get(
                "DPoP-Nonce"
            )

            if (
                response.status_code in (400, 401)
                and nonce
            ):

                dpop_proof = self._create_dpop_proof(
                    private_key_pem=dpop_private_key_pem,
                    method="POST",
                    url=par_endpoint,
                    nonce=nonce,
                )

                response = await client.post(
                    par_endpoint,
                    data=form_data,
                    headers={
                        "Content-Type": (
                            "application/x-www-form-urlencoded"
                        ),
                        "DPoP": dpop_proof,
                    },
                )

            response.raise_for_status()

            par_response = response.json()

        request_uri = par_response.get(
            "request_uri"
        )

        if not request_uri:
            raise RuntimeError(
                "Bluesky OAuth PAR response did not "
                "contain request_uri"
            )

        token_endpoint = self._normalize_dpop_htu(
            metadata["token_endpoint"]
        )

        session = BlueskyOAuthSession(
            state=state,
            code_verifier=code_verifier,
            dpop_private_key_pem=dpop_private_key_pem,
            issuer=metadata["issuer"],
            authorization_endpoint=(
                metadata["authorization_endpoint"]
            ),
            token_endpoint=token_endpoint,
            par_endpoint=par_endpoint,
            resource_server=resource_server,
            dpop_nonce=nonce,
            created_at=int(time.time()),
        )

        authorization_url = (
            session.authorization_endpoint
            + "?"
            + urlencode(
                {
                    "client_id": self.client_id,
                    "request_uri": request_uri,
                }
            )
        )

        return (
            authorization_url,
            session,
        )

    # =========================================================
    # Callback / Token Exchange
    # =========================================================

    @staticmethod
    def is_session_expired(session: BlueskyOAuthSession) -> bool:
        if not session.created_at:
            return True
        age_seconds = int(time.time()) - int(session.created_at)
        return age_seconds < 0 or age_seconds > OAUTH_SESSION_TTL_SECONDS

    async def exchange_code(
        self,
        code: str,
        session: BlueskyOAuthSession,
        issuer: str,
    ) -> dict[str, Any]:

        if self.is_session_expired(session):
            raise ValueError("OAuth session has expired")

        if issuer != session.issuer:
            raise ValueError(
                "OAuth authorization server issuer mismatch"
            )

        # -----------------------------------------------------
        # Public client:
        # NO client_assertion.
        # -----------------------------------------------------

        form_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": session.code_verifier,
        }

        token_endpoint = self._normalize_dpop_htu(
            session.token_endpoint
        )

        dpop_proof = self._create_dpop_proof(
            private_key_pem=session.dpop_private_key_pem,
            method="POST",
            url=token_endpoint,
            nonce=session.dpop_nonce,
        )

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:

            response = await client.post(
                token_endpoint,
                data=form_data,
                headers={
                    "Content-Type": (
                        "application/x-www-form-urlencoded"
                    ),
                    "DPoP": dpop_proof,
                },
            )

            nonce = response.headers.get(
                "DPoP-Nonce"
            )

            if (
                response.status_code in (400, 401)
                and nonce
                and nonce != session.dpop_nonce
            ):

                session.dpop_nonce = nonce

                dpop_proof = (
                    self._create_dpop_proof(
                        private_key_pem=(
                            session.dpop_private_key_pem
                        ),
                        method="POST",
                        url=token_endpoint,
                        nonce=nonce,
                    )
                )

                response = await client.post(
                    token_endpoint,
                    data=form_data,
                    headers={
                        "Content-Type": (
                            "application/x-www-form-urlencoded"
                        ),
                        "DPoP": dpop_proof,
                    },
                )

            response.raise_for_status()

            token_data = response.json()

        expires_in = token_data.get("expires_in")

        if expires_in:
            token_data["expires_at"] = (
                datetime.now(timezone.utc)
                + timedelta(seconds=int(expires_in))
            ).isoformat()

        if not token_data.get(
            "access_token"
        ):
            raise RuntimeError(
                "Bluesky OAuth response did not contain "
                "an access token"
            )

        if not token_data.get("sub"):
            raise RuntimeError(
                "Bluesky OAuth response did not contain "
                "the account DID"
            )

        return token_data

    # =========================================================
    # Get Bluesky profile
    # =========================================================

    async def get_user_info(
        self,
        did: str,
    ) -> dict[str, Any]:
        """Look up public account details after OAuth has returned its DID.

        OAuth access tokens are only valid for PDS resources.  The public
        profile endpoint does not require one, so this avoids sending an
        OAuth token to bsky.social's session-management endpoint.
        """

        endpoint = (
            self.settings.bluesky_public_api_url.rstrip("/")
            + "/xrpc/app.bsky.actor.getProfile"
        )

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                endpoint,
                params={"actor": did},
            )

            if response.status_code >= 400:
                print("========== BLUESKY PROFILE ERROR ==========")
                print("STATUS:", response.status_code)
                print("BODY:", response.text)
                print("ENDPOINT:", endpoint)
                print("=========================================")

            response.raise_for_status()

            user_info = response.json()

        return {
            "did": did,
            "handle": user_info.get("handle"),
            "display_name": user_info.get("displayName"),
        }


    async def _get_pds_url(self, did: str) -> str:
        if not did:
            raise ValueError("DID is required to get PDS URL.")

        if did.startswith("did:plc:"):
            did_document_url = ("https://plc.directory/" + did )
        elif did.startswith("did:web:"):
            domain = did[len("did:web:"):]

            if not domain:
                raise ValueError(
                    "Invalid did:web identifier."
                )
            did_document_url = (
                f"https://{domain}/.well-known/did.json"
            )

        else:
            raise ValueError("Unsupported DID format.")

        # Fetch the DID document to get the PDS URL
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:
            response = await client.get(did_document_url)

        if response.status_code >= 400:
            raise RuntimeError(
                "Failed to resolve Bluesky DID document: "
                f"{response.status_code} - "
                f"{response.text}"
            )

        did_document = response.json()

        services =  did_document.get("service", [])

        for service in services:
            if not isinstance(service, dict):
                continue

            service_type = service.get("type")
            service_id = service.get("id")
            service_endpoint = service.get("serviceEndpoint")

            if (
                service_type == "AtprotoPersonalDataServer"
                and (
                    service_id == "#atproto_pds"
                    or service_id == f"{did}#atproto_pds"
                )
                and isinstance(
                    service_endpoint,
                    str,
                )
                and service_endpoint
            ):
                self._require_https_url(
                    service_endpoint,
                    "Bluesky PDS endpoint",
                )

                return service_endpoint.rstrip("/")

            raise RuntimeError(
                "Bluesky DID document does not contain a valid "
            )


    async def publish_post(self, *, access_token: str, dpop_private_key_pem: str, repo: str, content: str) -> dict[str, Any]:
        if not access_token:
            raise ValueError("Access token is required for publishing a post.")

        if not repo:
            raise ValueError("Repository (repo) is required for publishing a post.")

        if not content or not content.strip():
            raise ValueError("Content is required for publishing a post.")

        if not dpop_private_key_pem:
            raise ValueError("DPoP private key PEM is required for publishing a post.")

        pds_url = await self._get_pds_url(
            repo
        )

        endpoint = (
            pds_url
            + "/xrpc/com.atproto.repo.createRecord"
        )

        record = {
            "$type": "app.bsky.feed.post",
            "text": content.strip(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        payload = {
            "repo": repo,
            "collection": "app.bsky.feed.post",
            "record": record,
        }

        dpop_proof = self._create_dpop_proof(
            private_key_pem=dpop_private_key_pem,
            method="POST",
            url=endpoint,
            access_token=access_token,
        )

        header = {
            "Authorization": f"DPoP {access_token}",
            "Content-Type": "application/json",
            "DPoP": dpop_proof,
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
        ) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=header,
            )

            nonce = response.headers.get("DPoP-Nonce")

            if (
                response.status_code in (400, 401)
                and nonce
            ):
                dpop_proof = self._create_dpop_proof(
                    private_key_pem=dpop_private_key_pem,
                    method="POST",
                    url=endpoint,
                    nonce=nonce,
                    access_token=access_token,
                )

                header["DPoP"] = dpop_proof

                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=header,
                )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Failed to publish post: {response.status_code} - {response.text}"
            )

        response_data = response.json()

        uri = response_data.get("uri")
        cid = response_data.get("cid")

        if not uri:
            raise RuntimeError(
                "Bluesky publish response did not contain 'uri'"
            )

        return {
            "platform": "bluesky",
            "platform_post_id": uri,
            "uri": uri,
            "cid": cid,
            "status_code": response.status_code,
            "response": response_data,
        }