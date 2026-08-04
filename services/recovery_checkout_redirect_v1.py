# -*- coding: utf-8 -*-
"""
Recovery checkout redirect tokens V1.

Mint / resolve opaque signed tokens for Meta URL-button {{1}}.
Destination URL is encrypted inside the token — never returned in error bodies.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

log = logging.getLogger(__name__)

TOKEN_VERSION = "v1"
DEFAULT_TTL_SECONDS = 14 * 24 * 3600  # 14 days
MAX_TOKEN_LEN = 1800

ERROR_MISSING = "missing_token"
ERROR_MALFORMED = "malformed_token"
ERROR_INVALID = "invalid_token"
ERROR_EXPIRED = "expired_token"
ERROR_ARCHIVED = "archived_recovery"
ERROR_LEGACY_INVALID = "invalid_checkout_token"


def _signing_secret() -> bytes:
    raw = (
        (os.getenv("SECRET_KEY") or "").strip()
        or (os.getenv("CARTFLOW_CHECKOUT_TOKEN_SECRET") or "").strip()
        or "dev-only-change-in-production"
    )
    return raw.encode("utf-8")


def _url_crypt_key() -> bytes:
    return hashlib.sha256(_signing_secret() + b"|checkout-url-v1").digest()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> Optional[bytes]:
    s = (raw or "").strip()
    if not s:
        return None
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    try:
        return base64.urlsafe_b64decode((s + pad).encode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return None


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _encrypt_destination(url: str) -> str:
    enc = _xor_crypt(url.encode("utf-8"), _url_crypt_key())
    return _b64url_encode(enc)


def _decrypt_destination(token_field: str) -> Optional[str]:
    raw = _b64url_decode(token_field)
    if raw is None:
        return None
    try:
        url = _xor_crypt(raw, _url_crypt_key()).decode("utf-8")
    except UnicodeDecodeError:
        return None
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return url


def _sign(payload_b64: str) -> str:
    dig = hmac.new(_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(dig[:16])


@dataclass(frozen=True)
class CheckoutRedirectClaims:
    destination_url: str
    recovery_key: str = ""
    store_slug: str = ""
    template_name: str = ""
    message_id: str = ""
    customer_phone: str = ""
    provider: str = ""
    provider_message_id: str = ""
    exp: int = 0
    legacy: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        """Safe view — never includes destination_url."""
        return {
            "recovery_key": self.recovery_key or None,
            "store_slug": self.store_slug or None,
            "template_name": self.template_name or None,
            "message_id": self.message_id or None,
            "customer_phone": self.customer_phone or None,
            "provider": self.provider or None,
            "provider_message_id": self.provider_message_id or None,
            "exp": self.exp or None,
            "legacy": self.legacy,
        }


@dataclass(frozen=True)
class CheckoutTokenResolveResult:
    ok: bool
    error_code: Optional[str] = None
    claims: Optional[CheckoutRedirectClaims] = None


def mint_checkout_redirect_token(
    *,
    checkout_url: str,
    recovery_key: str = "",
    store_slug: str = "",
    template_name: str = "",
    message_id: str = "",
    customer_phone: str = "",
    provider: str = "",
    provider_message_id: str = "",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now_ts: Optional[int] = None,
) -> Optional[str]:
    """
    Mint opaque signed token for /wa/checkout/{token}.
    Returns None if checkout_url invalid or token would exceed Meta length budget.
    """
    from urllib.parse import urlparse

    u = (checkout_url or "").strip()
    if not u:
        return None
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None

    now = int(now_ts if now_ts is not None else time.time())
    ttl = max(60, int(ttl_seconds or DEFAULT_TTL_SECONDS))
    body = {
        "v": 1,
        "exp": now + ttl,
        "u": _encrypt_destination(u),
        "rk": (recovery_key or "")[:120],
        "ss": (store_slug or "")[:255],
        "tn": (template_name or "")[:128],
        "mid": (message_id or "")[:128],
        "ph": (customer_phone or "")[:40],
        "p": (provider or "")[:32],
        "pmid": (provider_message_id or "")[:128],
    }
    try:
        payload_b64 = _b64url_encode(
            json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        )
    except (TypeError, ValueError):
        return None
    sig = _sign(payload_b64)
    token = f"{TOKEN_VERSION}.{payload_b64}.{sig}"
    if len(token) > MAX_TOKEN_LEN:
        return None
    return token


def _resolve_signed_token(token: str, *, now_ts: int) -> CheckoutTokenResolveResult:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != TOKEN_VERSION:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)
    payload_b64, sig = parts[1], parts[2]
    if not payload_b64 or not sig:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)
    expected = _sign(payload_b64)
    if not hmac.compare_digest(sig, expected):
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_INVALID)
    raw = _b64url_decode(payload_b64)
    if raw is None:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)
    if not isinstance(body, dict):
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)
    try:
        exp = int(body.get("exp") or 0)
    except (TypeError, ValueError):
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)
    if exp and now_ts > exp:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_EXPIRED)
    dest = _decrypt_destination(str(body.get("u") or ""))
    if not dest:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_INVALID)
    claims = CheckoutRedirectClaims(
        destination_url=dest,
        recovery_key=str(body.get("rk") or "")[:120],
        store_slug=str(body.get("ss") or "")[:255],
        template_name=str(body.get("tn") or "")[:128],
        message_id=str(body.get("mid") or "")[:128],
        customer_phone=str(body.get("ph") or "")[:40],
        provider=str(body.get("p") or "")[:32],
        provider_message_id=str(body.get("pmid") or "")[:128],
        exp=exp,
        legacy=False,
    )
    return CheckoutTokenResolveResult(ok=True, claims=claims)


def _resolve_legacy_plain_url_token(token: str) -> CheckoutTokenResolveResult:
    """Backward-compat: previous base64url(checkout_url) tokens."""
    from services.meta_recovery_template_contract_v1 import decode_checkout_url_button_param

    dest = decode_checkout_url_button_param(token)
    if not dest:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_LEGACY_INVALID)
    return CheckoutTokenResolveResult(
        ok=True,
        claims=CheckoutRedirectClaims(
            destination_url=dest,
            legacy=True,
        ),
    )


def is_recovery_archived(recovery_key: str) -> bool:
    """True when merchant lifecycle archive marks this recovery_key archived."""
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    try:
        from extensions import db
        from models import MerchantCartLifecycleArchive

        row = (
            db.session.query(MerchantCartLifecycleArchive)
            .filter(MerchantCartLifecycleArchive.recovery_key == rk[:512])
            .first()
        )
        if row is None:
            return False
        return bool(getattr(row, "is_archived", False))
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[CHECKOUT REDIRECT] archive_lookup_failed err=%s",
            type(exc).__name__,
        )
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        # Fail open for archive check — do not block customer redirect
        return False


def resolve_checkout_redirect_token(
    token: Optional[str],
    *,
    now_ts: Optional[int] = None,
    check_archived: bool = True,
) -> CheckoutTokenResolveResult:
    """
    Resolve token to claims. Never puts destination_url in error responses.
    """
    raw = (token or "").strip()
    if not raw:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MISSING)
    if len(raw) > 2000:
        return CheckoutTokenResolveResult(ok=False, error_code=ERROR_MALFORMED)

    now = int(now_ts if now_ts is not None else time.time())

    if raw.startswith(TOKEN_VERSION + "."):
        result = _resolve_signed_token(raw, now_ts=now)
    else:
        # Reject obvious garbage before legacy decode
        if "." in raw and not raw.startswith("http"):
            # Might be corrupted signed token
            result = _resolve_signed_token(raw, now_ts=now)
            if not result.ok:
                result = _resolve_legacy_plain_url_token(raw)
        else:
            result = _resolve_legacy_plain_url_token(raw)

    if not result.ok or result.claims is None:
        return result

    if check_archived and result.claims.recovery_key:
        if is_recovery_archived(result.claims.recovery_key):
            return CheckoutTokenResolveResult(ok=False, error_code=ERROR_ARCHIVED)

    return result


def mint_token_from_send_context(
    context: Mapping[str, Any],
    *,
    checkout_url: str,
    template_name: str = "",
) -> Optional[str]:
    """Mint from Meta send context fields."""
    phone = ""
    for key in ("customer_phone", "to_phone", "phone"):
        v = context.get(key)
        if isinstance(v, str) and v.strip():
            phone = "".join(c for c in v if c.isdigit())[:40]
            break
    return mint_checkout_redirect_token(
        checkout_url=checkout_url,
        recovery_key=str(context.get("recovery_key") or "")[:120],
        store_slug=str(context.get("store_slug") or "")[:255],
        template_name=(template_name or str(context.get("template_name") or ""))[:128],
        message_id=str(context.get("message_id") or context.get("idempotency_key") or "")[
            :128
        ],
        customer_phone=phone,
        provider=str(context.get("provider") or "meta")[:32],
        provider_message_id=str(
            context.get("provider_message_id") or context.get("external_message_id") or ""
        )[:128],
    )


__all__ = [
    "TOKEN_VERSION",
    "DEFAULT_TTL_SECONDS",
    "ERROR_MISSING",
    "ERROR_MALFORMED",
    "ERROR_INVALID",
    "ERROR_EXPIRED",
    "ERROR_ARCHIVED",
    "CheckoutRedirectClaims",
    "CheckoutTokenResolveResult",
    "mint_checkout_redirect_token",
    "mint_token_from_send_context",
    "resolve_checkout_redirect_token",
    "is_recovery_archived",
]
