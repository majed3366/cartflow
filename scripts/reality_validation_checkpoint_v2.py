# -*- coding: utf-8 -*-
"""
Reality Validation Checkpoint V2 — Time Authority WP-1…WP-6 validation.

Replays Reality Validation Lab V1 Small Reality (same seed/dates/scenarios)
and probes Knowledge / Dashboard / Daily Brief under production vs simulation
Query Time Context. Does NOT fix product issues.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "architecture" / "reality_validation_checkpoint_v2"
V1_OUT = ROOT / "docs" / "architecture" / "reality_validation_lab_v1_small"
SIM_END = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)


def _diff_note() -> list[str]:
    return [
        "Same SEED=20260715, START_DATE=2026-05-01, duration=3d, store_slug=demo, LAB_SCENARIOS as V1.",
        "New simulation_run_id generated each checkpoint run (not forced to V1 srs_0430…).",
        "Added Time Authority probes: production/wall vs simulation_scope(start=SIM_END).",
        "Daily Brief + cross-surface window equality added (post WP-6).",
        "Merchant signup→demo bind still attempted (INV-002 may still apply).",
    ]


def _window_tuple(tw) -> dict:
    return {
        "start": tw.start.isoformat(),
        "end": tw.end.isoformat(),
        "prev_start": tw.prev_start.isoformat(),
        "window_days": tw.window_days,
        "mode": tw.context.mode.value,
        "authoritative_now": tw.authoritative_now.isoformat(),
        "simulation_run_id": tw.context.simulation_run_id or None,
    }


def _probe_time_surfaces(db_session, demo_store) -> dict:
    from services.dashboard_kpi_time_v1 import (
        merchant_month_window_projection,
        resolve_dashboard_rolling_windows,
    )
    from services.knowledge_layer_v1 import build_knowledge_report
    from services.knowledge_time_authority_v1 import resolve_knowledge_windows
    from services.merchant_daily_brief_time_v1 import (
        assert_brief_dashboard_knowledge_windows_equal,
        brief_date_iso,
        resolve_brief_windows,
    )
    from services.merchant_daily_brief_v1 import build_merchant_daily_brief_api_payload
    from services.merchant_home_composition_v1 import (
        build_merchant_home_experience_api_payload,
    )
    from services.time_authority import clear_query_time_context, simulation_scope

    clear_query_time_context()

    def _knowledge_summary(report_dict: dict) -> dict:
        insights = report_dict.get("insights") or []
        metrics = report_dict.get("metrics") or report_dict.get("metrics_snapshot") or {}
        insufficient = sum(
            1
            for i in insights
            if isinstance(i, dict)
            and str(i.get("confidence") or "").lower() == "insufficient"
        )
        return {
            "cart_count": metrics.get("cart_count"),
            "purchase_count": metrics.get("purchase_count"),
            "insight_count": len(insights),
            "insufficient_count": insufficient,
            "insight_keys": [
                str(i.get("insight_key") or i.get("key") or "")
                for i in insights
                if isinstance(i, dict)
            ][:20],
        }

    # --- Production / ambient (wall or system clock) ---
    prod_kl_w = resolve_knowledge_windows(window_days=7)
    prod_dash_w = resolve_dashboard_rolling_windows(window_days=7)
    prod_brief_w = resolve_brief_windows(window_days=7)
    prod_eq = assert_brief_dashboard_knowledge_windows_equal(window_days=7)
    try:
        prod_report = build_knowledge_report(db_session, "demo", window_days=7)
        prod_kl = _knowledge_summary(
            prod_report.to_dict() if hasattr(prod_report, "to_dict") else {}
        )
    except Exception as exc:  # noqa: BLE001
        prod_kl = {"error": str(exc)[:400]}
    try:
        prod_kpi = merchant_month_window_projection(demo_store, days=7)
    except Exception as exc:  # noqa: BLE001
        prod_kpi = {"error": str(exc)[:400]}
    try:
        prod_home = build_merchant_home_experience_api_payload(
            db_session, "demo", demo_store, merchant_name_ar="متجر واقع صغير"
        )
    except Exception as exc:  # noqa: BLE001
        prod_home = {"error": str(exc)[:400]}
    try:
        prod_brief = build_merchant_daily_brief_api_payload(
            db_session, "demo", demo_store
        )
    except Exception as exc:  # noqa: BLE001
        prod_brief = {"error": str(exc)[:400]}

    production = {
        "windows": {
            "knowledge": _window_tuple(prod_kl_w),
            "dashboard": _window_tuple(prod_dash_w),
            "brief": _window_tuple(prod_brief_w),
            "cross_surface_equal": prod_eq,
        },
        "knowledge": prod_kl,
        "dashboard_kpi": {
            "abandoned_total": prod_kpi.get("abandoned_total")
            if isinstance(prod_kpi, dict)
            else None,
            "raw_keys": list(prod_kpi.keys())[:20] if isinstance(prod_kpi, dict) else [],
            "error": prod_kpi.get("error") if isinstance(prod_kpi, dict) else None,
        },
        "home": {
            "empty_calm": prod_home.get("empty_calm")
            if isinstance(prod_home, dict)
            else None,
            "brief_date": prod_home.get("brief_date")
            if isinstance(prod_home, dict)
            else None,
            "generated_at": prod_home.get("generated_at")
            if isinstance(prod_home, dict)
            else None,
            "while_away_count": len(
                ((prod_home.get("while_away") or {}).get("items") or [])
            )
            if isinstance(prod_home, dict)
            else None,
            "attention_count": (prod_home.get("attention_today") or {}).get("count")
            if isinstance(prod_home, dict)
            else None,
            "understanding_count": len(
                ((prod_home.get("store_understanding") or {}).get("items") or [])
            )
            if isinstance(prod_home, dict)
            else None,
            "error": prod_home.get("error") if isinstance(prod_home, dict) else None,
        },
        "brief": {
            "brief_date": prod_brief.get("brief_date")
            if isinstance(prod_brief, dict)
            else None,
            "generated_at": prod_brief.get("generated_at")
            if isinstance(prod_brief, dict)
            else None,
            "achievement_count": len(prod_brief.get("achievements") or [])
            if isinstance(prod_brief, dict)
            else None,
            "attention_count": len(
                prod_brief.get("attention_items") or prod_brief.get("items") or []
            )
            if isinstance(prod_brief, dict)
            else None,
            "time_window": ((prod_brief.get("observability") or {}).get("time_window"))
            if isinstance(prod_brief, dict)
            else None,
            "error": prod_brief.get("error") if isinstance(prod_brief, dict) else None,
        },
    }

    # --- Simulation-aligned QTC (historical end of May lab window) ---
    with simulation_scope(simulation_run_id="checkpoint_v2_sim", start=SIM_END):
        sim_kl_w = resolve_knowledge_windows(window_days=7)
        sim_dash_w = resolve_dashboard_rolling_windows(window_days=7)
        sim_brief_w = resolve_brief_windows(window_days=7)
        sim_eq = assert_brief_dashboard_knowledge_windows_equal(window_days=7)
        sim_day = brief_date_iso()
        try:
            sim_report = build_knowledge_report(db_session, "demo", window_days=7)
            sim_kl = _knowledge_summary(
                sim_report.to_dict() if hasattr(sim_report, "to_dict") else {}
            )
        except Exception as exc:  # noqa: BLE001
            sim_kl = {"error": str(exc)[:400]}
        try:
            sim_kpi = merchant_month_window_projection(demo_store, days=7)
        except Exception as exc:  # noqa: BLE001
            sim_kpi = {"error": str(exc)[:400]}
        try:
            sim_home = build_merchant_home_experience_api_payload(
                db_session, "demo", demo_store, merchant_name_ar="متجر واقع صغير"
            )
        except Exception as exc:  # noqa: BLE001
            sim_home = {"error": str(exc)[:400]}
        try:
            sim_brief = build_merchant_daily_brief_api_payload(
                db_session, "demo", demo_store
            )
        except Exception as exc:  # noqa: BLE001
            sim_brief = {"error": str(exc)[:400]}

    simulation = {
        "sim_end": SIM_END.isoformat(),
        "brief_date": sim_day,
        "windows": {
            "knowledge": _window_tuple(sim_kl_w),
            "dashboard": _window_tuple(sim_dash_w),
            "brief": _window_tuple(sim_brief_w),
            "cross_surface_equal": sim_eq,
        },
        "knowledge": sim_kl,
        "dashboard_kpi": {
            "abandoned_total": sim_kpi.get("abandoned_total")
            if isinstance(sim_kpi, dict)
            else None,
            "error": sim_kpi.get("error") if isinstance(sim_kpi, dict) else None,
        },
        "home": {
            "empty_calm": sim_home.get("empty_calm")
            if isinstance(sim_home, dict)
            else None,
            "brief_date": sim_home.get("brief_date")
            if isinstance(sim_home, dict)
            else None,
            "generated_at": sim_home.get("generated_at")
            if isinstance(sim_home, dict)
            else None,
            "while_away_count": len(
                ((sim_home.get("while_away") or {}).get("items") or [])
            )
            if isinstance(sim_home, dict)
            else None,
            "attention_count": (sim_home.get("attention_today") or {}).get("count")
            if isinstance(sim_home, dict)
            else None,
            "understanding_count": len(
                ((sim_home.get("store_understanding") or {}).get("items") or [])
            )
            if isinstance(sim_home, dict)
            else None,
            "error": sim_home.get("error") if isinstance(sim_home, dict) else None,
        },
        "brief": {
            "brief_date": sim_brief.get("brief_date")
            if isinstance(sim_brief, dict)
            else None,
            "generated_at": sim_brief.get("generated_at")
            if isinstance(sim_brief, dict)
            else None,
            "achievement_count": len(sim_brief.get("achievements") or [])
            if isinstance(sim_brief, dict)
            else None,
            "attention_count": len(
                sim_brief.get("attention_items") or sim_brief.get("items") or []
            )
            if isinstance(sim_brief, dict)
            else None,
            "time_window": ((sim_brief.get("observability") or {}).get("time_window"))
            if isinstance(sim_brief, dict)
            else None,
            "error": sim_brief.get("error") if isinstance(sim_brief, dict) else None,
        },
    }

    clear_query_time_context()
    return {"production": production, "simulation": simulation}


def _v1_baseline() -> dict:
    path = V1_OUT / "sim_now_knowledge.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _load_lab_v1():
    import importlib.util

    path = ROOT / "scripts" / "reality_validation_lab_v1_small.py"
    spec = importlib.util.spec_from_file_location("reality_validation_lab_v1_small", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot_load_lab_v1")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Reuse V1 lab bootstrap + simulation
    lab = _load_lab_v1()

    db_path = lab._bootstrap_env()
    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    t0 = time.perf_counter()
    auth = lab._signup_and_bind_demo(client)
    sim = lab._run_simulation(app)
    sim_wall_ms = (time.perf_counter() - t0) * 1000.0

    from models import Store

    demo = db.session.query(Store).filter_by(zid_store_id="demo").first()
    evidence = lab._collect_platform_evidence(client, auth.get("cookies") or {})
    ta = _probe_time_surfaces(db.session, demo)

    shots: list[str] = []
    try:
        server = lab._start_server(app, 8766)
        time.sleep(1.5)
        # Capture into checkpoint OUT
        old_out = lab.OUT
        lab.OUT = OUT
        shots = lab._capture_screenshots(
            "http://127.0.0.1:8766",
            auth.get("cookies") or {},
            auth.get("cookie_name") or "cartflow_merchant",
        )
        lab.OUT = old_out
        server.should_exit = True
    except Exception as exc:  # noqa: BLE001
        shots = []
        (OUT / "screenshot_error.txt").write_text(str(exc), encoding="utf-8")

    bundle = {
        "checkpoint": "reality_validation_checkpoint_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "replay_config": {
            "seed": lab.SEED,
            "start_date": lab.START_DATE,
            "duration_days": 3,
            "store_slug": "demo",
            "scenarios": lab.LAB_SCENARIOS,
            "sim_end_probe": SIM_END.isoformat(),
        },
        "differences_from_v1": _diff_note(),
        "auth": {k: v for k, v in auth.items() if k != "cookies"},
        "simulation": sim,
        "simulation_wall_ms": sim_wall_ms,
        "evidence": evidence,
        "time_authority_probes": ta,
        "v1_baseline_knowledge": _v1_baseline(),
        "screenshots": shots,
        "performance": {
            "simulation_wall_ms": sim_wall_ms,
            "note": "No scheduler started for checkpoint; TestClient + one-shot sim only.",
            "execute": (sim.get("execute") or {}).get("performance"),
        },
    }
    (OUT / "checkpoint_evidence.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "run_id": sim.get("simulation_run_id"),
                "out": str(OUT),
                "cross_surface_sim_equal": (
                    ta.get("simulation", {})
                    .get("windows", {})
                    .get("cross_surface_equal", {})
                    .get("equal")
                ),
                "sim_cart_count": ta.get("simulation", {})
                .get("knowledge", {})
                .get("cart_count"),
                "prod_cart_count": ta.get("production", {})
                .get("knowledge", {})
                .get("cart_count"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
