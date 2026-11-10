"""Authentication and channel authorization for the MPIPS staging update server."""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass

STAGING_READ_SCOPE = "staging:read"


class AuthenticationError(RuntimeError):
    """Client failed to supply valid authentication credentials."""


class AuthorizationError(RuntimeError):
    """Authenticated client is not permitted to access the requested channel."""


@dataclass(frozen=True)
class AuthenticatedClient:
    """Verified client identity and its granted scopes."""

    client_id: str
    scopes: frozenset[str]


class ClientAuthenticator:
    """Constant-time token authenticator with explicit channel scope checks."""

    def __init__(
        self,
        token_scopes: Mapping[str, set[str] | frozenset[str] | str] | None = None,
    ) -> None:
        resolved: list[tuple[str, frozenset[str]]] = []
        if token_scopes is not None:
            for token, scopes in token_scopes.items():
                clean_token = token.strip()
                if not clean_token:
                    raise ValueError("Configured client token must not be empty")
                if isinstance(scopes, str):
                    scope_set = frozenset(
                        s.strip() for s in scopes.split(",") if s.strip()
                    )
                else:
                    scope_set = frozenset(scopes)
                resolved.append((clean_token, scope_set))
        else:
            reader_token = os.getenv("MPIPS_UPDATE_STAGING_READER_TOKEN", "").strip()
            if reader_token:
                resolved.append((reader_token, frozenset({STAGING_READ_SCOPE})))
            allow_api_key = os.getenv(
                "MPIPS_UPDATE_ALLOW_API_KEY_AUTH", "false"
            ).lower() in ("1", "true", "yes")
            if allow_api_key:
                api_key = os.getenv("MPIPS_API_KEY", "").strip()
                if api_key and "replace-with" not in api_key:
                    resolved.append((api_key, frozenset({STAGING_READ_SCOPE})))
        self._credentials = tuple(resolved)

    def authenticate_staging_reader(
        self,
        *,
        authorization_header: str | None = None,
        api_key_header: str | None = None,
    ) -> AuthenticatedClient:
        """Authenticate client and verify permission for the staging channel."""
        candidate = ""
        if authorization_header and authorization_header.startswith("Bearer "):
            candidate = authorization_header[7:].strip()
        elif api_key_header:
            candidate = api_key_header.strip()

        if not candidate or not self._credentials:
            raise AuthenticationError("Valid staging client token required")

        matched_scopes: frozenset[str] | None = None
        matched_index = -1
        for idx, (expected_token, scopes) in enumerate(self._credentials):
            if secrets.compare_digest(candidate, expected_token):
                matched_scopes = scopes
                matched_index = idx

        if matched_scopes is None:
            raise AuthenticationError("Valid staging client token required")

        if STAGING_READ_SCOPE not in matched_scopes:
            raise AuthorizationError(
                "Authenticated client is not authorized for staging channel"
            )

        return AuthenticatedClient(
            client_id=f"staging-client-{matched_index}",
            scopes=matched_scopes,
        )
