# -*- coding: utf-8 -*-
"""Guidance Routing Foundation V1 — production probe (no merchant UI)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import GuidanceRoute
from schema_guidance_routing_v1 import ensure_guidance_routing_schema
from services.product_data.guidance_routing_flag_v1 import (
    ENV_GUIDANCE_ROUTING_V1,
    guidance_routing_v1_enabled,
)
from services.product_data.guidance_routing_foundation_v1 import (
    generate_guidance_routes_v1,
    materialize_guidance_routes_v1,
    verify_guidance_routing_determinism_v1,
)
from services.product_data.guidance_routing_types_v1 import (
    ROUTE_BLOCKED,
    ROUTE_DEFERRED,
    ROUTE_ELIGIBLE,
    ROUTE_EXPIRED,
    ROUTE_FAILED,
    ROUTE_INELIGIBLE,
    ROUTING_REGISTRY_VERSION_V1,
    SURFACE_REGISTRY_VERSION_V1,
)
from services.product_data.guidance_surface_registry_v1 import list_active_surfaces_v1

_ALLOWED_STORES = frozenset({"demo"})


def build_guidance_routing_prod_probe_v1(
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
        "foundation_enabled": guidance_routing_v1_enabled(),
        "flag_env": ENV_GUIDANCE_ROUTING_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "c2d3e4f5a6b7",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "routing_registry_version": ROUTING_REGISTRY_VERSION_V1,
        "active_surfaces": list_active_surfaces_v1(),
        "guidance_count": 0,
        "expected_route_pairs": 0,
        "eligible_route_count": 0,
        "ineligible_route_count": 0,
        "blocked_route_count": 0,
        "deferred_route_count": 0,
        "expired_route_count": 0,
        "failed_route_count": 0,
        "unaccounted_route_count": 0,
        "route_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "superseded": 0,
        "by_surface": {},
        "by_guidance_key": {},
        "sample_routes": [],
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "consumes_commercial_guidance_only": True,
        "accounting_ok": False,
        "no_home_presentation_fields": True,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_guidance_routing_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("guidance_routes"))
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
                out["alembic_stamped_exact"] = str(row[0]) == "c2d3e4f5a6b7"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_guidance_routing_determinism_v1(slug, assembly_window=window)
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

    generated = generate_guidance_routes_v1(
        slug, assembly_window=window, as_of=frozen
    )
    routes = list(generated.get("routes") or [])
    out["route_count"] = len(routes)
    out["guidance_count"] = int(generated.get("guidance_count") or 0)
    out["expected_route_pairs"] = int(generated.get("expected_route_pairs") or 0)

    counts = defaultdict(int)
    by_surface: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_key: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in routes:
        st = str(r.get("route_status") or "")
        counts[st] += 1
        by_surface[str(r.get("surface_key") or "")][st] += 1
        by_key[str(r.get("guidance_key") or "")][st] += 1
        blob = str(r)
        for banned in ("show_on_home", "home_card_title", "home_priority"):
            if banned in blob:
                out["no_home_presentation_fields"] = False

    out["eligible_route_count"] = counts[ROUTE_ELIGIBLE]
    out["ineligible_route_count"] = counts[ROUTE_INELIGIBLE]
    out["blocked_route_count"] = counts[ROUTE_BLOCKED]
    out["deferred_route_count"] = counts[ROUTE_DEFERRED]
    out["expired_route_count"] = counts[ROUTE_EXPIRED]
    out["failed_route_count"] = counts[ROUTE_FAILED]
    accounted = (
        out["eligible_route_count"]
        + out["ineligible_route_count"]
        + out["blocked_route_count"]
        + out["deferred_route_count"]
        + out["expired_route_count"]
        + out["failed_route_count"]
    )
    out["unaccounted_route_count"] = max(0, out["expected_route_pairs"] - accounted)
    out["accounting_ok"] = (
        out["expected_route_pairs"] > 0
        and accounted == out["expected_route_pairs"]
        and out["unaccounted_route_count"] == 0
    )
    out["by_surface"] = {k: dict(v) for k, v in by_surface.items()}
    out["by_guidance_key"] = {k: dict(v) for k, v in by_key.items()}

    # Prefer diverse samples: home eligible, decision eligible, carts, ineligible.
    samples = []
    wanted = [
        ("home", ROUTE_ELIGIBLE),
        ("decision_workspace", ROUTE_ELIGIBLE),
        ("carts", ROUTE_ELIGIBLE),
        ("settings", ROUTE_INELIGIBLE),
        ("communication", ROUTE_INELIGIBLE),
    ]
    used = set()
    for surface, status in wanted:
        for r in routes:
            rid = r.get("route_id")
            if rid in used:
                continue
            if r.get("surface_key") == surface and r.get("route_status") == status:
                samples.append(
                    {
                        "route_id": r.get("route_id"),
                        "guidance_id": r.get("guidance_id"),
                        "guidance_key": r.get("guidance_key"),
                        "surface_key": r.get("surface_key"),
                        "route_scope": r.get("route_scope"),
                        "route_role": r.get("route_role"),
                        "route_status": r.get("route_status"),
                        "routing_rationale_code": r.get("routing_rationale_code"),
                        "subject_type": r.get("subject_type"),
                        "input_fingerprint": r.get("input_fingerprint"),
                        "route_fingerprint": r.get("route_fingerprint"),
                    }
                )
                used.add(rid)
                break
    out["sample_routes"] = samples[:6]

    if materialize and guidance_routing_v1_enabled():
        mat = materialize_guidance_routes_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        out["superseded"] = int(mat.get("superseded") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(GuidanceRoute.id))
                .filter(GuidanceRoute.store_slug == slug)
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
        and out["accounting_ok"]
        and out["consumes_commercial_guidance_only"]
        and out["no_home_presentation_fields"]
        and out["route_count"] > 0
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_guidance_routing_prod_probe_v1"]
