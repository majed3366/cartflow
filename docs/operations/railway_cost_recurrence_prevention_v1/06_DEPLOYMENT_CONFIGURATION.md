# Deployment Configuration

**This task does not assign files in Railway and does not enable autodeploy.**

## Repository files

| File | Assign later to | Start command | Role |
|------|-----------------|---------------|------|
| `railway.api.toml` | `smart-reply-ai` (API) | `python -m uvicorn cartflow_api:app --host 0.0.0.0 --port ${PORT:-8000}` | `api` |
| `railway.scheduler.toml` | `cartflow` (Scheduler) | `python -m cartflow_scheduler` | `scheduler` |
| `railway.toml` | Fallback / local API default | same as API | `api` |

Scheduler must **not** inherit the API command.

## How to assign later (operator, not this task)

Railway → service → Settings → Config-as-code (or equivalent) → set the config file path:

1. `smart-reply-ai` → `railway.api.toml`
2. `cartflow` → `railway.scheduler.toml`

Do not apply that in this task.

## Pinned env in those files (jobs OFF)

Both files set:

- `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0`
- `CARTFLOW_DB_DUE_SCANNER_ENABLED=false`
- `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=0`
- `CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED=false`
- `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED=false`
- `CARTFLOW_ALLOW_PUBLIC_DATABASE=0`

API also sets `CARTFLOW_ENFORCE_API_ONLY=1`.

Image entrypoints (`Dockerfile` CMD, `Procfile`, `start.py`) start **API only**.

## Autodeploy

Must remain **disabled** on both services until a dedicated production-validation task completes. This implementation does not change Railway.

## Database URL on restore (later)

Production `DATABASE_URL` must be the **private** hostname (`*.railway.internal`). The public proxy host will fail closed unless `CARTFLOW_ALLOW_PUBLIC_DATABASE` is explicitly enabled.
