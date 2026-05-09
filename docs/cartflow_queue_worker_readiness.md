# CartFlow queue and worker readiness

This document maps **today’s async and deferred behavior** so future adoption of **Celery, RQ, Dramatiq, distributed workers, or external schedulers** can proceed incrementally without surprise rewrites.

**Scope:** architecture readiness and classification only. **No** queue product, **no** Redis, **no** change to recovery/WhatsApp/decision/admin UX.

---

## Part 1 — Async boundary mapping

Each operation is classified for **where it runs today** vs **where it could move**:

| Classification | Meaning |
|----------------|---------|
| `inline_safe` | Handled inside the HTTP/request path (sync or short async handler). |
| `future_worker_candidate` | Today tied to the app process (tasks, loops); natural fit for a worker pool later. |
| `future_scheduled_job` | Time-delayed or calendar-like execution (sleep, follow-up gaps, multi-slot delays). |
| `future_retry_candidate` | Provider or network actions where retry policy belongs outside the request. |

### Operations (high level)

| Area | Examples | Typical boundary today | Future roles |
|------|----------|------------------------|--------------|
| Recovery after abandon | `handle_cart_abandoned`, `_run_recovery_dispatch_*`, `_run_recovery_sequence_*` | `future_worker_candidate` + `future_scheduled_job` | Scheduled job, retry-backed worker |
| Multi-message / sequential | `_schedule_recovery_multi_slots`, second-step `asyncio.create_task` | `future_scheduled_job` | Ordered job chain / DAG |
| Reason poll | `_poll_recovery_reason_then_schedule_multi` | `future_worker_candidate` | Scheduled poll or event-driven |
| WhatsApp in-process queue | `services.whatsapp_queue` | `future_worker_candidate` | External queue + worker |
| Provider send | `send_whatsapp_real` / `send_whatsapp` | `future_retry_candidate` | Idempotent job with caps |
| Dev delay test | `dev_cartflow_delay_test` + `BackgroundTasks` | `future_scheduled_job` | Dev-only; not production scheduler |
| Return-to-site / cart-event | return tracker, `user_returned`, conversion flags | `inline_safe` (today) | Optional async consumer later |
| Behavioral merge | `merge_behavioral_state`, link tracking | `inline_safe` | Worker if write contention grows |
| cart_state_sync | `_handle_cart_state_sync` | `inline_safe` | Usually stay inline |
| Webhooks / Zid-style callbacks | ops routes, cart upsert | `inline_safe` | Optional queue for slow providers |
| Runtime / admin **read-only** snapshots | `runtime_health_snapshot_readonly`, admin summary | `inline_safe` | Stay inline; aggregates may need shared store |

Authoritative machine-readable list: `services/cartflow_queue_readiness.py` → `get_queue_candidate_registry()`.

---

## Part 3 — Worker safety classification

Tags used in code (see `get_worker_safety_classifications()`):

| Tag | Intent |
|-----|--------|
| `idempotent_safe` | Safe to run multiple times without extra external harm (read-only snapshots). |
| `requires_locking` | Concurrent workers could double-apply; needs DB row lock, lease, or unique job key. |
| `requires_ordering` | Step 2 must not run before step 1 semantics are settled (recovery sequences). |
| `provider_side_effect` | Calls WhatsApp/Twilio or other external APIs — **never blind retry** without idempotency. |
| `retry_sensitive` | Backoff and max attempts must be explicit; duplicates hurt UX or provider trust. |
| `lifecycle_sensitive` | Interacts with conversion, return-to-site, or abandonment lifecycle ordering. |

---

## Part 5 — Runtime ownership and multi-worker assumptions

### What **owns** execution today (typical)

- **Uvicorn + asyncio event loop (single process):** recovery `asyncio.create_task` chains, multi-slot tasks, reason poll loop.
- **Same-process BackgroundTasks:** dev delay test only (not production recovery).
- **Per-event-loop WhatsApp queue:** `services.whatsapp_queue` (`_queue_by_loop`, worker task started at app startup).
- **Request thread/handler:** cart_state_sync, many API mutations, read-only dashboard assembly.

### What **breaks or skews** under naive multi-worker

- **In-memory recovery maps** (e.g. `_session_recovery_*`, locks under `_recovery_session_lock`): **process-local**. Another worker does not see them; **DB + idempotent jobs** must become the source of truth before scaling workers horizontally.
- **WhatsApp queue dedupe** (`_inflight`, `_queue_by_loop`): **per process / per loop**. Distributed duplicate sends are possible without a shared dedupe or lease.
- **Timing assumptions:** `asyncio.sleep` delays are not durable across restarts; a real scheduler needs **persisted** `run_at` / job rows.
- **Runtime health / duplicate_guard counters:** diagnostic aggregates may **differ per instance** when multiple processes run.

### What **already helps**

- **Persistence:** `CartRecoveryLog`, reasons, abandoned carts — ground truth for “what was sent”.
- **Duplicate guard / lifecycle diagnostics:** observability for conflicts (not a distributed lock).
- **WhatsApp queue:** serializes and retries **within one process**; merge of inflight keys for same step/message.

---

## Part 6 — Queue migration risk visibility

Use:

```python
from services.cartflow_queue_readiness import get_readiness_summary
get_readiness_summary()
```

Returns aggregates such as:

- `queue_ready_operations` — ids that are not purely `inline_safe` for scheduling.
- `operations_requiring_locking`
- `operations_requiring_persistence`
- `operations_with_single_runtime_assumptions`

**Admin/dev safe:** no enqueue, no DB writes from this API alone.

---

## Part 4 — Diagnostics (logging only)

When you need structured traces:

```text
CARTFLOW_QUEUE_READINESS_LOG=1
```

Logs lines like:

```text
[CARTFLOW QUEUE READINESS] operation=recovery_send classification=provider_side_effect ...
```

Implemented by `emit_queue_readiness_diagnostic()` in `services/cartflow_queue_readiness.py`. Default without env: **DEBUG** only (typically silent). **Nothing is enqueued.**

---

## Part 7 — Operational safety notes

**Do not retry blindly**

- **WhatsApp / provider sends:** use message-level idempotency keys, provider status, and persisted “already sent” flags; respect `retry_sensitive`.
- **Recovery scheduling:** a second delayed job for the same session can duplicate outreach unless **locking** or **log-based skip** is applied before send.
- **Behavioral merges:** replaying the same event may corrupt counters; prefer **event ids** or **versioned state**.

**Require idempotency**

- Any job that can deliver a **customer-visible message** (`provider_side_effect`).
- Webhook handlers if the platform retries delivery.

**Require lifecycle reconciliation**

- Return-to-site, conversion, and abandonment must be ordered relative to **scheduled** recovery; use DB state, not only memory flags, when moving to workers.

**Provider-safe execution**

- Rate limits, opt-out, and Twilio error classes should surface into **job outcome**, not infinite retry loops.

---

## Part 8 — Tests

See `tests/test_cartflow_queue_readiness.py` for registry shape, classification consistency, and summary payload guarantees.

---

## Part 9 — Explicit non-goals

- No Celery/RQ/Dramatiq/Redis/cron containers in this change set.
- No rewrite of `handle_cart_abandoned`, decision engine, or merchant/admin surfaces.
- No distributed locks — documentation only for where they **will** be needed later.

---

## References in code

- Registry: `services/cartflow_queue_readiness.py`
- Recovery tasks: `main.handle_cart_abandoned`, `main._run_recovery_sequence_after_cart_abandoned*`, `main._schedule_recovery_multi_slots`
- WhatsApp queue: `services/whatsapp_queue.py`
- Duplicate / lifecycle context: `services/cartflow_duplicate_guard.py`, `services/cartflow_lifecycle_guard.py`
- Admin read models: `services/cartflow_admin_operational_summary.py`
