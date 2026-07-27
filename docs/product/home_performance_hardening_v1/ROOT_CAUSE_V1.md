# Home Performance Hardening V1 — Root Cause

## Before (measured)

Living Store production smoke (2026-07-27, Evidence Expansion pack):

| Metric | Desktop | Mobile |
|--------|---------|--------|
| Client `/api/dashboard/summary` `api_ms` | **3327** | **3297** |
| `diagnostic_snapshot_read_ms` | **13.8** | **13.2** |

Diagnostic read was never the bottleneck.

## Root cause (production timeline — Living Store)

`?home_perf=1` on production after first fix attempt:

```text
finalize#1 source=degraded has_persisted_row=False
reason=no_snapshot hes_sections=False
exit=observation_admission_bridge
home_stage_orv_admit ≈ 3314 ms (97.56% of total)
```

Dominant bottleneck = **Observation Admission Bridge on the Home request** when
`dashboard_snapshots` has **no summary row** for the resolved store.

Diagnostic snapshot read remained ~14 ms (not the bottleneck).

Contributing factor (also fixed): stale rows previously forced `TRANSPORT_DEGRADED`,
which skipped HES passthrough even when a persisted snapshot existed.

## Implementation

1. **Never run ORV→facts→situations→publication on SNAPSHOT/CACHE/DEGRADED Home reads.** LIVE builder only.
2. **DEGRADED + diagnostic publication** → `diagnostic_hes_only` (paint HES without ORV).
3. **Persisted stale rows** still use SNAPSHOT composition when a row exists.
4. **Timeline** via `?home_perf=1`; skip redundant finalize#2 when Home exit already done.

## What we did not do

- No collectors / observables
- No UI / language / diagnosis changes
- No other pages
