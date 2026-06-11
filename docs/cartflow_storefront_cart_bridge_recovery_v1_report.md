# Storefront Cart Bridge Recovery v1 — Report

**Date:** 2026-06-11 (UTC)  
**Scope:** Platform-agnostic Storefront Cart Bridge with Zid as first adapter  
**Status:** Implementation complete — **awaiting deploy + manual Zid verification**

---

## 1. Problem (proven)

Cart Journey Truth Trace v1 showed:

| Layer | Result |
|-------|--------|
| Zid `/api/v1/cart` | Populated (Sony A7 ~10,000 SAR) |
| `window.cart` on storefront | `[]` |
| `POST /api/cart-event` | **0 requests** |
| `AbandonedCart` | **Missing** |
| Dashboard row | **Missing** |

Root cause: legacy cart persistence read only `window.cart` / global state; Zid product pages do not hydrate that global while the official cart API is populated.

---

## 2. Architecture summary

```
Storefront Platform (Zid / Salla / Shopify / generic)
        ↓
Cart Source Adapter (canHandle → readCart → normalize)
        ↓
Normalized Cart Payload (StorefrontCartBridgeContract)
        ↓
Cart Bridge Core (validate → dedupe → POST /api/cart-event)
        ↓
AbandonedCart → Reason / Recovery / Dashboard / VIP
```

**Principles enforced:**

- Adapters **never** POST to CartFlow — only Cart Bridge Core posts.
- Recovery core has **no Zid-specific logic** — only normalized payloads.
- Legacy `window.cart` path preserved as fallback.
- Existing Cart Event Bridge (trigger/display) unchanged; persistence augmented.

---

## 3. Files changed

### New (client)

| File | Role |
|------|------|
| `static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_contract.js` | Normalized payload contract, validation, dedupe key, `toCartEventPayload()` |
| `static/cartflow_widget_runtime/cartflow_storefront_cart_adapters.js` | Adapter interface; Zid adapter; Salla/Shopify stubs; generic fallback |
| `static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js` | Select adapter, validate, dedupe, POST, proof logs, `ensureCartTruthBeforeReason()` |

### Modified (client)

| File | Change |
|------|--------|
| `static/cartflow_widget_runtime/cartflow_cart_event_bridge.js` | `syncBackendCartState()` delegates to `StorefrontCartBridge.persistFromTrigger()` first |
| `static/cartflow_widget_runtime/cartflow_cart_sources.js` | Zid click/network paths call `readAndPersist()` |
| `static/cartflow_widget_runtime/cartflow_widget_flows.js` | Reason save calls `ensureCartTruthBeforeReason()`; orphan diagnostics on payload |
| `static/cartflow_widget_runtime/cartflow_widget_config.js` | Beacon includes `storefront_cart_bridge` diagnostics |
| `static/cartflow_widget_runtime/cartflow_widget_loader.js` | Loads 3 new modules before cart sources; runtime tag `layered-runtime-v19` |
| `static/widget_loader.js` | `RUNTIME_VERSION` → `v2-storefront-cart-bridge-v1` |

### New (server)

| File | Role |
|------|------|
| `services/storefront_cart_bridge_diagnostics_v1.py` | Read-only beacon + AbandonedCart truth composer |

### Modified (server)

| File | Change |
|------|--------|
| `main.py` | Persist `cf_storefront_cart_bridge` in AbandonedCart raw payload; `GET /dev/storefront-cart-bridge-truth` |

### Tests

| File | Role |
|------|------|
| `tests/test_storefront_cart_bridge_v1.py` | Contract wiring, server payload, VIP, dedupe, diagnostics |
| `tests/test_cart_event_bridge_v1.py` | Updated runtime version + loader module asserts |

---

## 4. Adapter contract

Each adapter implements:

| Method | Purpose |
|--------|---------|
| `canHandle()` | Platform detection |
| `detect()` | Same as canHandle (v1) |
| `readCart()` | Returns raw/normalized snapshot (Promise) |
| `normalize(raw)` | Platform → normalized cart |
| `sourceName` | Diagnostic label |

### Normalized payload (required for persistence)

| Field | Required |
|-------|----------|
| `platform` | Yes |
| `store_slug` | Yes — fail closed if missing |
| `canonical_store_slug` | Optional |
| `session_id` | Yes — fail closed if missing |
| `cart_id` | Yes |
| `cart_token` | Optional |
| `cart_value` | Yes — must be > 0 |
| `currency` | Optional |
| `item_count` | Yes — must be > 0 |
| `items[]` | Yes (may be sparse item fields) |
| `source` | Yes |
| `observed_at` | Yes |

Posted to server as existing `cart_state_sync` shape plus additive `cf_storefront_cart_bridge` metadata block.

---

## 5. Zid adapter behavior

**Priority order:**

1. `GET /api/v1/cart` (same-origin fetch)
2. Cached `POST /api/v1/cart/items` response (network hook)
3. `window.cart` fallback (legacy)

**Handles:** cart page, product add-to-cart, reload hydration, quantity/remove via network hooks, delayed hydration (15s cache), empty cart (returns null → bridge SKIP).

**Network hooks:** `installZidNetworkHooks()` wraps `fetch` for `/api/v1/cart` and `/api/v1/cart/items` — triggers `readAndPersist()` after successful mutations.

---

## 6. Idempotency strategy

**Dedupe key:** `canonical_store_slug|session_id|cart_id|cart_token|item_count|cart_value|source`

**Client:** 2.5s window — identical key skipped with `[CF CART BRIDGE SKIP] dedupe_unchanged`.

**POST when:** first detection, value change, item count change, token change, or `ensureCartTruthBeforeReason()` before reason save.

**Server:** unchanged lite-add upsert by `zid_cart_id` — duplicate identical payloads keep single row.

---

## 7. Widget flow integration (Phase 6)

Before reason POST, `openReasonPath()` calls `ensureCartTruthBeforeReason()`:

- If cart already persisted → proceed.
- Else → bridge read + POST attempt.
- If cart cannot be read → `cf_reason_orphan_risk: true` + `cf_cart_bridge_diagnostic` on reason payload; console `[CF REASON ORPHAN RISK]` — **no fake cart**.

---

## 8. Server-side cart-event safety (Phase 7)

Reviewed `_handle_cart_state_sync()` — **no breaking changes**:

- Accepts existing `cart_state_sync` payload + additive `cf_storefront_cart_bridge`.
- Idempotent upsert by cart id (lite add path).
- Canonical store resolution unchanged.
- VIP classification from `cart_total` unchanged.
- Empty legacy POST still upserts `status=cleared` (unchanged); **bridge client skips empty carts before POST**.

New: `cf_storefront_cart_bridge` persisted into `AbandonedCart.raw_payload` for operator forensics.

---

## 9. Diagnostics (Phase 8)

| Surface | Purpose |
|---------|---------|
| Console proof logs | `[CF CART BRIDGE ADAPTER|READ|NORMALIZED|POST|SKIP|ERROR]` |
| Runtime beacon | `runtime_truth.storefront_cart_bridge` via `getDiagnostics()` |
| Reason orphan | `cf_reason_orphan_risk`, `cf_cart_bridge_diagnostic` on reason payload |
| Dev endpoint | `GET /dev/storefront-cart-bridge-truth?store_slug=&session_id=&cart_id=` |

Operator questions answered in dev endpoint JSON (`operator_questions[]`).

---

## 10. Tests passed

```
pytest tests/test_storefront_cart_bridge_v1.py tests/test_cart_event_bridge_v1.py
30 passed
```

Coverage map:

| # | Scenario | Test |
|---|----------|------|
| 1 | Zid API path while window.cart empty | JS wiring: `/api/v1/cart`, fallback, core POST |
| 2 | Add-to-cart response | `cacheCartItemResponse`, network hooks |
| 3 | Empty cart | Contract rejects; core SKIP; server legacy = cleared |
| 4 | Duplicate read | Dedupe key + server single row |
| 5 | Reason before cart | `ensureCartTruthBeforeReason` in flows |
| 6 | Missing store slug | Contract `missing_store_slug` |
| 7 | Missing session id | Contract `missing_session_id` |
| 8 | VIP threshold (≥1000) | Server test 10,000 SAR → `vip_mode=True` |
| 9 | Legacy window.cart path | Server legacy payload test |
| 10 | Independent adapter stub | `stubAdapter("salla")`, `generic` adapter |

---

## 11. Manual verification (Phase 10)

**Target store:** https://4hz49e.zid.store  
**Status:** **PENDING DEPLOY** — implementation is local; production widget still on prior runtime until static assets deploy.

**Expected post-deploy flow:**

1. Fresh tab → add Sony A7 (~10,000 SAR)
2. Console shows:
   - `[CF CART BRIDGE ADAPTER] { adapter: "zid" }`
   - `[CF CART BRIDGE READ]`
   - `[CF CART BRIDGE NORMALIZED]`
   - `[CF CART BRIDGE POST]`
3. Network: `POST /api/cart-event` with `cf_storefront_cart_bridge.platform=zid`
4. `AbandonedCart` created under canonical store `cartflow-42b491`
5. VIP classification if threshold ≤ 10,000
6. Dashboard: VIP surface if above threshold

**Pre-deploy evidence:** Cart Journey Truth Trace v1 (`scripts/_cart_journey_truth_trace_v1_out/`) documents the failure chain this work closes.

---

## 12. No-regression confirmation

| Area | Status |
|------|--------|
| Widget display / triggers | Unchanged — Cart Event Bridge still routes through `Cf.Triggers` |
| Purchase Truth | No server purchase logic touched |
| Lifecycle Truth | No lifecycle classifier changes |
| RecoverySchedule | No scheduler changes |
| WhatsApp | No send path changes |
| Dashboard classification | VIP threshold logic unchanged |
| Legacy `window.cart` sync | Preserved as fallback after bridge attempt |
| Existing cart-event payloads | Backward compatible |

---

## 13. Next steps (post-review)

1. Deploy static assets + verify on `4hz49e.zid.store`
2. Re-run journey trace script post-deploy
3. Confirm dashboard row for Sony A7 cart
4. Salla / Shopify adapter implementation (stubs in place)

**STOP** — awaiting review. No Widget Trust Closure / Pilot / WhatsApp work in this task.
