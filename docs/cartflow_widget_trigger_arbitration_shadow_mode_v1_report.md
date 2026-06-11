# Widget Trigger Arbitration Shadow Mode v1 — Report

**Date:** 2026-06-11 (UTC)  
**Type:** Shadow-mode observability only — **no enforcement, no customer-visible changes**  
**Runtime tag:** `v2-widget-trigger-arbitration-shadow-v1`  
**Prior review:** `docs/cartflow_widget_trigger_arbitration_review_v1.md`

---

## Executive summary

A central **Widget Trigger Arbitration** layer now **observes** widget open attempts, builds **`WidgetOpenIntent`** objects, evaluates **shadow decisions** (`allow` / `deny` / `upgrade` / `defer` / `ignore`), detects conflicts, and logs structured console output.

**Runtime widget behavior is unchanged:** existing gates, timers, copy selection, and UI paths execute exactly as before. Shadow calls run **before** existing logic and never return early or block opens.

---

## Files changed

| File | Change |
|------|--------|
| `static/cartflow_widget_runtime/cartflow_widget_arbitration.js` | **New** — shadow arbitration module |
| `static/cartflow_widget_runtime/cartflow_widget_loader.js` | Load arbitration after `state.js`, before `theme.js` |
| `static/cartflow_widget_runtime/cartflow_widget_flows.js` | Shadow observe hooks on `showBubbleCartRecovery`, `showExitNoCart`, trigger fire hooks |
| `static/cartflow_widget_runtime/cartflow_widget_triggers.js` | Shadow observe on hesitation/exit schedule |
| `static/widget_loader.js` | Runtime version → `v2-widget-trigger-arbitration-shadow-v1` |
| `tests/test_widget_trigger_arbitration_shadow_v1.py` | **New** — wiring + harness tests |
| `tests/fixtures/widget_arbitration_shadow_harness.js` | **New** — Node decision scenarios |
| `tests/test_cart_event_bridge_v1.py` | Runtime version assert updated |
| `tests/test_storefront_cart_bridge_v1.py` | Runtime version assert updated |
| `tests/test_storefront_cart_bridge_timing_v1.py` | Runtime version assert updated |
| `docs/cartflow_widget_trigger_arbitration_shadow_mode_v1_report.md` | This report |

**Not changed:** trigger timing, copy strings, gate enforcement, shell UI, dashboard, server APIs.

---

## Intent model (`WidgetOpenIntent`)

Built read-only by `Cf.Arbitration.buildIntent()` / `observeWidgetOpenAttempt()`:

| Field | Source |
|-------|--------|
| `trigger_source` | Tag / hook name (e.g. `exit_intent_with_cart`, `cart_hesitation_timer`) |
| `customer_context` | Cart detect state, checkout, dismiss suppress, converted |
| `cart_present` | `haveCartApprox`, bridge diagnostics, globals |
| `cart_value` | `cartflowState.cartTotal`, bridge normalized value |
| `has_reason` | `pending_reason_key` |
| `has_phone` | `State.hasValidStoredPhone()` |
| `is_vip` | `is_vip` / threshold vs cart value |
| `journey_type` | Resolved shadow type (see below) |
| `priority` | 1–6 from journey type |
| `requested_at` | `Date.now()` |
| `session_id` | `cartflowGetSessionId()` / recovery session storage |

**Journey types:** `cart_recovery`, `vip_recovery`, `exit_without_cart`, `return_to_site`, `manual_help`, `reason_continuation`.

Log: **`[CF ARBITRATION INTENT]`**

---

## Decision model (`requestWidgetOpen`)

Shadow-only evaluation — **`enforce: false`** in every **`[CF ARBITRATION DECISION]`** log.

| Action | When (shadow rules) |
|--------|---------------------|
| **allow** | No higher-priority block; cart/VIP path clear |
| **deny** | Reason or phone flow active (non-continuation intent) |
| **upgrade** | `cart_present` + `exit_without_cart` journey → `cart_recovery` or `vip_recovery` |
| **defer** | Exit intent while `cart_detected=pending` (bridge in-flight) |
| **ignore** | Widget already visible / first screen locked |

**Priority order (shadow):** vip_recovery → cart_recovery → reason_continuation → manual_help → exit_without_cart → return_to_site.

Log: **`[CF ARBITRATION DECISION]`** with `trigger_source`, `journey_type`, `priority`, `cart_present`, `action`, `reason`, `upgraded_to`.

---

## Copy decision shadow

For each open attempt, shadow compares:

| Field | Meaning |
|-------|---------|
| `actual_copy_source` | What runtime **does today** (tag-based: `exit_intent*` → exit template) |
| `shadow_copy_source` | What arbitration **would** use (`journey_type`-based) |
| `copy_would_change` | `true` when sources differ and `cart_present` |

Expected future rule validated in shadow:

- `cart_recovery` / `vip_recovery` → `"تبي أساعدك تكمل طلبك؟"`
- `exit_without_cart` → exit template

Log: **`[CF ARBITRATION COPY]`**

**Observed conflict (expected in shadow):** `exit_intent_with_cart` with cart → `actual_copy_source=exit_intent_template_via_tag`, `shadow_copy_source=cart_recovery_default` → **`copy_source_mismatch_with_cart`** conflict logged.

---

## Journey state shadow

Read-only mirror at **`Cf.Arbitration.getShadowState()`** — does **not** drive `bubbleShown`, shell, or timers.

| Field | Purpose |
|-------|---------|
| `journey_type` | Last shadow-allowed journey |
| `trigger_source` | Last observed trigger |
| `widget_visible` | Mirrored from runtime `bubbleShown` / shell open |
| `first_screen_locked` | Shadow lock after allow/upgrade |
| `reason_active` / `phone_active` | Mirrored from runtime |
| `cart_present` / `vip_present` | Mirrored from cart detection |

Log: **`[CF ARBITRATION STATE]`**

---

## Conflict detection

Logged as **`[CF ARBITRATION CONFLICT]`** with `kind`:

| Kind | Detection |
|------|-----------|
| `exit_plus_cart` | Exit trigger + `cart_present` |
| `vip_cart_plus_exit` | VIP + cart + exit trigger |
| `widget_already_visible` | Decision `ignore` |
| `reason_flow_interruption_attempt` | Deny while reason active |
| `phone_flow_interruption_attempt` | Deny while phone active |
| `multiple_triggers_same_second` | ≥2 intents within 1000ms |
| `copy_source_mismatch_with_cart` | Actual vs shadow copy sources differ with cart |

**No enforcement** — log only.

---

## Integration points (observe-only)

| Location | Hook |
|----------|------|
| `showBubbleCartRecovery` | First line — `observeWidgetOpenAttempt` |
| `showExitNoCart` | First line — `observeWidgetOpenAttempt` |
| `fireCartRecovery` / `fireExitNoCart` / `fireExitWithCart` | `observeTriggerSignal` before existing logic |
| `scheduleCartHesitation` | `observeTriggerSignal` (scheduled) |
| `scheduleExitIntentTimer` | `observeTriggerSignal` (scheduled) |

Observe runs **before** existing `storefrontUiBlocked`, hesitation wall, and `bubbleShown` checks — so shadow sees blocked attempts too.

---

## Test results

### Python wiring tests (`tests/test_widget_trigger_arbitration_shadow_v1.py`)

**10/10 passed**

- Module in loader chain (after state)
- Shadow logs present; `enforce: false`
- Intent fields declared
- Flows observe **before** existing gates
- Show functions still called unchanged
- No enforcement in flows

### Node decision harness (`tests/fixtures/widget_arbitration_shadow_harness.js`)

**11/11 scenarios passed**

| # | Scenario | Shadow decision |
|---|----------|-----------------|
| 1 | Cart + exit | **upgrade** → `cart_recovery` |
| 2 | VIP + exit | **upgrade** → `vip_recovery` |
| 3 | Cart + hesitation | **allow** |
| 4 | Widget already open | **ignore** |
| 5 | Reason active | **deny** |
| 6 | Phone active | **deny** |
| 7 | Return resume | journey `return_to_site` |
| 8 | Multiple triggers | recent intent tracking |
| 9 | Cart pending | **defer** |
| 10 | No cart exit | **allow** |
| 11 | Copy mismatch | actual ≠ shadow sources |

Related suites updated for runtime tag: bridge + cart-event tests **pass**.

---

## Runtime behavior unchanged — confirmation

| Check | Result |
|-------|--------|
| `showBubbleCartRecovery` / `showExitNoCart` body | Unmodified logic after observe call |
| Trigger timers / delays | Unchanged |
| `getCartRecoveryQuestion` tag rule | Unchanged |
| `bubbleShown` / dismiss / hesitation wall | Unchanged |
| Enforcement in arbitration | **`SHADOW_MODE = true`** — decisions logged only |
| Flows call `requestWidgetOpen` to block | **No** — only `observeWidgetOpenAttempt` |

Customer-visible widget timing, copy, and journey execution remain on the pre-shadow code paths.

---

## Manual verification (post-deploy checklist)

On `https://4hz49e.zid.store` after deploying `v2-widget-trigger-arbitration-shadow-v1`:

1. Fresh window → DevTools Console → filter `[CF ARBITRATION`
2. Add Sony A7 → expect `[CF ARBITRATION INTENT]` with `cart_hesitation_timer` schedule + `cart_present` when bridge confirms
3. Trigger exit intent (mouse to top) → expect `[CF ARBITRATION CONFLICT]` kinds `exit_plus_cart` / `copy_source_mismatch_with_cart` when cart exists
4. Wait for hesitation widget → expect `[CF WIDGET SHOW]` unchanged + shadow `cart_recovery` decision
5. Confirm **customer-visible journey unchanged** from pre-shadow (same copy/timing as before)

**Deploy status:** not executed in this task — shadow code ready for deploy + log verification.

---

## Next step (out of scope)

When shadow logs prove decision quality on production traffic: **Enforcement v2** — route opens through gate, journey-type copy, exit session on allow only.

**Stop condition met:** shadow mode implemented, tested, reported — no enforcement.
