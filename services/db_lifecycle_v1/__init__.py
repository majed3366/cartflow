# -*- coding: utf-8 -*-
"""
Request-scoped DB lifecycle: ownership, ledger, short unit-of-work.

Architecture lives here. main.py only binds HTTP.
"""
from __future__ import annotations

from services.db_lifecycle_v1.http_bind import (
    bind_request,
    finish_request,
    maybe_reject_heavy_before_db,
    release_identity_phase,
)
from services.db_lifecycle_v1.pool_truth import pool_truth_snapshot
from services.db_lifecycle_v1.request_session_scope import (
    begin_logical_session_scope,
    current_logical_scope_id,
    logical_request_scopefunc,
)
from services.db_lifecycle_v1.unit_of_work import (
    release_before_response,
    short_db_phase,
)

__all__ = [
    "begin_logical_session_scope",
    "bind_request",
    "current_logical_scope_id",
    "finish_request",
    "logical_request_scopefunc",
    "maybe_reject_heavy_before_db",
    "pool_truth_snapshot",
    "release_before_response",
    "release_identity_phase",
    "short_db_phase",
]
