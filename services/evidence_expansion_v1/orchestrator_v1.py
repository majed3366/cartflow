# -*- coding: utf-8 -*-
"""
Evidence Expansion orchestrator V1 — background only.

Registers Evidence Gaps from insufficient/conflicting diagnostics.
Never called from Home HTTP finalize. Never attaches gaps to merchant payloads.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Mapping

from services.evidence_expansion_v1.flag_v1 import (
    evidence_expansion_execute_enabled,
    evidence_expansion_v1_enabled,
)
from services.evidence_expansion_v1.gap_compose_v1 import (
    compose_evidence_gap_from_diagnostic_v1,
    should_open_evidence_gap_v1,
)
from services.evidence_expansion_v1.gap_store_v1 import upsert_evidence_gap_v1

log = logging.getLogger("cartflow")


def register_evidence_gaps_from_diagnostics_v1(
    contracts: list[Mapping[str, Any]],
    *,
    execute: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    For each insufficient/conflicting diagnostic, open/update an Evidence Gap.

    Dry-run when execute=False or EXECUTE flag off.
    """
    t0 = time.perf_counter()
    out: dict[str, Any] = {
        "ok": True,
        "enabled": evidence_expansion_v1_enabled(environ=environ),
        "execute": False,
        "candidates": 0,
        "composed": 0,
        "persisted": 0,
        "touched": 0,
        "skipped": 0,
        "errors": [],
        "gap_ids": [],
        "duration_ms": 0.0,
        "path": "background_evidence_expansion_v1",
        "merchant_exposure": False,
    }
    if not evidence_expansion_v1_enabled(environ=environ):
        out["errors"].append("evidence_expansion_disabled")
        out["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return out

    do_exec = bool(execute) and evidence_expansion_execute_enabled(environ=environ)
    out["execute"] = do_exec

    for contract in contracts or []:
        if not isinstance(contract, Mapping):
            continue
        if not should_open_evidence_gap_v1(contract):
            out["skipped"] += 1
            continue
        out["candidates"] += 1
        gap = compose_evidence_gap_from_diagnostic_v1(contract)
        if not gap or not gap.get("contract_ok"):
            out["errors"].append(
                f"compose_failed:{contract.get('diagnostic_family')}"
            )
            continue
        out["composed"] += 1
        out["gap_ids"].append(str(gap.get("gap_id") or ""))
        if not do_exec:
            continue
        try:
            res = upsert_evidence_gap_v1(gap)
            if res.get("ok") and res.get("mode") == "touch":
                out["touched"] += 1
            elif res.get("ok"):
                out["persisted"] += 1
            else:
                out["errors"].append(str(res.get("reason") or "persist_failed"))
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "evidence gap persist failed family=%s: %s",
                contract.get("diagnostic_family"),
                exc,
            )
            out["errors"].append(f"persist:{type(exc).__name__}")

    out["ok"] = not out["errors"] or out["composed"] > 0
    out["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return out


__all__ = ["register_evidence_gaps_from_diagnostics_v1"]
