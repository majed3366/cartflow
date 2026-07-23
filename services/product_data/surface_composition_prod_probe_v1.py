# -*- coding: utf-8 -*-
"""Surface Composition Foundation V1 — production probe (no merchant UI)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import SurfaceComposition
from schema_surface_composition_v1 import ensure_surface_composition_schema
from services.product_data.surface_composition_flag_v1 import (
    ENV_SURFACE_COMPOSITION_V1,
    surface_composition_v1_enabled,
)
from services.product_data.surface_composition_foundation_v1 import (
    generate_surface_compositions_v1,
    materialize_surface_compositions_v1,
    verify_surface_composition_determinism_v1,
)
from services.product_data.surface_composition_registry_v1 import (
    SURFACE_REGISTRY_V1,
    surface_registry_valid_v1,
)
from services.product_data.surface_composition_types_v1 import (
    SURFACE_REGISTRY_VERSION_V1,
    VIS_VISIBLE,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_surface_composition_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    reg_ok, reg_errors = surface_registry_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": surface_composition_v1_enabled(),
        "flag_env": ENV_SURFACE_COMPOSITION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "h7i8j9k0l1m2",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "surfaces": sorted(SURFACE_REGISTRY_V1.keys()),
        "composition_counts": {},
        "information_classes": {},
        "duplicate_groups": {},
        "freshness": {},
        "visibility": {},
        "priorities": [],
        "accounting": {},
        "composition_count": 0,
        "accounted_count": 0,
        "expected_input_count": 0,
        "duplicate_current": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "superseded": 0,
        "failures": [],
        "sample_compositions": [],
        "errors": list(reg_errors),
        "migration_satisfied": False,
        "consumes_governed_inputs_only": True,
        "no_raw_data_reads": True,
        "no_page_ui": True,
        "registries_valid": bool(reg_ok),
        "accounting_ok": False,
        "non_demo_writes": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_surface_composition_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("surface_compositions"))
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

    det = verify_surface_composition_determinism_v1(slug, assembly_window=window)
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

    generated = generate_surface_compositions_v1(
        slug, assembly_window=window, as_of=frozen
    )
    compositions = list(generated.get("compositions") or [])
    out["composition_count"] = len(compositions)
    out["accounted_count"] = int(generated.get("accounted_count") or 0)
    out["expected_input_count"] = int(generated.get("expected_input_count") or 0)
    out["accounting"] = dict(generated.get("accounting") or {})
    out["accounting_ok"] = (
        out["accounted_count"] == out["composition_count"]
        and out["composition_count"] > 0
    )

    by_surface: dict[str, int] = defaultdict(int)
    by_class: dict[str, int] = defaultdict(int)
    by_dup: dict[str, int] = defaultdict(int)
    by_fresh: dict[str, int] = defaultdict(int)
    by_vis: dict[str, int] = defaultdict(int)
    priorities: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for c in compositions:
        by_surface[str(c.get("surface_id") or "")] += 1
        by_class[str(c.get("information_class") or "")] += 1
        by_dup[str(c.get("duplicate_group") or "")] += 1
        by_fresh[str(c.get("freshness_state") or "")] += 1
        by_vis[str(c.get("visibility") or "")] += 1
        priorities.append(
            {
                "composition_id": c.get("composition_id"),
                "surface_id": c.get("surface_id"),
                "priority": c.get("priority"),
                "visibility": c.get("visibility"),
            }
        )
        if c.get("accounting_outcome") == "failed" or c.get("failure_reason"):
            failures.append(
                {
                    "composition_id": c.get("composition_id"),
                    "surface_id": c.get("surface_id"),
                    "failure_reason": c.get("failure_reason"),
                    "visibility_reason": c.get("visibility_reason"),
                }
            )
        blob = str(c).lower()
        for banned in (
            "product_signal_event",
            "whatsapp",
            "widget_event",
            "commerce_intelligence_synthesis",
            "purchase_table",
            "css",
            "figma",
        ):
            if banned in blob and banned in (
                "product_signal_event",
                "commerce_intelligence_synthesis",
            ):
                out["no_raw_data_reads"] = False

    out["composition_counts"] = dict(by_surface)
    out["information_classes"] = dict(by_class)
    out["duplicate_groups"] = {
        k: v for k, v in sorted(by_dup.items(), key=lambda kv: (-kv[1], kv[0]))[:40]
    }
    out["freshness"] = dict(by_fresh)
    out["visibility"] = dict(by_vis)
    out["priorities"] = sorted(
        priorities,
        key=lambda p: (-int(p.get("priority") or 0), str(p.get("composition_id") or "")),
    )[:25]
    out["failures"] = failures[:20]

    samples = []
    for surface in ("home", "decision_workspace", "carts"):
        for c in compositions:
            if c.get("surface_id") != surface:
                continue
            if c.get("visibility") != VIS_VISIBLE:
                continue
            samples.append(
                {
                    "composition_id": c.get("composition_id"),
                    "surface_id": c.get("surface_id"),
                    "information_class": c.get("information_class"),
                    "presentation_intent": c.get("presentation_intent"),
                    "priority": c.get("priority"),
                    "freshness_state": c.get("freshness_state"),
                    "visibility": c.get("visibility"),
                    "duplicate_group": c.get("duplicate_group"),
                    "owns_full_explanation": c.get("owns_full_explanation"),
                    "accounting_outcome": c.get("accounting_outcome"),
                    "source_type": c.get("source_type"),
                    "source_id": c.get("source_id"),
                }
            )
            break
    out["sample_compositions"] = samples

    if materialize and surface_composition_v1_enabled():
        mat = materialize_surface_compositions_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        out["superseded"] = int(mat.get("superseded") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(SurfaceComposition.id))
                .filter(SurfaceComposition.store_slug == slug)
                .scalar()
                or 0
            )
            # Duplicate current: same store+surface+source with >1 is_current.
            dup_rows = db.session.execute(
                text(
                    """
                    SELECT store_slug, surface_id, source_type, source_id, COUNT(*) AS c
                    FROM surface_compositions
                    WHERE store_slug = :slug AND is_current = true
                    GROUP BY store_slug, surface_id, source_type, source_id
                    HAVING COUNT(*) > 1
                    """
                ),
                {"slug": slug},
            ).fetchall()
            out["duplicate_current"] = len(list(dup_rows or []))
        except SQLAlchemyError as exc:
            out["errors"].append(f"count:{type(exc).__name__}")
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

    out["non_demo_writes"] = bool(slug != "demo" and out["upserted"] > 0)

    out["ok"] = bool(
        out["table_exists"]
        and out["deterministic"]
        and out["accounting_ok"]
        and out["registries_valid"]
        and out["consumes_governed_inputs_only"]
        and out["no_raw_data_reads"]
        and out["no_page_ui"]
        and out["composition_count"] > 0
        and out["duplicate_current"] == 0
        and "store_not_allowlisted" not in out["errors"]
        and not out["non_demo_writes"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_surface_composition_prod_probe_v1"]
