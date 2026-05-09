# -*- coding: utf-8 -*-
"""
Queue/worker readiness — **metadata and diagnostics only**.

No queue execution, no enqueue, no worker runtime. Safe to import from tests and
optional tooling without touching recovery or WhatsApp behavior.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Final

log = logging.getLogger("cartflow.queue_readiness")

# --- Async / execution boundary taxonomy (Part 1) ---------------------------------

BOUND_INLINE_SAFE: Final = "inline_safe"
BOUND_WORKER_CANDIDATE: Final = "future_worker_candidate"
BOUND_SCHEDULED_JOB: Final = "future_scheduled_job"
BOUND_RETRY_CANDIDATE: Final = "future_retry_candidate"

# --- Worker safety / distributed-runtime risk taxonomy (Part 3) --------------------

SAFETY_IDEMPOTENT_SAFE: Final = "idempotent_safe"
SAFETY_REQUIRES_LOCKING: Final = "requires_locking"
SAFETY_REQUIRES_ORDERING: Final = "requires_ordering"
SAFETY_PROVIDER_SIDE_EFFECT: Final = "provider_side_effect"
SAFETY_RETRY_SENSITIVE: Final = "retry_sensitive"
SAFETY_LIFECYCLE_SENSITIVE: Final = "lifecycle_sensitive"


def _env_readiness_log_enabled() -> bool:
    v = (os.getenv("CARTFLOW_QUEUE_READINESS_LOG") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def emit_queue_readiness_diagnostic(
    operation: str,
    classification: str,
    **extra: Any,
) -> None:
    """
    Structured log line for queue-readiness tracing (Part 4).

    Emits at INFO only when CARTFLOW_QUEUE_READINESS_LOG is truthy; otherwise
    DEBUG-only if the root logger level allows it (typically silent).
    """
    parts = [
        "[CARTFLOW QUEUE READINESS]",
        f"operation={operation}",
        f"classification={classification}",
    ]
    for k, v in sorted(extra.items(), key=lambda kv: kv[0]):
        if v is None:
            continue
        parts.append(f"{k}={v}")
    line = " ".join(parts)
    if _env_readiness_log_enabled():
        log.info(line)
    else:
        log.debug(line)


def get_queue_candidate_registry() -> list[dict[str, Any]]:
    """
    Read-only registry of async-like operations and how they behave today.

    Entries are descriptive only; they do not invoke application code.
    """
    return list(_QUEUE_CANDIDATE_REGISTRY)


def get_runtime_async_boundaries() -> dict[str, list[dict[str, Any]]]:
    """Operations grouped by async-boundary classification (Part 1)."""
    out: dict[str, list[dict[str, Any]]] = {
        BOUND_INLINE_SAFE: [],
        BOUND_WORKER_CANDIDATE: [],
        BOUND_SCHEDULED_JOB: [],
        BOUND_RETRY_CANDIDATE: [],
    }
    for row in _QUEUE_CANDIDATE_REGISTRY:
        b = str(row.get("async_boundary") or "")
        if b in out:
            out[b].append(row)
    return out


def get_worker_safety_classifications() -> dict[str, list[str]]:
    """Map each safety class to operation ids (Part 3)."""
    buckets: dict[str, list[str]] = {
        SAFETY_IDEMPOTENT_SAFE: [],
        SAFETY_REQUIRES_LOCKING: [],
        SAFETY_REQUIRES_ORDERING: [],
        SAFETY_PROVIDER_SIDE_EFFECT: [],
        SAFETY_RETRY_SENSITIVE: [],
        SAFETY_LIFECYCLE_SENSITIVE: [],
    }
    for row in _QUEUE_CANDIDATE_REGISTRY:
        op_id = str(row.get("id") or "")
        for tag in row.get("worker_safety") or []:
            t = str(tag)
            if t in buckets:
                buckets[t].append(op_id)
    return buckets


def get_readiness_summary() -> dict[str, Any]:
    """
    Lightweight, admin/dev-safe aggregate (Part 6).

    Does not read DB or call recovery; pure projection of the static registry.
    """
    reg = _QUEUE_CANDIDATE_REGISTRY
    queue_ready = [
        r["id"]
        for r in reg
        if r.get("async_boundary")
        in (BOUND_WORKER_CANDIDATE, BOUND_SCHEDULED_JOB, BOUND_RETRY_CANDIDATE)
    ]
    need_lock = [
        r["id"] for r in reg if SAFETY_REQUIRES_LOCKING in (r.get("worker_safety") or [])
    ]
    need_persist = [
        r["id"]
        for r in reg
        if r.get("persistence_assumption")
        in ("required", "strongly_recommended", "state_in_db")
    ]
    single_runtime = [
        r["id"]
        for r in reg
        if r.get("single_process_assumption") is True
    ]
    summary = {
        "registry_version": 1,
        "registry_entry_count": len(reg),
        "queue_ready_operations": sorted(set(queue_ready)),
        "operations_requiring_locking": sorted(set(need_lock)),
        "operations_requiring_persistence": sorted(set(need_persist)),
        "operations_with_single_runtime_assumptions": sorted(set(single_runtime)),
    }
    if _env_readiness_log_enabled():
        emit_queue_readiness_diagnostic(
            "readiness_summary",
            "inline_safe",
            entries=len(reg),
        )
    return summary


# --- Static registry (aligned with codebase survey; update when adding workers) -----

_QUEUE_CANDIDATE_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "recovery_dispatch_after_abandon",
        "title": "Normal recovery dispatch after cart_abandoned",
        "summary": (
            "asyncio.create_task from handle_cart_abandoned → delay/poll then "
            "recovery sequence (see main._run_recovery_dispatch_cart_abandoned*)."
        ),
        "code_anchors": [
            "main.handle_cart_abandoned",
            "main._run_recovery_dispatch_cart_abandoned_impl",
        ],
        "async_boundary": BOUND_WORKER_CANDIDATE,
        "future_execution_roles": [BOUND_SCHEDULED_JOB, BOUND_RETRY_CANDIDATE],
        "worker_safety": [
            SAFETY_REQUIRES_ORDERING,
            SAFETY_PROVIDER_SIDE_EFFECT,
            SAFETY_RETRY_SENSITIVE,
            SAFETY_LIFECYCLE_SENSITIVE,
        ],
        "persistence_assumption": "strongly_recommended",
        "single_process_assumption": True,
        "current_runtime_owner": "fastapi_uvicorn_event_loop_same_process",
        "multi_worker_risk_notes": (
            "In-memory session flags and locks (_recovery_session_lock, "
            "_session_recovery_*) are process-local; multiple workers need "
            "DB-backed or distributed claims."
        ),
        "existing_safeguards": [
            "CartRecoveryLog persistence",
            "cartflow_duplicate_guard notes",
            "per-recovery_key asyncio.Task scheduling in one loop",
        ],
    },
    {
        "id": "recovery_sequence_after_delay",
        "title": "Delayed recovery sequence (sleep + send path)",
        "summary": (
            "asyncio.sleep then should_send_whatsapp gate and send_whatsapp / "
            "queue enqueue (main._run_recovery_sequence_after_cart_abandoned*)."
        ),
        "code_anchors": [
            "main._run_recovery_sequence_after_cart_abandoned",
            "main._run_recovery_sequence_after_cart_abandoned_impl",
        ],
        "async_boundary": BOUND_SCHEDULED_JOB,
        "future_execution_roles": [BOUND_SCHEDULED_JOB, BOUND_RETRY_CANDIDATE],
        "worker_safety": [
            SAFETY_REQUIRES_ORDERING,
            SAFETY_PROVIDER_SIDE_EFFECT,
            SAFETY_RETRY_SENSITIVE,
            SAFETY_LIFECYCLE_SENSITIVE,
        ],
        "persistence_assumption": "required",
        "single_process_assumption": True,
        "current_runtime_owner": "fastapi_uvicorn_event_loop_same_process",
        "multi_worker_risk_notes": (
            "Ordering of steps (multi_message / sequential) assumes single "
            "scheduler or explicit job dependencies."
        ),
        "existing_safeguards": [
            "Duplicate slot guards (_session_recovery_multi_logged, seq keys)",
            "DB checks for prior sends",
        ],
    },
    {
        "id": "recovery_multi_message_slots",
        "title": "Multi-message slot scheduling",
        "summary": "Parallel asyncio tasks per slot with per-slot delay (main._schedule_recovery_multi_slots).",
        "code_anchors": ["main._schedule_recovery_multi_slots"],
        "async_boundary": BOUND_SCHEDULED_JOB,
        "future_execution_roles": [BOUND_SCHEDULED_JOB],
        "worker_safety": [
            SAFETY_REQUIRES_ORDERING,
            SAFETY_PROVIDER_SIDE_EFFECT,
            SAFETY_RETRY_SENSITIVE,
            SAFETY_LIFECYCLE_SENSITIVE,
        ],
        "persistence_assumption": "required",
        "single_process_assumption": True,
        "current_runtime_owner": "fastapi_uvicorn_event_loop_same_process",
        "multi_worker_risk_notes": "Slot index and cap tracked in memory per process.",
        "existing_safeguards": [
            "_session_recovery_multi_attempt_cap",
            "per-slot dedupe keys",
        ],
    },
    {
        "id": "recovery_reason_poll_loop",
        "title": "Reason-tag poll loop before multi scheduling",
        "summary": "asyncio task polling until reason exists (main._poll_recovery_reason_then_schedule_multi).",
        "code_anchors": ["main._poll_recovery_reason_then_schedule_multi"],
        "async_boundary": BOUND_WORKER_CANDIDATE,
        "future_execution_roles": [BOUND_SCHEDULED_JOB],
        "worker_safety": [
            SAFETY_REQUIRES_LOCKING,
            SAFETY_LIFECYCLE_SENSITIVE,
        ],
        "persistence_assumption": "state_in_db",
        "single_process_assumption": True,
        "current_runtime_owner": "fastapi_uvicorn_event_loop_same_process",
        "multi_worker_risk_notes": "Multiple pollers could race; today single-process.",
        "existing_safeguards": ["Recovery reason row in DB"],
    },
    {
        "id": "whatsapp_send_queue_worker",
        "title": "In-process WhatsApp send queue worker",
        "summary": (
            "Per-event-loop asyncio.Queue + worker task; inflight dedupe by "
            "(recovery_key, step, message) (services.whatsapp_queue)."
        ),
        "code_anchors": [
            "services.whatsapp_queue.start_whatsapp_queue_worker",
            "services.whatsapp_queue.enqueue_recovery_whatsapp",
        ],
        "async_boundary": BOUND_WORKER_CANDIDATE,
        "future_execution_roles": [BOUND_WORKER_CANDIDATE, BOUND_RETRY_CANDIDATE],
        "worker_safety": [
            SAFETY_PROVIDER_SIDE_EFFECT,
            SAFETY_RETRY_SENSITIVE,
            SAFETY_REQUIRES_LOCKING,
        ],
        "persistence_assumption": "strongly_recommended",
        "single_process_assumption": True,
        "current_runtime_owner": "asyncio_event_loop_worker_task",
        "multi_worker_risk_notes": (
            "_queue_by_loop and _inflight are per-process; not shared across "
            "workers or machines."
        ),
        "existing_safeguards": [
            "Inflight merge futures",
            "MAX_WA_SEND_ATTEMPTS",
            "Cart recovery log statuses",
        ],
    },
    {
        "id": "whatsapp_provider_send",
        "title": "Twilio / provider send_whatsapp_real",
        "summary": "External HTTP side effect (services.whatsapp_send).",
        "code_anchors": ["services.whatsapp_send.send_whatsapp_real", "main.send_whatsapp"],
        "async_boundary": BOUND_WORKER_CANDIDATE,
        "future_execution_roles": [BOUND_RETRY_CANDIDATE],
        "worker_safety": [
            SAFETY_PROVIDER_SIDE_EFFECT,
            SAFETY_RETRY_SENSITIVE,
        ],
        "persistence_assumption": "strongly_recommended",
        "single_process_assumption": False,
        "current_runtime_owner": "caller_thread_or_async_context",
        "multi_worker_risk_notes": "Idempotency must be enforced at job/message level.",
        "existing_safeguards": ["Queue retry policy optional", "Log persistence"],
    },
    {
        "id": "dev_cartflow_delay_test",
        "title": "Dev-only delayed send experiment",
        "summary": "FastAPI BackgroundTasks + asyncio.sleep (main.dev_cartflow_delay_test).",
        "code_anchors": ["main.dev_cartflow_delay_test", "main._run_dev_cartflow_delay_test_send"],
        "async_boundary": BOUND_SCHEDULED_JOB,
        "future_execution_roles": [BOUND_SCHEDULED_JOB],
        "worker_safety": [SAFETY_PROVIDER_SIDE_EFFECT, SAFETY_RETRY_SENSITIVE],
        "persistence_assumption": "optional",
        "single_process_assumption": True,
        "current_runtime_owner": "fastapi_background_tasks_same_process",
        "multi_worker_risk_notes": "Dev route only; not a production scheduler.",
        "existing_safeguards": ["ENV gating for most /dev routes"],
    },
    {
        "id": "return_to_site_tracking",
        "title": "Return-to-site / user-return signals",
        "summary": (
            "Widget return tracker and API cart-event paths marking user_returned / "
            "behavioral state (static/cartflow_return_tracker.js, main payload handlers)."
        ),
        "code_anchors": [
            "main.api_cart_event",
            "services.behavioral_recovery",
        ],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [BOUND_WORKER_CANDIDATE],
        "worker_safety": [
            SAFETY_LIFECYCLE_SENSITIVE,
            SAFETY_REQUIRES_LOCKING,
        ],
        "persistence_assumption": "state_in_db",
        "single_process_assumption": False,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": "Ordering vs delayed recovery must remain consistent.",
        "existing_safeguards": [
            "cartflow_lifecycle_guard diagnostics",
            "DB-backed abandoned cart / reasons",
        ],
    },
    {
        "id": "behavioral_state_merge",
        "title": "Behavioral merge / durable context updates",
        "summary": "Merging behavioral payloads into stored state (e.g. merge_behavioral_state).",
        "code_anchors": ["services.behavioral_recovery.state_store.merge_behavioral_state"],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [BOUND_WORKER_CANDIDATE],
        "worker_safety": [
            SAFETY_LIFECYCLE_SENSITIVE,
            SAFETY_REQUIRES_LOCKING,
        ],
        "persistence_assumption": "required",
        "single_process_assumption": False,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": "Concurrent merges need version or row locks when distributed.",
        "existing_safeguards": ["ORM transactions", "lifecycle diagnostics"],
    },
    {
        "id": "cart_state_sync_handler",
        "title": "cart_state_sync API handling",
        "summary": "Synchronous handler updating cart snapshot / VIP sync (main._handle_cart_state_sync).",
        "code_anchors": ["main._handle_cart_state_sync", "main.api_cart_event"],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [],
        "worker_safety": [SAFETY_LIFECYCLE_SENSITIVE],
        "persistence_assumption": "state_in_db",
        "single_process_assumption": False,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": "Generally safe multi-worker if DB is source of truth.",
        "existing_safeguards": ["Transaction commit/rollback"],
    },
    {
        "id": "zid_webhook_or_provider_callback",
        "title": "Platform webhooks / provider callbacks",
        "summary": "Inbound HTTP that may upsert carts or trigger side paths (routes/ops, main zid paths).",
        "code_anchors": ["routes.ops", "main (zid / webhook handlers)"],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [BOUND_WORKER_CANDIDATE],
        "worker_safety": [
            SAFETY_REQUIRES_LOCKING,
            SAFETY_LIFECYCLE_SENSITIVE,
        ],
        "persistence_assumption": "required",
        "single_process_assumption": False,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": "Webhook retries from provider may duplicate work.",
        "existing_safeguards": ["Idempotent keys where implemented", "DB uniqueness"],
    },
    {
        "id": "runtime_health_snapshot",
        "title": "Runtime / observability snapshot (read-only)",
        "summary": "Aggregates duplicate_guard, lifecycle, etc. for dashboards (runtime_health_snapshot_readonly).",
        "code_anchors": [
            "services.cartflow_observability_runtime",
            "services.cartflow_runtime_health",
        ],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [],
        "worker_safety": [SAFETY_IDEMPOTENT_SAFE],
        "persistence_assumption": "optional",
        "single_process_assumption": True,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": (
            "Some counters are in-memory per process; multi-worker aggregate "
            "differs from single-node view."
        ),
        "existing_safeguards": ["Read-only snapshots"],
    },
    {
        "id": "admin_operational_summary",
        "title": "Admin operational summary build",
        "summary": "Read-only assembly for admin HTML (build_admin_operational_summary_readonly).",
        "code_anchors": ["services.cartflow_admin_operational_summary"],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [],
        "worker_safety": [SAFETY_IDEMPOTENT_SAFE],
        "persistence_assumption": "optional",
        "single_process_assumption": True,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": "Same as runtime snapshot: per-process diagnostics partial.",
        "existing_safeguards": ["Read-only"],
    },
    {
        "id": "onboarding_dashboard_visibility",
        "title": "Onboarding readiness for merchant dashboard",
        "summary": "get_onboarding_dashboard_visibility / strip rendering inputs.",
        "code_anchors": [
            "services.cartflow_onboarding_readiness",
            "main.dashboard_normal_carts",
        ],
        "async_boundary": BOUND_INLINE_SAFE,
        "future_execution_roles": [],
        "worker_safety": [SAFETY_IDEMPOTENT_SAFE],
        "persistence_assumption": "state_in_db",
        "single_process_assumption": False,
        "current_runtime_owner": "request_handler_inline",
        "multi_worker_risk_notes": "Pure derivation from store rows.",
        "existing_safeguards": ["Read-only for summary"],
    },
]
