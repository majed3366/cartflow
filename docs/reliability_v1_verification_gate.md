# Reliability Program v1 — Verification Gate

**Date (UTC):** 2026-05-21  
**Scope:** Parts 1, 3, 4, 5, 6, 8 (restart survival, DB claim, WhatsApp idempotency, stale `running` repair, execution boundary, delay dispatcher).  
**Method:** Automated gate runner + existing pytest suite (no production code changes in this gate).  
**Runner:** `python scripts/reliability_v1_verification_gate.py`  
**Pytest (33 tests):** `tests/test_recovery_restart_survival.py`, `tests/test_recovery_execution_boundary.py`, `tests/test_recovery_schedule_claim.py`, `tests/test_recovery_whatsapp_idempotency.py`, `tests/test_recovery_delay_dispatcher.py`, `tests/test_cartflow_queue_readiness_verification.py`

---

## Executive summary

| Check | Result |
|-------|--------|
| Gate scenarios 1–7 (automated) | **7 / 7 PASS** |
| Reliability pytest suite | **33 / 33 PASS** |
| Live staging E2E (Twilio, real restart) | **Not run** — see risks |

---

## Pass/fail matrix

| Scenario | Expected logs | Expected DB transition | Actual result | PASS/FAIL | Notes |
|----------|---------------|------------------------|---------------|-----------|-------|
| **1. Restart during active delay** | `[RECOVERY RESUME SCAN]`, `[RECOVERY RESUME CANDIDATE]`, `[RECOVERY CLAIM ATTEMPT]`, `[RECOVERY CLAIMED]`, `[RECOVERY EXECUTION ENTRY]`, `[RECOVERY EXECUTION CLAIMED]`, `[RECOVERY EXECUTION FINISHED]`, `[RECOVERY TERMINAL UPDATE]` | `scheduled` → `running` → terminal (not stuck `running`) | DB before: `scheduled` id=1 `demo:gate-s1-restart-86a867`. After resume dispatch: `failed_resume` (mocked execution, no real WA log). Scan dry-run: `due_processed=1`. All listed logs **present** in captured stdout. | **PASS** | Simulates process restart (no in-process asyncio task): `due_at` backdated, `resume_one_schedule` + `execute_recovery_schedule`. `[RECOVERY DISPATCH *]` verified separately in `tests/test_recovery_delay_dispatcher.py` for live path. |
| **2. Duplicate dispatch prevention** | One `[RECOVERY CLAIMED]`; duplicate `[RECOVERY EXECUTION SKIPPED]` / claim skip | Single execution (`mock_run_count=1`); terminal not re-run | `mock_run_count=1`. Second `execute_recovery_schedule` → `[RECOVERY EXECUTION SKIPPED]` `already_terminal:failed_resume`. DB: `failed_resume`. | **PASS** | `tests/test_recovery_restart_survival.py::test_scenario_d_duplicate_resume_claim` — resume dispatch creates only one task. |
| **3. Resume after restart** | `[RECOVERY EXECUTION ENTRY]`, `[RECOVERY EXECUTION CLAIMED]`, `[RECOVERY EXECUTION FINISHED]`, `[RECOVERY TERMINAL UPDATE]` | `scheduled` → `running` → terminal | `execute_out.ok=true`. Logs: all four tags. DB: `scheduled` → `failed_resume` (mocked body). | **PASS** | `resume_scan` source on boundary; not left `running`. |
| **4. Stale running recovery** | `[RECOVERY STALE CHECK]`, `[RECOVERY STALE DETECTED]`, `[RECOVERY STALE FINALIZED]` | `running` (stale) → `completed` when `mock_sent` evidence | Before: `running`, `updated_at` ~900s old. After: `completed`. Repair: `finalized=1`. Logs: CHECK, DETECTED, FINALIZED. | **PASS** | `tests/test_recovery_restart_survival.py::test_stale_running_finalized_when_mock_sent_evidence`. |
| **5. WhatsApp duplicate prevention** | First `[WA IDEMPOTENCY MISS]`; second `[WA IDEMPOTENCY HIT]` | Duplicate identity blocked before provider | Miss then hit on same `recovery_key`/step; `existing_status=mock_sent`. Logs: CHECK, MISS, HIT. | **PASS** | Idempotency unit path. Full send-path `skipped_duplicate` on schedule: `tests/test_recovery_whatsapp_idempotency.py` + integration tests. |
| **6. Schedule lifecycle** | `[RECOVERY TERMINAL UPDATE]`; `[RECOVERY CLAIM SKIPPED]` on terminal reclaim | `scheduled`→`running`→`completed`; no downgrade | Claim → `completed`; overwrite `skipped_duplicate` **blocked**; reclaim `already_terminal:completed`. | **PASS** | `tests/test_recovery_schedule_claim.py::test_terminal_no_overwrite_completed`. |
| **7. Multi-trigger same session** | `[RECOVERY CLAIM ATTEMPT]` + `[RECOVERY CLAIM SKIPPED]` / duplicate schedule guard | One durable row; second claim `already_running` | `schedule_row_count=1` after double persist. Second claim `already_running`. | **PASS** | Upsert by `(recovery_key, step, slot)`. Cart-event duplicate scheduling: `tests/test_recovery_restart_survival.py` scenario D + in-memory session claim. |

---

## Scenario detail (steps, logs, DB)

### 1. Restart during active delay (simulated)

**Setup**
1. Clear `recovery_schedules` / `cart_recovery_log` in test DB.
2. `persist_recovery_schedule_durable` with `delay_seconds_scheduled=120`, `status=scheduled`.
3. Set `due_at` to 10 seconds in the past (in-process delay task gone).
4. `run_recovery_resume_scan_async(dry_run=True)` — expect due row visible.
5. `resume_one_schedule(row, dispatch=True)` → `execute_recovery_schedule(source=resume_scan)` with mocked `_run_recovery_sequence_after_cart_abandoned`.

**Expected logs (observed)**
```
[RECOVERY RESUME SCAN] pending_scheduled=1 due_now=1
[RECOVERY RESUME CANDIDATE] recovery_key=demo:gate-s1-restart-86a867 ...
[RECOVERY CLAIM ATTEMPT] path=resume_dispatch current_status=scheduled
[RECOVERY CLAIMED] path=resume_dispatch
[RECOVERY EXECUTION ENTRY] source=resume_scan
[RECOVERY CLAIM ATTEMPT] path=execution_boundary_resume_scan current_status=running
[RECOVERY CLAIMED] path=execution_boundary_resume_scan_reentry
[RECOVERY EXECUTION CLAIMED]
[RECOVERY EXECUTION FINISHED]
[RECOVERY TERMINAL UPDATE] from_status=running to_status=failed_resume
```

**DB snapshot**
| Phase | id | status | due_at |
|-------|-----|--------|--------|
| Before dispatch | 1 | `scheduled` | backdated (past) |
| After dispatch | 1 | `failed_resume` | past |

**Pass criteria:** Row survives “restart”; resume finds due row; exactly one claim chain; not stuck `running`. **Met.**

**Note:** `failed_resume` here is from mocked execution without a successful `CartRecoveryLog` send row — acceptable safe terminal for gate. Production path with real send finalizes to `completed` (see scenario 4 evidence path).

---

### 2. Duplicate dispatch prevention

**Setup**
1. One `scheduled` row.
2. Two sequential `execute_recovery_schedule` calls (same `schedule_id`).

**Observed**
- First: `[RECOVERY CLAIMED]` → `mock_run_count=1`.
- Second: `[RECOVERY EXECUTION SKIPPED]` `detail=already_terminal:failed_resume`.

**DB:** `failed_resume` — no second execution.

---

### 3. Resume after restart

**Setup:** `scheduled` row, `due_at` past → `execute_recovery_schedule(..., source=resume_scan)`.

**Observed:** `ok=true`; full execution log chain; terminal finalize.

---

### 4. Stale running recovery

**Setup:** `status=running`, `updated_at` 900s ago, `CartRecoveryLog` `mock_sent` step=1.

**Observed**
```
[RECOVERY STALE CHECK] running_rows=1
[RECOVERY STALE DETECTED] age_seconds=900.0
[RECOVERY STALE FINALIZED] terminal_status=completed detail=stale_send_evidence:mock_sent
[RECOVERY TERMINAL UPDATE] to_status=completed
```

**DB:** `running` → `completed`.

---

### 5. WhatsApp duplicate prevention

**Setup**
1. `check_whatsapp_recovery_send_idempotency` → MISS.
2. Insert `CartRecoveryLog` `mock_sent`.
3. Check again → HIT.

**Observed**
```
[WA IDEMPOTENCY MISS]
[WA IDEMPOTENCY HIT] existing_status=mock_sent
```

Provider `send_whatsapp` not invoked on HIT (verified in `tests/test_cartflow_queue_readiness_verification.py::test_idempotency_hit_does_not_invoke_provider`).

---

### 6. Schedule lifecycle

**Observed transitions**
- `claim` → `running`
- `finalize` → `completed`
- `finalize skipped_duplicate` on `completed` → **no overwrite**
- `claim` after complete → `already_terminal:completed`

---

### 7. Multi-trigger same session

**Setup:** Double `persist_recovery_schedule_durable` same `recovery_key`.

**DB query result:** `schedule_row_count=1`.

**Observed:** First claim OK; second `already_running`.

---

## Automated test evidence (pytest)

| Command | Result |
|---------|--------|
| `python -m pytest tests/test_recovery_restart_survival.py tests/test_recovery_execution_boundary.py tests/test_recovery_schedule_claim.py tests/test_recovery_whatsapp_idempotency.py tests/test_recovery_delay_dispatcher.py tests/test_cartflow_queue_readiness_verification.py -q` | **33 passed** (2026-05-21) |

---

## Blocked / not run in this gate

| Item | Status | Reason |
|------|--------|--------|
| Full live Twilio send on staging | **BLOCKED** | Gate uses mocks; avoids merchant/provider impact. |
| Real uvicorn kill mid-`asyncio.sleep` | **BLOCKED** | Simulated via due row + resume scan (equivalent durable behavior). |
| Multi-worker race across hosts | **BLOCKED** | Single-process SQLite/Postgres test DB; DB claim tests cover single DB. |

---

## Unresolved risks (before Queue/Worker expansion)

1. **`failed_resume` on mocked runs** — Terminal inference when execution exits without send log can label `failed_resume`; production with successful send should land on `completed` (stale repair + idempotency tests cover evidence).
2. **Stale terminal rows in dev DB** — Re-running abandon tests without clearing `recovery_schedules` can leave `failed_resume`/`completed` and block new dispatch (`already_terminal` skip). Ops: clear stale rows or use fresh session keys.
3. **Live `[RECOVERY DISPATCH *]`** — Verified in unit tests; staging smoke still recommended once before queue work.
4. **In-memory guards** — Pre-delay session dicts still exist; boundary/resume paths are DB-backed; queue worker must not rely on process memory.
5. **No horizontal worker yet** — Claim gate is DB-atomic in one database; multi-host needs lease/TTL ops (documented in queue readiness docs).

---

## Reliability Program v1 Verification Gate

**Status: PASS**

**Decision:** Safe to continue to the next Queue/Worker readiness step (enqueue replacement for `recovery_delay_dispatcher`, worker calling `execute_recovery_schedule` only). Do **not** skip staging smoke for first production deploy of reliability changes.

**Re-run gate:** `python scripts/reliability_v1_verification_gate.py` (exit code 0 = all scenarios pass).
