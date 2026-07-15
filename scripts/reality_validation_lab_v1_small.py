# -*- coding: utf-8 -*-
"""
Reality Validation Lab V1 — Small Reality (3-day) controlled product validation.

Runs Store Reality Simulator against demo only. Collects merchant-surface
evidence. Does NOT change product logic.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "architecture" / "reality_validation_lab_v1_small"
SEED = 20260715
START_DATE = "2026-05-01"

LAB_SCENARIOS = [
    "S01_normal_store_baseline",
    "S03_shipping_cost_hesitation",
    "S04_product_high_atc_low_purchase",
    "S05_wa_return_without_purchase",
    "S06_wa_success",
    "S09_widget_opened_ignored",
    "S10_widget_reason_capture",
    "S11_ignore_all_recovery",
    "S12_multi_return_customer",
    "S13_organic_purchase",
    "S14_ambiguous_influence",
    "S15_vip_customer",
    "S16_insufficient_data",
]


def _bootstrap_env() -> Path:
    db_path = Path(tempfile.gettempdir()) / f"cartflow_reality_lab_v1_{SEED}.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass
    os.environ["DATABASE_URL"] = "sqlite:///" + str(db_path).replace("\\", "/")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")
    return db_path


def _lab_scale_profile():
    from services.store_reality_simulator.scale_profiles_v1 import ScaleProfile

    # ~24–30 journeys over 3 days (lab store size), still “Small Reality”
    return ScaleProfile(
        profile_id="small_reality_lab_v1",
        duration_days=3,
        journeys_per_day=9.0,
        max_events_per_run=500,
        batch_size=25,
        pause_ms_between_batches=20,
        description="Reality Validation Lab V1 — Small Reality (3 days)",
    )


def _run_simulation(app) -> dict:
    from extensions import db
    from models import Store
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
        require_run,
    )
    from services.store_reality_simulator.schema_v1 import ensure_srs_phase3_schema

    ensure_srs_phase3_schema()
    if db.session.query(Store).filter_by(zid_store_id="demo").first() is None:
        db.session.add(
            Store(
                zid_store_id="demo",
                is_active=True,
                whatsapp_recovery_enabled=False,
                recovery_delay=1,
                recovery_delay_unit="minutes",
                recovery_attempts=2,
            )
        )
        db.session.commit()

    profile = _lab_scale_profile()
    cfg = load_simulation_config(
        {
            "store_slug": "demo",
            "scenario_ids": LAB_SCENARIOS,
            "seed": SEED,
            "start_date": START_DATE,
            "duration_days": 3,
            "scale": 1.0,
            "mode": "execute",
            "batch_size": profile.batch_size,
            "max_events_per_job": profile.max_events_per_run,
            "metadata": {
                "lab": "reality_validation_lab_v1",
                "lab_profile": "small_reality_lab_v1",
            },
        }
    )
    row = create_simulation_run(cfg)
    run_id = row.simulation_run_id
    start_dt = datetime(2026, 5, 1, tzinfo=timezone.utc)
    t0 = time.perf_counter()
    plan = build_reality_plan(
        simulation_run_id=run_id,
        seed=SEED,
        start_date=start_dt,
        duration_days=3,
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
    # Registry key must be a known progressive profile (batch/pause only);
    # journey volume already materialised in the cold ledger via lab ScaleProfile.
    row.scale_profile = "small"
    row.status = "created"
    persist_run(row)

    result = execute_reality_run(
        run_id,
        max_batches=40,
        thresholds=PerformanceThresholds(batch_wall_ms_max=300_000.0),
    )
    elapsed = (time.perf_counter() - t0) * 1000.0
    write_manifest_file(result.get("manifest") or manifest, OUT / run_id)
    return {
        "simulation_run_id": run_id,
        "plan_summary": plan.to_summary(),
        "reality_score": result.get("reality_score") or score,
        "manifest": result.get("manifest") or manifest,
        "execute": {
            "status": result.get("status"),
            "pause_reason": result.get("pause_reason"),
            "batches_done": result.get("batches_done"),
            "accounting": result.get("accounting"),
            "performance": result.get("performance"),
            "validation_report": result.get("validation_report"),
        },
        "wall_ms": elapsed,
        "profile": profile.to_dict(),
    }


def _collect_platform_evidence(client, cookies) -> dict:
    from extensions import db
    from models import (
        AbandonedCart,
        CartRecoveryLog,
        CartRecoveryReason,
        MovementSnapshot,
        PurchaseTruthRecord,
        RecoverySchedule,
        RecoveryTruthTimelineEvent,
        Store,
    )

    demo = db.session.query(Store).filter_by(zid_store_id="demo").first()
    store_id = int(demo.id) if demo else None

    def _get(path: str) -> dict:
        r = client.get(path, cookies=cookies)
        try:
            body = r.json()
        except Exception:
            body = {"_raw_status": r.status_code, "_text": (r.text or "")[:2000]}
        return {"status": r.status_code, "body": body}

    summary = _get("/api/dashboard/summary")
    carts = _get("/api/dashboard/normal-carts")
    vip = _get("/api/dashboard/vip-carts")
    followups = _get("/api/dashboard/followups")

    knowledge = {}
    try:
        from services.knowledge_layer_v1 import build_knowledge_report

        report = build_knowledge_report(db.session, "demo", window_days=7)
        knowledge = report.to_dict() if hasattr(report, "to_dict") else {"raw": str(report)[:2000]}
    except Exception as exc:  # noqa: BLE001
        knowledge = {"error": str(exc)[:400]}

    home = {}
    try:
        from services.merchant_home_composition_v1 import (
            build_merchant_home_experience_api_payload,
        )

        home = build_merchant_home_experience_api_payload(
            db.session, "demo", demo, merchant_name_ar="متجر واقع صغير"
        )
    except Exception as exc:  # noqa: BLE001
        home = {"error": str(exc)[:400]}

    monthly = {}
    try:
        from services.dashboard_snapshot_v1 import SNAPSHOT_TYPE_MONTHLY_SUMMARY
        from models import DashboardSnapshot

        snap = (
            db.session.query(DashboardSnapshot)
            .filter(
                DashboardSnapshot.store_slug == "demo",
                DashboardSnapshot.snapshot_type == SNAPSHOT_TYPE_MONTHLY_SUMMARY,
            )
            .order_by(DashboardSnapshot.id.desc())
            .first()
        )
        if snap is not None:
            monthly = {
                "id": snap.id,
                "created_at": str(getattr(snap, "created_at", None)),
                "payload_preview": (snap.payload_json or "")[:4000],
            }
        else:
            monthly = {"present": False, "note": "no_monthly_summary_snapshot_row"}
    except Exception as exc:  # noqa: BLE001
        monthly = {"error": str(exc)[:400]}

    carts_q = db.session.query(AbandonedCart)
    if store_id is not None:
        carts_q = carts_q.filter(AbandonedCart.store_id == store_id)
    abandoned = carts_q.count()
    purchases = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.store_slug == "demo")
        .count()
    )
    schedules = (
        db.session.query(RecoverySchedule)
        .filter(RecoverySchedule.store_slug == "demo")
        .count()
    )
    reasons = (
        db.session.query(CartRecoveryReason)
        .filter(CartRecoveryReason.store_slug == "demo")
        .count()
    )
    mock_wa = (
        db.session.query(CartRecoveryLog)
        .filter(
            CartRecoveryLog.store_slug == "demo",
            CartRecoveryLog.status == "mock_sent",
        )
        .count()
    )
    movements = (
        db.session.query(MovementSnapshot)
        .filter(MovementSnapshot.store_slug == "demo")
        .count()
    )
    timeline = (
        db.session.query(RecoveryTruthTimelineEvent)
        .filter(RecoveryTruthTimelineEvent.store_slug == "demo")
        .count()
    )

    # Sample rows for trust review
    pt_samples = [
        {
            "recovery_key": r.recovery_key,
            "store_slug": r.store_slug,
            "source": r.purchase_source,
            "evidence": r.evidence_detail,
            "purchase_time": str(r.purchase_time),
        }
        for r in db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.store_slug == "demo")
        .limit(8)
        .all()
    ]
    reason_dist: dict[str, int] = {}
    for r in (
        db.session.query(CartRecoveryReason)
        .filter(CartRecoveryReason.store_slug == "demo")
        .all()
    ):
        tag = (r.reason or "other").strip() or "other"
        reason_dist[tag] = reason_dist.get(tag, 0) + 1

    return {
        "api": {
            "summary": summary,
            "normal_carts": carts,
            "vip_carts": vip,
            "followups": followups,
        },
        "composed": {"knowledge": knowledge, "home": home, "monthly": monthly},
        "counts": {
            "abandoned_carts": abandoned,
            "purchase_truth_demo": purchases,
            "recovery_schedules": schedules,
            "reasons": reasons,
            "mock_whatsapp_logs": mock_wa,
            "movement_snapshots": movements,
            "timeline_events": timeline,
        },
        "samples": {"purchases": pt_samples, "reason_distribution": reason_dist},
    }


def _signup_and_bind_demo(client) -> dict:
    from extensions import db
    from models import MerchantUser, Store
    from services.merchant_auth_http import merchant_cookie_name

    email = f"reality-lab-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/signup",
        data={
            "store_name": "متجر واقع صغير",
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    cookies = dict(r.cookies)
    # Ensure merchant owns demo for dashboard scoping where possible
    user = db.session.query(MerchantUser).filter_by(email=email).first()
    demo = db.session.query(Store).filter_by(zid_store_id="demo").first()
    if user is not None and demo is not None:
        try:
            if hasattr(user, "store_id"):
                user.store_id = demo.id
            if hasattr(demo, "merchant_user_id"):
                demo.merchant_user_id = user.id
            db.session.add(user)
            db.session.add(demo)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    return {
        "email": email,
        "signup_status": r.status_code,
        "cookie_name": merchant_cookie_name(),
        "cookies": cookies,
    }


def _capture_screenshots(base_url: str, cookies: dict, cookie_name: str) -> list[str]:
    shots: list[str] = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return shots

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, viewport, filename in (
            ("desktop", {"width": 1440, "height": 900}, "01_desktop_home.png"),
            ("mobile", {"width": 390, "height": 844}, "02_mobile_home.png"),
        ):
            ctx = browser.new_context(viewport=viewport)
            if cookies:
                ctx.add_cookies(
                    [
                        {
                            "name": cookie_name,
                            "value": cookies.get(cookie_name, ""),
                            "url": base_url,
                        }
                    ]
                )
            page = ctx.new_page()
            page.goto(f"{base_url}/dashboard", wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(1200)
            # Prefer Home hash if present
            try:
                page.evaluate("location.hash = '#home'")
                page.wait_for_timeout(800)
            except Exception:  # noqa: BLE001
                pass
            path = OUT / filename
            page.screenshot(path=str(path), full_page=True)
            shots.append(filename)

            # Cart workspace
            try:
                page.evaluate("location.hash = '#carts'")
                page.wait_for_timeout(1000)
                cname = filename.replace("home", "carts")
                page.screenshot(path=str(OUT / cname), full_page=True)
                shots.append(cname)
            except Exception:  # noqa: BLE001
                pass
            ctx.close()
        browser.close()
    return shots


def _start_server(app, port: int = 8765):
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(60):
        time.sleep(0.25)
        if getattr(server, "started", False):
            break
    return server


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db_path = _bootstrap_env()

    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    auth = _signup_and_bind_demo(client)
    sim = _run_simulation(app)
    evidence = _collect_platform_evidence(client, auth.get("cookies") or {})

    shots: list[str] = []
    try:
        server = _start_server(app, 8765)
        time.sleep(1.5)
        shots = _capture_screenshots(
            "http://127.0.0.1:8765",
            auth.get("cookies") or {},
            auth.get("cookie_name") or "cartflow_merchant",
        )
        server.should_exit = True
    except Exception as exc:  # noqa: BLE001
        shots = []
        (OUT / "screenshot_error.txt").write_text(str(exc), encoding="utf-8")

    bundle = {
        "lab": "reality_validation_lab_v1",
        "profile": "Small Reality",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "auth": {k: v for k, v in auth.items() if k != "cookies"},
        "simulation": sim,
        "evidence": evidence,
        "screenshots": shots,
    }
    (OUT / "lab_evidence.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "run_id": sim["simulation_run_id"], "out": str(OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
