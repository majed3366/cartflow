# CartFlow WhatsApp Production Strategy Phase 1 — WhatsApp Mode Architecture & Merchant Experience

**Date (UTC):** 2026-06-07  
**Phase:** Architecture + merchant/admin UX only  
**Commit message:** `whatsapp production strategy phase 1 whatsapp mode architecture`  
**Status:** Implemented (configuration layer — no Meta/send changes)

**Builds on:** WhatsApp production reality audits (Phase 1 / 1.5 / 2.0), template library foundation

**Explicitly not implemented:** Meta onboarding, Embedded Signup, Cloud API send, webhooks, WABA connection, token management, provider migration, delivery truth changes

---

## Executive summary

CartFlow merchants fall into three categories: no WhatsApp knowledge, WhatsApp Business app users, and advanced WABA-ready merchants. Phase 1 introduces a **Simple First / Advanced Later** configuration model:

| Mode | Key | Merchant sees |
|------|-----|---------------|
| **A — CartFlow Managed** | `cartflow_managed` | Default — CartFlow handles customer messaging; merchant configures recovery only |
| **B — Merchant WhatsApp** | `merchant_whatsapp` | Advanced — customer messages from merchant-owned infrastructure |
| **C — Future** | `future_provider` | Architecture only — not selectable |

**Principle:** Hide complexity (WABA, Cloud API, Meta Business Manager, tokens, webhooks) from the default merchant path.

---

## Part A — Settings source of truth

| Field | Location | Default |
|-------|----------|---------|
| `whatsapp_mode` | `stores.whatsapp_mode` | `cartflow_managed` |
| `whatsapp_recovery_enabled` | existing | `true` |
| `whatsapp_provider_mode` | existing (advanced/ops) | inferred sandbox/test/production |

**Service:** `services/merchant_whatsapp_mode_v1.py`  
**Schema:** idempotent DDL via `ensure_whatsapp_mode_schema()`  
**API:** merged into `GET/POST /api/recovery-settings` via `merchant_whatsapp_settings_fields_for_api()`

---

## Part B — Merchant experience (`#whatsapp`)

**Default card — «رسائل العملاء عبر واتساب»**

| Element | Behavior |
|---------|----------|
| Connection status pill | `غير متصل` / `قيد الإعداد` / `متصل` |
| Primary CTA | «تفعيل استرجاع واتساب» when not connected |
| Description | Mode-specific Arabic copy (no Meta terminology) |

**Advanced Options** (collapsed `<details>`)

- WhatsApp Mode radio: CartFlow Managed (Recommended) / Merchant WhatsApp
- Store number (optional in managed mode)
- Recovery toggle
- Nested technical provider mode (sandbox/test/production) — ops/testing only

**UI:** `templates/merchant_app.html`, `static/merchant_whatsapp_settings.js`, `static/merchant_app.css`

---

## Part C — Admin visibility

**Page:** `/admin/whatsapp`  
**API:** `GET /api/admin/whatsapp/stores`

| Column | Source |
|--------|--------|
| Store | `merchant_store_display_name` |
| WhatsApp Mode | `whatsapp_mode_label_ar` |
| Connection Status | `whatsapp_customer_connection_status_ar` |
| VIP Destination | `resolve_vip_alert_destination()` (read-only) |
| Last Validation | last send status + timestamp from recovery logs |

**Service:** `services/admin_whatsapp_visibility_v1.py`

---

## Part D — Regression safety

| Area | Status |
|------|--------|
| `whatsapp_send.py` | Untouched |
| Recovery engine / widget / VIP send paths | Untouched |
| Templates / delivery truth | Untouched |
| Entitlements / billing | Untouched |

---

## Part E — Implementation map

| Artifact | Path |
|----------|------|
| Mode model | `services/merchant_whatsapp_mode_v1.py` |
| Settings merge | `services/merchant_whatsapp_settings.py` |
| Admin rows | `services/admin_whatsapp_visibility_v1.py` |
| Merchant UI | `#page-whatsapp` in `merchant_app.html` |
| Admin UI | `admin_whatsapp_visibility.html`, `admin_whatsapp_visibility.js` |
| Tests | `tests/test_merchant_whatsapp_mode_v1.py` |

---

## Part F — Future phases (not in scope)

| Phase | Deliverable |
|-------|-------------|
| 2 | Meta Cloud API adapter (send) behind mode A |
| 3 | Merchant WABA onboarding (mode B) |
| 4 | Webhook registration + delivery truth for Meta |

---

**End of audit.**
