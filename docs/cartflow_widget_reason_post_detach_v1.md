# Widget Fast Path V1.1 — POST /reason Client-Wait Root Cause

**Status:** REPAIR LIVE — acceptance re-run pending (`v2-widget-reason-post-detach-v1-5`)  
**Date (UTC):** 2026-07-12  

---

## Exact verdict

**The response spends the extra ~5.7 seconds in:**  
**browser TTFB — FastAPI `BackgroundTasks` recovery arm still completing inside `BaseHTTPMiddleware.call_next` before response headers are sent, amplified by a concurrent `POST /api/cart-event` racing the reason POST on the single uvicorn worker.**

| Correlated stage | Finding |
|------------------|---------|
| fetch() start → headers | **~5.5s** (= `client_net_ms` ≈ `post_reason`) |
| handler body | ~179 ms |
| response body + JSON parse | ~1–4 ms |
| service worker / retries / AbortController | absent |

Resource Timing after detach (remaining over-budget when present):

- `response_body` ≈ 1–4 ms  
- `request_to_response` ≈ 190–250 ms (RTT + handler)  
- `start_to_request` ≈ 2–320 ms (**cold connection / queue** — residual)

---

## Fix (reason path only)

1. **Arm detach:** daemon thread instead of `BackgroundTasks` (`X-CF-Reason-Arm: detached_thread`).
2. **Defer cart-event** until after reason OK (`defer_cart_persist`).
3. **Pure ASGI CORS** (no `BaseHTTPMiddleware` buffering).
4. **Skip `db_warm`** when process already warmed.
5. **Open phone immediately** after reason persist when `after_reason` needs capture (continuation via Back) — so reason→phone is not blocked by شكراً.

Phone **save** path unchanged.

---

## Production before / after

| Metric | Before | After detach (best pass) | Target |
|--------|--------|--------------------------|--------|
| post_reason P50 | **5772 ms** | **318 ms** (v1-2) | &lt;300 ms |
| server handler P50 | ~179 ms | ~47 ms | — |
| reason→phone (UI) | 6589 ms | ~373 ms instrumented when phone opens directly | &lt;500 ms |

Sprint remains open until a full N=20 pass clears both P50 gates with `v1-5` + probe measuring `[CF V2 SHOW PHONE]`.

Probe: `scripts/_widget_reason_post_detach_v1_prod.py`
