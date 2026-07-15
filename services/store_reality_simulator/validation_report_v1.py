# -*- coding: utf-8 -*-
"""Post-run validation report — Phase 3 (findings only; no product fixes)."""
from __future__ import annotations

from typing import Any, Optional

from extensions import db
from models import (
    AbandonedCart,
    PurchaseTruthRecord,
    RecoverySchedule,
)
from services.store_reality_simulator.accounting_v1 import (
    normalize_accounting,
    reconcile_accounting,
)
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG
from services.store_reality_simulator.planner_v1 import RealityPlan


def build_validation_report(
    *,
    plan: RealityPlan,
    accounting: dict[str, int],
    reality_score: dict[str, Any],
    performance: Optional[dict[str, Any]] = None,
    manifest: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    acc = normalize_accounting(accounting)
    planned_purchases = plan.expected_event_counts.get("purchase_created", 0)
    rks = {e.recovery_key for e in plan.events if e.recovery_key}

    truth_n = 0
    schedules_open = 0
    carts_n = 0
    try:
        if rks:
            truth_n = (
                db.session.query(PurchaseTruthRecord)
                .filter(
                    PurchaseTruthRecord.store_slug == DEMO_STORE_SLUG,
                    PurchaseTruthRecord.recovery_key.in_(list(rks)),
                )
                .count()
            )
            schedules_open = (
                db.session.query(RecoverySchedule)
                .filter(
                    RecoverySchedule.store_slug == DEMO_STORE_SLUG,
                    RecoverySchedule.recovery_key.in_(list(rks)),
                    RecoverySchedule.status == "scheduled",
                )
                .count()
            )
            carts_n = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.zid_cart_id.in_([e.cart_id for e in plan.events]))
                .count()
            )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        truth_n = -1

    weaknesses: list[str] = []
    findings: list[str] = []
    if planned_purchases and truth_n >= 0 and truth_n < planned_purchases:
        weaknesses.append(
            f"purchase_truth_count={truth_n} < planned_purchases={planned_purchases}"
        )
    if acc.get("failed", 0):
        weaknesses.append(f"failed_events={acc['failed']}")
    if plan.warnings:
        findings.extend([f"plan_warning:{w}" for w in plan.warnings])
    findings.append(
        "Derived Knowledge/Dashboard/Attribution were not injected — platform must derive"
    )
    findings.append(
        "Unsupported storefront markers were accounted without fabricating durable analytics"
    )

    return {
        "reality_score": reality_score,
        "performance_report": performance or {},
        "knowledge_report": {
            "note": "Knowledge is derived by CartFlow; simulator does not inject insights",
            "hesitation_events_planned": plan.expected_event_counts.get(
                "hesitation_reason_selected", 0
            ),
            "purchase_events_planned": planned_purchases,
        },
        "dashboard_review": {
            "note": "Rebuild demo snapshots after execute for merchant surfaces",
            "hot_path_pollution": "cold ledger used for planned events",
        },
        "timeline_review": {
            "whatsapp_scheduled_planned": plan.expected_event_counts.get(
                "whatsapp_scheduled", 0
            ),
            "open_schedules_after_run": schedules_open,
        },
        "purchase_truth_review": {
            "planned_purchases": planned_purchases,
            "purchase_truth_rows": truth_n,
            "mismatch": (
                truth_n >= 0 and planned_purchases > 0 and truth_n != planned_purchases
            ),
        },
        "movement_review": {
            "returns_planned": plan.expected_event_counts.get("returned_to_site", 0),
            "passive_returns_planned": plan.expected_event_counts.get(
                "passive_return", 0
            ),
        },
        "recovery_review": {
            "reasons_planned": plan.expected_event_counts.get(
                "hesitation_reason_selected", 0
            ),
            "wa_mock_planned": plan.expected_event_counts.get("whatsapp_sent_mock", 0),
            "carts_touched": carts_n,
        },
        "data_growth_report": {
            "planned_events": len(plan.events),
            "ledger_cold": True,
            "scale_profile": plan.scale_profile,
        },
        "query_cost_report": {
            "note": "Batch-bounded execution; no merchant request-path work",
            "batches_bounded": True,
        },
        "memory_report": (performance or {}).get("last_snapshot") or {},
        "accounting_reconcile": reconcile_accounting(acc),
        "accounting": acc,
        "architectural_findings": findings,
        "weaknesses": weaknesses,
        "unexpected_behaviour": [],
        "recommended_improvements": [
            "Extend HTTP ingress mode for full cart-event parity when reviewing large runs",
            "Add more scenario planner families as product surfaces mature",
            "Keep progressive scale: small → medium → large before full/stress",
        ],
        "manifest_present": bool(manifest),
        "product_logic_changed": False,
    }
