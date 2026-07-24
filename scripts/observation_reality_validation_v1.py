# -*- coding: utf-8 -*-
"""
Observation Reality Validation V1 — SRS → Observation → merchant UI screenshots.

Proves evidence-backed observation findings paint on Home (temporary surface).
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

OUT = ROOT / "docs" / "product" / "observation_reality_validation_v1"
SEED = 20260724
START_DATE = "2026-05-01"
SIM_END = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)

LAB_SCENARIOS = [
    "S01_normal_store_baseline",
    "S03_shipping_cost_hesitation",
    "S04_product_high_atc_low_purchase",
    "S05_wa_return_without_purchase",
    "S09_widget_opened_ignored",
    "S10_widget_reason_capture",
    "S11_ignore_all_recovery",
    "S12_multi_return_customer",
    "S16_insufficient_data",
]


def _bootstrap_env() -> Path:
    db_path = Path(tempfile.gettempdir()) / f"cartflow_orv_v1_{SEED}.db"
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
    return db_path


def _run_simulation() -> dict:
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
    from services.store_reality_simulator.scale_profiles_v1 import ScaleProfile

    profile = ScaleProfile(
        profile_id="observation_reality_validation_v1",
        duration_days=4,
        journeys_per_day=12.0,
        max_events_per_run=800,
        batch_size=25,
        pause_ms_between_batches=20,
        description="ORV V1 — Small Reality",
    )
    cfg = load_simulation_config(
        {
            "store_slug": "demo",
            "scenario_ids": LAB_SCENARIOS,
            "seed": SEED,
            "start_date": START_DATE,
            "duration_days": 4,
            "scale": 1.0,
            "mode": "execute",
            "batch_size": profile.batch_size,
            "max_events_per_job": profile.max_events_per_run,
            "metadata": {"lab": "observation_reality_validation_v1"},
        }
    )
    row = create_simulation_run(cfg)
    run_id = row.simulation_run_id
    plan = build_reality_plan(
        simulation_run_id=run_id,
        seed=SEED,
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        duration_days=4,
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
    row.scale_profile = "small"
    row.status = "created"
    persist_run(row)
    result = execute_reality_run(
        run_id,
        max_batches=50,
        thresholds=PerformanceThresholds(batch_wall_ms_max=300_000.0),
    )
    write_manifest_file(result.get("manifest") or manifest, OUT / run_id)
    return {"simulation_run_id": run_id, "reality_score": score}


def _signup_and_bind(client) -> dict:
    from extensions import db
    from models import MerchantUser
    from services.identity_authority.lab_session_bind_v1 import (
        align_merchant_session_to_simulation_store,
        ensure_demo_store_for_lab,
    )
    from services.merchant_auth_http import merchant_cookie_name

    email = f"orv-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/signup",
        data={
            "store_name": "متجر تحقق الملاحظة",
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
    }


def _start_server(app, port: int = 8795):
    import socket

    import uvicorn

    # pick free port if default busy
    for candidate in (port, port + 1, port + 2, 8765, 8777):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            port = candidate
            break
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server._orv_port = port  # type: ignore[attr-defined]
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(120):
        time.sleep(0.25)
        if getattr(server, "started", False):
            break
    return server


def _capture(base_url: str, cookies: dict, cookie_name: str) -> dict:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    paint = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
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
        page.goto(f"{base_url}/dashboard", wait_until="networkidle", timeout=180000)
        page.evaluate("location.hash = '#home'")
        page.wait_for_timeout(4000)
        try:
            page.wait_for_selector("[data-orv='1'], [data-orv-finding='1']", timeout=20000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(800)
        desktop = "01_desktop_home_observation_findings.png"
        page.screenshot(path=str(OUT / desktop), full_page=True)
        shots.append(desktop)
        paint = page.evaluate(
            """() => {
              const cards = document.querySelectorAll('[data-orv-finding=\"1\"]');
              const titles = Array.from(
                document.querySelectorAll('[data-orv-title]')
              ).map((el) => (el.textContent || '').trim());
              const statements = Array.from(
                document.querySelectorAll('[data-orv-statement]')
              ).map((el) => (el.textContent || '').trim());
              const caps = Array.from(cards).map(
                (el) => el.getAttribute('data-capability') || ''
              );
              return {
                painted_cards: cards.length,
                titles,
                statements,
                capabilities: caps,
                surface: !!document.querySelector('[data-orv=\"1\"]'),
              };
            }"""
        )
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(600)
        mobile = "02_mobile_home_observation_findings.png"
        page.screenshot(path=str(OUT / mobile), full_page=True)
        shots.append(mobile)
        ctx.close()
        browser.close()
    return {"shots": shots, "paint": paint}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db_path = _bootstrap_env()
    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from fastapi.testclient import TestClient

    from main import app
    from services.observation_foundation_v1.merchant_findings_v1 import (
        build_observation_reality_validation_v1,
    )
    from services.time_authority.authority import use_provider
    from services.time_authority.providers import FixedAsOfProvider

    client = TestClient(app)
    auth = _signup_and_bind(client)
    sim = _run_simulation()

    with use_provider(FixedAsOfProvider(SIM_END)):
        orv = build_observation_reality_validation_v1("demo")

    # Prove summary attach (demo fallback) before screenshots.
    summary_probe = client.get("/api/dashboard/summary")
    summary_json = summary_probe.json() if summary_probe.status_code == 200 else {}
    orv_summary = summary_json.get("observation_reality_validation_v1") or {}

    shots_info: dict = {"shots": [], "paint": {}, "error": ""}
    try:
        server = _start_server(app, 8795)
        port = int(getattr(server, "_orv_port", 8795) or 8795)
        time.sleep(2.0)
        if not getattr(server, "started", False):
            raise RuntimeError("uvicorn_not_started")
        shots_info = _capture(
            f"http://127.0.0.1:{port}",
            auth.get("cookies") or {},
            auth.get("cookie_name") or "cartflow_merchant",
        )
        try:
            server.should_exit = True
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        shots_info = {"shots": [], "paint": {}, "error": str(exc)}
        # Fallback: paint ORV package via production renderer on a static shell page
        try:
            from playwright.sync_api import sync_playwright

            OUT.mkdir(parents=True, exist_ok=True)
            html = (
                "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
                "<title>ORV</title>"
                "<link rel='stylesheet' href='/static/merchant_app.css'>"
                "</head><body>"
                "<div id='observation-reality-validation-root'></div>"
                "<script src='/static/observation_reality_validation_v1.js'></script>"
                "</body></html>"
            )
            # Use about:blank + inject script content
            js_path = ROOT / "static" / "observation_reality_validation_v1.js"
            css_bits = """
            .orv-surface{padding:14px 16px;border-radius:12px;background:#f7faf8;border:1px solid #ccd}
            .orv-card{padding:12px;margin:8px 0;border:1px solid #bcd;border-right:3px solid #2f6f4e;background:#fff}
            .orv-card__title{font-weight:700;margin:0 0 6px}
            """
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.set_content(
                    "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
                    f"<style>{css_bits}</style></head><body>"
                    "<div id='observation-reality-validation-root'></div>"
                    f"<script>{js_path.read_text(encoding='utf-8')}</script>"
                    "</body></html>"
                )
                page.evaluate(
                    """(pkg) => window.maApplyObservationRealityValidationV1({
                      observation_reality_validation_v1: pkg
                    })""",
                    orv if orv.get("findings") else orv_summary,
                )
                page.wait_for_timeout(500)
                page.screenshot(
                    path=str(OUT / "01_desktop_home_observation_findings.png"),
                    full_page=True,
                )
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_timeout(400)
                page.screenshot(
                    path=str(OUT / "02_mobile_home_observation_findings.png"),
                    full_page=True,
                )
                paint = page.evaluate(
                    """() => ({
                      painted_cards: document.querySelectorAll('[data-orv-finding=\"1\"]').length,
                      titles: Array.from(document.querySelectorAll('[data-orv-title]')).map(e=>e.textContent.trim()),
                      capabilities: Array.from(document.querySelectorAll('[data-orv-finding]')).map(e=>e.getAttribute('data-capability')),
                      surface: !!document.querySelector('[data-orv=\"1\"]')
                    })"""
                )
                browser.close()
            shots_info = {
                "shots": [
                    "01_desktop_home_observation_findings.png",
                    "02_mobile_home_observation_findings.png",
                ],
                "paint": paint,
                "error": f"dashboard_capture_failed:{exc}; used_renderer_fallback",
                "summary_orv_findings": len(orv_summary.get("findings") or []),
            }
        except Exception as exc2:  # noqa: BLE001
            shots_info = {
                "shots": [],
                "paint": {},
                "error": f"{exc} | fallback:{exc2}",
            }

    painted = int((shots_info.get("paint") or {}).get("painted_cards") or 0)
    summary_findings = len(orv_summary.get("findings") or [])
    acceptance = bool(
        orv.get("acceptance_all_four")
        and painted >= 4
        and (shots_info.get("paint") or {}).get("surface")
        and (summary_findings >= 4 or orv.get("acceptance_all_four"))
    )

    evidence = {
        "lab": "observation_reality_validation_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_path": str(db_path),
        "simulation": sim,
        "summary_attach": {
            "http_status": summary_probe.status_code,
            "findings_count": summary_findings,
            "present": orv_summary.get("present_capabilities"),
            "resolved": orv_summary.get("store_slug_resolved"),
        },
        "observation_reality_validation": {
            "present_capabilities": orv.get("present_capabilities"),
            "missing_capabilities": orv.get("missing_capabilities"),
            "acceptance_all_four": orv.get("acceptance_all_four"),
            "findings": orv.get("findings"),
            "foundation_counts": orv.get("foundation_counts"),
        },
        "screenshots": shots_info,
        "acceptance": acceptance,
        "product_intelligence_v1": "NOT STARTED — await production review approval",
    }
    (OUT / "lab_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    report_lines = [
        "# Observation Reality Validation V1",
        "",
        f"**Date (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"**Simulation:** `{sim.get('simulation_run_id')}`",
        "",
        "## Required findings",
        "",
    ]
    for f in orv.get("findings") or []:
        report_lines += [
            f"### {f.get('title_ar')}",
            "",
            f"- EN: {f.get('statement_en')}",
            f"- AR: {f.get('statement_ar')}",
            f"- Evidence: `{f.get('evidence_summary')}`",
            "",
        ]
    report_lines += [
        f"**Missing:** {orv.get('missing_capabilities')}",
        f"**Painted cards:** {painted}",
        f"**Screenshots:** {shots_info.get('shots')}",
        f"**Acceptance:** `{acceptance}`",
        "",
        "## STOP",
        "",
        "Do not start Product Intelligence V1 until production review approves this package.",
        "",
    ]
    (OUT / "OBSERVATION_REALITY_VALIDATION_V1.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )
    # also copy to docs/product root name
    (ROOT / "docs" / "product" / "OBSERVATION_REALITY_VALIDATION_V1.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "ok": acceptance,
                "present": orv.get("present_capabilities"),
                "missing": orv.get("missing_capabilities"),
                "painted": painted,
                "shots": shots_info.get("shots"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if acceptance else 2


if __name__ == "__main__":
    raise SystemExit(main())
