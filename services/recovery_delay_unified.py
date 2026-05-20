# -*- coding: utf-8 -*-
"""One effective delay per recovery attempt — scheduling, sleep, and final gate."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _timing_label(timing: Dict[str, Any]) -> str:
    return str(timing.get("source") or "unknown")[:96]


def log_recovery_delay_resolved(
    timing: Dict[str, Any],
    *,
    recovery_key: str,
    path: str = "",
) -> None:
    try:
        print("[RECOVERY DELAY RESOLVED]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"reason_tag={(timing.get('reason_tag') or '-')[:64]}", flush=True)
        print(f"stage={timing.get('stage', 1)}", flush=True)
        print(f"effective_delay_seconds={float(timing.get('effective_delay_seconds', 0))}", flush=True)
        print(f"source={_timing_label(timing)}", flush=True)
        if timing.get("fallback_reason"):
            print(f"fallback_reason={timing['fallback_reason']}", flush=True)
        if path:
            print(f"path={path[:64]}", flush=True)
    except OSError:
        pass


def log_recovery_delay_scheduled(
    timing: Dict[str, Any],
    *,
    recovery_key: str,
    scheduled_delay_seconds: float,
) -> None:
    try:
        print("[RECOVERY DELAY SCHEDULED]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"scheduled_delay_seconds={float(scheduled_delay_seconds)}", flush=True)
        print(f"effective_delay_seconds={float(timing.get('effective_delay_seconds', 0))}", flush=True)
        print(f"source={_timing_label(timing)}", flush=True)
        print(f"reason_tag={(timing.get('reason_tag') or '-')[:64]}", flush=True)
        print(f"stage={timing.get('stage', 1)}", flush=True)
    except OSError:
        pass


def log_final_delay_gate(
    timing: Dict[str, Any],
    *,
    recovery_key: str,
    gate_delay_seconds: float,
    should_send: bool,
    skip_delay_check: bool = False,
) -> None:
    try:
        print("[FINAL DELAY GATE]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"gate_delay_seconds={float(gate_delay_seconds)}", flush=True)
        print(f"effective_delay_seconds={float(timing.get('effective_delay_seconds', 0))}", flush=True)
        print(f"source={_timing_label(timing)}", flush=True)
        print(f"should_send={'true' if should_send else 'false'}", flush=True)
        if skip_delay_check:
            print("delay_check=skipped", flush=True)
    except OSError:
        pass


def timing_from_recovery_context(
    recovery_context: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not recovery_context:
        return None
    raw = recovery_context.get("schedule_timing")
    if isinstance(raw, dict) and raw.get("effective_delay_seconds") is not None:
        return dict(raw)
    return None


def attach_schedule_timing_to_context(
    recovery_context: Optional[Dict[str, Any]],
    timing: Dict[str, Any],
) -> Dict[str, Any]:
    ctx = dict(recovery_context or {})
    ctx["schedule_timing"] = dict(timing)
    return ctx


def effective_delay_for_gate(
    *,
    recovery_context: Optional[Dict[str, Any]],
    delay_seconds_scheduled: float,
    multi_slot_index: Optional[int],
    step_num: int,
    reason_tag: Optional[str],
    store_obj: Any,
    recovery_key: str,
    resolve_timing_fn: Any,
) -> Dict[str, Any]:
    """
    Return the same timing dict used for scheduling when present; otherwise resolve once.
    ``resolve_timing_fn`` is ``resolve_recovery_schedule_timing`` (injected to avoid import cycles).
    """
    cached = timing_from_recovery_context(recovery_context)
    if cached is not None:
        return cached

    if multi_slot_index is not None or step_num > 1:
        return {
            "reason_tag": (reason_tag or "")[:128],
            "canon": None,
            "stage": step_num,
            "template_delay_value": None,
            "template_delay_unit": None,
            "effective_delay_seconds": float(delay_seconds_scheduled),
            "source": "scheduled_task_delay",
            "fallback_reason": None,
        }

    stage_index = max(0, int(step_num) - 1)
    return resolve_timing_fn(
        reason_tag,
        store_obj,
        stage_index=stage_index,
        recovery_key=recovery_key,
        path="delay_gate_resolve",
    )


def gate_uses_template_timing(timing: Dict[str, Any]) -> bool:
    src = _timing_label(timing).casefold()
    if "legacy_recovery_delay" in src:
        return False
    return bool(timing.get("fallback_reason") is None and timing.get("effective_delay_seconds"))
