# Widget Fast Path V1 — Bridge Ensure Fail-Fast Repair

**Status:** PRODUCTION ACCEPTED (bridge target) — click→phone stretch not met  
**Date (UTC):** 2026-07-11  
**Runtime:** `v2-widget-bridge-fail-fast-v1`  
**Commit:** `3497c2c`

---

## Root cause branch removed

`ensureCartTruthBeforeReason` previously called:

```js
readAndPersist({ source_hint: "ensure_before_reason", allowFreshAfterInFlight: true })
```

That path:

1. Marked the call as a **priority** trigger (`isPriorityAddTrigger`)
2. **Awaited** any in-flight cart-event POST, then re-ran
3. Could also run a full cart-event POST on the reason critical path

Prod evidence (invest V1): **bridge_ensure P50 ≈ 3391 ms** — first over-budget stage.

---

## Smallest repair

| Path | Behavior |
|------|----------|
| `cart_persisted` | Return immediately (`already_persisted`) |
| Stable session + (cart id \| last normalized \| prior post ok) | Return immediately; schedule **non-blocking** bg persist (`ensure_before_reason_bg`) |
| Session only | Same — reason scopes by `store_slug` + `session_id` |
| No session | `missing_identity` → widget retry error (no wait) |

Also removed `ensure_before_reason` from `isPriorityAddTrigger` so bg hints never chain-wait.

**Not changed:** empty-retry ladder for normal add flows, phone save path, lifecycle, persistence semantics, persist-then-advance.

---

## Safety assertions (preserved)

| Assertion | How |
|-----------|-----|
| Event durability | Background `readAndPersist(ensure_before_reason_bg)` still scheduled (coalesce, not await) |
| Identity correctness | Reason uses stable session (+ cart_id when available); fail-fast when neither safe |
| No duplicate reason writes | In-flight reason lock unchanged; prod N=20 → 1 reason POST per journey |
| No cross-cart writes | Session/cart identity resolution unchanged |
| Persist-then-advance | `persistThenAdvance(res)` still gates screen advance on reason POST success |
| Lifecycle contracts | Phone path untouched; recovery arm not moved onto critical path |
| Missing identity | Clear retry UI (`fail_fast_path === "missing_identity"`) |

---

## Production before / after

| Metric | Before (invest V1) | After (fail-fast V1) | Target |
|--------|--------------------|----------------------|--------|
| bridge_ensure P50 | **3390.7 ms** | **2.6 ms** | &lt;100 ms ✅ |
| bridge_ensure P90 | — | 3.9 ms | — |
| reason → phone P50 | 6345.5 ms | 6588.5 ms | &lt;500 ms ❌ |
| pass journeys | — | **19 / 20** | ≥16 for bridge gate |

Dominant remaining stage after repair (journey 0 example):

| Stage | ms |
|-------|-----|
| ui_ack | 6.1 |
| bridge_ensure | **2.9** |
| payload_ready | 4.2 |
| post_reason (client wait) | **5771.8** |
| server handler | 178.9 |
| next_screen_render | 76.9 |

Fail-fast path observed: **`stable_identity_no_wait`** on all 20 journeys (never waited; never `missing_identity`).

Journey 9 flake: bridge 0.4 ms + 1 reason POST, but phone UI / fast-path trace missing (advance flake) — not a bridge wait regression.

---

## Evidence

- Probe: `scripts/_widget_bridge_fail_fast_v1_prod.py`
- Report: `scripts/_widget_bridge_fail_fast_v1_out/acceptance_report.json`
- Videos (first 5): `scripts/_widget_bridge_fail_fast_v1_out/videos/journey_01.webm` … `journey_05.webm`
- Tests: `tests/test_widget_bridge_fail_fast_v1.py`

---

## Honest follow-up

Bridge wait is removed. Reason→phone &lt;500 ms is **blocked by client `post_reason` / network wait (~5–6 s)** while server handler stays ~180 ms — out of scope for this bridge-only repair (phone-save path untouched).
