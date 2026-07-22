# -*- coding: utf-8 -*-
"""
Operational Truth Integration Foundation V1 (OTIF).

Independent governed producer of Operational Truth packages for Surface Composition.
No recommendations. No Guidance. No Knowledge generation. No page logic.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func

from extensions import db
from services.product_data.operational_truth_flag_v1 import (
    operational_truth_v1_enabled,
)
from services.product_data.operational_truth_registry_v1 import (
    OPERATIONAL_TRUTH_REGISTRY_V1,
    SEVERITY_BANDS_V1,
    operational_truth_registry_v1,
    operational_truth_registry_valid_v1,
)
from services.product_data.operational_truth_types_v1 import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_CLEARED,
    LIFECYCLE_SUPPRESSED,
    OT_GENERATION_VERSION_V1,
    OT_REGISTRY_VERSION_V1,
    OT_SOURCE_CONTRACT_VERSION_V1,
    OT_VERSION_V1,
    SEVERITY_CRITICAL,
    SEVERITY_INFORMATIONAL,
    SEVERITY_WARNING,
    STABILITY_FORMING,
    STABILITY_STABLE,
    STABILITY_UNKNOWN,
    VIS_DEFER,
    VIS_EXPOSE,
    VIS_SUPPRESS,
)

log = logging.getLogger("cartflow")


def read_operational_state_snapshot_v1(store_slug: str) -> dict[str, Any]:
    """
    Durable operational counts only — shared source for OT packages.
    Not recommendations. Not KPI invention. Avoids MEIF↔SCF import cycles.
    """
    from models import (
        AbandonedCart,
        CartRecoveryLog,
        CartRecoveryReason,
        PurchaseTruthRecord,
        RecoverySchedule,
        Store,
    )

    slug = (store_slug or "").strip()[:255]
    out: dict[str, Any] = {
        "store_slug": slug,
        "abandoned_carts": 0,
        "purchase_truth": 0,
        "hesitation_reasons": 0,
        "recovery_schedules": 0,
        "mock_whatsapp_sent": 0,
        "has_durable_carts": False,
        "has_communication_activity": False,
        "source": "operational_truth_snapshot_v1",
    }
    if not slug:
        return out
    store = db.session.query(Store).filter_by(zid_store_id=slug).first()
    store_id = int(store.id) if store is not None else None
    abandoned = 0
    if store_id is not None:
        abandoned = int(
            db.session.query(func.count(AbandonedCart.id))
            .filter(AbandonedCart.store_id == store_id)
            .scalar()
            or 0
        )
    purchases = int(
        db.session.query(func.count(PurchaseTruthRecord.id))
        .filter(PurchaseTruthRecord.store_slug == slug)
        .scalar()
        or 0
    )
    reasons = int(
        db.session.query(func.count(CartRecoveryReason.id))
        .filter(CartRecoveryReason.store_slug == slug)
        .scalar()
        or 0
    )
    schedules = int(
        db.session.query(func.count(RecoverySchedule.id))
        .filter(RecoverySchedule.store_slug == slug)
        .scalar()
        or 0
    )
    mock_wa = int(
        db.session.query(func.count(CartRecoveryLog.id))
        .filter(
            CartRecoveryLog.store_slug == slug,
            CartRecoveryLog.status == "mock_sent",
        )
        .scalar()
        or 0
    )
    out.update(
        {
            "abandoned_carts": abandoned,
            "purchase_truth": purchases,
            "hesitation_reasons": reasons,
            "recovery_schedules": schedules,
            "mock_whatsapp_sent": mock_wa,
            "has_durable_carts": abandoned > 0,
            "has_communication_activity": mock_wa > 0 or schedules > 0,
        }
    )
    return out


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _metric_value(ops: dict[str, Any], metric_key: str) -> int:
    if metric_key == "recovery_execution_composite":
        return int(ops.get("recovery_schedules") or 0) + int(
            ops.get("mock_whatsapp_sent") or 0
        )
    return int(ops.get(metric_key) or 0)


def _severity_for_count(policy: str, count: int) -> str:
    bands = SEVERITY_BANDS_V1.get(policy) or {}
    critical_enter = int(bands.get("critical_enter") or 9999)
    warning_enter = int(bands.get("warning_enter") or 9999)
    if count >= critical_enter:
        return SEVERITY_CRITICAL
    if count >= warning_enter:
        return SEVERITY_WARNING
    if count > 0:
        return SEVERITY_INFORMATIONAL
    return SEVERITY_INFORMATIONAL


def _stability_for_count(policy: str, count: int, threshold: int) -> str:
    if count <= 0:
        return STABILITY_UNKNOWN
    bands = SEVERITY_BANDS_V1.get(policy.replace("hysteresis_", "bands_")) or {}
    # Durable counts above warning_enter are treated as stable (no wall-clock flap).
    warning_enter = int(bands.get("warning_enter") or threshold)
    if count >= max(threshold, warning_enter):
        return STABILITY_STABLE
    if count >= threshold:
        return STABILITY_FORMING
    return STABILITY_FORMING


def _visibility_decision(
    *,
    count: int,
    threshold: int,
    severity: str,
) -> tuple[str, str]:
    """Debounce + evidence threshold governance."""
    if count < threshold:
        return VIS_SUPPRESS, "below_evidence_threshold"
    if severity == SEVERITY_INFORMATIONAL and count < threshold:
        return VIS_DEFER, "informational_deferred"
    return VIS_EXPOSE, "threshold_met"


def _explain(
    *,
    truth_id: str,
    count: int,
    severity: str,
    metric_key: str,
) -> dict[str, str]:
    labels = {
        "abandoned_carts": "سلات مسجّلة",
        "recovery_schedules": "جداول استرجاع",
        "mock_whatsapp_sent": "إرسالات تواصل مسجّلة",
        "hesitation_reasons": "أسباب تردد مسجّلة",
        "purchase_truth": "مشتريات موثّقة",
        "recovery_execution_composite": "ضغط تنفيذ الاسترجاع",
    }
    label = labels.get(metric_key, metric_key)
    what = f"يوجد {count} من {label} في حقيقة التشغيل."
    why = (
        f"العدّاد التشغيلي «{metric_key}» تجاوز عتبة الأدلة لهذه الحقيقة "
        f"({truth_id}) بدرجة خطورة {severity}."
    )
    evidence = (
        f"المصدر: عدّادات حقيقة التشغيل المحكومة · المفتاح={metric_key} · القيمة={count}."
    )
    return {
        "what_happened_ar": what,
        "why_true_ar": why,
        "evidence_ar": evidence,
    }


def _build_package(
    *,
    definition: dict[str, Any],
    ops: dict[str, Any],
    store_slug: str,
    as_of: datetime,
) -> dict[str, Any]:
    tid = str(definition["id"])
    metric_key = str(definition["metric_key"])
    count = _metric_value(ops, metric_key)
    threshold = int(definition.get("evidence_threshold") or 1)
    severity = _severity_for_count(str(definition["severity"]), count)
    stability = _stability_for_count(
        str(definition.get("stability") or ""), count, threshold
    )
    visibility, visibility_reason = _visibility_decision(
        count=count, threshold=threshold, severity=severity
    )
    attention = False
    if definition.get("attention_required_when") == "never_critical":
        attention = False
    elif count >= threshold and severity in {SEVERITY_CRITICAL, SEVERITY_WARNING}:
        attention = True
    elif count >= threshold and tid == "ot_waiting_carts":
        attention = True

    lifecycle = LIFECYCLE_ACTIVE
    if count < threshold:
        lifecycle = LIFECYCLE_CLEARED
    if visibility == VIS_SUPPRESS:
        lifecycle = LIFECYCLE_SUPPRESSED

    explain = _explain(
        truth_id=tid, count=count, severity=severity, metric_key=metric_key
    )
    package_id = _sha(
        {
            "v": OT_GENERATION_VERSION_V1,
            "truth_id": tid,
            "store": store_slug,
            "as_of": as_of.isoformat(sep=" "),
            "count": count,
            "severity": severity,
        }
    )[:32]
    return {
        "package_id": package_id,
        "truth_id": tid,
        "store_slug": store_slug,
        "ot_version": OT_VERSION_V1,
        "generation_version": OT_GENERATION_VERSION_V1,
        "source_contract_version": OT_SOURCE_CONTRACT_VERSION_V1,
        "registry_version": OT_REGISTRY_VERSION_V1,
        "metric_key": metric_key,
        "count": count,
        "severity": severity,
        "freshness": "fresh",
        "lifecycle": lifecycle,
        "visibility": visibility,
        "visibility_reason": visibility_reason,
        "stability": stability,
        "confidence": "high"
        if "high" in str(definition.get("confidence") or "")
        else "medium",
        "requires_merchant_attention": attention,
        "destination_surfaces": list(definition.get("destination_surfaces") or []),
        "information_class": definition.get("information_class"),
        "merchant_relevance": definition.get("merchant_relevance"),
        "explainability": explain,
        "evidence": {
            "metric_key": metric_key,
            "count": count,
            "ops_snapshot_keys": sorted(ops.keys()),
            "source": definition.get("source"),
            "evidence_threshold": threshold,
        },
        "as_of": as_of.isoformat(sep=" "),
        "owner": definition.get("owner"),
        "is_operational_truth": True,
        "no_recommendation": True,
        "no_guidance": True,
        "no_knowledge": True,
    }


def generate_operational_truth_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate Operational Truth packages from durable operational facts only."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    reg_ok, reg_errors = operational_truth_registry_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "ot_version": OT_VERSION_V1,
        "generation_version": OT_GENERATION_VERSION_V1,
        "registry_version": OT_REGISTRY_VERSION_V1,
        "enabled": operational_truth_v1_enabled(),
        "packages": [],
        "package_count": 0,
        "exposed_count": 0,
        "suppressed_count": 0,
        "deferred_count": 0,
        "orphan_count": 0,
        "severity_counts": {
            SEVERITY_CRITICAL: 0,
            SEVERITY_WARNING: 0,
            SEVERITY_INFORMATIONAL: 0,
        },
        "canonical_fingerprint": "",
        "errors": list(reg_errors),
        "registries_valid": bool(reg_ok),
        "registry": operational_truth_registry_v1(),
        "inputs": {
            "merchant_operational_state": True,
            "no_raw_widget_events": True,
            "no_recommendations": True,
            "no_guidance": True,
            "no_knowledge_generation": True,
        },
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not reg_ok:
        out["errors"].append("invalid_registry")
        return out
    if not operational_truth_v1_enabled():
        out["errors"].append("otif_disabled")
        return out

    from services.product_data.time_authority_binding_resolve_v1 import (  # noqa: PLC0415
        resolve_bound_as_of_v1,
    )

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")
    ops = read_operational_state_snapshot_v1(slug)
    out["operational_state"] = ops

    packages: list[dict[str, Any]] = []
    for tid in sorted(OPERATIONAL_TRUTH_REGISTRY_V1.keys()):
        definition = OPERATIONAL_TRUTH_REGISTRY_V1[tid]
        try:
            packages.append(
                _build_package(
                    definition=definition,
                    ops=ops,
                    store_slug=slug,
                    as_of=anchor,
                )
            )
        except Exception as exc:  # noqa: BLE001
            out["errors"].append(f"package_fail:{tid}:{type(exc).__name__}")
            log.warning("otif package failed %s: %s", tid, exc)

    exposed = [p for p in packages if p.get("visibility") == VIS_EXPOSE]
    suppressed = [p for p in packages if p.get("visibility") == VIS_SUPPRESS]
    deferred = [p for p in packages if p.get("visibility") == VIS_DEFER]
    # Orphans: registry truths with no destination surfaces (should be none).
    orphans = [p for p in packages if not (p.get("destination_surfaces") or [])]

    for p in packages:
        sev = str(p.get("severity") or SEVERITY_INFORMATIONAL)
        if sev in out["severity_counts"]:
            out["severity_counts"][sev] += 1

    out["packages"] = packages
    out["package_count"] = len(packages)
    out["exposed_count"] = len(exposed)
    out["suppressed_count"] = len(suppressed)
    out["deferred_count"] = len(deferred)
    out["orphan_count"] = len(orphans)
    out["exposed_packages"] = exposed
    out["suppressed_packages"] = suppressed
    out["canonical_fingerprint"] = _sha(
        {
            "v": OT_GENERATION_VERSION_V1,
            "store": slug,
            "as_of": out["as_of"],
            "packages": [
                {
                    "truth_id": p.get("truth_id"),
                    "count": p.get("count"),
                    "severity": p.get("severity"),
                    "visibility": p.get("visibility"),
                    "stability": p.get("stability"),
                }
                for p in packages
            ],
        }
    )
    out["ok"] = (
        out["registries_valid"]
        and out["orphan_count"] == 0
        and out["package_count"] == len(OPERATIONAL_TRUTH_REGISTRY_V1)
        and not any(str(e).startswith("package_fail:") for e in out["errors"])
    )
    return out


def verify_operational_truth_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    a = generate_operational_truth_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    b = generate_operational_truth_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    return {
        "deterministic": a.get("canonical_fingerprint") == b.get("canonical_fingerprint"),
        "fingerprint_a": a.get("canonical_fingerprint"),
        "fingerprint_b": b.get("canonical_fingerprint"),
        "ok_a": a.get("ok"),
        "ok_b": b.get("ok"),
    }


__all__ = [
    "generate_operational_truth_v1",
    "verify_operational_truth_determinism_v1",
]
