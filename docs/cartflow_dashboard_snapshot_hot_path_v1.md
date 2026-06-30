# Dashboard Hot Path Elimination — P0

Merchant dashboard JSON endpoints become **read-only snapshot consumers** when
`CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1`. Live computation moves to a background builder
on the scheduler service only.

## Architecture

```
Scheduler service                    API service (smart-reply-ai)
─────────────────                    ─────────────────────────────
dashboard_snapshot_loop_v1           GET /api/dashboard/*
  └─ builder (bounded)                   └─ read dashboard_snapshots ONLY
       └─ upsert rows                         └─ stale OK, miss → degraded
```

## Feature flag

| Variable | Value | Service |
|----------|-------|---------|
| `CARTFLOW_DASHBOARD_SNAPSHOT_MODE` | `1` | API + Scheduler |
| `CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED` | `1` (optional on scheduler) | Scheduler |
| `CARTFLOW_DASHBOARD_SNAPSHOT_INTERVAL_SECONDS` | `45` (default) | Scheduler |
| `CARTFLOW_DASHBOARD_SNAPSHOT_STORES_PER_TICK` | `5` (default) | Scheduler |

**API service:** set `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1`, keep `CARTFLOW_PROCESS_ROLE=api`.
Do **not** enable builder on API.

**Scheduler service:** set both `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1` and
`CARTFLOW_PROCESS_ROLE=scheduler` (builder auto-starts).

## Snapshot types

| Type | Endpoint |
|------|----------|
| `summary` | `GET /api/dashboard/summary` |
| `normal_carts` | `GET /api/dashboard/normal-carts` |
| `refresh_state` | `GET /api/dashboard/refresh-state` |
| `widget_panel` | `GET /api/dashboard/widget-panel` |
| `store_connection` | `GET /api/merchant/store-connection` |
| `dashboard_cards` | (embedded in summary builder) |

## Observability logs

- `[DASHBOARD SNAPSHOT READ]` — successful snapshot read (`endpoint=widget-panel|store-connection|...`)
- `[DASHBOARD SNAPSHOT MISS]` — no row found
- `[DASHBOARD DEGRADED]` — empty/stale/budget fallback
- `[DASHBOARD HOT PATH VIOLATION]` — live builder invoked during API request (`endpoint=...`)
- `[DASHBOARD FIRST REQUEST WARM BLOCKED]` — DB READY / heavy warm skipped on dashboard path
- `[DASHBOARD SNAPSHOT BUILDER TICK]` — background build pass
- `[DASHBOARD SNAPSHOT LOOP STARTED]` — scheduler loop boot

## Production verification plan

### Pre-deploy

1. Run migration: `alembic upgrade head`
2. Local tests: `python -m pytest tests/test_dashboard_snapshot_hot_path_v1.py -q`

### Phase A — shadow (flag off)

1. Deploy code to API + scheduler with `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=0`
2. Confirm no behavior change; builder loop skipped on API

### Phase B — builder only

1. Enable on **scheduler only**: `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1`
2. Wait 2–3 loop ticks (~90s)
3. SQL check:
   ```sql
   SELECT store_slug, snapshot_type, generated_at, expires_at, version, status
   FROM dashboard_snapshots
   ORDER BY generated_at DESC
   LIMIT 20;
   ```
4. Confirm `[DASHBOARD SNAPSHOT BUILDER TICK]` in scheduler logs

### Phase C — API read path

1. Enable on **API**: `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1`
2. Smoke:
   ```bash
   curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" \
     -H "Cookie: ..." https://smartreplyai.net/api/dashboard/summary
   curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" \
     -H "Cookie: ..." https://smartreplyai.net/api/dashboard/normal-carts
   ```
3. Expect `<0.2s` P95 and logs `[DASHBOARD SNAPSHOT READ]` (not `[DASHBOARD HOT PATH VIOLATION]`)
4. Dashboard UI shows data (may be up to TTL seconds stale)

### Phase D — failure modes

1. Stop scheduler → API returns **stale** then **degraded empty** (not 500)
2. Pool pressure on scheduler → `[DASHBOARD SNAPSHOT BUILDER SKIP] reason=pool_pressure_*`
3. No simultaneous `/ping` stalls during dashboard load

## Rollout plan

| Step | Action | Rollback |
|------|--------|----------|
| 1 | Deploy migration + code | — |
| 2 | Scheduler: `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1` | Set `=0` |
| 3 | Verify snapshots populated (5 min) | — |
| 4 | API: `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1` | Set `=0` (instant live path) |
| 5 | Monitor 24h: 499 rate, pool pressure, snapshot age | Disable flag |

**Rollback:** set `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=0` on API — immediate return to live computation. Snapshot table is derived; no data loss.

## Success criteria

- [ ] Dashboard API P95 < 200ms with snapshot mode on
- [ ] Zero `[DASHBOARD HOT PATH VIOLATION]` on production API logs
- [ ] No `abandoned_carts` / `cart_recovery_logs` queries on dashboard GET paths
- [ ] Stale snapshots served when builder delayed (no hang)
- [ ] Degraded empty JSON when no snapshot (no 500)

## Files

| File | Role |
|------|------|
| `models.py` | `DashboardSnapshot` ORM |
| `alembic/versions/o1p2q3r4s5t6_add_dashboard_snapshot.py` | Table + indexes |
| `services/dashboard_snapshot_v1.py` | Storage + flags |
| `services/dashboard_snapshot_read_v1.py` | API read path |
| `services/dashboard_snapshot_builder_v1.py` | Background builder |
| `services/dashboard_snapshot_loop_v1.py` | Async loop |
| `services/dashboard_snapshot_hot_path_guard_v1.py` | Violation guard |
| `tests/test_dashboard_snapshot_hot_path_v1.py` | Tests |
