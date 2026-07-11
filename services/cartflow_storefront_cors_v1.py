# -*- coding: utf-8 -*-
"""CORS for CartFlow widget APIs embedded on merchant storefronts (e.g. Zid)."""
from __future__ import annotations

import logging
import os
import re
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger("cartflow")

_ZID_STORE_ORIGIN_RE = re.compile(
    r"^https://[a-z0-9][a-z0-9-]*\.zid\.store$",
    re.IGNORECASE,
)

_WIDGET_CORS_EXACT_PATHS = frozenset(
    {
        "/api/cartflow/ready",
        "/api/cartflow/public-config",
        "/api/cartflow/reason",
        "/api/cart-event",
        "/api/storefront/widget-seen",
    }
)

_WIDGET_CORS_ALLOW_METHODS = "GET, POST, OPTIONS"
_WIDGET_CORS_ALLOW_HEADERS = "Content-Type, Accept"
_WIDGET_CORS_MAX_AGE = "86400"


def _extra_allowed_origins() -> frozenset[str]:
    raw = (os.getenv("CARTFLOW_STOREFRONT_CORS_EXTRA_ORIGINS") or "").strip()
    if not raw:
        return frozenset()
    out: set[str] = set()
    for part in raw.split(","):
        o = part.strip().rstrip("/")
        if o.startswith("http://") or o.startswith("https://"):
            out.add(o)
    return frozenset(out)


def widget_cors_path_matches(path: str) -> bool:
    p = (path or "").split("?", 1)[0].rstrip("/") or "/"
    return p in _WIDGET_CORS_EXACT_PATHS


def is_allowed_storefront_widget_origin(origin: Optional[str]) -> bool:
    o = (origin or "").strip().rstrip("/")
    if not o:
        return False
    if o in _extra_allowed_origins():
        return True
    try:
        parsed = urlparse(o)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    return bool(_ZID_STORE_ORIGIN_RE.match(f"https://{host}"))


def log_storefront_cors_request(
    *,
    origin: str,
    path: str,
    allowed: bool,
    method: str = "",
) -> None:
    line = (
        f"[CORS REQUEST] origin={(origin or '-')[:220]} "
        f"path={(path or '-')[:128]} "
        f"method={(method or '-')[:16]} "
        f"allowed={'true' if allowed else 'false'}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def apply_storefront_widget_cors_headers(response, *, origin: str) -> None:
    o = (origin or "").strip()
    if not o or not is_allowed_storefront_widget_origin(o):
        return
    response.headers["Access-Control-Allow-Origin"] = o
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = _WIDGET_CORS_ALLOW_METHODS
    response.headers["Access-Control-Allow-Headers"] = _WIDGET_CORS_ALLOW_HEADERS
    response.headers["Access-Control-Max-Age"] = _WIDGET_CORS_MAX_AGE


from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


class StorefrontWidgetCorsMiddleware:
    """
    OPTIONS preflight + ACAO for Zid storefront widget APIs (no wildcard *).

    Pure ASGI (not BaseHTTPMiddleware): BaseHTTPMiddleware buffers the response
    through an anyio memory stream and was part of the reason-POST TTFB pile-up
    when paired with BackgroundTasks. Keep this path streaming.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path
        if not widget_cors_path_matches(path):
            await self.app(scope, receive, send)
            return

        origin = request.headers.get("origin") or ""
        allowed = is_allowed_storefront_widget_origin(origin)
        log_storefront_cors_request(
            origin=origin,
            path=path,
            allowed=allowed,
            method=request.method,
        )

        if request.method == "OPTIONS":
            resp = Response(status_code=204 if allowed else 403, content=b"")
            if allowed:
                apply_storefront_widget_cors_headers(resp, origin=origin)
            await resp(scope, receive, send)
            return

        if not allowed:
            await self.app(scope, receive, send)
            return

        async def send_with_cors(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=list(message.get("headers") or []))
                headers["Access-Control-Allow-Origin"] = origin.strip()
                headers["Access-Control-Allow-Credentials"] = "true"
                vary = headers.get("Vary")
                if vary:
                    if "Origin" not in vary:
                        headers["Vary"] = f"{vary}, Origin"
                else:
                    headers["Vary"] = "Origin"
                headers["Access-Control-Allow-Methods"] = _WIDGET_CORS_ALLOW_METHODS
                headers["Access-Control-Allow-Headers"] = _WIDGET_CORS_ALLOW_HEADERS
                headers["Access-Control-Max-Age"] = _WIDGET_CORS_MAX_AGE
                message = {**message, "headers": headers.raw}
            await send(message)

        await self.app(scope, receive, send_with_cors)


__all__ = [
    "StorefrontWidgetCorsMiddleware",
    "apply_storefront_widget_cors_headers",
    "is_allowed_storefront_widget_origin",
    "log_storefront_cors_request",
    "widget_cors_path_matches",
]
