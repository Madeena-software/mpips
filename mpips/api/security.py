import os
from typing import Dict, Any, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient

security_scheme = HTTPBearer()


def get_bypass_config() -> Dict[str, Any]:
    return {
        "bypass": os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true",
        "token": os.getenv("DEV_BEARER_TOKEN", "mock_developer_token_xyz"),
    }


def get_idp_config() -> Dict[str, Any]:
    return {
        "jwks_url": os.getenv(
            "MADEENA_IDP_JWKS_URL", "https://sso.madeena.com/.well-known/jwks.json"
        ),
        "scopes": [
            s.strip()
            for s in os.getenv(
                "MADEENA_REQUIRED_SCOPES", "image:process,nodes:read"
            ).split(",")
            if s.strip()
        ],
    }


class JWKSKeyResolver:
    """Lazily resolves signing keys from JWKS to avoid network calls on startup."""

    def __init__(self, jwks_url: str):
        self.jwks_url = jwks_url
        self._jwk_client: PyJWKClient | None = None

    @property
    def jwk_client(self) -> PyJWKClient:
        if self._jwk_client is None:
            self._jwk_client = PyJWKClient(self.jwks_url)
        return self._jwk_client

    def get_signing_key(self, token: str) -> Any:
        return self.jwk_client.get_signing_key_from_jwt(token)


# We instantiate the resolver lazily
_resolver: JWKSKeyResolver | None = None


def get_key_resolver() -> JWKSKeyResolver:
    global _resolver
    if _resolver is None:
        cfg = get_idp_config()
        _resolver = JWKSKeyResolver(cfg["jwks_url"])
    return _resolver


def decode_and_verify_token(token: str, resolver: JWKSKeyResolver) -> Dict[str, Any]:
    try:
        signing_key = resolver.get_signing_key(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_iss": False},
        )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token or signature: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    resolver: JWKSKeyResolver = Depends(get_key_resolver),
) -> Dict[str, Any]:
    token = credentials.credentials
    bypass_cfg = get_bypass_config()

    if bypass_cfg["bypass"]:
        if token == bypass_cfg["token"]:
            # Returns a mock payload matching the required scopes
            idp_cfg = get_idp_config()
            return {
                "sub": "mock-client-id",
                "scope": " ".join(idp_cfg["scopes"]),
                "tenant_id": "default-tenant-id",
                "bypass": True,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid developer bypass token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Decode and verify against JWKS IDP
    payload = decode_and_verify_token(token, resolver)

    # Scope validation
    idp_cfg = get_idp_config()
    scopes_str = payload.get("scope", "")
    scopes: List[str] = [s.strip() for s in scopes_str.split(" ") if s.strip()]

    for required_scope in idp_cfg["scopes"]:
        if required_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )

    return payload
