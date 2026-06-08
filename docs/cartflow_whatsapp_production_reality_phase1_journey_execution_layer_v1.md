# CartFlow — WhatsApp Production Reality Phase 1: Journey Execution Layer V1

**Date:** 2026-06-07 (UTC)  
**Scope:** Actionable merchant journeys with progress states. No Meta/send/runtime changes.

## Problem

Onboarding journey selection (UI V1) was guidance-only. Merchants needed real next actions per path.

## Solution

`merchant_whatsapp_journey_execution_v1.py` converts each journey into:

| Journey | Primary CTA | Action |
|---------|-------------|--------|
| لدي واتساب أعمال | متابعة التفعيل | Scroll to number + recovery settings |
| لا أملك واتساب أعمال | إنشاء واتساب أعمال | Open official WhatsApp Business guide |
| أريد رقماً جديداً | تجهيز رقم جديد | Guided number prep + settings |
| لدي إعدادات Meta جاهزة | الربط المتقدم | Honest placeholder only |

**Progress states:** `whatsapp_onboarding_journey_status` — `not_started` | `in_progress` | `completed` (derived from store fields + explicit markers).

**Readiness integration:** Action-first card uses journey-specific CTA, remaining step, and outcome.

**Admin:** `/admin/whatsapp` shows journey + journey status + readiness.

**Future Meta hooks (reserved, not implemented):** `embedded_signup`, `meta_connection`, `business_verification`, `phone_verification`.

## Tests

`tests/test_merchant_whatsapp_journey_execution_v1.py` + existing WhatsApp readiness/onboarding tests.

## Regression safety

WhatsApp Mode, Readiness Engine, templates, execution policy, recovery, widget, lifecycle unchanged.
