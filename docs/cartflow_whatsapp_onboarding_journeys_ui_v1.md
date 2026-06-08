# CartFlow — WhatsApp Onboarding Journeys UI V1

**Date:** 2026-06-07 (UTC)  
**Scope:** Merchant-facing journey selector + persistence + readiness/admin visibility.  
**Out of scope:** Meta integration, Embedded Signup, Cloud API, WABA, provider migration, send-path changes.

## Problem

A single generic CTA («إكمال التفعيل») cannot serve merchants in different real-world situations (existing WhatsApp Business, no Business account, Meta-ready, new number).

## Solution

1. **Journey selector** on `#whatsapp`: «كيف تريد استخدام واتساب؟» with four options.
2. **Persistence:** `stores.whatsapp_onboarding_journey` — `existing_whatsapp_business` | `no_whatsapp_business` | `meta_ready` | `new_number` | `null`.
3. **Journey-specific guidance:** activation steps, next action, expected outcome per path.
4. **CTA behavior:** no journey → «اختيار مسار واتساب» (`open_journey_selector`); with journey → «متابعة التفعيل» (existing action-first CTA). `meta_ready` shows honest placeholder for advanced linking.
5. **Readiness card:** selected journey, remaining step, next action, outcome (via `enrich_readiness_with_onboarding_journey`).
6. **Admin:** `/admin/whatsapp` shows onboarding journey + connection/readiness state.

## Module

- `services/merchant_whatsapp_onboarding_journeys_v1.py`

## API / UI wiring

- `GET/POST /api/recovery-settings` — `whatsapp_onboarding_journey`, `onboarding_journeys` block.
- `merchant_whatsapp_settings.js` — `renderJourneyBlock()`, journey option POST, CTA handler.
- `merchant_whatsapp_connection_readiness_v1.py` — merchant API enriched with journey fields.
- `admin_whatsapp_visibility_v1.py` — journey key + Arabic label on admin rows.

## Copy principles

Arabic-first, short, action-oriented. Default merchant copy avoids: WABA, Cloud API, Token, Webhook, System User.

## Tests

`tests/test_merchant_whatsapp_onboarding_journeys_v1.py` — selector, guidance, persistence, readiness CTA, admin row, banned terms, JS wiring.

## Regression safety

WhatsApp Mode, Readiness Engine, CTA behavior, Template Registry, recovery/VIP/widget/lifecycle unchanged.
