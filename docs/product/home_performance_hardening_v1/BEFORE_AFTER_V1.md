# Home Performance Hardening V1 — Before / After

## Before (Living Store, 2026-07-27)

| Metric | Desktop | Mobile |
|--------|---------|--------|
| Client `api_ms` | 3327–3584 | 3297–3952 |
| Server timeline total | ~3398 ms | ~3574 ms |
| Dominant stage | `home_stage_orv_admit` **97.5%** | same |
| Diagnostic read | ~14 ms | ~13–26 ms |

Root cause note: `reason=no_snapshot` → Observation Admission Bridge on Home request.

## After (Living Store, merge `070f914`, Railway Success)

| Metric | Desktop | Mobile |
|--------|---------|--------|
| Client `api_ms` cold/warm/repeat | 264 / **217** / 227 | 350 / **271** / 269 |
| Server timeline total | **23–27 ms** | **29–38 ms** |
| Dominant stage | `home_stage_diagnostic_snapshot_read` (~60%) | same |
| `home_stage_orv_admit` | **absent** | **absent** |

Verdict: `PASS_HOME_PERFORMANCE_HARDENING_V1`

## Separation (desktop warm example)

| Layer | ms |
|-------|-----|
| Server timeline (`_home_perf_timeline_v1.total_ms`) | ~26 |
| Snapshot row read | ~8 |
| Diagnostic snapshot read | ~16 |
| JSON serialize measure | &lt;1 |
| Client `api_ms` − server total ≈ network + TLS + browser | ~190 |

## Success

We know why Home was slow (`orv_admit` on `no_snapshot`), removed that path from Home reads, and measurements prove server work dropped from ~3.4s to ~26ms.
