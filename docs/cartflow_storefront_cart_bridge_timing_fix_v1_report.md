# Storefront Cart Bridge Timing Fix v1 — Report

**Date:** 2026-06-11 (UTC)  
**Status:** Implementation complete — **awaiting deploy + manual Zid verification**

---

## Root cause (restated)

Zid cart mapping is correct (RAW C → 10,000 / 1 PASS). Failure was **timing**:

1. `cart_sources.js` fires `readAndPersist` **1200ms after click**, before `POST /api/v1/cart/items` completes.
2. `fetchZidCartApi()` reads **empty** GET body → validation SKIP.
3. POST-hook `readAndPersist` was **coalesced** onto the in-flight empty read.
4. Empty GET responses **overwrote** populated cache.
5. No retry → no `POST /api/cart-event` → no `AbandonedCart`.

Evidence: `docs/cartflow_storefront_cart_bridge_timing_truth_v1_report.md`

---

## Files changed

| File | Change |
|------|--------|
| `static/cartflow_widget_runtime/cartflow_storefront_cart_adapters.js` | Empty-cache protection; populated-cache fallback after empty fetch; POST partial unchanged via `cacheCartItemResponse` |
| `static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js` | Retry scheduler (500/1200/2500ms); in-flight defer for priority triggers; `readAndPersistOnce` split |
| `static/cartflow_widget_runtime/cartflow_cart_sources.js` | `allowFreshAfterInFlight` on bridge calls |
| `static/widget_loader.js` | `RUNTIME_VERSION` → `v2-storefront-cart-bridge-timing-v1` |
| `static/cartflow_widget_runtime/cartflow_widget_loader.js` | Runtime tag → `layered-runtime-v20` |
| `tests/test_storefront_cart_bridge_timing_v1.py` | **New** — timing fix wiring + simulation + server regression |
| `tests/test_storefront_cart_bridge_v1.py` | Runtime version assert updated |
| `tests/test_cart_event_bridge_v1.py` | Runtime version assert updated |

**Not changed:** Dashboard, Lifecycle, Purchase Truth, WhatsApp, RecoverySchedule, VIP logic, widget UI, reason copy, server recovery core.

---

## Phase 1 — Empty cache protection

`cacheCartBody()` now:

- Detects populated cache (`cart_value > 0` AND `item_count > 0`)
- Rejects empty incoming bodies with `[CF CART BRIDGE CACHE KEEP] reason=ignore_empty_overwrite`
- Updates cache with `[CF CART BRIDGE CACHE UPDATE]` when incoming body is populated

`fetchZidCartApi()` after empty GET returns normalized cart from **retained populated cache** when available.

---

## Phase 2 — Retry after empty read

On `empty_cart_value` / `empty_item_count` (or empty read) during **`reason=add`** flows:

| Attempt | Delay |
|---------|-------|
| 1 | 500ms |
| 2 | 1200ms |
| 3 | 2500ms |

Logs: `[CF CART BRIDGE RETRY SCHEDULED]`, `[CF CART BRIDGE RETRY FIRED]`, `[CF CART BRIDGE RETRY STOP]`

Stops when: `cart_persisted`, max attempts, or generation cancelled on successful POST.

---

## Phase 3 — In-flight coalescing fix

Priority add triggers (`post_items`, `cart_sources`, `zid_network_hook`, `ensure_before_reason`, `empty_retry`) with `allowFreshAfterInFlight`:

- If `inFlightPromise` active → **defer** fresh `readAndPersist` until prior promise settles
- Does **not** return stale empty result to POST-hook caller without retry

Non-priority calls still coalesce to in-flight promise (unchanged dedupe behavior).

---

## Phase 4 — POST items partial priority

Unchanged adapter path: `cacheCartItemResponse()` → synthetic `products[]` partial → `cacheCartBody()` → `readCart()` cache hit → normalize → bridge validation → POST.

Protected from empty GET overwrite (Phase 1). POST-hook uses `force: true` + fresh-after-in-flight.

---

## Phase 5 — Reason guard

`ensureCartTruthBeforeReason()` passes `source_hint: ensure_before_reason` + `allowFreshAfterInFlight` — benefits from retry + cache protection. Orphan diagnostics preserved if all retries fail.

---

## Tests passed

```
pytest tests/test_storefront_cart_bridge_timing_v1.py \
       tests/test_storefront_cart_bridge_v1.py \
       tests/test_cart_event_bridge_v1.py
44 passed
```

Coverage map:

| # | Scenario | Test |
|---|----------|------|
| 1 | Empty GET before add doesn't permanently block | Cache keep + retry wiring |
| 2 | Empty GET can't overwrite populated cache | `test_cache_empty_does_not_overwrite_populated` |
| 3 | POST partial normalizes | Journey simulation |
| 4 | In-flight defer for priority | `test_inflight_defer_for_priority_triggers` |
| 5 | Retry eventually posts | Retry scheduler + server VIP test |
| 6 | Retry stops after persist | `cancelEmptyRetries` on POST ok |
| 7 | Empty removal no fake abandoned | `test_empty_legacy_sync_still_cleared_not_abandoned` |
| 8 | Duplicate protection | `test_duplicate_protection_unchanged` |
| 9 | Reason guard retry path | `test_reason_guard_uses_retry_path` |
| 10 | window.cart fallback | `test_window_cart_fallback_preserved` |

---

## Manual verification

**Status:** **PENDING DEPLOY** — fix is local until push/deploy to `smartreplyai.net`.

Post-deploy checklist on `https://4hz49e.zid.store`:

1. Fresh tab → add Sony A7
2. Console: `[CF CART BRIDGE RETRY SCHEDULED]` (if first read empty) → `[CF CART BRIDGE POST]`
3. Network: `POST /api/cart-event`
4. AbandonedCart: `cart_value=10000`, VIP mode, store `cartflow-42b491`

---

## No-regression confirmation

| Area | Status |
|------|--------|
| Dashboard / Lifecycle / Purchase / WhatsApp / RecoverySchedule | Unchanged |
| VIP threshold logic (server) | Unchanged — test passes |
| Duplicate AbandonedCart upsert | Unchanged — test passes |
| Empty cart server path (`status=cleared`) | Unchanged |
| Platform architecture (Adapter → Core → POST) | Preserved |
| window.cart fallback | Preserved |

---

**STOP** — awaiting deploy + manual verification. No Widget Trust / Pilot work in this task.
