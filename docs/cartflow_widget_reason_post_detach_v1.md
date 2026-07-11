# Widget Fast Path V1.1 — POST /reason Client-Wait Root Cause

**Status:** REPAIR APPLIED — production acceptance pending (`v2-widget-reason-post-detach-v1-1`)  
**Date (UTC):** 2026-07-11  
**Commits:** `9860a71` (arm detach) + follow-up (defer cart-event race)

---

## Exact verdict

**The response spends the extra ~5.7 seconds in:**

1. **Primary (~2.5–5.5s):** FastAPI/Starlette `BackgroundTasks` for `_arm_recovery_after_reason_saved_bg`, which still runs to completion **inside** `@app.middleware("http")` / `BaseHTTPMiddleware.call_next` **before** response headers reach the browser.  
2. **Amplifier (~+2–3s after bridge fail-fast):** concurrent client `cart-event` (`ensure_before_reason_bg` at `setTimeout(0)`) racing the reason POST on the **single uvicorn worker**, monopolizing the event loop with sync DB work.

Not in: body parse, compression, service worker, fetch retries, or the measured handler body (~179 ms).

### Proof

| Evidence | Result |
|----------|--------|
| Local `BackgroundTasks` + `sleep(0.5)` under BaseHTTPMiddleware | client **~703 ms** |
| Local `threading.Thread` + `sleep(0.5)` | client **~21 ms** |
| Prod after arm detach only (`detached_thread` header) | post_reason still **~2–4 s** (race remains) |
| Handler `cf_timing.total_handler_ms` | **~179 ms** throughout |

---

## Fix (reason path only)

1. **Arm detach:** `_spawn_reason_recovery_arm_detached` — daemon thread + `asyncio.run(arm)` instead of `BackgroundTasks`.  
2. **No cart-event race:** `ensureCartTruthBeforeReason` sets `defer_cart_persist`; flows call `scheduleBackgroundPersistAfterReason()` **after** reason POST succeeds.

Headers: `X-CF-Reason-Arm: detached_thread`, `Server-Timing: handler;dur=…`.

Phone flow / lifecycle scheduling logic / bridge fail-fast identity rules unchanged.

---

## Acceptance targets

| Metric | Target | Before (fail-fast V1) |
|--------|--------|------------------------|
| post_reason client wait P50 | &lt;300 ms | ~5772 ms |
| reason → phone P50 | &lt;500 ms | ~6589 ms |

Probe: `scripts/_widget_reason_post_detach_v1_prod.py`
