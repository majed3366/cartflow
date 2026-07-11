# Widget Fast Path V1.1 — POST /reason Client-Wait Root Cause

**Status:** REPAIR DEPLOYED — production acceptance in progress (`v2-widget-reason-post-detach-v1-3`)  
**Date (UTC):** 2026-07-11 / 2026-07-12  

---

## Exact verdict

**The response spends the extra ~5.7 seconds in:**  
**browser TTFB — FastAPI `BackgroundTasks` recovery arm still completing inside `BaseHTTPMiddleware.call_next` before response headers are sent, amplified by a concurrent `POST /api/cart-event` racing the reason POST on the single uvicorn worker.**

Not in: response body download, JSON parse, compression, service worker, fetch retries, AbortController, or the measured handler body (~179 ms).

| Correlated stage | Where the ~5.7s lived |
|------------------|------------------------|
| 1. fetch() start | client — start of `post_reason` |
| 2. request leaves browser | immediate |
| 3. server request received | often delayed behind cart-event / queue |
| 4. server handler completed | ~179 ms (already fast) |
| 5. response bytes sent | **blocked here** until BackgroundTasks finished under middleware |
| 6. browser response headers received | **~5.5s after (1)** ← matches `client_net_ms` |
| 7–9. body / parse / transition | ~2–80 ms |

Proof: `post_reason` ≈ `client_net_ms` (±3 ms); keep-alive direct POST after detach ≈ 170 ms client / ~45 ms server.

---

## Fix (reason path only)

1. **Arm detach:** `_spawn_reason_recovery_arm_detached` (daemon thread + `asyncio.run`) instead of `BackgroundTasks`.
2. **No cart-event race:** `defer_cart_persist` — schedule `ensure_before_reason_bg` only **after** reason POST succeeds.
3. **CORS ASGI:** `StorefrontWidgetCorsMiddleware` converted from `BaseHTTPMiddleware` to pure ASGI (no response buffering stream).
4. **db_warm skip** when process already warmed.

Headers: `X-CF-Reason-Arm: detached_thread`, `Server-Timing: handler;dur=…`.

Phone save / lifecycle logic / bridge identity rules / widget copy unchanged.

---

## Production timing (first acceptance pass, v1-2)

| Metric | Before (fail-fast V1) | After detach | Target |
|--------|----------------------|--------------|--------|
| post_reason P50 | **5772 ms** | **318 ms** | &lt;300 ms (barely miss) |
| server handler P50 | ~179 ms | **47.5 ms** | — |
| reason→continuation (`total_ms`) warm | — | **~255–290 ms** | — |
| reason→phone (incl. شكراً) P50 | 6589 ms | **1275 ms** | &lt;500 ms |

**Phone criterion note:** product `after_reason` gates phone behind **شكراً**. Measured `min(phone − post) ≈ 546 ms`, so reason→phone **cannot** be &lt;500 ms without changing that second-click flow. Reason→continuation already clears &lt;500 ms when POST is warm.

---

## Acceptance targets

| Metric | Target |
|--------|--------|
| post_reason client wait P50 | &lt;300 ms |
| reason click → phone P50 | &lt;500 ms (blocked by شكراً by design unless flow changes) |

Probe: `scripts/_widget_reason_post_detach_v1_prod.py`  
Runtime: `v2-widget-reason-post-detach-v1-3`
