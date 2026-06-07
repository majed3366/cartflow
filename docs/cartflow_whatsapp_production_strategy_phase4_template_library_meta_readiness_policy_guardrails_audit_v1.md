# CartFlow WhatsApp Production Strategy Phase 4 — Template Library, Meta Readiness & Policy Guardrails

**Date (UTC):** 2026-06-07  
**Phase:** Library + guardrails architecture (no Meta/send migration)  
**Commit message:** `whatsapp production strategy phase 4 template library meta readiness policy guardrails`  
**Status:** Implemented (policy + dashboard guardrails — runtime send unchanged)

**Builds on:** Phases 1–3 (mode, registry, execution policy), UX cleanup (transport vs content)

---

## Executive summary

Phase 4 completes the **pre-Meta foundation**:

| Layer | Module | Role |
|-------|--------|------|
| Template Library | `merchant_whatsapp_template_library_v1.py` | Versioned templates, approval states, fallback chains |
| Meta policy awareness | `merchant_whatsapp_meta_policy_awareness_v1.py` | Calm merchant guidance (no Meta jargon) |
| Timing guardrails | `merchant_whatsapp_timing_guardrails_v1.py` | Stage 2/3 minimum delays + auto-adjust on save |
| Admin library visibility | `admin_whatsapp_template_library_visibility_v1.py` | Version/state/fallback ops schema |

---

## Part A — Template Library

Each logical template (`PRICE_TEMPLATE`) maps to versioned keys (`PRICE_TEMPLATE_V1`, optional `PRICE_TEMPLATE_V2` draft).

Fields per version: `template_key`, `template_version`, `reason_tag`, `default_content`, `enabled`, `active_version`, `fallback_template_key`, `created_at`, `updated_at`, `approval_state`.

Merchants see **active version only** via `resolve_merchant_visible_template()`.

---

## Part B — Approval states

`draft` · `pending_review` · `approved` · `rejected` · `disabled`

Validated transitions via `can_transition_approval_state()` / `transition_approval_state()` — **no Meta sync**.

---

## Part C — Fallback policy

Example chain:

```
PRICE_TEMPLATE → PRICE_TEMPLATE_V1 → UNKNOWN_REASON_TEMPLATE
```

`resolve_sendable_template_key()` walks chain skipping rejected/disabled versions.

---

## Part D — Versioning

- Admin inspects all versions (`GET /api/admin/whatsapp/template-library`)
- Merchant UI shows current active content only
- `PRICE_TEMPLATE_V2` exists as draft example — not active

---

## Part E — Meta policy awareness

Calm Arabic guidance on `#trigger-templates`:

- التواصل المتوازن يحقق نتائج أفضل.
- إرسال عدد كبير من الرسائل…
- يوصى باستخدام التوقيت المقترح من CartFlow.

---

## Part F — Safe timing guardrails

| Stage | Merchant config | Recommended | Hard minimum |
|-------|-----------------|-------------|--------------|
| 1 | Yes | Visible (per reason defaults) | None |
| 2 | Yes | 24 hours | 6 hours |
| 3 | Yes | 72 hours | 24 hours |

Applied on **`POST /api/dashboard/trigger-templates`** save only (dashboard policy layer).

---

## Part G — UI behavior

When timing clamped, save response includes:

> تم تعديل التوقيت تلقائياً للحفاظ على جودة التواصل مع العملاء.

No error-heavy UX.

---

## Part H — Managed sender protection

Extended in Phase 3 execution policy + Phase 4 library:

- daily store send guard
- repeated failure suppression
- provider unavailable suppression
- **template unavailable suppression** (fallback chain)
- no infinite retries

Architecture only — no runtime enforcement.

---

## Part I — Admin visibility

`GET /api/admin/whatsapp/template-library` — versions, states, fallback chains, sendable key map.

Future fields: `policy_adjustment_reason`, `timing_guardrail_events`.

---

## Regression safety

Recovery engine, `RecoverySchedule`, delay runtime in send path, VIP, widget, lifecycle, purchase truth — **unchanged**.

Dashboard GET trigger-templates enriched with policy metadata only.

---

## Tests

`tests/test_merchant_whatsapp_template_library_phase4_v1.py` + existing WhatsApp strategy tests.
