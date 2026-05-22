# Queue / Worker Maturity v1 — Audit Report

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit of delayed recovery reliability under restart, duplicate dispatch, stale jobs, and idempotency.  
**Commit:** `audit: verify queue worker maturity v1`  
**Companion:** `docs/cartflow_queue_worker_readiness.md`, `docs/cartflow_queue_readiness_verification.md`

No changes to lifecycle, Purchase Truth, Reply Intent, Continuation, WhatsApp send behavior, widget, or dashboard.

---

## Executive verdict

| Area | Maturity | Notes |
|------|----------|--------|
| Durable `RecoverySchedule` + `due_at` | **High** | Survives restart; resume scan + future rearm |
| DB claim `scheduled → running` | **High** | Atomic; duplicate execute blocked |
| Stale `running` repair | **High** | Evidence-based terminal (`completed`, `skipped_duplicate`, `failed_resume_stale`) |
| WA send idempotency (DB) | **High** | `CartRecoveryLog` before provider |
| In-process asyncio delay | **Partial** | Coexists with durable row — dual-path risk |
| Multi-worker / horizontal scale | **Designed, not deployed** | Claim is DB-safe; no distributed queue lease yet |
| Dedicated recovery worker queue | **Not present** | Delay = `asyncio.sleep` + `recovery_delay_dispatcher` |

**Automated audit:** `pytest tests/test_queue_worker_maturity_audit_v1.py -q`

**Focused reliability suite:**

```bash
python -m pytest tests/test_recovery_restart_survival.py tests/test_recovery_execution_boundary.py tests/test_recovery_schedule_claim.py tests/test_recovery_whatsapp_idempotency.py tests/test_cartflow_queue_readiness_verification.py tests/test_recovery_delay_dispatcher.py tests/test_queue_worker_maturity_audit_v1.py -q
```

---

## Verification matrix (10 scenarios)

| # | Scenario | Expected | Observed (code + tests) | PASS / FAIL | Risk | Priority |
|---|----------|----------|-------------------------|-------------|------|----------|
| 1 | **Restart before `due_at`** | Schedule remains `scheduled`; future rearm; no early send | `rearm_one_future_scheduled_recovery` + `spawn_recovery_schedule_dispatch`; `test_future_scheduled_rearms_dispatcher_without_early_execute` | **PASS** | Low | — |
| 2 | **Restart after `due_at`** | Resume scan dispatches; claim → execute → terminal | `run_recovery_resume_scan_sync` / `resume_one_schedule` → `execute_recovery_schedule`; `test_scenario_a_due_after_restart_discoverable`, `test_resume_executor_finalizes_running_not_stuck` | **PASS** | Low | — |
| 3 | **Duplicate dispatch** | Second path skipped (`already_running` / `already_terminal` / one `create_task`) | `claim_recovery_schedule_execution`, `execute_recovery_schedule`; `test_scenario_d_duplicate_resume_claim`, `test_second_execute_skipped_after_claim`, `test_scheduled_row_double_execute_single_run` | **PASS** | Medium if live task + resume race without claim | P2 |
| 4 | **Recovery already running** | Second execute returns `already_running`; no second send | `claim` rejects non-`scheduled`; `test_second_execute_skipped_after_claim` | **PASS** | Low | — |
| 5 | **Stale running recovery** | Age > threshold → `failed_resume_stale` or evidence → `completed` / `skipped_duplicate` | `reconcile_stale_running_schedules`, `repair_stale_running_recovery_schedules`; stale tests in restart_survival + queue verification | **PASS** | Low | P2 ops tuning `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS` |
| 6 | **RecoverySchedule resume** | Startup scan + dev verify; safety gates | `evaluate_resume_safety`, `CARTFLOW_RECOVERY_RESUME_ON_STARTUP`; scenarios A–E, purchase/return/sent blocks | **PASS** | Medium — in-memory guards still on pre-delay path | P2 |
| 7 | **Multi-worker collision** | Single claim per row; DB idempotency | SQL `scheduled→running` update; **no** separate worker processes today; Uvicorn multi-worker + in-memory dicts **not** fully isolated | **PARTIAL** | **High** without dedicated scheduler + `RESUME_ON_STARTUP=0` on API | **P1** |
| 8 | **WA idempotency** | HIT blocks provider; MISS allows one send | `check_whatsapp_recovery_send_idempotency`; `test_recovery_whatsapp_idempotency`, `test_idempotency_hit_does_not_invoke_provider` | **PASS** | Low | — |
| 9 | **Dead schedule recovery** | Orphan `scheduled` past due picked up; future rows rearmed not lost | Resume scan `due_processed`; persist discoverable; no infinite `running` without repair | **PASS** (automated); *manual* full abandon→restart | **PARTIAL** manual | P2 |
| 10 | **Recovery terminal states** | Terminal rows not re-executed; `completed` not downgraded | `_TERMINAL` frozenset; `test_skips_terminal_schedule`, `test_terminal_completed_cannot_re_execute`, `test_terminal_not_claimable` | **PASS** | Low | — |

---

## Scenario detail

### 1 — Restart before `due_at`

- **Expected:** Row stays `scheduled`; dispatcher re-armed with preserved `due_at`; logs `[RECOVERY FUTURE REARM REARMED]`.
- **Observed:** `recovery_restart_survival.rearm_one_future_scheduled_recovery`; per-process `_future_rearm_spawned` dedupes spawn.
- **Verified:** `test_future_scheduled_rearms_dispatcher_without_early_execute`.

### 2 — Restart after `due_at`

- **Expected:** `[RECOVERY RESUME SCAN]` → execute via `execute_recovery_schedule(source=resume_scan)`.
- **Observed:** Dry-run and live scan in `run_recovery_resume_scan_sync`; finalize leaves non-`running`.
- **Verified:** `test_scenario_a_due_after_restart_discoverable`, `test_resume_executor_finalizes_running_not_stuck`.

### 3 — Duplicate dispatch

- **Expected:** At most one post-delay execution per `(recovery_key, step)`.
- **Observed:** DB claim + `resume_one_schedule` single `asyncio.create_task` guard.
- **Verified:** duplicate tests above.

### 4 — Recovery already running

- **Expected:** `execute_recovery_schedule` → `reason=already_running`.
- **Observed:** `claim_recovery_schedule_execution` with row already `running`.

### 5 — Stale running recovery

- **Expected:** Stale detection; terminal from log evidence when send already happened.
- **Observed:** Default 600s (`CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS`); repair promotes to `completed` / `skipped_duplicate`.
- **Verified:** `test_stale_running_*` family.

### 6 — RecoverySchedule resume

- **Expected:** Resume respects purchase, return, already_sent, store mismatch.
- **Observed:** `evaluate_resume_safety` → `skipped_resume_unsafe` or allow.
- **Verified:** scenarios B, C, E, already_sent in `test_recovery_restart_survival.py`.

### 7 — Multi-worker collision

- **Expected (future):** One lease/claim per schedule across processes.
- **Observed:** DB claim works for **post-delay boundary**; **pre-delay** still uses `_session_recovery_*` dicts and `asyncio.create_task` in the HTTP process.
- **Verdict:** **PARTIAL** — safe for single API process + DB boundary; **not** proven under N Uvicorn workers without env discipline.

### 8 — WA idempotency

- **Expected:** `[WA IDEMPOTENCY HIT]` → no `send_whatsapp`.
- **Observed:** `services/recovery_whatsapp_idempotency.py` queries `CartRecoveryLog` block statuses.

### 9 — Dead schedule recovery

- **Expected:** Past-due `scheduled` rows not abandoned forever.
- **Observed:** Resume scan processes `due_now`; dev endpoint `GET /dev/recovery-restart-survival-verify?action=scan|inspect`.
- **Manual PASS criteria:** After kill + restart, one send or documented terminal skip; schedule not stuck `scheduled` > 2× delay.

### 10 — Recovery terminal states

- **Terminal set:** `completed`, `cancelled`, `skipped_resume_unsafe`, `needs_review`, `failed_resume`, `failed_resume_stale`, `skipped_duplicate`, `skipped_no_phone`, `skipped_no_reason`, `whatsapp_failed`.
- **Protected:** `completed` not downgraded without override.

---

## Real verification (deploy / staging)

**Prerequisites:** Deploy includes restart survival + execution boundary (commits through Reliability Program v1). Set `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1` on the process that should scan (typically API startup).

| Step | Action | PASS if |
|------|--------|---------|
| A | Abandon cart with phone + reason; note `recovery_key` / `schedule_id` in logs | `[RECOVERY DELAY SCHEDULED]` + `recovery_schedules` row `scheduled` |
| B | Restart process **before** `due_at` | Row still `scheduled`; `[RECOVERY FUTURE REARM REARMED]` or equivalent; no send |
| C | Restart **after** `due_at` | `[RECOVERY RESUME SCAN]` → send or terminal skip; row ≠ `running` |
| D | `GET /dev/recovery-restart-survival-verify?action=inspect` | `persistence.table=recovery_schedules` |
| E | Trigger duplicate resume (scan twice) | Second skip; one send max |
| F | `POST /api/conversion` with `purchase_completed` then scan | Resume blocked; schedule terminal/skip |

**Overall PASS:** Scenarios 1–6 and 8–10 automated green; 7 accepted as PARTIAL until queue worker; manual A–F succeed on staging.

**Overall FAIL:** Stuck `running` > stale threshold without repair; double `sent_real` same step; past-due `scheduled` never processed after restart.

---

## Gaps

### Closed gaps ✅

- Durable schedule persistence and discoverability.
- Restart before/after `due_at` behavior.
- Atomic schedule claim and duplicate execute prevention.
- Stale `running` reconciliation with send-log evidence.
- Resume safety (purchase, return, already sent).
- WhatsApp DB idempotency before provider.
- Terminal state protection and execution boundary (`execute_recovery_schedule`).
- Dev/staging verify endpoint for persistence inspect/scan.

### Remaining gaps 🟡

- **Dual execution substrate:** in-process `asyncio.sleep` **and** durable row — worker migration must disable one path.
- **Pre-delay session dicts** (`_session_recovery_started`, etc.) not shared across processes.
- **Multi-Uvicorn workers** without dedicated scheduler: resume scan may run on every worker unless env/config split.
- **Dead schedule** full E2E requires manual restart test (automated covers row-level repair/scan).
- **`whatsapp_queue.py`** is a separate queue (non-recovery-delay); do not confuse with recovery schedule maturity.

### Dangerous gaps 🔴

- **Live asyncio task + resume scan** both active for same row if claim/finalize fails mid-flight → mitigated by claim + stale repair, but ops must monitor stuck `running`.
- **Horizontal scale without queue:** multiple API processes can duplicate **pre-delay** scheduling unless only one runs resume scan and abandon handling is idempotent at DB layer.

---

## Code map

| Concern | Module / entry |
|---------|----------------|
| Durable rows | `services/recovery_restart_survival.py` |
| Delay wait → execute | `services/recovery_delay_dispatcher.py` |
| Post-delay boundary | `services/recovery_execution_boundary.py` |
| Schedule claim | `claim_recovery_schedule_execution()` |
| WA idempotency | `services/recovery_whatsapp_idempotency.py` |
| Startup resume | `main` startup → `run_recovery_resume_scan_async` |
| Dev verify | `GET /dev/recovery-restart-survival-verify` |

---

## Recommendations (future — out of audit scope)

1. Dedicated scheduler service: enqueue by `due_at`, `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0` on API replicas.
2. Replace `asyncio.create_task` delay with worker poll + `execute_recovery_schedule` only.
3. Distributed lease TTL aligned with `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS`.
4. Runbook: grep `[RECOVERY RESUME SCAN]`, `[RECOVERY CLAIM SKIPPED]`, `[WA IDEMPOTENCY HIT]`, `[RECOVERY TERMINAL UPDATE]`.
