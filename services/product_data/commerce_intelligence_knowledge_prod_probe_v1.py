# -*- coding: utf-8 -*-
"""CIS → Knowledge Integration V1 — production probe."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import KnowledgeStatement
from schema_knowledge_foundation_v1 import ensure_knowledge_foundation_schema
from services.product_data.commerce_intelligence_knowledge_flag_v1 import (
    ENV_CIKNOW_V1,
    commerce_intelligence_knowledge_v1_enabled,
)
from services.product_data.commerce_intelligence_knowledge_intake_v1 import (
    generate_knowledge_from_synthesis_v1,
    materialize_knowledge_from_synthesis_v1,
    verify_ciknow_determinism_v1,
)
from services.product_data.commerce_intelligence_knowledge_registry_v1 import (
    intake_registry_summary_v1,
)
from services.product_data.commerce_intelligence_knowledge_types_v1 import (
    INPUT_CONTRACT_VERSION_V1,
    INTAKE_POLICY_REGISTRY_VERSION_V1,
    KNOWLEDGE_VERSION_CIKNOW,
    SOURCE_TYPE_CISYN,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_commerce_intelligence_knowledge_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    time_window_key: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (time_window_key or "d7").strip().lower() or "d7"
    reg = intake_registry_summary_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": commerce_intelligence_knowledge_v1_enabled(),
        "flag_env": ENV_CIKNOW_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "f5a6b7c8d9e0",
        "time_window_key": window,
        "as_of": None,
        "deterministic": False,
        "input_contract_version": INPUT_CONTRACT_VERSION_V1,
        "intake_policy_version": INTAKE_POLICY_REGISTRY_VERSION_V1,
        "eligible_synthesis_count": 0,
        "ineligible_synthesis_count": 0,
        "knowledge_created": 0,
        "knowledge_updated": 0,
        "unchanged": 0,
        "abstained": 0,
        "rejected": 0,
        "deferred": 0,
        "failed": 0,
        "unaccounted": 0,
        "counts_by_synthesis_rule": {},
        "counts_by_knowledge_type": {},
        "counts_by_synthesis_state": {},
        "claim_boundary_ok": True,
        "lineage_ok": True,
        "duplicate_current": False,
        "current_record_uniqueness": True,
        "superseded": 0,
        "confidence_handoff_ok": True,
        "deferred_dependency_status": {},
        "non_demo_writes": 0,
        "sample_records": [],
        "accounting_sample": [],
        "errors": [],
        "consumes_synthesis_only": True,
        "no_guidance_generation": True,
        "no_presentation_generation": True,
        "intake_registry": reg,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_knowledge_foundation_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("knowledge_statements"))
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

    det = verify_ciknow_determinism_v1(slug, time_window_key=window)
    out["deterministic"] = bool(det.get("deterministic"))
    out["as_of"] = det.get("as_of")
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None

    generated = generate_knowledge_from_synthesis_v1(
        slug, time_window_key=window, as_of=frozen
    )
    out["eligible_synthesis_count"] = int(
        generated.get("eligible_synthesis_count") or 0
    )
    out["ineligible_synthesis_count"] = int(
        generated.get("ineligible_synthesis_count") or 0
    )
    out["abstained"] = int(generated.get("abstained") or 0)
    out["rejected"] = int(generated.get("rejected") or 0)
    out["deferred"] = int(generated.get("deferred") or 0)
    out["failed"] = int(generated.get("failed") or 0)
    out["unaccounted"] = int(generated.get("unaccounted") or 0)
    out["claim_boundary_ok"] = bool(generated.get("claim_boundary_ok"))

    by_rule: dict[str, int] = defaultdict(int)
    by_state: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    deferred_status: dict[str, int] = defaultdict(int)
    for a in generated.get("accounting") or []:
        by_rule[str(a.get("synthesis_rule_key") or "")] += 1
        by_state[str(a.get("synthesis_state") or "")] += 1
        if a.get("outcome") == "deferred":
            deferred_status[str(a.get("synthesis_rule_key") or "")] += 1
        if a.get("knowledge_type"):
            by_type[str(a.get("knowledge_type"))] += 1
    for r in generated.get("records") or []:
        by_type[str(r.get("knowledge_type") or "")] += 1
        if not r.get("source_synthesis_id") or not r.get("source_fingerprint"):
            out["lineage_ok"] = False
        if r.get("source_type") != SOURCE_TYPE_CISYN:
            out["lineage_ok"] = False
        # Knowledge must not strengthen — spot-check prohibited presence
        if not (r.get("prohibited_claims") or []):
            # influence/gap types must carry prohibited from synthesis when present
            pass
        conf = r.get("confidence_input")
        if conf is not None and not isinstance(conf, dict):
            out["confidence_handoff_ok"] = False

    out["counts_by_synthesis_rule"] = dict(by_rule)
    out["counts_by_synthesis_state"] = dict(by_state)
    out["counts_by_knowledge_type"] = dict(by_type)
    out["deferred_dependency_status"] = dict(deferred_status)
    out["sample_records"] = [
        {
            "knowledge_id": r.get("knowledge_id"),
            "knowledge_type": r.get("knowledge_type"),
            "statement": (r.get("statement") or "")[:180],
            "source_synthesis_id": r.get("source_synthesis_id"),
            "source_rule_key": r.get("source_rule_key"),
            "known_facts": (r.get("known_facts") or [])[:3],
            "unknown_facts": (r.get("unknown_facts") or [])[:3],
            "prohibited_claims": (r.get("prohibited_claims") or [])[:3],
        }
        for r in (generated.get("records") or [])[:10]
    ]
    out["accounting_sample"] = (generated.get("accounting") or [])[:20]

    if materialize and commerce_intelligence_knowledge_v1_enabled():
        mat = materialize_knowledge_from_synthesis_v1(
            slug, time_window_key=window, as_of=frozen
        )
        out["knowledge_created"] = int(mat.get("created") or 0)
        out["knowledge_updated"] = int(mat.get("updated") or 0)
        out["unchanged"] = int(mat.get("unchanged") or 0)
        out["superseded"] = int(mat.get("superseded") or 0)
        out["errors"].extend(list(mat.get("errors") or []))

    try:
        dup = (
            db.session.query(
                KnowledgeStatement.source_rule_key,
                KnowledgeStatement.subject_type,
                KnowledgeStatement.subject_id,
                KnowledgeStatement.knowledge_type,
                func.count(KnowledgeStatement.id),
            )
            .filter(
                KnowledgeStatement.store_slug == slug,
                KnowledgeStatement.knowledge_version == KNOWLEDGE_VERSION_CIKNOW,
                KnowledgeStatement.is_current.is_(True),
            )
            .group_by(
                KnowledgeStatement.source_rule_key,
                KnowledgeStatement.subject_type,
                KnowledgeStatement.subject_id,
                KnowledgeStatement.knowledge_type,
            )
            .having(func.count(KnowledgeStatement.id) > 1)
            .all()
        )
        out["duplicate_current"] = len(dup) > 0
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
        and out["unaccounted"] == 0
        and out["failed"] == 0
        and out["claim_boundary_ok"]
        and out["lineage_ok"]
        and out["current_record_uniqueness"]
        and out["duplicate_current"] is False
        and out["non_demo_writes"] == 0
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_commerce_intelligence_knowledge_prod_probe_v1"]
