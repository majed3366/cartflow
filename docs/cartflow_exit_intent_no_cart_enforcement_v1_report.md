# Exit Intent No-Cart Enforcement v1 — Report

**Date (UTC):** 2026-06-11  
**Runtime tag:** `v2-exit-intent-no-cart-enforcement-v1`  
**Scope:** Exit intent open path only — via Widget Trigger Arbitration  
**Deploy status:** Local implementation + tests PASS — **not deployed to production in this task**

---

## 1) Product decision (enforced)

Exit Intent is **not** an independent customer journey on CartFlow.

| Condition | Policy |
|-----------|--------|
| `cart_present = false` | Exit intent **must not** open widget UI (`deny` / `ignore` / `defer` only) |
| `cart_present = true` | Exit intent may **accelerate** cart recovery (`cart_recovery` or `vip_recovery`) |

Blocked UI paths when no cart:

- `showBubbleCartRecovery("exit_intent_*")`
- `showExitNoCart()`
- Storefront recovery opener (`exit_intent_storefront_recovery`)

---

## 2) Root cause (production)

**Observed:** `cart_present=false`, `journey_type=exit_without_cart`, tag `exit_intent_storefront_recovery` → widget opened with browsing copy (*"هلا 👋 فيه خيارات ممكن تعجبك"*).

**Cause:** `fireExitNoCart()` in `cartflow_widget_flows.js` bypassed cart ownership and called `showBubbleCartRecovery("exit_intent_storefront_recovery")` when `isStorefrontRecoveryMode()` was true, even with no cart. `getCartRecoveryQuestion()` uses exit template whenever the tag contains `exit_intent`.

---

## 3) Files changed

| File | Change |
|------|--------|
| `static/cartflow_widget_runtime/cartflow_widget_arbitration.js` | `EXIT_NO_CART_POLICY_ENFORCED = true`; `evaluateShadowDecision()` returns `{ action: "deny", reason: "exit_without_cart_blocked", enforce: true }` for exit triggers without cart (non-pending); new `gateExitIntentOpen()`; conflict log `kind: exit_without_cart_blocked`; decision log includes `policy: exit_no_cart_v1` when blocked |
| `static/cartflow_widget_runtime/cartflow_widget_flows.js` | `fireExitNoCart`, `fireExitWithCart`, `showExitNoCart`, exit-tagged `showBubbleCartRecovery` route through `gateExitIntentOpen()`; cart exit opens with `openTag: cart_hesitation_timer` (cart copy, not exit template) |
| `static/widget_loader.js` | `RUNTIME_VERSION = v2-exit-intent-no-cart-enforcement-v1` |
| `tests/fixtures/widget_arbitration_shadow_harness.js` | Replaced `no_cart_exit_allow` with blocked/gate scenarios (+3 cases) |
| `tests/test_exit_intent_no_cart_enforcement_v1.py` | New wiring + harness gate (9 tests) |
| `tests/test_widget_trigger_arbitration_shadow_v1.py` | Updated for enforcement wiring + runtime bump |
| `docs/SYSTEM_SUMMARY.md` | §3 load model + §10 changelog |
| `docs/cartflow_exit_intent_no_cart_enforcement_v1_report.md` | This report |

**Not modified (per safety constraints):** Cart Bridge modules, persistence, AbandonedCart server logic, VIP server logic, RecoverySchedule, WhatsApp, dashboard.

---

## 4) Exact decision path

```
Exit trigger (mouse leave / timer)
        ↓
Cf.Triggers → fireExitNoCart | fireExitWithCart
        ↓
Cf.Arbitration.gateExitIntentOpen({ trigger_source, entrypoint })
        ↓
buildIntent()  →  [CF ARBITRATION INTENT]
        ↓
requestWidgetOpen(intent)  →  evaluateShadowDecision(intent)
        ↓
[CF ARBITRATION DECISION]  (+ [CF ARBITRATION CONFLICT] when blocked)
        ↓
Case B — no cart (not pending):
  action=deny, reason=exit_without_cart_blocked, enforce=true
  → gate returns { allowed: false } → NO UI

Case A — cart present:
  action=upgrade → upgraded_to=cart_recovery|vip_recovery
  → gate returns { allowed: true, openTag: cart_hesitation_timer }
  → showBubbleCartRecovery("cart_hesitation_timer")
  → getCartRecoveryQuestion → "تبي أساعدك تكمل طلبك؟"

Cart bridge pending (no resolved cart yet):
  action=defer, reason=cart_bridge_pending → NO UI (wait for bridge)
```

Secondary defense: `showExitNoCart` and exit-tagged `showBubbleCartRecovery` also call `gateExitIntentOpen()` before rendering.

Legacy fallback (arbitration module absent): prior behavior preserved — not used in normal V2 loader chain.

---

## 5) Shadow log compatibility

Preserved tags:

- `[CF ARBITRATION INTENT]`
- `[CF ARBITRATION DECISION]`
- `[CF ARBITRATION CONFLICT]`

New explicit reason / conflict kind:

```javascript
reason: "exit_without_cart_blocked"
kind: "exit_without_cart_blocked"
policy: "exit_no_cart_v1"
enforce: true
```

---

## 6) Tests passed

### Node harness (`tests/fixtures/widget_arbitration_shadow_harness.js`)

**14/14 PASS**, including:

| Scenario | Result |
|----------|--------|
| Exit + no cart | `deny` / `exit_without_cart_blocked` |
| Storefront recovery + no cart | `deny` / `exit_without_cart_blocked` |
| `gateExitIntentOpen` no cart | `allowed: false` |
| `gateExitIntentOpen` with cart | `allowed: true`, `openTag: cart_hesitation_timer` |
| Exit + cart | `upgrade` → `cart_recovery` |
| Exit + VIP cart | `upgrade` → `vip_recovery` |
| Cart hesitation | `allow` (unchanged) |
| Cart pending | `defer` (unchanged) |
| Reason / phone active | `deny` (unchanged) |
| Widget already visible | `ignore` (unchanged) |

### Python

```text
python -m unittest tests.test_exit_intent_no_cart_enforcement_v1 tests.test_widget_trigger_arbitration_shadow_v1 -v
→ 19 tests OK
```

### Required checklist (task §TESTS)

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Exit intent + no cart → widget does not open | PASS (gate + decision) |
| 2 | Exit intent + cart → cart journey opens | PASS (upgrade + cart tag) |
| 3 | Exit intent + VIP cart → VIP journey opens | PASS (upgrade → vip_recovery) |
| 4 | Hesitation journey unchanged | PASS (no gate on `fireCartRecovery`) |
| 5 | Cart Bridge unchanged | PASS (no bridge file edits) |
| 6 | AbandonedCart unchanged | PASS (no server/persistence edits) |
| 7 | Reason flow unchanged | PASS (reason deny path intact) |
| 8 | Return tracking unchanged | PASS (no visibility/resume edits) |
| 9 | Multiple exit events same session | PASS (`widget_already_visible` ignore + repeated deny) |
| 10 | Arbitration logs correct decision | PASS (`exit_without_cart_blocked` + CONFLICT) |

---

## 7) Manual verification

**Status:** Automated only in this task — production manual scenarios require deploy of `v2-exit-intent-no-cart-enforcement-v1`.

### Scenario 1 — Fresh session, no cart, attempt exit

**Expected after deploy:**

- No widget visible
- Console includes:

```text
[CF ARBITRATION DECISION] { action: "deny", reason: "exit_without_cart_blocked", enforce: true, policy: "exit_no_cart_v1", ... }
[CF ARBITRATION CONFLICT] { kind: "exit_without_cart_blocked", ... }
```

### Scenario 2 — Add Sony A7, exit before hesitation timer

**Expected after deploy:**

- Cart recovery yes/no opens (not exit browsing flow)
- Opening copy: **"تبي أساعدك تكمل طلبك؟"**
- `[CF ARBITRATION DECISION]` shows `action: "upgrade"` or cart allow with `openTag: cart_hesitation_timer`
- Journey type: `cart_recovery` or `vip_recovery` (Sony A7 ~10k SAR VIP store)

---

## 8) Regression check

| Area | Risk | Check |
|------|------|-------|
| Cart Bridge | Low | No bridge module changes; pending cart still `defer` |
| Hesitation timer | Low | `fireCartRecovery` unchanged; still uses shadow observe only |
| VIP server / lane | Low | VIP threshold read unchanged in arbitration; exit+cart upgrades to `vip_recovery` |
| Reason / phone flows | Low | Active reason/phone still denies non-continuation opens |
| Purchase / lifecycle truth | Low | No backend or AbandonedCart writes touched |
| Return-to-site | Low | `visibility_resume` journey type unchanged |
| Storefront recovery mode | **Fixed** | No longer opens widget without cart |

---

## 9) Verdict

**Exit Intent No-Cart Enforcement v1 — IMPLEMENTED (local), tests PASS.**

Next step (outside this task): push, deploy `v2-exit-intent-no-cart-enforcement-v1`, run manual Scenarios 1–2 on `https://4hz49e.zid.store`.
