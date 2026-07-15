# -*- coding: utf-8 -*-
"""
Controlled Reality Engine — Phase 3.

Plans and executes governed historical behaviour for demo only.
Never runs on merchant request paths. Never injects derived truth.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from extensions import db
from models import SimulationEventLedger
from services.store_reality_simulator.accounting_v1 import (
    accounting_from_json,
    accounting_to_json,
    empty_accounting,
    increment_bucket,
)
from services.store_reality_simulator.checkpoint_v1 import (
    apply_checkpoint_to_run,
    build_checkpoint,
)
from services.store_reality_simulator.clock_v1 import SimulationClock
from services.store_reality_simulator.config_loader_v1 import (
    SimulationConfig,
    load_simulation_config,
)
from services.store_reality_simulator.context_v1 import simulation_scope
from services.store_reality_simulator.contracts_v1 import (
    BUCKET_FAILED,
    BUCKET_PERSISTED,
    BUCKET_PLANNED,
    BUCKET_PROCESSED,
    BUCKET_REJECTED,
    BUCKET_SUPPRESSED,
    BUCKET_UNSUPPORTED,
    DEMO_STORE_SLUG,
    STATUS_COMPLETED,
    STATUS_CREATED,
    STATUS_DRY_RUN,
    STATUS_PAUSED,
    STATUS_RUNNING,
    assert_demo_store,
)
from services.store_reality_simulator.event_ledger_v1 import (
    list_ledger_events,
    mark_ledger_result,
    persist_plan_to_ledger,
    planned_event_from_ledger,
)
from services.store_reality_simulator.ingress_adapter_v1 import execute_planned_event
from services.store_reality_simulator.manifest_v1 import (
    build_simulation_manifest,
    write_manifest_file,
)
from services.store_reality_simulator.performance_guards_v1 import (
    BatchTimer,
    PerformanceThresholds,
    capture_performance_snapshot,
    evaluate_stop_condition,
    sleep_between_batches,
)
from services.store_reality_simulator.planner_v1 import RealityPlan, build_reality_plan
from services.store_reality_simulator.progress_v1 import (
    build_progress_monitor,
    normalize_progress,
    progress_from_json,
    progress_to_json,
)
from services.store_reality_simulator.reality_score_v1 import compute_reality_score
from services.store_reality_simulator.run_registry_v1 import (
    clock_for_run,
    create_simulation_run,
    get_run,
    persist_run,
    require_run,
    sync_clock_to_run,
)
from services.store_reality_simulator.scale_profiles_v1 import resolve_scale_profile
from services.store_reality_simulator.schema_v1 import ensure_srs_phase3_schema
from services.store_reality_simulator.validation_report_v1 import build_validation_report

log = logging.getLogger("cartflow.store_reality_simulator")

_MANIFEST_DIR = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "srs_runs"


def _cfg_dict(cfg: SimulationConfig) -> dict[str, Any]:
    return cfg.to_dict()


def plan_and_attach(
    config: SimulationConfig | dict[str, Any],
    *,
    simulation_run_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create run (if needed), build deterministic plan, persist cold ledger + manifest."""
    cfg = (
        config
        if isinstance(config, SimulationConfig)
        else load_simulation_config(config)
    )
    assert_demo_store(cfg.store_slug)
    ensure_srs_phase3_schema()
    profile = resolve_scale_profile(
        profile_id=(cfg.metadata or {}).get("scale_profile"),
        duration_days=cfg.duration_days,
    )
    # Align duration to profile when profile chosen explicitly
    if (cfg.metadata or {}).get("scale_profile"):
        cfg.duration_days = profile.duration_days
        cfg.batch_size = min(cfg.batch_size, profile.batch_size)
        cfg.max_events_per_job = min(cfg.max_events_per_job, profile.max_events_per_run)

    row = create_simulation_run(cfg, simulation_run_id=simulation_run_id)
    start_dt = datetime(
        cfg.start_date.year,
        cfg.start_date.month,
        cfg.start_date.day,
        tzinfo=timezone.utc,
    )
    plan = build_reality_plan(
        simulation_run_id=row.simulation_run_id,
        seed=cfg.seed,
        start_date=start_dt,
        duration_days=cfg.duration_days,
        scenario_ids=cfg.scenario_ids,
        scale=profile,
        scale_factor=float(cfg.scale),
    )
    persist_plan_to_ledger(plan)
    acc = empty_accounting()
    acc = increment_bucket(acc, BUCKET_PLANNED, len(plan.events))
    score = compute_reality_score(plan, accounting=acc)
    manifest = build_simulation_manifest(
        plan=plan,
        config=_cfg_dict(cfg),
        reality_score=score,
    )
    try:
        write_manifest_file(manifest, _MANIFEST_DIR / row.simulation_run_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("manifest write failed: %s", exc)

    row.accounting_json = accounting_to_json(acc)
    row.status = STATUS_DRY_RUN if cfg.mode == "dry_run" else STATUS_CREATED
    if hasattr(row, "manifest_json"):
        row.manifest_json = json.dumps(manifest, ensure_ascii=False)
    if hasattr(row, "reality_score_json"):
        row.reality_score_json = json.dumps(score, ensure_ascii=False)
    if hasattr(row, "scale_profile"):
        row.scale_profile = profile.profile_id
    if hasattr(row, "plan_summary_json"):
        row.plan_summary_json = json.dumps(plan.to_summary(), ensure_ascii=False)
    progress = progress_from_json(row.progress_json)
    progress = normalize_progress(progress)
    progress.update(
        {
            "phase": "planned",
            "current_step": 0,
            "total_steps_estimate": len(plan.events),
            "events_generated": True,
            "message": f"Plan ready: {len(plan.events)} events ({profile.profile_id})",
            "reality_score_overall": score.get("overall"),
            "scale_profile": profile.profile_id,
        }
    )
    row.progress_json = progress_to_json(progress)
    persist_run(row)
    return {
        "ok": True,
        "simulation_run_id": row.simulation_run_id,
        "mode": cfg.mode,
        "plan": plan.to_summary(),
        "manifest": manifest,
        "reality_score": score,
        "monitor": build_progress_monitor(row),
    }


def execute_reality_run(
    simulation_run_id: str,
    *,
    max_batches: Optional[int] = None,
    thresholds: Optional[PerformanceThresholds] = None,
) -> dict[str, Any]:
    """
    Execute planned ledger events in bounded batches under simulation_scope.
    Auto-pauses when performance guards fire.
    """
    row = require_run(simulation_run_id)
    assert_demo_store(row.store_slug)
    cfg = load_simulation_config(json.loads(row.config_json or "{}"))
    profile = resolve_scale_profile(
        profile_id=getattr(row, "scale_profile", None)
        or (cfg.metadata or {}).get("scale_profile"),
        duration_days=cfg.duration_days,
    )
    batch_size = min(int(cfg.batch_size), int(profile.batch_size))
    pause_ms = int(profile.pause_ms_between_batches)

    pending = list_ledger_events(row.simulation_run_id, status="planned")
    if not pending:
        # resume: also pick failed? only planned for now
        row.status = STATUS_COMPLETED
        persist_run(row)
        return {"ok": True, "status": STATUS_COMPLETED, "note": "no_pending_events"}

    row.status = STATUS_RUNNING
    persist_run(row)

    acc = accounting_from_json(row.accounting_json)
    clock = clock_for_run(row)
    t0 = time.perf_counter()
    batches_done = 0
    consecutive_failures = 0
    processed_in_job = 0
    max_events = int(cfg.max_events_per_job)
    last_snap: dict[str, Any] = {}
    pause_reason: Optional[str] = None

    with simulation_scope(
        simulation_run_id=row.simulation_run_id,
        clock=clock,
        seed=int(row.seed),
        scenario_ids=list(cfg.scenario_ids),
        store_slug=DEMO_STORE_SLUG,
    ):
        while pending and processed_in_job < max_events:
            batch = pending[:batch_size]
            pending = pending[batch_size:]
            timer = BatchTimer()
            batch_fail = 0
            for ledger_row in batch:
                # Re-bind after prior ingress (purchase/reconcile may rotate sessions)
                ledger_id = int(ledger_row.id)
                live = db.session.get(SimulationEventLedger, ledger_id)
                if live is None:
                    continue
                ev = planned_event_from_ledger(live)
                # Advance simulation clock to event time (monotonic)
                try:
                    if ev.simulated_at > clock.now():
                        clock.advance_to(ev.simulated_at)
                    else:
                        clock.set_now(ev.simulated_at)
                except ValueError:
                    clock.set_now(ev.simulated_at)

                run_id = row.simulation_run_id
                seed = int(row.seed)
                result = execute_planned_event(
                    ev,
                    simulation_run_id=run_id,
                    seed=seed,
                )
                # Platform ingress may have replaced the scoped session
                row = require_run(run_id)
                bucket = str(result.get("bucket") or "failed")
                if bucket == "unsupported":
                    acc = increment_bucket(acc, BUCKET_UNSUPPORTED)
                    mark_ledger_result(ledger_id, status="unsupported", result=result)
                elif bucket == "persisted":
                    acc = increment_bucket(acc, BUCKET_PERSISTED)
                    acc = increment_bucket(acc, BUCKET_PROCESSED)
                    mark_ledger_result(ledger_id, status="processed", result=result)
                elif bucket == "processed":
                    acc = increment_bucket(acc, BUCKET_PROCESSED)
                    mark_ledger_result(ledger_id, status="processed", result=result)
                elif bucket == "suppressed":
                    acc = increment_bucket(acc, BUCKET_SUPPRESSED)
                    acc = increment_bucket(acc, BUCKET_PROCESSED)
                    mark_ledger_result(ledger_id, status="processed", result=result)
                elif bucket == "rejected":
                    acc = increment_bucket(acc, BUCKET_REJECTED)
                    mark_ledger_result(ledger_id, status="rejected", result=result)
                else:
                    acc = increment_bucket(acc, BUCKET_FAILED)
                    mark_ledger_result(ledger_id, status="failed", result=result)
                    batch_fail += 1
                    consecutive_failures += 1
                if result.get("ok"):
                    consecutive_failures = 0
                processed_in_job += 1
                row.current_step = int(live.event_index) + 1

            db.session.commit()
            row = require_run(row.simulation_run_id)
            sync_clock_to_run(row, clock)
            batches_done += 1
            wall_ms = timer.elapsed_ms()
            fail_rate = batch_fail / max(1, len(batch))
            snap = capture_performance_snapshot(
                batch_wall_ms=wall_ms,
                failure_rate=fail_rate,
                consecutive_failures=consecutive_failures,
            )
            last_snap = snap.to_dict()
            reason = evaluate_stop_condition(snap, thresholds)
            cp = build_checkpoint(
                current_step=int(row.current_step or 0),
                current_day=row.current_day,
                simulated_now=clock.now(),
                last_simulated_event_id=batch[-1].simulated_event_id if batch else None,
                batch_index=batches_done,
                reason="batch_complete" if not reason else reason,
            )
            apply_checkpoint_to_run(row, cp)
            row.accounting_json = accounting_to_json(acc)
            progress = progress_from_json(row.progress_json)
            progress.update(
                {
                    "phase": "executing",
                    "current_step": row.current_step,
                    "throttle_state": "paused" if reason else "running",
                    "pause_reason": reason,
                    "last_batch_ms": wall_ms,
                    "batches_done": batches_done,
                }
            )
            row.progress_json = progress_to_json(progress)
            if hasattr(row, "throttle_state_json"):
                row.throttle_state_json = json.dumps(
                    {"state": "paused" if reason else "running", "reason": reason},
                    ensure_ascii=False,
                )
            persist_run(row)

            if reason:
                row.status = STATUS_PAUSED
                persist_run(row)
                pause_reason = reason
                log.warning(
                    "[SRS] auto-pause run=%s reason=%s", row.simulation_run_id, reason
                )
                break

            if max_batches is not None and batches_done >= int(max_batches):
                break
            sleep_between_batches(pause_ms)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    # Rebuild score + validation if completed or paused
    # Reconstruct plan summary from config + ledger counts
    start_dt = row.start_date
    if getattr(start_dt, "tzinfo", None) is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    plan = build_reality_plan(
        simulation_run_id=row.simulation_run_id,
        seed=int(row.seed),
        start_date=start_dt,
        duration_days=int(row.duration_days),
        scenario_ids=cfg.scenario_ids,
        scale=profile,
        scale_factor=float(cfg.scale),
    )
    score = compute_reality_score(plan, accounting=acc)
    manifest = build_simulation_manifest(
        plan=plan,
        config=_cfg_dict(cfg),
        reality_score=score,
        execution_time_ms=elapsed_ms,
        warnings=[pause_reason] if pause_reason else None,
    )
    validation = build_validation_report(
        plan=plan,
        accounting=acc,
        reality_score=score,
        performance={"last_snapshot": last_snap, "execution_time_ms": elapsed_ms},
        manifest=manifest,
    )
    if hasattr(row, "manifest_json"):
        row.manifest_json = json.dumps(manifest, ensure_ascii=False)
    if hasattr(row, "reality_score_json"):
        row.reality_score_json = json.dumps(score, ensure_ascii=False)
    if hasattr(row, "validation_report_json"):
        row.validation_report_json = json.dumps(validation, ensure_ascii=False)

    still_pending = list_ledger_events(row.simulation_run_id, status="planned")
    if not still_pending and row.status != STATUS_PAUSED:
        row.status = STATUS_COMPLETED
        progress = progress_from_json(row.progress_json)
        progress["phase"] = "completed"
        progress["message"] = "Reality engine run completed"
        row.progress_json = progress_to_json(progress)
    persist_run(row)
    try:
        write_manifest_file(manifest, _MANIFEST_DIR / row.simulation_run_id)
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "simulation_run_id": row.simulation_run_id,
        "status": row.status,
        "pause_reason": pause_reason,
        "batches_done": batches_done,
        "accounting": acc,
        "reality_score": score,
        "manifest": manifest,
        "validation_report": validation,
        "monitor": build_progress_monitor(row),
        "performance": last_snap,
    }


def dry_run_reality(config: SimulationConfig | dict[str, Any]) -> dict[str, Any]:
    body = dict(config if isinstance(config, dict) else config.to_dict())
    body["mode"] = "dry_run"
    return plan_and_attach(body)
