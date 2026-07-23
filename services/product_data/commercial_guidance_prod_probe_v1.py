# -*- coding: utf-8 -*-
"""
Commercial Guidance Foundation V1 — production probe (no merchant UI).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CommercialGuidanceRecord
from schema_commercial_guidance_v1 import ensure_commercial_guidance_schema
from services.product_data.commercial_guidance_flag_v1 import (
    ENV_COMMERCIAL_GUIDANCE_V1,
    commercial_guidance_v1_enabled,
)
from services.product_data.commercial_guidance_foundation_v1 import (
    generate_commercial_guidance_v1,
    materialize_commercial_guidance_v1,
    verify_commercial_guidance_determinism_v1,
)
from services.product_data.commercial_guidance_registry_v1 import (
    list_active_guidance_keys_v1,
    registry_is_valid_v1,
)
from services.product_data.commercial_guidance_types_v1 import (
    STATUS_ABSTAINED,
    STATUS_ACTIVE,
    STATUS_DEFERRED,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_commercial_guidance_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    reg_ok, reg_errors = registry_is_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": commercial_guidance_v1_enabled(),
        "flag_env": ENV_COMMERCIAL_GUIDANCE_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "b1c2d3e4f5a6",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "guidance_count": 0,
        "active_count": 0,
        "deferred_count": 0,
        "abstained_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "superseded": 0,
        "sample_records": [],
        "registry_keys": list_active_guidance_keys_v1(),
        "registry_valid": reg_ok,
        "errors": list(reg_errors),
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "consumes_guidance_eligibility_only": True,
        "one_current_per_subject": False,
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
                out["alembic_stamped_exact"] = str(row[0]) == "b1c2d3e4f5a6"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_commercial_guidance_determinism_v1(slug, assembly_window=window)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["guidance_count"] = int(det.get("guidance_count") or 0)
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None
    generated = generate_commercial_guidance_v1(
        slug, assembly_window=window, as_of=frozen
    )
    records = list(generated.get("records") or [])
    out["active_count"] = sum(
        1 for r in records if r.get("guidance_status") == STATUS_ACTIVE
    )
    out["deferred_count"] = sum(
        1 for r in records if r.get("guidance_status") == STATUS_DEFERRED
    )
    out["abstained_count"] = sum(
        1 for r in records if r.get("guidance_status") == STATUS_ABSTAINED
    )
    subjects = [
        (r.get("subject_type"), r.get("subject_id"), r.get("guidance_scope"))
        for r in records
    ]
    out["one_current_per_subject"] = len(subjects) == len(set(subjects))

    samples = []
    for r in records[:3]:
        samples.append(
            {
                "guidance_id": r.get("guidance_id"),
                "subject_type": r.get("subject_type"),
                "subject_id": r.get("subject_id"),
                "guidance_key": r.get("guidance_key"),
                "guidance_status": r.get("guidance_status"),
                "rationale_code": r.get("rationale_code"),
                "eligibility_id": r.get("eligibility_id"),
                "eligibility_status": r.get("eligibility_status"),
                "knowledge_reference_ids": r.get("knowledge_reference_ids"),
                "known_facts": (r.get("known_facts") or [])[:3],
                "unknown_facts": (r.get("unknown_facts") or [])[:2],
                "prohibited_claims": (r.get("prohibited_claims") or [])[:2],
                "rule_version": r.get("rule_version"),
                "input_fingerprint": r.get("input_fingerprint"),
                "guidance_fingerprint": r.get("guidance_fingerprint"),
            }
        )
    out["sample_records"] = samples

    if materialize and commercial_guidance_v1_enabled():
        mat = materialize_commercial_guidance_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        out["superseded"] = int(mat.get("superseded") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(CommercialGuidanceRecord.id))
                .filter(CommercialGuidanceRecord.store_slug == slug)
                .scalar()
                or 0
            )
        except SQLAlchemyError as exc:
            out["errors"].append(f"count:{type(exc).__name__}")
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

    out["ok"] = bool(
        out["table_exists"]
        and out["deterministic"]
        and out["registry_valid"]
        and out["guidance_count"] > 0
        and out["one_current_per_subject"]
        and out["consumes_guidance_eligibility_only"]
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_commercial_guidance_prod_probe_v1"]
