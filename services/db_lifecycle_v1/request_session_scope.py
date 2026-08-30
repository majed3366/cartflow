# -*- coding: utf-8 -*-
"""
Logical request scope for SQLAlchemy scoped_session (INV-OWN-01…08).

Scope identity is a request/UoW id in a ContextVar, not threading.get_ident().
AnyIO copies ContextVar into worker threads (proven). Scheduler/CLI/background
fall back to thread identity — they are not HTTP request owners.
"""
from __future__ import annotations

import threading
from contextvars import ContextVar, Token
from typing import Any, Optional

_logical_scope_id: ContextVar[Optional[str]] = ContextVar(
    "db_logical_request_scope", default=None
)
_uow_id: ContextVar[Optional[str]] = ContextVar("db_logical_uow_id", default=None)


def logical_request_scopefunc() -> tuple[str, int | str]:
    sid = _logical_scope_id.get()
    if sid:
        return ("req", sid)
    return ("thr", int(threading.get_ident() or 0))


def current_logical_scope_id() -> Optional[str]:
    return _logical_scope_id.get()


def current_uow_id() -> Optional[str]:
    return _uow_id.get()


def begin_logical_session_scope(*, request_id: str) -> Token:
    """Bind this task (and copied worker contexts) to one request-owned session."""
    rid = (request_id or "").strip() or "unknown"
    token = _logical_scope_id.set(rid)
    _uow_id.set(f"uow:{rid}")
    return token


def end_logical_session_scope(token: Optional[Token] = None) -> None:
    if token is not None:
        try:
            _logical_scope_id.reset(token)
        except Exception:  # noqa: BLE001
            _logical_scope_id.set(None)
    else:
        _logical_scope_id.set(None)
    _uow_id.set(None)


def ownership_snapshot() -> dict[str, Any]:
    return {
        "logical_scope": current_logical_scope_id() or "",
        "uow_id": current_uow_id() or "",
        "scope_key": list(logical_request_scopefunc()),
        "thread_ident": int(threading.get_ident() or 0),
        "thread_is_request_owner": False,
    }


def reset_for_tests() -> None:
    _logical_scope_id.set(None)
    _uow_id.set(None)


__all__ = [
    "begin_logical_session_scope",
    "current_logical_scope_id",
    "current_uow_id",
    "end_logical_session_scope",
    "logical_request_scopefunc",
    "ownership_snapshot",
    "reset_for_tests",
]
