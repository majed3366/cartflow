# -*- coding: utf-8 -*-
"""
Merchant Experience Binding V1 — MEIF consumes Business Findings Lifecycle only.

Does not generate, rebuild, or infer findings.
Does not modify BFL / Knowledge / Operational Truth producers.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

log = logging.getLogger("cartflow")

ENV_ME_BFL_BINDING_V1 = "CARTFLOW_MERCHANT_EXPERIENCE_BINDING_V1"
BINDING_VERSION_V1 = "mebf_v1"

PAGE_HOME = "home"
PAGE_DECISION = "decision_workspace"
PAGE_CARTS = "carts"
PAGE_COMMUNICATION = "communication"


def merchant_experience_binding_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_ME_BFL_BINDING_V1) or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _norm(v: Any) -> str:
    return str(v or "").strip()


def project_finding_render_contract_v1(finding: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Canonical merchant render contract — no finding_id ⇒ reject."""
    if not isinstance(finding, dict):
        return None
    fid = _norm(finding.get("finding_id"))
    ftype = _norm(finding.get("finding_type"))
    if not fid or not ftype:
        return None
    title = _norm(
        finding.get("title")
        or finding.get("merchant_summary")
        or finding.get("merchant_statement_ar")
    )
    if not title:
        return None
    evidence = finding.get("evidence") or {}
    if isinstance(evidence, dict):
        evidence_summary = _norm(
            evidence.get("evidence_summary")
            or finding.get("evidence_summary")
            or finding.get("evidence_ar")
        )
    else:
        evidence_summary = _norm(evidence)
    reasoning = finding.get("reasoning") or {}
    if not isinstance(reasoning, dict):
        reasoning = {}
    explanation = _norm(
        finding.get("explanation")
        or finding.get("commercial_meaning")
        or reasoning.get("commercial_meaning")
        or finding.get("merchant_summary")
        or finding.get("business_impact")
        or reasoning.get("business_impact")
    )
    confidence = _norm(
        finding.get("confidence")
        or finding.get("confidence_level")
        or finding.get("confidence_label")
    )
    action = _norm(
        finding.get("recommended_action")
        or finding.get("recommended_direction")
        or finding.get("recommended_direction_ar")
    )
    destinations = list(
        (finding.get("eligible_surfaces") or [])
        or ((finding.get("routing") or {}).get("surface") or {}).get("destinations")
        or []
    )
    # Payload from engine may carry home_eligible / authoritative_surface
    if finding.get("home_eligible") or finding.get("lifecycle_state") in {
        "surface_eligible",
        "displayed",
    }:
        if "merchant_home" not in destinations and PAGE_HOME not in destinations:
            destinations.append("merchant_home")
    auth = _norm(finding.get("authoritative_surface"))
    if auth and auth not in destinations:
        destinations.append(auth)

    return {
        "finding_id": fid,
        "finding_type": ftype,
        "title": title,
        "explanation": explanation or title,
        "evidence_summary": evidence_summary or "أدلة من سجل المتجر التاريخي.",
        "confidence": confidence or "unknown",
        "recommended_action": action
        or "راجع هذا الاستنتاج في مساحة القرار قبل أي إجراء.",
        "severity": _norm(finding.get("severity")),
        "eligible_surfaces": destinations,
        "lifecycle_state": _norm(finding.get("lifecycle_state")),
        # MEIF card compatibility (still BFL-sourced; not SCF inference)
        "information_class": "business_finding",
        "source_type": "business_finding",
        "trust_class": "observation",
        "trust_class_ar": "استنتاج تجاري",
        "merchant_statement_ar": title,
        "presentation_intent": "insight_card",
        "bfl_binding": True,
        "binding_version": BINDING_VERSION_V1,
        "source_lineage": {
            "finding_id": fid,
            "finding_type": ftype,
            "source_type": "business_finding",
            "confidence": confidence or "unknown",
            "explainability": {
                "what_happened_ar": title,
                "why_true_ar": explanation or title,
                "evidence_ar": evidence_summary or "",
                "next_step_ar": action
                or "راجع هذا الاستنتاج في مساحة القرار قبل أي إجراء.",
            },
        },
        "priority": 10,
    }


def _surface_for_destinations(destinations: list[str]) -> list[str]:
    out: list[str] = []
    joined = " ".join(destinations).lower()
    if any(
        x in joined
        for x in ("merchant_home", "home", "knowledge_layer")
    ):
        out.append(PAGE_HOME)
    if "decision" in joined or "workspace" in joined:
        out.append(PAGE_DECISION)
    if "cart" in joined:
        out.append(PAGE_CARTS)
    if "whatsapp" in joined or "communication" in joined:
        out.append(PAGE_COMMUNICATION)
    if not out and destinations:
        # Default home when destinations unknown but finding is home-eligible payload
        out.append(PAGE_HOME)
    return out


def load_bound_findings_v1(
    store_slug: str,
    *,
    mark_displayed: bool = True,
) -> dict[str, Any]:
    """Consume BFL package only — never call the findings engine."""
    slug = _norm(store_slug)[:255]
    empty = {
        "ok": False,
        "store_slug": slug,
        "binding_version": BINDING_VERSION_V1,
        "findings": [],
        "by_surface": {
            PAGE_HOME: [],
            PAGE_DECISION: [],
            PAGE_CARTS: [],
            PAGE_COMMUNICATION: [],
        },
        "diagnostics": [],
        "errors": [],
    }
    if not slug or not merchant_experience_binding_v1_enabled():
        empty["errors"].append("binding_disabled_or_empty_slug")
        return empty
    try:
        from services.business_findings_lifecycle_v1.consume_home_v1 import (
            load_current_findings_package_v1,
        )
    except Exception as exc:  # noqa: BLE001
        empty["errors"].append(f"import:{type(exc).__name__}")
        return empty

    try:
        package = load_current_findings_package_v1(
            slug, mark_displayed=bool(mark_displayed)
        )
    except Exception as exc:  # noqa: BLE001
        empty["errors"].append(f"consume:{type(exc).__name__}")
        log.warning("mebf consume failed: %s", exc)
        return empty

    raw = [f for f in list(package.get("findings") or []) if isinstance(f, dict)]
    diagnostics: list[dict[str, Any]] = []
    by_surface: dict[str, list[dict[str, Any]]] = {
        PAGE_HOME: [],
        PAGE_DECISION: [],
        PAGE_CARTS: [],
        PAGE_COMMUNICATION: [],
    }
    contracts: list[dict[str, Any]] = []

    for f in raw:
        contract = project_finding_render_contract_v1(f)
        diag_base = {
            "finding_id": _norm(f.get("finding_id")),
            "finding_type": _norm(f.get("finding_type")),
            "surface_requested": [],
            "renderer_invoked": False,
            "render_accepted": False,
            "render_skipped": False,
            "skip_reason": None,
        }
        if contract is None:
            diag_base["render_skipped"] = True
            diag_base["skip_reason"] = "incomplete_render_contract"
            diagnostics.append(diag_base)
            continue
        surfaces = _surface_for_destinations(
            list(contract.get("eligible_surfaces") or [])
        )
        # Home-eligible payload always binds Home
        if f.get("home_eligible") is True or contract.get("lifecycle_state") in {
            "surface_eligible",
            "displayed",
        }:
            if PAGE_HOME not in surfaces:
                surfaces.append(PAGE_HOME)
        if not surfaces:
            diag_base["render_skipped"] = True
            diag_base["skip_reason"] = "no_eligible_surface"
            diagnostics.append(diag_base)
            continue
        diag_base["surface_requested"] = surfaces
        contracts.append(contract)
        for s in surfaces:
            if s in by_surface:
                by_surface[s].append(contract)
        diagnostics.append(diag_base)

    return {
        "ok": True,
        "store_slug": slug,
        "binding_version": BINDING_VERSION_V1,
        "source": package.get("source") or "lifecycle_consume",
        "findings": contracts,
        "by_surface": by_surface,
        "diagnostics": diagnostics,
        "errors": [],
        "count": len(contracts),
    }


def _strip_non_finding_insights(items: Any) -> list[dict[str, Any]]:
    """Remove merchant insight cards that lack finding_id (legacy SCF/guidance)."""
    out: list[dict[str, Any]] = []
    for it in list(items or []):
        if not isinstance(it, dict):
            continue
        fid = _norm(it.get("finding_id")) or _norm(
            (it.get("source_lineage") or {}).get("finding_id")
        )
        if fid or it.get("bfl_binding") or it.get("source_type") == "business_finding":
            out.append(it)
    return out


def apply_business_findings_binding_to_meif_v1(
    meif_report: dict[str, Any],
    store_slug: str,
) -> dict[str, Any]:
    """
    Bind BFL findings into MEIF pages. Pure consumer seam.

    OT fact strips remain; commercial insight sections require finding_id.
    """
    if not isinstance(meif_report, dict):
        return meif_report
    if not merchant_experience_binding_v1_enabled():
        meif_report["business_findings_binding_v1"] = {
            "ok": False,
            "enabled": False,
            "binding_version": BINDING_VERSION_V1,
        }
        return meif_report

    bound = load_bound_findings_v1(store_slug, mark_displayed=True)
    pages = dict(meif_report.get("pages") or {})

    home = dict(pages.get(PAGE_HOME) or {})
    home_sections = dict(home.get("sections") or {})
    home_findings = list((bound.get("by_surface") or {}).get(PAGE_HOME) or [])
    home_sections["business_findings"] = home_findings[:6]
    # Commercial insight bands: BFL only (no SCF guidance without finding_id)
    home_sections["commercial_guidance_highlights"] = home_findings[:3]
    home_sections["executive_summary"] = _strip_non_finding_insights(
        home_sections.get("executive_summary")
    )
    if home_findings:
        # Lead executive with top finding
        home_sections["executive_summary"] = (
            home_findings[:1] + list(home_sections.get("executive_summary") or [])
        )[:4]
    home_sections["knowledge_highlights"] = _strip_non_finding_insights(
        home_sections.get("knowledge_highlights")
    )
    home["sections"] = home_sections
    home["business_findings_bound"] = True
    home["business_findings_count"] = len(home_findings)
    pages[PAGE_HOME] = home

    decision = dict(pages.get(PAGE_DECISION) or {})
    d_sections = dict(decision.get("sections") or {})
    d_findings = list((bound.get("by_surface") or {}).get(PAGE_DECISION) or [])
    # Prefer BFL for review; keep OT critical_attention separately if needed
    review = _strip_non_finding_insights(d_sections.get("review_items"))
    d_sections["review_items"] = (d_findings + review)[:8]
    d_sections["business_findings"] = d_findings[:6]
    decision["sections"] = d_sections
    pages[PAGE_DECISION] = decision

    carts = dict(pages.get(PAGE_CARTS) or {})
    c_sections = dict(carts.get("sections") or {})
    c_findings = list((bound.get("by_surface") or {}).get(PAGE_CARTS) or [])
    composition = _strip_non_finding_insights(c_sections.get("composition_items"))
    c_sections["composition_items"] = (c_findings + composition)[:6]
    c_sections["business_findings"] = c_findings[:4]
    carts["sections"] = c_sections
    pages[PAGE_CARTS] = carts

    communication = dict(pages.get(PAGE_COMMUNICATION) or {})
    cm_sections = dict(communication.get("sections") or {})
    cm_findings = list(
        (bound.get("by_surface") or {}).get(PAGE_COMMUNICATION) or []
    )
    cm_comp = _strip_non_finding_insights(cm_sections.get("composition_items"))
    cm_sections["composition_items"] = (cm_findings + cm_comp)[:6]
    cm_sections["business_findings"] = cm_findings[:4]
    communication["sections"] = cm_sections
    pages[PAGE_COMMUNICATION] = communication

    meif_report["pages"] = pages
    meif_report["business_findings_binding_v1"] = {
        "ok": bool(bound.get("ok")),
        "enabled": True,
        "binding_version": BINDING_VERSION_V1,
        "source": bound.get("source"),
        "findings_bound": int(bound.get("count") or 0),
        "home_bound": len(home_findings),
        "decision_bound": len(d_findings),
        "carts_bound": len(c_findings),
        "communication_bound": len(cm_findings),
        "diagnostics": list(bound.get("diagnostics") or []),
        "errors": list(bound.get("errors") or []),
        "pure_consumer": True,
        "never_generates_findings": True,
    }
    inputs = dict(meif_report.get("inputs") or {})
    inputs["business_findings_lifecycle"] = True
    inputs["no_new_business_logic"] = True
    meif_report["inputs"] = inputs
    return meif_report


__all__ = [
    "ENV_ME_BFL_BINDING_V1",
    "BINDING_VERSION_V1",
    "merchant_experience_binding_v1_enabled",
    "project_finding_render_contract_v1",
    "load_bound_findings_v1",
    "apply_business_findings_binding_to_meif_v1",
]
