# -*- coding: utf-8 -*-
"""
Guidance Routing Foundation V1 — surface eligibility from Commercial Guidance only.

No presentation, UI, wording, or automatic actions.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import GuidanceRoute
from schema_guidance_routing_v1 import ensure_guidance_routing_schema
from services.product_data.commercial_guidance_foundation_v1 import (
    generate_commercial_guidance_v1,
)
from services.product_data.commercial_guidance_types_v1 import KEY_DEFER, KEY_NO_GUIDANCE
from services.product_data.guidance_routing_flag_v1 import guidance_routing_v1_enabled
from services.product_data.guidance_routing_registry_v1 import (
    matching_rules_for_surface_v1,
    routing_registry_valid_v1,
)
from services.product_data.guidance_routing_types_v1 import (
    EVALUATOR_VERSION_V1,
    ROLE_SUPPRESSED,
    ROUTE_BLOCKED,
    ROUTE_DEFERRED,
    ROUTE_ELIGIBLE,
    ROUTE_EXPIRED,
    ROUTE_FAILED,
    ROUTE_INELIGIBLE,
    ROUTE_SUPERSEDED,
    ROUTING_REGISTRY_VERSION_V1,
    ROUTING_VERSION_V1,
    SCOPE_INTERNAL,
    SOURCE_CONTRACT_VERSION_V1,
    SURFACE_REGISTRY_VERSION_V1,
    SURFACES_V1,
)
from services.product_data.guidance_surface_registry_v1 import (
    get_surface_v1,
    list_active_surfaces_v1,
    surface_registry_valid_v1,
)

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _as_of_key(dt: datetime) -> str:
    return _floor_second(dt).strftime("%Y%m%d%H%M%S")


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _floor_second(value)
    try:
        return _floor_second(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def evaluate_guidance_surface_route_v1(
    *,
    guidance: dict[str, Any],
    surface_key: str,
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    """One route for one guidance × surface pair."""
    g_key = str(guidance.get("guidance_key") or "")
    g_status = str(guidance.get("guidance_status") or "")
    subject_type = str(guidance.get("subject_type") or "")
    ctx = dict(guidance.get("routing_context") or {})
    cart_related = bool(ctx.get("cart_related"))
    if not cart_related:
        cart_related = subject_type in {"cart", "product"}

    surface = get_surface_v1(surface_key)
    valid_until = _parse_iso(guidance.get("valid_until")) or as_of
    guidance_expired = valid_until < as_of or g_status == "expired"

    route_scope = SCOPE_INTERNAL
    route_role = ROLE_SUPPRESSED
    rule_version = ""
    rationale = "ineligible:no_matching_rule"

    if surface is None:
        route_status = ROUTE_FAILED
        rationale = "failed:unsupported_surface"
    elif guidance_expired:
        route_status = ROUTE_EXPIRED
        rationale = "expired:source_guidance"
    else:
        matches = matching_rules_for_surface_v1(
            guidance_key=g_key,
            guidance_status=g_status,
            subject_type=subject_type,
            surface_key=surface_key,
            cart_related=cart_related,
        )
        if matches:
            rule = matches[0]
            route_scope = str(rule.get("route_scope") or SCOPE_INTERNAL)
            route_role = str(rule.get("route_role") or ROLE_SUPPRESSED)
            rule_version = str(rule.get("rule_version") or "")
            if g_key == KEY_NO_GUIDANCE:
                route_status = ROUTE_BLOCKED
                rationale = f"blocked:{rule.get('rule_key')}"
            elif g_key == KEY_DEFER or g_status == "deferred":
                route_status = ROUTE_DEFERRED
                rationale = f"deferred:{rule.get('rule_key')}"
            else:
                route_status = ROUTE_ELIGIBLE
                rationale = f"eligible:{rule.get('rule_key')}"
        else:
            route_status = ROUTE_INELIGIBLE
            rationale = f"ineligible:surface_responsibility:{surface_key}"

    digest = _sha(
        {
            "guidance_id": guidance.get("guidance_id"),
            "guidance_key": g_key,
            "guidance_status": g_status,
            "subject_type": subject_type,
            "cart_related": cart_related,
            "surface": surface_key,
            "routing_context": ctx,
        }
    )
    input_fingerprint = _sha(
        {
            "guidance_id": guidance.get("guidance_id"),
            "guidance_fingerprint": guidance.get("guidance_fingerprint"),
            "routing_context": ctx,
            "surface": surface_key,
            "as_of": _as_of_key(as_of),
        }
    )
    route_id = _sha(
        {
            "v": ROUTING_VERSION_V1,
            "eval": EVALUATOR_VERSION_V1,
            "guidance_id": guidance.get("guidance_id"),
            "surface": surface_key,
            "as_of": _as_of_key(as_of),
            "status": route_status,
            "scope": route_scope,
            "role": route_role,
            "input": input_fingerprint,
        }
    )[:32]

    # Presentation-safe digest for Merchant Presentation (no UI fields).
    known = list(guidance.get("known_facts") or [])
    unknown = list(guidance.get("unknown_facts") or [])
    prohibited = list(guidance.get("prohibited_claims") or [])
    if g_key == KEY_NO_GUIDANCE or g_status == "abstained":
        evidence_state = "insufficient_evidence"
    elif g_key == KEY_DEFER or g_status == "deferred":
        evidence_state = "continued_observation"
    elif g_key in {"verify_evidence_gap"}:
        evidence_state = "limited_evidence"
    elif g_key in {"monitor_new_pattern", "continue_observing"}:
        evidence_state = "continued_observation"
    else:
        evidence_state = "sufficient_evidence"

    record = {
        "route_id": route_id,
        "guidance_id": str(guidance.get("guidance_id") or ""),
        "store_slug": str(guidance.get("store_slug") or ""),
        "subject_type": subject_type,
        "subject_id": str(guidance.get("subject_id") or ""),
        "surface_key": surface_key,
        "guidance_key": g_key,
        "route_scope": route_scope,
        "route_role": route_role,
        "route_status": route_status,
        "routing_rationale_code": rationale,
        "routing_context_digest": digest,
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "is_current": True,
        "routing_version": ROUTING_VERSION_V1,
        "routing_rule_version": rule_version or EVALUATOR_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "routing_registry_version": ROUTING_REGISTRY_VERSION_V1,
        "source_contract_version": str(
            (ctx.get("contract_version") if ctx else None)
            or SOURCE_CONTRACT_VERSION_V1
        ),
        "input_fingerprint": input_fingerprint,
        "generation_version": EVALUATOR_VERSION_V1,
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "presentation_context": {
            "contract_version": "grf_v1_presentation_context",
            "guidance_key": g_key,
            "guidance_status": g_status,
            "known_facts": known,
            "unknown_facts": unknown,
            "prohibited_claims": prohibited,
            "evidence_state": evidence_state,
            "subject_type": subject_type,
        },
    }
    record["route_fingerprint"] = _sha(
        {k: v for k, v in record.items() if k != "route_fingerprint"}
    )
    return record


def generate_guidance_routes_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate routes exclusively via Commercial Guidance API."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    surf_ok, surf_errors = surface_registry_valid_v1()
    rule_ok, rule_errors = routing_registry_valid_v1()
    surfaces = list_active_surfaces_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "routing_version": ROUTING_VERSION_V1,
        "evaluator_version": EVALUATOR_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "routing_registry_version": ROUTING_REGISTRY_VERSION_V1,
        "routes": [],
        "route_count": 0,
        "guidance_count": 0,
        "expected_route_pairs": 0,
        "canonical_fingerprint": "",
        "errors": list(surf_errors) + list(rule_errors),
        "inputs": {"commercial_guidance_only": True},
        "registries_valid": bool(surf_ok and rule_ok),
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not surf_ok or not rule_ok:
        out["errors"].append("invalid_registry")
        return out

    anchor = _floor_second(as_of or _utc_naive_now())
    out["as_of"] = anchor.isoformat(sep=" ")
    guidance = generate_commercial_guidance_v1(
        slug, assembly_window=window, as_of=anchor
    )
    if not guidance.get("ok"):
        out["errors"].extend(
            [f"guidance:{e}" for e in (guidance.get("errors") or ["failed"])]
        )
        return out

    records = list(guidance.get("records") or [])
    out["guidance_count"] = len(records)
    out["expected_route_pairs"] = len(records) * len(surfaces)

    routes: list[dict[str, Any]] = []
    for g in sorted(
        records,
        key=lambda r: (
            str(r.get("subject_type") or ""),
            str(r.get("subject_id") or ""),
            str(r.get("guidance_id") or ""),
        ),
    ):
        for surface_key in surfaces:
            try:
                routes.append(
                    evaluate_guidance_surface_route_v1(
                        guidance=g,
                        surface_key=surface_key,
                        as_of=anchor,
                        generated_at=anchor,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — isolate surface failures
                routes.append(
                    {
                        "route_id": _sha(
                            f"failed:{g.get('guidance_id')}:{surface_key}:{exc}"
                        )[:32],
                        "guidance_id": str(g.get("guidance_id") or ""),
                        "store_slug": slug,
                        "subject_type": str(g.get("subject_type") or ""),
                        "subject_id": str(g.get("subject_id") or ""),
                        "surface_key": surface_key,
                        "guidance_key": str(g.get("guidance_key") or ""),
                        "route_scope": SCOPE_INTERNAL,
                        "route_role": ROLE_SUPPRESSED,
                        "route_status": ROUTE_FAILED,
                        "routing_rationale_code": f"failed:{type(exc).__name__}",
                        "routing_context_digest": "",
                        "valid_from": anchor.isoformat(sep=" "),
                        "valid_until": anchor.isoformat(sep=" "),
                        "is_current": True,
                        "routing_version": ROUTING_VERSION_V1,
                        "routing_rule_version": EVALUATOR_VERSION_V1,
                        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
                        "routing_registry_version": ROUTING_REGISTRY_VERSION_V1,
                        "source_contract_version": SOURCE_CONTRACT_VERSION_V1,
                        "input_fingerprint": "",
                        "route_fingerprint": "",
                        "generation_version": EVALUATOR_VERSION_V1,
                        "as_of": anchor.isoformat(sep=" "),
                        "created_at": anchor.isoformat(sep=" "),
                        "refreshed_at": anchor.isoformat(sep=" "),
                        "superseded_at": None,
                    }
                )
                out["errors"].append(
                    f"route_fail:{surface_key}:{type(exc).__name__}"
                )

    out["routes"] = routes
    out["route_count"] = len(routes)
    out["canonical_fingerprint"] = _sha(
        {
            "v": EVALUATOR_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "routes": [
                {
                    "route_id": r["route_id"],
                    "surface_key": r["surface_key"],
                    "route_status": r["route_status"],
                    "route_fingerprint": r.get("route_fingerprint") or "",
                }
                for r in routes
            ],
        }
    )
    out["ok"] = out["route_count"] == out["expected_route_pairs"]
    if not out["ok"]:
        out["errors"].append("route_accounting_mismatch")
    return out


def materialize_guidance_routes_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not guidance_routing_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "superseded": 0,
            "errors": ["guidance_routing_disabled"],
        }

    report = generate_guidance_routes_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if not report.get("ok") and report.get("route_count", 0) == 0:
        return {
            "ok": False,
            "upserted": 0,
            "superseded": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_guidance_routing_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    superseded = 0
    errors: list[str] = list(report.get("errors") or [])

    for rec in report.get("routes") or []:
        surface_key = str(rec.get("surface_key") or "")
        if surface_key not in SURFACES_V1 or get_surface_v1(surface_key) is None:
            errors.append(f"unsupported_surface:{surface_key}")
            continue
        try:
            rid = str(rec["route_id"])
            store = str(rec["store_slug"])
            gid = str(rec.get("guidance_id") or "")

            currents = (
                db.session.query(GuidanceRoute)
                .filter(
                    GuidanceRoute.store_slug == store,
                    GuidanceRoute.guidance_id == gid,
                    GuidanceRoute.surface_key == surface_key,
                    GuidanceRoute.is_current.is_(True),
                    GuidanceRoute.route_id != rid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.route_status = ROUTE_SUPERSEDED
                row.superseded_at = now
                superseded += 1

            existing = (
                db.session.query(GuidanceRoute)
                .filter(GuidanceRoute.route_id == rid)
                .first()
            )
            fields = dict(
                guidance_id=gid,
                store_slug=store,
                subject_type=str(rec.get("subject_type") or ""),
                subject_id=str(rec.get("subject_id") or ""),
                surface_key=surface_key,
                guidance_key=str(rec.get("guidance_key") or ""),
                route_scope=str(rec.get("route_scope") or ""),
                route_role=str(rec.get("route_role") or ""),
                route_status=str(rec.get("route_status") or ROUTE_INELIGIBLE),
                routing_rationale_code=str(rec.get("routing_rationale_code") or ""),
                routing_context_digest=str(rec.get("routing_context_digest") or ""),
                valid_from=anchor,
                valid_until=_parse_iso(rec.get("valid_until")) or anchor,
                is_current=True,
                routing_version=ROUTING_VERSION_V1,
                routing_rule_version=str(rec.get("routing_rule_version") or ""),
                surface_registry_version=SURFACE_REGISTRY_VERSION_V1,
                routing_registry_version=ROUTING_REGISTRY_VERSION_V1,
                source_contract_version=str(
                    rec.get("source_contract_version") or SOURCE_CONTRACT_VERSION_V1
                ),
                input_fingerprint=str(rec.get("input_fingerprint") or ""),
                route_fingerprint=str(rec.get("route_fingerprint") or ""),
                generation_version=EVALUATOR_VERSION_V1,
                as_of=anchor,
                as_of_key=as_key,
                created_at=existing.created_at if existing else now,
                refreshed_at=now,
                superseded_at=None,
            )
            if existing is None:
                db.session.add(GuidanceRoute(route_id=rid, **fields))
            else:
                for k, v in fields.items():
                    setattr(existing, k, v)
            db.session.commit()
            upserted += 1
        except SQLAlchemyError as exc:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            errors.append(f"materialize:{surface_key}:{type(exc).__name__}")
            log.debug("guidance route materialize failed: %s", exc)

    accounting_ok = report.get("route_count") == report.get("expected_route_pairs")
    return {
        "ok": bool(accounting_ok and upserted > 0),
        "upserted": upserted,
        "superseded": superseded,
        "errors": errors,
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "route_count": report.get("route_count") or 0,
        "expected_route_pairs": report.get("expected_route_pairs") or 0,
        "guidance_count": report.get("guidance_count") or 0,
        "store_slug": report.get("store_slug"),
        "assembly_window": report.get("assembly_window"),
        "as_of": report.get("as_of"),
    }


def verify_guidance_routing_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = _floor_second(as_of or _utc_naive_now())
    a = generate_guidance_routes_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = generate_guidance_routes_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    match = bool(
        a.get("ok")
        and b.get("ok")
        and a.get("canonical_fingerprint")
        and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
    )
    return {
        "ok": match,
        "deterministic": match,
        "as_of": anchor.isoformat(sep=" "),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "route_count": a.get("route_count") or 0,
        "expected_route_pairs": a.get("expected_route_pairs") or 0,
        "guidance_count": a.get("guidance_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "evaluate_guidance_surface_route_v1",
    "generate_guidance_routes_v1",
    "materialize_guidance_routes_v1",
    "verify_guidance_routing_determinism_v1",
]
