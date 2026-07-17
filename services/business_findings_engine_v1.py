# -*- coding: utf-8 -*-
"""
Business Findings Engine V1 — deterministic commercial findings from evidence.

Pipeline:
  Truth → Evidence Aggregation → Pattern Detection → Finding → Guidance →
  Confidence → Ranking/Dedupe → Knowledge Routing candidates → Surfaces

Home must consume governed findings later; this module does not redesign Home.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import (
    ENGINE_VERSION,
    FINDING_VERSION,
    REC_ACT_NOW,
    REC_INSUFFICIENT,
    REC_TEST,
    STATUS_CONFLICTING,
    STATUS_INSUFFICIENT,
    TYPE_MISSING_CONTACT_BLOCKS,
    finalize_finding,
    is_merchant_worthy,
    norm,
    utc_now_iso,
)
from services.business_findings_evidence_v1 import (
    EvidenceBundle,
    build_demo_rich_evidence_bundle_v1,
    load_evidence_bundle_from_db_v1,
)
from services.business_findings_families_v1 import evaluate_all_families_v1

log = logging.getLogger("cartflow")

# Contact-blocker synonyms collapse into one family finding.
_CONTACT_DEDUPE_TOKENS = (
    "بلا رقم",
    "بيانات التواصل",
    "نقص بيانات",
    "no_phone",
    "بدون هاتف",
    "وسيلة التواصل",
)


def score_finding_v1(finding: Mapping[str, Any]) -> float:
    """Deterministic rank score — higher = more merchant-worthy now."""
    sample = int(finding.get("sample_size") or 0)
    conf = float(finding.get("confidence_score") or 0.0)
    status = norm(finding.get("status"))
    rec = norm(finding.get("recommendation_type"))
    impact = 0.0
    if rec == REC_ACT_NOW:
        impact += 40
    elif rec == REC_TEST:
        impact += 28
    elif rec == "investigate":
        impact += 24
    elif rec == "monitor":
        impact += 10
    elif rec == REC_INSUFFICIENT:
        impact += 6  # honest meta still ranks, but below action
    if status == "confirmed":
        impact += 18
    elif status == "emerging":
        impact += 10
    elif status == STATUS_CONFLICTING:
        impact += 12
    elif status == STATUS_INSUFFICIENT:
        impact += 4
    # Recurrence / sample
    impact += min(25.0, sample / 2.0)
    impact += conf * 20.0
    if finding.get("home_eligible"):
        impact += 5
    if finding.get("is_confirmed_cause"):
        impact += 8
    # Novelty proxy: product/channel variety via family
    family = norm(finding.get("family_key"))
    if family.startswith("product"):
        impact += 6
    if "hesitation" in family:
        impact += 5
    return round(impact, 3)


def dedupe_findings_v1(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """
    Collapse duplicate commercial issues (esp. missing-contact variants).
    Keep highest-ranked finding per family_key / contact cluster.
    """
    suppressed = 0
    by_family: dict[str, dict[str, Any]] = {}
    contact_keeper: Optional[dict[str, Any]] = None

    def _is_contact(f: Mapping[str, Any]) -> bool:
        if norm(f.get("finding_type")) == TYPE_MISSING_CONTACT_BLOCKS:
            return True
        blob = f"{f.get('title')} {f.get('merchant_summary')}".lower()
        return any(tok in blob for tok in _CONTACT_DEDUPE_TOKENS)

    ranked = sorted(findings, key=lambda f: -float(f.get("rank_score") or 0))
    out: list[dict[str, Any]] = []
    for f in ranked:
        if _is_contact(f):
            if contact_keeper is None:
                # Prefer canonical missing-contact type
                contact_keeper = f
                if norm(f.get("finding_type")) != TYPE_MISSING_CONTACT_BLOCKS:
                    # still keep first; later canonical may replace if higher/equal
                    pass
                out.append(f)
                by_family[norm(f.get("family_key")) or "contact_blocker"] = f
            else:
                # Replace if this one is canonical type and keeper is not
                if (
                    norm(f.get("finding_type")) == TYPE_MISSING_CONTACT_BLOCKS
                    and norm(contact_keeper.get("finding_type")) != TYPE_MISSING_CONTACT_BLOCKS
                ):
                    out = [x for x in out if x is not contact_keeper]
                    contact_keeper = f
                    out.append(f)
                suppressed += 1
            continue
        fam = norm(f.get("family_key")) or norm(f.get("finding_type"))
        # Allow hesitation_resolution to keep up to 2 (resolved + unresolved)
        if fam == "hesitation_resolution":
            key = f"{fam}:{norm(f.get('scope_reference'))}:{norm(f.get('finding_id'))}"
        elif fam == "channel_whatsapp":
            key = fam  # one WA effectiveness finding
        else:
            key = fam
        if key in by_family:
            suppressed += 1
            continue
        by_family[key] = f
        out.append(f)
    return out, suppressed


def select_home_candidates_v1(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Home consume feed — executive selection only (no Home redesign here).

    Returns at most:
      - one most important finding
      - one strongest opportunity
      - one highest-value action
      - one meaningful new understanding
    """
    eligible = [
        f
        for f in findings
        if f.get("home_eligible") and is_merchant_worthy(f)
    ]
    eligible.sort(key=lambda f: -float(f.get("rank_score") or 0))

    most_important = eligible[0] if eligible else None
    opportunity = next(
        (
            f
            for f in eligible
            if norm(f.get("recommendation_type")) == REC_TEST
            or "فرصة" in str(f.get("commercial_meaning") or "")
            or norm(f.get("family_key")).startswith("product")
        ),
        None,
    )
    if opportunity is None:
        opportunity = next(
            (f for f in eligible if f is not most_important),
            None,
        )
    action = next(
        (
            f
            for f in eligible
            if norm(f.get("recommendation_type")) == REC_ACT_NOW
        ),
        None,
    )
    if action is None:
        action = next(
            (
                f
                for f in eligible
                if norm(f.get("recommendation_type")) in ("investigate", REC_TEST)
            ),
            None,
        )
    understanding = next(
        (
            f
            for f in eligible
            if "hesitation" in norm(f.get("family_key"))
            or norm(f.get("finding_type")).startswith("insufficient")
            or "فهم" in str(f.get("commercial_meaning") or "")
            or norm(f.get("status")) in (STATUS_INSUFFICIENT, STATUS_CONFLICTING)
        ),
        None,
    )
    if understanding is None and len(eligible) > 1:
        understanding = eligible[-1]

    def _brief(f: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
        if not f:
            return None
        return {
            "finding_id": f.get("finding_id"),
            "title": f.get("title"),
            "merchant_summary": f.get("merchant_summary"),
            "recommendation_type": f.get("recommendation_type"),
            "confidence_level": f.get("confidence_level"),
            "authoritative_surface": f.get("authoritative_surface"),
            "family_key": f.get("family_key"),
        }

    # Avoid repeating the same finding across opportunity/understanding slots.
    # most_important + highest_value_action may share an act_now finding.
    briefs = {
        "most_important_finding": _brief(most_important),
        "strongest_opportunity": _brief(opportunity),
        "highest_value_action": _brief(action),
        "new_understanding": _brief(understanding),
    }
    primary_id = norm((briefs.get("most_important_finding") or {}).get("finding_id"))
    action_id = norm((briefs.get("highest_value_action") or {}).get("finding_id"))
    for key in ("strongest_opportunity", "new_understanding"):
        brief = briefs.get(key)
        if not brief:
            continue
        fid = norm(brief.get("finding_id"))
        if fid and fid in {primary_id, action_id}:
            briefs[key] = None
    return briefs


def project_finding_to_knowledge_item_v1(finding: Mapping[str, Any]) -> dict[str, Any]:
    """Publishable knowledge-routing item (surfaces consume; do not reinvent)."""
    return {
        "insight_key": norm(finding.get("finding_type")),
        "knowledge_id": norm(finding.get("finding_id")),
        "category": "business_finding",
        "severity": (
            "attention"
            if norm(finding.get("recommendation_type")) == REC_ACT_NOW
            else "info"
        ),
        "title_ar": finding.get("title"),
        "message_ar": finding.get("merchant_summary"),
        "impact_ar": finding.get("commercial_meaning"),
        "action_ar": finding.get("recommended_direction"),
        "confidence": finding.get("confidence_level"),
        "evidence": {
            "evidence_summary": finding.get("evidence_summary"),
            "evidence_refs": list(finding.get("evidence_refs") or []),
            "sample_size": finding.get("sample_size"),
        },
        "sample_size": finding.get("sample_size"),
        "finding_v1": True,
        "authoritative_surface": finding.get("authoritative_surface"),
        "eligible_surfaces": [
            "knowledge_layer",
            "merchant_home",
            norm(finding.get("authoritative_surface")) or "knowledge_layer",
        ],
        "aggregation_key": f"bfe:{norm(finding.get('family_key'))}:{norm(finding.get('scope_reference'))}",
        "merchant_visibility": True,
        "ai_used": False,
    }


def run_business_findings_engine_v1(
    *,
    store_slug: str,
    evidence: Optional[EvidenceBundle] = None,
    window_days: int = 14,
    load_db: bool = False,
    dash_store: Any = None,
    demo_fixture: bool = False,
) -> dict[str, Any]:
    """
    Execute the engine and return a governed package.

    Prefer injecting ``evidence`` in tests. ``demo_fixture=True`` uses the rich
    demo bundle. ``load_db=True`` attempts a bounded DB load.
    """
    t0 = time.perf_counter()
    slug = norm(store_slug)
    obs: dict[str, Any] = {
        "findings_evaluated": 0,
        "findings_produced": 0,
        "findings_suppressed": 0,
        "insufficient_evidence_count": 0,
        "conflicting_evidence_count": 0,
        "deduplicated_count": 0,
        "unsupported_hypothesis_count": 0,
        "confidence_distribution": {},
        "finding_families_represented": [],
        "query_cost": 0,
        "slow_stages_ms": {},
        "evidence_coverage_gaps": [],
        "ai_used": False,
        "probabilistic": False,
    }

    t_ev = time.perf_counter()
    if evidence is not None:
        ev = evidence
    elif demo_fixture:
        ev = build_demo_rich_evidence_bundle_v1(store_slug=slug or "demo", window_days=window_days)
    elif load_db:
        ev = load_evidence_bundle_from_db_v1(
            store_slug=slug, window_days=window_days, dash_store=dash_store
        )
    else:
        ev = build_demo_rich_evidence_bundle_v1(store_slug=slug or "demo", window_days=window_days)
    obs["slow_stages_ms"]["evidence_ms"] = round((time.perf_counter() - t_ev) * 1000.0, 2)
    obs["query_cost"] = int(ev.query_cost or 0)
    if not ev.has_visitor_truth:
        obs["evidence_coverage_gaps"].append("visitor_truth_unavailable")
    if not ev.has_product_views:
        obs["evidence_coverage_gaps"].append("product_views_unavailable")
    if ev.widget_shown is None:
        obs["evidence_coverage_gaps"].append("widget_shown_metrics_unavailable")

    t_fam = time.perf_counter()
    raw = evaluate_all_families_v1(ev)
    obs["findings_evaluated"] = len(raw)
    obs["slow_stages_ms"]["families_ms"] = round((time.perf_counter() - t_fam) * 1000.0, 2)

    finalized: list[dict[str, Any]] = []
    for item in raw:
        f = finalize_finding(item)
        if not is_merchant_worthy(f):
            obs["unsupported_hypothesis_count"] += 1
            obs["findings_suppressed"] += 1
            continue
        f["rank_score"] = score_finding_v1(f)
        finalized.append(f)

    t_dd = time.perf_counter()
    deduped, dedupe_count = dedupe_findings_v1(finalized)
    obs["deduplicated_count"] = dedupe_count
    obs["findings_suppressed"] += dedupe_count
    obs["slow_stages_ms"]["dedupe_ms"] = round((time.perf_counter() - t_dd) * 1000.0, 2)

    deduped.sort(key=lambda f: -float(f.get("rank_score") or 0))
    obs["findings_produced"] = len(deduped)
    obs["insufficient_evidence_count"] = sum(
        1 for f in deduped if f.get("status") == STATUS_INSUFFICIENT
    )
    obs["conflicting_evidence_count"] = sum(
        1 for f in deduped if f.get("status") == STATUS_CONFLICTING
    )
    conf_dist: dict[str, int] = {}
    families: list[str] = []
    for f in deduped:
        cl = norm(f.get("confidence_level")) or "unknown"
        conf_dist[cl] = conf_dist.get(cl, 0) + 1
        fam = norm(f.get("family_key"))
        if fam and fam not in families:
            families.append(fam)
    obs["confidence_distribution"] = conf_dist
    obs["finding_families_represented"] = families

    home_feed = select_home_candidates_v1(deduped)
    knowledge_items = [project_finding_to_knowledge_item_v1(f) for f in deduped]

    duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    obs["slow_stages_ms"]["total_ms"] = duration_ms

    return {
        "ok": True,
        "engine_version": ENGINE_VERSION,
        "finding_version": FINDING_VERSION,
        "store_slug": ev.store_slug,
        "generated_at": utc_now_iso(),
        "evidence": {
            "loaded_from": ev.loaded_from,
            "window_days": ev.window_days,
            "observed_period": ev.observed_period,
            "source_tables": list(ev.source_tables or []),
            "query_cost": ev.query_cost,
            "coverage": {
                "has_visitor_truth": ev.has_visitor_truth,
                "has_product_views": ev.has_product_views,
                "widget_shown_known": ev.widget_shown is not None,
            },
        },
        "findings": deduped,
        "home_candidates_v1": home_feed,
        "knowledge_items_v1": knowledge_items,
        "observability": obs,
        "ai_used": False,
        "probabilistic": False,
    }


def render_findings_report_markdown_v1(package: Mapping[str, Any]) -> str:
    """Merchant-facing validation report (Arabic conclusions + evidence)."""
    lines = [
        "# Business Findings Demo Report V1",
        "",
        f"**Store:** `{package.get('store_slug')}`  ",
        f"**Generated:** {package.get('generated_at')}  ",
        f"**Engine:** {package.get('engine_version')}  ",
        f"**Evidence:** {(package.get('evidence') or {}).get('loaded_from')}  ",
        "",
        "## Findings",
        "",
    ]
    for i, f in enumerate(package.get("findings") or [], 1):
        lines.extend(
            [
                f"### {i}. {f.get('title')}",
                "",
                f"- **Family:** `{f.get('family_key')}` / `{f.get('finding_type')}`",
                f"- **Summary:** {f.get('merchant_summary')}",
                f"- **Commercial meaning:** {f.get('commercial_meaning')}",
                f"- **Evidence:** {f.get('evidence_summary')}",
                f"- **Confidence:** {f.get('confidence_level')} ({f.get('confidence_score')})",
                f"- **Recommendation:** `{f.get('recommendation_type')}` — {f.get('recommended_direction')}",
                f"- **Status:** `{f.get('status')}`",
                f"- **Authoritative surface:** `{f.get('authoritative_surface')}`",
                f"- **Sample size:** {f.get('sample_size')}",
                "",
            ]
        )
    home = package.get("home_candidates_v1") or {}
    lines.extend(["## Home candidates (consume later — no Home redesign)", ""])
    for key in (
        "most_important_finding",
        "strongest_opportunity",
        "highest_value_action",
        "new_understanding",
    ):
        brief = home.get(key)
        if brief:
            lines.append(f"- **{key}:** {brief.get('title')}")
        else:
            lines.append(f"- **{key}:** _(none)_")
    obs = package.get("observability") or {}
    lines.extend(
        [
            "",
            "## Observability (internal)",
            "",
            f"- produced: {obs.get('findings_produced')}",
            f"- suppressed: {obs.get('findings_suppressed')}",
            f"- deduplicated: {obs.get('deduplicated_count')}",
            f"- insufficient: {obs.get('insufficient_evidence_count')}",
            f"- conflicting: {obs.get('conflicting_evidence_count')}",
            f"- families: {', '.join(obs.get('finding_families_represented') or [])}",
            f"- gaps: {', '.join(obs.get('evidence_coverage_gaps') or [])}",
            "",
        ]
    )
    return "\n".join(lines)
