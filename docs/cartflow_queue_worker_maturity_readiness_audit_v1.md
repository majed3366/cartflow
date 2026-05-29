# Queue / Worker Maturity Readiness Audit

**Date (UTC):** 2026-05-29  
**Type:** Read-only audit — **no implementation**, no Redis/Celery, no scheduling behavior changes.  
**Commit:** `docs: audit queue worker maturity readiness`  
**Related code:** `services/recovery_restart_survival.py`, `services/recovery_execution_boundary.py`, `services/recovery_delay_dispatcher.py`, `services/recovery_db_due_scanner.py`, `services/recovery_whatsapp_idempotency.py`  
**Automated proofs:** `pytest tests/test_queue_worker_maturity_audit_v1.py -q`

---

## Executive summary

CartFlow’s recovery execution is **durable and restart-safe for a single scheduler process**, but **not yet a horizontally scaled worker queue**. The design center is correct: `RecoverySchedule` rows survive restart, atomic `scheduled → running` claims prevent double execution at the DB layer, stale `running` rows are repaired from log evidence, and WhatsApp sends are idempotent via `CartRecoveryLog` before the provider is called.

**Readiness for real merchants (single production API + one scheduler role):** **PARTIAL — acceptable with ops discipline.**  
**Readiness for multi-worker API replicas without a dedicated scheduler:** **NOT READY.**  
**Readiness for 1000 schedules due in the same minute:** **PARTIAL — safe but slow; backlog drains at ~25 rows per scan tick.**

---

## 1. Current execution model

There is **no external job queue** (no Redis, Celery, SQS). Recovery work runs inside the **FastAPI/Uvicorn process event loop**, backed by **`recovery_schedules`** in the app database.

### Three complementary drivers (same table, different triggers)

| Driver | Module | When it runs | What it does |
|--------|--------|--------------|--------------|
| **A. In-process delay** | `recovery_delay_dispatcher.dispatch_recovery_schedule` | After `cart_abandoned` persists a row; after startup **future rearm** | `asyncio.sleep` until `due_at`, then `execute_recovery_schedule` |
| **B. Startup resume scan** | `recovery_restart_survival.run_recovery_resume_scan_async` | **Every startup by default** (`CARTFLOW_RECOVERY_RESUME_ON_STARTUP` unset → enabled) | Stale repair → dispatch up to **25** past-due `scheduled` rows → rearm up to **25** future rows |
| **C. Optional DB due scanner** | `recovery_db_due_scanner` + `recovery_db_due_scanner_loop` | Only if `CARTFLOW_DB_DUE_SCANNER_ENABLED=true` (default **off**) | Poll every 30s (configurable), limit **25**, **sequentially** `await execute_recovery_schedule` per row |

### Canonical execution entry (queue-ready boundary)

All post-delay paths converge on:

```
execute_recovery_schedule(schedule_id=…, source=…)
  → resolve row
  → stale-running repair at entry (if needed)
  → claim_recovery_schedule_execution (scheduled → running)
  → _run_recovery_sequence_after_cart_abandoned (unchanged recovery/send logic)
  → finalize row to terminal status from CartRecoveryLog outcome
```

This boundary is explicitly documented as the future worker hook — Redis/Celery would enqueue **here**, not replace abandon or delay persistence.

### Persistence before wait

`persist_recovery_schedule_durable` upserts a row **before** `asyncio.create_task(dispatch_recovery_schedule(…))`, so delay state survives process kill. `due_at`, `context_json`, step/slot keys, and merchant identity are stored on the row.

### WhatsApp path (separate in-process queue)

`services/whatsapp_queue.start_whatsapp_queue_worker` runs at startup and serializes provider sends **within one process**. It is **not** the recovery schedule queue; recovery still owns when to attempt send via the execution boundary.

---

## 2. How due rows are claimed

**Mechanism:** `claim_recovery_schedule_execution` in `recovery_restart_survival.py`.

1. Load row by `row_id` / `(recovery_key, step, slot)`.
2. Reject if status ∈ `_TERMINAL` → `already_terminal:*`.
3. Reject if status == `running` → `already_running` (except `accept_already_running=True` for resume re-entry edge).
4. Reject if status != `scheduled` → `not_claimable:*`.
5. **Atomic UPDATE:** `WHERE id = ? AND status = 'scheduled'` SET `status = 'running'`.
6. If `updated != 1` → `claim_race_lost` (another worker/path won).

**Resume path nuance:** `resume_one_schedule` claims **before** `asyncio.create_task(execute_recovery_schedule)`, so a second resume attempt hits `already_running` instead of spawning a duplicate task.

**Delay path nuance:** `dispatch_recovery_schedule` sleeps first while row stays `scheduled`; claim happens inside `execute_recovery_schedule` after wake.

**Evidence logs:** `[RECOVERY CLAIM ATTEMPT]`, `[RECOVERY CLAIMED]`, `[RECOVERY CLAIM SKIPPED] reason=claim_race_lost`.

---

## 3. Current safeguards

| Safeguard | Status | Detail |
|-----------|--------|--------|
| **Durable schedule rows** | ✅ Strong | Survive restart; future rearm re-spawns delay tasks |
| **Atomic DB claim** | ✅ Strong | Single winner per `scheduled` row; tested in `test_audit_07_db_claim_atomic_second_fails` |
| **Terminal state protection** | ✅ Strong | `_TERMINAL` frozenset; `completed` not downgraded without override |
| **Stale `running` repair** | ✅ Strong | Default 600s (`CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS`); log evidence → `completed` / `skipped_duplicate`; else `failed_resume_stale` |
| **Resume safety gates** | ✅ Strong | `evaluate_resume_safety` blocks purchase, return, already-sent, store mismatch |
| **WhatsApp send idempotency** | ✅ Strong | `check_whatsapp_recovery_send_idempotency` blocks on `sent_real` / `mock_sent` / `queued` per step |
| **Purchase stop** | ✅ Strong | `cancel_durable_schedules_for_purchase` + resume safety |
| **DB session lifecycle** | ✅ Strong | Session released before `asyncio.sleep` in delay dispatcher |
| **Scheduler ownership env** | ✅ Present | `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0` on non-scheduler replicas |
| **Demo filter on prod startup** | ✅ Present | Sandbox schedules skipped/terminal on production boot |
| **Pre-delay memory guards** | ⚠️ Process-local | `_session_recovery_*` dicts in `main.py` — not shared across workers |
| **Distributed lease / queue ack** | ❌ Missing | No Redis/Celery; no cross-process leader election |
| **Storm throttle / global rate limit** | ❌ Missing | Beyond Twilio account limits and WA in-process queue |
| **Throughput cap** | ⚠️ By design | `max_dispatch=25` resume scan; DB scanner limit 25 |

---

## 4. Checklist deep-dive

### Duplicate prevention

| Layer | Mechanism | Cross-worker? |
|-------|-----------|---------------|
| HTTP abandon | `_try_claim_recovery_session` + `_session_recovery_started` | **No** — memory only |
| Schedule row | Upsert one row per `(recovery_key, step, slot)` | **Yes** — DB |
| Post-delay execute | `claim_recovery_schedule_execution` | **Yes** — DB |
| Resume dispatch | Claim before `create_task` | **Yes** — DB |
| WhatsApp send | `CartRecoveryLog` idempotency before provider | **Yes** — DB |
| Same-process burst | `cartflow_duplicate_guard` inflight TTL (~6s) | **No** |

**Verdict:** Double **send** for the same step is **unlikely** once a blocking log row exists. Double **dispatch attempts** (extra asyncio tasks, wasted CPU) remain possible across workers **before** claim.

### Stuck `running` rows

- Detected when `updated_at` older than threshold (default **600s**).
- `repair_stale_running_recovery_schedules` runs at startup resume and DB due scan **before** dispatch.
- If matching `CartRecoveryLog` shows send → finalize to `completed` or `skipped_duplicate`.
- Otherwise → `failed_resume_stale` (does **not** auto-reschedule immediate retry).

**Ops:** Monitor `[RECOVERY STALE DETECTED]` and count of `status=running` older than threshold.

### Restart resume behavior

| Timing | Behavior |
|--------|----------|
| **Before `due_at`** | Row stays `scheduled`; `rearm_one_future_scheduled_recovery` spawns new delay task; no early send |
| **After `due_at`** | Resume scan picks row; safety gates; claim; `execute_recovery_schedule` |
| **Process mid-execute** | In-flight asyncio task lost; row may stay `running` until stale repair or successful finalize |

Startup hook (`main` startup): `run_recovery_resume_scan_async(max_dispatch=25)` unless disabled.

Dev inspect: `GET /dev/recovery-restart-survival-verify?action=inspect|simulate_restart_scan`.

### Multi-worker safety

| Concern | Single worker | N Uvicorn workers (default config) |
|---------|---------------|--------------------------------------|
| DB claim at execute | ✅ Safe | ✅ Safe |
| WA idempotency | ✅ Safe | ✅ Safe |
| Startup resume on all replicas | ✅ OK | ⚠️ **N × scan** — load amplification, not usually double send |
| Pre-delay `create_task` per worker | ✅ One process | 🔴 **Two workers can each spawn delay task** until first claim |
| Memory session guards | ✅ OK | 🔴 Not shared |

**Minimum ops pattern today:** One “scheduler” process with resume enabled; API replicas set `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0`. Documented in `services/recovery_scheduler_guardrails.py` and `docs/cartflow_queue_worker_runtime_rules.md`.

### Idempotency around WhatsApp sends

Flow in recovery sequence:

1. Build idempotency key `(recovery_key, step, session, cart, phone digits)`.
2. Query `CartRecoveryLog` for blocking statuses.
3. On hit → `[WA IDEMPOTENCY HIT]` — **no provider call**.
4. On miss → insert log row (often `queued`) then call provider.

Failed sends (`whatsapp_failed`) are **not** blocking — retries by design.

### 1000 schedules due near the same time

**Scenario:** Outage recovery, shared template delay, or campaign causes ~1000 rows with `status=scheduled` and `due_at <= now`.

| Phase | Behavior |
|-------|----------|
| **Startup resume** | Processes **25** due rows per scan invocation; creates up to 25 concurrent `execute_recovery_schedule` tasks |
| **DB due scanner** (if enabled) | **25 rows/tick**, **sequential** `await` per row — ~40 ticks to touch 1000 rows at 30s interval ≈ **20+ minutes** best case |
| **Live delay tasks** | Up to 1000 concurrent `asyncio.sleep` timers in one process — event-loop pressure |
| **Claim races** | Losers get `claim_race_lost` / `already_running` — safe, not silent duplicates |
| **WhatsApp** | In-process queue serializes provider calls — **send backlog**, not thread explosion |
| **DB pool** | Risk under concurrent execute + dashboard load — connection pool timeouts possible |

**Expected outcome:** Work **drains slowly**; merchants may see delayed first messages after a storm. **Not** expected: mass duplicate `sent_real` for same step if idempotency path runs.

**Estimate (single scheduler, scanner off, post-outage restart):**

- First 25 execute immediately on startup.
- Remaining 975 stay `scheduled` until next manual scan, restart, or enabling DB scanner.
- **Without scanner:** backlog requires repeated resume scans or restarts — **operational gap**.

---

## 5. Remaining risks

### High 🔴

1. **Multi-worker API without scheduler split** — duplicate delay tasks and N-fold startup scans.
2. **No dedicated recovery worker** — HTTP latency and recovery compete on same process.
3. **Post-outage backlog** — `max_dispatch=25` with optional scanner **off by default** leaves most due rows waiting.

### Medium 🟡

4. **Triple driver** (sleep + resume + scanner) — confusing ops; races until claim (safe but noisy).
5. **Pre-delay memory claims** — cross-worker duplicate scheduling attempts.
6. **1000+ concurrent asyncio delay tasks** — timer fairness and memory in one process.
7. **Platform gateway idempotency** — in-memory only (`_seen_external_events`), not restart-durable.

### Low 🟢

8. Stuck `running` without stale repair if threshold misconfigured.
9. `whatsapp_failed` allows retry — intentional; monitor for retry storms.

---

## 6. Minimum required changes before real merchants

**No Redis/Celery required for initial merchant launch** if the deployment matches a **single scheduler** pattern:

| # | Requirement | Rationale |
|---|-------------|-----------|
| 1 | **One scheduler role** per database | Enable resume + delay on one process; `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0` on other replicas |
| 2 | **Enable DB due scanner on scheduler** | `CARTFLOW_DB_DUE_SCANNER_ENABLED=true`, tune `CARTFLOW_DB_DUE_SCANNER_LIMIT` (e.g. 50–100) and interval |
| 3 | **Ops runbook + alerts** | Grep/monitor: `[RECOVERY STALE DETECTED]`, `[RECOVERY CLAIM SKIPPED]`, stuck `running`, `failed_resume_stale` count |
| 4 | **Stale threshold tuned** | Confirm `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS` ≥ p99 execute time |
| 5 | **Staging restart drill** | Manual A–F from `docs/audit_queue_worker_maturity_v1.md` before go-live |
| 6 | **Connection pool headroom** | Pool sized for dashboard + concurrent recovery executes |

**Not required for v1 launch (but blocks scale):** Redis, Celery, separate worker fleet.

---

## 7. Recommended next P0 task

**P0: Dedicated scheduler deployment contract + backlog drain**

Implement **operational** (not necessarily new infrastructure) clarity:

1. **Document and enforce** single scheduler process per DB (env + health check: `[RECOVERY SCHEDULER OWNER]`).
2. **Turn on** `CARTFLOW_DB_DUE_SCANNER_ENABLED=true` **only on scheduler**, with higher limit (50–100) so post-outage due backlogs drain without restart loops.
3. **Add metric/export** (read-only): count of `scheduled` rows with `due_at < now()` and oldest overdue age — surfaces storm before merchants notice delays.

**Why this is P0:** Code-level claim/idempotency already prevents most double sends; the **production failure mode** for real merchants is **delayed recovery after restarts or storms**, not silent duplicate WhatsApp. The 25-row resume cap + scanner-off default is the gap between “safe” and “ready.”

**P0 (engineering, next sprint after ops):** Insert/`scheduled` row **before** any `create_task` on abandon and reject duplicate session dispatch at DB layer — closes cross-worker pre-delay race without Redis.

---

## 8. Readiness matrix

| Load / deployment | Ready? | Notes |
|-------------------|--------|-------|
| 1 merchant, 1 process, restarts rare | **Yes** | Current design target |
| 10–50 merchants, 1 scheduler + API | **Partial** | Enable scanner; monitor backlog |
| 100 merchants, 1 scheduler | **Partial** | Dashboard hot-path + recovery share DB; storm drain slow |
| N API workers, all resume-on-startup | **No** | Ops misconfiguration risk |
| 1000 due same minute, scanner off | **No** (latency) | Safe idempotency; **unacceptable delay** |
| Horizontal recovery workers | **No** | Needs external queue + lease (future) |

---

## 9. Verification commands

```bash
# 10-scenario audit matrix
python -m pytest tests/test_queue_worker_maturity_audit_v1.py -q

# Extended reliability suite
python -m pytest tests/test_recovery_restart_survival.py tests/test_recovery_execution_boundary.py tests/test_recovery_schedule_claim.py tests/test_recovery_whatsapp_idempotency.py tests/test_recovery_db_due_scanner.py -q
```

**Production log signatures:**

```text
[RECOVERY RESUME SCAN]
[RECOVERY CLAIMED]
[RECOVERY CLAIM SKIPPED]
[RECOVERY STALE DETECTED]
[WA IDEMPOTENCY HIT]
[RECOVERY EXECUTION FINISHED]
[DB DUE SCANNER LOOP TICK]
```

---

## Document control

| Item | Value |
|------|--------|
| Runtime / scheduling changes | **None** |
| Redis / Celery | **Not proposed** |
| Authoritative worker entry (future) | `execute_recovery_schedule(schedule_id=…, source=…)` |
| Supersedes | Nothing — complements `docs/cartflow_queue_worker_maturity_audit_v1.md`, `docs/audit_queue_worker_maturity_v1.md` |
