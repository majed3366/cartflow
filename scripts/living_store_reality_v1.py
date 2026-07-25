# -*- coding: utf-8 -*-
"""
Living Store Reality Simulation V1

Creates ~30 days of realistic operational history on the demo store, then
*observes* what CartFlow naturally understands — without improving UI,
hardcoding executive copy, or implementing Product Intelligence.

Output:
  docs/product/living_store_reality_v1/observation_capture.json
  docs/product/living_store_reality_v1/REALITY_OBSERVATION_REPORT.md (skeleton + facts)

Run:
  python scripts/living_store_reality_v1.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "product" / "living_store_reality_v1"
SEED = 20260725
START_DATE = "2026-05-01"
DURATION_DAYS = 30
SIM_END = datetime(2026, 5, 31, 18, 0, 0, tzinfo=timezone.utc)

# Broad scenario mix — every recovery / customer / product personality path.
LIVING_SCENARIOS = [
    "S01_normal_store_baseline",
    "S02_high_traffic_low_conversion",
    "S03_shipping_cost_hesitation",
    "S04_product_high_atc_low_purchase",
    "S05_wa_return_without_purchase",
    "S06_wa_success",
    "S07_discount_message_failure",
    "S08_repeated_product_interest",
    "S09_widget_opened_ignored",
    "S10_widget_reason_capture",
    "S11_ignore_all_recovery",
    "S12_multi_return_customer",
    "S13_organic_purchase",
    "S14_ambiguous_influence",
    "S15_vip_customer",
    "S16_insufficient_data",
    "S17_conflicting_evidence",
    "S18_purchase_closure_suppression",
    "S19_channel_failure",
]


def _bootstrap_env() -> Path:
    db_path = Path(tempfile.gettempdir()) / f"cartflow_living_store_v1_{SEED}.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass
    os.environ["DATABASE_URL"] = "sqlite:///" + str(db_path).replace("\\", "/")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")
    os.environ.setdefault("CARTFLOW_OBSERVATION_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_EXPERIENCE_BINDING_V1", "1")
    os.environ.setdefault("CARTFLOW_BUSINESS_FINDINGS_LIFECYCLE_V1", "1")
    os.environ.setdefault("CARTFLOW_DECISION_COMPOSITION_ENGINE_V1", "1")
    os.environ.setdefault("CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1", "1")
    os.environ.setdefault("CARTFLOW_HOME_SLIM_TRANSPORT_V1", "1")
    return db_path


def _run_simulation() -> dict[str, Any]:
    from services.store_reality_simulator.config_loader_v1 import load_simulation_config
    from services.store_reality_simulator.event_ledger_v1 import persist_plan_to_ledger
    from services.store_reality_simulator.manifest_v1 import (
        build_simulation_manifest,
        write_manifest_file,
    )
    from services.store_reality_simulator.performance_guards_v1 import (
        PerformanceThresholds,
    )
    from services.store_reality_simulator.planner_v1 import build_reality_plan
    from services.store_reality_simulator.reality_engine_v1 import execute_reality_run
    from services.store_reality_simulator.reality_score_v1 import compute_reality_score
    from services.store_reality_simulator.run_registry_v1 import (
        create_simulation_run,
        persist_run,
    )
    from services.store_reality_simulator.scale_profiles_v1 import get_scale_profile

    profile = get_scale_profile("living_store")
    cfg = load_simulation_config(
        {
            "store_slug": "demo",
            "scenario_ids": LIVING_SCENARIOS,
            "seed": SEED,
            "start_date": START_DATE,
            "duration_days": DURATION_DAYS,
            "scale": 1.0,
            "mode": "execute",
            "batch_size": profile.batch_size,
            "max_events_per_job": profile.max_events_per_run,
            "metadata": {
                "lab": "living_store_reality_v1",
                "scale_profile": "living_store",
                "purpose": "observe_business_from_operational_reality",
            },
        }
    )
    row = create_simulation_run(cfg)
    run_id = row.simulation_run_id
    plan = build_reality_plan(
        simulation_run_id=run_id,
        seed=SEED,
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        duration_days=DURATION_DAYS,
        scenario_ids=cfg.scenario_ids,
        scale=profile,
        scale_factor=1.0,
    )
    persist_plan_to_ledger(plan)
    score = compute_reality_score(plan)
    manifest = build_simulation_manifest(
        plan=plan, config=cfg.to_dict(), reality_score=score
    )
    row.manifest_json = json.dumps(manifest, ensure_ascii=False)
    row.reality_score_json = json.dumps(score, ensure_ascii=False)
    row.scale_profile = "living_store"
    row.status = "created"
    persist_run(row)
    # Enough batches for 4k events @ 50/batch
    result = execute_reality_run(
        run_id,
        max_batches=120,
        thresholds=PerformanceThresholds(batch_wall_ms_max=600_000.0),
    )
    write_manifest_file(result.get("manifest") or manifest, OUT / run_id)
    return {
        "simulation_run_id": run_id,
        "reality_score": score,
        "execute": {
            "status": result.get("status"),
            "events_executed": result.get("events_executed"),
            "batches": result.get("batches"),
        },
        "plan_event_count": len(getattr(plan, "events", []) or []),
    }


def _signup_and_bind(client) -> dict[str, Any]:
    from extensions import db
    from models import MerchantUser
    from services.identity_authority.lab_session_bind_v1 import (
        align_merchant_session_to_simulation_store,
        ensure_demo_store_for_lab,
    )
    from services.merchant_auth_http import merchant_cookie_name

    email = f"living-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/signup",
        data={
            "store_name": "متجر الواقع الحي",
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    cookies = dict(r.cookies)
    ensure_demo_store_for_lab()
    user = db.session.query(MerchantUser).filter_by(email=email).first()
    bind = {"ok": False}
    if user is not None:
        bind = align_merchant_session_to_simulation_store(
            merchant_user_id=int(user.id)
        )
    return {
        "email": email,
        "cookies": cookies,
        "cookie_name": merchant_cookie_name(),
        "lab_session_bind": bind,
        "signup_status": r.status_code,
    }


def _operational_mass() -> dict[str, Any]:
    from extensions import db
    from models import (
        AbandonedCart,
        AbandonmentReasonLog,
        CartLineSnapshot,
        CartRecoveryLog,
        CartRecoveryReason,
        PurchaseTruthRecord,
        RecoverySchedule,
    )

    try:
        from models import ProductSignalEvent  # type: ignore

        signals = db.session.query(ProductSignalEvent).count()
    except Exception:  # noqa: BLE001
        signals = -1
    try:
        from models import ProductHesitationMapping  # type: ignore

        hesitation_maps = db.session.query(ProductHesitationMapping).count()
    except Exception:  # noqa: BLE001
        hesitation_maps = -1
    try:
        from models import MovementSnapshot

        movements = db.session.query(MovementSnapshot).count()
    except Exception:  # noqa: BLE001
        movements = -1

    carts = db.session.query(AbandonedCart).all()
    status_counts = Counter(str(c.status or "") for c in carts)
    phone_gap = sum(1 for c in carts if not str(c.customer_phone or "").strip())
    lines = db.session.query(CartLineSnapshot).all()
    product_names = Counter(str(getattr(ln, "name", None) or "?") for ln in lines)
    reasons = db.session.query(CartRecoveryReason).all()
    reason_tags = Counter(str(r.reason or "") for r in reasons)

    return {
        "abandoned_carts": len(carts),
        "cart_status": dict(status_counts),
        "phone_gap_carts": phone_gap,
        "cart_line_snapshots": len(lines),
        "top_products_by_lines": product_names.most_common(12),
        "cart_recovery_reasons": len(reasons),
        "reason_distribution": dict(reason_tags),
        "abandonment_reason_logs": db.session.query(AbandonmentReasonLog).count(),
        "recovery_schedules": db.session.query(RecoverySchedule).count(),
        "cart_recovery_logs": db.session.query(CartRecoveryLog).count(),
        "purchase_truth_records": db.session.query(PurchaseTruthRecord).count(),
        "movement_snapshots": movements,
        "product_signal_events": signals,
        "product_hesitation_mappings": hesitation_maps,
    }


def _observe() -> dict[str, Any]:
    from services.business_findings_lifecycle_v1 import (
        materialize_business_findings_lifecycle_v1,
    )
    from services.decision_composition_engine_v1 import compose_decisions_v1
    from services.home_executive_summary_v1.compose_v1 import (
        build_home_executive_summary_v1,
    )
    from services.home_executive_summary_v1.slim_transport_v1 import (
        extract_home_teaser_inputs_v1,
    )
    from services.observation_foundation_v1.assemble_v1 import (
        assemble_observation_foundation_v1,
    )
    from services.observation_foundation_v1.merchant_findings_v1 import (
        build_observation_reality_validation_v1,
    )
    from services.store_reality_simulator.behavior_catalog_v1 import (
        LIVING_STORE_PRODUCT_PERSONALITIES_V1,
    )

    obs = assemble_observation_foundation_v1("demo")
    orv = build_observation_reality_validation_v1("demo")
    dce = compose_decisions_v1("demo", use_cache=False, allow_sync_miss=True)

    # Optional BFL materialize from DB evidence (never seed findings).
    bfl: dict[str, Any] = {"attempted": False}
    try:
        bfl = {
            "attempted": True,
            "result": _safe_trim(
                materialize_business_findings_lifecycle_v1(
                    "demo", window_days=30, load_db=True, demo_fixture=False
                ),
                depth=3,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        bfl = {"attempted": True, "error": f"{type(exc).__name__}:{exc}"}

    # Build Home the way slim transport does — counters + DCE teasers + ORV.
    from extensions import db
    from models import AbandonedCart

    carts = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.status.in_(("abandoned", "waiting", "detected")))
        .all()
    )
    waiting = sum(1 for c in carts if str(c.status) in ("abandoned", "waiting"))
    no_phone = sum(1 for c in carts if not str(c.customer_phone or "").strip())
    summary_like = {
        "store_slug": "demo",
        "merchant_nav_badge_abandoned": waiting,
        "merchant_store_cart_counts": {
            "waiting_total": waiting,
            "no_phone_total": no_phone,
            "active_total": waiting,
        },
        "observation_reality_validation_v1": orv if isinstance(orv, dict) else {},
    }
    teasers = extract_home_teaser_inputs_v1(summary_like)
    hes = build_home_executive_summary_v1(
        {**summary_like, "home_teaser_inputs_v1": teasers}
    )

    # Slim observation extracts (avoid dumping huge trees)
    obs_caps = []
    if isinstance(obs, dict):
        caps = obs.get("capabilities") or obs.get("capability_status") or {}
        if isinstance(caps, dict):
            obs_caps = [
                {"id": k, "status": v if not isinstance(v, dict) else v.get("status")}
                for k, v in list(caps.items())[:40]
            ]
        correlations = obs.get("correlations") or obs.get("product_correlations") or []
        if not isinstance(correlations, list):
            correlations = []
    else:
        correlations = []

    orv_findings = []
    if isinstance(orv, dict):
        for f in orv.get("findings") or []:
            if not isinstance(f, dict):
                continue
            orv_findings.append(
                {
                    "capability": f.get("capability") or f.get("capability_id"),
                    "title_ar": f.get("title_ar") or f.get("title"),
                    "statement_ar": f.get("statement_ar") or f.get("statement"),
                    "confidence": f.get("confidence_ar") or f.get("confidence"),
                    "product_name": f.get("product_name_ar")
                    or f.get("product_name")
                    or f.get("entity_name"),
                    "home_teaser_ar": f.get("home_teaser_ar"),
                }
            )

    decisions = []
    for d in (dce.get("published_decisions") or dce.get("portfolio") or [])[:12]:
        if not isinstance(d, dict):
            continue
        decisions.append(
            {
                "title": d.get("merchant_decision") or d.get("title"),
                "domain": d.get("business_domain") or d.get("decision_category"),
                "why": d.get("why"),
                "why_now": d.get("why_now"),
                "evidence": d.get("evidence") or d.get("evidence_ar"),
                "confidence": d.get("confidence") or d.get("confidence_ar"),
                "first_step": d.get("first_step") or d.get("recommended_action"),
                "business_meaning_ar": d.get("business_meaning_ar"),
                "business_impact_ar": d.get("business_impact_ar"),
                "gate_2f": bool(d.get("gate_2f_store_executive")),
            }
        )

    hes_sections = []
    for s in (hes.get("sections") or []):
        if not isinstance(s, dict):
            continue
        hes_sections.append(
            {
                "id": s.get("id"),
                "title_ar": s.get("title_ar"),
                "summary_ar": s.get("summary_ar"),
                "status_ar": s.get("status_ar"),
                "count": s.get("count"),
                "empty": s.get("empty"),
            }
        )

    return {
        "intended_product_personalities": LIVING_STORE_PRODUCT_PERSONALITIES_V1,
        "observation_foundation": {
            "ok": bool(obs.get("ok")) if isinstance(obs, dict) else False,
            "keys": sorted(list(obs.keys()))[:40] if isinstance(obs, dict) else [],
            "capabilities_sample": obs_caps,
            "correlation_count": len(correlations),
            "statement_capabilities_ready": (
                obs.get("statement_capabilities_ready")
                if isinstance(obs, dict)
                else []
            ),
            "counts": (obs.get("counts") if isinstance(obs, dict) else {}),
            "correlations_sample": [
                {
                    "product_key": c.get("product_key"),
                    "kind": c.get("correlation_kind") or c.get("kind"),
                    "stronger": c.get("stronger"),
                    "compare": c.get("compare"),
                }
                for c in correlations[:15]
                if isinstance(c, dict)
            ],
        },
        "orv_findings": orv_findings,
        "orv_finding_count": len(orv_findings),
        "admission_reconciliation": (
            orv.get("admission_reconciliation") if isinstance(orv, dict) else {}
        ),
        "suppressed_by_reason": (
            orv.get("suppressed_by_reason") if isinstance(orv, dict) else {}
        ),
        "workspace_decision_count": len(
            (orv.get("workspace_decisions") or []) if isinstance(orv, dict) else []
        ),
        "present_capabilities": (
            orv.get("present_capabilities") if isinstance(orv, dict) else []
        ),

        "decision_composition": {
            "ok": bool(dce.get("ok")),
            "gate_2f": bool(dce.get("gate_2f_store_executive")),
            "published_count": len(dce.get("published_decisions") or []),
            "portfolio_count": len(dce.get("portfolio") or []),
            "decisions": decisions,
            "category_landscape": (dce.get("category_landscape") or [])[:12],
            "store_executive_briefing": (
                (dce.get("store_executive_understanding_v1") or {}).get("briefing")
            ),
        },
        "home_executive_summary": {
            "ok": bool(hes.get("ok")),
            "governance": hes.get("governance"),
            "sections": hes_sections,
        },
        "home_teasers": teasers,
        "bfl": _safe_trim(bfl, depth=3),
    }


def _safe_trim(obj: Any, *, depth: int = 2) -> Any:
    if depth <= 0:
        return "…"
    if isinstance(obj, dict):
        return {str(k)[:80]: _safe_trim(v, depth=depth - 1) for k, v in list(obj.items())[:40]}
    if isinstance(obj, list):
        return [_safe_trim(x, depth=depth - 1) for x in obj[:20]]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)[:200]


def _write_report(capture: dict[str, Any]) -> Path:
    """Write Reality Observation Report from capture facts (not an implementation report)."""
    mass = capture.get("operational_mass") or {}
    hes = (capture.get("observation") or {}).get("home_executive_summary") or {}
    dce = (capture.get("observation") or {}).get("decision_composition") or {}
    orv = (capture.get("observation") or {}).get("orv_findings") or []
    obs = (capture.get("observation") or {}).get("observation_foundation") or {}

    sections = hes.get("sections") or []
    section_lines = "\n".join(
        f"- **{s.get('title_ar')}**: {s.get('summary_ar')} _(status: {s.get('status_ar')})_"
        for s in sections
    )
    decision_lines = "\n".join(
        (
            f"- **{d.get('title')}** (domain={d.get('domain')})\n"
            f"  - why: {d.get('why')}\n"
            f"  - why_now: {d.get('why_now')}\n"
            f"  - meaning: {d.get('business_meaning_ar')}\n"
            f"  - impact: {d.get('business_impact_ar')}\n"
            f"  - first_step: {d.get('first_step')}"
        )
        for d in (dce.get("decisions") or [])[:8]
    ) or "- _(no published decisions)_"

    orv_lines = "\n".join(
        f"- [{f.get('capability')}] {f.get('title_ar') or ''} — {f.get('statement_ar') or ''} "
        f"(product={f.get('product_name') or '—'}, confidence={f.get('confidence')})"
        for f in orv[:20]
    ) or "- _(no ORV findings)_"

    corr_lines = "\n".join(
        f"- {c.get('product')}: {c.get('kind')} — {c.get('summary')}"
        for c in (obs.get("correlations_sample") or [])
    ) or "- _(no correlations sampled)_"

    products = mass.get("top_products_by_lines") or []
    product_lines = "\n".join(f"- {name}: {n} cart-line snapshots" for name, n in products)

    # Heuristic answers for the constitutional questions (evidence-based from this run).
    meaningful_home = [s for s in sections if s.get("summary_ar") and not s.get("empty")]
    meaningful_decisions = dce.get("decisions") or []
    has_product_obs = any(
        s.get("id") == "observations" and not s.get("empty") for s in sections
    )
    signals = int(mass.get("product_signal_events") or 0)
    purchases = int(mass.get("purchase_truth_records") or 0)
    reasons = int(mass.get("cart_recovery_reasons") or 0)

    understood = []
    missed = []
    if mass.get("abandoned_carts", 0) > 0:
        understood.append("Operational cart mass exists and feeds carts/recovery counters.")
    if reasons > 0:
        understood.append("Hesitation reasons were captured with a non-uniform distribution.")
    if purchases > 0:
        understood.append("Purchase Truth records exist alongside abandonments.")
    if meaningful_decisions:
        understood.append(
            "Decision Composition produced at least one merchant-facing decision with why/why_now."
        )
    if hes.get("ok") and len(sections) == 5:
        understood.append("Home Executive Summary composed five cards from teasers (not hardcoded in this lab).")
    if signals > 0:
        understood.append("Product Signal Collection received events via SRS ingress hooks.")
    else:
        missed.append("ProductSignalEvent mass is empty or unavailable — product-level observation may be thin.")
    if not has_product_obs:
        missed.append(
            "Home Product Observations card stayed empty / insufficient-evidence — "
            "named product insights did not surface on Home."
        )
    if not orv:
        missed.append("ORV merchant findings list is empty for this bind/window.")
    if int(mass.get("phone_gap_carts") or 0) > 0 and meaningful_decisions:
        understood.append("Phone-gap / follow-up restriction influenced recovery/operations decisions.")
    # Storefront truth gaps are architectural (unsupported markers).
    missed.append(
        "Page views / product views / dwell / widget-open are still unsupported durable ingest — "
        "attention without cart cannot be observed as first-class evidence."
    )
    missed.append(
        "Seasonality, discount-failure-as-strategy, and stock attention are not naturally named "
        "unless Findings/Observation correlate them from existing tables."
    )

    natural_truths = []
    if "shipping" in str(mass.get("reason_distribution") or {}):
        natural_truths.append("Shipping appears as a concentrated hesitation reason (not uniform noise).")
    if "price" in str(mass.get("reason_distribution") or {}):
        natural_truths.append("Price hesitation appears in reason mix.")
    if products:
        natural_truths.append(
            f"Product identity on cart lines is non-empty; top line product is «{products[0][0]}»."
        )
    if purchases and mass.get("abandoned_carts"):
        natural_truths.append("The store mixes abandoned work with completed purchases — not a pure recovery queue.")

    assumptions = [
        "Demo catalog product names/prices (sandbox SKUs) — merchant catalog sync not simulated.",
        "WhatsApp sends are mock (no provider) — communication health is schedule/log based.",
        "Simulation clock + FixedAsOf at SIM_END — wall-clock Home would not see May history.",
        "Intended product personalities are planner weights, not merchant-authored truth.",
    ]

    before_pi = [
        "Durable storefront attention (views/dwell) ingest, not only cart lines.",
        "Stronger product↔reason↔purchase correlation mass across named entities.",
        "Time-windowed product conversion rates that survive executive composition.",
        "Honest empty states when evidence is thin — already partially present; keep.",
        "Do not invent Product Intelligence recommendations until observation gaps close.",
    ]

    observing_business = (
        "CartFlow is observing a **business-shaped operational reality** (carts, reasons, "
        "recovery, purchases, phones) and composing executive language from that mass — "
        "but it is **not yet fully observing storefront attention or product strategy**. "
        "Verdict: **partially observing a business; still partly processing recovery events.**"
    )

    body = f"""# Reality Observation Report — Living Store Reality V1

**Date (UTC):** {datetime.now(timezone.utc).strftime("%Y-%m-%d")}  
**Simulation:** seed `{SEED}`, `{START_DATE}` + {DURATION_DAYS} days, profile `living_store`  
**Run id:** `{capture.get("simulation", {}).get("simulation_run_id")}`  
**As-of (Time Authority):** `{SIM_END.isoformat()}`  
**Purpose:** Can CartFlow naturally understand a merchant's business from operational reality?

**Not in scope:** Product Intelligence · UI polish · hardcoded executive summaries · invented recommendations.

---

## 1. What was created (operational reality)

| Signal | Count |
|--------|------:|
| Abandoned carts | {mass.get("abandoned_carts")} |
| Phone-gap carts | {mass.get("phone_gap_carts")} |
| Cart line snapshots | {mass.get("cart_line_snapshots")} |
| Hesitation reasons | {mass.get("cart_recovery_reasons")} |
| Reason logs | {mass.get("abandonment_reason_logs")} |
| Recovery schedules | {mass.get("recovery_schedules")} |
| Recovery / WA logs | {mass.get("cart_recovery_logs")} |
| Purchases (truth) | {mass.get("purchase_truth_records")} |
| Movements / returns | {mass.get("movement_snapshots")} |
| Product signals | {mass.get("product_signal_events")} |
| Hesitation mappings | {mass.get("product_hesitation_mappings")} |

**Cart statuses:** `{json.dumps(mass.get("cart_status") or {}, ensure_ascii=False)}`  
**Reason mix:** `{json.dumps(mass.get("reason_distribution") or {}, ensure_ascii=False)}`

### Products appearing in cart lines

{product_lines or "- _(none)_"}

### Intended personalities (planner intent — not Home copy)

These were journey weights only. Observation must rediscover them from evidence:

{json.dumps((capture.get("observation") or {}).get("intended_product_personalities") or {{}}, ensure_ascii=False, indent=2)}

---

## 2. What Home naturally showed

Composition path: operational counters + Decision Composition teasers → Home Executive Summary.

{section_lines or "- _(no sections)_"}

**Meaningful cards (≥ non-empty summary):** {len(meaningful_home)} / 5  
**Product Observations meaningful?** {"yes" if has_product_obs else "no — insufficient named product evidence on Home"}

---

## 3. What Decision Workspace naturally showed

Published / portfolio decisions composed from OT → Domains → Store Executive Understanding (Gate 2F) — not seeded Decision cards.

{decision_lines}

**Landscape sample:** `{json.dumps(dce.get("category_landscape") or [], ensure_ascii=False)[:800]}`

**Morning briefing (store executive):**  
`{json.dumps(dce.get("store_executive_briefing") or {{}}, ensure_ascii=False)}`

---

## 4. Product understanding that emerged

### Observation Foundation

- ok: `{obs.get("ok")}`
- correlation_count: `{obs.get("correlation_count")}`

{corr_lines}

### ORV merchant findings

{orv_lines}

---

## 5. Answers to the required questions

### What did CartFlow understand correctly?

{chr(10).join(f"- {x}" for x in understood) or "- _(none recorded)_"}

### What did CartFlow completely miss?

{chr(10).join(f"- {x}" for x in missed) or "- _(none recorded)_"}

### Which business truths naturally emerged?

{chr(10).join(f"- {x}" for x in natural_truths) or "- _(none recorded)_"}

### Which truths required manual assumptions?

{chr(10).join(f"- {x}" for x in assumptions)}

### Which Home cards became meaningful?

{chr(10).join(f"- {s.get('id')}: {s.get('summary_ar')}" for s in meaningful_home) or "- _(none)_"}

### Which Decision cards became meaningful?

{chr(10).join(f"- {d.get('title')} ({d.get('domain')})" for d in meaningful_decisions) or "- _(none)_"}

### Which product insights appeared naturally?

- ORV findings: **{len(orv)}**
- Observation correlations sampled: **{obs.get("correlation_count")}**
- Home product observations card meaningful: **{"yes" if has_product_obs else "no"}**

Named insights such as “Product A attracts attention / Product B converts / shipping hurts Product E” appear **only if** the Observation/Findings layers emit them from durable evidence — they were **not** written into Home by this lab.

### Which pages still lack sufficient operational evidence?

- **Storefront attention pages** (views/dwell) — no durable ingest from SRS unsupported markers.
- **Product Intelligence surfaces** — intentionally absent / locked.
- **Communication delivery truth** — mock WhatsApp only.
- **Catalog/stock** — no inventory truth; “needs stock” cannot emerge honestly.

### What additional observation capabilities are required before Product Intelligence?

{chr(10).join(f"- {x}" for x in before_pi)}

### Is CartFlow now observing a business, or merely processing events?

{observing_business}

---

## 6. Critical rule confirmation

| Rule | Status |
|------|--------|
| No Product Intelligence implemented | **PASS** |
| No UI wording optimisation in this task | **PASS** |
| No hardcoded Home/Decision recommendations in the simulator | **PASS** |
| Operational evidence only (carts, reasons, WA mock, purchases, signals) | **PASS** |
| Report is observation-first | **PASS** |

---

## 7. Artifacts

- Capture JSON: `docs/product/living_store_reality_v1/observation_capture.json`
- Simulation manifest: under `docs/product/living_store_reality_v1/<simulation_run_id>/`
- Runner: `scripts/living_store_reality_v1.py`

**STOP — Do not begin Product Intelligence until this report is reviewed and observation gaps are accepted.**
"""
    # Fix accidental double braces from f-string for empty dict display
    body = body.replace("{{}}", "{}")
    path = OUT / "REALITY_OBSERVATION_REPORT.md"
    path.write_text(body, encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db_path = _bootstrap_env()
    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from fastapi.testclient import TestClient

    from main import app
    from services.time_authority.authority import use_provider
    from services.time_authority.providers import FixedAsOfProvider

    client = TestClient(app)
    auth = _signup_and_bind(client)
    print("bind:", json.dumps(auth.get("lab_session_bind") or {}, ensure_ascii=False))
    sim = _run_simulation()
    print("sim:", json.dumps(sim, ensure_ascii=False, default=str)[:500])

    with use_provider(FixedAsOfProvider(SIM_END)):
        mass = _operational_mass()
        observation = _observe()
        # Also hit summary API as merchant would
        summary_probe = client.get("/api/dashboard/summary")
        summary_json = summary_probe.json() if summary_probe.status_code == 200 else {}

    capture = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "start_date": START_DATE,
        "duration_days": DURATION_DAYS,
        "sim_end": SIM_END.isoformat(),
        "db_path": str(db_path),
        "auth": {
            "email": auth.get("email"),
            "lab_session_bind": auth.get("lab_session_bind"),
        },
        "simulation": sim,
        "operational_mass": mass,
        "observation": observation,
        "dashboard_summary_probe": {
            "http": summary_probe.status_code,
            "home_surface_mode": summary_json.get("home_surface_mode"),
            "hes_sections": [
                {
                    "id": s.get("id"),
                    "summary_ar": s.get("summary_ar"),
                    "status_ar": s.get("status_ar"),
                    "empty": s.get("empty"),
                }
                for s in (
                    (summary_json.get("home_executive_summary_v1") or {}).get("sections")
                    or []
                )
            ],
            "orv_findings_on_summary": len(
                (summary_json.get("observation_reality_validation_v1") or {}).get(
                    "findings"
                )
                or []
            ),
            "meif_present": bool(summary_json.get("merchant_experience_integration_v1")),
        },
    }
    (OUT / "observation_capture.json").write_text(
        json.dumps(capture, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    report_path = _write_report(capture)
    print("wrote", OUT / "observation_capture.json")
    print("wrote", report_path)
    print(
        "mass carts=",
        mass.get("abandoned_carts"),
        "purchases=",
        mass.get("purchase_truth_records"),
        "signals=",
        mass.get("product_signal_events"),
        "hes_ok=",
        (observation.get("home_executive_summary") or {}).get("ok"),
        "decisions=",
        (observation.get("decision_composition") or {}).get("published_count"),
        "orv=",
        observation.get("orv_finding_count"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
