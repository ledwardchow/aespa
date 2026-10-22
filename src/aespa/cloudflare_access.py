from __future__ import annotations

import time

import httpx
import jwt

JWT_HEADER = "cf-access-jwt-assertion"
JWKS_CACHE_TTL = 3600.0
_JWKS_CACHE: dict[str, tuple[dict, float]] = {}


def _get_jwks(issuer: str) -> dict:
    now = time.time()
    if issuer in _JWKS_CACHE:
        keys, expiry = _JWKS_CACHE[issuer]
        if now < expiry:
            return keys

    from aespa.services.llm_network import httpx_options

    resp = httpx.get(
        f"{issuer.rstrip('/')}/cdn-cgi/access/certs", **httpx_options()
    )
    resp.raise_for_status()
    keys = resp.json()
    _JWKS_CACHE[issuer] = (keys, now + JWKS_CACHE_TTL)
    return keys


def team_issuer(team_domain: str) -> str:
    host = team_domain.strip().removeprefix("https://").rstrip("/")
    return f"https://{host}"


def verify_jwt(
    token: str, audience: str | None = None, issuer: str | None = None
) -> dict | None:
    """Return the verified claims of a Cloudflare Access JWT, or None.

    Without an audience any Cloudflare Access tenant's token passes, so callers
    that grant access must pass both ``audience`` and ``issuer``.
    """
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        token_issuer = unverified.get("iss")
        if (
            not token_issuer
            or not token_issuer.startswith("https://")
            or not token_issuer.endswith(".cloudflareaccess.com")
            or (issuer is not None and token_issuer.rstrip("/") != issuer)
        ):
            return None

        kid = jwt.get_unverified_header(token).get("kid")
        if not kid:
            return None
        jwk = next(
            (k for k in _get_jwks(token_issuer).get("keys", []) if k.get("kid") == kid),
            None,
        )
        if not jwk:
            return None

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        if audience:
            return jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
                issuer=token_issuer,
            )
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except Exception:
        return None
