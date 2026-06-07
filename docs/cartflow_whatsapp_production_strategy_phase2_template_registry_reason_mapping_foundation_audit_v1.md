# CartFlow WhatsApp Production Strategy Phase 2 — Template Registry & Reason Mapping Foundation

**Date (UTC):** 2026-06-07  
**Phase:** Architecture + merchant/admin UX only  
**Commit message:** `whatsapp production strategy phase 2 template registry reason mapping foundation`  
**Status:** Implemented (configuration layer — no Meta/send/runtime changes)

**Builds on:** Phase 1 WhatsApp mode architecture, template library foundation audit

**Explicitly not implemented:** Meta Cloud API, template creation/approval, send path changes, recovery engine changes, entitlement enforcement

---

## Executive summary

Phase 2 establishes the **permanent template strategy foundation** before Meta integration:

| Layer | Service | Role |
|-------|---------|------|
| **Template Registry** | `merchant_whatsapp_template_registry_v1.py` | Canonical 11 keys with `default_content`, Meta-ready fields |
| **Reason Mapping** | `merchant_whatsapp_reason_mapping_v1.py` | Single `reason_tag → template_key` map |
| **Merchant Layer** | `merchant_whatsapp_template_layer_v1.py` | Edit wording, enable/disable, restore default |
| **Admin Visibility** | `admin_whatsapp_template_visibility_v1.py` | Registry + per-store customization ops view |

**Regression safety:** `whatsapp_send.py`, `recovery_message_templates.py`, recovery execution, widget, VIP, timeline, delivery truth — **unchanged**.

---

## Part A — Template Registry (canonical)

| template_key | display_name_ar | reason_tag | template_type |
|--------------|-----------------|------------|---------------|
| `PRICE_TEMPLATE` | السعر | price | reason_recovery |
| `SHIPPING_TEMPLATE` | الشحن | shipping | reason_recovery |
| `QUALITY_TEMPLATE` | الجودة | quality | reason_recovery |
| `DELIVERY_TEMPLATE` | التوصيل | delivery | reason_recovery |
| `WARRANTY_TEMPLATE` | الضمان | warranty | reason_recovery |
| `OTHER_TEMPLATE` | سبب آخر | other | reason_recovery |
| `UNKNOWN_REASON_TEMPLATE` | سبب غير معروف | unknown | fallback |
| `FOLLOWUP_1_TEMPLATE` | متابعة 1 | — | followup |
| `FOLLOWUP_2_TEMPLATE` | متابعة 2 | — | followup |
| `FOLLOWUP_3_TEMPLATE` | متابعة 3 | — | followup |
| `VIP_ALERT_TEMPLATE` | تنبيه VIP | — | vip_alert |

Each entry includes: `enabled`, `default_content`, `future_meta_template_name`, `future_meta_status` (`draft` / `approved` / `rejected` / `disabled` — architecture only).

---

## Part B — Reason mapping (locked)

```
price     → PRICE_TEMPLATE
shipping  → SHIPPING_TEMPLATE
quality   → QUALITY_TEMPLATE
delivery  → DELIVERY_TEMPLATE
warranty  → WARRANTY_TEMPLATE
other     → OTHER_TEMPLATE
unknown   → UNKNOWN_REASON_TEMPLATE
```

Widget aliases (`price_high`, `thinking`, …) normalize via `normalize_reason_tag()` before lookup.

Merchants **cannot** alter mappings or create new template types.

---

## Part C — Merchant customization

**Storage:** `stores.whatsapp_template_overrides_json` — `{ TEMPLATE_KEY: { enabled, custom_content } }`

**Merchant can (6 reason templates):**

- Edit wording (`custom_content`)
- Enable / disable
- Restore default (`whatsapp_template_restore_defaults`)

**Merchant cannot:**

- Create arbitrary template types
- Change `template_key` or reason mapping
- Edit system templates (followups, VIP, unknown)

**UI:** `#whatsapp` — «قوالب رسائل الاسترجاع» card; `merchant_whatsapp_template_registry.js`

**API:** merged into `GET`/`POST /api/recovery-settings` via `whatsapp_template_fields_for_api()`

---

## Part D — Plan alignment (architecture only)

| Plan | Template capability (documented, not enforced) |
|------|-----------------------------------------------|
| Starter | Default templates only |
| Growth | Per-reason wording + enable/disable |
| Pro | Advanced template library (future) |

---

## Part E — Admin visibility

**Page:** `/admin/whatsapp` (extended)

| API | Purpose |
|-----|---------|
| `GET /api/admin/whatsapp/templates` | Canonical registry rows |
| `GET /api/admin/whatsapp/store-templates` | Per-store enabled + default/customized |

Columns: `template_key`, `reason_tag`, `enabled`, `default/customized`, `future_meta_status`

---

## Part F — Future Meta readiness

Registry entries carry `future_meta_template_name` + `future_meta_status`. No Meta calls, no approval workflow, no provider dependency.

Next phases wire runtime send path to registry + approved Meta template IDs.

---

## Part G — Tests

`tests/test_merchant_whatsapp_template_registry_v1.py` — registry keys, reason mapping, merchant overrides, admin rows, dashboard UX markers.
