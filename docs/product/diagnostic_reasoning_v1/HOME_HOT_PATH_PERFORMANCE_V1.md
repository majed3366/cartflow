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

## Note

If production warm summary exceeds 300 ms, report the slowest finalize stage from `[DASHBOARD SUMMARY SUBPROFILE]` — do not hide behind wording.
