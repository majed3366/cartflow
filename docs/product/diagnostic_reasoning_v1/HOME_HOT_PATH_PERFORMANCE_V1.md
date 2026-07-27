# Home Hot-Path Performance Report V1

## Architecture change

| Before | After |
|--------|-------|
| Finalize always recomposed ORV → facts → situations → publication → HES + invented diagnosis language | Snapshot/cache Home: read diagnostic snapshot + passthrough pre-painted HES (no ORV/diagnosis compose) |
| Diagnosis invented in request (`diagnosis_language_v1`) | Diagnosis from persisted `diagnostic_snapshots` |

## Targets

- No request-time diagnostic composition on snapshot Home
- Warm Home summary ≤ 300 ms server time
- Cached repeat ≤ 200 ms where infrastructure permits
- Diagnostic snapshot read ≤ 50 ms (`diagnostic_snapshot_read_ms`)
- No unbounded historical query on Home (cap `MAX_REASON_ROWS=200` off-path only)

## Measurement

Use Living Store certified session + profiler spans:

- `home_stage_diagnostic_snapshot_read`
- `home_stage_hes_snapshot_passthrough`
- `home_stage_diagnostic_hes_only`

Background composition time is recorded on snapshot builder as `diagnostic_reasoning_v1.duration_ms` and is **not** part of Home request budget.

## Production measurement (2026-07-27 Living Store demo)

| Metric | Desktop | Mobile | Target |
|--------|---------|--------|--------|
| `/api/dashboard/summary` client wait | **6813 ms** | **7727 ms** | ≤300 ms warm |
| `diagnostic_snapshot_read_ms` | **14 ms** | **16 ms** | ≤50 ms |

**Constraint (honest):** diagnostic snapshot **read** meets ≤50 ms. Total summary latency still exceeds 300 ms because production Home was not yet on snapshot HES passthrough with pre-painted packages for this store (empty `diagnostic_snapshots` until materialize; live finalize still expensive). Root cause = snapshot/builder coverage + missing persisted diagnostics, not diagnostic scoring on the request.

After materialize + snapshot rebuild, Home should hit `home_stage_hes_snapshot_passthrough` / `home_stage_diagnostic_hes_only` and drop ORV recompose from the request budget.
