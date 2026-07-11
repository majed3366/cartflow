# Widget Fast Path V1.1 — POST /reason Client-Wait Root Cause

**Status:** REPAIR APPLIED — production acceptance pending  
**Date (UTC):** 2026-07-11  
**Runtime:** `v2-widget-reason-post-detach-v1`

---

## Exact verdict

**The response spends the extra ~5.7 seconds in:** FastAPI/Starlette `BackgroundTasks` for `_arm_recovery_after_reason_saved_bg` (recovery arm after reason commit), which still runs to completion **inside** `@app.middleware("http")` / `BaseHTTPMiddleware.call_next` **before** response headers reach the browser.

Not in: body parse, compression streaming, service worker, fetch wrapper retries, or the measured handler body (~179 ms).

### Proof

Local reproduction with the same middleware pattern:

| Pattern | Client wait |
|---------|-------------|
| `BackgroundTasks` + `asyncio.sleep(0.5)` | **~703 ms** |
| `threading.Thread` + `time.sleep(0.5)` | **~21 ms** |

Prod correlation (fail-fast V1):

| Stage | ms |
|-------|-----|
| Server `total_handler_ms` | ~179 |
| Client `post_reason` / `client_net_ms` (TTFB) | ~5772 |
| Gap | ≈ arm duration still on the response path |

Sprint 2.3 had already moved the arm off the handler `await`, but **BackgroundTasks ≠ client-visible detach** under BaseHTTPMiddleware.

---

## Fix (smallest, reason path only)

Replace:

```python
background_tasks.add_task(_arm_recovery_after_reason_saved_bg, ...)
```

with:

```python
_spawn_reason_recovery_arm_detached(...)  # daemon thread + asyncio.run(arm)
```

Same arm function, same scheduling logic, fresh DB scope. Phone flow / bridge ensure / lifecycle contracts unchanged.

Headers for correlation: `X-CF-Reason-Arm: detached_thread`, `Server-Timing: handler;dur=…`.

---

## Acceptance targets

| Metric | Target | Before |
|--------|--------|--------|
| post_reason client wait P50 | &lt;300 ms | ~5772 ms |
| reason → phone P50 | &lt;500 ms | ~6589 ms |

Probe: `scripts/_widget_reason_post_detach_v1_prod.py`
