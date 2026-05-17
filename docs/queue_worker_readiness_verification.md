# Queue / worker readiness verification

Companion to `docs/cartflow_queue_worker_readiness.md` and `services/cartflow_queue_readiness.py`.  
This document supports **verification and migration planning** — not a queue rollout.

---

## Safe load test (admin)

**Endpoint:** `POST /admin/ops/load-test/cart-event` (admin session cookie required)

| Field | Default | Notes |
|-------|---------|--------|
| `store_slug` | `demo` | Store context for payloads |
| `events_count` | `20` | Max `50` |
| `dry_run_whatsapp` | `true` | Mocks provider send for the run only |
| `reason_tag` | omitted | If set → `cart_abandoned`; else → lite `cart_state_sync` / `add` |
| `phone_present` | `true` | Includes test phone in payload when true |

**Returns:** success/error counts, avg/max duration, slow count (>2500ms), QueuePool timeout delta, background failure delta, DB pool snapshot before/after.

**Does not change:** recovery rules, delay/anti-spam, merchant/widget, or production handler code.

---

## What still runs in-process (asyncio) today

| Area | Examples | Risk under scale |
|------|----------|------------------|
| Recovery delay chains | `asyncio.sleep` + `_run_recovery_*` after abandon | Lost on restart; one process only |
| Multi-slot scheduling | `_schedule_recovery_multi_slots`, second-step tasks | Ordering tied to event loop |
| Reason poll loop | `_poll_recovery_reason_then_schedule_multi` | Competing tasks on hot path |
| WhatsApp in-process queue | `services/whatsapp_queue` | Per-process dedupe only |
| FastAPI `BackgroundTasks` | Dev delay test, some deferrals | Same worker as HTTP |

---

## What should move to queue/worker later

| Priority | Work unit | Why |
|----------|-----------|-----|
| 1 | Delayed recovery send after abandon | Long sleeps hold connections if mis-scoped; durable `run_at` |
| 2 | Provider send (`send_whatsapp_real`) | `provider_side_effect` — retries need idempotency |
| 3 | Multi-message sequence steps | `requires_ordering` |
| 4 | Reason-poll / schedule bridge | Reduce cart-event tail latency |
| 5 | Heavy admin aggregates (optional) | Read-only but can starve pool if co-located |

Keep **inline:** `cart_state_sync` lite path, read-only admin/health, webhooks that must ACK quickly.

---

## Risks under scale

1. **QueuePool exhaustion** — concurrent cart-events + scoped sessions + background DB without `remove()`.
2. **Slow cart-event** — DB warm, ORM scope, scheduling side effects on abandon path.
3. **Duplicate outreach** — in-memory recovery maps are **per process**; horizontal workers need DB/log idempotency.
4. **Blind retries** — WhatsApp and recovery must not retry without “already sent” checks.

---

## Safe migration order

1. Persist `run_at` + job id for delayed recovery (no send logic change).
2. External worker consumes job → calls existing send path once.
3. Shared dedupe/lease (DB or Redis) before provider call.
4. Move multi-slot chains to ordered job DAG.
5. Leave cart-event HTTP path thin: write state → enqueue only.

---

## Idempotency requirements

- Any **customer-visible message** (WhatsApp).
- Recovery schedule per `store + session` (or `recovery_key`).
- Webhook handlers with platform retries.
- Load-test sessions (`loadtest-*`) — safe to ignore in merchant metrics; optional DB cleanup.

---

## Must not retry blindly

- `provider_side_effect` sends (Twilio errors, rate limits).
- Recovery after **conversion** or **return-to-site** flags.
- Behavioral merge / lifecycle transitions (`lifecycle_sensitive`).

---

## Verification checklist

1. Run load test: `events_count=20`, `dry_run_whatsapp=true`.
2. Confirm `queuepool_timeout_count` delta = 0.
3. Confirm `error_count` = 0 and avg/max duration reported.
4. Open `/admin/operational-health` — page loads; optional “آخر اختبار ضغط” line.
5. Single normal `cart_state_sync` or abandon flow still works afterward.

Machine registry: `python -c "from services.cartflow_queue_readiness import get_readiness_summary; print(get_readiness_summary())"`
