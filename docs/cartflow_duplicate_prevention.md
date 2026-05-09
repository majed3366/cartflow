# CartFlow duplicate prevention (operational hardening)

This document describes the **in-process**, **deterministic** duplicate safeguards added around recovery scheduling, outbound WhatsApp attempts, behavioral merges, and dashboard diagnostics. It does not replace the decision engine, VIP handling, templates, or provider integrations.

## Philosophy

- **Single source of truth** for duplicate bookkeeping: `services/cartflow_duplicate_guard.py`.
- **Log correlation** via the canonical prefix `[CARTFLOW DUPLICATE]` with a stable `type=` field.
- **No silent double execution** where overlapping tasks could hit the provider twice for the same logical attempt.
- **Lightweight**: threading locks and monotonic clocks only — no distributed locks, no new workers or queues.

## Canonical signatures

| Signature | Purpose |
|-----------|---------|
| `sched:{store_slug}\|{session_id}\|{cart_id}` | Recovery scheduling scope |
| `send:{store_slug}\|{session_id}\|{cart_id}\|step={n}` | Logical send / attempt index |
| `beh_ret:…` | Behavioral return-to-site merge (store, session, cart, timestamps, page flags, short context) |

These strings are suitable for logs and diagnostics; they are not secrets.

## Idempotency strategy

1. **Schedule**: Existing `_try_claim_recovery_session(recovery_key)` remains authoritative. On duplicate claim, the guard emits `type=recovery_schedule_duplicate` and records a symbolic anomaly.
2. **Send (DB)**: Existing `_cart_recovery_log_has_successful_send_for_step` remains authoritative. Duplicates log `type=send_duplicate_blocked` with `reason=already_sent_log` (etc.).
3. **Send (in-flight)**: Before `send_whatsapp`, the guard claims a short TTL slot per `(recovery_key, step)`. Overlapping tasks log `type=send_duplicate_blocked` with `subtype=inflight_overlap`, persist `skipped_duplicate`, and **do not** call the provider.
4. **Behavioral return**: Identical merge signatures within ~45s are skipped at the DB merge entrypoint (compatible with identity safeguards — no trust flags are altered on skip).
5. **Cart events**: `should_process_cart_event_burst(...)` is available for optional rapid dedupe of identical `(store, session, cart, event)` keys; default prod path relies on schedule/send guards to avoid breaking legitimate back-to-back API timing in tests.

## Scheduling safeguards

- Duplicate schedule attempts → `[CARTFLOW DUPLICATE] type=recovery_schedule_duplicate`
- Duplicate multi-slot / sequential / single-session delay slots → `type=recovery_slot_duplicate`

## Send safeguards

- Duplicate logical send (log already has success for step) → `send_duplicate_blocked`
- In-flight overlap for same step → `send_duplicate_blocked` + `skipped_duplicate` row
- Pre-provider **diagnostics only** for impossible lifecycle overlaps (`send_after_conversion`, `send_after_return`, `send_after_reply`): logs `type=lifecycle_conflict` and may increment buffered anomalies — **no** extra business cleanup.

## Behavioral safeguards

- Return merges: `try_consume_behavioral_return_merge(signature=...) → False` skips the merge and logs `type=duplicate_behavioral_merge`.

## Runtime visibility

`build_runtime_health_snapshot()` augments `duplicate_protection_runtime` with:

- `duplicate_prevention_runtime_ok` — false only if internal inflight map grows unusually large (sanity bound).
- `duplicate_anomaly_count` — count of recent buffered anomalies whose types belong to the duplicate/send/lifecycle/dashboard set.
- `duplicate_send_blocked_recently` — whether a duplicate send was blocked in the last few minutes (process-local).
- `duplicate_guard_counters` / `duplicate_inflight_send_keys` — shallow diagnostics.

Trust derivation treats unhealthy duplicate prevention as **warning/degraded** signal input.

## Dashboard / merchant hints

`recovery_blocker_display` maps `skipped_duplicate` → `duplicate_attempt_blocked` with merchant-safe Arabic copy (no internal keys in customer-facing text).

## Known limitations

- All guards are **per-process memory**. Horizontal scale without shared state can still duplicate work across instances until architecture moves to a shared dedupe or queue.
- Lifecycle conflict logs may fire on rare races; they are observability-only unless combined with existing gates.
- Cart-event burst helper is conservative; wiring it too aggressively can drop legitimate rapid events.

## Future queue / worker considerations

If recovery moves to a background worker:

- Persist canonical signatures or idempotency keys in Redis/DB with TTL.
- Reuse the same `type=` strings in worker logs for trace continuity.
- Replace in-flight TTL maps with single-flight claims on the queue message id.
