# -*- coding: utf-8 -*-
"""
Knowledge Foundation V1 — production probe (no merchant UI).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import KnowledgeStatement
from schema_knowledge_foundation_v1 import ensure_knowledge_foundation_schema
from services.product_data.knowledge_foundation_flag_v1 import (
    ENV_KNOWLEDGE_FOUNDATION_V1,
    knowledge_foundation_v1_enabled,
)
from services.product_data.knowledge_foundation_v1 import (
    generate_knowledge_v1,
    materialize_knowledge_v1,
    verify_knowledge_determinism_v1,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_knowledge_foundation_prod_probe_v1(
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
        "foundation_enabled": knowledge_foundation_v1_enabled(),
        "flag_env": ENV_KNOWLEDGE_FOUNDATION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "z9a0b1c2d3e4",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "statement_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "sample_statements": [],
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "inputs_evidence_confidence_only": True,
        "all_statements_reference_confidence": False,
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
                out["alembic_stamped_exact"] = str(row[0]) == "z9a0b1c2d3e4"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_knowledge_determinism_v1(slug, assembly_window=window)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["statement_count"] = int(det.get("statement_count") or 0)
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None
    generated = generate_knowledge_v1(slug, assembly_window=window, as_of=frozen)
    statements = list(generated.get("statements") or [])
    out["all_statements_reference_confidence"] = bool(
        statements
        and all(str(s.get("evidence_confidence_id") or "") for s in statements)
    )
    out["sample_statements"] = [
        {
            "knowledge_type": s.get("knowledge_type"),
            "statement": s.get("statement"),
            "confidence_level": s.get("confidence_level"),
            "evidence_confidence_id": s.get("evidence_confidence_id"),
        }
        for s in statements
        if s.get("subject_type") == "store"
    ][:12]

    if materialize and knowledge_foundation_v1_enabled():
        mat = materialize_knowledge_v1(slug, assembly_window=window, as_of=frozen)
        out["upserted"] = int(mat.get("upserted") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(KnowledgeStatement.id))
                .filter(KnowledgeStatement.store_slug == slug)
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
        and out["statement_count"] > 0
        and out["all_statements_reference_confidence"]
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_knowledge_foundation_prod_probe_v1"]
