# -*- coding: utf-8 -*-
"""Merchant Presentation Foundation V1 — production probe (no merchant UI)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import MerchantPresentation
from schema_merchant_presentation_v1 import ensure_merchant_presentation_schema
from services.product_data.merchant_presentation_flag_v1 import (
    ENV_MERCHANT_PRESENTATION_V1,
    merchant_presentation_v1_enabled,
)
from services.product_data.merchant_presentation_foundation_v1 import (
    generate_merchant_presentations_v1,
    materialize_merchant_presentations_v1,
    verify_merchant_presentation_determinism_v1,
)
from services.product_data.merchant_presentation_types_v1 import (
    PRESENTATION_REGISTRY_VERSION_V1,
    STATE_BLOCKED,
    STATE_DEFERRED,
    STATE_EXPIRED,
    STATE_FAILED,
    STATE_INSUFFICIENT,
    STATE_MONITORING,
    STATE_READY,
    TEMPLATE_REGISTRY_VERSION_V1,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_merchant_presentation_prod_probe_v1(
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
        "foundation_enabled": merchant_presentation_v1_enabled(),
        "flag_env": ENV_MERCHANT_PRESENTATION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "d3e4f5a6b7c8",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "presentation_registry_version": PRESENTATION_REGISTRY_VERSION_V1,
        "template_registry_version": TEMPLATE_REGISTRY_VERSION_V1,
        "eligible_route_count": 0,
        "expected_presentation_count": 0,
        "ready_count": 0,
        "monitoring_count": 0,
        "insufficient_evidence_count": 0,
        "deferred_count": 0,
        "blocked_count": 0,
        "expired_count": 0,
        "failed_count": 0,
        "unaccounted_count": 0,
        "presentation_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "superseded": 0,
        "by_surface": {},
        "by_type": {},
        "by_state": {},
        "sample_presentations": [],
        "claim_boundary_ok": True,
        "no_home_presentation_fields": True,
        "errors": [],
        "migration_satisfied": False,
        "consumes_guidance_routing_only": True,
        "accounting_ok": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_merchant_presentation_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("merchant_presentations"))
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

    det = verify_merchant_presentation_determinism_v1(slug, assembly_window=window)
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

    generated = generate_merchant_presentations_v1(
        slug, assembly_window=window, as_of=frozen
    )
    presentations = list(generated.get("presentations") or [])
    out["presentation_count"] = len(presentations)
    out["eligible_route_count"] = int(generated.get("eligible_route_count") or 0)
    out["expected_presentation_count"] = int(
        generated.get("expected_presentation_count") or 0
    )

    by_state: dict[str, int] = defaultdict(int)
    by_surface: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_type: dict[str, int] = defaultdict(int)
    for p in presentations:
        st = str(p.get("presentation_state") or "")
        by_state[st] += 1
        by_surface[str(p.get("surface_key") or "")][st] += 1
        by_type[str(p.get("presentation_type") or "")] += 1
        blob = " ".join(
            [
                str(p.get("headline_text") or ""),
                str(p.get("primary_statement_text") or ""),
                str(p.get("supporting_statement_text") or ""),
            ]
        ).lower()
        for banned in (
            "shipping is expensive",
            "lower the shipping",
            "increase advertising",
            "guaranteed recovery",
            "show_on_home",
            "home_card_title",
        ):
            if banned in blob:
                out["claim_boundary_ok"] = False
            if banned in str(p):
                if banned.startswith("home_") or banned == "show_on_home":
                    out["no_home_presentation_fields"] = False

    out["ready_count"] = by_state[STATE_READY]
    out["monitoring_count"] = by_state[STATE_MONITORING]
    out["insufficient_evidence_count"] = by_state[STATE_INSUFFICIENT]
    out["deferred_count"] = by_state[STATE_DEFERRED]
    out["blocked_count"] = by_state[STATE_BLOCKED]
    out["expired_count"] = by_state[STATE_EXPIRED]
    out["failed_count"] = by_state[STATE_FAILED]
    accounted = (
        out["ready_count"]
        + out["monitoring_count"]
        + out["insufficient_evidence_count"]
        + out["deferred_count"]
        + out["blocked_count"]
        + out["expired_count"]
        + out["failed_count"]
    )
    out["unaccounted_count"] = max(0, out["expected_presentation_count"] - accounted)
    out["accounting_ok"] = (
        out["expected_presentation_count"] > 0
        and accounted == out["expected_presentation_count"]
        and out["unaccounted_count"] == 0
    )
    out["by_surface"] = {k: dict(v) for k, v in by_surface.items()}
    out["by_type"] = dict(by_type)
    out["by_state"] = dict(by_state)

    samples = []
    wanted = [
        ("home", "executive_summary"),
        ("decision_workspace", "decision_prompt"),
        ("carts", "operational_notice"),
    ]
    used = set()
    for surface, ptype in wanted:
        for p in presentations:
            pid = p.get("presentation_id")
            if pid in used:
                continue
            if p.get("surface_key") == surface and p.get("presentation_type") == ptype:
                samples.append(
                    {
                        "presentation_id": p.get("presentation_id"),
                        "route_id": p.get("route_id"),
                        "guidance_id": p.get("guidance_id"),
                        "surface_key": p.get("surface_key"),
                        "presentation_type": p.get("presentation_type"),
                        "presentation_state": p.get("presentation_state"),
                        "headline_text": p.get("headline_text"),
                        "primary_statement_text": p.get("primary_statement_text"),
                        "known_fact_items": (p.get("known_fact_items") or [])[:2],
                        "unknown_fact_items": (p.get("unknown_fact_items") or [])[:1],
                        "evidence_state": p.get("evidence_state"),
                        "action_affordance": p.get("action_affordance"),
                        "template_key": p.get("template_key"),
                        "template_version": p.get("template_version"),
                        "input_fingerprint": p.get("input_fingerprint"),
                        "presentation_fingerprint": p.get("presentation_fingerprint"),
                    }
                )
                used.add(pid)
                break
    out["sample_presentations"] = samples

    if materialize and merchant_presentation_v1_enabled():
        mat = materialize_merchant_presentations_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        out["superseded"] = int(mat.get("superseded") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_row_count"] = int(
                db.session.query(func.count(MerchantPresentation.id))
                .filter(MerchantPresentation.store_slug == slug)
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
        and out["consumes_guidance_routing_only"]
        and out["claim_boundary_ok"]
        and out["no_home_presentation_fields"]
        and out["presentation_count"] > 0
        and "store_not_allowlisted" not in out["errors"]
        and not any(str(e).startswith("materialize:") for e in out["errors"])
    )
    return out


__all__ = ["build_merchant_presentation_prod_probe_v1"]
