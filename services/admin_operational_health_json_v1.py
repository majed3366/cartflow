# -*- coding: utf-8 -*-
"""
Admin operational health JSON v1 — Operational Truth Center.

Read-only composition of existing health providers. No behavior changes.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import Store
from services.operational_health_diagnosis_v1 import build_operational_health_diagnosis
from services.operational_control_v1 import (
    build_operational_control_verification,
    get_operational_control_state,
)
from services.lifecycle_reconciliation_summary_v1 import build_lifecycle_reconciliation_summary
from services.purchase_truth_gap_visibility_v1 import build_purchase_truth_gap_summary
from services.recovery_health_v1 import build_recovery_health_snapshot
from services.recovery_process_role_v1 import build_scheduler_health_snapshot
from services.scheduler_store_visibility_v1 import build_scheduler_store_visibility


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _commit_sha() -> Optional[str]:
    for key in ("GIT_COMMIT", "RENDER_GIT_COMMIT", "SOURCE_VERSION"):
        val = (os.getenv(key) or "").strip()
        if val:
            return val[:40]
    return None


def _primary_store_slug() -> str:
    try:
        db.create_all()
        row = (
            db.session.query(Store.slug)
            .filter(Store.slug.isnot(None))
            .filter(Store.slug != "")
            .order_by(Store.id.asc())
            .first()
        )
        if row and row[0]:
            return str(row[0]).strip()[:255]
    except Exception:  # noqa: BLE001
        db.session.rollback()
    return ""


def _product_foundation_health_summary(store_slug: str) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return {"ok": False, "error": "no_store_for_summary"}
    try:
        from services.product_data.product_data_health_v1 import build_product_data_health_report

        report = build_product_data_health_report(db.session, slug, window_days=30)
        if hasattr(report, "to_dict"):
            full = report.to_dict()
            return {
                "ok": bool(getattr(report, "ok", True)),
                "store_slug": slug,
                "readiness": full.get("readiness"),
                "foundation_health": full.get("foundation_health"),
                "identity_coverage": full.get("identity_coverage"),
            }
        return {
            "ok": bool(getattr(report, "ok", True)),
            "store_slug": slug,
            "readiness": getattr(report, "readiness", None),
            "foundation_health": getattr(report, "foundation", None),
            "identity_coverage": getattr(report, "identity_coverage", None),
        }
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return {"ok": False, "store_slug": slug, "error": str(exc)[:200]}


def _governance_health_summary(store_slug: str) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return {"ok": False, "error": "no_store_for_summary"}
    try:
        from services.product_data.product_foundation_governance_v1 import (
            try_build_product_foundation_governance_report,
        )

        return try_build_product_foundation_governance_report(db.session, slug)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return {"ok": False, "store_slug": slug, "error": str(exc)[:200]}


def _whatsapp_readiness_summary() -> dict[str, Any]:
    try:
        from services.cartflow_provider_readiness import get_whatsapp_provider_readiness

        provider = get_whatsapp_provider_readiness()
        return {
            "ok": bool(provider.get("ready", provider.get("ok", True))),
            "provider_readiness": provider,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}


def build_admin_operational_health_json(
    *,
    store_slug: Optional[str] = None,
) -> dict[str, Any]:
    """Compose platform operational truth for admin JSON endpoint."""
    slug = (store_slug or _primary_store_slug()).strip()[:255]

    scheduler = {}
    ownership_diagnosis: dict[str, Any] = {}
    try:
        scheduler = build_scheduler_health_snapshot()
        ownership_diagnosis = dict(scheduler.get("ownership_diagnosis") or {})
    except Exception as exc:  # noqa: BLE001
        scheduler = {"ok": False, "error": str(exc)[:200]}
        ownership_diagnosis = {
            "codes": ["policy_error"],
            "severity": "critical",
            "summary": str(exc)[:200],
        }

    recovery = build_recovery_health_snapshot(emit_warn_log=False)

    operational_control = get_operational_control_state()
    oc_verification = {}
    try:
        oc_verification = build_operational_control_verification()
    except Exception as exc:  # noqa: BLE001
        oc_verification = {"error": str(exc)[:200]}

    lifecycle_reconciliation = build_lifecycle_reconciliation_summary()
    purchase_truth_gaps = build_purchase_truth_gap_summary()
    scheduler_store_visibility = build_scheduler_store_visibility()

    diagnosis = build_operational_health_diagnosis(
        operational_control=operational_control,
        scheduler_ownership_diagnosis=ownership_diagnosis,
        lifecycle_reconciliation=lifecycle_reconciliation,
        purchase_truth_gaps=purchase_truth_gaps,
        scheduler_store_visibility=scheduler_store_visibility,
    )

    oc_available = bool(
        (operational_control.get("availability") or {}).get("available", True)
    )
    scheduler_ok = bool(scheduler.get("ok", False))
    recovery_health_label = str(recovery.get("health") or "unknown")
    severity = str(diagnosis.get("severity") or "info")

    ok = (
        oc_available
        and scheduler_ok
        and severity not in ("critical",)
        and not lifecycle_reconciliation.get("disagreements_present")
        and not purchase_truth_gaps.get("gaps_detected")
    )

    return {
        "ok": ok,
        "version": "admin_operational_health_v1",
        "generated_at": _utc_now_iso(),
        "environment": (os.getenv("ENV") or "development").strip()[:64],
        "commit_sha": _commit_sha(),
        "operational_truth_center": True,
        "diagnosis": diagnosis,
        "scheduler_ownership": {
            "health": scheduler,
            "ownership_diagnosis": ownership_diagnosis,
        },
        "recovery_health": recovery,
        "operational_control": {
            "state": operational_control,
            "verification": oc_verification,
        },
        "whatsapp_readiness": _whatsapp_readiness_summary(),
        "lifecycle_reconciliation": lifecycle_reconciliation,
        "purchase_truth_gaps": purchase_truth_gaps,
        "scheduler_store_visibility": scheduler_store_visibility,
        "product_foundation_health_summary": _product_foundation_health_summary(slug),
        "governance_health_summary": _governance_health_summary(slug),
        "summary": {
            "scheduler_ok": scheduler_ok,
            "recovery_health": recovery_health_label,
            "operational_control_available": oc_available,
            "recovery_paused": bool(operational_control.get("platform_wa_paused"))
            or bool(operational_control.get("platform_schedule_paused")),
            "lifecycle_disagreements": int(lifecycle_reconciliation.get("disagreement_count") or 0),
            "purchase_truth_gaps": int(purchase_truth_gaps.get("non_durable_stop_total") or 0),
            "stores_with_due": int(scheduler_store_visibility.get("stores_with_due") or 0),
        },
    }


__all__ = ["build_admin_operational_health_json"]
