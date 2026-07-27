# Home Performance Hardening V1 — Root Cause

## Before (measured)

Living Store production smoke (2026-07-27, Evidence Expansion pack):

| Metric | Desktop | Mobile |
|--------|---------|--------|
| Client `/api/dashboard/summary` `api_ms` | **3327** | **3297** |
| `diagnostic_snapshot_read_ms` | **13.8** | **13.2** |

Diagnostic read was never the bottleneck.

## Root cause (proven in code + unit tests)

`build_summary_from_snapshot` selected:

```text
source = TRANSPORT_DEGRADED if body.get("snapshot_degraded") else TRANSPORT_SNAPSHOT
```

`read_dashboard_snapshot_payload` sets `snapshot_degraded=True` whenever the row is **stale** (TTL expired), **while still returning the full persisted payload** (including pre-painted HES).

`finalize_dashboard_summary_payload` allows HES passthrough only for `TRANSPORT_SNAPSHOT` / `TRANSPORT_CACHE`.

Therefore:

```text
stale snapshot (common)
  → TRANSPORT_DEGRADED
  → HES passthrough skipped
  → Observation Admission Bridge (ORV → facts → themes → situations → publication → HES)
  → multi-second Home request
```

Unit proof:

- `test_degraded_transport_skips_passthrough_and_hits_orv` — DEGRADED + ready HES still calls ORV
- `test_snapshot_transport_passthrough_skips_orv` — SNAPSHOT + ready HES skips ORV
- `test_persisted_row_selects_snapshot_source_even_when_stale` — composition source is SNAPSHOT when a persisted row exists

## Implementation

1. **Composition transport** uses `TRANSPORT_SNAPSHOT` whenever a persisted snapshot row exists (`generated_at` or `version > 0`), even if stale/degraded freshness flags remain for UI.
2. **Timeline instrumentation** (`?home_perf=1`) records every Home stage with duration + % of total.
3. **Skip finalize#2** when finalize#1 already completed executive Home exit.

Freshness flags (`snapshot_stale` / `snapshot_degraded`) are unchanged for merchant visibility — only composition path is fixed.

## What we did not do

- No collectors / observables
- No UI / language / diagnosis changes
- No other pages
