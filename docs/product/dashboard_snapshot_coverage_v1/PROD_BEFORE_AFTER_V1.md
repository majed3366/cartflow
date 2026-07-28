# Dashboard Snapshot Coverage V1 — Production before / after

**PR:** [#117](https://github.com/majed3366/cartflow/pull/117)  
**Merge:** `12c6a6a8b3224fbc48449143a7c20a6f628ed22f`  
**Railway:** Success  

## BEFORE (Home Performance Hardening measure)

Living Store `demo` Home timeline notes:

```text
finalize#1 source=degraded has_persisted_row=False
reason=no_snapshot hes_sections=False
exit=diagnostic_hes_only
```

| Field | Value |
|-------|--------|
| `snapshot_reason` | `no_snapshot` |
| Persisted summary row | **No** |
| Exit | `diagnostic_hes_only` (fast fallback) |
| Client `api_ms` | ~217–271 ms (after ORV ban) |

Root cause: builder eligibility `widget_placeholder_slug` excluded merchant-bound `demo`.

## AFTER (coverage verify)

Verdict: **`PASS_SNAPSHOT_COVERAGE_V1`**

| Field | Value |
|-------|--------|
| Review store | `demo` |
| `has_persisted_row` | **true** |
| `snapshot_reason` | none |
| `snapshot_version` | 1 |
| `snapshot_generated_at` | `2026-07-28T00:21:33Z` |
| Exit | **`hes_snapshot_passthrough`** |
| Client `api_ms` | **181** |
| Server timeline | **24.5 ms** |
| HES present | yes |

Evidence JSON: `prod_coverage_verify.json`  
Screenshot: `prod_coverage_home.png`

## Preserved

- Home fast path (no ORV on snapshot reads)
- Diagnosis unchanged
- No collectors / other pages

## STOP

Verification complete. No further work in this package.
