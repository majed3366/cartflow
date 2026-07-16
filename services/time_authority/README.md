# Platform Time Authority (WP-1 / WP-2 / WP-3)

First-class CartFlow capability for a single authoritative **now**, carried by **Query Time Context**, with governed **time filtering**.

## Import rules

```python
from services.time_authority import (
    authority_now,
    activate_query_time_context,
    QueryTimeContextKind,
    production_scope,
    simulation_scope,
    historical_replay_scope,
    resolve_effective_context,
    window_for,
    WindowRecipeId,
    classify_timestamp,
    classify_store_history,
)
```

## Ambient default (backward compatible)

With no explicit context, `resolve_effective_context()` / `authority_now()` use **production + SystemClock**. Missing context never invents simulation or replay.

## Query Time Context (WP-2)

Immutable after build. Fields include: `mode`, `source_id`, `time_provenance`, `authoritative_now`, `timezone_policy` (UTC), correlation/request/job ids, `simulation_run_id`, `replay_id`, opaque `scope_key`.

### HTTP

`register_query_time_context_middleware(app)` — registered from `main.py` as composition-only wiring (WP-2). **WP-3 does not touch `main.py`.**

## Time Filtering Contract (WP-3)

Stable interval shape: **`[start_at, end_at)`** (start inclusive, end exclusive) in **UTC**.

```python
from services.time_authority import window_for, WindowRecipeId, frozen_clock_scope
from datetime import datetime, timezone

as_of = datetime(2026, 5, 4, 15, 30, tzinfo=timezone.utc)
with frozen_clock_scope(as_of):
    today = window_for(WindowRecipeId.TODAY)
    last7 = window_for(WindowRecipeId.LAST_N_DAYS, n_days=7)
    month = window_for(WindowRecipeId.CURRENT_MONTH)
    prev = window_for(WindowRecipeId.COMPARISON_PERIOD, primary=last7)

# Index-friendly predicates:
#   timestamp >= today.start_at AND timestamp < today.end_at
start, end = today.as_sql_bounds()
```

### Recipes

| Recipe | Meaning (UTC) |
|--------|----------------|
| `today` / `yesterday` | Calendar day containing / before authoritative_now |
| `last_n_days` | Rolling `[now - N days, now)` |
| `current_week` / `previous_week` | ISO week Mon–Sun |
| `current_month` / `previous_month` | Calendar month (`this_month` alias → current) |
| `explicit_range` | Caller-supplied bounds (normalized to UTC) |
| `comparison_period` | Immediately preceding equal-duration window |
| `simulation_range` / `historical_replay_range` / `recovery_replay_range` | Mode-gated; optional `n_days` or calendar day |

Relative recipes never call the wall clock; they use `QueryTimeContext.authoritative_now`.

### Typed results

`WindowResultStatus`: `valid_window`, `out_of_window`, `invalid_range`, `insufficient_history`, `unsupported_timezone_policy`, `missing_query_time_context`, `invalid_argument`.

Timezone: **UTC only**. `TimezonePolicy.STORE_LOCAL_RESERVED` is rejected (Q1 parked).

### Emptiness

`classify_timestamp` / `classify_store_history` distinguish `no_store_history` vs `out_of_window` vs future sample thresholds — no merchant copy.

### Performance

Window construction is pure, O(1), no DB/network. Safe to call on hot paths. No caching layer.

## Compatibility

`legacy_utc_now()` remains the dual-path target. **Do not** migrate Knowledge/Dashboard consumers in WP-3.

## Not migrated yet

Consumer migration — WP-4+. Reality Simulator clock bind — **WP-10**. Presentation/merchant labels — **WP-11**.
