# -*- coding: utf-8 -*-
"""
OAuth redirect_uri helpers for Embedded Signup code exchange.

Meta error 100/36008 requires the exchange redirect_uri to match the
authorization dialog character-for-character (or be omitted when the
FB.login JS SDK popup did not bind a server redirect).

Never log authorization codes, tokens, or app secrets.
"""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import parse_qsl, urlparse, urlunparse


def oauth_redirect_uris_match(left: str, right: str) -> bool:
    """Character-for-character equality (Meta's requirement)."""
    return (left or "") == (right or "")


def safe_redirect_uri_diag(uri: Optional[str]) -> Optional[dict[str, Any]]:
    """
    Safe diagnostic shape for a redirect URI.
    Records scheme/host/path/query *keys* only — never full query values
    (xd_arbiter URLs can contain opaque callback ids).
    """
    raw = (uri or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except Exception:  # noqa: BLE001
        return {
            "parse_ok": False,
            "length": len(raw),
        }
    query_keys = sorted({k for k, _ in parse_qsl(parsed.query, keep_blank_values=True)})
    path = parsed.path or ""
    return {
        "parse_ok": True,
        "scheme": parsed.scheme or "",
        "host": (parsed.hostname or "").lower(),
        "port": parsed.port,
        "path": path,
        "trailing_slash": path.endswith("/"),
        "query_keys": query_keys,
        "has_query": bool(parsed.query),
        "has_fragment": bool(parsed.fragment),
        "length": len(raw),
    }


def compare_redirect_uris(auth_uri: str, exchange_uri: str) -> dict[str, Any]:
    """
    Compare authorization vs exchange redirect URIs.
    Exact match is authoritative; component diffs are for diagnostics only.
    """
    exact = oauth_redirect_uris_match(auth_uri, exchange_uri)
    left = safe_redirect_uri_diag(auth_uri)
    right = safe_redirect_uri_diag(exchange_uri)
    component_mismatch: list[str] = []
    if left and right and left.get("parse_ok") and right.get("parse_ok"):
        for key in ("scheme", "host", "port", "path", "trailing_slash", "has_query"):
            if left.get(key) != right.get(key):
                component_mismatch.append(key)
        if left.get("query_keys") != right.get("query_keys"):
            component_mismatch.append("query_keys")
    return {
        "exact_match": exact,
        "auth": left,
        "exchange": right,
        "component_mismatch": component_mismatch,
    }


def build_token_exchange_params(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    dialog_redirect_uri: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    """
    Build oauth/access_token query params for FB.login Embedded Signup.

    Policy:
    - If the browser captured the dialog's redirect_uri, send it EXACTLY.
    - Otherwise OMIT redirect_uri entirely (do not guess page URL / login_success.html).
    """
    params: dict[str, str] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }
    dialog = (dialog_redirect_uri or "").strip()
    diag: dict[str, Any] = {
        "redirect_uri_included": False,
        "redirect_uri_mode": "omit",
        "dialog_redirect": None,
        "param_keys": sorted(params.keys()),
    }
    if dialog:
        params["redirect_uri"] = dialog  # exact — no normalize/rewrite
        diag["redirect_uri_included"] = True
        diag["redirect_uri_mode"] = "dialog_exact"
        diag["dialog_redirect"] = safe_redirect_uri_diag(dialog)
        diag["param_keys"] = sorted(params.keys())
        # Self-check: exchange URI equals auth dialog URI by construction.
        diag["auth_exchange_compare"] = compare_redirect_uris(dialog, params["redirect_uri"])
    else:
        diag["auth_exchange_compare"] = {
            "exact_match": True,
            "note": "both_omitted",
            "auth": None,
            "exchange": None,
            "component_mismatch": [],
        }
    # Never put secrets into diag.
    return params, diag


def rebuild_uri_for_test(
    *,
    scheme: str,
    host: str,
    path: str,
    query: str = "",
    port: Optional[int] = None,
) -> str:
    """Test helper only — reconstruct a URI from parts."""
    netloc = host if port is None else f"{host}:{port}"
    return urlunparse((scheme, netloc, path, "", query, ""))


__all__ = [
    "build_token_exchange_params",
    "compare_redirect_uris",
    "oauth_redirect_uris_match",
    "rebuild_uri_for_test",
    "safe_redirect_uri_diag",
]
