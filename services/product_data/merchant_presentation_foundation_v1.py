# -*- coding: utf-8 -*-
"""
Merchant Presentation Foundation V1 — Guidance Routing–only representation contracts.

No UI, layout, AI, or action execution.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import MerchantPresentation
from schema_merchant_presentation_v1 import ensure_merchant_presentation_schema
from services.product_data.guidance_routing_foundation_v1 import (
    generate_guidance_routes_v1,
)
from services.product_data.guidance_routing_types_v1 import (
    ROUTE_BLOCKED,
    ROUTE_DEFERRED,
    ROUTE_ELIGIBLE,
    ROUTE_EXPIRED,
    ROUTE_INELIGIBLE,
)
from services.product_data.merchant_presentation_flag_v1 import (
    merchant_presentation_v1_enabled,
)
from services.product_data.merchant_presentation_registry_v1 import (
    matching_presentation_rules_v1,
    presentation_registry_valid_v1,
)
from services.product_data.merchant_presentation_templates_v1 import (
    get_template_v1,
    render_template_text_v1,
    template_registry_valid_v1,
)
from services.product_data.merchant_presentation_types_v1 import (
    AFFORDANCE_NONE,
    GENERATION_VERSION_V1,
    LANGUAGE_CODE_V1,
    PRESENTATION_REGISTRY_VERSION_V1,
    PRESENTATION_VERSION_V1,
    SOURCE_CONTRACT_VERSION_V1,
    STATE_BLOCKED,
    STATE_EXPIRED,
    STATE_FAILED,
    STATE_SUPERSEDED,
    TEMPLATE_REGISTRY_VERSION_V1,
)
from services.product_data.time_authority_binding_resolve_v1 import resolve_bound_as_of_v1

log = logging.getLogger("cartflow")

_ACTION_LABELS = {
    "none": "action_none",
    "navigate": "action_navigate",
    "review": "action_review",
    "inspect": "action_inspect",
    "configure": "action_configure",
    "acknowledge": "action_acknowledge",
}


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


def _route_needs_presentation(route: dict[str, Any]) -> bool:
    status = str(route.get("route_status") or "")
    return status in {ROUTE_ELIGIBLE, ROUTE_BLOCKED, ROUTE_DEFERRED}


def _failed_presentation(
    *,
    route: dict[str, Any],
    as_of: datetime,
    generated_at: datetime,
    reason: str,
) -> dict[str, Any]:
    pid = _sha(
        {
            "v": PRESENTATION_VERSION_V1,
            "route": route.get("route_id"),
            "fail": reason,
            "as_of": _as_of_key(as_of),
        }
    )[:32]
    rec = {
        "presentation_id": pid,
        "route_id": str(route.get("route_id") or ""),
        "guidance_id": str(route.get("guidance_id") or ""),
        "store_slug": str(route.get("store_slug") or ""),
        "subject_type": str(route.get("subject_type") or ""),
        "subject_id": str(route.get("subject_id") or ""),
        "surface_key": str(route.get("surface_key") or ""),
        "route_scope": str(route.get("route_scope") or ""),
        "route_role": str(route.get("route_role") or ""),
        "guidance_key": str(route.get("guidance_key") or ""),
        "presentation_type": "abstention_state",
        "presentation_state": STATE_FAILED,
        "headline_key": "",
        "headline_text": "",
        "primary_statement_key": "",
        "primary_statement_text": "",
        "supporting_statement_key": "",
        "supporting_statement_text": "",
        "known_fact_items": [],
        "unknown_fact_items": [],
        "evidence_state": "",
        "merchant_relevance_key": "",
        "merchant_relevance_text": "",
        "action_affordance": AFFORDANCE_NONE,
        "action_label_key": "action_none",
        "disclaimer_key": "disclaimer_claim_boundary",
        "status_label_key": "status_failed",
        "template_key": "",
        "template_version": "",
        "presentation_rule_version": "",
        "language_code": LANGUAGE_CODE_V1,
        "failure_reason": reason,
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": str(route.get("valid_until") or as_of.isoformat(sep=" ")),
        "is_current": True,
        "presentation_version": PRESENTATION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "source_contract_version": SOURCE_CONTRACT_VERSION_V1,
        "presentation_registry_version": PRESENTATION_REGISTRY_VERSION_V1,
        "template_registry_version": TEMPLATE_REGISTRY_VERSION_V1,
        "input_fingerprint": "",
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
    }
    rec["presentation_fingerprint"] = _sha(
        {k: v for k, v in rec.items() if k != "presentation_fingerprint"}
    )
    return rec


def evaluate_route_presentation_v1(
    *,
    route: dict[str, Any],
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any] | None:
    """Build one presentation from one route, or None if route is skipped."""
    status = str(route.get("route_status") or "")
    if status in {ROUTE_INELIGIBLE, ROUTE_EXPIRED, "superseded"}:
        return None
    if not _route_needs_presentation(route):
        return None

    ctx = dict(route.get("presentation_context") or {})
    known = list(ctx.get("known_facts") or [])
    unknown = list(ctx.get("unknown_facts") or [])
    prohibited = list(ctx.get("prohibited_claims") or [])
    evidence_state = str(ctx.get("evidence_state") or "")

    # Never render prohibited claim text as merchant statements.
    banned_fragments = ("shipping is expensive", "lower the shipping", "increase advertising")
    for fact in known:
        low = str(fact).lower()
        if any(b in low for b in banned_fragments):
            return _failed_presentation(
                route=route,
                as_of=as_of,
                generated_at=generated_at,
                reason="prohibited_claim_in_known_facts",
            )

    matches = matching_presentation_rules_v1(route)
    if not matches:
        if status == ROUTE_ELIGIBLE:
            return _failed_presentation(
                route=route,
                as_of=as_of,
                generated_at=generated_at,
                reason="no_matching_presentation_rule",
            )
        # blocked/deferred without state rule → skip (not expected)
        return None

    rule = matches[0]
    template = get_template_v1(str(rule.get("template_key") or ""))
    if template is None:
        return _failed_presentation(
            route=route,
            as_of=as_of,
            generated_at=generated_at,
            reason=f"missing_template:{rule.get('template_key')}",
        )

    variables: dict[str, str] = {
        "guidance_key": str(route.get("guidance_key") or ""),
        "surface_key": str(route.get("surface_key") or ""),
        "subject_type": str(route.get("subject_type") or ""),
    }
    for req in template.get("required_variables") or []:
        if req not in variables or not variables[req]:
            return _failed_presentation(
                route=route,
                as_of=as_of,
                generated_at=generated_at,
                reason=f"missing_variable:{req}",
            )

    affordance = str(rule.get("action_affordance") or AFFORDANCE_NONE)
    headline = render_template_text_v1(template["headline_template"], variables)
    primary = render_template_text_v1(template["primary_template"], variables)
    supporting = render_template_text_v1(template["supporting_template"], variables)
    relevance = render_template_text_v1(template["relevance_template"], variables)
    max_len = int(template.get("max_content_length") or 280)
    headline = headline[:max_len]
    primary = primary[:max_len]
    supporting = supporting[:max_len]

    slots = set(rule.get("permitted_content_slots") or [])
    known_out = known if "known_facts" in slots else []
    unknown_out = unknown if "unknown_facts" in slots else []

    input_fingerprint = _sha(
        {
            "route_id": route.get("route_id"),
            "route_fingerprint": route.get("route_fingerprint"),
            "presentation_context": ctx,
            "rule": rule.get("presentation_rule_key"),
            "template": template.get("template_key"),
            "as_of": _as_of_key(as_of),
        }
    )
    presentation_id = _sha(
        {
            "v": PRESENTATION_VERSION_V1,
            "gen": GENERATION_VERSION_V1,
            "route_id": route.get("route_id"),
            "rule": rule.get("presentation_rule_key"),
            "as_of": _as_of_key(as_of),
            "input": input_fingerprint,
        }
    )[:32]

    state = str(rule.get("presentation_state") or STATE_FAILED)
    if status == ROUTE_BLOCKED and state not in {STATE_BLOCKED, STATE_INSUFFICIENT}:
        state = STATE_BLOCKED
    if status == ROUTE_DEFERRED:
        state = STATE_DEFERRED

    record = {
        "presentation_id": presentation_id,
        "route_id": str(route.get("route_id") or ""),
        "guidance_id": str(route.get("guidance_id") or ""),
        "store_slug": str(route.get("store_slug") or ""),
        "subject_type": str(route.get("subject_type") or ""),
        "subject_id": str(route.get("subject_id") or ""),
        "surface_key": str(route.get("surface_key") or ""),
        "route_scope": str(route.get("route_scope") or ""),
        "route_role": str(route.get("route_role") or ""),
        "guidance_key": str(route.get("guidance_key") or ""),
        "presentation_type": str(rule.get("presentation_type") or ""),
        "presentation_state": state,
        "headline_key": f"{template['template_key']}:headline",
        "headline_text": headline if "headline" in slots else "",
        "primary_statement_key": f"{template['template_key']}:primary",
        "primary_statement_text": primary if "primary_statement" in slots else "",
        "supporting_statement_key": f"{template['template_key']}:supporting",
        "supporting_statement_text": supporting
        if "supporting_statement" in slots
        else "",
        "known_fact_items": known_out,
        "unknown_fact_items": unknown_out,
        "evidence_state": evidence_state if "evidence_state" in slots else "",
        "merchant_relevance_key": f"{template['template_key']}:relevance",
        "merchant_relevance_text": relevance if "merchant_relevance" in slots else "",
        "action_affordance": affordance,
        "action_label_key": _ACTION_LABELS.get(affordance, "action_none"),
        "disclaimer_key": "disclaimer_claim_boundary",
        "status_label_key": f"status_{state}",
        "template_key": str(template.get("template_key") or ""),
        "template_version": str(template.get("template_version") or ""),
        "presentation_rule_version": str(rule.get("rule_version") or ""),
        "language_code": LANGUAGE_CODE_V1,
        "failure_reason": "",
        "prohibited_claims_echo": prohibited,
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": str(route.get("valid_until") or as_of.isoformat(sep=" ")),
        "is_current": True,
        "presentation_version": PRESENTATION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "source_contract_version": str(
            ctx.get("contract_version") or SOURCE_CONTRACT_VERSION_V1
        ),
        "presentation_registry_version": PRESENTATION_REGISTRY_VERSION_V1,
        "template_registry_version": TEMPLATE_REGISTRY_VERSION_V1,
        "input_fingerprint": input_fingerprint,
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
    }
    record["presentation_fingerprint"] = _sha(
        {k: v for k, v in record.items() if k != "presentation_fingerprint"}
    )
    return record


def generate_merchant_presentations_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate presentations exclusively via Guidance Routing API."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    pres_ok, pres_errors = presentation_registry_valid_v1()
    tpl_ok, tpl_errors = template_registry_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "presentation_version": PRESENTATION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "presentation_registry_version": PRESENTATION_REGISTRY_VERSION_V1,
        "template_registry_version": TEMPLATE_REGISTRY_VERSION_V1,
        "presentations": [],
        "presentation_count": 0,
        "eligible_route_count": 0,
        "expected_presentation_count": 0,
        "canonical_fingerprint": "",
        "errors": list(pres_errors) + list(tpl_errors),
        "inputs": {"guidance_routing_only": True},
        "registries_valid": bool(pres_ok and tpl_ok),
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not (pres_ok and tpl_ok):
        out["errors"].append("invalid_registry")
        return out

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")
    routes_report = generate_guidance_routes_v1(
        slug, assembly_window=window, as_of=anchor
    )
    if not routes_report.get("ok"):
        out["errors"].extend(
            [f"routing:{e}" for e in (routes_report.get("errors") or ["failed"])]
        )
        return out

    routes = list(routes_report.get("routes") or [])
    eligible = [r for r in routes if r.get("route_status") == ROUTE_ELIGIBLE]
    out["eligible_route_count"] = len(eligible)

    presentations: list[dict[str, Any]] = []
    expected = 0
    for route in sorted(
        routes,
        key=lambda r: (
            str(r.get("surface_key") or ""),
            str(r.get("guidance_id") or ""),
            str(r.get("route_id") or ""),
        ),
    ):
        if not _route_needs_presentation(route):
            continue
        # Count expected only when a rule matches or eligible (must account).
        matches = matching_presentation_rules_v1(route)
        if not matches and route.get("route_status") != ROUTE_ELIGIBLE:
            continue
        expected += 1
        try:
            pres = evaluate_route_presentation_v1(
                route=route, as_of=anchor, generated_at=anchor
            )
            if pres is None:
                presentations.append(
                    _failed_presentation(
                        route=route,
                        as_of=anchor,
                        generated_at=anchor,
                        reason="silent_skip_prevented",
                    )
                )
            else:
                presentations.append(pres)
        except Exception as exc:  # noqa: BLE001 — isolate failures
            presentations.append(
                _failed_presentation(
                    route=route,
                    as_of=anchor,
                    generated_at=anchor,
                    reason=f"exception:{type(exc).__name__}",
                )
            )
            out["errors"].append(
                f"presentation_fail:{route.get('surface_key')}:{type(exc).__name__}"
            )

    out["presentations"] = presentations
    out["presentation_count"] = len(presentations)
    out["expected_presentation_count"] = expected
    out["canonical_fingerprint"] = _sha(
        {
            "v": GENERATION_VERSION_V1,
            "store": slug,
            "as_of": out["as_of"],
            "presentations": [
                {
                    "presentation_id": p["presentation_id"],
                    "surface_key": p["surface_key"],
                    "presentation_state": p["presentation_state"],
                    "presentation_fingerprint": p.get("presentation_fingerprint") or "",
                }
                for p in presentations
            ],
        }
    )
    out["ok"] = out["presentation_count"] == out["expected_presentation_count"]
    if not out["ok"]:
        out["errors"].append("presentation_accounting_mismatch")
    return out


def materialize_merchant_presentations_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not merchant_presentation_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "superseded": 0,
            "errors": ["merchant_presentation_disabled"],
        }

    report = generate_merchant_presentations_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if report.get("presentation_count", 0) == 0 and not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "superseded": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_merchant_presentation_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    superseded = 0
    errors: list[str] = list(report.get("errors") or [])

    for rec in report.get("presentations") or []:
        surface = str(rec.get("surface_key") or "")
        try:
            pid = str(rec["presentation_id"])
            store = str(rec["store_slug"])
            rid = str(rec.get("route_id") or "")

            currents = (
                db.session.query(MerchantPresentation)
                .filter(
                    MerchantPresentation.store_slug == store,
                    MerchantPresentation.route_id == rid,
                    MerchantPresentation.is_current.is_(True),
                    MerchantPresentation.presentation_id != pid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.presentation_state = STATE_SUPERSEDED
                row.superseded_at = now
                superseded += 1

            existing = (
                db.session.query(MerchantPresentation)
                .filter(MerchantPresentation.presentation_id == pid)
                .first()
            )
            fields = dict(
                route_id=rid,
                guidance_id=str(rec.get("guidance_id") or ""),
                store_slug=store,
                subject_type=str(rec.get("subject_type") or ""),
                subject_id=str(rec.get("subject_id") or ""),
                surface_key=surface,
                route_scope=str(rec.get("route_scope") or ""),
                route_role=str(rec.get("route_role") or ""),
                guidance_key=str(rec.get("guidance_key") or ""),
                presentation_type=str(rec.get("presentation_type") or ""),
                presentation_state=str(rec.get("presentation_state") or STATE_FAILED),
                headline_key=str(rec.get("headline_key") or ""),
                headline_text=str(rec.get("headline_text") or ""),
                primary_statement_key=str(rec.get("primary_statement_key") or ""),
                primary_statement_text=str(rec.get("primary_statement_text") or ""),
                supporting_statement_key=str(rec.get("supporting_statement_key") or ""),
                supporting_statement_text=str(
                    rec.get("supporting_statement_text") or ""
                ),
                known_facts_json=json.dumps(
                    rec.get("known_fact_items") or [],
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                unknown_facts_json=json.dumps(
                    rec.get("unknown_fact_items") or [],
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                evidence_state=str(rec.get("evidence_state") or ""),
                merchant_relevance_key=str(rec.get("merchant_relevance_key") or ""),
                merchant_relevance_text=str(rec.get("merchant_relevance_text") or ""),
                action_affordance=str(rec.get("action_affordance") or AFFORDANCE_NONE),
                action_label_key=str(rec.get("action_label_key") or ""),
                disclaimer_key=str(rec.get("disclaimer_key") or ""),
                status_label_key=str(rec.get("status_label_key") or ""),
                template_key=str(rec.get("template_key") or ""),
                template_version=str(rec.get("template_version") or ""),
                presentation_rule_version=str(
                    rec.get("presentation_rule_version") or ""
                ),
                language_code=LANGUAGE_CODE_V1,
                failure_reason=str(rec.get("failure_reason") or ""),
                valid_from=anchor,
                valid_until=_parse_iso(rec.get("valid_until")) or anchor,
                is_current=True,
                presentation_version=PRESENTATION_VERSION_V1,
                generation_version=GENERATION_VERSION_V1,
                source_contract_version=str(
                    rec.get("source_contract_version") or SOURCE_CONTRACT_VERSION_V1
                ),
                input_fingerprint=str(rec.get("input_fingerprint") or ""),
                presentation_fingerprint=str(
                    rec.get("presentation_fingerprint") or ""
                ),
                as_of=anchor,
                as_of_key=as_key,
                created_at=existing.created_at if existing else now,
                refreshed_at=now,
                superseded_at=None,
            )
            if existing is None:
                db.session.add(MerchantPresentation(presentation_id=pid, **fields))
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
            errors.append(f"materialize:{surface}:{type(exc).__name__}")
            log.debug("merchant presentation materialize failed: %s", exc)

    accounting_ok = report.get("presentation_count") == report.get(
        "expected_presentation_count"
    )
    return {
        "ok": bool(accounting_ok and upserted > 0),
        "upserted": upserted,
        "superseded": superseded,
        "errors": errors,
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "presentation_count": report.get("presentation_count") or 0,
        "expected_presentation_count": report.get("expected_presentation_count") or 0,
        "eligible_route_count": report.get("eligible_route_count") or 0,
        "store_slug": report.get("store_slug"),
        "as_of": report.get("as_of"),
    }


def verify_merchant_presentation_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = resolve_bound_as_of_v1(as_of)
    a = generate_merchant_presentations_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = generate_merchant_presentations_v1(
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
        "presentation_count": a.get("presentation_count") or 0,
        "expected_presentation_count": a.get("expected_presentation_count") or 0,
        "eligible_route_count": a.get("eligible_route_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "evaluate_route_presentation_v1",
    "generate_merchant_presentations_v1",
    "materialize_merchant_presentations_v1",
    "verify_merchant_presentation_determinism_v1",
]
