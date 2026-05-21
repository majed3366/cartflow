# DB due scanner — manual verification report

**Date (UTC):** 2026-05-19  
**Scope:** Visibility only — `scripts/db_due_scanner_verify.py` and this document.  
**Does not change:** production runtime, `scan_due_recovery_schedules`, `execute_recovery_schedule`, claim gate, WhatsApp idempotency, stale `running` repair, RecoverySchedule lifecycle, widget, dashboard, provider, schema, asyncio delay, startup resume, or automatic scanning.

---

## What this verification proves

| Check | Meaning |
|--------|---------|
| **Before scan** | A `recovery_schedules` row exists with `status=scheduled` and `due_at` in the past (`is_due=true`). |
| **Run 1** | Manual `scan_due_recovery_schedules` finds the row, dispatches through `execute_recovery_schedule` (`source=db_due_scanner`), and expected log tags appear. |
| **After run 1** | The same row reaches a **terminal** status (`completed`, `failed_resume`, `skipped_duplicate`, etc.). |
| **Run 2** | Second scan is **idempotent**: `found=0` or no re-dispatch; status unchanged; no new successful WhatsApp log for that step. |
| **Verdict** | `PASS` only when run 1 and run 2 criteria are met. |

Recovery **send** is mocked in the script (`main._run_recovery_sequence_after_cart_abandoned` patched) so you can run verification without sending real WhatsApp. Production paths are unchanged.

---

## What this does NOT change

- No new HTTP endpoints.
- No Redis / Celery / RQ / worker processes.
- No cron or startup hook for the scanner.
- No edits to `services/recovery_db_due_scanner.py` scan/dispatch logic (script-only reporting).
- No widget, dashboard, or provider changes.

---

## Commands

From the repository root:

```bash
python scripts/db_due_scanner_verify.py
```

Human-readable sections: BEFORE → RUN 1 summary → AFTER → RUN 2 idempotency → FINAL VERDICT.

```bash
python scripts/db_due_scanner_verify.py --json
```

Single JSON object with keys: `before`, `run1`, `after`, `run2`, `verdict` (plus `meta`, `pass`).

---

## Sample readable output (abbreviated)

```
========================================================================
DB DUE SCANNER — MANUAL VERIFICATION REPORT
========================================================================
Setup: created_test_due_row
Schedule id: 3
Recovery send: MOCKED (no real WhatsApp)

========================================================================
1. BEFORE SCAN (run 1)
========================================================================
  schedule_id: 3
  recovery_key: demo:db-scanner-abc12345
  step: 1
  status: scheduled
  due_at: 2026-05-21T18:30:00.000000
  updated_at: 2026-05-21T18:30:05.000000
  is_due: True
  WhatsApp send logs (step): {'send_log_count': 0, 'successful_send_count': 0, ...}

========================================================================
2. RUN 1 — SCANNER SUMMARY
========================================================================
  found: 1
  dispatched: 1
  skipped: 0
  stale_running_finalized: 0
  terminal_or_dispatched_count: 1
  required logs present: True
    DB DUE SCANNER START: yes
    ...
  RUN 1 PASS: yes

========================================================================
3. AFTER SCAN (run 1)
========================================================================
  status: failed_resume
  is_terminal: True
  terminal_evidence: {'status_in_terminal_set': True, 'last_error': ...}

========================================================================
4. RUN 2 — IDEMPOTENCY CHECK
========================================================================
  found: 0
  dispatched: 0
  idempotent_safe (found=0 or no re-dispatch): True
  no duplicate WhatsApp log: True
  RUN 2 PASS: yes

========================================================================
5. FINAL VERDICT
========================================================================
  PASS
```

Terminal status may be `completed` or another safe terminal (e.g. `failed_resume` under mock) — both satisfy pass criteria.

---

## Sample JSON structure

```json
{
  "meta": {
    "script": "db_due_scanner_verify",
    "setup_action": "created_test_due_row",
    "schedule_id": 3,
    "mocked_recovery_send": true,
    "scanner_source": "db_due_scanner"
  },
  "before": {
    "schedule_id": 3,
    "recovery_key": "demo:db-scanner-...",
    "step": 1,
    "status": "scheduled",
    "due_at": "...",
    "updated_at": "...",
    "is_due": true,
    "is_terminal": false,
    "terminal_evidence": { "status_in_terminal_set": false, "last_error": null },
    "whatsapp_logs": { "send_log_count": 0, "successful_send_count": 0, "statuses": [] }
  },
  "run1": {
    "scanner_out": { "found": 1, "dispatched": 1, "skipped": 0, "outcomes": [...] },
    "summary": { "found": 1, "dispatched": 1, "pass": true, "logs_all_present": true },
    "logs_found": { "DB DUE SCANNER START": true, ... },
    "errors": []
  },
  "after": {
    "run1": { "schedule_id": 3, "status": "failed_resume", "is_terminal": true, ... }
  },
  "run2": {
    "scanner_out": { "found": 0, "dispatched": 0, ... },
    "summary": { "idempotent_safe": true, "no_duplicate_whatsapp": true, "pass": true },
    "row": { ... },
    "logs_excerpt_lines": [ ... ]
  },
  "verdict": "PASS",
  "pass": true
}
```

---

## Pass / fail criteria

| Phase | PASS when |
|--------|-----------|
| Before | `status == scheduled` and `is_due == true` |
| Run 1 | `found >= 1`, `dispatched >= 1`, row terminal after scan, all required log tags present |
| After | `is_terminal == true` |
| Run 2 | `dispatched == 0` and (`found == 0` or status unchanged); no increase in successful WA logs |
| Final | `verdict == PASS` (exit code 0) |

**FAIL** prints error codes in `run1.errors` / `run2.summary.errors` (JSON) or `errors:` lines (human). Exit code `1`.

---

## What to screenshot or copy for verification notes

1. **Section 1 (BEFORE)** — `status: scheduled`, `is_due: True`, `step`, `due_at`.
2. **Section 2 (RUN 1)** — `found`, `dispatched`, `required logs present: True`.
3. **Section 3 (AFTER)** — final `status` and `is_terminal: True`.
4. **Section 4 (RUN 2)** — `found: 0`, `dispatched: 0`, `idempotent_safe: True`.
5. **Section 5** — `PASS`.
6. Optional: full JSON from `--json` for CI/archival.

Also run before tagging queue work:

```bash
python -m pytest tests/test_recovery_db_due_scanner.py tests/test_recovery_restart_survival.py tests/test_recovery_execution_boundary.py tests/test_recovery_schedule_claim.py tests/test_recovery_whatsapp_idempotency.py tests/test_recovery_delay_dispatcher.py tests/test_cartflow_queue_readiness_verification.py -q
```

---

## Related files

| File | Role |
|------|------|
| `services/recovery_db_due_scanner.py` | Manual scanner (unchanged by this doc/script reporting work) |
| `scripts/db_due_scanner_verify.py` | This verification report |
| `docs/cartflow_queue_worker_readiness.md` | Queue readiness program context |
