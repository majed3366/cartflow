# Fast Add Trigger Race Recovery v1 Report

**Date (UTC):** 2026-06-13  
**Runtime:** `v2-fast-add-trigger-race-recovery-v1`  
**Prior audit:** `docs/zid_widget_trigger_block_truth_v1_report.md`  
**Verdict:** **FIX IMPLEMENTED** — durable replay + storefront persist hook; no silent deferred flush

---

## Executive summary

Fast add-to-cart on Zid could **POST `/api/cart-event` successfully** while the widget **never armed hesitation** and emitted **no trigger logs**. Root cause: **init race + silent `flushDeferredScheduling()` return** when the deferred queue was empty or `haveCartApprox()` was false at init time, compounded by **storefront cart bridge not notifying the trigger orchestrator** after persist.

This fix:

1. Hooks **`onStorefrontCartPersisted(cart)`** after successful storefront bridge POST.
2. Extends **`haveCartApprox()`** with **`storefrontBridgeHasCart()`** (`cart_persisted` + normalized cart).
3. Replaces silent flush with **`scheduleDeferredReplay()`** (poll up to 12s) → **arm** or **explicit `[CF TRIGGER BLOCKED]`** via `scheduleCartHesitation()`.
4. Emits **`[CF TRIGGER DEFERRED REPLAY]`** for every replay attempt (never silent).

---

## 1. Trigger scheduling path (trace)

```
Zid add-to-cart
  → StorefrontCartBridge.readAndPersist / zid network hook
  → postCartEvent → POST /api/cart-event
  → [NEW] Triggers.onStorefrontCartPersisted(cart)
  → onV2CartChannel / onNormalizedCartEvent (cart event bridge path)
  → scheduleCartHesitation OR defer if !v2TriggerInitDone
  → gateHesitationAfterCartAdd()
       ├─ ok → [CF TRIGGER DECISION] allowed + [CF TRIGGER SCHEDULED]
       └─ fail → [CF TRIGGER BLOCKED] + [CF TRIGGER BLOCKED REASON] + [CF TRIGGER DECISION] block_reason
  → setTimeout → [CF HESITATION TIMER FIRED] → fireCartRecovery
```

**Init boundary:** `Cf.Triggers.init()` (from `Flows.start()` after `public-config`) sets `v2TriggerInitDone = true` and calls **`flushDeferredScheduling()`**.

---

## 2. Deferred scheduling queue (before fix)

| Field | Purpose |
|-------|---------|
| `v2DeferredScheduleReasons[]` | Source tags (`cart_bridge`, `storefront_bridge_persist`, …) |
| `st.cfV2HesitationDeferredBaseAt` | Wall-clock base for hesitation deadline (preserves configured delay from first signal) |

**Pre-init path** (`onV2CartChannel`): push tag + set `cfV2HesitationDeferredBaseAt`, log `[CF HESITATION SKIPPED]` `trigger_init_not_done_deferred`, return.

**Gap:** Storefront bridge POST did **not** enter this queue unless cart event bridge also emitted.

---

## 3. `flushDeferredScheduling()` — why fast-add events were lost

### Before (silent loss)

```javascript
if (!had || !stRef || stRef.bubbleShown || !haveCartApprox()) {
  return;  // ← silent, no BLOCKED, no SCHEDULED
}
```

| Failure mode | What happened |
|--------------|---------------|
| **`!had`** | Only storefront POST, no `onV2CartChannel` → queue empty → **silent return** |
| **`!haveCartApprox()` at init** | `CartBridge.hasCart()` false (bridge never `emit()`); `window.cart` empty on product page → **silent return** even when `cart_persisted === true` |
| **Timing** | POST in flight at init; deferred base set but cart not detectable yet → **silent return** |

User-visible: cart-event OK, widget runtime loaded, **zero** `[CF TRIGGER *]` logs.

---

## 4. Implementation (v1)

### 4.1 `storefrontBridgeHasCart()`

Reads `StorefrontCartBridge.getDiagnostics()` — true when `cart_persisted` and normalized cart has items/value.

### 4.2 `onStorefrontCartPersisted(cart)`

Called from `postCartEvent` on HTTP 200 + `ok`. Pre-init: records deferred intent; post-init: schedules or starts replay.

### 4.3 `flushDeferredScheduling()` (rewritten)

Pending if: deferred queue **or** `cfV2HesitationDeferredBaseAt` **or** `storefrontBridgeHasCart()`.

- Cart detectable → `finalizeDeferredHesitation()` → `scheduleCartHesitation()` (explicit allow/block).
- Not detectable → `scheduleDeferredReplay()` (250ms poll, 12s max) → then same.

### 4.4 `[CF TRIGGER DEFERRED REPLAY]`

Logs `{ via, phase, outcome: cart_detected | exhausted_explicit_schedule, elapsed_ms }`.

On exhaustion, still calls `scheduleCartHesitation()` → if still no cart, **`block_reason: no_cart`** (explicit, not silent).

### Files changed

| File | Change |
|------|--------|
| `static/cartflow_widget_runtime/cartflow_widget_triggers.js` | Replay + persist hook + `haveCartApprox` extension |
| `static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js` | Call `onStorefrontCartPersisted` after POST ok |
| `static/widget_loader.js` | `RUNTIME_VERSION` → `v2-fast-add-trigger-race-recovery-v1` |
| `tests/test_fast_add_trigger_race_recovery_v1.py` | Static wiring tests (5) |

---

## 5. Scenario matrix (expected post-fix)

| Scenario | Expected outcome |
|----------|------------------|
| Add immediately after page load | `[CF TRIGGER RECEIVED]` via `storefront_bridge_persist` → defer/replay → **SCHEDULED** or **BLOCKED** |
| Add within first second | Same |
| Add before `Triggers.init()` | Defer → init flush/replay → **SCHEDULED** or **BLOCKED** |
| Add after init complete | Direct **SCHEDULED** or **BLOCKED** |

**Never:** zero trigger logs after valid add + successful cart POST.

---

## 6. Tests

```bash
python -m pytest tests/test_fast_add_trigger_race_recovery_v1.py -q
# 5 passed
```

Updated version assertions: `test_exit_intent_no_cart_enforcement_v1.py`, `test_widget_trigger_arbitration_shadow_v1.py`.

---

## 7. Related docs

- `docs/zid_widget_trigger_block_truth_v1_report.md` — audit that motivated this fix
- `scripts/fast_add_trigger_race_recovery_verify_v1.py` — four-scenario production probe

---

**End of fix report.**
