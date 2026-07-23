# -*- coding: utf-8 -*-
"""
BFSV Exp 1 *class* check — Product persist → Evidence accounting (WP-ET-07).

Synthetic verification only. Does **not** resume BFSV experiments or Reality
Validation. Proves Observation→Evidence volume linkage and no ATC-as-view.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.accounting_v1 import (
    STAGE_EVIDENCE_OUT,
    STAGE_OBSERVATION_OUT,
    get_evidence_accounting_ledger_v1,
    reset_evidence_accounting_ledger_v1,
)
from services.evidence_truth.evidence_dual_write_v1 import shadow_dual_write_evidence_v1
from services.evidence_truth.evidence_store_v1 import (
    get_evidence_truth_store_v1,
    reset_evidence_truth_store_v1,
)
from services.evidence_truth.families_v1 import FAMILY_PRODUCT
from services.evidence_truth.observation_store_v1 import reset_canonical_observation_store_v1
from services.evidence_truth.observation_types_v1 import RAW_KIND_PRODUCT_SIGNAL
from services.evidence_truth.product_signal_classification_v1 import SIGNAL_ATC, SIGNAL_VIEW


def run_bfsv_exp1_class_check_persist_to_evidence_v1(
    *,
    reset_global: bool = True,
) -> dict[str, Any]:
    """
    Class check: N product signal dual-writes → N Product Evidence versions
    (idempotent duplicates excluded); ATC never claims view.
    """
    if reset_global:
        reset_evidence_accounting_ledger_v1()
        reset_canonical_observation_store_v1()
        reset_evidence_truth_store_v1()

    checks: list[dict[str, Any]] = []
    signals = [
        {
            "store_slug": "demo",
            "session_id": "s-p1",
            "product_id": "sku-1",
            "event": "cart_state_sync",
            "capture_source": "cart_state_sync",
            "reason": "add",
        },
        {
            "store_slug": "demo",
            "session_id": "s-p2",
            "product_id": "sku-2",
            "event": "cart_abandoned",
            "capture_source": "cart_abandoned",
        },
        {
            "store_slug": "demo",
            "session_id": "s-p3",
            "product_id": "sku-3",
            "event": "product_view",
            "signal_class": SIGNAL_VIEW,
        },
    ]
    results = []
    for i, payload in enumerate(signals):
        out = shadow_dual_write_evidence_v1(
            raw_kind=RAW_KIND_PRODUCT_SIGNAL,
            payload=payload,
            force=True,
            source=f"bfsv_exp1_class:{i}",
        )
        results.append(out)

    created = sum(1 for r in results if r.get("created"))
    checks.append(
        {
            "id": "B1_all_ok",
            "ok": all(bool(r.get("ok")) and not r.get("rejected") for r in results),
        }
    )
    checks.append(
        {
            "id": "B2_persist_to_evidence_count",
            "ok": created == len(signals),
            "detail": {"created": created, "signals": len(signals)},
        }
    )

    store = get_evidence_truth_store_v1()
    product_n = store.count(family=FAMILY_PRODUCT)
    checks.append(
        {
            "id": "B3_product_evidence_volume",
            "ok": product_n >= len(signals),
            "detail": {"product_evidence": product_n},
        }
    )

    # ATC / cart-line must not claim view
    atc_ok = True
    view_ok = True
    for r in results:
        rec = store.get(str(r.get("evidence_id") or ""))
        if rec is None:
            atc_ok = False
            continue
        sc = str(rec.envelope.payload.get("signal_class") or "")
        if sc in {SIGNAL_ATC, "cart_line"}:
            if rec.envelope.payload.get("view_claimed"):
                atc_ok = False
            if rec.envelope.payload.get("has_product_views_ready"):
                atc_ok = False
            if not rec.envelope.payload.get("atc_is_not_view"):
                atc_ok = False
        if sc == SIGNAL_VIEW:
            if not rec.envelope.payload.get("view_claimed"):
                view_ok = False
    checks.append({"id": "B4_no_atc_as_view", "ok": atc_ok})
    checks.append({"id": "B5_explicit_view_claimed", "ok": view_ok})

    snap = get_evidence_accounting_ledger_v1().snapshot()
    obs_out = int(snap["stage_counts"][STAGE_OBSERVATION_OUT])
    ev_out = int(snap["stage_counts"][STAGE_EVIDENCE_OUT])
    checks.append(
        {
            "id": "B6_accounting_balanced",
            "ok": obs_out >= len(signals) and ev_out >= len(signals),
            "detail": {"observation_out": obs_out, "evidence_out": ev_out},
        }
    )

    # Idempotent re-delivery does not invent volume
    dup = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload=signals[0],
        force=True,
        observation_id=str(results[0].get("observation_id") or ""),
        source="bfsv_exp1_class:dup",
    )
    checks.append(
        {
            "id": "B7_idempotent",
            "ok": bool(dup.get("ok")) and bool(dup.get("duplicated")),
        }
    )

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "gate": "BFSV_Exp1_class_check",
        "name": "Product persist→Evidence (synthetic; BFSV not resumed)",
        "passed": passed,
        "checks": checks,
        "accounting_snapshot": snap,
        "evidence_store": store.snapshot(),
        "bfsv_resumed": False,
        "note": "Class check only — does not authorize BFSV or Reality Validation",
    }
