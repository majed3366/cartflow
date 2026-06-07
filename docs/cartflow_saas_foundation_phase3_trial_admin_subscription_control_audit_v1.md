# CartFlow SaaS Foundation Phase 3 — Trial & Admin Subscription Control Audit

**Date (UTC):** 2026-06-07  
**Phase:** Operational subscription control before billing / marketplace activation  
**Commit message:** `saas foundation phase 3 trial admin subscription control`  
**Status:** Implemented

**Builds on:** Phase 1 plan model, Phase 2 merchant plans UI, `cartflow_packages_pricing_foundation_audit_v1.md`

**Not implemented:** Moyasar, Stripe, checkout, invoices, auto-renewal, Zid/Salla billing webhooks, merchant self-service upgrades.

---

## Summary

Phase 3 adds **admin-only** subscription operations for pilot merchants: trial lifecycle, manual plan assignment, expiration control, and **append-only audit logs**. Merchant dashboard reflects admin changes (plan, Trial status, trial end date, Manual source). Feature enforcement remains **off by default** (`CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE`).

---

## Part A — Trial model

| Field | Location | Notes |
|-------|----------|-------|
| `plan_status` | `merchant_users` | `active`, `trialing`, `expired`, `cancelled` (+ legacy `trial` → `trialing`) |
| `trial_started_at` | `merchant_users` | Set on `start_trial` |
| `trial_expires_at` | `merchant_users` | Set / extended by admin |

Trial respects **selected plan entitlements** when enforcement is enabled. Expired/cancelled blocks entitlements only when enforcement is on.

---

## Part B — Admin plan assignment

**Service:** `services/admin_subscription_control_v1.py`

| Action | Effect |
|--------|--------|
| `change_plan` | Set Starter / Growth / Pro |
| `start_trial` | Plan + `trialing` + trial dates |
| `extend_trial` | Add days to `trial_expires_at` |
| `mark_active` | `active` |
| `mark_expired` | `expired` |
| `cancel` | `cancelled` |
| `reactivate` | `active` |
| `set_plan_expiration` | `plan_expires_at` |
| `clear_expiration` | Clear plan + trial expiry |

All actions require **admin reason** string.

---

## Part C — Admin UI

| URL | Purpose |
|-----|---------|
| `GET /admin/subscriptions/control` | HTML control panel |
| `GET /api/admin/subscriptions` | Merchant list |
| `POST /api/admin/subscriptions/{id}/action` | Apply change |
| `GET /api/admin/subscriptions/{id}/audit` | Audit log |

Nav: Admin sidebar → **اشتراك المتاجر**

---

## Part D — Audit log

**Table:** `merchant_subscription_audit_logs`

Logs: admin source, merchant/store ids, old/new plan, old/new status, old/new expiry fields, reason, timestamp.

---

## Part E — Merchant dashboard reflection

`GET /api/merchant/subscription` extended with:

- `trial_started_at_ar`, `trial_expires_at_ar`
- `is_trialing`
- `subscription_updated_at_ar`

Settings card + `#plans` current-plan strip show Trial status and trial end when trialing.

---

## Part F — Entitlement readiness

`subscription_entitlements_blocked()` in `merchant_subscription_v1.py` — used by `has_feature()` when enforcement enabled.

| State | Enforcement OFF | Enforcement ON |
|-------|-----------------|----------------|
| Growth trial | All features allowed | Growth entitlements |
| Expired | All features allowed | Blocked |
| Active Starter | All features allowed | Starter entitlements only |

---

## Tests

`tests/test_admin_subscription_control_v1.py` — 8 cases per task requirements.

---

## Regression safety

No changes to recovery send paths, widget, VIP logic, WhatsApp, purchase truth, or billing. Merchant-facing UI remains read-only (no upgrade/payment).

---

**End of audit.**
