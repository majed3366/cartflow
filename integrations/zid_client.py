# -*- coding: utf-8 -*-
"""
Zid API client — ‎OAuth‎، الويبهوك، بيانات المتجر. لا تسجيل لرموز الدخول أو الأسرار.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple, TYPE_CHECKING
from urllib.parse import urlencode, urlparse

import requests

if TYPE_CHECKING:
    from starlette.requests import Request as StarletteRequest
else:
    StarletteRequest = Any

log = logging.getLogger("cartflow")


def _release_before_zid_http() -> None:
    try:
        from services.db_resource_safety_v1.release_before_wait_v1 import (
            release_before_external_wait,
        )

        release_before_external_wait(reason="zid_http")
    except Exception:  # noqa: BLE001
        pass


def _zid_get(*args: Any, **kwargs: Any) -> Any:
    _release_before_zid_http()
    return requests.get(*args, **kwargs)


def _zid_post(*args: Any, **kwargs: Any) -> Any:
    _release_before_zid_http()
    return requests.post(*args, **kwargs)

ZID_OAUTH_BASE = (os.getenv("ZID_OAUTH_BASE") or "https://oauth.zid.sa").rstrip("/")
_DEFAULT_OAUTH_CALLBACK = "https://smartreplyai.net/auth/callback"
ZID_API_BASE = (os.getenv("ZID_API_BASE") or "https://api.zid.sa/v1").rstrip("/")
ZID_PROFILE_API = os.getenv(
    "ZID_PROFILE_API_URL", "https://api.zid.sa/v1/managers/account/profile"
)
ZID_OAUTH_TOKEN_URL = f"{ZID_OAUTH_BASE}/oauth/token"
ZID_OAUTH_AUTHORIZE_URL = f"{ZID_OAUTH_BASE}/oauth/authorize"
# Minimal CartFlow scopes — must be enabled in Partner Dashboard Application Scopes.
# Override with ZID_OAUTH_SCOPE (space-separated). Set ZID_OAUTH_SCOPE= to omit scope.
_DEFAULT_ZID_OAUTH_SCOPE = "abandoned_carts.read orders.read"


def get_oauth_redirect_uri() -> str:
    """
    OAuth callback URL sent to Zid — must match Partner Dashboard allowed redirection URLs.

    Priority: OAUTH_REDIRECT_URI → CARTFLOW_PUBLIC_BASE_URL/auth/callback → default.
    """
    explicit = (os.getenv("OAUTH_REDIRECT_URI") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    base = (
        os.getenv("CARTFLOW_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or ""
    ).strip().rstrip("/")
    if base:
        return f"{base}/auth/callback"
    return _DEFAULT_OAUTH_CALLBACK


# Back-compat: callers that read module constant see resolved value at import time.
OAUTH_REDIRECT_URI = get_oauth_redirect_uri()


def _oauth_redirect_uri_source_tag() -> str:
    if (os.getenv("OAUTH_REDIRECT_URI") or "").strip():
        return "OAUTH_REDIRECT_URI"
    base = (
        os.getenv("CARTFLOW_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or ""
    ).strip()
    if base:
        return "public_base_url"
    return "default"


def emit_zid_oauth_trace(tag: str, **fields: Any) -> None:
    """Safe structured OAuth logs — never tokens or secrets."""
    lines = [f"[{tag}]"]
    for k, v in fields.items():
        if v is None:
            continue
        lines.append(f"{k}={str(v)[:220]}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def get_zid_oauth_scope() -> str:
    """
    OAuth scope string for authorize URL (space-separated per Zid docs).

    Unset ZID_OAUTH_SCOPE → default minimal CartFlow scopes.
    ZID_OAUTH_SCOPE= (empty) → omit scope param (legacy/debug).
    """
    if "ZID_OAUTH_SCOPE" in os.environ:
        return (os.environ.get("ZID_OAUTH_SCOPE") or "").strip()
    return _DEFAULT_ZID_OAUTH_SCOPE


def _safe_authorize_url_for_log(authorize_url: str, *, client_id: str) -> str:
    """Authorize URL with client_id redacted — safe to copy from logs for manual browser test."""
    cid = (client_id or "").strip()
    if not cid:
        return authorize_url[:512]
    return authorize_url.replace(cid, "[REDACTED]", 1)[:512]


def zid_oauth_start_trace(
    *,
    authorize_url: str,
    query: dict[str, str],
    client_id_present: bool,
) -> None:
    redirect_uri = query.get("redirect_uri") or get_oauth_redirect_uri()
    redirect_parsed = urlparse(redirect_uri)
    auth_parsed = urlparse(authorize_url)
    emit_zid_oauth_trace(
        "ZID OAUTH START",
        authorize_host=(auth_parsed.netloc or "-")[:128],
        authorize_path=(auth_parsed.path or "-")[:128],
        response_type=(query.get("response_type") or "-")[:32],
        client_id_present=str(bool(client_id_present)).lower(),
        redirect_uri=redirect_uri,
        redirect_host=(redirect_parsed.netloc or "-")[:128],
        redirect_path=(redirect_parsed.path or "-")[:128],
        redirect_source=_oauth_redirect_uri_source_tag(),
        scope=(query.get("scope") or "-")[:128],
        scope_source=(
            "env"
            if "ZID_OAUTH_SCOPE" in os.environ
            else ("default" if query.get("scope") else "omitted")
        )[:32],
        state_present=str(bool((query.get("state") or "").strip())).lower(),
        state_len=str(len((query.get("state") or ""))),
        authorize_url_safe=_safe_authorize_url_for_log(
            authorize_url,
            client_id=query.get("client_id") or "",
        ),
    )


def zid_oauth_callback_trace(
    *,
    has_code: bool,
    has_state: bool,
    query_keys: str = "-",
) -> None:
    emit_zid_oauth_trace(
        "ZID OAUTH CALLBACK HIT",
        has_code=str(bool(has_code)).lower(),
        has_state=str(bool(has_state)).lower(),
        query_keys=(query_keys or "-")[:256],
    )


def zid_oauth_token_exchange_trace(
    *,
    success: bool,
    status_code: int,
    detail: str = "",
    authorization_present: Optional[bool] = None,
) -> None:
    fields: dict[str, str] = {
        "success": str(bool(success)).lower(),
        "status_code": str(int(status_code)),
        "detail": (detail or "-")[:128],
    }
    if authorization_present is not None:
        fields["authorization_present"] = str(bool(authorization_present)).lower()
    emit_zid_oauth_trace("ZID OAUTH TOKEN EXCHANGE", **fields)


def zid_oauth_store_linked_trace(
    *,
    store_slug: str = "",
    merchant_user_id: Optional[int] = None,
    store_id: Optional[int] = None,
) -> None:
    emit_zid_oauth_trace(
        "ZID OAUTH STORE LINKED",
        store_slug=(store_slug or "-")[:128],
        merchant_user_id=str(int(merchant_user_id)) if merchant_user_id is not None else "-",
        store_id=str(int(store_id)) if store_id is not None else "-",
    )


def parse_zid_authorization_from_token_response(
    token_response: dict[str, Any],
) -> Optional[str]:
    """OAuth ``Authorization`` field (Bearer value without prefix)."""
    raw = token_response.get("Authorization")
    if raw is None:
        raw = token_response.get("authorization")
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.lower().startswith("bearer "):
        s = s[7:].strip()
    return s or None


def parse_zid_store_id_from_token(data: dict[str, Any]) -> Optional[str]:
    for key in ("zid_store_id", "store_id", "merchant_id"):
        v = data.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    store = data.get("store")
    if isinstance(store, dict) and store.get("id") is not None:
        return str(store["id"]).strip()
    user = data.get("user")
    if isinstance(user, dict) and user.get("store_id") is not None:
        return str(user["store_id"]).strip()
    return None


ZID_MANAGER_AUTH_INCOMPLETE = "zid_manager_auth_incomplete"
ZID_MANAGER_CROSS_STORE_REJECTED = "zid_manager_cross_store_rejected"


def _strip_bearer_prefix(raw: str) -> str:
    s = (raw or "").strip()
    if s.lower().startswith("bearer "):
        return s[7:].strip()
    return s


def zid_manager_auth_state(store: Any) -> dict[str, Any]:
    """Presence-only Manager auth state for one store row. Never includes secrets."""
    store_id = getattr(store, "id", None) if store is not None else None
    access_present = bool(
        (getattr(store, "access_token", None) or "").strip()
    ) if store is not None else False
    auth_present = bool(
        (getattr(store, "zid_authorization_token", None) or "").strip()
    ) if store is not None else False
    missing: list[str] = []
    if not auth_present:
        missing.append("zid_authorization_token")
    if not access_present:
        missing.append("access_token")
    return {
        "store_id": store_id,
        "access_token": "present" if access_present else "missing",
        "zid_authorization_token": "present" if auth_present else "missing",
        "ready": not missing,
        "missing": missing,
        "error": None if not missing else ZID_MANAGER_AUTH_INCOMPLETE,
    }


def _manager_header_dict(*, authorization: str, access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_strip_bearer_prefix(authorization)}",
        "X-MANAGER-TOKEN": (access_token or "").strip(),
        "Accept": "application/json",
        "Accept-Language": "en",
    }


def manager_headers_for_store(
    store: Any,
) -> Tuple[Optional[dict[str, str]], Optional[dict[str, Any]]]:
    """
    Dual-header Manager contract from ONE canonical store row.

    Authorization ← stores.zid_authorization_token
    X-MANAGER-TOKEN ← stores.access_token
    No ZID_API_AUTHORIZATION fallback.
    """
    state = zid_manager_auth_state(store)
    if not state["ready"]:
        err = {
            "error": ZID_MANAGER_AUTH_INCOMPLETE,
            "missing": list(state["missing"]),
            "store_id": state["store_id"],
        }
        try:
            log.info(
                "[ZID MANAGER AUTH] incomplete store_id=%s missing=%s",
                state["store_id"] if state["store_id"] is not None else "-",
                ",".join(state["missing"]),
            )
        except Exception:  # noqa: BLE001
            pass
        return None, err
    access = (getattr(store, "access_token", None) or "").strip()
    auth = (getattr(store, "zid_authorization_token", None) or "").strip()
    return _manager_header_dict(authorization=auth, access_token=access), None


def manager_headers_for_oauth_grant(
    token_response: dict[str, Any],
) -> Tuple[Optional[dict[str, str]], Optional[dict[str, Any]]]:
    """Same-grant pair from one token-exchange body. Used before persist."""
    access = (token_response.get("access_token") or "").strip()
    auth = parse_zid_authorization_from_token_response(token_response)
    missing: list[str] = []
    if not auth:
        missing.append("Authorization")
    if not access:
        missing.append("access_token")
    if missing:
        return None, {
            "error": ZID_MANAGER_AUTH_INCOMPLETE,
            "missing": missing,
            "source": "oauth_grant",
        }
    return _manager_header_dict(authorization=str(auth), access_token=access), None


def manager_headers_from_explicit_pair(
    *,
    store: Any,
    authorization_token: str,
    access_token: str,
) -> Tuple[Optional[dict[str, str]], Optional[dict[str, Any]]]:
    """
    Reject unless both provided values match the same store row.
    Prevents Store A Authorization + Store B manager token.
    """
    state = zid_manager_auth_state(store)
    if not state["ready"]:
        return None, {
            "error": ZID_MANAGER_AUTH_INCOMPLETE,
            "missing": list(state["missing"]),
            "store_id": state["store_id"],
        }
    row_auth = _strip_bearer_prefix(getattr(store, "zid_authorization_token", None) or "")
    row_access = (getattr(store, "access_token", None) or "").strip()
    given_auth = _strip_bearer_prefix(authorization_token)
    given_access = (access_token or "").strip()
    auth_ok = bool(row_auth) and bool(given_auth) and hmac.compare_digest(
        row_auth, given_auth
    )
    access_ok = bool(row_access) and bool(given_access) and hmac.compare_digest(
        row_access, given_access
    )
    if not auth_ok or not access_ok:
        return None, {
            "error": ZID_MANAGER_CROSS_STORE_REJECTED,
            "store_id": state["store_id"],
        }
    return manager_headers_for_store(store)


def reject_cross_store_manager_pair(
    *,
    authorization_store: Any,
    manager_token_store: Any,
) -> Tuple[Optional[dict[str, str]], Optional[dict[str, Any]]]:
    a_id = getattr(authorization_store, "id", None) if authorization_store is not None else None
    b_id = getattr(manager_token_store, "id", None) if manager_token_store is not None else None
    if a_id is None or b_id is None or int(a_id) != int(b_id):
        return None, {
            "error": ZID_MANAGER_CROSS_STORE_REJECTED,
            "authorization_store_id": a_id,
            "manager_token_store_id": b_id,
        }
    return manager_headers_for_store(authorization_store)


def _manager_get_json(
    url: str,
    headers: dict[str, str],
    *,
    params: Optional[dict[str, Any]] = None,
    timeout: int = 20,
) -> Tuple[Optional[dict[str, Any]], int]:
    try:
        r = _zid_get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException:
        return None, 0
    try:
        body: Any = r.json()
    except Exception:
        return None, r.status_code
    if isinstance(body, dict):
        return body, r.status_code
    return None, r.status_code


def fetch_zid_manager_profile(store: Any) -> Optional[dict[str, Any]]:
    """Full manager profile JSON — used for store identity sync."""
    headers, err = manager_headers_for_store(store)
    if err or not headers:
        return None
    body, status = _manager_get_json(ZID_PROFILE_API, headers)
    if status // 100 != 2 or not isinstance(body, dict):
        return None
    return body


def fetch_zid_manager_store_payload(store: Any) -> Optional[dict[str, Any]]:
    """Full JSON from GET /v1/managers/account/store — often has storefront URL."""
    headers, err = manager_headers_for_store(store)
    if err or not headers:
        return None
    body, status = _manager_get_json(ZID_MANAGER_STORE_URL, headers)
    if status // 100 != 2 or not isinstance(body, dict):
        return None
    return body


def _store_id_from_manager_profile_json(j: Any) -> Optional[str]:
    if not isinstance(j, dict):
        return None
    for path in (
        ("data", "store", "id"),
        ("data", "store_id"),
        ("store", "id"),
        ("user", "store", "id"),
    ):
        cur: Any = j
        for p in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(p)
        if cur is not None and str(cur).strip():
            return str(cur).strip()
    return None


def fetch_zid_store_id_from_profile(store: Any) -> Optional[str]:
    return _store_id_from_manager_profile_json(fetch_zid_manager_profile(store))


def fetch_zid_store_id_from_oauth_grant(token_response: dict[str, Any]) -> Optional[str]:
    """Profile store id using the same OAuth grant pair. Fail closed if Authorization missing."""
    headers, err = manager_headers_for_oauth_grant(token_response)
    if err or not headers:
        return None
    body, status = _manager_get_json(ZID_PROFILE_API, headers)
    if status // 100 != 2:
        return None
    return _store_id_from_manager_profile_json(body)


def persist_oauth_tokens_on_store_row(
    row: Any,
    token_response: dict[str, Any],
) -> bool:
    """
    Write OAuth tokens onto an existing Store row (no latest-store fallback).

    Never overwrites ``stores.zid_store_id`` (CartFlow identity).
    Does not write ``connected_at`` (verified connection owns that stamp).
    Does not call Manager HTTP.
    """
    access = (token_response.get("access_token") or "").strip()
    if not access:
        return False
    refresh: Optional[str] = None
    r = token_response.get("refresh_token")
    if r is not None and str(r).strip():
        refresh = str(r).strip()
    exp: Optional[datetime] = None
    ei = token_response.get("expires_in")
    if isinstance(ei, (int, float)):
        exp = datetime.now(timezone.utc) + timedelta(seconds=float(ei))
    row.access_token = access
    auth = parse_zid_authorization_from_token_response(token_response)
    # New grant must not keep a previous Authorization paired with a new manager token.
    row.zid_authorization_token = auth
    if refresh is not None:
        row.refresh_token = refresh
    row.token_expires_at = exp
    row.is_active = True
    try:
        attempts = int(getattr(row, "recovery_attempts", 0) or 0)
    except (TypeError, ValueError):
        attempts = 0
    if attempts < 1:
        row.recovery_attempts = 1
    return True


def probe_zid_manager_store(
    store: Any,
    *,
    timeout_s: float = 8.0,
) -> Tuple[Optional[dict[str, Any]], int, str]:
    """
    One inexpensive read-only Manager probe for connection verification.

    GET /v1/managers/account/store — store identity, not a merchant data dump.
    Returns (json_or_none, http_status, outcome) where outcome is
    ok | auth_incomplete | auth_rejected | unavailable.
    Never logs secrets or response bodies.
    """
    headers, err = manager_headers_for_store(store)
    if err or not headers:
        return None, 0, "auth_incomplete"
    url = f"{ZID_API_BASE}/managers/account/store"
    try:
        r = requests.get(url, headers=headers, timeout=float(timeout_s))
    except requests.Timeout:
        return None, 0, "unavailable"
    except requests.RequestException:
        return None, 0, "unavailable"
    status = int(r.status_code)
    if status in (401, 403):
        try:
            log.info(
                "[ZID MANAGER PROBE] store_id=%s http_status=%s outcome=auth_rejected",
                getattr(store, "id", None) if store is not None else "-",
                status,
            )
        except Exception:  # noqa: BLE001
            pass
        return None, status, "auth_rejected"
    if status // 100 != 2:
        try:
            log.info(
                "[ZID MANAGER PROBE] store_id=%s http_status=%s outcome=unavailable",
                getattr(store, "id", None) if store is not None else "-",
                status,
            )
        except Exception:  # noqa: BLE001
            pass
        return None, status, "unavailable"
    try:
        body: Any = r.json()
    except Exception:
        return None, status, "unavailable"
    if not isinstance(body, dict):
        return None, status, "unavailable"
    try:
        log.info(
            "[ZID MANAGER PROBE] store_id=%s http_status=%s outcome=ok",
            getattr(store, "id", None) if store is not None else "-",
            status,
        )
    except Exception:  # noqa: BLE001
        pass
    return body, status, "ok"


def zid_oauth_configured() -> bool:
    return bool((os.getenv("ZID_CLIENT_ID") or "").strip()) and bool(
        (os.getenv("ZID_CLIENT_SECRET") or "").strip()
    )


def build_zid_authorize_url(*, state: str = "") -> Tuple[Optional[str], Optional[dict]]:
    """
    Build Zid OAuth authorize redirect URL.
    Returns (url, error_payload) — error_payload when OAuth env is missing.
    """
    client_id = (os.getenv("ZID_CLIENT_ID") or "").strip()
    if not zid_oauth_configured():
        missing: list[str] = []
        if not client_id:
            missing.append("ZID_CLIENT_ID")
        if not (os.getenv("ZID_CLIENT_SECRET") or "").strip():
            missing.append("ZID_CLIENT_SECRET")
        return (
            None,
            {
                "error": "oauth_not_configured",
                "message_ar": "ميزة الربط قيد الإعداد",
                "missing_environment_variables": missing,
            },
        )
    redirect_uri = get_oauth_redirect_uri()
    q: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }
    scope = get_zid_oauth_scope()
    if scope:
        q["scope"] = scope
    st = (state or "").strip()
    if st:
        q["state"] = st
    authorize_url = f"{ZID_OAUTH_AUTHORIZE_URL}?{urlencode(q)}"
    zid_oauth_start_trace(
        authorize_url=authorize_url,
        query=q,
        client_id_present=bool(client_id),
    )
    return authorize_url, None


def exchange_code_for_token(code: str) -> Tuple[dict, int]:
    client_id = (os.getenv("ZID_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("ZID_CLIENT_SECRET") or "").strip()
    missing: list[str] = []
    if not client_id:
        missing.append("ZID_CLIENT_ID")
    if not client_secret:
        missing.append("ZID_CLIENT_SECRET")
    if missing:
        return (
            {
                "error": "OAuth is not configured: set the following in the server environment",
                "missing_environment_variables": missing,
            },
            500,
        )
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": get_oauth_redirect_uri(),
        "code": code,
    }
    try:
        tr = _zid_post(
            ZID_OAUTH_TOKEN_URL,
            data=payload,
            timeout=30,
        )
    except requests.RequestException as e:
        zid_oauth_token_exchange_trace(success=False, status_code=502, detail="request_failed")
        return (
            {
                "error": "Failed to reach Zid OAuth token endpoint",
                "detail": str(e),
            },
            502,
        )
    try:
        body: Any = tr.json()
    except Exception:
        zid_oauth_token_exchange_trace(
            success=False, status_code=tr.status_code, detail="non_json_response"
        )
        return (
            {
                "error": "Zid returned a non-JSON response",
                "http_status": tr.status_code,
                "raw": (tr.text or "")[:4000],
            },
            tr.status_code,
        )
    ok = 200 <= tr.status_code < 300 and isinstance(body, dict) and bool(
        (body.get("access_token") or "").strip()
    )
    err_hint = ""
    auth_present: Optional[bool] = None
    if isinstance(body, dict):
        auth_present = bool(parse_zid_authorization_from_token_response(body))
    if isinstance(body, dict) and not ok:
        err_hint = str(body.get("error") or body.get("message") or "")[:128]
    zid_oauth_token_exchange_trace(
        success=ok,
        status_code=tr.status_code,
        detail=err_hint or ("ok" if ok else "no_access_token"),
        authorization_present=auth_present,
    )
    if isinstance(body, dict):
        return (body, tr.status_code)
    return ({"response": body}, tr.status_code)


def fetch_abandoned_carts(store: Any) -> Tuple[dict, int]:
    headers, err = manager_headers_for_store(store)
    if err or not headers:
        return (err or {"error": ZID_MANAGER_AUTH_INCOMPLETE}, 409)
    url = f"{ZID_API_BASE}/managers/store/abandoned-carts"
    try:
        r = _zid_get(
            url,
            params={"page": 1, "page_size": 20},
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as e:
        return ({"error": "request_failed", "detail": str(e)}, 502)
    try:
        body: Any = r.json()
    except Exception:
        return ({"raw": (r.text or "")[:2000], "http_status": r.status_code}, r.status_code)
    if isinstance(body, dict):
        return (body, r.status_code)
    return ({"data": body}, r.status_code)


def fetch_orders(
    store: Any,
    *,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[dict, int]:
    headers, err = manager_headers_for_store(store)
    if err or not headers:
        return (err or {"error": ZID_MANAGER_AUTH_INCOMPLETE}, 409)
    url = f"{ZID_API_BASE}/managers/store/orders"
    try:
        r = _zid_get(
            url,
            params={"page": int(page), "page_size": int(page_size)},
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as e:
        return ({"error": "request_failed", "detail": str(e)}, 502)
    try:
        body: Any = r.json()
    except Exception:
        return ({"raw": (r.text or "")[:2000], "http_status": r.status_code}, r.status_code)
    if isinstance(body, dict):
        return (body, r.status_code)
    return ({"data": body}, r.status_code)


def fetch_order_view(store: Any, order_id: str) -> Tuple[dict, int]:
    oid = str(order_id or "").strip()
    if not oid:
        return ({"error": "order_id_required"}, 400)
    headers, err = manager_headers_for_store(store)
    if err or not headers:
        return (err or {"error": ZID_MANAGER_AUTH_INCOMPLETE}, 409)
    url = f"{ZID_API_BASE}/managers/store/orders/{oid}/view"
    try:
        r = _zid_get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        return ({"error": "request_failed", "detail": str(e)}, 502)
    try:
        body: Any = r.json()
    except Exception:
        return ({"raw": (r.text or "")[:2000], "http_status": r.status_code}, r.status_code)
    if isinstance(body, dict):
        return (body, r.status_code)
    return ({"data": body}, r.status_code)


ZID_APP_SCRIPTS_URL = (
    os.getenv("ZID_APP_SCRIPTS_URL") or "https://api.zid.sa/v1/scripts"
).rstrip("/")
ZID_MANAGER_STORE_URL = (
    os.getenv("ZID_MANAGER_STORE_URL") or f"{ZID_API_BASE}/managers/account/store"
).rstrip("/")


def fetch_zid_app_scripts_manifest() -> Tuple[dict, int]:
    """
    Partner project manifest (GET /api/v1/scripts) — approved external_scripts + snippets.
    Requires ZID_API_AUTHORIZATION (Partner project token).
    """
    auth = (os.getenv("ZID_API_AUTHORIZATION") or "").strip()
    if not auth:
        return ({}, 0)
    h = {
        "Authorization": f"Bearer {auth}" if not auth.lower().startswith("bearer ") else auth,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    try:
        r = _zid_get(ZID_APP_SCRIPTS_URL, headers=h, timeout=20)
    except requests.RequestException:
        return ({}, 0)
    try:
        body: Any = r.json()
    except Exception:
        return ({}, r.status_code)
    if isinstance(body, dict):
        return (body, r.status_code)
    return ({}, r.status_code)


def fetch_zid_manager_store_url(store: Any) -> Optional[str]:
    """Storefront base URL from GET /v1/managers/account/store."""
    j = fetch_zid_manager_store_payload(store)
    if not isinstance(j, dict):
        return None
    for path in (
        ("store", "url"),
        ("data", "store", "url"),
        ("data", "url"),
    ):
        cur: Any = j
        for p in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(p)
        if isinstance(cur, str) and cur.strip():
            return cur.strip().rstrip("/")
    return None


def probe_storefront_for_widget_loader(
    store_url: str,
    *,
    loader_url: str,
) -> Tuple[bool, str]:
    """
    Best-effort check that Zid serves CartFlow loader on the merchant storefront.
    Uses official storefront GET /api/v1/scripts when available, else homepage HTML.
    """
    base = (store_url or "").strip().rstrip("/")
    if not base:
        return False, "no_store_url"
    scripts_url = f"{base}/api/v1/scripts"
    detail = "scripts_probe_skipped"
    try:
        r = _zid_get(
            scripts_url,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if r.status_code // 100 == 2:
            text = (r.text or "")[:8000]
            if _html_contains_widget_marker(text, loader_url):
                return True, "storefront_scripts_api"
        detail = f"scripts_http_{r.status_code}"
    except requests.RequestException as exc:
        detail = type(exc).__name__
    try:
        hp = _zid_get(
            base,
            headers={"Accept": "text/html"},
            timeout=15,
            allow_redirects=True,
        )
        if hp.status_code // 100 == 2:
            if _html_contains_widget_marker((hp.text or "")[:120000], loader_url):
                return True, "storefront_homepage"
        detail = f"homepage_http_{hp.status_code}"
    except requests.RequestException as exc:
        detail = type(exc).__name__
    return False, detail


def _html_contains_widget_marker(html: str, loader_url: str) -> bool:
    low = (html or "").lower()
    if "widget_loader" in low or "cartflow" in low:
        return True
    path = urlparse(loader_url).path
    if path and path.lower() in low:
        return True
    return False


def verify_webhook_signature(
    req: "StarletteRequest", raw_body: Optional[bytes] = None
) -> bool:
    if raw_body is not None:
        body = raw_body
    else:
        return False
    header_sig: Optional[str] = req.headers.get("X-Zid-Signature")
    secret = (os.getenv("ZID_WEBHOOK_SECRET") or "").strip()
    if not secret or not body or not (header_sig or "").strip():
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    hexd = mac.hexdigest()
    b64d = base64.b64encode(mac.digest()).decode("ascii")
    s = header_sig.strip()
    if s.lower().startswith("sha256="):
        s = s[7:].strip()
    if hmac.compare_digest(hexd, s) or hmac.compare_digest(b64d, s):
        return True
    return False
