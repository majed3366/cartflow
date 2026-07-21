# -*- coding: utf-8 -*-
"""
Commercial Guidance Foundation V1 — Eligibility-only permitted guidance.

Deterministic registry selection. No AI, UI, or automatic actions.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CommercialGuidanceRecord
from schema_commercial_guidance_v1 import ensure_commercial_guidance_schema
from services.product_data.commercial_guidance_flag_v1 import (
    commercial_guidance_v1_enabled,
)
from services.product_data.commercial_guidance_registry_v1 import (
    get_registry_entry_v1,
    registry_is_valid_v1,
)
from services.product_data.commercial_guidance_types_v1 import (
    CART_PROGRESSION_METRIC_KEYS,
    GENERATION_VERSION_V1,
    GUIDANCE_KEYS,
    GUIDANCE_SCOPE_V1,
    GUIDANCE_VERSION_V1,
    INTENT_METRIC_KEYS,
    KEY_CONTINUE_OBSERVING,
    KEY_DEFER,
    KEY_INVESTIGATE_CONVERSION,
    KEY_MONITOR_NEW,
    KEY_NO_GUIDANCE,
    KEY_REVIEW_CART,
    KEY_REVIEW_PRODUCT,
    KEY_VERIFY_GAP,
    SOURCE_CONTRACT_VERSION_V1,
    STATUS_ABSTAINED,
    STATUS_ACTIVE,
    STATUS_DEFERRED,
    STATUS_SUPERSEDED,
)
from services.product_data.guidance_eligibility_foundation_v1 import (
    evaluate_guidance_eligibility_v1,
)
from services.product_data.guidance_eligibility_types_v1 import STATUS_ELIGIBLE

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _as_of_key(dt: datetime) -> str:
    return _floor_second(dt).strftime("%Y%m%d%H%M%S")


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _floor_second(value)
    try:
        return _floor_second(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def _ctx_types(ctx: list[dict[str, Any]]) -> set[str]:
    return {str(c.get("knowledge_type") or "") for c in ctx}


def _known_facts(ctx: list[dict[str, Any]]) -> list[str]:
    facts = [str(c.get("statement") or "").strip() for c in ctx]
    return sorted({f for f in facts if f})


def _select_guidance_key_v1(
    *,
    eligibility_status: str,
    subject_type: str,
    knowledge_context: list[dict[str, Any]],
    blocking_conditions: list[str],
) -> tuple[str, str, str]:
    """
    Return (guidance_key, rationale_code, rationale_summary).
    Deterministic priority; first match wins.
    """
    status = str(eligibility_status or "")
    if status != STATUS_ELIGIBLE:
        code = status or "ineligible"
        return (
            KEY_NO_GUIDANCE,
            f"abstain:{code}",
            f"Eligibility status {code} blocks commercial guidance.",
        )

    if blocking_conditions:
        return (
            KEY_NO_GUIDANCE,
            "abstain:blocking_conditions",
            "Blocking conditions remain on the eligibility record.",
        )

    if not knowledge_context:
        return (
            KEY_NO_GUIDANCE,
            "abstain:missing_knowledge_context",
            "Eligibility record lacks knowledge_context required for guidance.",
        )

    types = _ctx_types(knowledge_context)
    gaps = {
        str(c.get("gap_key") or "")
        for c in knowledge_context
        if str(c.get("knowledge_type") or "") == "evidence_gap"
    }
    trends = [
        c
        for c in knowledge_context
        if str(c.get("knowledge_type") or "") == "metric_trend_observation"
    ]
    trend_metrics = {str(t.get("metric_key") or "") for t in trends}
    directions = {str(t.get("trend_direction") or "") for t in trends}
    has_intent = bool(trend_metrics & INTENT_METRIC_KEYS)
    has_purchase_gap = "purchase_count" in gaps
    has_new = "newly_appeared" in directions
    has_cart_prog = bool(trend_metrics & CART_PROGRESSION_METRIC_KEYS)

    if has_purchase_gap and has_intent:
        return (
            KEY_INVESTIGATE_CONVERSION,
            "rule:intent_without_purchase_evidence",
            "Intent/cart activity is observed while purchase evidence is missing.",
        )
    if has_new:
        return (
            KEY_MONITOR_NEW,
            "rule:newly_appeared_pattern",
            "A pattern newly appeared; monitor persistence before commercial change.",
        )
    if has_cart_prog:
        return (
            KEY_REVIEW_CART,
            "rule:cart_progression_review",
            "Cart progression knowledge warrants review without a proven cause.",
        )
    if subject_type == "product" and has_intent:
        return (
            KEY_REVIEW_PRODUCT,
            "rule:product_journey_review",
            "Product-level activity warrants experience review without a proven cause.",
        )
    if "evidence_gap" in types:
        return (
            KEY_VERIFY_GAP,
            "rule:evidence_gap_limits_guidance",
            "An evidence gap limits stronger commercial conclusions.",
        )
    if "evidence_quality" in types and "metric_trend_observation" in types:
        return (
            KEY_CONTINUE_OBSERVING,
            "rule:observe_eligible_pattern",
            "Eligible pattern exists without justification for stronger guidance.",
        )
    return (
        KEY_DEFER,
        "rule:defer_until_more_evidence",
        "Eligible but no registered stronger rule matched; defer action.",
    )


def evaluate_subject_guidance_v1(
    *,
    eligibility: dict[str, Any],
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    """Build one guidance record from a single eligibility evaluation dict."""
    ok_reg, reg_errors = registry_is_valid_v1()
    if not ok_reg:
        key = KEY_NO_GUIDANCE
        rationale_code = "abstain:invalid_registry"
        rationale_summary = "Guidance registry failed validation."
        entry = get_registry_entry_v1(KEY_NO_GUIDANCE) or {}
    else:
        key, rationale_code, rationale_summary = _select_guidance_key_v1(
            eligibility_status=str(eligibility.get("eligibility_status") or ""),
            subject_type=str(eligibility.get("subject_type") or ""),
            knowledge_context=list(eligibility.get("knowledge_context") or []),
            blocking_conditions=list(eligibility.get("blocking_conditions") or []),
        )
        entry = get_registry_entry_v1(key)
        if entry is None or key not in GUIDANCE_KEYS:
            key = KEY_NO_GUIDANCE
            rationale_code = "abstain:unsupported_guidance_type"
            rationale_summary = "Selected guidance key is not registry-supported."
            entry = get_registry_entry_v1(KEY_NO_GUIDANCE) or {}

    ctx = list(eligibility.get("knowledge_context") or [])
    known = _known_facts(ctx)
    unknowns = list(entry.get("default_unknowns") or [])
    prohibited = list(entry.get("default_prohibited_claims") or [])
    g_status = str(entry.get("default_guidance_status") or STATUS_ABSTAINED)
    if key == KEY_NO_GUIDANCE:
        g_status = STATUS_ABSTAINED
    elif key == KEY_DEFER:
        g_status = STATUS_DEFERRED
    elif g_status not in {STATUS_ACTIVE, STATUS_DEFERRED, STATUS_ABSTAINED}:
        g_status = STATUS_ACTIVE

    days = int(entry.get("default_validity_days") or 7)
    valid_until = as_of + timedelta(days=days)
    knowledge_refs = sorted(
        str(x) for x in (eligibility.get("knowledge_ids") or []) if x
    )
    if not knowledge_refs:
        knowledge_refs = sorted(
            str(c.get("knowledge_id") or "") for c in ctx if c.get("knowledge_id")
        )

    input_fingerprint = _sha(
        {
            "eligibility_id": eligibility.get("eligibility_id"),
            "eligibility_status": eligibility.get("eligibility_status"),
            "eligibility_fingerprint": eligibility.get("fingerprint"),
            "knowledge_context": ctx,
            "blocking_conditions": eligibility.get("blocking_conditions") or [],
            "contract_version": eligibility.get("contract_version")
            or SOURCE_CONTRACT_VERSION_V1,
        }
    )
    guidance_id = _sha(
        {
            "v": GUIDANCE_VERSION_V1,
            "gen": GENERATION_VERSION_V1,
            "store": eligibility.get("store_slug"),
            "subject_type": eligibility.get("subject_type"),
            "subject_id": eligibility.get("subject_id"),
            "scope": GUIDANCE_SCOPE_V1,
            "as_of": _as_of_key(as_of),
            "key": key,
            "eligibility_id": eligibility.get("eligibility_id"),
            "input": input_fingerprint,
        }
    )[:32]

    subject_type = str(eligibility.get("subject_type") or "")
    cart_related = subject_type in {"cart", "product"} or key in {
        KEY_REVIEW_CART,
        KEY_INVESTIGATE_CONVERSION,
    }
    record = {
        "guidance_id": guidance_id,
        "store_slug": str(eligibility.get("store_slug") or ""),
        "subject_type": subject_type,
        "subject_id": str(eligibility.get("subject_id") or ""),
        "guidance_key": key,
        "guidance_version": GUIDANCE_VERSION_V1,
        "guidance_scope": GUIDANCE_SCOPE_V1,
        "eligibility_id": str(eligibility.get("eligibility_id") or ""),
        "eligibility_status": str(eligibility.get("eligibility_status") or ""),
        "knowledge_reference_ids": knowledge_refs,
        "source_contract_version": str(
            eligibility.get("contract_version") or SOURCE_CONTRACT_VERSION_V1
        ),
        "rule_version": str(entry.get("rule_version") or ""),
        "guidance_status": g_status,
        "rationale_code": rationale_code,
        "rationale_summary": rationale_summary,
        "known_facts": known,
        "unknown_facts": unknowns,
        "prohibited_claims": prohibited,
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "generated_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "is_current": True,
        "input_fingerprint": input_fingerprint,
        "generation_version": GENERATION_VERSION_V1,
        "as_of": as_of.isoformat(sep=" "),
        "registry_errors": list(reg_errors),
        # Governed digest for Guidance Routing (no presentation fields).
        "routing_context": {
            "guidance_key": key,
            "guidance_status": g_status,
            "subject_type": subject_type,
            "guidance_scope": GUIDANCE_SCOPE_V1,
            "cart_related": bool(cart_related),
            "contract_version": "cgf_v1_routing_context",
        },
    }
    record["guidance_fingerprint"] = _sha(
        {k: v for k, v in record.items() if k != "guidance_fingerprint"}
    )
    return record


def generate_commercial_guidance_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate guidance exclusively via Guidance Eligibility API."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "guidance_version": GUIDANCE_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "records": [],
        "guidance_count": 0,
        "canonical_fingerprint": "",
        "errors": [],
        "inputs": {"guidance_eligibility_only": True},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out

    anchor = _floor_second(as_of or _utc_naive_now())
    out["as_of"] = anchor.isoformat(sep=" ")
    eligibility = evaluate_guidance_eligibility_v1(
        slug, assembly_window=window, as_of=anchor
    )
    if not eligibility.get("ok"):
        out["errors"].extend(
            [f"eligibility:{e}" for e in (eligibility.get("errors") or ["failed"])]
        )
        return out

    records = [
        evaluate_subject_guidance_v1(
            eligibility=ev,
            as_of=anchor,
            generated_at=anchor,
        )
        for ev in sorted(
            eligibility.get("evaluations") or [],
            key=lambda e: (
                str(e.get("subject_type") or ""),
                str(e.get("subject_id") or ""),
            ),
        )
    ]
    out["records"] = records
    out["guidance_count"] = len(records)
    out["canonical_fingerprint"] = _sha(
        {
            "v": GENERATION_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "records": [
                {
                    "guidance_id": r["guidance_id"],
                    "guidance_key": r["guidance_key"],
                    "guidance_fingerprint": r["guidance_fingerprint"],
                }
                for r in records
            ],
        }
    )
    out["ok"] = True
    return out


def materialize_commercial_guidance_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not commercial_guidance_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "superseded": 0,
            "errors": ["commercial_guidance_disabled"],
        }

    report = generate_commercial_guidance_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "superseded": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_commercial_guidance_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    superseded = 0
    try:
        for rec in report.get("records") or []:
            key = str(rec.get("guidance_key") or "")
            if key not in GUIDANCE_KEYS or get_registry_entry_v1(key) is None:
                return {
                    "ok": False,
                    "upserted": 0,
                    "superseded": 0,
                    "errors": [f"unsupported_guidance_type:{key}"],
                    "canonical_fingerprint": report.get("canonical_fingerprint") or "",
                }
            gid = str(rec["guidance_id"])
            store = str(rec["store_slug"])
            stype = str(rec.get("subject_type") or "")
            sid = str(rec.get("subject_id") or "")
            scope = str(rec.get("guidance_scope") or GUIDANCE_SCOPE_V1)

            # Supersede other current rows for same subject/scope when id differs.
            currents = (
                db.session.query(CommercialGuidanceRecord)
                .filter(
                    CommercialGuidanceRecord.store_slug == store,
                    CommercialGuidanceRecord.subject_type == stype,
                    CommercialGuidanceRecord.subject_id == sid,
                    CommercialGuidanceRecord.guidance_scope == scope,
                    CommercialGuidanceRecord.is_current.is_(True),
                    CommercialGuidanceRecord.guidance_id != gid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.guidance_status = STATUS_SUPERSEDED
                row.superseded_at = now
                superseded += 1

            existing = (
                db.session.query(CommercialGuidanceRecord)
                .filter(CommercialGuidanceRecord.guidance_id == gid)
                .first()
            )
            fields = dict(
                store_slug=store,
                subject_type=stype,
                subject_id=sid,
                guidance_key=key,
                guidance_version=GUIDANCE_VERSION_V1,
                guidance_scope=scope,
                eligibility_id=str(rec.get("eligibility_id") or ""),
                eligibility_status=str(rec.get("eligibility_status") or ""),
                knowledge_reference_ids_json=json.dumps(
                    rec.get("knowledge_reference_ids") or [], sort_keys=True
                ),
                source_contract_version=str(
                    rec.get("source_contract_version") or SOURCE_CONTRACT_VERSION_V1
                ),
                rule_version=str(rec.get("rule_version") or ""),
                guidance_status=str(rec.get("guidance_status") or STATUS_ABSTAINED),
                rationale_code=str(rec.get("rationale_code") or ""),
                rationale_summary=str(rec.get("rationale_summary") or ""),
                known_facts_json=json.dumps(
                    rec.get("known_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                unknown_facts_json=json.dumps(
                    rec.get("unknown_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                prohibited_claims_json=json.dumps(
                    rec.get("prohibited_claims") or [],
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                valid_from=anchor,
                valid_until=_parse_iso(rec.get("valid_until")) or (
                    anchor + timedelta(days=7)
                ),
                generated_at=existing.generated_at if existing else now,
                refreshed_at=now,
                superseded_at=None,
                is_current=True,
                input_fingerprint=str(rec.get("input_fingerprint") or ""),
                guidance_fingerprint=str(rec.get("guidance_fingerprint") or ""),
                generation_version=GENERATION_VERSION_V1,
                as_of=anchor,
                as_of_key=as_key,
            )
            if existing is None:
                db.session.add(CommercialGuidanceRecord(guidance_id=gid, **fields))
            else:
                for k, v in fields.items():
                    setattr(existing, k, v)
            upserted += 1
        db.session.commit()
    except SQLAlchemyError as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.debug("commercial guidance materialize failed: %s", exc)
        return {
            "ok": False,
            "upserted": 0,
            "superseded": 0,
            "errors": [f"materialize:{type(exc).__name__}"],
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    return {
        "ok": True,
        "upserted": upserted,
        "superseded": superseded,
        "errors": [],
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "guidance_count": report.get("guidance_count") or 0,
        "store_slug": report.get("store_slug"),
        "assembly_window": report.get("assembly_window"),
        "as_of": report.get("as_of"),
    }


def verify_commercial_guidance_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = _floor_second(as_of or _utc_naive_now())
    a = generate_commercial_guidance_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = generate_commercial_guidance_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    match = bool(
        a.get("ok")
        and b.get("ok")
        and a.get("canonical_fingerprint")
        and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
    )
    return {
        "ok": match,
        "deterministic": match,
        "as_of": anchor.isoformat(sep=" "),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "guidance_count": a.get("guidance_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "evaluate_subject_guidance_v1",
    "generate_commercial_guidance_v1",
    "materialize_commercial_guidance_v1",
    "verify_commercial_guidance_determinism_v1",
]
