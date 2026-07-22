# -*- coding: utf-8 -*-
"""
Merchant Experience Binding V1 — prove Home paints a real Business Finding.

Historical SRS demo → BFL materialize (no fixtures) → MEIF bind → screenshot.
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

OUT = ROOT / "docs" / "architecture" / "merchant_experience_binding_v1"
SEED = 20260722
START_DATE = "2026-05-01"
SIM_END = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)

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
    db_path = Path(tempfile.gettempdir()) / f"cartflow_mebf_v1_{SEED}.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass
    os.environ["DATABASE_URL"] = "sqlite:///" + str(db_path).replace("\\", "/")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")
    os.environ.setdefault("CARTFLOW_BUSINESS_FINDINGS_LIFECYCLE_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_EXPERIENCE_BINDING_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1", "1")
    os.environ.setdefault("CARTFLOW_SURFACE_COMPOSITION_V1", "1")
    os.environ.setdefault("CARTFLOW_OPERATIONAL_TRUTH_V1", "1")
    os.environ.setdefault("CARTFLOW_KNOWLEDGE_FOUNDATION_V1", "1")
    return db_path


def _run_simulation() -> dict:
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
    )
    from services.store_reality_simulator.schema_v1 import ensure_srs_phase3_schema
    from services.store_reality_simulator.scale_profiles_v1 import ScaleProfile

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

    profile = ScaleProfile(
        profile_id="merchant_experience_binding_v1",
        duration_days=3,
        journeys_per_day=9.0,
        max_events_per_run=500,
        batch_size=25,
        pause_ms_between_batches=20,
        description="MEBF V1 — Small Reality",
    )
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
            "metadata": {"lab": "merchant_experience_binding_v1"},
        }
    )
    row = create_simulation_run(cfg)
    run_id = row.simulation_run_id
    plan = build_reality_plan(
        simulation_run_id=run_id,
        seed=SEED,
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
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
    row.scale_profile = "small"
    row.status = "created"
    persist_run(row)
    result = execute_reality_run(
        run_id,
        max_batches=40,
        thresholds=PerformanceThresholds(batch_wall_ms_max=300_000.0),
    )
    write_manifest_file(result.get("manifest") or manifest, OUT / run_id)
    return {"simulation_run_id": run_id, "reality_score": score}


def _signup_and_bind(client) -> dict:
    from extensions import db
    from models import MerchantUser
    from services.merchant_auth_http import merchant_cookie_name
    from services.identity_authority.lab_session_bind_v1 import (
        align_merchant_session_to_simulation_store,
        ensure_demo_store_for_lab,
    )

    email = f"mebf-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/signup",
        data={
            "store_name": "متجر ربط التجربة",
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    cookies = dict(r.cookies)
    bind = {"ok": False}
    try:
        ensure_demo_store_for_lab()
        user = db.session.query(MerchantUser).filter_by(email=email).first()
        if user is not None:
            bind = align_merchant_session_to_simulation_store(
                merchant_user_id=int(user.id)
            )
    except Exception as exc:  # noqa: BLE001
        bind = {"ok": False, "error": str(exc)}
    return {
        "email": email,
        "cookies": cookies,
        "cookie_name": merchant_cookie_name(),
        "lab_session_bind": bind,
    }


def _start_server(app, port: int = 8781):
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(80):
        time.sleep(0.25)
        if getattr(server, "started", False):
            break
    return server


def _capture_home(base_url: str, cookies: dict, cookie_name: str) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "playwright_not_installed", "shots": []}

    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    diag = {}
    painted = 0
    titles = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
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
        page.goto(f"{base_url}/dashboard", wait_until="networkidle", timeout=120000)
        page.evaluate("location.hash = '#home'")
        page.wait_for_timeout(3500)
        # Wait for finding card or timeout
        try:
            page.wait_for_selector("[data-mebf-title], [data-finding-id]", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(1000)
        fname = "01_desktop_home_business_finding.png"
        page.screenshot(path=str(OUT / fname), full_page=True)
        shots.append(fname)
        painted = page.locator("[data-mebf='1'][data-finding-id]").count()
        titles = page.locator("[data-mebf-title]").all_text_contents()
        diag = page.evaluate("() => window.__mebfRenderDiagnostics || {}")
        # mobile
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        mname = "02_mobile_home_business_finding.png"
        page.screenshot(path=str(OUT / mname), full_page=True)
        shots.append(mname)
        ctx.close()
        browser.close()
    return {
        "shots": shots,
        "painted_finding_cards": painted,
        "titles": titles,
        "render_diagnostics": diag,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db_path = _bootstrap_env()
    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from main import app
    from fastapi.testclient import TestClient
    from services.time_authority.authority import use_provider
    from services.time_authority.providers import FixedAsOfProvider
    from services.business_findings_lifecycle_v1.materialize_v1 import (
        materialize_business_findings_lifecycle_v1,
    )
    from services.product_data.merchant_experience_integration_foundation_v1 import (
        generate_merchant_experience_integration_v1,
    )

    client = TestClient(app)
    auth = _signup_and_bind(client)
    sim = _run_simulation()

    with use_provider(FixedAsOfProvider(SIM_END)):
        mat = materialize_business_findings_lifecycle_v1(
            "demo",
            load_db=True,
            demo_fixture=False,
            admit_review_fixtures=False,
            window_days=14,
        )

    meif = generate_merchant_experience_integration_v1("demo")
    binding = meif.get("business_findings_binding_v1") or {}
    home_findings = (
        ((meif.get("pages") or {}).get("home") or {}).get("sections") or {}
    ).get("business_findings") or []

    shots_info: dict = {"shots": [], "error": ""}
    try:
        server = _start_server(app, 8781)
        time.sleep(1.5)
        shots_info = _capture_home(
            "http://127.0.0.1:8781",
            auth.get("cookies") or {},
            auth.get("cookie_name") or "cartflow_merchant",
        )
        try:
            server.should_exit = True
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        shots_info = {"shots": [], "error": str(exc)}

    painted = int(shots_info.get("painted_finding_cards") or 0)
    titles = list(shots_info.get("titles") or [])
    acceptance = bool(
        mat.get("persisted", 0) >= 1
        and binding.get("home_bound", 0) >= 1
        and painted >= 1
        and titles
    )

    evidence = {
        "lab": "merchant_experience_binding_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_path": str(db_path),
        "constraints": {
            "demo_fixture": False,
            "admit_review_fixtures": False,
            "load_db": True,
            "pure_consumer": True,
        },
        "simulation": sim,
        "materialize": {
            "ok": mat.get("ok"),
            "detected": mat.get("detected"),
            "persisted": mat.get("persisted"),
            "surface_eligible": mat.get("surface_eligible"),
            "errors": mat.get("errors"),
        },
        "meif_binding": binding,
        "home_business_findings": home_findings,
        "screenshots": shots_info,
        "acceptance_home_painted": acceptance,
    }
    (OUT / "lab_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    lines = [
        "# Merchant Experience Binding V1 — Validation",
        "",
        f"**Date (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"**Simulation:** `{sim.get('simulation_run_id')}`",
        "**Constraints:** no fixtures · no demo_fixture · BFL consume only · no KF/OT/BFL producer changes",
        "",
        "## Binding audit",
        "",
        "| Surface | Renderer | Prior source | Canonical source | Binding |",
        "|---------|----------|--------------|------------------|---------|",
        "| Home | `applyHome` MEIF JS | SCF/OT/KF | `business_findings` via BFL consume | `sections.business_findings` + paint |",
        "| Decision | `applyDecision` | SCF review_items | BFL destinations | `sections.business_findings` |",
        "| Carts | `applyCarts` | OT composition | BFL cart destinations | `sections.business_findings` |",
        "| Communication | `applyCommunication` | OT composition | BFL WA destinations | `sections.business_findings` |",
        "",
        "## Materialize (historical)",
        "",
        f"- persisted: {mat.get('persisted')} · surface_eligible: {mat.get('surface_eligible')}",
        "",
        "## MEIF binding",
        "",
        f"- home_bound: {binding.get('home_bound')}",
        f"- findings_bound: {binding.get('findings_bound')}",
        f"- ok: {binding.get('ok')}",
        "",
        "## Home paint",
        "",
        f"- painted finding cards: **{painted}**",
        f"- titles: {titles}",
        f"- screenshots: {shots_info.get('shots')}",
        "",
        "### Render diagnostics",
        "",
        "```json",
        json.dumps(shots_info.get("render_diagnostics") or {}, ensure_ascii=False, indent=2),
        "```",
        "",
        f"**Acceptance (Home paints ≥1 real finding):** `{acceptance}`",
        "",
        "## STOP",
        "",
        "Screenshots + diagnostics submitted. No commit requested.",
        "",
    ]
    report = ROOT / "docs" / "product" / "MERCHANT_EXPERIENCE_BINDING_V1.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": acceptance, "painted": painted, "titles": titles, "report": str(report)}, indent=2, ensure_ascii=False))
    return 0 if acceptance else 2


if __name__ == "__main__":
    raise SystemExit(main())
