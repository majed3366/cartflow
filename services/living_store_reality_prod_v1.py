# -*- coding: utf-8 -*-
"""
Living Store Reality — production demo seed + Home review session.

Runs the same SRS ``living_store`` profile against the **connected** database
(demo-only). Uses a trailing wall-clock calendar so production Home (no
FixedAsOf) can admit observations.

Also issues a review merchant whose ``primary_store_id`` is demo so
``/api/dashboard/summary`` resolves ``store_slug=demo``.
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG

log = logging.getLogger("cartflow.living_store_reality_prod_v1")

SEED = 20260725
DURATION_DAYS = 30

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

REVIEW_EMAIL = "cf.living.store.review@smartreplyai.net"

_JOB_LOCK = threading.Lock()
_JOB: dict[str, Any] = {
    "status": "idle",
    "ok": None,
    "error": None,
    "started_at_utc": None,
    "finished_at_utc": None,
    "simulation": None,
    "calendar": None,
    "observation": None,
}


def wall_clock_living_calendar_v1(
    *,
    now: Optional[datetime] = None,
    duration_days: int = DURATION_DAYS,
) -> dict[str, Any]:
    """Trailing window ending today so wall-clock Home can see the mass."""
    anchor = now or datetime.now(timezone.utc)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    end = anchor.astimezone(timezone.utc)
    start = (end - timedelta(days=int(duration_days) - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return {
        "start_date": start.date().isoformat(),
        "start_at": start,
        "sim_end": end,
        "duration_days": int(duration_days),
        "calendar_mode": "wall_clock_trailing",
        "note": (
            "Lab script used FixedAsOf May-2026; production Home uses wall clock, "
            "so prod seed must land inside the trailing window."
        ),
    }


def living_store_prod_job_status_v1() -> dict[str, Any]:
    with _JOB_LOCK:
        return dict(_JOB)


def _set_job(**fields: Any) -> None:
    with _JOB_LOCK:
        _JOB.update(fields)


def _observe_demo_wall_clock() -> dict[str, Any]:
    from services.home_executive_summary_v1.compose_v1 import (  # noqa: PLC0415
        build_home_executive_summary_v1,
    )
    from services.home_executive_summary_v1.slim_transport_v1 import (  # noqa: PLC0415
        extract_home_teaser_inputs_v1,
    )
    from services.observation_foundation_v1.assemble_v1 import (  # noqa: PLC0415
        assemble_observation_foundation_v1,
    )
    from services.observation_foundation_v1.merchant_findings_v1 import (  # noqa: PLC0415
        build_observation_reality_validation_v1,
    )

    obs = assemble_observation_foundation_v1(DEMO_STORE_SLUG)
    orv = build_observation_reality_validation_v1(DEMO_STORE_SLUG)
    summary_like = {
        "store_slug": DEMO_STORE_SLUG,
        "observation_reality_validation_v1": orv if isinstance(orv, dict) else {},
    }
    teasers = extract_home_teaser_inputs_v1(summary_like)
    hes = build_home_executive_summary_v1(
        {**summary_like, "home_teaser_inputs_v1": teasers}
    )
    findings = []
    for f in (orv.get("findings") or []) if isinstance(orv, dict) else []:
        if not isinstance(f, dict):
            continue
        findings.append(
            {
                "capability": f.get("capability_id") or f.get("capability"),
                "title_ar": f.get("title_ar"),
                "statement_ar": f.get("statement_ar"),
                "product_name": f.get("product_name_ar")
                or f.get("product_name")
                or f.get("entity_name"),
            }
        )
    obs_section = None
    for s in (hes.get("sections") or []) if isinstance(hes, dict) else []:
        if isinstance(s, dict) and s.get("id") == "observations":
            obs_section = {
                "summary_ar": s.get("summary_ar"),
                "count": s.get("count"),
                "empty": s.get("empty"),
            }
            break
    return {
        "store_slug": DEMO_STORE_SLUG,
        "foundation_ready": (
            obs.get("statement_capabilities_ready") if isinstance(obs, dict) else []
        ),
        "orv_count": len(findings),
        "present_capabilities": (
            orv.get("present_capabilities") if isinstance(orv, dict) else []
        ),
        "admission_reconciliation": (
            orv.get("admission_reconciliation") if isinstance(orv, dict) else {}
        ),
        "findings": findings,
        "hes_observations": obs_section,
        "mass_source": orv.get("mass_source") if isinstance(orv, dict) else None,
        "clock": "wall_clock",
    }


def _execute_living_store_simulation(*, calendar: dict[str, Any]) -> dict[str, Any]:
    from services.identity_authority.lab_session_bind_v1 import (  # noqa: PLC0415
        ensure_demo_store_for_lab,
    )
    from services.store_reality_simulator.config_loader_v1 import (  # noqa: PLC0415
        load_simulation_config,
    )
    from services.store_reality_simulator.event_ledger_v1 import (  # noqa: PLC0415
        persist_plan_to_ledger,
    )
    from services.store_reality_simulator.manifest_v1 import (  # noqa: PLC0415
        build_simulation_manifest,
    )
    from services.store_reality_simulator.performance_guards_v1 import (  # noqa: PLC0415
        PerformanceThresholds,
    )
    from services.store_reality_simulator.planner_v1 import (  # noqa: PLC0415
        build_reality_plan,
    )
    from services.store_reality_simulator.reality_engine_v1 import (  # noqa: PLC0415
        execute_reality_run,
    )
    from services.store_reality_simulator.reality_score_v1 import (  # noqa: PLC0415
        compute_reality_score,
    )
    from services.store_reality_simulator.run_registry_v1 import (  # noqa: PLC0415
        create_simulation_run,
        persist_run,
    )
    from services.store_reality_simulator.scale_profiles_v1 import (  # noqa: PLC0415
        get_scale_profile,
    )

    ensure_demo_store_for_lab()
    profile = get_scale_profile("living_store")
    start_at: datetime = calendar["start_at"]
    cfg = load_simulation_config(
        {
            "store_slug": DEMO_STORE_SLUG,
            "scenario_ids": LIVING_SCENARIOS,
            "seed": SEED,
            "start_date": calendar["start_date"],
            "duration_days": int(calendar["duration_days"]),
            "scale": 1.0,
            "mode": "execute",
            "batch_size": profile.batch_size,
            "max_events_per_job": profile.max_events_per_run,
            "metadata": {
                "lab": "living_store_reality_prod_v1",
                "scale_profile": "living_store",
                "purpose": "production_demo_home_verification",
                "calendar_mode": calendar.get("calendar_mode"),
            },
        }
    )
    row = create_simulation_run(cfg)
    run_id = row.simulation_run_id
    plan = build_reality_plan(
        simulation_run_id=run_id,
        seed=SEED,
        start_date=start_at,
        duration_days=int(calendar["duration_days"]),
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
    result = execute_reality_run(
        run_id,
        max_batches=120,
        thresholds=PerformanceThresholds(batch_wall_ms_max=600_000.0),
    )
    return {
        "simulation_run_id": run_id,
        "reality_score_overall": (score or {}).get("overall"),
        "execute": {
            "status": result.get("status"),
            "events_executed": result.get("events_executed"),
            "batches": result.get("batches"),
        },
        "plan_event_count": len(getattr(plan, "events", []) or []),
        "store_slug": DEMO_STORE_SLUG,
    }


def _job_worker() -> None:
    started = datetime.now(timezone.utc).isoformat()
    calendar = wall_clock_living_calendar_v1()
    _set_job(
        status="running",
        ok=None,
        error=None,
        started_at_utc=started,
        finished_at_utc=None,
        simulation=None,
        calendar={
            "start_date": calendar["start_date"],
            "sim_end": calendar["sim_end"].isoformat(),
            "duration_days": calendar["duration_days"],
            "calendar_mode": calendar["calendar_mode"],
            "note": calendar["note"],
        },
        observation=None,
    )
    try:
        sim = _execute_living_store_simulation(calendar=calendar)
        _set_job(simulation=sim, status="observing")
        observation = _observe_demo_wall_clock()
        _set_job(
            status="completed",
            ok=True,
            observation=observation,
            finished_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        log.info(
            "living_store_prod_v1 completed run_id=%s orv_count=%s",
            (sim or {}).get("simulation_run_id"),
            (observation or {}).get("orv_count"),
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("living_store_prod_v1 failed: %s", exc)
        _set_job(
            status="failed",
            ok=False,
            error=f"{type(exc).__name__}:{exc}"[:500],
            finished_at_utc=datetime.now(timezone.utc).isoformat(),
        )


def start_living_store_prod_run_v1() -> dict[str, Any]:
    """Start async Living Store execute against connected DB (demo only)."""
    with _JOB_LOCK:
        st = str(_JOB.get("status") or "idle")
        if st in ("starting", "running", "observing"):
            return {
                "ok": False,
                "error": "already_running",
                "job": dict(_JOB),
            }
        _JOB.update(
            {
                "status": "starting",
                "ok": None,
                "error": None,
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "finished_at_utc": None,
                "simulation": None,
                "calendar": None,
                "observation": None,
            }
        )
    thread = threading.Thread(
        target=_job_worker,
        name="living-store-reality-prod-v1",
        daemon=True,
    )
    thread.start()
    return {
        "ok": True,
        "accepted": True,
        "store_slug": DEMO_STORE_SLUG,
        "environment": "connected_database",
        "job": living_store_prod_job_status_v1(),
    }


def issue_demo_home_review_session_v1() -> dict[str, Any]:
    """
    Merchant session whose primary store is ``demo``.

    Lab bind keeps signup primary ≠ demo; Home auth reads primary only.
    This review principal is intentionally primary=demo for CEO verification.
    """
    from extensions import db
    from models import MerchantUser, Store
    from services.identity_authority.lab_session_bind_v1 import (  # noqa: PLC0415
        ensure_demo_store_for_lab,
    )
    from services.merchant_auth_http import (  # noqa: PLC0415
        merchant_cookie_name,
    )
    from services.merchant_auth_v1 import (  # noqa: PLC0415
        hash_password,
        session_cookie_value_for_user,
    )

    demo = ensure_demo_store_for_lab()
    demo_pk = int(demo.id)
    password = f"LivingReview!{secrets.token_hex(4)}"
    user = db.session.query(MerchantUser).filter_by(email=REVIEW_EMAIL).first()
    created = False
    if user is None:
        user = MerchantUser(
            email=REVIEW_EMAIL,
            password_hash=hash_password(password),
            merchant_name="Living Store Review",
            primary_store_id=demo_pk,
        )
        db.session.add(user)
        created = True
    else:
        user.password_hash = hash_password(password)
        user.merchant_name = user.merchant_name or "Living Store Review"
        user.primary_store_id = demo_pk
        db.session.add(user)

    db.session.commit()
    db.session.refresh(user)

    demo_row = db.session.query(Store).filter(Store.id == demo_pk).first()
    if demo_row is None:
        raise RuntimeError("demo_store_missing_after_ensure")
    demo_row.merchant_user_id = int(user.id)
    db.session.add(demo_row)
    db.session.commit()
    db.session.refresh(user)
    db.session.refresh(demo_row)

    if int(user.primary_store_id or 0) != demo_pk:
        raise RuntimeError("primary_store_id_not_demo")
    if str(getattr(demo_row, "zid_store_id", "") or "") != DEMO_STORE_SLUG:
        raise RuntimeError("demo_slug_mismatch")

    cookie_value = session_cookie_value_for_user(user)
    return {
        "ok": True,
        "store_slug": DEMO_STORE_SLUG,
        "canonical_store_id": str(demo_pk),
        "merchant_user_id": int(user.id),
        "email": REVIEW_EMAIL,
        "password_once": password,
        "user_created": created,
        "cookie_name": merchant_cookie_name(),
        "cookie_value": cookie_value,
        "dashboard_url": "/dashboard#home",
        "source": "living_store_reality_prod_v1",
        "note": (
            "primary_store_id=demo so resolve_authenticated_store_slug → demo. "
            "Distinct from lab_session_bind (membership alongside signup primary)."
        ),
    }


__all__ = [
    "DURATION_DAYS",
    "LIVING_SCENARIOS",
    "REVIEW_EMAIL",
    "SEED",
    "issue_demo_home_review_session_v1",
    "living_store_prod_job_status_v1",
    "start_living_store_prod_run_v1",
    "wall_clock_living_calendar_v1",
]
