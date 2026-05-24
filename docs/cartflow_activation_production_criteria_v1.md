# Production activation hide criteria v1

**Date:** 2026-05-19  
**Scope:** `resolve_merchant_home_layout()` / `has_production_signal()` only (no JS timing change).

## Change

| | Before | After |
|---|--------|-------|
| **Production signals** | `first_recovered` OR `month_recovered > 0` OR `month_revenue > 0` OR (`first_sent` AND `month_abandoned >= 5`) | Recovery/revenue only (same first three) |
| **Removed reason** | `first_sent_and_month_abandoned_gte_5` | — |

## Verification matrix

| Merchant profile | Old stage / display | New stage / display | Notes |
|------------------|---------------------|---------------------|-------|
| Onboarded, first send, 20 abandoned, 0 recovered, 0 revenue | `production` / `hidden` | `activated` / `compact` | **Primary fix** — false production removed |
| Onboarded, first send, 5 abandoned, 0 recovered | `production` / `hidden` | `activated` / `compact` | Threshold 5 no longer triggers hide |
| Onboarded, `first_recovered` or month recovered > 0 | `production` / `hidden` | `production` / `hidden` | Unchanged — mature |
| Month recovered revenue > 0 | `production` / `hidden` | `production` / `hidden` | Unchanged |
| New / incomplete onboarding | `activation` / `prominent` | `activation` / `prominent` | Unchanged (state A) |

## Expected merchants affected

- **Gain compact activation UI:** Stores that sent WhatsApp and accumulated abandoned carts in the 30-day window but have **no** recovered cart and **no** recovered revenue in that window.
- **Unchanged:** Stores with at least one recovery signal (milestone, monthly recovered count, or monthly recovered revenue).

## Code

- `services/merchant_dashboard_home_stage_v1.py` — `production_signal_reasons()`, `has_production_signal()`
- Debug payload uses the same helpers via `merchant_activation_visibility_debug_v1.py`
