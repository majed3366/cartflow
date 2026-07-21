# -*- coding: utf-8 -*-
"""
Commerce Intelligence → Knowledge Intake V1 (ciknow_v1).

Consumes commerce_intelligence_synthesis_v1 only.
Does not modify generate_knowledge_v1 (ECF-only path preserved).
No Guidance / Presentation / UI.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import KnowledgeStatement
from schema_knowledge_foundation_v1 import ensure_knowledge_foundation_schema
from services.product_data.commerce_intelligence_knowledge_flag_v1 import (
    commerce_intelligence_knowledge_v1_enabled,
)
from services.product_data.commerce_intelligence_knowledge_registry_v1 import (
    intake_policy_for_rule_v1,
    intake_registry_valid_v1,
)
from services.product_data.commerce_intelligence_knowledge_types_v1 import (
    GENERATION_VERSION_V1,
    INPUT_CONTRACT_VERSION_V1,
    INTAKE_POLICY_REGISTRY_VERSION_V1,
    INTAKE_VERSION_V1,
    KNOWLEDGE_VERSION_CIKNOW,
    OUTCOME_ABSTAINED,
    OUTCOME_CREATED,
    OUTCOME_DEFERRED,
    OUTCOME_FAILED,
    OUTCOME_REJECTED,
    OUTCOME_UNCHANGED,
    OUTCOME_UPDATED,
    REASON_BLOCKED,
    REASON_CLAIM_BOUNDARY,
    REASON_COVERAGE,
    REASON_DEFERRED_DEP,
    REASON_DIVERSITY,
    REASON_FAILED_SYN,
    REASON_OBSERVING,
    REASON_POLICY_MISSING,
    REASON_SAMPLE,
    REASON_STATE_NOT_ELIGIBLE,
    REASON_TECHNICAL,
    SOURCE_TYPE_CISYN,
)
from services.product_data.commerce_intelligence_synthesis_foundation_v1 import (
    generate_commerce_intelligence_syntheses_v1,
)
from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    STATE_BLOCKED,
    STATE_FAILED,
    STATE_OBSERVING,
    OUTPUT_CONTRACT_VERSION_V1,
)

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


def _claim_boundary_ok(synthesis: dict[str, Any], record: dict[str, Any]) -> bool:
    """Knowledge must not strengthen synthesis claims."""
    syn_known = set(str(x) for x in (synthesis.get("known_facts") or []))
    syn_unknown = set(str(x) for x in (synthesis.get("unknown_facts") or []))
    syn_prohibited = set(str(x) for x in (synthesis.get("prohibited_claims") or []))
    kn_known = set(str(x) for x in (record.get("known_facts") or []))
    kn_unknown = set(str(x) for x in (record.get("unknown_facts") or []))
    kn_prohibited = set(str(x) for x in (record.get("prohibited_claims") or []))
    # Unknown/prohibited must be preserved (superset OK for unknown; prohibited must cover).
    if not syn_prohibited.issubset(kn_prohibited):
        return False
    if not syn_unknown.issubset(kn_unknown):
        return False
    # Known facts in knowledge must come from synthesis known (plus structural lineage keys).
    structural = {
        k
        for k in kn_known
        if k.startswith("source_") or k.startswith("blocked_") or k.startswith("intake_")
    }
    if not (kn_known - structural).issubset(syn_known | set()):
        # Allow empty known if template-only; disallow invented commercial knowns.
        commercial = kn_known - structural - syn_known
        if commercial:
            return False
    blob = (record.get("statement") or "").lower()
    for bad in ("caused", "will increase", "will improve", "definitely", "guaranteed"):
        if bad in blob:
            return False
    return True


def _account(
    *,
    synthesis: dict[str, Any],
    outcome: str,
    reason: str = "",
    knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "synthesis_id": synthesis.get("synthesis_id"),
        "synthesis_key": synthesis.get("synthesis_key"),
        "synthesis_rule_key": synthesis.get("synthesis_rule_key"),
        "synthesis_state": synthesis.get("synthesis_state"),
        "subject_type": synthesis.get("subject_type"),
        "subject_id": synthesis.get("subject_id"),
        "outcome": outcome,
        "reason": reason,
        "knowledge_id": (knowledge or {}).get("knowledge_id") or "",
        "knowledge_type": (knowledge or {}).get("knowledge_type") or "",
    }


def evaluate_synthesis_for_knowledge_v1(
    synthesis: dict[str, Any],
    *,
    as_of: datetime,
) -> tuple[str, str, dict[str, Any] | None]:
    """
    Returns (outcome, reason, knowledge_record_or_none).
    """
    state = str(synthesis.get("synthesis_state") or "")
    rule_key = str(synthesis.get("synthesis_rule_key") or "")

    if state == STATE_FAILED:
        return OUTCOME_REJECTED, REASON_FAILED_SYN, None
    if state == STATE_BLOCKED:
        return OUTCOME_REJECTED, REASON_BLOCKED, None
    if state == STATE_OBSERVING:
        return OUTCOME_ABSTAINED, REASON_OBSERVING, None

    policy = intake_policy_for_rule_v1(rule_key)
    if policy is None:
        return OUTCOME_REJECTED, REASON_POLICY_MISSING, None
    if policy.get("deferred"):
        return OUTCOME_DEFERRED, REASON_DEFERRED_DEP, None

    eligible = set(policy.get("eligible_states") or ())
    if state not in eligible:
        return OUTCOME_REJECTED, REASON_STATE_NOT_ELIGIBLE, None

    req_summary = str(policy.get("require_summary_contains") or "")
    if req_summary and req_summary not in str(
        synthesis.get("synthesis_summary_key") or ""
    ):
        return OUTCOME_ABSTAINED, REASON_STATE_NOT_ELIGIBLE, None

    coverage = float(synthesis.get("evidence_coverage") or 0.0)
    if coverage < float(policy.get("minimum_evidence_coverage") or 0.0):
        return OUTCOME_REJECTED, REASON_COVERAGE, None
    diversity = len(synthesis.get("source_domains") or [])
    if diversity < int(policy.get("minimum_source_diversity") or 0):
        return OUTCOME_REJECTED, REASON_DIVERSITY, None
    sample = int(synthesis.get("sample_size") or 0)
    if sample < int(policy.get("minimum_sample_size") or 0):
        return OUTCOME_REJECTED, REASON_SAMPLE, None

    subject_type = str(synthesis.get("subject_type") or "")
    allowed_subjects = set(policy.get("target_subject_types") or ())
    if allowed_subjects and subject_type not in allowed_subjects:
        return OUTCOME_REJECTED, REASON_STATE_NOT_ELIGIBLE, None

    contract = str(synthesis.get("contract_version") or "")
    if contract and contract != OUTPUT_CONTRACT_VERSION_V1:
        return OUTCOME_REJECTED, "source_contract_version_unsupported", None

    known = list(synthesis.get("known_facts") or [])
    unknown = list(synthesis.get("unknown_facts") or [])
    prohibited = list(synthesis.get("prohibited_claims") or [])
    if not isinstance(prohibited, list):
        return OUTCOME_REJECTED, REASON_CLAIM_BOUNDARY, None

    statement = str(policy.get("statement_template") or "").strip()
    if not statement:
        return OUTCOME_REJECTED, REASON_STATE_NOT_ELIGIBLE, None

    ktype = str(policy["target_knowledge_type"])
    knowledge_id = _sha(
        {
            "v": INTAKE_VERSION_V1,
            "store": synthesis.get("store_slug"),
            "rule": rule_key,
            "subject_type": subject_type,
            "subject_id": synthesis.get("subject_id"),
            "ktype": ktype,
            "window": synthesis.get("time_window_key"),
            "policy": policy.get("version"),
        }
    )[:32]
    fingerprint = _sha(
        {
            "knowledge_id": knowledge_id,
            "statement": statement,
            "known": known,
            "unknown": unknown,
            "prohibited": prohibited,
            "synthesis_fingerprint": synthesis.get("synthesis_fingerprint"),
            "synthesis_id": synthesis.get("synthesis_id"),
        }
    )
    conf_in = synthesis.get("confidence_input") or {}
    record = {
        "knowledge_id": knowledge_id,
        "store_slug": str(synthesis.get("store_slug") or ""),
        "subject_type": subject_type,
        "subject_id": str(synthesis.get("subject_id") or ""),
        "knowledge_type": ktype,
        "statement": statement,
        "evidence_confidence_id": "",  # CIS path — not ECF
        "confidence_level": str(
            (conf_in.get("sample_maturity") or "from_synthesis")
        )[:32],
        "assembly_window": str(synthesis.get("time_window_key") or ""),
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": (
            _parse_iso(synthesis.get("valid_until")) or (as_of + timedelta(days=7))
        ).isoformat(sep=" "),
        "generated_at": as_of.isoformat(sep=" "),
        "as_of": as_of.isoformat(sep=" "),
        "knowledge_version": KNOWLEDGE_VERSION_CIKNOW,
        "fingerprint": fingerprint,
        "source_type": SOURCE_TYPE_CISYN,
        "source_contract_version": INPUT_CONTRACT_VERSION_V1,
        "source_synthesis_id": str(synthesis.get("synthesis_id") or ""),
        "source_synthesis_key": str(synthesis.get("synthesis_key") or ""),
        "source_rule_key": rule_key,
        "source_rule_version": str(synthesis.get("rule_version") or ""),
        "source_fingerprint": str(synthesis.get("synthesis_fingerprint") or ""),
        "source_window_start": str(synthesis.get("window_start") or ""),
        "source_window_end": str(synthesis.get("window_end") or ""),
        "source_domains": list(synthesis.get("source_domains") or []),
        "known_facts": known,
        "unknown_facts": unknown,
        "prohibited_claims": prohibited,
        "confidence_input": conf_in,
        "intake_version": INTAKE_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "is_current": True,
    }
    if not _claim_boundary_ok(synthesis, record):
        return OUTCOME_REJECTED, REASON_CLAIM_BOUNDARY, None
    return OUTCOME_CREATED, "", record


def generate_knowledge_from_synthesis_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
    rule_keys: Optional[list[str]] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (time_window_key or "d7").strip().lower() or "d7"
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "time_window_key": window,
        "as_of": None,
        "input_contract_version": INPUT_CONTRACT_VERSION_V1,
        "intake_policy_version": INTAKE_POLICY_REGISTRY_VERSION_V1,
        "intake_version": INTAKE_VERSION_V1,
        "eligible_synthesis_count": 0,
        "ineligible_synthesis_count": 0,
        "records": [],
        "accounting": [],
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "abstained": 0,
        "rejected": 0,
        "deferred": 0,
        "failed": 0,
        "unaccounted": 0,
        "canonical_fingerprint": "",
        "claim_boundary_ok": True,
        "errors": [],
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not intake_registry_valid_v1():
        out["errors"].append("intake_registry_invalid")
        return out

    anchor = _floor_second(as_of or _utc_naive_now())
    out["as_of"] = anchor.isoformat(sep=" ")
    syn_report = generate_commerce_intelligence_syntheses_v1(
        slug,
        time_window_key=window,
        as_of=anchor,
        rule_keys=rule_keys,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    syntheses = list(syn_report.get("syntheses") or [])
    if syn_report.get("errors"):
        out["errors"].extend(
            [f"synthesis:{e}" for e in syn_report.get("errors") or []]
        )

    accounting: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for syn in syntheses:
        try:
            outcome, reason, rec = evaluate_synthesis_for_knowledge_v1(
                syn, as_of=anchor
            )
            if outcome == OUTCOME_CREATED and rec is not None:
                records.append(rec)
                out["eligible_synthesis_count"] += 1
                out["created"] += 1
                accounting.append(
                    _account(synthesis=syn, outcome=outcome, knowledge=rec)
                )
            else:
                out["ineligible_synthesis_count"] += 1
                if outcome == OUTCOME_ABSTAINED:
                    out["abstained"] += 1
                elif outcome == OUTCOME_DEFERRED:
                    out["deferred"] += 1
                elif outcome == OUTCOME_REJECTED:
                    out["rejected"] += 1
                elif outcome == OUTCOME_FAILED:
                    out["failed"] += 1
                accounting.append(
                    _account(synthesis=syn, outcome=outcome, reason=reason)
                )
        except Exception as exc:  # noqa: BLE001
            out["failed"] += 1
            out["ineligible_synthesis_count"] += 1
            out["errors"].append(
                f"intake_fail:{syn.get('synthesis_rule_key')}:{type(exc).__name__}"
            )
            accounting.append(
                _account(
                    synthesis=syn,
                    outcome=OUTCOME_FAILED,
                    reason=f"{REASON_TECHNICAL}:{type(exc).__name__}",
                )
            )

    accounted = (
        out["created"]
        + out["updated"]
        + out["unchanged"]
        + out["abstained"]
        + out["rejected"]
        + out["deferred"]
        + out["failed"]
    )
    out["unaccounted"] = max(0, len(syntheses) - accounted)
    out["records"] = records
    out["accounting"] = accounting
    out["canonical_fingerprint"] = _sha(
        {
            "v": GENERATION_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "records": [
                {
                    "knowledge_id": r["knowledge_id"],
                    "fingerprint": r["fingerprint"],
                    "source_synthesis_id": r["source_synthesis_id"],
                }
                for r in records
            ],
            "accounting": [
                {
                    "synthesis_id": a["synthesis_id"],
                    "outcome": a["outcome"],
                    "reason": a.get("reason") or "",
                }
                for a in accounting
            ],
        }
    )
    out["ok"] = out["unaccounted"] == 0 and out["failed"] == 0
    if out["unaccounted"]:
        out["errors"].append("intake_accounting_mismatch")
    return out


def materialize_knowledge_from_synthesis_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
    rule_keys: Optional[list[str]] = None,
) -> dict[str, Any]:
    if not commerce_intelligence_knowledge_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "superseded": 0,
            "errors": ["commerce_intelligence_knowledge_disabled"],
        }

    report = generate_knowledge_from_synthesis_v1(
        store_slug,
        time_window_key=time_window_key,
        as_of=as_of,
        rule_keys=rule_keys,
    )
    ensure_knowledge_foundation_schema(db)
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
            kid = str(rec["knowledge_id"])
            store = str(rec["store_slug"])
            # Supersede other current ciknow rows for same logical key dimensions.
            currents = (
                db.session.query(KnowledgeStatement)
                .filter(
                    KnowledgeStatement.store_slug == store,
                    KnowledgeStatement.knowledge_version == KNOWLEDGE_VERSION_CIKNOW,
                    KnowledgeStatement.source_rule_key
                    == str(rec.get("source_rule_key") or ""),
                    KnowledgeStatement.subject_type == str(rec.get("subject_type") or ""),
                    KnowledgeStatement.subject_id == str(rec.get("subject_id") or ""),
                    KnowledgeStatement.knowledge_type
                    == str(rec.get("knowledge_type") or ""),
                    KnowledgeStatement.is_current.is_(True),
                    KnowledgeStatement.knowledge_id != kid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.superseded_at = now
                superseded += 1

            existing = (
                db.session.query(KnowledgeStatement)
                .filter(KnowledgeStatement.knowledge_id == kid)
                .first()
            )
            fields = dict(
                store_slug=store,
                subject_type=str(rec.get("subject_type") or ""),
                subject_id=str(rec.get("subject_id") or ""),
                knowledge_type=str(rec.get("knowledge_type") or ""),
                statement=str(rec.get("statement") or ""),
                evidence_confidence_id=str(rec.get("evidence_confidence_id") or ""),
                confidence_level=str(rec.get("confidence_level") or ""),
                assembly_window=str(rec.get("assembly_window") or ""),
                valid_from=_parse_iso(rec.get("valid_from")) or anchor,
                valid_until=_parse_iso(rec.get("valid_until"))
                or (anchor + timedelta(days=7)),
                generated_at=now,
                as_of=anchor,
                as_of_key=as_key,
                knowledge_version=KNOWLEDGE_VERSION_CIKNOW,
                fingerprint=str(rec.get("fingerprint") or ""),
                source_type=SOURCE_TYPE_CISYN,
                source_contract_version=str(
                    rec.get("source_contract_version") or INPUT_CONTRACT_VERSION_V1
                ),
                source_synthesis_id=str(rec.get("source_synthesis_id") or ""),
                source_synthesis_key=str(rec.get("source_synthesis_key") or ""),
                source_rule_key=str(rec.get("source_rule_key") or ""),
                source_rule_version=str(rec.get("source_rule_version") or ""),
                source_fingerprint=str(rec.get("source_fingerprint") or ""),
                source_window_start=_parse_iso(rec.get("source_window_start")),
                source_window_end=_parse_iso(rec.get("source_window_end")),
                source_domains_json=json.dumps(
                    rec.get("source_domains") or [], sort_keys=True
                ),
                known_facts_json=json.dumps(
                    rec.get("known_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                unknown_facts_json=json.dumps(
                    rec.get("unknown_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                prohibited_claims_json=json.dumps(
                    rec.get("prohibited_claims") or [], sort_keys=True
                ),
                is_current=True,
                superseded_at=None,
            )
            if existing is None:
                db.session.add(KnowledgeStatement(knowledge_id=kid, **fields))
                created += 1
            else:
                if existing.fingerprint == fields["fingerprint"] and existing.is_current:
                    existing.generated_at = now
                    unchanged += 1
                else:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    updated += 1
            db.session.commit()
        except SQLAlchemyError as exc:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            errors.append(
                f"materialize:{rec.get('source_rule_key')}:{type(exc).__name__}"
            )
            log.debug("ciknow materialize failed: %s", exc)

    return {
        "ok": created + updated + unchanged >= 0
        and not any(e.startswith("materialize:") for e in errors)
        and report.get("unaccounted", 0) == 0
        and report.get("failed", 0) == 0,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "superseded": superseded,
        "abstained": report.get("abstained") or 0,
        "rejected": report.get("rejected") or 0,
        "deferred": report.get("deferred") or 0,
        "failed": report.get("failed") or 0,
        "unaccounted": report.get("unaccounted") or 0,
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "accounting": report.get("accounting") or [],
        "errors": errors,
    }


def verify_ciknow_determinism_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = _floor_second(as_of or _utc_naive_now())
    a = generate_knowledge_from_synthesis_v1(
        store_slug, time_window_key=time_window_key, as_of=anchor
    )
    b = generate_knowledge_from_synthesis_v1(
        store_slug, time_window_key=time_window_key, as_of=anchor
    )
    return {
        "deterministic": (
            a.get("canonical_fingerprint")
            and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
            and a.get("unaccounted") == 0
            and b.get("unaccounted") == 0
        ),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "as_of": anchor.isoformat(sep=" "),
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "evaluate_synthesis_for_knowledge_v1",
    "generate_knowledge_from_synthesis_v1",
    "materialize_knowledge_from_synthesis_v1",
    "verify_ciknow_determinism_v1",
]
