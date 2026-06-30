# -*- coding: utf-8 -*-
"""Block live dashboard computation during merchant HTTP when snapshot mode is on."""
from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager
from typing import Iterator

from services.dashboard_snapshot_v1 import (
    dashboard_snapshot_mode_enabled,
    emit_hot_path_violation,
)

_in_dashboard_api_request: ContextVar[bool] = ContextVar(
    "_in_dashboard_api_request", default=False
)
_dashboard_api_path: ContextVar[str] = ContextVar("_dashboard_api_path", default="-")


@contextmanager
def dashboard_api_snapshot_request_scope(*, path: str = "-") -> Iterator[None]:
    token = _in_dashboard_api_request.set(True)
    path_token = _dashboard_api_path.set((path or "-")[:256])
    try:
        yield
    finally:
        _in_dashboard_api_request.reset(token)
        _dashboard_api_path.reset(path_token)


def is_dashboard_api_snapshot_request() -> bool:
    return bool(_in_dashboard_api_request.get())


def guard_dashboard_hot_path(operation: str) -> None:
    """
    Log when live dashboard builders run during a merchant HTTP request
    while snapshot mode is enabled.
    """
    if not dashboard_snapshot_mode_enabled():
        return
    if not _in_dashboard_api_request.get():
        return
    emit_hot_path_violation(
        operation=(operation or "unknown")[:128],
        path=_dashboard_api_path.get() or "-",
    )


__all__ = [
    "dashboard_api_snapshot_request_scope",
    "guard_dashboard_hot_path",
    "is_dashboard_api_snapshot_request",
]
