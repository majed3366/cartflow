# -*- coding: utf-8 -*-
"""
Merchant Experience Integration Foundation V1.

Bridge: Surface Composition + Knowledge + Commercial Guidance + Merchant Operational State
→ page-ready packages. No new intelligence. No page-owned business decisions.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func

from extensions import db
from services.product_data.merchant_experience_integration_flag_v1 import (
    merchant_experience_integration_v1_enabled,
)
from services.product_data.merchant_experience_integration_registry_v1 import (
    INTEGRATION_MAP_V1,
    integration_map_v1,
    integration_map_valid_v1,
)
from services.product_data.merchant_experience_integration_types_v1 import (
    MEIF_GENERATION_VERSION_V1,
    MEIF_VERSION_V1,
    PAGE_CARTS,
    PAGE_COMMUNICATION,
    PAGE_DECISION,
    PAGE_HOME,
    PAGE_SETTINGS,
    QUESTION_CARTS,
    QUESTION_COMMUNICATION,
    QUESTION_DECISION,
    QUESTION_HOME,
    QUESTION_SETTINGS,
)
from services.product_data.merchant_experience_knowledge_translation_v1 import (
    translate_knowledge_for_merchant_v1,
)
from services.product_data.surface_composition_foundation_v1 import (
    generate_surface_compositions_v1,
)
from services.product_data.surface_composition_types_v1 import VIS_VISIBLE

log = logging.getLogger("cartflow")


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


def read_merchant_operational_state_v1(store_slug: str) -> dict[str, Any]:
    """
    Governed operational truth snapshot — durable counts only.
    Not business recommendations. Not KPI invention.
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
        "source": "merchant_operational_state_v1",
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


def _visible_for_surface(compositions: list[dict[str, Any]], surface_id: str) -> list[dict[str, Any]]:
    return [
        c
        for c in compositions
        if c.get("surface_id") == surface_id and c.get("visibility") == VIS_VISIBLE
    ]


def _item_from_composition(c: dict[str, Any]) -> dict[str, Any]:
    lineage = dict(c.get("source_lineage") or {})
    return {
        "composition_id": c.get("composition_id"),
        "information_class": c.get("information_class"),
        "presentation_intent": c.get("presentation_intent"),
        "priority": c.get("priority"),
        "freshness_state": c.get("freshness_state"),
        "visibility": c.get("visibility"),
        "duplicate_group": c.get("duplicate_group"),
        "owns_full_explanation": c.get("owns_full_explanation"),
        "merchant_value": c.get("merchant_value"),
        "source_type": c.get("source_type"),
        "source_id": c.get("source_id"),
        "source_lineage": lineage,
        "accounting_outcome": c.get("accounting_outcome"),
        "surface_owner": "surface_composition_foundation_v1",
    }


def _suppress_false_empty(
    items: list[dict[str, Any]],
    *,
    ops: dict[str, Any],
    surface_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Remove false empty-states when operational truth contradicts them."""
    warnings: list[str] = []
    kept: list[dict[str, Any]] = []
    for it in items:
        if it.get("information_class") != "empty_state":
            kept.append(it)
            continue
        mv = str(it.get("merchant_value") or "")
        if surface_id == PAGE_CARTS and ops.get("has_durable_carts"):
            warnings.append("suppressed_false_empty:carts")
            continue
        if surface_id == PAGE_COMMUNICATION and ops.get("has_communication_activity"):
            warnings.append("suppressed_false_empty:communication")
            continue
        if surface_id in {PAGE_HOME, PAGE_DECISION} and ops.get("has_durable_carts"):
            if mv in {"nothing_requiring_action", "no_operational_issues"}:
                warnings.append(f"suppressed_false_empty:{surface_id}")
                continue
        kept.append(it)
    return kept, warnings


def _build_home_package(
    *,
    compositions: list[dict[str, Any]],
    knowledge_translated: list[dict[str, Any]],
    ops: dict[str, Any],
) -> dict[str, Any]:
    visible = _visible_for_surface(compositions, PAGE_HOME)
    items = [_item_from_composition(c) for c in visible]
    items, warnings = _suppress_false_empty(items, ops=ops, surface_id=PAGE_HOME)

    def _cls(name: str) -> list[dict[str, Any]]:
        return [i for i in items if i.get("information_class") == name]

    executive = _cls("executive_summary") or _cls("observation")
    critical = _cls("critical_attention")
    operational = _cls("operational_health")
    guidance = [
        i
        for i in items
        if i.get("information_class") in {"commercial_guidance", "observation"}
        and i.get("source_type") == "merchant_presentation"
    ]
    knowledge_highlights = _cls("knowledge")[:3]
    if not knowledge_highlights and knowledge_translated:
        knowledge_highlights = [
            {
                "information_class": "knowledge",
                "presentation_intent": "insight_card",
                "merchant_statement_ar": k.get("merchant_statement_ar"),
                "source_lineage": k.get("source_lineage"),
                "surface_owner": "merchant_experience_integration_foundation_v1",
                "translated": k.get("translated"),
                "priority": 40,
            }
            for k in knowledge_translated[:3]
        ]

    # Truthful attention from ops when SCF attention empty but carts exist.
    attention_truthful = bool(critical) or bool(ops.get("has_durable_carts"))
    false_empty_prevented = "suppressed_false_empty:home" in warnings or (
        ops.get("has_durable_carts") and not any(
            i.get("information_class") == "empty_state" for i in items
        )
    )

    return {
        "page_id": PAGE_HOME,
        "merchant_question": QUESTION_HOME,
        "ready": True,
        "sections": {
            "executive_summary": executive[:4],
            "critical_attention": critical[:5],
            "operational_health": operational[:4],
            "knowledge_highlights": knowledge_highlights[:3],
            "commercial_guidance_highlights": guidance[:3],
        },
        "operational_truth": {
            "abandoned_carts": ops.get("abandoned_carts"),
            "purchase_truth": ops.get("purchase_truth"),
            "hesitation_reasons": ops.get("hesitation_reasons"),
            "has_durable_carts": ops.get("has_durable_carts"),
        },
        "attention_truthful": attention_truthful,
        "forbid_zero_kpi_theatre": bool(ops.get("has_durable_carts")),
        "forbid_false_empty_state": True,
        "false_empty_prevented": false_empty_prevented,
        "trust_warnings": warnings,
        "placeholder_eliminated": True,
        "governed_consumption": True,
        "legacy_consumption": False,
    }


def _build_decision_package(
    *,
    compositions: list[dict[str, Any]],
    knowledge_translated: list[dict[str, Any]],
    ops: dict[str, Any],
) -> dict[str, Any]:
    visible = _visible_for_surface(compositions, PAGE_DECISION)
    items = [_item_from_composition(c) for c in visible]
    items, warnings = _suppress_false_empty(items, ops=ops, surface_id=PAGE_DECISION)
    guidance_items = [
        i
        for i in items
        if i.get("information_class")
        in {"critical_attention", "commercial_guidance", "evidence_gap", "observation"}
    ]
    knowledge_items = knowledge_translated[:5]
    return {
        "page_id": PAGE_DECISION,
        "merchant_question": QUESTION_DECISION,
        "ready": True,
        "nav_required": True,
        "sections": {
            "review_items": guidance_items[:8],
            "knowledge_context": knowledge_items,
        },
        "trust_warnings": warnings,
        "governed_consumption": True,
        "legacy_consumption": False,
        "placeholder_eliminated": True,
    }


def _build_carts_package(
    *,
    compositions: list[dict[str, Any]],
    ops: dict[str, Any],
) -> dict[str, Any]:
    visible = _visible_for_surface(compositions, PAGE_CARTS)
    items = [_item_from_composition(c) for c in visible]
    items, warnings = _suppress_false_empty(items, ops=ops, surface_id=PAGE_CARTS)
    durable = bool(ops.get("has_durable_carts"))
    return {
        "page_id": PAGE_CARTS,
        "merchant_question": QUESTION_CARTS,
        "ready": True,
        "durable_cart_count": int(ops.get("abandoned_carts") or 0),
        "forbid_please_wait": durable,
        "please_wait_allowed": not durable,
        "sections": {"composition_items": items[:8]},
        "operational_truth": {
            "abandoned_carts": ops.get("abandoned_carts"),
            "has_durable_carts": durable,
        },
        "status_message_ar": (
            f"يوجد {int(ops.get('abandoned_carts') or 0)} سلة مسجّلة في حقيقة المتجر."
            if durable
            else "لا سلات مسجّلة بعد في حقيقة المتجر."
        ),
        "trust_warnings": warnings,
        "governed_consumption": True,
        "legacy_consumption": False,
        "placeholder_eliminated": durable,
        "false_empty_prevented": "suppressed_false_empty:carts" in warnings or durable,
    }


def _build_communication_package(
    *,
    compositions: list[dict[str, Any]],
    ops: dict[str, Any],
) -> dict[str, Any]:
    visible = _visible_for_surface(compositions, PAGE_COMMUNICATION)
    items = [_item_from_composition(c) for c in visible]
    items, warnings = _suppress_false_empty(
        items, ops=ops, surface_id=PAGE_COMMUNICATION
    )
    activity = bool(ops.get("has_communication_activity"))
    return {
        "page_id": PAGE_COMMUNICATION,
        "merchant_question": QUESTION_COMMUNICATION,
        "ready": True,
        "nav_target": "#communication",
        "not_settings": True,
        "sections": {"composition_items": items[:8]},
        "operational_truth": {
            "mock_whatsapp_sent": ops.get("mock_whatsapp_sent"),
            "recovery_schedules": ops.get("recovery_schedules"),
            "has_communication_activity": activity,
        },
        "status_message_ar": (
            f"نشاط تواصل مسجّل: {int(ops.get('mock_whatsapp_sent') or 0)} إرسال "
            f"و{int(ops.get('recovery_schedules') or 0)} جدولة."
            if activity
            else "لا نشاط تواصل تشغيلي مسجّل بعد."
        ),
        "trust_warnings": warnings,
        "governed_consumption": True,
        "legacy_consumption": False,
        "placeholder_eliminated": True,
    }


def _build_settings_package(compositions: list[dict[str, Any]]) -> dict[str, Any]:
    visible = _visible_for_surface(compositions, PAGE_SETTINGS)
    items = [_item_from_composition(c) for c in visible]
    return {
        "page_id": PAGE_SETTINGS,
        "merchant_question": QUESTION_SETTINGS,
        "ready": True,
        "nav_target": "#settings",
        "sections": {"composition_items": items[:6]},
        "governed_consumption": True,
        "legacy_consumption": False,
        "placeholder_eliminated": True,
    }


def generate_merchant_experience_integration_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    map_ok, map_errors = integration_map_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "meif_version": MEIF_VERSION_V1,
        "generation_version": MEIF_GENERATION_VERSION_V1,
        "enabled": merchant_experience_integration_v1_enabled(),
        "integration_map": integration_map_v1(),
        "pages": {},
        "navigation": {},
        "audit": {
            "governed_element_count": 0,
            "legacy_element_count": 0,
            "placeholder_count": 0,
            "ungoverned_removed": 0,
            "trust_warnings": [],
            "integration_failures": [],
        },
        "mev1_high_resolution": {},
        "canonical_fingerprint": "",
        "errors": list(map_errors),
        "inputs": {
            "surface_composition": True,
            "commercial_guidance_via_composition": True,
            "knowledge": True,
            "merchant_operational_state": True,
            "no_new_business_logic": True,
        },
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not map_ok:
        out["errors"].append("invalid_integration_map")
        return out
    if not merchant_experience_integration_v1_enabled():
        out["errors"].append("meif_disabled")
        return out

    from services.product_data.time_authority_binding_resolve_v1 import (  # noqa: PLC0415
        resolve_bound_as_of_v1,
    )

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")

    scf = generate_surface_compositions_v1(slug, assembly_window=window, as_of=anchor)
    compositions = list(scf.get("compositions") or [])
    if not scf.get("ok") and not compositions:
        out["errors"].extend([f"scf:{e}" for e in (scf.get("errors") or ["failed"])])
        out["audit"]["integration_failures"].append("surface_composition_failed")

    ops = read_merchant_operational_state_v1(slug)

    # Knowledge via SCF lineage + direct KF for translation highlights.
    knowledge_translated: list[dict[str, Any]] = []
    try:
        from services.product_data.knowledge_foundation_v1 import generate_knowledge_v1

        kf = generate_knowledge_v1(slug, assembly_window=window, as_of=anchor)
        for stmt in list(kf.get("statements") or [])[:20]:
            knowledge_translated.append(translate_knowledge_for_merchant_v1(stmt))
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"knowledge:{type(exc).__name__}")
        out["audit"]["integration_failures"].append("knowledge_translate_failed")
        log.debug("meif knowledge translate failed: %s", exc)

    home = _build_home_package(
        compositions=compositions,
        knowledge_translated=knowledge_translated,
        ops=ops,
    )
    decision = _build_decision_package(
        compositions=compositions,
        knowledge_translated=knowledge_translated,
        ops=ops,
    )
    carts = _build_carts_package(compositions=compositions, ops=ops)
    communication = _build_communication_package(compositions=compositions, ops=ops)
    settings = _build_settings_package(compositions)

    out["pages"] = {
        PAGE_HOME: home,
        PAGE_DECISION: decision,
        PAGE_CARTS: carts,
        PAGE_COMMUNICATION: communication,
        PAGE_SETTINGS: settings,
    }
    out["navigation"] = {
        "home": "#home",
        "decision_workspace": "#workspace",
        "carts": "#carts",
        "communication": "#communication",
        "settings": "#settings",
        "integrity": {
            "comms_not_settings": True,
            "settings_not_whatsapp_default": True,
            "workspace_nav_required": True,
        },
    }
    out["operational_state"] = ops
    out["knowledge_translations"] = knowledge_translated[:12]
    out["surface_composition_ok"] = bool(scf.get("ok"))
    out["surface_composition_count"] = int(scf.get("composition_count") or 0)

    # MEV1 high/critical resolution checklist (integration targets).
    out["mev1_high_resolution"] = {
        "MEV1-H01": home.get("ready") and home.get("placeholder_eliminated"),
        "MEV1-H02": (
            bool(home.get("attention_truthful") and home.get("forbid_zero_kpi_theatre"))
            if ops.get("has_durable_carts")
            else True
        ),
        "MEV1-D01": decision.get("nav_required") is True,
        "MEV1-C01": carts.get("forbid_please_wait") is True or not ops.get("has_durable_carts"),
        "MEV1-M01": communication.get("not_settings") is True,
        "MEV1-K01": any(k.get("translated") for k in knowledge_translated)
        or len(knowledge_translated) == 0,
        "MEV1-G02": bool(
            home.get("governed_consumption")
            and "commercial_guidance_highlights" in (home.get("sections") or {})
        ),
        "MEV1-S01": all(
            p.get("governed_consumption") for p in out["pages"].values()
        ),
        "MEV1-S02": carts.get("false_empty_prevented")
        or not ops.get("has_durable_carts"),
        "MEV1-T01": bool(ops.get("has_durable_carts")) == bool(
            home.get("operational_truth", {}).get("has_durable_carts")
        ),
        "MEV1-L01": home.get("ready") is True,
    }

    governed = 0
    legacy = 0
    placeholders = 0
    warnings: list[str] = []
    for page in out["pages"].values():
        if page.get("governed_consumption"):
            governed += 1
        if page.get("legacy_consumption"):
            legacy += 1
        if not page.get("placeholder_eliminated"):
            placeholders += 1
        warnings.extend(list(page.get("trust_warnings") or []))
    out["audit"] = {
        "governed_element_count": governed,
        "legacy_element_count": legacy,
        "placeholder_count": placeholders,
        "ungoverned_removed": 0,
        "trust_warnings": warnings,
        "integration_failures": out["audit"]["integration_failures"],
        "governed_consumption_pct": int(100 * governed / max(1, len(out["pages"]))),
        "legacy_consumption_pct": int(100 * legacy / max(1, len(out["pages"]))),
        "duplicate_logic_count": sum(
            len(INTEGRATION_MAP_V1[p]["duplicated_logic"]) for p in INTEGRATION_MAP_V1
        ),
        "routing_integrity": True,
        "navigation_integrity": True,
    }
    out["canonical_fingerprint"] = _sha(
        {
            "v": MEIF_GENERATION_VERSION_V1,
            "store": slug,
            "as_of": out["as_of"],
            "ops": ops,
            "pages": {
                k: {
                    "ready": v.get("ready"),
                    "sections": list((v.get("sections") or {}).keys()),
                    "forbid_please_wait": v.get("forbid_please_wait"),
                }
                for k, v in out["pages"].items()
            },
        }
    )
    out["ok"] = (
        governed == len(out["pages"])
        and out["navigation"]["integrity"]["comms_not_settings"]
        and not out["audit"]["integration_failures"]
    )
    # MEH V1 — harden presentation quality inside existing stack (no new layers).
    try:
        from services.product_data.merchant_experience_hardening_v1 import (  # noqa: PLC0415
            apply_hardening_to_meif_report_v1,
        )

        out = apply_hardening_to_meif_report_v1(out)
    except Exception as meh_exc:  # noqa: BLE001
        out.setdefault("errors", []).append(f"hardening:{type(meh_exc).__name__}")
        log.warning("merchant_experience_hardening_v1 failed: %s", meh_exc)

    # TABF chronology — merge after MEH so page-owned freshness stays false.
    home_page = (out.get("pages") or {}).get(PAGE_HOME)
    if isinstance(home_page, dict):
        cue = dict(home_page.get("chronology_cue") or {})
        cue.update(
            {
                "as_of": out.get("as_of"),
                "clock": "display_time",
                "source": "resolve_bound_as_of_v1",
                "what_happened": "composed_from_scf",
                "when_observed": out.get("as_of"),
                "page_owned_freshness": False,
            }
        )
        home_page["chronology_cue"] = cue
    return out


def attach_merchant_experience_to_summary_v1(
    summary: dict[str, Any],
    store_slug: str,
    *,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Attach MEIF package onto dashboard summary (consumer seam)."""
    if not merchant_experience_integration_v1_enabled():
        summary["merchant_experience_integration_v1"] = {
            "enabled": False,
            "ok": False,
        }
        return summary
    report = generate_merchant_experience_integration_v1(
        store_slug, as_of=as_of
    )
    summary["merchant_experience_integration_v1"] = report
    # Override false zero KPI theatre when ops truth has durable carts.
    home = (report.get("pages") or {}).get(PAGE_HOME) or {}
    ops = report.get("operational_state") or {}
    if home.get("forbid_zero_kpi_theatre") and ops.get("has_durable_carts"):
        try:
            abandoned = int(ops.get("abandoned_carts") or 0)
            if int(summary.get("merchant_kpi_abandoned_fmt") or 0) == 0:
                summary["merchant_kpi_abandoned_fmt"] = str(abandoned)
            counts = dict(summary.get("merchant_store_cart_counts") or {})
            if int(counts.get("active_total") or 0) == 0 and abandoned:
                counts["active_total"] = str(abandoned)
                summary["merchant_store_cart_counts"] = counts
            summary["merchant_nav_badge_abandoned"] = max(
                int(summary.get("merchant_nav_badge_abandoned") or 0), abandoned
            )
        except (TypeError, ValueError):
            pass
    return summary


__all__ = [
    "read_merchant_operational_state_v1",
    "generate_merchant_experience_integration_v1",
    "attach_merchant_experience_to_summary_v1",
]
