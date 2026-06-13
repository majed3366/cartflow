# DB Pool Health Visibility v1 — Report

**Date (UTC):** 2026-06-13  
**Verdict:** **PASS — implemented and tested locally**

---

## Goal

Expose pool pressure before scanner failure; fail deployment gate when pool is exhausted.

---

## Exposed fields

Via `services/db_pool_diagnostics.build_db_pool_health_snapshot()`:

| Field | Description |
|-------|-------------|
| `size` | Base pool size |
| `checked_out` | Connections in use |
| `overflow` | Overflow connections |
| `max_connections` | `size + overflow` |
| `available_slots` | `max_connections - checked_out` |
| `timeout_count` | In-process QueuePool timeout events |
| `exhausted` | `true` if timeouts > 0 or `checked_out >= max_connections` |

---

## Surfaces

| Surface | Path |
|---------|------|
| Scheduler health | `GET /health/scheduler` → `db_pool` |
| Admin Operations JSON | `GET /api/admin/operational-health` → `db_pool` + `summary.db_pool_*` |
| Deployment gate | `evaluate_pool_health_gate()` + scheduler gate checks `db_pool.exhausted` / scanner pool errors |

---

## Deployment gate

`run_production_deployment_gate()` adds check `db_pool_health`:

- **Fail** if `exhausted=true`
- **Fail** if `timeout_count > 0`
- **Fail** if `checked_out >= max_connections`
- Scheduler gate also fails on `scheduler_db_pool_exhausted` or scanner `last_error` containing `queuepool` / `timed out`

---

## Tests

```bash
python -m pytest tests/test_db_pool_health_visibility_v1.py -q
```

**3 passed**

---

## Deploy note

Production `/health/scheduler` will include `db_pool` after deploy of this commit. Gate pool check uses remote scheduler response (not local process).
