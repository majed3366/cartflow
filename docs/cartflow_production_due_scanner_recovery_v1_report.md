# Production Due Scanner Recovery v1 — Report

**Date:** 2026-06-13 (UTC)  
**Production:** `https://smartreplyai.net`  
**Status:** Fix committed in `railway.toml` — **awaiting deploy** for production verification PASS

---

## 1. Exact root cause

Production runs a **production-like runtime** (`ENV` unset or not `development` → `is_production_like_runtime() == true`) **without** `CARTFLOW_PROCESS_ROLE`.

Phase 1 scheduler ownership enforcement (`evaluate_scheduler_ownership_policy()` in `services/recovery_process_role_v1.py`) **fail-closes** all recovery drivers when role is unset:

| Driver | Blocked | Mechanism |
|--------|---------|-----------|
| Startup resume scan | Yes | `may_resume: false`, `block_reason: role_unset_production` |
| DB due scanner loop | Yes | `start_db_due_recovery_scanner_loop()` returns immediately — logs `[DB DUE SCANNER LOOP SKIPPED] reason=role_unset_production` |
| In-process delay dispatch | Yes | `may_delay_dispatch: false` |

Additionally, **`CARTFLOW_DB_DUE_SCANNER_ENABLED` defaults to false** even when role would allow scanning — production never set it to `true`.

**Live evidence (pre-fix, 2026-06-13):**

```json
GET /health/scheduler
{
  "ok": false,
  "role": "unset",
  "due_scanner_enabled": false,
  "overdue_scheduled_count": 5,
  "scheduler_ownership": {
    "compliance": "misconfigured",
    "block_reason": "role_unset_production",
    "may_due_scan": false
  }
}
```

`GET /dev/recovery-health`: `pending_due: 5`, `last_claim: null`, `last_execution: null`, `protections.db_due_scanner_loop.status: disabled`.

**Why overdue schedules accumulate while scanner stays inactive:** Schedules are **written durably** when merchants capture hesitation / abandon flows (`RecoverySchedule` rows with `status=scheduled`, `due_at` in the past). The due scanner is a **separate poll loop** that only runs when ownership policy + env allow it. With drivers blocked, rows age past `due_at` but nothing claims them — backlog grows (`overdue_scheduled_count` / `pending_due`).

This is **not** a per-cart guardrail bug; it is **platform-wide scheduler misconfiguration** after Phase 1 fail-closed deploy without matching Railway env.

---

## 2. Exact fix

Restore the **production execution path** via Railway config-as-code (no manual schedule processing, no one-off scripts):

**`railway.toml` `[env]`** (single-service deploy — one scheduler owner):

```toml
CARTFLOW_PROCESS_ROLE = "scheduler"
CARTFLOW_RECOVERY_RESUME_ON_STARTUP = "1"
CARTFLOW_DB_DUE_SCANNER_ENABLED = "true"
```

**Deploy** the commit containing this change so Railway applies variables on the next build.

**If scaling to multiple replicas later:** one dedicated scheduler service with the above env; all HTTP replicas:

```env
CARTFLOW_PROCESS_ROLE=api
CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0
```

No code workaround — env matches the architecture Phase 1 designed for.

---

## 3. Architectural explanation

### Startup path (single process)

`main.py` FastAPI `startup`:

1. `log_scheduler_owner_at_startup()` — logs `[SCHEDULER OWNER]` role / compliance
2. `run_recovery_resume_scan_async(max_dispatch=25)` — startup resume + stale `running` repair (blocked when misconfigured)
3. `start_db_due_recovery_scanner_loop()` — spawns asyncio loop if `may_due_scan` (blocked when misconfigured)

### Due scanner loop

`services/recovery_db_due_scanner_loop.py`:

- Poll interval: `CARTFLOW_DB_DUE_SCANNER_INTERVAL_SECONDS` (default 30s)
- Each tick: `scan_due_recovery_schedules()` → `execute_recovery_schedule()` per due row
- Tick lock prevents overlapping passes (no duplicate tick concurrency)

### Required runtime role/config (production)

| Variable | Scheduler owner value |
|----------|----------------------|
| `CARTFLOW_PROCESS_ROLE` | `scheduler` |
| `CARTFLOW_DB_DUE_SCANNER_ENABLED` | `true` |
| `CARTFLOW_RECOVERY_RESUME_ON_STARTUP` | `1` (explicit; default when unset is also enabled) |

### Duplicate execution risk

Unchanged by this fix — existing guards remain:

- `claim_recovery_schedule_execution()` — atomic claim to `running` before send
- `execute_recovery_schedule()` — second call → `claim_race_lost` / terminal skip
- `evaluate_resume_safety()` — skips unsafe resume candidates
- Scanner tick lock — one pass at a time per process

### Restart survival

`repair_stale_running_recovery_schedules()` runs inside resume scan and due scanner passes; startup resume re-arms future work when `may_resume` is true. Misconfiguration blocked **both** resume and scanner — fixing env restores the full restart-survival path without changing survival logic.

---

## 4. Production verification

### Pre-deploy (current)

```bash
python scripts/due_scanner_recovery_verify_v1.py --base https://smartreplyai.net --json
# Expected: FAIL on scheduler_role_and_compliance, db_due_scanner_loop_enabled
```

Or:

```bash
python scripts/scheduler_ownership_verify.py --scheduler https://smartreplyai.net --json
```

### Post-deploy (expected PASS)

1. **Scanner starts** — Railway logs after deploy:
   ```text
   [SCHEDULER OWNER] role=scheduler resume_enabled=true due_scanner=true compliance=ok
   [DB DUE SCANNER LOOP STARTED] interval_seconds=30 limit=25
   ```

2. **Scanner polls** — logs every ~30s:
   ```text
   [DB DUE SCANNER LOOP TICK] ...
   [DB DUE SCANNER LOOP TICK] phase=done found=... dispatched=...
   ```

3. **Scanner claims / executes** — `GET /dev/recovery-health`:
   - `last_claim` and `last_execution` populated after first due row processed
   - `protections.db_due_scanner_loop.status: enabled`

4. **Overdue schedules progress** — `GET /health/scheduler`:
   - `ok: true`, `role: scheduler`, `due_scanner_enabled: true`
   - `overdue_scheduled_count` decreases toward 0 (batch limit 25 per tick)

5. **Automated gate** (wait one scanner interval + margin):

   ```bash
   python scripts/due_scanner_recovery_verify_v1.py --base https://smartreplyai.net --wait 90 --json
   ```

6. **Duplicate / restart** — no change to claim layer; confirm no duplicate sends via existing `CartRecoveryLog` / schedule terminal statuses for processed `recovery_key`s.

---

## 5. Files changed

| File | Change |
|------|--------|
| `railway.toml` | `[env]` scheduler ownership variables |
| `.env.example` | Document scheduler env block |
| `docs/cartflow_production_readiness.md` | Required scheduler vars + Railway note |
| `scripts/due_scanner_recovery_verify_v1.py` | Post-deploy verification script |
| `docs/cartflow_production_due_scanner_recovery_v1_report.md` | This report |

---

## 6. Verdict

| Item | Result |
|------|--------|
| Root cause | `role_unset_production` + `CARTFLOW_DB_DUE_SCANNER_ENABLED` unset (false) on production-like runtime |
| Fix | `railway.toml` env: `scheduler` + due scanner enabled + resume on startup |
| Architecture | Startup → resume scan + due scanner loop gated by `evaluate_scheduler_ownership_policy()` |
| Production verification | **Pending deploy** — pre-fix probes confirm failure mode; post-fix run `due_scanner_recovery_verify_v1.py` |
