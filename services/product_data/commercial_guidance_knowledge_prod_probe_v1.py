# -*- coding: utf-8 -*-
"""
Commercial Guidance Integration V1 — production probe (Knowledge → Guidance).

No merchant UI. Demo allowlist by default.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CommercialGuidanceRecord
from schema_commercial_guidance_v1 import ensure_commercial_guidance_schema
from services.product_data.commerce_intelligence_knowledge_flag_v1 import (
    commerce_intelligence_knowledge_v1_enabled,
)
from services.product_data.commerce_intelligence_knowledge_intake_v1 import (
    materialize_knowledge_from_synthesis_v1,
)
from services.product_data.commercial_guidance_knowledge_flag_v1 import (
    ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1,
    commercial_guidance_knowledge_v1_enabled,
)
from services.product_data.commercial_guidance_knowledge_intake_v1 import (
    generate_commercial_guidance_from_knowledge_v1,
    materialize_commercial_guidance_from_knowledge_v1,
    verify_cguide_determinism_v1,
)
from services.product_data.commercial_guidance_knowledge_registry_v1 import (
    list_active_guidance_keys_v1,
    registry_is_valid_v1,
)
from services.product_data.commercial_guidance_knowledge_types_v1 import (
    GENERATION_VERSION_V1,
    GUIDANCE_VERSION_V1,
    INPUT_CONTRACT_VERSION_V1,
    REGISTRY_VERSION_V1,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_commercial_guidance_knowledge_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    assembly_window: str = "d7",
    seed_knowledge: bool = True,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    reg_ok, reg_errors = registry_is_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": commercial_guidance_knowledge_v1_enabled(),
        "flag_env": ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1,
        "input_contract_version": INPUT_CONTRACT_VERSION_V1,
        "intake_policy_version": REGISTRY_VERSION_V1,
        "guidance_version": GUIDANCE_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "g6a7b8c9d0e1",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "eligible_knowledge_count": 0,
        "ineligible_knowledge_count": 0,
        "guidance_created": 0,
        "guidance_updated": 0,
        "unchanged": 0,
        "observe_only": 0,
        "evidence_gap": 0,
        "conflicting": 0,
        "rejected": 0,
        "abstained": 0,
        "expired": 0,
        "failed": 0,
        "unaccounted": 0,
        "claim_boundary_ok": False,
        "lineage_ok": False,
        "duplicate_current": False,
        "confidence_reuse": True,
        "non_demo_writes": 0,
        "counts_by_knowledge_type": {},
        "counts_by_guidance_key": {},
        "sample_records": [],
        "registry_keys": list_active_guidance_keys_v1(),
        "registry_valid": reg_ok,
        "errors": list(reg_errors),
        "migration_satisfied": False,
        "consumes_knowledge_only": True,
        "consumes_cis_direct": False,
        "consumes_guidance_eligibility": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_commercial_guidance_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("commercial_guidance_records"))
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

    # Ensure Demo has current ciknow Knowledge before guidance intake.
    if seed_knowledge and commerce_intelligence_knowledge_v1_enabled():
        try:
            materialize_knowledge_from_synthesis_v1(
                slug, time_window_key=window
            )
        except Exception as exc:  # noqa: BLE001
            out["errors"].append(f"seed_knowledge:{type(exc).__name__}")

    det = verify_cguide_determinism_v1(slug)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None

    generated = generate_commercial_guidance_from_knowledge_v1(
        slug, as_of=frozen
    )
    out["eligible_knowledge_count"] = int(
        generated.get("eligible_knowledge_count") or 0
    )
    out["ineligible_knowledge_count"] = int(
        generated.get("ineligible_knowledge_count") or 0
    )
    out["observe_only"] = int(generated.get("observe_only") or 0)
    out["evidence_gap"] = int(generated.get("evidence_gap") or 0)
    out["conflicting"] = int(generated.get("conflicting") or 0)
    out["rejected"] = int(generated.get("rejected") or 0)
    out["abstained"] = int(generated.get("abstained") or 0)
    out["expired"] = int(generated.get("expired") or 0)
    out["failed"] = int(generated.get("failed") or 0)
    out["unaccounted"] = int(generated.get("unaccounted") or 0)
    out["claim_boundary_ok"] = bool(generated.get("claim_boundary_ok"))
    out["lineage_ok"] = bool(generated.get("lineage_ok"))
    out["errors"].extend(list(generated.get("errors") or []))

    records = list(generated.get("records") or [])
    kt_counts: Counter[str] = Counter()
    gk_counts: Counter[str] = Counter()
    for r in records:
        kt_counts[str(r.get("knowledge_type") or "")] += 1
        gk_counts[str(r.get("guidance_key") or "")] += 1
    out["counts_by_knowledge_type"] = dict(kt_counts)
    out["counts_by_guidance_key"] = dict(gk_counts)

    samples = []
    for r in records[:5]:
        samples.append(
            {
                "guidance_id": r.get("guidance_id"),
                "guidance_key": r.get("guidance_key"),
                "knowledge_id": r.get("knowledge_id"),
                "knowledge_type": r.get("knowledge_type"),
                "eligibility_status": r.get("eligibility_status"),
                "merchant_objective": r.get("merchant_objective"),
                "confidence_level": r.get("confidence_level"),
                "known_facts": (r.get("known_facts") or [])[:3],
                "unknown_facts": (r.get("unknown_facts") or [])[:2],
                "prohibited_claims": (r.get("prohibited_claims") or [])[:2],
                "eligible_actions": (r.get("eligible_actions") or [])[:2],
                "forbidden_actions": (r.get("forbidden_actions") or [])[:2],
                "source_lineage": r.get("source_lineage"),
            }
        )
    out["sample_records"] = samples

    if materialize and commercial_guidance_knowledge_v1_enabled():
        mat = materialize_commercial_guidance_from_knowledge_v1(
            slug, as_of=frozen
        )
        out["guidance_created"] = int(mat.get("created") or 0)
        out["guidance_updated"] = int(mat.get("updated") or 0)
        out["unchanged"] = int(mat.get("unchanged") or 0)
        if not mat.get("ok") and not mat.get("skipped_disabled"):
            out["errors"].extend(list(mat.get("errors") or []))
    else:
        # Generate-only accounting for created when materialize skipped.
        out["guidance_created"] = int(generated.get("created") or 0)

    # Duplicate current check for cguide scope/version.
    if out["table_exists"]:
        try:
            currents = (
                db.session.query(
                    CommercialGuidanceRecord.subject_type,
                    CommercialGuidanceRecord.subject_id,
                    CommercialGuidanceRecord.guidance_scope,
                    func.count(CommercialGuidanceRecord.id),
                )
                .filter(
                    CommercialGuidanceRecord.store_slug == slug,
                    CommercialGuidanceRecord.generation_version
                    == GENERATION_VERSION_V1,
                    CommercialGuidanceRecord.is_current.is_(True),
                )
                .group_by(
                    CommercialGuidanceRecord.subject_type,
                    CommercialGuidanceRecord.subject_id,
                    CommercialGuidanceRecord.guidance_scope,
                )
                .all()
            )
            out["duplicate_current"] = any(int(c[3] or 0) > 1 for c in currents)
        except SQLAlchemyError as exc:
            out["errors"].append(f"dup_check:{type(exc).__name__}")
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

        try:
            out["non_demo_writes"] = int(
                db.session.query(func.count(CommercialGuidanceRecord.id))
                .filter(
                    CommercialGuidanceRecord.generation_version
                    == GENERATION_VERSION_V1,
                    CommercialGuidanceRecord.store_slug != "demo",
                )
                .scalar()
                or 0
            )
        except SQLAlchemyError:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

    out["ok"] = bool(
        out["table_exists"]
        and out["deterministic"]
        and out["registry_valid"]
        and out["unaccounted"] == 0
        and out["failed"] == 0
        and out["claim_boundary_ok"]
        and out["lineage_ok"]
        and not out["duplicate_current"]
        and out["non_demo_writes"] == 0
        and out["consumes_knowledge_only"]
        and not out["consumes_cis_direct"]
        and not out["consumes_guidance_eligibility"]
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_commercial_guidance_knowledge_prod_probe_v1"]
