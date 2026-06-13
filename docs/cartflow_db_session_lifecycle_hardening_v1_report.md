# DB Session Lifecycle Hardening v1 — Report

**Date (UTC):** 2026-06-13  
**Verdict:** **PASS — implemented and tested locally**

---

## Goal

Ensure scheduler/resume background jobs always return SQLAlchemy connections to the pool.

---

## Changes

| File | Change |
|------|--------|
| `services/recovery_db_due_scanner.py` | `scoped_db_session_begin()` + `release_scoped_db_session()` in `finally`; re-fetch schedule row by id each loop iteration (safe after per-row execution boundary release) |
| `services/recovery_restart_survival.py` | `run_recovery_resume_scan_async()` — same begin/finally lifecycle |
| `services/recovery_db_due_scanner_loop.py` | Extra `release_scoped_db_session()` in tick `finally` (no hold across ticks; sleep remains before tick) |
| `tests/test_db_session_lifecycle_scheduler_v1.py` | **New** — release assertions + dispatch regression |
| `tests/test_recovery_db_due_scanner.py` | Use saved `sid` after scan (session no longer leaks row handle) |

---

## Behavior preserved

- No changes to recovery dispatch logic, WhatsApp, or dashboard paths
- Due scanner still finds/dispatches due rows (`test_scan_due_dispatches_once_then_idempotent` passes)
- Loop still sleeps **before** each tick — no connection held during sleep

---

## Tests

```bash
python -m pytest tests/test_db_session_lifecycle_scheduler_v1.py tests/test_recovery_db_due_scanner.py tests/test_recovery_db_due_scanner_loop.py -q
```

**15 passed**

---

## Not in scope (follow-up)

- Remove per-tick `db.create_all()` from scanner/resume (separate perf task)
- `repair_stale_running_recovery_schedules()` when called standalone outside wrapped callers
