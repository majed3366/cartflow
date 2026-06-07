# CartFlow SaaS Foundation Phase 4 — Subscription Experience & Plan Visibility

**Date (UTC):** 2026-06-07  
**Phase:** Merchant-visible subscription experience (read-only)  
**Commit message:** `saas foundation phase 4 subscription experience`  
**Status:** Implemented

**Builds on:** Phase 1–3.1 subscription infrastructure, Phase 2 plans UI, marketplace sync architecture audit

**Not implemented:** payment gateway, billing, checkout, upgrade/downgrade flows, entitlement enforcement, marketplace webhooks

---

## Summary

Phase 4 moves from backend subscription infrastructure to **merchant-visible understanding**:

- What plan am I on?
- What do I receive today?
- What becomes available in higher tiers?
- How much time remains on trial or subscription?

All surfaces remain **read-only** — no payments, no upgrades, no feature blocking.

---

## Part A — Subscription Status Card V2

**Locations:** `#settings` (الباقة الحالية), `#plans` (باقتك الحالية)

**Displays:**

| Element | Source |
|---------|--------|
| Plan badge | `current_plan_label_ar` + `plan_badge_class` |
| Status badge | `status_badge_label_ar` (Active / Trial / …) |
| Source badge | `source_badge_label_ar` (Manual / Zid / Salla) |
| Health message | `subscription_health_ar` |
| Days remaining | `days_remaining_label_ar` |
| Trial end / plan expiry | existing date fields |

**Service:** `services/merchant_subscription_experience_v1.py`  
**API:** enriched `GET /api/merchant/subscription` via `MerchantSubscriptionStatus.to_api_dict()`  
**UI:** `static/merchant_subscription.js`, `static/merchant_plans_ui.js`, `templates/merchant_app.html`

---

## Part B — Plan benefits visibility

**Section:** «تشمل باقتك الحالية» with ✓ list

| Plan | Highlights |
|------|------------|
| Starter | Widget, WhatsApp recovery, dashboard, basic analytics |
| Growth | Starter + VIP detection/alerts, multi-message, advanced analytics |
| Pro | Growth + advanced recovery controls, operational insights, future intelligence |

**API field:** `current_benefits_ar`

---

## Part C — Upgrade discovery (read-only)

**Section:** dashed blocks «متاح في Growth» / «متاح في Pro»

Shown only for tiers above the merchant's current plan. Awareness only — no CTA to purchase.

**API fields:** `upgrade_discovery`, `upgrade_discovery_sections_ar`

---

## Part D — Subscription health

Calm merchant-facing Arabic messages:

| Condition | Example message |
|-----------|-----------------|
| Active trial | تنتهي التجربة خلال 12 يوماً |
| Active subscription | ينتهي الاشتراك خلال 27 يوماً |
| Expired | انتهى الاشتراك |
| Cancelled | تم إلغاء الاشتراك |
| No expiry date | اشتراكك نشط |

**API fields:** `subscription_health_ar`, `subscription_health_tone` (`ok` \| `warning` \| `danger` \| `neutral`)

**Helper:** `days_remaining_until()` — calendar-day diff to `subscription_expires_at`

---

## Part E — Admin visibility

**Page:** `/admin/subscriptions/control`

List table now includes without opening merchant details:

- Current plan, status, billing interval
- Days remaining (`days_remaining_label_ar`)
- Subscription health (`subscription_health_ar`)

**Service:** `build_admin_subscription_visibility()` used in `build_admin_subscription_row()`

---

## Implementation map

| Artifact | Path |
|----------|------|
| Experience logic | `services/merchant_subscription_experience_v1.py` |
| API enrichment | `services/merchant_subscription_v1.py` → `to_api_dict()` |
| Admin rows | `services/admin_subscription_control_v1.py` |
| Merchant UI | `templates/merchant_app.html`, `static/merchant_app.css` |
| Merchant JS | `static/merchant_subscription.js`, `static/merchant_plans_ui.js` |
| Admin UI | `templates/admin_subscription_control.html`, `static/admin_subscription_control.js` |
| Tests | `tests/test_merchant_subscription_experience_v1.py` |

---

## Regression safety

| Area | Status |
|------|--------|
| Plan model / entitlements | Unchanged — display only |
| Trial / admin control | Unchanged behavior |
| Enforcement | Off by default |
| Widget / recovery / VIP / WhatsApp | Untouched |

**Tests:** 35 SaaS-related tests pass (Phase 4 + Phase 1–3.1 regression)

---

**End of audit.**
