# -*- coding: utf-8 -*-
"""
Commercial Guidance Integration Foundation V1 (cguide_v1).

Consumes current Knowledge records only.
Does not modify generate_commercial_guidance_v1 (eligibility path preserved).
No Routing / Presentation / UI / AI / automatic actions.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CommercialGuidanceRecord, KnowledgeStatement
from schema_commercial_guidance_v1 import ensure_commercial_guidance_schema
from services.product_data.commercial_guidance_knowledge_flag_v1 import (
    commercial_guidance_knowledge_v1_enabled,
)
from services.product_data.commercial_guidance_knowledge_registry_v1 import (
    intake_policy_for_knowledge_type_v1,
    registry_is_valid_v1,
)
from services.product_data.commercial_guidance_knowledge_types_v1 import (
    CAUSAL_INFLATION_TOKENS,
    CIKNOW_KNOWLEDGE_TYPES,
    ELIG_ABSTAIN,
    ELIG_BLOCKED,
    ELIG_CONFLICTING,
    ELIG_ELIGIBLE,
    ELIG_EXPIRED,
    ELIG_INSUFFICIENT,
    ELIG_OBSERVE_ONLY,
    GENERATION_VERSION_V1,
    GUIDANCE_SCOPE_V1,
    GUIDANCE_VERSION_V1,
    INPUT_CONTRACT_VERSION_V1,
    KEY_NO_GUIDANCE,
    KNOWLEDGE_VERSION_FILTER,
    OUTCOME_ABSTAINED,
    OUTCOME_CONFLICTING,
    OUTCOME_CREATED,
    OUTCOME_EVIDENCE_GAP,
    OUTCOME_EXPIRED,
    OUTCOME_FAILED,
    OUTCOME_OBSERVE_ONLY,
    OUTCOME_REJECTED,
    OUTCOME_UNCHANGED,
    OUTCOME_UPDATED,
    REASON_CLAIM_BOUNDARY,
    REASON_EXPIRED,
    REASON_KNOWLEDGE_TYPE_UNSUPPORTED,
    REASON_NOT_CURRENT,
    REASON_POLICY_MISSING,
    REASON_TECHNICAL,
    REGISTRY_VERSION_V1,
    SOURCE_CONTRACT_VERSION_V1,
)
from services.product_data.time_authority_binding_resolve_v1 import resolve_bound_as_of_v1

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


def _loads_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    if not raw:
        return []
    try:
        val = json.loads(str(raw))
        return list(val) if isinstance(val, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _knowledge_row_to_dict(row: KnowledgeStatement) -> dict[str, Any]:
    return {
        "knowledge_id": str(row.knowledge_id or ""),
        "store_slug": str(row.store_slug or ""),
        "subject_type": str(row.subject_type or ""),
        "subject_id": str(row.subject_id or ""),
        "knowledge_type": str(row.knowledge_type or ""),
        "statement": str(row.statement or ""),
        "confidence_level": str(row.confidence_level or ""),
        "assembly_window": str(row.assembly_window or ""),
        "valid_from": row.valid_from.isoformat(sep=" ") if row.valid_from else "",
        "valid_until": row.valid_until.isoformat(sep=" ") if row.valid_until else "",
        "as_of": row.as_of.isoformat(sep=" ") if row.as_of else "",
        "knowledge_version": str(row.knowledge_version or ""),
        "fingerprint": str(row.fingerprint or ""),
        "source_type": str(getattr(row, "source_type", "") or ""),
        "source_contract_version": str(
            getattr(row, "source_contract_version", "") or ""
        ),
        "source_synthesis_id": str(getattr(row, "source_synthesis_id", "") or ""),
        "source_rule_key": str(getattr(row, "source_rule_key", "") or ""),
        "source_fingerprint": str(getattr(row, "source_fingerprint", "") or ""),
        "known_facts": _loads_list(getattr(row, "known_facts_json", "[]")),
        "unknown_facts": _loads_list(getattr(row, "unknown_facts_json", "[]")),
        "prohibited_claims": _loads_list(getattr(row, "prohibited_claims_json", "[]")),
        "is_current": bool(getattr(row, "is_current", True)),
    }


def load_current_knowledge_for_guidance_v1(
    store_slug: str,
    *,
    knowledge_types: Optional[list[str]] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Read current Knowledge only — no CIS, eligibility, or raw domain tables."""
    slug = (store_slug or "").strip()[:255]
    q = db.session.query(KnowledgeStatement).filter(
        KnowledgeStatement.store_slug == slug,
        KnowledgeStatement.is_current.is_(True),
        KnowledgeStatement.knowledge_version == KNOWLEDGE_VERSION_FILTER,
    )
    if knowledge_types:
        q = q.filter(KnowledgeStatement.knowledge_type.in_(list(knowledge_types)))
    else:
        q = q.filter(KnowledgeStatement.knowledge_type.in_(sorted(CIKNOW_KNOWLEDGE_TYPES)))
    if subject_type:
        q = q.filter(KnowledgeStatement.subject_type == subject_type)
    if subject_id is not None:
        q = q.filter(KnowledgeStatement.subject_id == subject_id)
    rows = q.order_by(
        KnowledgeStatement.knowledge_type.asc(),
        KnowledgeStatement.subject_type.asc(),
        KnowledgeStatement.subject_id.asc(),
        KnowledgeStatement.knowledge_id.asc(),
    ).all()
    return [_knowledge_row_to_dict(r) for r in rows]


def _claim_boundary_ok(knowledge: dict[str, Any], guidance: dict[str, Any]) -> bool:
    """Guidance claims ⊆ Knowledge claims; never strengthen."""
    kn_known = set(str(x) for x in (knowledge.get("known_facts") or []))
    kn_unknown = set(str(x) for x in (knowledge.get("unknown_facts") or []))
    kn_prohibited = set(str(x) for x in (knowledge.get("prohibited_claims") or []))
    g_known = set(str(x) for x in (guidance.get("known_facts") or []))
    g_unknown = set(str(x) for x in (guidance.get("unknown_facts") or []))
    g_prohibited = set(str(x) for x in (guidance.get("prohibited_claims") or []))

    if not kn_prohibited.issubset(g_prohibited):
        return False
    if not kn_unknown.issubset(g_unknown):
        return False
    structural = {
        k
        for k in g_known
        if k.startswith("knowledge_")
        or k.startswith("guidance_")
        or k.startswith("source_")
    }
    if not (g_known - structural).issubset(kn_known):
        return False

    blob = " ".join(
        [
            str(guidance.get("merchant_objective") or ""),
            str(guidance.get("rationale_summary") or ""),
            " ".join(str(x) for x in (guidance.get("eligible_actions") or [])),
        ]
    ).lower()
    for bad in CAUSAL_INFLATION_TOKENS:
        if bad in blob:
            return False
    return True


def _account(
    *,
    knowledge: dict[str, Any],
    outcome: str,
    reason: str = "",
    guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "knowledge_id": knowledge.get("knowledge_id"),
        "knowledge_type": knowledge.get("knowledge_type"),
        "subject_type": knowledge.get("subject_type"),
        "subject_id": knowledge.get("subject_id"),
        "outcome": outcome,
        "reason": reason,
        "guidance_id": (guidance or {}).get("guidance_id") or "",
        "guidance_key": (guidance or {}).get("guidance_key") or "",
        "eligibility_status": (guidance or {}).get("eligibility_status") or "",
    }


def evaluate_knowledge_for_guidance_v1(
    knowledge: dict[str, Any],
    *,
    as_of: datetime,
) -> tuple[str, str, dict[str, Any] | None]:
    """
    Returns (outcome, reason, guidance_record_or_none).
    """
    if not knowledge.get("is_current", True):
        return OUTCOME_REJECTED, REASON_NOT_CURRENT, None

    ktype = str(knowledge.get("knowledge_type") or "")
    if ktype not in CIKNOW_KNOWLEDGE_TYPES:
        return OUTCOME_REJECTED, REASON_KNOWLEDGE_TYPE_UNSUPPORTED, None

    policy = intake_policy_for_knowledge_type_v1(ktype)
    if policy is None or not policy.get("active"):
        return OUTCOME_REJECTED, REASON_POLICY_MISSING, None

    valid_until = _parse_iso(knowledge.get("valid_until"))
    if valid_until is not None and valid_until < as_of:
        return OUTCOME_EXPIRED, REASON_EXPIRED, None

    eligibility = str(policy.get("eligibility_when_current") or ELIG_ELIGIBLE)
    guidance_key = str(policy.get("guidance_key") or KEY_NO_GUIDANCE)
    merchant_objective = str(policy.get("merchant_objective") or "").strip()
    eligible_actions = list(policy.get("eligible_actions") or [])
    forbidden_actions = list(policy.get("forbidden_actions") or [])

    known = list(knowledge.get("known_facts") or [])
    unknown = list(knowledge.get("unknown_facts") or [])
    prohibited = list(knowledge.get("prohibited_claims") or [])
    if not isinstance(prohibited, list):
        return OUTCOME_REJECTED, REASON_CLAIM_BOUNDARY, None

    days = int(policy.get("freshness_days") or 7)
    valid_until_g = as_of + timedelta(days=days)
    kn_valid = _parse_iso(knowledge.get("valid_until"))
    if kn_valid is not None and kn_valid < valid_until_g:
        valid_until_g = kn_valid

    input_fingerprint = _sha(
        {
            "knowledge_id": knowledge.get("knowledge_id"),
            "knowledge_fingerprint": knowledge.get("fingerprint"),
            "knowledge_type": ktype,
            "known": known,
            "unknown": unknown,
            "prohibited": prohibited,
            "policy_version": policy.get("version"),
            "registry": REGISTRY_VERSION_V1,
        }
    )
    guidance_id = _sha(
        {
            "v": GUIDANCE_VERSION_V1,
            "gen": GENERATION_VERSION_V1,
            "store": knowledge.get("store_slug"),
            "knowledge_id": knowledge.get("knowledge_id"),
            "knowledge_type": ktype,
            "subject_type": knowledge.get("subject_type"),
            "subject_id": knowledge.get("subject_id"),
            "guidance_key": guidance_key,
            "scope": GUIDANCE_SCOPE_V1,
            "policy": policy.get("version"),
        }
    )[:32]

    if eligibility == ELIG_ELIGIBLE:
        g_status = "active"
        outcome = OUTCOME_CREATED
    elif eligibility == ELIG_OBSERVE_ONLY:
        g_status = "deferred"
        outcome = OUTCOME_OBSERVE_ONLY
    elif eligibility == ELIG_INSUFFICIENT:
        g_status = "deferred"
        outcome = OUTCOME_EVIDENCE_GAP
    elif eligibility == ELIG_CONFLICTING:
        g_status = "deferred"
        outcome = OUTCOME_CONFLICTING
    elif eligibility == ELIG_BLOCKED:
        return OUTCOME_REJECTED, ELIG_BLOCKED, None
    elif eligibility == ELIG_ABSTAIN:
        return OUTCOME_ABSTAINED, ELIG_ABSTAIN, None
    elif eligibility == ELIG_EXPIRED:
        return OUTCOME_EXPIRED, REASON_EXPIRED, None
    else:
        g_status = "abstained"
        outcome = OUTCOME_ABSTAINED

    record = {
        "guidance_id": guidance_id,
        "store_slug": str(knowledge.get("store_slug") or ""),
        "subject_type": str(knowledge.get("subject_type") or ""),
        "subject_id": str(knowledge.get("subject_id") or ""),
        "guidance_key": guidance_key,
        "guidance_version": GUIDANCE_VERSION_V1,
        "guidance_scope": GUIDANCE_SCOPE_V1,
        "knowledge_id": str(knowledge.get("knowledge_id") or ""),
        "knowledge_type": ktype,
        "eligibility_id": str(knowledge.get("knowledge_id") or ""),
        "eligibility_status": eligibility,
        "knowledge_reference_ids": [str(knowledge.get("knowledge_id") or "")],
        "source_contract_version": SOURCE_CONTRACT_VERSION_V1,
        "rule_version": f"cguide_rule_{guidance_key}_v{policy.get('version')}",
        "guidance_status": g_status,
        "rationale_code": f"knowledge:{ktype}:{eligibility}",
        "rationale_summary": merchant_objective,
        "merchant_objective": merchant_objective,
        "eligible_actions": eligible_actions,
        "forbidden_actions": forbidden_actions,
        "known_facts": known,
        "unknown_facts": unknown,
        "prohibited_claims": prohibited,
        "confidence_level": str(knowledge.get("confidence_level") or "from_knowledge"),
        "source_knowledge_fingerprint": str(knowledge.get("fingerprint") or ""),
        "source_lineage": {
            "knowledge_id": knowledge.get("knowledge_id"),
            "knowledge_version": knowledge.get("knowledge_version"),
            "source_type": knowledge.get("source_type"),
            "source_synthesis_id": knowledge.get("source_synthesis_id"),
            "source_rule_key": knowledge.get("source_rule_key"),
            "source_fingerprint": knowledge.get("source_fingerprint"),
        },
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until_g.isoformat(sep=" "),
        "generated_at": as_of.isoformat(sep=" "),
        "refreshed_at": as_of.isoformat(sep=" "),
        "superseded_at": None,
        "is_current": True,
        "input_fingerprint": input_fingerprint,
        "generation_version": GENERATION_VERSION_V1,
        "as_of": as_of.isoformat(sep=" "),
        "routing_eligibility": bool(policy.get("routing_eligibility")),
    }
    record["guidance_fingerprint"] = _sha(
        {k: v for k, v in record.items() if k != "guidance_fingerprint"}
    )
    if not _claim_boundary_ok(knowledge, record):
        return OUTCOME_REJECTED, REASON_CLAIM_BOUNDARY, None
    return outcome, "", record


def generate_commercial_guidance_from_knowledge_v1(
    store_slug: str,
    *,
    as_of: Optional[datetime] = None,
    knowledge_types: Optional[list[str]] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "as_of": None,
        "input_contract_version": INPUT_CONTRACT_VERSION_V1,
        "intake_policy_version": REGISTRY_VERSION_V1,
        "guidance_version": GUIDANCE_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "eligible_knowledge_count": 0,
        "ineligible_knowledge_count": 0,
        "records": [],
        "accounting": [],
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "observe_only": 0,
        "evidence_gap": 0,
        "conflicting": 0,
        "abstained": 0,
        "rejected": 0,
        "expired": 0,
        "failed": 0,
        "unaccounted": 0,
        "canonical_fingerprint": "",
        "claim_boundary_ok": True,
        "lineage_ok": True,
        "errors": [],
        "inputs": {"knowledge_only": True, "cis_direct": False, "eligibility": False},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    ok_reg, reg_errors = registry_is_valid_v1()
    if not ok_reg:
        out["errors"].extend([f"registry:{e}" for e in reg_errors])
        return out

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")

    try:
        knowledge_rows = load_current_knowledge_for_guidance_v1(
            slug,
            knowledge_types=knowledge_types,
            subject_type=subject_type,
            subject_id=subject_id,
        )
    except SQLAlchemyError as exc:
        out["errors"].append(f"knowledge_load:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return out

    accounting: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for kn in knowledge_rows:
        try:
            outcome, reason, rec = evaluate_knowledge_for_guidance_v1(
                kn, as_of=anchor
            )
            if rec is not None:
                records.append(rec)
                out["eligible_knowledge_count"] += 1
                if outcome == OUTCOME_CREATED:
                    out["created"] += 1
                elif outcome == OUTCOME_OBSERVE_ONLY:
                    out["observe_only"] += 1
                elif outcome == OUTCOME_EVIDENCE_GAP:
                    out["evidence_gap"] += 1
                elif outcome == OUTCOME_CONFLICTING:
                    out["conflicting"] += 1
                elif outcome == OUTCOME_UPDATED:
                    out["updated"] += 1
                elif outcome == OUTCOME_UNCHANGED:
                    out["unchanged"] += 1
                else:
                    out["failed"] += 1
                    out["errors"].append(
                        f"unexpected_record_outcome:{outcome}:{kn.get('knowledge_id')}"
                    )
                if not _claim_boundary_ok(kn, rec):
                    out["claim_boundary_ok"] = False
                if not rec.get("knowledge_id") or not rec.get("source_lineage"):
                    out["lineage_ok"] = False
                accounting.append(
                    _account(knowledge=kn, outcome=outcome, guidance=rec)
                )
            else:
                out["ineligible_knowledge_count"] += 1
                if outcome == OUTCOME_ABSTAINED:
                    out["abstained"] += 1
                elif outcome == OUTCOME_REJECTED:
                    out["rejected"] += 1
                elif outcome == OUTCOME_EXPIRED:
                    out["expired"] += 1
                elif outcome == OUTCOME_FAILED:
                    out["failed"] += 1
                elif outcome == OUTCOME_OBSERVE_ONLY:
                    out["observe_only"] += 1
                else:
                    out["rejected"] += 1
                accounting.append(
                    _account(knowledge=kn, outcome=outcome, reason=reason)
                )
        except Exception as exc:  # noqa: BLE001
            out["failed"] += 1
            out["ineligible_knowledge_count"] += 1
            out["errors"].append(
                f"intake_fail:{kn.get('knowledge_type')}:{type(exc).__name__}"
            )
            accounting.append(
                _account(
                    knowledge=kn,
                    outcome=OUTCOME_FAILED,
                    reason=f"{REASON_TECHNICAL}:{type(exc).__name__}",
                )
            )

    accounted = (
        out["created"]
        + out["updated"]
        + out["unchanged"]
        + out["observe_only"]
        + out["evidence_gap"]
        + out["conflicting"]
        + out["abstained"]
        + out["rejected"]
        + out["expired"]
        + out["failed"]
    )
    out["unaccounted"] = max(0, len(knowledge_rows) - accounted)
    out["records"] = records
    out["accounting"] = accounting
    out["canonical_fingerprint"] = _sha(
        {
            "v": GENERATION_VERSION_V1,
            "store": slug,
            "as_of": out["as_of"],
            "records": [
                {
                    "guidance_id": r["guidance_id"],
                    "guidance_fingerprint": r["guidance_fingerprint"],
                    "knowledge_id": r["knowledge_id"],
                }
                for r in records
            ],
            "accounting": [
                {
                    "knowledge_id": a["knowledge_id"],
                    "outcome": a["outcome"],
                    "reason": a.get("reason") or "",
                }
                for a in accounting
            ],
        }
    )
    out["ok"] = out["unaccounted"] == 0 and out["failed"] == 0 and out["claim_boundary_ok"]
    if out["unaccounted"]:
        out["errors"].append("intake_accounting_mismatch")
    return out


def materialize_commercial_guidance_from_knowledge_v1(
    store_slug: str,
    *,
    as_of: Optional[datetime] = None,
    knowledge_types: Optional[list[str]] = None,
) -> dict[str, Any]:
    if not commercial_guidance_knowledge_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "superseded": 0,
            "errors": ["commercial_guidance_knowledge_disabled"],
        }

    report = generate_commercial_guidance_from_knowledge_v1(
        store_slug,
        as_of=as_of,
        knowledge_types=knowledge_types,
    )
    ensure_commercial_guidance_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    created = 0
    updated = 0
    unchanged = 0
    superseded = 0
    errors: list[str] = list(report.get("errors") or [])

    for rec in report.get("records") or []:
        try:
            gid = str(rec["guidance_id"])
            store = str(rec["store_slug"])
            stype = str(rec.get("subject_type") or "")
            sid = str(rec.get("subject_id") or "")
            scope = str(rec.get("guidance_scope") or GUIDANCE_SCOPE_V1)

            currents = (
                db.session.query(CommercialGuidanceRecord)
                .filter(
                    CommercialGuidanceRecord.store_slug == store,
                    CommercialGuidanceRecord.subject_type == stype,
                    CommercialGuidanceRecord.subject_id == sid,
                    CommercialGuidanceRecord.guidance_scope == scope,
                    CommercialGuidanceRecord.generation_version
                    == GENERATION_VERSION_V1,
                    CommercialGuidanceRecord.is_current.is_(True),
                    CommercialGuidanceRecord.guidance_id != gid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.guidance_status = "superseded"
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
                guidance_key=str(rec.get("guidance_key") or ""),
                guidance_version=GUIDANCE_VERSION_V1,
                guidance_scope=scope,
                eligibility_id=str(rec.get("eligibility_id") or ""),
                eligibility_status=str(rec.get("eligibility_status") or ""),
                knowledge_reference_ids_json=json.dumps(
                    rec.get("knowledge_reference_ids") or [], sort_keys=True
                ),
                source_contract_version=SOURCE_CONTRACT_VERSION_V1,
                rule_version=str(rec.get("rule_version") or ""),
                guidance_status=str(rec.get("guidance_status") or "abstained"),
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
                knowledge_id=str(rec.get("knowledge_id") or ""),
                knowledge_type=str(rec.get("knowledge_type") or ""),
                merchant_objective=str(rec.get("merchant_objective") or ""),
                eligible_actions_json=json.dumps(
                    rec.get("eligible_actions") or [], sort_keys=True
                ),
                forbidden_actions_json=json.dumps(
                    rec.get("forbidden_actions") or [], sort_keys=True
                ),
                confidence_level=str(rec.get("confidence_level") or ""),
                source_knowledge_fingerprint=str(
                    rec.get("source_knowledge_fingerprint") or ""
                ),
                valid_from=anchor,
                valid_until=_parse_iso(rec.get("valid_until"))
                or (anchor + timedelta(days=7)),
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
                created += 1
            else:
                same_fp = str(existing.guidance_fingerprint or "") == str(
                    fields["guidance_fingerprint"]
                )
                for k, v in fields.items():
                    setattr(existing, k, v)
                if same_fp:
                    unchanged += 1
                else:
                    updated += 1
            db.session.commit()
        except Exception as exc:  # noqa: BLE001
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            errors.append(
                f"materialize:{rec.get('knowledge_id')}:{type(exc).__name__}"
            )
            log.debug("cguide materialize item failed: %s", exc)

    return {
        "ok": len(errors) == 0 and report.get("unaccounted", 0) == 0,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "superseded": superseded,
        "errors": errors,
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "generate_report": {
            "created": report.get("created"),
            "observe_only": report.get("observe_only"),
            "evidence_gap": report.get("evidence_gap"),
            "conflicting": report.get("conflicting"),
            "abstained": report.get("abstained"),
            "rejected": report.get("rejected"),
            "expired": report.get("expired"),
            "failed": report.get("failed"),
            "unaccounted": report.get("unaccounted"),
            "eligible_knowledge_count": report.get("eligible_knowledge_count"),
            "ineligible_knowledge_count": report.get("ineligible_knowledge_count"),
            "claim_boundary_ok": report.get("claim_boundary_ok"),
            "lineage_ok": report.get("lineage_ok"),
        },
        "store_slug": report.get("store_slug"),
        "as_of": report.get("as_of"),
    }


def verify_cguide_determinism_v1(
    store_slug: str,
    *,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = resolve_bound_as_of_v1(as_of)
    a = generate_commercial_guidance_from_knowledge_v1(store_slug, as_of=anchor)
    b = generate_commercial_guidance_from_knowledge_v1(store_slug, as_of=anchor)
    return {
        "deterministic": (
            a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
            and a.get("ok") == b.get("ok")
        ),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "as_of": a.get("as_of"),
        "guidance_count": len(a.get("records") or []),
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "load_current_knowledge_for_guidance_v1",
    "evaluate_knowledge_for_guidance_v1",
    "generate_commercial_guidance_from_knowledge_v1",
    "materialize_commercial_guidance_from_knowledge_v1",
    "verify_cguide_determinism_v1",
]
