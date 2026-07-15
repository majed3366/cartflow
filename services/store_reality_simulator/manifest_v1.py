# -*- coding: utf-8 -*-
"""simulation_manifest.json builder — Phase 3."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from services.store_reality_simulator.planner_v1 import RealityPlan


def _git_commit_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        return out.decode("utf-8").strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def build_simulation_manifest(
    *,
    plan: RealityPlan,
    config: dict[str, Any],
    reality_score: Optional[dict[str, Any]] = None,
    warnings: Optional[list[str]] = None,
    known_limitations: Optional[list[str]] = None,
    execution_time_ms: float = 0.0,
    clock_mode: str = "SimulationClock",
    platform_version: str = "store_reality_simulator_v1_phase3",
) -> dict[str, Any]:
    end_date = plan.start_date
    if plan.duration_days:
        from datetime import timedelta

        end_date = plan.start_date + timedelta(days=int(plan.duration_days) - 1)
    warns = list(plan.warnings) + list(warnings or [])
    limitations = list(
        known_limitations
        or [
            "Storefront chrome events (page/scroll/dwell/widget_open) are unsupported markers",
            "WhatsApp uses simulation-safe mock path only — no real provider calls",
            "Visitor traffic metrics may be unavailable to Knowledge Layer",
            "Ingress uses service-boundary writers under SimulationClock (not merchant request path)",
        ]
    )
    return {
        "simulation_run_id": plan.simulation_run_id,
        "seed": plan.seed,
        "scenario_ids": [v["scenario_id"] for v in plan.scenario_versions],
        "scenario_versions": plan.scenario_versions,
        "commit_hash": _git_commit_hash(),
        "platform_version": platform_version,
        "start_date": plan.start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "clock_mode": clock_mode,
        "products": plan.products,
        "customers": plan.customers,
        "sessions": plan.sessions,
        "expected_events": plan.expected_event_counts,
        "expected_event_total": len(plan.events),
        "configuration": config,
        "execution_time_ms": float(execution_time_ms),
        "reality_score": reality_score or {},
        "warnings": warns,
        "known_limitations": limitations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "replay": {
            "seed": plan.seed,
            "scenario_ids": [v["scenario_id"] for v in plan.scenario_versions],
            "scenario_versions": plan.scenario_versions,
            "start_date": plan.start_date.date().isoformat(),
            "duration_days": plan.duration_days,
            "scale_profile": plan.scale_profile,
            "commit_hash": _git_commit_hash(),
        },
    }


def write_manifest_file(manifest: dict[str, Any], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "simulation_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
