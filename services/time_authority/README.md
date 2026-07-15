# Platform Time Authority (WP-1 / WP-2)

First-class CartFlow capability for a single authoritative **now**, carried by **Query Time Context**.

## Import rules

```python
from services.time_authority import (
    authority_now,
    activate_query_time_context,
    QueryTimeContextKind,
    production_scope,
    request_scope,
    worker_scope,
    frozen_clock_scope,
    historical_replay_scope,
    simulation_scope,
    resolve_effective_context,
    legacy_utc_now,
)
```

## Ambient default (backward compatible)

With no explicit context, `resolve_effective_context()` / `authority_now()` use **production + SystemClock**. Missing context never invents simulation or replay.

## Query Time Context (WP-2)

Immutable after build. Fields include: `mode`, `source_id`, `time_provenance`, `authoritative_now`, `timezone_policy` (UTC), correlation/request/job ids, `simulation_run_id`, `replay_id`, opaque `scope_key`.

Internal provenance sets `merchant_visible: False`.

### Scopes

| Helper | Use |
|--------|-----|
| `request_scope` / HTTP middleware | Per HTTP request (production) |
| `worker_scope` | Scheduler / background jobs |
| `frozen_clock_scope` | Frozen tests |
| `historical_replay_scope` / `recovery_replay_scope` | As-of replay |
| `simulation_scope` | Time Authority simulation mode (engine bind = WP-10) |

### HTTP

`register_query_time_context_middleware(app)` — registered from `main.py` as composition-only wiring.

## Compatibility

`legacy_utc_now()` remains the dual-path target. **Do not** migrate Knowledge/Dashboard consumers in WP-2.

## Not in this package yet

- Window filtering / emptiness — **WP-3**
- Consumer migration — later WPs
- Reality Simulator clock bind — **WP-10**
