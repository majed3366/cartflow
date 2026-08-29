# Settings Product Composition V1

**Status:** AUTHORIZED PRODUCT COMPOSITION  
**Date:** 2026-08-29 (UTC)  
**Predecessor:** `docs/product/settings_ownership_correction_v1/REPORT.md` (`READY_FOR_PRODUCT_COMPOSITION: YES`)  
**Forbidden in this task:** new product features, new Settings categories, API redesign, Scheduler / Postgres / Railway changes, Admin redesign, Home / Workspace / Carts / Communication / Merchant Shell edits

---

## Canonical question (governs the surface)

**ما الذي أحتاج ضبطه لكي يعمل CartFlow بشكل صحيح وآمن؟**

One restrained orientation line under it. No marketing hero. No diagnostics center.

---

## Composition model

V2 `#settings` is a configuration workspace, not a V1 visual copy and not a long form dump.

**Desktop:** overview list + detail panel (master/detail).  
**Mobile:** overview → tap area → focused detail → back. Side-by-side is not compressed onto small viewports.

Existing form IDs and existing `maInit*` writers stay. Composition only hosts, classifies, and discloses.

Marker: `settings-product-composition-v1` (`static/merchant_ui_v2_settings.js`).  
Host: `templates/partials/merchant_settings_canonical_v1.html` inside `#cf2-settings-root`.

---

## Configuration areas (existing truth only)

| Area | Hosted truth | Status source |
|------|----------------|---------------|
| Store | Zid connection + subscription READ_ONLY | `GET /api/merchant/store-connection` |
| Communication | WhatsApp config + notification prefs + templates entry | `GET /api/recovery-settings` |
| Recovery | delay / unit / attempts | same recovery-settings payload |
| Merchant policies | VIP threshold / enable | `GET /api/recovery-settings?scope=vip` |
| Experience | widget name / enabled | `GET /api/recovery-settings?scope=general` |

Statuses used: **READY / NEEDS_SETUP / PARTIAL / READ_ONLY / UNAVAILABLE**.  
No numeric readiness scores. No fake health metrics.

---

## Store

- Zid: REAL — connect / reconnect / disconnect remain the existing store-connection actions (confirm on reconnect/disconnect).
- Subscription: READ_ONLY card. No billing, checkout, upgrade, or invoices.
- Salla: STUB — not rendered as a connect control. Copy: unavailable.
- Shopify: NOT_AUTHORIZED — no settings surface. Mentioned only as unavailable.

---

## Communication

Settings owns configuration. «ضبط التواصل» from Communication still lands on `#settings` (overview; `#whatsapp` / `#whatsapp-connect` open the communication panel).

Hosted: WhatsApp number, recovery enable, connect host, readiness, notification checkboxes.

Not hosted: inbox, send log, follow-up queue, Communication history facts.

Templates: V1 truth, not yet a V2 engine host. Controlled handoff: `/dashboard?cf_ui=v1#trigger-templates`.

---

## Recovery policy

Merchant-owned delay / attempts only. Existing `#ma-recovery-policy-form` + confirm on save.

Not exposed: scheduler, due queue, retry workers, incident controls.

Write path unchanged: `POST /api/recovery-settings` via `merchant_settings_write_boundary_v1`.  
**RECOVERY SETTINGS WRITE BOUNDARY = PARTIAL** — no new writers.

---

## VIP policy

Threshold + enable (+ existing advanced notify/note). Operational VIP cart lists stay on Carts (`#vip`).

---

## Widget / experience

Existing display preferences only (`cartflow_widget_enabled`, `widget_name`). Not a theme builder.

---

## Mutation safety

**MUTATION SAFETY CONTRACT = PARTIAL** — preserved.

| Action | Class |
|--------|--------|
| Notification / widget prefs save | SAFE_REVERSIBLE (existing general writer) |
| WhatsApp number / recovery enable | SAFE_WITH_CONFIRMATION (existing confirm) |
| Recovery delay / attempts | SAFE_WITH_CONFIRMATION (existing confirm) |
| VIP policy save | SAFE_WITH_CONFIRMATION (existing confirm) |
| Zid reconnect / disconnect | HIGH_IMPACT_CONFIRMATION_REQUIRED (existing confirm) |
| Unclear / admin / operational fields | not exposed |

No silent destructive actions. No new POST paths.

---

## Admin / merchant boundary

Provider mode, scheduler, incident recovery, platform diagnostics, and operator overrides stay off this surface.

---

## Protected surfaces

Home, Decision Workspace, Carts, Communication, Merchant Shell, Admin/Ops: not modified in this composition.

---

## Validation (local)

Composition tests: `tests/test_settings_product_composition_v1.py` (10).  
Ownership + store-section tests: 18 passed after updating the V2 dashboard assertion (Salla is unavailable copy, not a connect control).

Browser (`127.0.0.1:8771/dashboard?cf_ui=v2#settings`):

| Check | Result |
|-------|--------|
| Store connected | Demo: **NEEDS_SETUP** — «غير مربوط» |
| Store needs attention | Banner «يحتاج ضبط: المتجر» |
| Communication not ready / partial | **PARTIAL** — number empty, recovery enable on |
| Recovery policy visible | **READY** — delay/attempts form in recovery panel |
| VIP policy visible | **READY** — «متابعة VIP غير مفعّلة» |
| Widget prefs visible | **READY** — «اسم العرض: مساعد المتجر» |
| Templates entry | Handoff card in communication panel |
| Subscription READ_ONLY | «اشتراكك نشط» on store panel |
| Salla / Shopify | Unavailable copy; no Salla connect button |
| Desktop 1440 | Overview 272px + detail 1072px; back hidden |
| Mobile 394 | Overview only → tap store → detail + back; overview hidden |
| «ضبط التواصل» | Lands `#settings` overview |
| Home question | Unchanged: ماذا يجب أن أعرف الآن عن متجري؟ |

Communication / Carts / Workspace / Home / Admin / Scheduler were not edited.

---

CANONICAL QUESTION:
ما الذي أحتاج ضبطه لكي يعمل CartFlow بشكل صحيح وآمن؟

COMPOSITION MODEL:
OVERVIEW → AREA → DETAIL (desktop master/detail; mobile list → detail → back)

STORE CONFIG:
HOSTED — Zid REAL; subscription READ_ONLY in the same area

COMMUNICATION CONFIG:
HOSTED — WhatsApp + notifications; «ضبط التواصل» → `#settings`

RECOVERY POLICY:
HOSTED — delay / attempts only; existing writer; no scheduler

VIP POLICY:
HOSTED — threshold / enable; operational VIP lists remain Carts

WIDGET PREFS:
HOSTED — existing display name / enabled only

TEMPLATES:
V1 HANDOFF — `/dashboard?cf_ui=v1#trigger-templates` (engine not rewritten)

SUBSCRIPTION:
READ_ONLY — current plan card; no billing actions

UNSUPPORTED INTEGRATIONS:
Salla UNAVAILABLE (no connect control); Shopify NOT_AUTHORIZED (no surface)

MUTATION SAFETY:
PRESERVED

ADMIN/MERCHANT BOUNDARY:
PRESERVED

MOBILE COMPOSITION:
PASS

DESKTOP COMPOSITION:
PASS

OPERATIONAL REGRESSION:
NO

READY_FOR_VISUAL_REVIEW:
YES

STOP.
