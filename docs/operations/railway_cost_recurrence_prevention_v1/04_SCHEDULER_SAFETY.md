# Scheduler Safety

## Expensive jobs default OFF

| Job | Enablement (all required) | Default |
|-----|---------------------------|---------|
| Due scanner | `CARTFLOW_DB_DUE_SCANNER_ENABLED=true` **and** role `scheduler` | OFF |
| Resume processing | `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1` **and** role `scheduler` | OFF |
| Snapshot builder | `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1` **and** `CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED=1` | OFF |
| Snapshot archive | `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED=1` | OFF |

Scheduler role alone does **not** start any expensive loop. `verify_runtime_role_at_startup()` no longer requires scanner/resume ON for the Scheduler role.

`railway.scheduler.toml` pins all four flags to off. Enablement is a later, explicit dashboard/env change.

## Loop bounds (`services/scheduler_cycle_guard_v1.py`)

- Minimum sleep: **5 seconds**. `next_sleep_seconds(0)` and negative values clamp to 5.
- Exponential backoff after consecutive failures, cap **300 seconds**.
- No zero-sleep retry path.
- Scanner and snapshot loops use an `asyncio.Lock`; a second tick returns `skipped=tick_in_progress`.
- Postgres single-instance: `pg_try_advisory_lock(814229017)`. Failure raises `SchedulerInstanceLockError` (fail closed). SQLite / missing engine is local-only (tests).
- Scanner per-cycle row limit: `CARTFLOW_DUE_SCANNER_LIMIT` / `CARTFLOW_DB_DUE_SCANNER_LIMIT` (default 25).
- Snapshot store limit remains in the builder; cycle byte budget is additional.

## Metrics (no customer payloads)

In-process cache (`scheduler_runtime_state_v1`) records:

- last successful cycle
- last failure kind
- next scheduled cycle
- enabled job names
- ready / live

Snapshot ticks also emit `cycle_bytes`, `cycle_records`, `cycle_byte_budget`, `cycle_aborted`. Logs do not print snapshot JSON or secrets.

## `create_all()` removed from recurring loops

`scan_due_recovery_schedules` no longer calls `db.create_all()`. Schema creation stays on the explicit startup/migration warm path (`_ensure_cartflow_api_db_warmed` / controlled init), not every 30 seconds.

## Snapshot / archive controls

- Builder requires **both** snapshot mode and `CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED`.
- Hard per-record JSON cap remains (65k / 512k / 256k family).
- Cycle budget default **1.5 MB** (`CARTFLOW_DASHBOARD_SNAPSHOT_CYCLE_BYTE_BUDGET`, clamp 50 KB–8 MB).
- `upsert_dashboard_snapshot` charges `len(payload_json)` into the active `SnapshotCycleBudget`.
- Exceeding the budget raises `SnapshotCycleBudgetExceeded`; the tick aborts safely and records metrics.
- Empty database: interval remains ≥ 15 s (snapshot) / ≥ 5 s (scanner). No busy loop.

## Tests

- Interval / backoff / never-zero: `SchedulerIntervalTests`
- Overlap: `tests/test_recovery_db_due_scanner_loop.py::test_no_overlapping_ticks`
- Single-instance lock: `SingleInstanceAndOverlapTests`
- Empty DB not busy: `SnapshotBudgetTests.test_empty_cycle_not_busy`
- Large payload bounded: `LargePayloadBudgetTests`
- Builder default OFF: `SnapshotBuilderDefaultOffTests`
- `create_all` absent from scanner source: `test_scanner_source_has_no_create_all`
