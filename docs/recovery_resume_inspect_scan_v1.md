# Recovery Resume Inspect / Scan v1

**Date (UTC):** 2026-06-01  
**Service:** `services/admin_recovery_resume_inspect_scan_v1.py`

## Purpose

Read-only observability for restart-survival / resume scanner behavior. Answers:

- Are there recoveries eligible for resume?
- Are there stale `running` schedules?
- Did restart survival leave schedules behind?
- What would the resume scanner do **right now**?
- Why would a row be resumed, skipped, or ignored?

**Not a repair tool.** No execution, claims, sends, scheduling mutations, or stale repair.

## Endpoints (admin session auth)

| Route | Role |
|-------|------|
| `GET /admin/operations/recovery-resume-inspect` | Per-row inspect + summary |
| `GET /admin/operations/recovery-resume-scan` | Dry-run scan simulation |

### Inspect filters

| Query | Description |
|-------|-------------|
| `store_slug` | Scope to one store |
| `status` | e.g. `scheduled`, `running` |
| `resume_only=1` | Only `resume_eligible` rows |
| `stale_only=1` | Only `stale_running` rows |
| `limit` | Max rows (default 100, max 400) |

### Inspect response

```json
{
  "ok": true,
  "version": "admin_recovery_resume_inspect_v1",
  "dry_run": true,
  "read_only": true,
  "summary": {
    "scheduled": 0,
    "running": 0,
    "completed": 0,
    "resume_eligible": 0,
    "stale_running": 0,
    "scheduled_due_now": 0
  },
  "items": [
    {
      "recovery_key": "store:session",
      "store_slug": "store",
      "status": "scheduled",
      "due_at": "2026-06-01T12:00:00Z",
      "created_at": "2026-06-01T11:00:00Z",
      "age_minutes": 60.0,
      "running_age_minutes": null,
      "resume_eligible": true,
      "resume_reason": "scheduled_due",
      "stale_running": false,
      "schedule_id": 1
    }
  ]
}
```

### Scan response (dry-run only)

```json
{
  "ok": true,
  "version": "admin_recovery_resume_scan_v1",
  "dry_run": true,
  "read_only": true,
  "no_db_writes": true,
  "would_resume": 1,
  "would_skip": 0,
  "would_ignore": 2,
  "results": [
    {
      "recovery_key": "store:session",
      "action": "resume",
      "reason": "scheduled_due"
    },
    {
      "recovery_key": "store:session2",
      "action": "ignore",
      "reason": "future_due_at"
    }
  ]
}
```

**Actions:** `resume` | `skip` | `ignore`

## Dry-run guarantees

The admin scan endpoint:

- Does **not** call `run_recovery_resume_scan_async` / `run_recovery_resume_scan_sync`
- Does **not** call `repair_stale_running_recovery_schedules`
- Does **not** call `resume_one_schedule` (which can mutate on safety failure)
- Does **not** claim, send WhatsApp, or write DB rows

Classification reuses read-only helpers: `recovery_resume_filter_decision`, `evaluate_resume_safety`, `_is_running_schedule_stale`.

## Admin Operations Center card

`/admin/operations` command center shows **Recovery Resume Health** with counts and buttons:

- **Inspect** → opens inspect JSON
- **Scan (Dry Run)** → opens scan JSON

## Tests

```bash
pytest tests/test_admin_recovery_resume_inspect_scan_v1.py -q
```
