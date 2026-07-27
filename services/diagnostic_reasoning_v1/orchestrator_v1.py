# -*- coding: utf-8 -*-
"""
Diagnostic Reasoning orchestrator V1 — background / CLI only.

Never invoke from Home HTTP finalize.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.compose_v1 import compose_store_diagnostics_v1
from services.diagnostic_reasoning_v1.evidence_bag_v1 import load_bounded_evidence_bags_v1
from services.diagnostic_reasoning_v1.flag_v1 import (
    diagnostic_reasoning_execute_enabled,
    diagnostic_reasoning_v1_enabled,
)
from services.diagnostic_reasoning_v1.publish_v1 import (
    pick_primary_diagnostic_publication_v1,
    publish_diagnostic_for_merchant_v1,
)
from services.diagnostic_reasoning_v1.snapshot_store_v1 import (
    upsert_diagnostic_snapshot_v1,
)

log = logging.getLogger("cartflow")


def materialize_diagnostics_for_store_v1(
    store_slug: str,
    *,
    dash_store: Any = None,
    publication: Mapping[str, Any] | None = None,
    evidence_bags: list[Mapping[str, Any]] | None = None,
    execute: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Compose (+ optionally persist) diagnostics for one store.

    Dry-run when execute=False or EXECUTE flag off.
    """
    t0 = time.perf_counter()
    slug = (store_slug or "").strip()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "enabled": diagnostic_reasoning_v1_enabled(environ=environ),
        "execute": False,
        "composed": 0,
        "persisted": 0,
        "touched": 0,
        "errors": [],
        "publications": [],
        "primary": None,
        "duration_ms": 0.0,
        "path": "background_diagnostic_reasoning_v1",
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not diagnostic_reasoning_v1_enabled(environ=environ):
        out["errors"].append("diagnostic_reasoning_disabled")
        out["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return out

    do_exec = bool(execute) and diagnostic_reasoning_execute_enabled(environ=environ)
    out["execute"] = do_exec

    bags = list(evidence_bags or [])
    if not bags:
        bags = load_bounded_evidence_bags_v1(
            slug, dash_store=dash_store, publication=publication
        )
    contracts = compose_store_diagnostics_v1(store_slug=slug, evidence_bags=bags)
    out["composed"] = len(contracts)
    pubs = []
    for contract in contracts:
        pub = publish_diagnostic_for_merchant_v1(contract)
        pubs.append(pub)
        if not do_exec:
            continue
        try:
            res = upsert_diagnostic_snapshot_v1(contract)
            if res.get("ok") and res.get("mode") == "touch":
                out["touched"] += 1
            elif res.get("ok"):
                out["persisted"] += 1
            else:
                out["errors"].append(str(res.get("reason") or "persist_failed"))
        except Exception as exc:  # noqa: BLE001
            # Last-good preserved in store — do not delete.
            log.warning("diagnostic persist failed store=%s: %s", slug, exc)
            out["errors"].append(f"persist:{type(exc).__name__}")

    out["publications"] = pubs
    out["primary"] = pick_primary_diagnostic_publication_v1(pubs)
    out["ok"] = out["composed"] > 0 or not out["errors"]
    out["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return out


def attach_diagnostic_publication_from_snapshots_v1(
    summary: dict[str, Any],
    *,
    store_slug: str = "",
) -> dict[str, Any]:
    """Home/read path: stamp publication from persisted snapshots only (no compose)."""
    if not isinstance(summary, dict):
        return summary
    from services.diagnostic_reasoning_v1.snapshot_store_v1 import (  # noqa: PLC0415
        read_diagnostic_snapshots_for_store_v1,
        read_primary_diagnostic_publication_v1,
    )

    slug = (store_slug or str(summary.get("store_slug") or "")).strip()
    t0 = time.perf_counter()
    primary = read_primary_diagnostic_publication_v1(slug) if slug else None
    all_pubs = read_diagnostic_snapshots_for_store_v1(slug) if slug else []
    read_ms = round((time.perf_counter() - t0) * 1000, 2)
    summary["diagnostic_publication_v1"] = primary
    summary["diagnostic_publications_v1"] = all_pubs
    summary["diagnostic_snapshot_read_ms"] = read_ms
    # Feed merchant publication if present.
    pub = summary.get("merchant_publication_v1")
    if isinstance(pub, dict) and primary:
        pub["primary_diagnosis"] = primary
        pub["diagnostic_reasoning_v1"] = True
    return summary


__all__ = [
    "attach_diagnostic_publication_from_snapshots_v1",
    "materialize_diagnostics_for_store_v1",
]
