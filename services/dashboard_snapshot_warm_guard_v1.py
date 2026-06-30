# -*- coding: utf-8 -*-
"""
Block DB READY / heavy warm on dashboard HTTP when snapshot mode is active.
"""
from __future__ import annotations

import logging

log = logging.getLogger("cartflow")

_PREFIX_WARM_BLOCKED = "[DASHBOARD FIRST REQUEST WARM BLOCKED]"


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def dashboard_db_ready_should_skip(*, source: str = "dashboard") -> bool:
    from services.dashboard_snapshot_hot_path_guard_v1 import (
        is_dashboard_api_snapshot_request,
    )
    from services.dashboard_snapshot_v1 import dashboard_snapshot_mode_enabled

    if dashboard_snapshot_mode_enabled():
        return True
    if is_dashboard_api_snapshot_request():
        return True
    return False


def emit_dashboard_first_request_warm_blocked(
    *,
    source: str,
    endpoint: str = "-",
) -> None:
    _emit(
        f"{_PREFIX_WARM_BLOCKED} source={(source or 'dashboard')[:32]} "
        f"endpoint={(endpoint or '-')[:64]}"
    )


__all__ = [
    "dashboard_db_ready_should_skip",
    "emit_dashboard_first_request_warm_blocked",
]
