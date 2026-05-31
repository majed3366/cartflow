# Onboarding Hardening Audit — Real Merchant Journey (V2)

**Date:** 2026-06-01 (UTC)  
**Scope:** `services/merchant_onboarding_journey_v2.py`, nav locks + page gates in `static/merchant_dashboard_lazy.js`, readiness card, mobile CSS.  
**Out of scope:** recovery engine, WhatsApp send, widget runtime, lifecycle, decision engine.

**Verification:** `tests/test_merchant_onboarding_hardening_audit.py` (10 scenarios + account scoping).

---

## Results summary

| # | Scenario | Result | Notes |
|---|----------|--------|-------|
| 1 | Fresh merchant | **PASS** | 1/6 — only «تم إنشاء الحساب» complete; settings/WhatsApp/templates/widget nav locked |
| 2 | Widget test only | **PASS** | 2/6; settings unlocks; WhatsApp/templates stay locked |
| 3 | Store connected | **PASS** | «ربط المتجر» complete; WhatsApp unlocks; templates locked until WhatsApp |
| 4 | WhatsApp configured | **PASS** | WhatsApp step complete; templates unlock |
| 5 | Templates reviewed | **PASS** | Templates complete; «جاهز للتشغيل» stays locked until live widget enabled |
| 6 | Fully activated store | **PASS** (after fix) | 6/6; home shows «متجرك جاهز للتشغيل» with truth-derived checklist |
| 7 | Regression — disconnect store | **PASS** | Store step incomplete; progress drops; readiness card removed |
| 8 | Regression — disable WhatsApp | **PASS** | WhatsApp incomplete; templates config may persist; readiness removed |
| 9 | Direct URL access | **PASS** | All four gated pages expose guidance card data (`nav_locks`); JS gates controls (`ma-journey-gated`) |
| 10 | Mobile (iPhone / Android width) | **PASS** (after fix) | Responsive rules at 639px / 390px for progress, checklist, CTAs, gate cards |

---

## Issues found and fixed

### 1. Account step bypass (truth bug)

**Symptom:** `_flags_from_unified` forced `account=True` whenever any `Store` row existed, ignoring `merchant_user_id` ownership.

**Fix:** Removed override; account completion now follows unified sandbox account step only.

**File:** `services/merchant_onboarding_journey_v2.py`

### 2. Store Ready checklist incomplete (truth bug)

**Symptom:** Readiness card showed a static 3-line list (widget, WhatsApp, templates) — missing store connection and recovery enabled states required by the activation contract.

**Fix:** `_readiness_checklist()` derives lines from live flags: widget, store connected, WhatsApp, recovery enabled.

**File:** `services/merchant_onboarding_journey_v2.py`

### 3. Mobile overflow risk (presentation truth)

**Symptom:** Journey V2 panel had no mobile breakpoints; long Arabic copy and CTAs could clip on ~390px widths.

**Fix:** `@media (max-width: 639px)` and `390px` rules for wrap, `overflow-wrap`, full-width CTAs.

**File:** `static/merchant_app.css`

---

## No issues (verified)

- **Incorrect unlocks:** Nav locks follow `widget_test → connect_store → configure_whatsapp → review_messages` chain; all pages unlock only when `onboarding_complete`.
- **Progress mismatches:** `completed_steps` matches count of `is_complete` journey steps; percent = `round(100 * completed / 6)`.
- **Bypasses:** `maApplyJourneyPageGate` hides editable page content (`pointer-events: none`) when locked; gate card is the only interactive element.
- **Scenario 1 note:** Progress shows **1/6** (not 0/6) because «تم إنشاء الحساب» is legitimately complete for a signed-up merchant with an owned store row — all other steps remain locked.

---

## Regression coverage

Automated tests lock scenarios 1–10 in `tests/test_merchant_onboarding_hardening_audit.py`. Run:

```bash
python -m pytest tests/test_merchant_onboarding_hardening_audit.py tests/test_merchant_onboarding_journey_v2.py -v
```
