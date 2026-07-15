# -*- coding: utf-8 -*-
"""
HTTP middleware — attach default production Query Time Context (WP-2).

Logic lives here, not in main.py. Registration in main.py is composition-only.
Does not change merchant-facing results: SystemClock remains authoritative.
"""
from __future__ import annotations

from typing import Any, Callable, Optional
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from services.time_authority.context_scope import request_scope


def _request_correlation_id(request: Request) -> str:
    headers = request.headers
    for key in ("x-request-id", "x-correlation-id", "x-cartflow-request-id"):
        val = (headers.get(key) or "").strip()
        if val:
            return val[:128]
    return uuid4().hex[:16]


class QueryTimeContextMiddleware(BaseHTTPMiddleware):
    """
    Activate production Query Time Context for the duration of each HTTP request.

    Opt-out: set attribute ``request.state.skip_query_time_context = True`` before
    this middleware runs (not used by default).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if getattr(request.state, "skip_query_time_context", False):
            return await call_next(request)
        rid = _request_correlation_id(request)
        # Opaque scope key reserved for future store binding (INV-002) — empty for WP-2.
        scope_key = ""
        with request_scope(request_id=rid, correlation_id=rid, scope_key=scope_key) as ctx:
            request.state.query_time_context = ctx
            request.state.query_time_correlation_id = ctx.correlation_id
            return await call_next(request)


def register_query_time_context_middleware(app: Any) -> None:
    """
    Composition helper for application startup.

    Intended call site: main.py (one line) — no business logic here beyond add_middleware.
    """
    app.add_middleware(QueryTimeContextMiddleware)
