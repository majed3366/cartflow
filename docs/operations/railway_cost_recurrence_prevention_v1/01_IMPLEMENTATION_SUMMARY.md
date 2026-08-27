# Cost Recurrence Prevention V1 — Implementation Summary

**Date (UTC):** 2026-08-27  
**Mode:** local code + tests only.  
**Railway mutations:** none. **Production deploys:** none. **Production database:** not accessed.

## What this pack is

Structural protections so the Railway public-network cost incident cannot recur when production is later restored. The incident path was: one `uvicorn main:app` image hosting Scheduler loops, public-proxy `DATABASE_URL`, expensive jobs default ON, `create_all()` in recurring/health paths, and healthchecks that queried Postgres.

This task implements those protections **in code**. Documentation alone is not the control.

## What changed (code)

| Area | Control |
|------|---------|
| Process entry | `cartflow_api.py` and `cartflow_scheduler.py` are independent entries. Wrong role fails closed. |
| API startup | `main.py` startup no longer starts scanner, resume, snapshot, or archive loops. |
| Database host | Production rejects Railway public proxy / missing / malformed URL before a pool opens. |
| Scheduler jobs | Scanner, resume, snapshot builder, archive default **OFF**. Explicit env required. |
| Loops | Min sleep 5s, exponential backoff, no zero-sleep, no overlapping ticks, Postgres advisory lock. |
| Snapshots | Per-record cap kept; per-cycle byte budget added; abort when exceeded. |
| Health | `GET /health/scheduler` is in-process cache only. Deep DB diagnostic is admin + rate-limited. |
| Pool | Role-based bounds (API 5/5, Scheduler 2/2). Invalid/excessive values fail closed. |
| Deploy files | `railway.api.toml` and `railway.scheduler.toml` exist in-repo. **Not assigned in Railway.** |

`main.py` remains the composition layer. Scheduler lifecycle was extracted; no new operational logic was added to `main.py`.

## Intended Railway commands (later)

- API (`smart-reply-ai`): `python -m uvicorn cartflow_api:app --host 0.0.0.0 --port ${PORT:-8000}`
- Scheduler (`cartflow`): `python -m cartflow_scheduler`

Do not start either service in this task.

## Permanent rules preserved

- `main.py` is a wiring layer, not a place to add new loops.
- Autodeploy stays disabled until a later production-validation task.
- No secrets in logs or error strings.
- No production or Railway change occurred here.
