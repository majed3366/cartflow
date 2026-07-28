# -*- coding: utf-8 -*-
"""
Decision Workspace durable snapshot — Home architectural parity.

Off-request: materialize full paint projection into ``dashboard_snapshots``
(type ``decision_workspace``).

On-request: read that row only — no ORV / facts / situations / DCE compose.
"""
from __future__ import annotations

import copy
import logging
import time
from typing import Any, Optional

log = logging.getLogger("cartflow")

SNAPSHOT_TYPE_DECISION_WORKSPACE = "decision_workspace"


def _empty_projection(store_slug: str) -> dict[str, Any]:
    return {
        "store_slug": store_slug,
        "zone_a": [],
        "zone_b": [],
        "zone_labels": {"B": "ما يحتاج قرارك"},
        "quiet": True,
        "mission_question": "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟",
        "degraded_load": False,
    }


def build_decision_workspace_projection_v1(store_slug: str) -> dict[str, Any]:
    """Full enrich path — intended for builder / miss fallback only."""
    slug = str(store_slug or "").strip()
    from services.cart_workspace.business_findings_enrichment_v1 import (  # noqa: PLC0415
        enrich_projection_with_fde_v1,
    )

    base = _empty_projection(slug)
    return enrich_projection_with_fde_v1(base, slug)


def materialize_decision_workspace_snapshot_v1(
    *,
    store_id: int,
    store_slug: str,
) -> dict[str, Any]:
    """Compose + persist Workspace projection off the merchant request path."""
    from services.dashboard_snapshot_change_v1 import (  # noqa: PLC0415
        write_dashboard_snapshot_guarded,
    )
    from services.dashboard_snapshot_v1 import (  # noqa: PLC0415
        canonical_snapshot_store_slug,
    )
    from services.decision_workspace_v2.paint_cache_v1 import (  # noqa: PLC0415
        workspace_paint_cache_set,
    )

    t0 = time.perf_counter()
    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    try:
        projection = build_decision_workspace_projection_v1(slug)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "workspace_snapshot_materialize_failed store=%s err=%s",
            slug,
            type(exc).__name__,
        )
        return {
            "ok": False,
            "store_slug": slug,
            "error": type(exc).__name__,
            "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    payload = {
        "ok": True,
        "store_slug": slug,
        "invalidated": False,
        "projection": projection,
        "zone_assignment": {
            "zone_a": [],
            "zone_b": [
                c.get("decision_id")
                for c in list(projection.get("zone_b") or [])
                if isinstance(c, dict)
            ],
        },
        "materialized_at_ms": int(time.time() * 1000),
        "gate_workspace_snapshot_v1": True,
    }
    outcome = write_dashboard_snapshot_guarded(
        store_id=int(store_id),
        store_slug=slug,
        snapshot_type=SNAPSHOT_TYPE_DECISION_WORKSPACE,
        payload=payload,
    )
    try:
        workspace_paint_cache_set(slug, projection)
    except Exception:  # noqa: BLE001
        pass
    return {
        "ok": True,
        "store_slug": slug,
        "mode": getattr(outcome, "mode", None),
        "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "decision_card_count": int(projection.get("decision_card_count") or 0),
    }


def read_decision_workspace_snapshot_v1(
    store_slug: str,
) -> Optional[dict[str, Any]]:
    """
    Return paint-ready projection from durable snapshot, or None on miss/invalid.
    Never composes ORV/facts/situations.
    """
    from services.dashboard_snapshot_v1 import (  # noqa: PLC0415
        canonical_snapshot_store_slug,
        decode_snapshot_payload,
        fetch_latest_snapshot_row,
        snapshot_row_is_stale,
    )

    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    if not slug:
        return None
    row = fetch_latest_snapshot_row(
        store_slug=slug, snapshot_type=SNAPSHOT_TYPE_DECISION_WORKSPACE
    )
    if row is None:
        return None
    body = decode_snapshot_payload(row)
    if not isinstance(body, dict):
        return None
    if body.get("invalidated"):
        return None
    projection = body.get("projection")
    if not isinstance(projection, dict):
        return None
    if projection.get("zone_b") is None and not projection.get("quiet"):
        return None
    out = copy.deepcopy(projection)
    out["_workspace_snapshot_v1"] = {
        "hit": True,
        "stale": bool(snapshot_row_is_stale(row)),
        "version": int(getattr(row, "version", 0) or 0),
        "read_ms": None,
        "snapshot_type": SNAPSHOT_TYPE_DECISION_WORKSPACE,
    }
    return out


def invalidate_decision_workspace_snapshot_v1(
    *,
    store_id: int | None,
    store_slug: str,
) -> None:
    """Mark durable Workspace snapshot unusable after merchant command."""
    from services.dashboard_snapshot_change_v1 import (  # noqa: PLC0415
        write_dashboard_snapshot_guarded,
    )
    from services.dashboard_snapshot_v1 import (  # noqa: PLC0415
        canonical_snapshot_store_slug,
    )
    from services.decision_workspace_v2.paint_cache_v1 import (  # noqa: PLC0415
        workspace_paint_cache_clear,
    )

    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    workspace_paint_cache_clear(slug)
    if store_id is None:
        try:
            from models import Store  # noqa: PLC0415
            from extensions import db  # noqa: PLC0415

            row = (
                db.session.query(Store.id)
                .filter(Store.zid_store_id == slug)
                .first()
            )
            if row is None:
                return
            store_id = int(row[0] if isinstance(row, tuple) else row.id)
        except Exception:  # noqa: BLE001
            return
    try:
        write_dashboard_snapshot_guarded(
            store_id=int(store_id),
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_DECISION_WORKSPACE,
            payload={
                "ok": False,
                "store_slug": slug,
                "invalidated": True,
                "projection": None,
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "workspace_snapshot_invalidate_failed store=%s err=%s",
            slug,
            type(exc).__name__,
        )


__all__ = [
    "SNAPSHOT_TYPE_DECISION_WORKSPACE",
    "build_decision_workspace_projection_v1",
    "invalidate_decision_workspace_snapshot_v1",
    "materialize_decision_workspace_snapshot_v1",
    "read_decision_workspace_snapshot_v1",
]
