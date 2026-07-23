# -*- coding: utf-8 -*-
"""
Merchant Experience Validation V1 — product validation only.

Runs historical Store Reality Simulator (Small Reality), collects merchant
journey + Knowledge/Guidance/Surface Composition evidence. Does NOT change
product logic, redesign pages, or inject fake dashboard data.
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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "architecture" / "merchant_experience_validation_v1"
SEED = 20260722
START_DATE = "2026-05-01"
SIM_END = datetime(2026, 5, 4, 12, 0, 0)

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
    db_path = Path(tempfile.gettempdir()) / f"cartflow_mev1_{SEED}.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass
    os.environ["DATABASE_URL"] = "sqlite:///" + str(db_path).replace("\\", "/")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")
    os.environ.setdefault("CARTFLOW_SURFACE_COMPOSITION_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_PRESENTATION_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_GUIDANCE_ROUTING_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_GUIDANCE_ELIGIBILITY_V1", "1")
    os.environ.setdefault("CARTFLOW_KNOWLEDGE_FOUNDATION_V1", "1")
    return db_path


def _lab_scale_profile():
    from services.store_reality_simulator.scale_profiles_v1 import ScaleProfile

    return ScaleProfile(
        profile_id="merchant_experience_validation_v1",
        duration_days=3,
        journeys_per_day=9.0,
        max_events_per_run=500,
        batch_size=25,
        pause_ms_between_batches=20,
        description="Merchant Experience Validation V1 — Small Reality (3 days)",
    )


def _http_json(url: str) -> dict:
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=180) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body) if body else {"http_error": exc.code}
        except json.JSONDecodeError:
            return {"http_error": exc.code, "raw": body[:500]}
    except URLError as exc:
        return {"error": str(exc)}


def _collect_prod_probes() -> dict:
    base = "https://smartreplyai.net"
    return {
        "surface_composition": _http_json(
            f"{base}/dev/surface-composition?store=demo&assembly_window=d7"
        ),
        "merchant_presentation": _http_json(
            f"{base}/dev/merchant-presentation?store=demo&assembly_window=d7"
        ),
        "guidance_routing": _http_json(
            f"{base}/dev/guidance-routing?store=demo&assembly_window=d7"
        ),
        "commercial_guidance": _http_json(
            f"{base}/dev/commercial-guidance?store=demo&assembly_window=d7"
        ),
        "knowledge_foundation": _http_json(
            f"{base}/dev/knowledge-foundation?store=demo&assembly_window=d7"
        ),
    }


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
                "lab": "merchant_experience_validation_v1",
                "lab_profile": "merchant_experience_validation_v1",
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
        "execute": {
            "status": result.get("status"),
            "batches_done": result.get("batches_done"),
            "accounting": result.get("accounting"),
        },
        "wall_ms": elapsed,
    }


def _signup_and_bind_demo(client) -> dict:
    from extensions import db
    from models import MerchantUser
    from services.merchant_auth_http import merchant_cookie_name
    from services.identity_authority.lab_session_bind_v1 import (
        align_merchant_session_to_simulation_store,
        ensure_demo_store_for_lab,
    )

    email = f"mev1-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/signup",
        data={
            "store_name": "متجر تجربة التاجر",
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    cookies = dict(r.cookies)
    bind_result = {"ok": False, "error": "merchant_missing"}
    try:
        ensure_demo_store_for_lab()
        user = db.session.query(MerchantUser).filter_by(email=email).first()
        if user is not None:
            bind_result = align_merchant_session_to_simulation_store(
                merchant_user_id=int(user.id)
            )
    except Exception as exc:  # noqa: BLE001
        bind_result = {"ok": False, "error": str(exc)}
    return {
        "email": email,
        "signup_status": r.status_code,
        "cookie_name": merchant_cookie_name(),
        "cookies": cookies,
        "lab_session_bind": bind_result,
    }


def _collect_stack_evidence(*, as_of: datetime) -> dict:
    """Governed Product Performance stack — no raw event reads."""
    out: dict = {"as_of": as_of.isoformat(sep=" "), "errors": []}

    try:
        from services.product_data.knowledge_foundation_v1 import generate_knowledge_v1

        out["knowledge"] = generate_knowledge_v1("demo", assembly_window="d7", as_of=as_of)
    except Exception as exc:  # noqa: BLE001
        out["knowledge"] = {"error": f"{type(exc).__name__}:{exc}"}
        out["errors"].append("knowledge")

    try:
        from services.product_data.commercial_guidance_foundation_v1 import (
            generate_commercial_guidance_v1,
        )

        out["commercial_guidance"] = generate_commercial_guidance_v1(
            "demo", assembly_window="d7", as_of=as_of
        )
    except Exception as exc:  # noqa: BLE001
        out["commercial_guidance"] = {"error": f"{type(exc).__name__}:{exc}"}
        out["errors"].append("commercial_guidance")

    try:
        from services.product_data.guidance_routing_foundation_v1 import (
            generate_guidance_routes_v1,
        )

        out["guidance_routing"] = generate_guidance_routes_v1(
            "demo", assembly_window="d7", as_of=as_of
        )
    except Exception as exc:  # noqa: BLE001
        out["guidance_routing"] = {"error": f"{type(exc).__name__}:{exc}"}
        out["errors"].append("guidance_routing")

    try:
        from services.product_data.merchant_presentation_foundation_v1 import (
            generate_merchant_presentations_v1,
        )

        out["merchant_presentation"] = generate_merchant_presentations_v1(
            "demo", assembly_window="d7", as_of=as_of
        )
    except Exception as exc:  # noqa: BLE001
        out["merchant_presentation"] = {"error": f"{type(exc).__name__}:{exc}"}
        out["errors"].append("merchant_presentation")

    try:
        from services.product_data.surface_composition_foundation_v1 import (
            generate_surface_compositions_v1,
        )

        out["surface_composition"] = generate_surface_compositions_v1(
            "demo", assembly_window="d7", as_of=as_of
        )
    except Exception as exc:  # noqa: BLE001
        out["surface_composition"] = {"error": f"{type(exc).__name__}:{exc}"}
        out["errors"].append("surface_composition")

    return out


def _collect_merchant_surfaces(client, cookies) -> dict:
    from extensions import db
    from models import (
        AbandonedCart,
        CartRecoveryLog,
        CartRecoveryReason,
        PurchaseTruthRecord,
        RecoverySchedule,
        Store,
    )

    demo = db.session.query(Store).filter_by(zid_store_id="demo").first()
    store_id = int(demo.id) if demo else None

    def _get(path: str) -> dict:
        r = client.get(path, cookies=cookies)
        try:
            body = r.json()
        except Exception:
            body = {"_raw_status": r.status_code, "_text": (r.text or "")[:2500]}
        return {"status": r.status_code, "body": body}

    home = {}
    try:
        from services.merchant_home_composition_v1 import (
            build_merchant_home_experience_api_payload,
        )

        home = build_merchant_home_experience_api_payload(
            db.session, "demo", demo, merchant_name_ar="متجر تجربة التاجر"
        )
    except Exception as exc:  # noqa: BLE001
        home = {"error": str(exc)[:500]}

    knowledge_layer = {}
    try:
        from services.knowledge_layer_v1 import build_knowledge_report

        report = build_knowledge_report(db.session, "demo", window_days=7)
        knowledge_layer = (
            report.to_dict() if hasattr(report, "to_dict") else {"raw": str(report)[:2000]}
        )
    except Exception as exc:  # noqa: BLE001
        knowledge_layer = {"error": str(exc)[:500]}

    carts_q = db.session.query(AbandonedCart)
    if store_id is not None:
        carts_q = carts_q.filter(AbandonedCart.store_id == store_id)

    return {
        "api": {
            "summary": _get("/api/dashboard/summary"),
            "normal_carts": _get("/api/dashboard/normal-carts"),
            "vip_carts": _get("/api/dashboard/vip-carts"),
            "followups": _get("/api/dashboard/followups"),
        },
        "composed": {"home": home, "knowledge_layer": knowledge_layer},
        "counts": {
            "abandoned_carts": carts_q.count(),
            "purchase_truth": db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.store_slug == "demo")
            .count(),
            "schedules": db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.store_slug == "demo")
            .count(),
            "reasons": db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.store_slug == "demo")
            .count(),
            "mock_wa": db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.store_slug == "demo",
                CartRecoveryLog.status == "mock_sent",
            )
            .count(),
        },
    }


def _capture_screenshots(base_url: str, cookies: dict, cookie_name: str) -> list[str]:
    shots: list[str] = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        (OUT / "screenshot_error.txt").write_text(
            "playwright_not_installed", encoding="utf-8"
        )
        return shots

    OUT.mkdir(parents=True, exist_ok=True)
    pages = [
        ("home", "#home"),
        ("decision", "#workspace"),
        ("carts", "#carts"),
        ("communication", "#whatsapp"),
        ("settings", "#settings"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, viewport in (
            ("desktop", {"width": 1440, "height": 900}),
            ("mobile", {"width": 390, "height": 844}),
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
            page.wait_for_timeout(1000)
            for name, hash_path in pages:
                try:
                    page.evaluate(f"location.hash = '{hash_path}'")
                    page.wait_for_timeout(1200)
                    fname = f"{label}_{name}.png"
                    page.screenshot(path=str(OUT / fname), full_page=True)
                    shots.append(fname)
                except Exception:  # noqa: BLE001
                    pass
            ctx.close()
        browser.close()
    return shots


def _start_server(app, port: int = 8771):
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prod = _collect_prod_probes()
    (OUT / "production_probes.json").write_text(
        json.dumps(prod, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

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

    # Wall-clock vs sim-aligned stack (temporal trust)
    stack_wall = _collect_stack_evidence(as_of=datetime.utcnow().replace(microsecond=0))
    stack_sim = _collect_stack_evidence(as_of=SIM_END)
    surfaces = _collect_merchant_surfaces(client, auth.get("cookies") or {})

    shots: list[str] = []
    screenshot_error = ""
    try:
        server = _start_server(app, 8771)
        time.sleep(1.5)
        shots = _capture_screenshots(
            "http://127.0.0.1:8771",
            auth.get("cookies") or {},
            auth.get("cookie_name") or "cartflow_merchant",
        )
        server.should_exit = True
    except Exception as exc:  # noqa: BLE001
        screenshot_error = str(exc)
        (OUT / "screenshot_error.txt").write_text(screenshot_error, encoding="utf-8")

    # Compact reviews for report generation
    scf = stack_sim.get("surface_composition") or {}
    compositions = list(scf.get("compositions") or [])
    visible = [c for c in compositions if c.get("visibility") == "visible"]
    by_surface: dict[str, list] = {}
    for c in compositions:
        by_surface.setdefault(str(c.get("surface_id")), []).append(c)

    knowledge_stmts = list((stack_sim.get("knowledge") or {}).get("statements") or [])
    guidance_items = list(
        (stack_sim.get("commercial_guidance") or {}).get("guidance")
        or (stack_sim.get("commercial_guidance") or {}).get("records")
        or []
    )

    bundle = {
        "lab": "merchant_experience_validation_v1",
        "profile": "Small Reality historical",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "auth": {k: v for k, v in auth.items() if k != "cookies"},
        "simulation": sim,
        "merchant_surfaces": surfaces,
        "stack_wall_clock": {
            "ok_flags": {
                k: bool((stack_wall.get(k) or {}).get("ok"))
                for k in (
                    "knowledge",
                    "commercial_guidance",
                    "guidance_routing",
                    "merchant_presentation",
                    "surface_composition",
                )
            },
            "errors": stack_wall.get("errors"),
            "knowledge_count": len(
                list((stack_wall.get("knowledge") or {}).get("statements") or [])
            ),
            "composition_count": int(
                (stack_wall.get("surface_composition") or {}).get("composition_count")
                or 0
            ),
        },
        "stack_sim_aligned": {
            "as_of": stack_sim.get("as_of"),
            "errors": stack_sim.get("errors"),
            "knowledge_statement_count": len(knowledge_stmts),
            "knowledge_sample": [
                {
                    "knowledge_id": s.get("knowledge_id"),
                    "knowledge_type": s.get("knowledge_type"),
                    "statement": (s.get("statement") or "")[:220],
                    "confidence_level": s.get("confidence_level"),
                }
                for s in knowledge_stmts[:12]
            ],
            "guidance_count": len(guidance_items),
            "guidance_sample": [
                {
                    "guidance_id": g.get("guidance_id"),
                    "guidance_key": g.get("guidance_key"),
                    "guidance_status": g.get("guidance_status"),
                    "subject_type": g.get("subject_type"),
                }
                for g in guidance_items[:12]
            ],
            "surface_composition": {
                "ok": scf.get("ok"),
                "composition_count": scf.get("composition_count"),
                "accounting": scf.get("accounting"),
                "visible_count": len(visible),
                "by_surface_counts": {k: len(v) for k, v in by_surface.items()},
                "visible_sample": [
                    {
                        "surface_id": c.get("surface_id"),
                        "information_class": c.get("information_class"),
                        "presentation_intent": c.get("presentation_intent"),
                        "priority": c.get("priority"),
                        "freshness_state": c.get("freshness_state"),
                        "visibility": c.get("visibility"),
                        "duplicate_group": c.get("duplicate_group"),
                        "owns_full_explanation": c.get("owns_full_explanation"),
                        "accounting_outcome": c.get("accounting_outcome"),
                    }
                    for c in sorted(
                        visible,
                        key=lambda x: (
                            str(x.get("surface_id")),
                            -int(x.get("priority") or 0),
                        ),
                    )[:20]
                ],
            },
        },
        "production_probe_ok": {
            k: bool((prod.get(k) or {}).get("ok")) for k in prod
        },
        "screenshots": shots,
        "screenshot_error": screenshot_error,
    }
    (OUT / "mev1_evidence.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    # Keep full stack dumps for deep review (may be large).
    (OUT / "stack_sim_full.json").write_text(
        json.dumps(stack_sim, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "run_id": sim.get("simulation_run_id"),
                "out": str(OUT),
                "screenshots": len(shots),
                "prod_ok": bundle["production_probe_ok"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
