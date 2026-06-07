# CartFlow WhatsApp Production Strategy Phase 5 — Merchant Connection Architecture & Production Readiness

**Date (UTC):** 2026-06-07  
**Phase:** Connection architecture + operational readiness (no Meta/send migration)  
**Commit message:** `whatsapp production strategy phase 5 merchant connection architecture and readiness`  
**Status:** Implemented (architecture + merchant/admin UX — runtime unchanged)

**Builds on:** Phases 1–4 (mode, registry, execution policy, library/guardrails)

---

## Executive summary

Phase 5 answers the merchant question: **«How do I become ready for production?»**

| Layer | Module | Role |
|-------|--------|------|
| Connection & readiness engine | `merchant_whatsapp_connection_readiness_v1.py` | Canonical connection states, readiness dimensions, production truth |
| Merchant readiness card | `merchant_whatsapp_readiness_ui.py` + partial + `#whatsapp` JS | Connection status, mode, required actions, expected outcome |
| Mode API enrichment | `merchant_whatsapp_mode_v1.py` | Exposes `whatsapp_connection_readiness` on `/api/recovery-settings` |
| Admin visibility | `admin_whatsapp_visibility_v1.py` + `/api/admin/whatsapp/connection-readiness` | Store mode, connection/readiness, missing requirements, notes |
| Meta placeholders | `meta_future_placeholders_for_api()` | Embedded Signup / WABA / verification — hidden until future phase |

**Not implemented:** Cloud API, Embedded Signup, WABA creation, tokens, provider migration, send/recovery/billing enforcement changes.

---

## Part A — Connection journeys

### Path A — CartFlow Managed

Merchant provides: business name, WhatsApp number, readiness information.  
Hidden: WABA, tokens, Cloud API, webhooks, Meta terminology.

### Path B — Merchant WhatsApp

Merchant sees: number, connection status, readiness requirements.  
Still avoids unnecessary Meta jargon.

Journey metadata: `connection_journey_for_mode()`.

---

## Part B — Connection states (canonical)

| Key | Arabic label |
|-----|----------------|
| `not_connected` | غير متصل |
| `setup_required` | يلزم إعداد |
| `pending_configuration` | قيد الإعداد |
| `connected` | متصل |
| `action_required` | يلزم إجراء |
| `paused` | متوقف مؤقتاً |
| `provider_issue` | يحتاج متابعة |

Derived from onboarding flags + recovery toggle — **not persisted** (no WABA columns).

Legacy pill CSS keys preserved via `connection_state_legacy_pill_key`.

---

## Part C — Readiness engine

Dimensions:

- **Widget Ready** (`widget_ready`)
- **WhatsApp Ready** (`whatsapp_ready`)
- **Store Connected** (`store_connected`)
- **Plan Eligible** (`plan_eligible`) — visibility only, no enforcement

Overall: `ready` | `not_ready`

Entry point: `evaluate_whatsapp_connection_readiness(store)`.

---

## Part D — Merchant setup experience

`setup_checklist` block (headline, ✓/✗ checklist, outcome) follows onboarding card style:

> متجرك قريب من التشغيل الكامل  
> المتبقي: ✓ ربط المتجر · ✗ ربط واتساب  
> النتيجة: سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء.

---

## Part E — WhatsApp readiness card

Server partial: `templates/partials/whatsapp_readiness_card.html`  
SPA `#whatsapp`: `ma-wa-readiness-root` rendered from API via `merchant_whatsapp_settings.js`.

Shows: connection status, current mode, required actions, expected outcome.

---

## Part F — Production truth

`production_truth` object on every evaluation:

- `why_not_connected_ar`
- `why_paused_ar`
- `action_required_ar`
- `after_completion_ar`

---

## Part G — Admin visibility

`AdminWhatsappStoreRow` extended with:

- `connection_state` / `readiness_state`
- `missing_requirements_ar`
- `operational_notes_ar`

`GET /api/admin/whatsapp/connection-readiness?store_id=` — per-store detail.

---

## Part H — Meta future placeholders

Architecture-only keys (hidden by default):

- `embedded_signup`
- `meta_verification`
- `waba_status`
- `phone_verification`

---

## Tests

`tests/test_merchant_whatsapp_connection_readiness_v1.py` — state evaluation, transitions, card fields, admin row.

Existing Phase 1–4 WhatsApp tests must continue passing.

---

## Regression safety

No changes to: recovery engine, WhatsApp runtime send, template system, execution policy, widget, lifecycle, purchase truth, dashboard cart logic, subscription enforcement.

---

## Addendum — Readiness UX V2 (action-first)

**Commit:** `whatsapp readiness ux v2 action first setup experience`

Turns the readiness card from a status display into an **action-oriented setup experience** — *truth + next action*. Engine, connection states, dimensions, production truth, and admin APIs are **unchanged**; this is presentation only.

- **Per-state mapping** `CONNECTION_STATE_ACTION_FIRST` (7 states → title / next action / single primary CTA / outcome) and pure builder `build_action_first_card(...)`.
- Surfaced as `action_first` on the merchant API (`connection_readiness_for_merchant_api`) and on the merchant card (`build_merchant_whatsapp_readiness_card`).
- **Visual priority** in partial + SPA: next action → remaining step → outcome → technical status (demoted, muted). **Single primary CTA** (`data-cf-wa-primary-cta`).
- Merchant-facing copy only (no Provider/API/WABA/Cloud API/Token/Webhook jargon).

State → title / primary CTA:

| State | Title | Primary CTA |
|-------|-------|-------------|
| `not_connected` | واتساب غير مرتبط | تفعيل واتساب |
| `setup_required` | يلزم إكمال الإعداد | استكمال الإعداد |
| `pending_configuration` | جاري إعداد الاتصال | إكمال التفعيل |
| `connected` | واتساب جاهز | فتح الإعدادات |
| `action_required` | يوجد إجراء مطلوب | مراجعة المتطلبات |
| `paused` | واتساب متوقف مؤقتاً | استئناف التشغيل |
| `provider_issue` | توجد مشكلة لدى مزود الخدمة | مراجعة الحالة |

Tests: `tests/test_merchant_whatsapp_readiness_ux_v2.py` (7-state rendering, single CTA, no-jargon copy, checklist mapping).
