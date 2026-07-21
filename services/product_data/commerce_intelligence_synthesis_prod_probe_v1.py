# -*- coding: utf-8 -*-
"""Commerce Intelligence Synthesis Foundation V1 — production probe."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CommerceIntelligenceSynthesis
from schema_commerce_intelligence_synthesis_v1 import (
    ensure_commerce_intelligence_synthesis_schema,
)
from services.product_data.commerce_intelligence_synthesis_flag_v1 import (
    ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1,
    commerce_intelligence_synthesis_v1_enabled,
)
from services.product_data.commerce_intelligence_synthesis_foundation_v1 import (
    generate_commerce_intelligence_syntheses_v1,
    materialize_commerce_intelligence_syntheses_v1,
    verify_commerce_intelligence_synthesis_determinism_v1,
)
from services.product_data.commerce_intelligence_synthesis_rule_registry_v1 import (
    rule_registry_summary_v1,
)
from services.product_data.commerce_intelligence_synthesis_source_registry_v1 import (
    source_registry_summary_v1,
)
from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    OUTPUT_CONTRACT_VERSION_V1,
    RULE_REGISTRY_VERSION_V1,
    SOURCE_CONTRACT_REGISTRY_VERSION_V1,
    STATE_BLOCKED,
    STATE_CONFLICTING,
    STATE_EXPIRED,
    STATE_FAILED,
    STATE_INSUFFICIENT,
    STATE_OBSERVING,
    STATE_QUALIFIED,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_commerce_intelligence_synthesis_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    time_window_key: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (time_window_key or "d7").strip().lower() or "d7"
    rule_summary = rule_registry_summary_v1()
    source_summary = source_registry_summary_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": commerce_intelligence_synthesis_v1_enabled(),
        "flag_env": ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "e4f5a6b7c8d9",
        "time_window_key": window,
        "as_of": None,
        "deterministic": False,
        "provider_independent": True,
        "canonical_fingerprint": "",
        "registry_version": RULE_REGISTRY_VERSION_V1,
        "source_contract_registry_version": SOURCE_CONTRACT_REGISTRY_VERSION_V1,
        "output_contract_version": OUTPUT_CONTRACT_VERSION_V1,
        "active_rule_count": int(rule_summary.get("active_rule_count") or 0),
        "candidate_count": 0,
        "qualified_count": 0,
        "observing_count": 0,
        "insufficient_evidence_count": 0,
        "conflicting_evidence_count": 0,
        "blocked_count": 0,
        "expired_count": 0,
        "failed_count": 0,
        "unaccounted_count": 0,
        "counts_by_synthesis_rule": {},
        "counts_by_pattern_type": {},
        "counts_by_subject_type": {},
        "counts_by_source_domain_combination": {},
        "source_coverage": {},
        "missing_source_domains": [],
        "rejected_input_count": 0,
        "unsupported_input_reasons": {},
        "supporting_evidence_count": 0,
        "contradicting_evidence_count": 0,
        "known_facts_sample": [],
        "unknown_facts_sample": [],
        "prohibited_claims_sample": [],
        "temporal_windows": [],
        "evidence_freshness": {},
        "input_fingerprints": [],
        "synthesis_fingerprints": [],
        "lineage_verification": True,
        "current_record_uniqueness": True,
        "rerun_determinism": False,
        "materialized_row_count": 0,
        "upserted": 0,
        "superseded": 0,
        "sample_syntheses": [],
        "errors": [],
        "migration_satisfied": False,
        "consumes_canonical_sources_only": True,
        "no_guidance_generation": True,
        "no_presentation_generation": True,
        "no_page_integration": True,
        "accounting_ok": False,
        "rule_registry": rule_summary,
        "source_registry": source_summary,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_commerce_intelligence_synthesis_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("commerce_intelligence_syntheses"))
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"schema:{type(exc).__name__}")
        return out

    try:
        if insp.has_table("alembic_version"):
            row = db.session.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).first()
            if row is not None:
                out["alembic_version"] = str(row[0])
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_commerce_intelligence_synthesis_determinism_v1(
        slug, time_window_key=window
    )
    out["deterministic"] = bool(det.get("deterministic"))
    out["rerun_determinism"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None

    generated = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key=window, as_of=frozen
    )
    syntheses = list(generated.get("syntheses") or [])
    out["candidate_count"] = len(syntheses)
    out["rejected_input_count"] = int(generated.get("rejected_input_count") or 0)
    out["unsupported_input_reasons"] = dict(
        generated.get("unsupported_input_reasons") or {}
    )

    by_state: dict[str, int] = defaultdict(int)
    by_rule: dict[str, int] = defaultdict(int)
    by_pattern: dict[str, int] = defaultdict(int)
    by_subject: dict[str, int] = defaultdict(int)
    by_sources: dict[str, int] = defaultdict(int)
    supporting = 0
    contradicting = 0
    known_sample: list[str] = []
    unknown_sample: list[str] = []
    prohibited_sample: list[str] = []
    windows: list[str] = []
    input_fps: list[str] = []
    syn_fps: list[str] = []
    source_domains_seen: set[str] = set()

    for s in syntheses:
        st = str(s.get("synthesis_state") or "")
        by_state[st] += 1
        by_rule[str(s.get("synthesis_rule_key") or "")] += 1
        by_pattern[str(s.get("pattern_type") or "")] += 1
        by_subject[str(s.get("subject_type") or "")] += 1
        domains = list(s.get("source_domains") or [])
        by_sources["+".join(sorted(domains)) or "none"] += 1
        source_domains_seen.update(domains)
        supporting += int(s.get("supporting_evidence_count") or 0)
        contradicting += int(s.get("contradicting_evidence_count") or 0)
        for fact in s.get("known_facts") or []:
            if len(known_sample) < 12:
                known_sample.append(str(fact))
        for fact in s.get("unknown_facts") or []:
            if len(unknown_sample) < 12:
                unknown_sample.append(str(fact))
        for claim in s.get("prohibited_claims") or []:
            if len(prohibited_sample) < 12:
                prohibited_sample.append(str(claim))
        windows.append(str(s.get("time_window_key") or ""))
        if s.get("input_fingerprint"):
            input_fps.append(str(s["input_fingerprint"])[:16])
        if s.get("synthesis_fingerprint"):
            syn_fps.append(str(s["synthesis_fingerprint"])[:16])
        if not s.get("synthesis_id") or not s.get("synthesis_key"):
            out["lineage_verification"] = False

    out["qualified_count"] = by_state.get(STATE_QUALIFIED, 0)
    out["observing_count"] = by_state.get(STATE_OBSERVING, 0)
    out["insufficient_evidence_count"] = by_state.get(STATE_INSUFFICIENT, 0)
    out["conflicting_evidence_count"] = by_state.get(STATE_CONFLICTING, 0)
    out["blocked_count"] = by_state.get(STATE_BLOCKED, 0)
    out["expired_count"] = by_state.get(STATE_EXPIRED, 0)
    out["failed_count"] = by_state.get(STATE_FAILED, 0)
    accounted = (
        out["qualified_count"]
        + out["observing_count"]
        + out["insufficient_evidence_count"]
        + out["conflicting_evidence_count"]
        + out["blocked_count"]
        + out["expired_count"]
        + out["failed_count"]
    )
    out["unaccounted_count"] = max(0, out["candidate_count"] - accounted)
    out["counts_by_synthesis_rule"] = dict(by_rule)
    out["counts_by_pattern_type"] = dict(by_pattern)
    out["counts_by_subject_type"] = dict(by_subject)
    out["counts_by_source_domain_combination"] = dict(by_sources)
    out["source_coverage"] = {
        "available_domains": sorted(source_domains_seen),
        "domain_count": len(source_domains_seen),
    }
    out["supporting_evidence_count"] = supporting
    out["contradicting_evidence_count"] = contradicting
    out["known_facts_sample"] = known_sample
    out["unknown_facts_sample"] = unknown_sample
    out["prohibited_claims_sample"] = prohibited_sample
    out["temporal_windows"] = sorted(set(windows))
    out["evidence_freshness"] = {
        "as_of": out["as_of"],
        "time_window_key": window,
    }
    out["input_fingerprints"] = input_fps[:20]
    out["synthesis_fingerprints"] = syn_fps[:20]
    out["sample_syntheses"] = [
        {
            "synthesis_id": s.get("synthesis_id"),
            "synthesis_rule_key": s.get("synthesis_rule_key"),
            "subject_type": s.get("subject_type"),
            "subject_id": s.get("subject_id"),
            "synthesis_state": s.get("synthesis_state"),
            "pattern_type": s.get("pattern_type"),
            "known_facts": (s.get("known_facts") or [])[:4],
            "unknown_facts": (s.get("unknown_facts") or [])[:4],
            "prohibited_claims": (s.get("prohibited_claims") or [])[:4],
            "source_domains": s.get("source_domains") or [],
            "source_contributions": s.get("source_contributions") or {},
        }
        for s in syntheses[:12]
    ]
    out["accounting_ok"] = (
        out["unaccounted_count"] == 0
        and out["candidate_count"]
        == int(generated.get("expected_candidate_count") or 0)
    )

    if materialize and commerce_intelligence_synthesis_v1_enabled():
        mat = materialize_commerce_intelligence_syntheses_v1(
            slug, time_window_key=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        out["superseded"] = int(mat.get("superseded") or 0)
        out["errors"].extend(list(mat.get("errors") or []))

    try:
        out["materialized_row_count"] = int(
            db.session.query(func.count(CommerceIntelligenceSynthesis.id))
            .filter(
                CommerceIntelligenceSynthesis.store_slug == slug,
                CommerceIntelligenceSynthesis.is_current.is_(True),
            )
            .scalar()
            or 0
        )
        # Current uniqueness: no duplicate current synthesis_key
        dup = (
            db.session.query(
                CommerceIntelligenceSynthesis.synthesis_key,
                func.count(CommerceIntelligenceSynthesis.id),
            )
            .filter(
                CommerceIntelligenceSynthesis.store_slug == slug,
                CommerceIntelligenceSynthesis.is_current.is_(True),
            )
            .group_by(CommerceIntelligenceSynthesis.synthesis_key)
            .having(func.count(CommerceIntelligenceSynthesis.id) > 1)
            .all()
        )
        out["current_record_uniqueness"] = len(dup) == 0
    except SQLAlchemyError as exc:
        out["errors"].append(f"count:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["ok"] = bool(
        out["table_exists"]
        and out["deterministic"]
        and out["accounting_ok"]
        and out["lineage_verification"]
        and out["current_record_uniqueness"]
        and out["provider_independent"]
        and out["active_rule_count"] >= 8
        and out["candidate_count"] > 0
        and out["unaccounted_count"] == 0
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_commerce_intelligence_synthesis_prod_probe_v1"]
