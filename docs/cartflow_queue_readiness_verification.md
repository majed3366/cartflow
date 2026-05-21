# CartFlow — Queue Readiness Verification Matrix (Reliability Program v1, Part 7)

**Date (UTC):** 2026-05-19  
**Purpose:** Practical checklist to prove the **current** recovery runtime is ready for a future queue/worker migration **without** adding queue infrastructure.  
**Companion docs:** `docs/cartflow_queue_worker_readiness.md` (architecture audit), `services/recovery_execution_boundary.py` (execution entry).

---

## Executive summary — are we queue-ready?

| Area | Status | Notes |
|------|--------|--------|
| **Durable schedule + claim gate** | Ready | `recovery_schedules` + `claim_recovery_schedule_execution` |
| **Single execution boundary** | Ready | `execute_recovery_schedule(schedule_id \| recovery_key+step, source)` |
| **Restart resume** | Ready | Startup scan → same boundary as live post-delay |
| **Send idempotency (DB)** | Ready | `CartRecoveryLog` before provider |
| **Stale `running` repair** | Ready | Startup/due scan only; evidence-based terminal |
| **Terminal protection** | Ready | No reclaim of `completed`; no downgrade |
| **Delay source of truth** | Ready | `schedule_timing` / unified gate |
| **Store context** | Ready | Canonical `store_slug` from `recovery_key` |
| **Scheduling / delay wait** | **Partial** | `services/recovery_delay_dispatcher.dispatch_recovery_schedule` owns in-process wait; replace module for queue/cron later |
| **Session in-memory guards** | **Partial** | Boundary is DB-only; pre-delay path still uses `_session_recovery_*` dicts |
| **Multi-worker dispatch** | **Designed, not deployed** | Claim is DB-atomic; needs real queue + lease TTL ops |

**Verdict:** Safe to adopt a **worker that calls `execute_recovery_schedule`** for the **post-delay execution** phase. **Before** turning off in-process asyncio, migrate **scheduling** (enqueue at abandon, worker polls `due_at`) and document lease/stale thresholds per environment.

---

## Automated test map

| Scenario (below) | Automated test(s) |
|------------------|-------------------|
| Delay dispatcher → execution | `tests/test_recovery_delay_dispatcher.py` |
| Execution boundary duplicate | `tests/test_recovery_execution_boundary.py::test_second_execute_skipped_after_claim`, `tests/test_cartflow_queue_readiness_verification.py::test_scheduled_row_double_execute_single_run` |
| Terminal cannot re-execute | `tests/test_recovery_execution_boundary.py::test_skips_terminal_schedule`, `tests/test_recovery_schedule_claim.py::test_terminal_not_claimable` |
| Stale running + send evidence → `completed` | `tests/test_recovery_restart_survival.py::test_stale_running_finalized_when_mock_sent_evidence`, `tests/test_cartflow_queue_readiness_verification.py::test_stale_running_with_send_evidence_finalizes_completed` |
| WA idempotency blocks provider | `tests/test_recovery_whatsapp_idempotency.py`, `tests/test_cartflow_queue_readiness_verification.py::test_idempotency_hit_does_not_invoke_provider` |
| Resume duplicate dispatch | `tests/test_recovery_restart_survival.py::test_scenario_d_duplicate_resume_claim` |
| Terminal no overwrite | `tests/test_recovery_schedule_claim.py::test_terminal_no_overwrite_completed` |
| Provider failure retry | `tests/test_recovery_whatsapp_idempotency.py::test_whatsapp_failed_does_not_block` |
| Unified delay | `tests/test_recovery_delay_unified.py` |
| Store isolation | `tests/test_recovery_store_context_isolation.py`, `tests/test_dashboard_trigger_templates.py` |

**Run (focused):**

```bash
python -m pytest tests/test_recovery_delay_dispatcher.py tests/test_cartflow_queue_readiness_verification.py tests/test_recovery_execution_boundary.py tests/test_recovery_restart_survival.py tests/test_recovery_schedule_claim.py tests/test_recovery_whatsapp_idempotency.py tests/test_recovery_delay_unified.py -q
```

**Manual / staging:** Scenarios marked *manual* below still require a running app + widget abandon or process restart.

---

## Verification matrix

### 1. Normal recovery execution

| Field | Detail |
|-------|--------|
| **Setup** | Demo store, reason template enabled, phone on abandon, delay > 0 (e.g. 1 min). |
| **Trigger** | Widget: capture reason → `cart_abandoned` (or `POST /api/cart-event`). |
| **Expected logs** | `[RECOVERY DELAY SCHEDULED]` / `[DELAY STARTED]` → `[DELAY FINISHED]` → `[RECOVERY EXECUTION ENTRY]` → `[RECOVERY CLAIM ATTEMPT]` → `[RECOVERY CLAIMED]` → `[RECOVERY EXECUTION CLAIMED]` → send path → `[RECOVERY EXECUTION FINISHED]` → `[RECOVERY TERMINAL UPDATE]` `to_status=completed` (or skip reason if gates block). |
| **Expected DB** | `recovery_schedules`: `scheduled` → `running` → terminal (`completed`, `skipped_*`, or `whatsapp_failed`). `CartRecoveryLog`: `queued` then `mock_sent`/`sent_real` or skip status. |
| **Expected WhatsApp** | One provider attempt when gates allow; message from template engine. |
| **Pass** | Exactly one claim per step; one send (or documented skip); schedule not left `running`. |
| **Fail** | Stuck `running`, double send, or no durable row after abandon. |
| **Automation** | Partial — boundary unit tests mock post-delay; full path *manual*. |

---

### 2. Restart resume

| Field | Detail |
|-------|--------|
| **Setup** | Durable row `scheduled`, `due_at` in the past; process restarted (or `run_recovery_resume_scan_async` / dev verify). |
| **Trigger** | App startup (`CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1`) or `GET /dev/recovery-restart-survival-verify?action=scan`. |
| **Expected logs** | `[RECOVERY RESUME SCAN]` → `[RECOVERY RESUME CANDIDATE]` → `[RECOVERY RESUME SENT]` → `[RECOVERY EXECUTION ENTRY]` `source=resume_scan` → claim → post-delay recovery → `[RECOVERY EXECUTION FINISHED]`. |
| **Expected DB** | Row was `scheduled`; after dispatch claim → `running`; after execution → terminal. |
| **Expected WhatsApp** | Same as normal if safety allows (`evaluate_resume_safety` = allowed). |
| **Pass** | Send occurs after restart without re-waiting full delay; schedule finalized. |
| **Fail** | Row stays `scheduled` forever, or resume blocked without terminal reason. |
| **Automation** | `tests/test_recovery_restart_survival.py` (scenarios A–E, finalize). |

---

### 3. Duplicate live + resume execution

| Field | Detail |
|-------|--------|
| **Setup** | Same `(recovery_key, step)` — e.g. live task still running **and** resume scan fires, or two resume dispatches. |
| **Trigger** | Second `execute_recovery_schedule` or second `resume_one_schedule` while row `running`/`completed`. |
| **Expected logs** | First: `[RECOVERY EXECUTION CLAIMED]`. Second: `[RECOVERY CLAIM SKIPPED]` or `[RECOVERY EXECUTION SKIPPED]` `detail=already_running` / `already_terminal` / `duplicate_resume_claim`. |
| **Expected DB** | One `running` holder; no second send; terminal set once. |
| **Expected WhatsApp** | At most one successful send per step. |
| **Pass** | Second path skips before provider; `CartRecoveryLog` not duplicated with `sent_real`. |
| **Fail** | Two claims both send, or race leaves duplicate `queued` + send. |
| **Automation** | `test_scenario_d_duplicate_resume_claim`, `test_second_execute_skipped_after_claim`, `test_scheduled_row_double_execute_single_run`. |

---

### 4. Duplicate WhatsApp protection

| Field | Detail |
|-------|--------|
| **Setup** | Existing `CartRecoveryLog` for same session/cart/step with `mock_sent`, `sent_real`, or `queued`. |
| **Trigger** | Recovery execution reaches send gate (live, resume, or boundary re-entry). |
| **Expected logs** | `[WA IDEMPOTENCY CHECK]` → `[WA IDEMPOTENCY HIT]`; recovery skip logs; schedule `skipped_duplicate`. |
| **Expected DB** | `recovery_schedules.status=skipped_duplicate`; new log `skipped_duplicate` optional; **no** second `sent_real`. |
| **Expected WhatsApp** | Provider **not** called on HIT. |
| **Pass** | HIT path returns before `send_whatsapp`; idempotency tests green. |
| **Fail** | Second Twilio call for same step/phone. |
| **Automation** | `tests/test_recovery_whatsapp_idempotency.py`, `test_idempotency_hit_does_not_invoke_provider`. |

---

### 5. Stale running repair

| Field | Detail |
|-------|--------|
| **Setup** | `recovery_schedules.status=running`, `updated_at` older than `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS` (default 600s). |
| **Trigger** | `run_recovery_resume_scan_async` / `repair_stale_running_recovery_schedules` (startup only, not mid-flight repair of fresh `running`). |
| **Expected logs** | `[RECOVERY STALE CHECK]` → `[RECOVERY STALE DETECTED]` → `[RECOVERY STALE REPAIRED]` or `[RECOVERY STALE FINALIZED]`. |
| **Expected DB** | With send evidence (`mock_sent`/`sent_real`): `completed`. With `skipped_duplicate` log: `skipped_duplicate`. Else: `failed_resume_stale` — **not** reset to `scheduled`. |
| **Expected WhatsApp** | No new send on repair (terminal only). |
| **Pass** | No infinite `running`; evidence matches terminal. |
| **Fail** | Stale row rescheduled to `scheduled` and spams sends. |
| **Automation** | `tests/test_recovery_restart_survival.py` (stale suite), `test_stale_running_with_send_evidence_finalizes_completed`. |

---

### 6. Terminal status protection

| Field | Detail |
|-------|--------|
| **Setup** | Row already `completed`, `skipped_duplicate`, `failed_resume`, etc. |
| **Trigger** | `claim_recovery_schedule_execution` or `execute_recovery_schedule` or `finalize_recovery_schedule_durable` with weaker status. |
| **Expected logs** | `[RECOVERY CLAIM SKIPPED]` `already_terminal:completed` or `[RECOVERY EXECUTION SKIPPED]`; `[RECOVERY TERMINAL UPDATE]` skipped when not `running`. |
| **Expected DB** | Status unchanged (especially `completed` not → `skipped_duplicate`). |
| **Expected WhatsApp** | None. |
| **Pass** | Terminal is absorbing; no downgrade. |
| **Fail** | `completed` overwritten or reclaim sends again. |
| **Automation** | `test_terminal_not_claimable`, `test_terminal_no_overwrite_completed`, `test_skips_terminal_schedule`. |

---

### 7. Provider failure retry safety

| Field | Detail |
|-------|--------|
| **Setup** | Prior `CartRecoveryLog.status=whatsapp_failed` for the step (no successful send). |
| **Trigger** | Retry via resume or new execution after failure. |
| **Expected logs** | `[WA IDEMPOTENCY CHECK]` → `[WA IDEMPOTENCY MISS]` (failure does not count as sent). |
| **Expected DB** | Schedule may return to `running` then `completed` or fail again; not blocked by idempotency. |
| **Expected WhatsApp** | Retry allowed to provider. |
| **Pass** | Failed send does not permanently block; no false HIT. |
| **Fail** | `whatsapp_failed` treated as success and blocks retry. |
| **Automation** | `test_whatsapp_failed_does_not_block`. |

---

### 8. Future multi-worker claim behavior

| Field | Detail |
|-------|--------|
| **Setup** | Two logical workers (simulated: concurrent `claim_recovery_schedule_execution` on same `scheduled` row). |
| **Trigger** | Both call claim; only one `UPDATE … WHERE status=scheduled` succeeds. |
| **Expected logs** | One `[RECOVERY CLAIMED]`; other `[RECOVERY CLAIM SKIPPED]` `claim_race_lost` or `already_running`. |
| **Expected DB** | Single `running` row; one execution finishes to terminal. |
| **Expected WhatsApp** | One send. |
| **Pass** | DB claim is authoritative; workers are interchangeable if they call `execute_recovery_schedule`. |
| **Fail** | Both workers proceed to send without claim. |
| **Automation** | `test_second_claim_skipped` in `test_recovery_schedule_claim.py`; *production* needs queue visibility + lease metrics (*manual* ops). |
| **Before queue** | Add worker heartbeat, `lease_expires_at`, and alert on `running` age — not in runtime today. |

---

### 9. No in-memory dependency in execution boundary

| Field | Detail |
|-------|--------|
| **Setup** | Cold process: no `_session_recovery_logged` primed; durable row + `context_json` populated. |
| **Trigger** | `execute_recovery_schedule(schedule_id=…, source=test\|resume_scan)`. |
| **Expected logs** | `[RECOVERY EXECUTION ENTRY]` with `schedule_id=`; context rebuilt from DB (`recovery_post_delay_only`). |
| **Expected DB** | Claim/finalize via row id / `recovery_key` only. |
| **Expected WhatsApp** | Driven by DB context + store row lookup, not session dict. |
| **Pass** | Boundary accepts only durable identifiers; safe to call twice. |
| **Fail** | Boundary requires pre-populated in-memory task or local dict for claim. |
| **Automation** | `test_claims_and_runs_post_delay` asserts `recovery_post_delay_only` + `schedule_execution_claimed`; resolve by `schedule_id` test. |
| **Caveat** | Pre-delay scheduling still uses in-memory guards; queue migration must enqueue **after** persist, worker runs boundary only. |

---

### 10. Store context isolation

| Field | Detail |
|-------|--------|
| **Setup** | Two stores (`demo`, `demo2` or loadtest rows); template/delay differ per store. |
| **Trigger** | Abandon on store A; dashboard/templates for store A slug. |
| **Expected logs** | `[STORE LOOKUP]` `canonical_store=` matches `recovery_key` prefix; `[TEMPLATE LOOKUP]` uses matched store id. |
| **Expected DB** | `recovery_schedules.store_slug` matches canonical slug from key. |
| **Expected WhatsApp** | Template/delay from store A, not B. |
| **Pass** | Runtime and dashboard use same canonical row (`dashboard_store_context` / `recovery_store_context`). |
| **Fail** | Latest `Store.id` or wrong slug serves wrong template. |
| **Automation** | `tests/test_recovery_store_context_isolation.py`, `tests/test_dashboard_trigger_templates.py`. |

---

### 11. Unified delay source

| Field | Detail |
|-------|--------|
| **Setup** | Store with reason template delay (e.g. 1 min vs 2 h). |
| **Trigger** | Abandon with reason; observe schedule + final gate. |
| **Expected logs** | `[RECOVERY DELAY RESOLVED]` / `[RECOVERY DELAY SCHEDULED]` with same `effective_delay_seconds` and `source` as `[FINAL DELAY GATE]`. |
| **Expected DB** | `recovery_schedules.effective_delay_seconds` / `context_json.schedule_timing` consistent with gate. |
| **Expected WhatsApp** | Send only after unified effective delay elapsed (unless step>1 / multi-slot rules skip activity check). |
| **Pass** | No drift between sleep duration and `should_send_whatsapp` gate. |
| **Fail** | Scheduled 60s but gate uses legacy store minutes only. |
| **Automation** | `tests/test_recovery_delay_unified.py`. |

---

## Pre-queue adoption checklist (ops)

- [ ] All automated tests in **Automated test map** pass in CI.
- [ ] Manual normal abandon → delay → WA on staging (scenario 1).
- [ ] Manual restart with due row (scenario 2).
- [ ] Confirm `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS` appropriate for expected job length.
- [ ] Document worker entrypoint: `await execute_recovery_schedule(schedule_id=row.id, source="queue_worker")`.
- [ ] Plan removal of in-process `asyncio.sleep` once enqueue + worker poll `due_at` exists.

---

## What remains before real queue adoption

1. **Job enqueue** at abandon instead of (or in addition to) `asyncio.create_task` sleep.  
2. **Worker process** calling `execute_recovery_schedule` exclusively for execution.  
3. **Lease / heartbeat** column or external lock TTL for multi-worker stale detection.  
4. **Metrics** on claim skip reasons, stale repairs, idempotency HIT rate, `running` age.  
5. **Deprecate** in-memory `_session_recovery_*` for post-restart paths (already bypassed on `resume_from_durable_schedule` / boundary).
