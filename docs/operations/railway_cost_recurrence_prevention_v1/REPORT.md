# CartFlow — Railway Cost Recurrence Prevention V1

**Date (UTC):** 2026-08-27  
**Mode:** local implementation and testing only.  
**Railway mutations:** none. **Production deploys:** none. **Production database:** not accessed.  
**Secrets:** none printed.

---

## What was implemented

Independent process entries so API and Scheduler can no longer share one `uvicorn main:app` process. Production database host classification rejects the Railway public proxy before a pool opens. Expensive Scheduler jobs default OFF. Recurring `create_all()` was removed from the due-scanner loop. Loops are bounded (minimum 5s sleep, backoff, no overlap, Postgres advisory lock). Snapshot ticks have a total-per-cycle byte budget. Routine `/health/scheduler` is in-process cache only. Pool sizes are role-based and fail closed. Distinct `railway.api.toml` / `railway.scheduler.toml` exist in the repo and were **not** assigned in Railway.

## Incident path now blocked in code

| Incident multiplier | Code control |
|---------------------|--------------|
| Scheduler loops inside API uvicorn | `cartflow_api` + `reject_scheduler_via_web_entry`; startup no longer starts drivers |
| Scheduler inheriting API command | `python -m cartflow_scheduler` never imports FastAPI |
| Public-proxy `DATABASE_URL` | Guard fails closed before `create_engine` |
| Jobs default ON | Scanner / resume / snapshot builder / archive default OFF |
| `create_all()` every scan | Removed from `recovery_db_due_scanner` |
| Zero-sleep / overlap / multi-instance | Cycle guard + tick locks + advisory lock |
| Healthcheck → Postgres | Cache-only `/health/scheduler` |
| 30+30 pool | API 5/5, Scheduler 2/2, validated caps |

## Tests

Local pytest, SQLite/mocks only: **129 passed** in 35.01s.

Suites: `test_cost_recurrence_prevention_v1`, process-role / guardrails / diagnosis / phase0 / recovery health / snapshot loop / due-scanner loop / session lifecycle / deployment verify / due scanner / scheduler meta.

No test connected to Railway or production Postgres.

## Railway / production

No settings changed. No deploy. No start. No volume or service delete. Autodeploy was not touched.

## Pack

`docs/operations/railway_cost_recurrence_prevention_v1/` — `01`–`07` + this report.

---

COST RECURRENCE PREVENTION VERDICT:
- API and Scheduler entry points separated: YES
- API can start Scheduler loops: NO
- Scheduler can start API: NO
- Public Railway database proxy rejected in production: YES
- Scheduler expensive features default OFF: YES
- Recurring create_all removed: YES
- Zero-sleep retry possible: NO
- Overlapping scheduler cycles prevented: YES
- Scheduler healthcheck queries database: NO
- Snapshot cycle byte budget enforced: YES
- Role-based pool bounds implemented: YES
- main.py growth: scheduler loops extracted from startup; no new operational logic; ~22405 lines remain
- Tests passed: 129 passed (relevant local suite, 35.01s)
- Railway changes performed: NONE
- Production deployments performed: NONE
- Production database accessed: NO
- Recommended next single task: Assign `railway.api.toml` to `smart-reply-ai` and `railway.scheduler.toml` to `cartflow`, and set production `DATABASE_URL` to the private `*.railway.internal` hostname only — do not start API, Scheduler, or Postgres, and do not enable autodeploy.
