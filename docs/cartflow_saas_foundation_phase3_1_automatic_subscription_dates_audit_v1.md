# CartFlow SaaS Foundation Phase 3.1 — Automatic Subscription Dates

**Date:** 2026-06-07  
**Status:** Implemented  
**Scope:** Admin subscription date automation, billing interval model, audit enrichment, merchant dashboard reflection. No billing, payment, checkout, or marketplace webhooks.

---

## Summary

Phase 3.1 replaces manual-first date entry in admin subscription control with preset actions that compute dates automatically. Admins enter custom start/end dates only when **Custom date** (`manual_custom`) is selected.

---

## Billing interval model

Canonical values (`services/merchant_billing_interval_v1.py`):

| Value | Label | Auto duration |
|-------|-------|---------------|
| `trial` | Trial — 14 days | 14 days |
| `monthly` | Monthly — 30 days | 30 days |
| `annual` | Annual — 365 days | 365 days |
| `manual_custom` | Custom | admin-provided dates |

Stored on `MerchantUser.billing_interval`.

---

## Automatic date rules

| Admin action | Fields set |
|--------------|------------|
| `start_trial` | `trial_started_at=now`, `trial_expires_at=now+14d`, `plan_status=trialing`, `billing_interval=trial` |
| `activate_monthly` | `plan_started_at=now`, `plan_expires_at=now+30d`, `plan_status=active`, `billing_interval=monthly` |
| `activate_annual` | `plan_started_at=now`, `plan_expires_at=now+365d`, `plan_status=active`, `billing_interval=annual` |
| `activate_custom` | `plan_started_at` (optional, default now), `plan_expires_at` (required), `billing_interval=manual_custom` |

Legacy Phase 3 actions (`change_plan`, `extend_trial`, `mark_active`, etc.) remain available.

---

## Admin UI

Page: `/admin/subscriptions/control`

Primary actions:

- Start 14-day trial
- Activate monthly (30 days)
- Activate annual (365 days)
- Custom date (shows date inputs only when selected)

---

## Audit log

`merchant_subscription_audit_logs` records:

- `action`
- `old_*` / `new_*` for plan, status, billing_interval, plan_started_at, plan_expires_at, trial_started_at, trial_expires_at
- `reason`
- `created_at`

---

## Merchant dashboard

`GET /api/merchant/subscription` includes:

- `billing_interval`, `billing_interval_label_ar`
- `subscription_expires_at` / `subscription_expires_at_ar` (display helper)
- Trial interval → show trial end; monthly/annual → show plan expiry

Settings card (`#settings`) and plans page (`#plans`) reflect interval and expiry.

---

## Marketplace readiness

`preview_marketplace_subscription_dates()` and `calculate_expires_at_from_interval()` accept future Zid/Salla payloads:

```json
{
  "plan": "growth",
  "billing_interval": "monthly",
  "started_at": "2026-06-07T00:00:00Z",
  "expires_at": null
}
```

If `expires_at` is missing, CartFlow derives it from `billing_interval`. No webhook handlers wired.

---

## Tests

- `tests/test_merchant_billing_interval_v1.py` — Phase 3.1 scenarios
- `tests/test_admin_subscription_control_v1.py` — Phase 3 regression

---

## Out of scope

Payment gateway, checkout, invoices, auto-renewal, marketplace webhook integration, feature blocking (enforcement remains off by default).
