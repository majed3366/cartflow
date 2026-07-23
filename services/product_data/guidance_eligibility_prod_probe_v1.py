# -*- coding: utf-8 -*-
"""
Guidance Eligibility Foundation V1 — production probe (no merchant UI).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import GuidanceEligibilityEvaluation
from schema_guidance_eligibility_v1 import ensure_guidance_eligibility_schema
from services.product_data.guidance_eligibility_flag_v1 import (
    ENV_GUIDANCE_ELIGIBILITY_V1,
    guidance_eligibility_v1_enabled,
)
from services.product_data.guidance_eligibility_foundation_v1 import (
    evaluate_guidance_eligibility_v1,
    materialize_guidance_eligibility_v1,
    verify_guidance_eligibility_determinism_v1,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_guidance_eligibility_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": guidance_eligibility_v1_enabled(),
        "flag_env": ENV_GUIDANCE_ELIGIBILITY_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "a0b1c2d3e4f5",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "evaluation_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "sample_store_evaluation": None,
        "by_status": {},
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "inputs_knowledge_foundation_only": True,
        "one_status_per_subject": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_guidance_eligibility_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("guidance_eligibility_evaluations"))
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
                out["alembic_stamped_exact"] = str(row[0]) == "a0b1c2d3e4f5"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_guidance_eligibility_determinism_v1(slug, assembly_window=window)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["evaluation_count"] = int(det.get("evaluation_count") or 0)
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None
    evaluated = evaluate_guidance_eligibility_v1(
        slug, assembly_window=window, as_of=frozen
    )
    evaluations = list(evaluated.get("evaluations") or [])
    subjects = [
        (e.get("subject_type"), e.get("subject_id")) for e in evaluations
    ]
    out["one_status_per_subject"] = len(subjects) == len(set(subjects))
    by_status: dict[str, int] = {}
    for e in evaluations:
        st = str(e.get("eligibility_status") or "")
        by_status[st] = by_status.get(st, 0) + 1
    out["by_status"] = by_status
    store_evals = [e for e in evaluations if e.get("subject_type") == "store"]
    if store_evals:
        e0 = store_evals[0]
        out["sample_store_evaluation"] = {
            "eligibility_id": e0.get("eligibility_id"),
            "eligibility_status": e0.get("eligibility_status"),
            "eligibility_reason": e0.get("eligibility_reason"),
            "knowledge_count": e0.get("knowledge_count"),
            "required_knowledge_count": e0.get("required_knowledge_count"),
            "blocking_conditions": e0.get("blocking_conditions"),
        }

    if materialize and guidance_eligibility_v1_enabled():
        mat = materialize_guidance_eligibility_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(GuidanceEligibilityEvaluation.id))
                .filter(GuidanceEligibilityEvaluation.store_slug == slug)
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
        and out["evaluation_count"] > 0
        and out["one_status_per_subject"]
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_guidance_eligibility_prod_probe_v1"]
