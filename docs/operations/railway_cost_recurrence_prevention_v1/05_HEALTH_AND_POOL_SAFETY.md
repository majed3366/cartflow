# Health and Pool Safety

## Routine Scheduler health — no Postgres

`GET /health/scheduler` (`routes/ops.py`) returns `build_scheduler_health_snapshot()`.

That snapshot is **in-process only**:

- `source=in_process_cache`
- process role (from ownership policy)
- last successful cycle / last failure / next scheduled cycle
- enabled job names
- ready / live
- `overdue_scheduled_count` and `running_stale_count` forced to **0** (not queried)

It does not call `db.session.query`, `create_all()`, or any count against `RecoverySchedule`.

Railway / load-balancer probes must use this path (or `/ping` / `/health` without `?db=1`).

## Deep diagnostic — not a healthcheck

`GET /health/scheduler/deep?key=…`

- Requires `CARTFLOW_ADMIN_PASSWORD` or `CARTFLOW_SCHEDULER_DEEP_HEALTH_TOKEN`
- Rate-limited to one success per 60 seconds
- Returns overdue / stale counts
- Never calls `create_all()`
- **Must not** be assigned as the Railway healthcheck

Unauthorized → 403. Rate-limited → 429.

## Pool bounds

`services/db_pool_bounds_v1.py` replaces the old universal 30 + 30 overflow.

| Role | Default size | Default overflow | Timeout | Hard max size | Hard max overflow |
|------|--------------|------------------|---------|---------------|-------------------|
| API (default) | 5 | 5 | 5 s | 10 | 10 |
| Scheduler | 2 | 2 | 5 s | 5 | 5 |

Env overrides (validated, fail closed):

- `CARTFLOW_DB_POOL_SIZE`
- `CARTFLOW_DB_POOL_MAX_OVERFLOW`
- `CARTFLOW_DB_POOL_TIMEOUT` (max 30 s)

Non-integers, size &lt; 1, overflow &lt; 0, or values above the role cap raise `PoolBoundsError` before `create_engine`.

Connections: `pool_reset_on_return=rollback`, recycle 300 s, `pool_pre_ping` on Postgres. SQLite still uses `NullPool`.

No pool is created until the database network guard accepts the URL.

Legacy constants `POSTGRES_POOL_SIZE` / `MAX_OVERFLOW` / `TIMEOUT` in `extensions.py` are now 5 / 5 / 5 (import compatibility only). Live values come from `resolve_pool_bounds()`.
