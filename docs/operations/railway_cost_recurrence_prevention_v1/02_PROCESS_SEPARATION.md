# Process Separation

## Entry points

| Process | Module | Command | Starts web API | Starts Scheduler loops |
|---------|--------|---------|----------------|------------------------|
| API | `cartflow_api.py` | `python -m uvicorn cartflow_api:app --host 0.0.0.0 --port ${PORT:-8000}` | Yes (`main.app`) | No |
| Scheduler | `cartflow_scheduler.py` | `python -m cartflow_scheduler` | No | Only jobs explicitly enabled |

`CARTFLOW_PROCESS_ENTRY` is set only by these two modules (`services/process_entry_v1.py`).

## Fail-closed rules

- `configure_api_entry()` sets `CARTFLOW_PROCESS_ENTRY=api` and default `CARTFLOW_PROCESS_ROLE=api`.
- `configure_scheduler_entry()` sets both entry and role to `scheduler`.
- `assert_entry_matches_role()` raises `ProcessEntryError` on mismatch.
- `reject_scheduler_via_web_entry()` raises if:
  - entry is `scheduler` (uvicorn / `cartflow_api` / `main:app` must never host Scheduler), or
  - role is `scheduler` and entry is `api` or the runtime is production-like.

A wrong process role therefore fails before serving traffic or opening Scheduler loops.

## API must never start Scheduler loops

`main.py` `_startup_whatsapp_queue` now:

1. Rejects Scheduler-via-web.
2. Verifies runtime role.
3. Logs ownership / warms DB / starts the WhatsApp queue worker.

It does **not** call `run_scheduler_drivers_at_startup`, `start_db_due_recovery_scanner_loop`, `start_dashboard_snapshot_builder_loop`, or `start_dashboard_snapshot_archive_loop`.

Those drivers run only from `cartflow_scheduler.py`.

## Scheduler must never start the web API

`cartflow_scheduler.py`:

- Does not import `main.app`.
- Does not import FastAPI or uvicorn.
- Sleeps after starting enabled drivers; it is not an HTTP server.

Health for the Scheduler process is the in-process cache written by those drivers. Railway should not point the Scheduler service at `uvicorn`.

## Do not rely on env flags inside one uvicorn process

The previous design used `CARTFLOW_PROCESS_ROLE` inside `uvicorn main:app`. That is no longer sufficient. Distinct commands are required so a mis-set env cannot start both roles in one process.

Root `railway.toml`, `Dockerfile`, `Procfile`, and `start.py` now start `cartflow_api:app` (API-only). Scheduler must use `railway.scheduler.toml`.
