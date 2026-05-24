# Activation visibility debug v1

**Date:** 2026-05-19  
**Scope:** Read-only instrumentation — no recovery, widget, or WhatsApp changes.

## Problem

After `cedd18f`, dashboard home shows KPI + month summary but not the activation card or compact strip.

## How to inspect

1. Open `/dashboard` (home) and check the **temporary debug band** under the activation slot (lazy shell only).
2. Browser console: `[ACTIVATION VISIBILITY]` object (server + client snapshot).
3. API: `GET /api/dashboard/summary` → `merchant_activation_visibility_debug` (duplicate of `merchant_activation.activation_visibility_debug`).
4. Server logs: `[ACTIVATION VISIBILITY] slug=… stage=… display=…`.

## Verdict: primarily **B (stage logic)**, often compounded by **JS apply timing**

### B — Server stage resolution

`resolve_merchant_home_layout()` sets `home_stage=production` and `activation_display=hidden` when `has_production_signal` and not state A (new/incomplete merchant):

| Signal | Condition |
|--------|-----------|
| `first_recovered` | First recovered cart milestone |
| `month_recovered_gt_0` | Any recovered carts in 30-day window |
| `month_revenue_gt_0` | Any recovered revenue in window |
| `first_sent_and_month_abandoned_gte_5` | First WhatsApp sent **and** ≥5 abandoned carts this month |

Many active stores hit production via **month stats** or **`first_sent` + 5+ abandoned**, not only “mature” merchants with real recovery revenue.

### Not primarily A — CSS alone

Rules in `merchant_app.css`:

- `#page-home.page.active #ma-activation-root:not([hidden])` only applies when the `[hidden]` attribute is **absent**.
- If JS sets `root.hidden = true`, CSS cannot force visibility.

So a CSS-only bug is unlikely unless the root never gets `hidden` cleared; the usual failure is **`[hidden]` left by JS**.

### JS timing (explains “I’m on home but card is gone”)

`applyMerchantActivation()` in `merchant_dashboard_lazy.js` runs **once** when `/api/dashboard/summary` returns:

- If `activation_display === "hidden"` and `#page-home` is **not** `.active` at that moment → early exit: `root.hidden = true`, `innerHTML = ""`.
- Navigating to home later does **not** re-run activation apply.
- If home **is** active, `hidden` is upgraded to **compact** (`cedd18f`) — card should render unless summary never included `merchant_activation`.

**Inferred `ui_blocker_inferred` values** (client debug):

| Value | Meaning |
|-------|---------|
| `js_applied_while_not_on_home` | Production hidden + summary applied off home |
| `css_hidden_attr_or_js_cleared_root` | Root still hidden on home after apply |
| `server_hidden_upgraded_to_compact_expected` | Server hidden but on home — compact should show |
| `missing_merchant_activation` | Summary missing activation payload |
| `ok_should_show` | Root visible with content |

## Expected product behavior (reference)

| Merchant | Home should show |
|----------|------------------|
| New / incomplete | Full activation card (`activation_display=prominent`) |
| Activated, not production | Compact strip (`compact`) |
| Production (mature) | Hide activation entirely **or** compact on home only (product decision; current server sends `hidden`) |

## Recommended follow-ups (not in this debug commit)

1. Re-run `applyMerchantActivation` on `hashchange` when page is `home`.
2. Tighten production signals (e.g. require `first_recovered` or revenue, not `month_abandoned >= 5` alone).
3. Remove temporary debug band + API fields after fix is verified.
