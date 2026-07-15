# Platform Time Authority (WP-1)

First-class CartFlow capability for a single authoritative **now**.

## Import rules

```python
from services.time_authority import (
    authority_now,
    activate_query_time_context,
    QueryTimeContextKind,
    FrozenTestProvider,
    use_provider,
    legacy_utc_now,
)
```

Prefer the package façade (`services.time_authority`). Do not call `datetime.now()` for new merchant-relevant decisions.

## Ambient default

With no active context, `authority_now()` uses **SystemClockProvider** (wall UTC). Existing platform behaviour is unchanged until consumers migrate (later WPs).

## Query Time Context

```python
with activate_query_time_context(
    QueryTimeContextKind.TESTING,
    as_of=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
):
    assert authority_now().year == 2026
```

HTTP middleware attach is **WP-2**. Filtering windows are **WP-3**.

## Compatibility

`legacy_utc_now()` is the dual-path target for replacing module-local `_utc_now` helpers later. **Do not** wire production consumers in WP-1.

## `main.py`

This package must not grow `main.py`. Composition wiring (if any) is WP-2+.
