# -*- coding: utf-8 -*-
"""Projection version / live-update envelope compare — server contract for P4."""
from __future__ import annotations

from typing import Any, Optional


ACCEPT = "ACCEPT"
STALE_OLDER = "STALE_OLDER"
CONFLICT_SAME_VERSION = "CONFLICT_SAME_VERSION"
MISSING_PAYLOAD = "MISSING_PAYLOAD"
UNAUTHORIZED = "UNAUTHORIZED"


def compare_projection_envelope(
    local: Optional[dict[str, Any]],
    incoming: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """
    Renderer must update only when projection_version advances (or first paint).
    No business recomputation here — version/fingerprint only.
    """
    if not incoming or not isinstance(incoming, dict):
        return {"decision": MISSING_PAYLOAD, "should_paint": False}

    in_ver = int(incoming.get("projection_version") or 0)
    in_fp = str(incoming.get("projection_fingerprint") or "")

    if not local:
        return {
            "decision": ACCEPT,
            "should_paint": True,
            "reason": "first_projection",
            "incoming_version": in_ver,
        }

    loc_ver = int(local.get("projection_version") or 0)
    loc_fp = str(local.get("projection_fingerprint") or "")

    if in_ver < loc_ver:
        return {
            "decision": STALE_OLDER,
            "should_paint": False,
            "local_version": loc_ver,
            "incoming_version": in_ver,
        }

    if in_ver == loc_ver:
        if in_fp and loc_fp and in_fp != loc_fp:
            return {
                "decision": CONFLICT_SAME_VERSION,
                "should_paint": False,
                "local_version": loc_ver,
                "incoming_version": in_ver,
            }
        return {
            "decision": ACCEPT,
            "should_paint": False,
            "reason": "same_version_no_repaint",
            "local_version": loc_ver,
            "incoming_version": in_ver,
        }

    # in_ver > loc_ver
    return {
        "decision": ACCEPT,
        "should_paint": True,
        "reason": "version_advanced",
        "local_version": loc_ver,
        "incoming_version": in_ver,
    }
