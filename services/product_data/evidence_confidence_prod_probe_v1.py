# -*- coding: utf-8 -*-
"""
Evidence Confidence Foundation V1 — production probe (no merchant UI).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import EvidenceConfidenceEvaluation
from schema_evidence_confidence_v1 import ensure_evidence_confidence_schema
from services.product_data.evidence_confidence_flag_v1 import (
    ENV_EVIDENCE_CONFIDENCE_V1,
    evidence_confidence_v1_enabled,
)
from services.product_data.evidence_confidence_foundation_v1 import (
    evaluate_evidence_confidence_v1,
    materialize_evidence_confidence_v1,
    verify_evidence_confidence_determinism_v1,
)
_ALLOWED_STORES = frozenset({"demo"})


def build_evidence_confidence_prod_probe_v1(
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
        "foundation_enabled": evidence_confidence_v1_enabled(),
        "flag_env": ENV_EVIDENCE_CONFIDENCE_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "y8z9a0b1c2d3",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "evaluation_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "sample_store_evaluation": None,
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "inputs_evidence_assembly_only": True,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_evidence_confidence_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("evidence_confidence_evaluations"))
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
                out["alembic_stamped_exact"] = str(row[0]) == "y8z9a0b1c2d3"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_evidence_confidence_determinism_v1(slug, assembly_window=window)
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
    evaluated = evaluate_evidence_confidence_v1(
        slug, assembly_window=window, as_of=frozen
    )
    store_evals = [
        e
        for e in (evaluated.get("evaluations") or [])
        if e.get("subject_type") == "store"
    ]
    if store_evals:
        e0 = store_evals[0]
        out["sample_store_evaluation"] = {
            "confidence_id": e0.get("confidence_id"),
            "evidence_bundle_id": e0.get("evidence_bundle_id"),
            "confidence_level": e0.get("confidence_level"),
            "confidence_score": e0.get("confidence_score"),
            "factors": e0.get("factors"),
            "missing_sources": e0.get("missing_sources"),
            "conflicting_signals": e0.get("conflicting_signals"),
            "confidence_notes": e0.get("confidence_notes"),
        }

    if materialize and evidence_confidence_v1_enabled():
        mat = materialize_evidence_confidence_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(EvidenceConfidenceEvaluation.id))
                .filter(EvidenceConfidenceEvaluation.store_slug == slug)
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
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_evidence_confidence_prod_probe_v1"]
