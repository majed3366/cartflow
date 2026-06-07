# VIP Merchant WhatsApp Alert Delivery Truth Audit v1

**Date (UTC):** 2026-06-06  
**Task:** VIP Merchant WhatsApp Alert Delivery (Operational Truth)

## Executive summary

VIP carts were detected and shown on the dashboard, but **merchants did not reliably receive WhatsApp VIP alerts**. Root-cause trace identified **four independent failures** on the auto-alert path (widget `cart_state_sync` with `reason=add`):

| # | Issue | Divergence point |
|---|--------|------------------|
| 1 | **24h template gate blocked merchant sends** | `send_whatsapp` → `enforce_whatsapp_template_window_before_send` treated merchant phone like customer recovery |
| 2 | **`lite_add` deferred alerts** | Background `_defer_vip_merchant_auto_alert_after_cart_state_sync` — silent/unreliable vs sync commit path |
| 3 | **`vip_notify_enabled` not wired** | Dashboard toggle saved but `_send_vip_merchant_auto_alert` ignored it |
| 4 | **No delivery persistence** | No `CartRecoveryLog` for auto merchant alerts; dashboard `merchant_vip_alert_state_ar` is count-only |

**Fix scope (VIP merchant alert path only):** sync auto alert after `cart_state_sync` commit; respect `merchant_vip_notify_enabled`; bypass 24h template gate for `vip_merchant_alert` / `vip_phone_capture_merchant`; persist `CartRecoveryLog` + `[VIP MERCHANT ALERT TRUTH]`; `GET /dev/vip-merchant-alert-operational-truth`.

**Not changed:** normal cart recovery, customer WhatsApp recovery, template runtime truth, delay engine, `RecoverySchedule`, widget flow, store identity, dashboard cart classification.

---

## VIP alert path (code map)

1. **VIP detection:** `POST /api/cart-event` (`cart_state_sync` / `cart_abandoned`) → `is_vip_cart()` / `_activate_vip_manual_cart_handling`
2. **Alert decision:** `_vip_merchant_auto_alert_if_newly_entering()` → `_send_vip_merchant_auto_alert()`
3. **Merchant phone:** `resolve_merchant_whatsapp_phone()` — `Store.store_whatsapp_number` then `whatsapp_support_url`
4. **Send:** `try_send_vip_merchant_whatsapp_alert()` → `send_whatsapp()` (Twilio), `reason_tag=vip_merchant_alert`
5. **Logging:** `emit_vip_merchant_alert_truth_log()` + `CartRecoveryLog` (`reason_tag=vip_merchant_alert`, `source=auto_vip_cart`)
6. **Dashboard:** VIP row from `_vip_priority_cart_alert_list`; alert badge is **not** delivery truth

---

## Answers to audit questions

1. **Is the alert never created?** — Decision ran but could skip (notify off, no phone) without durable log before fix.
2. **Is the alert created but never scheduled?** — N/A; auto path is **sync send**, not `RecoverySchedule`.
3. **Is the alert scheduled but never executed?** — **`lite_add`** used background defer; often never executed reliably.
4. **Is the alert executed but sent to the wrong number?** — Phone source is correct when `store_whatsapp_number` saved; failure was gate/skip not wrong routing.
5. **Is the alert executed but blocked by a gate?** — **Yes:** `template_required_outside_24h` on merchant phone before fix.
6. **Is the alert sent but not persisted?** — **Yes:** no `CartRecoveryLog` on auto path before fix.
7. **Is the dashboard showing a false alert state?** — Badge reflects active VIP count, not WhatsApp delivery status.

---

## Tests

`tests/test_vip_merchant_alert_delivery_truth_v1.py`:

- `cart_state_sync` + `reason=add` triggers sync merchant alert + `CartRecoveryLog`
- `vip_notify_enabled=false` skips send + persists skip log
- `vip_merchant_alert` reason bypasses 24h template gate in `send_whatsapp`

---

## Production verification

Script: `scripts/_vip_merchant_alert_truth_audit.py`  
Artifacts: `scripts/_vip_merchant_alert_truth_audit_out/`

Flow:

1. Sign up / log in fresh merchant on **smartreplyai.net**
2. Save VIP threshold 500 + notify enabled (`#vip`)
3. Save merchant WhatsApp number (`#whatsapp`)
4. `POST /api/cart-event` — `cart_state_sync`, `reason=add`, `cart_total=1299`
5. Poll `GET /dev/vip-merchant-alert-operational-truth?cart_id=&store_slug=`
6. Screenshot VIP dashboard row (`03_vip_dashboard_row.png`)

Evidence fields captured in `vip_merchant_alert_truth_audit.json`:

- `cart_id`, `store_slug`, `session_id`
- `settings.vip` / `settings.wa` (threshold, notify, merchant phone)
- `dev_vip_merchant_alert_operational_truth` (merchant phone, alert log rows, `latest_alert_status`)
- `vip_carts_api` (row count, `merchant_vip_alert_state_ar`)

**Merchant phone receipt:** confirm WhatsApp message on configured `CARTFLOW_VIP_ALERT_MERCHANT_PHONE` (default `966579706669`) — operational proof requires human/device confirmation alongside JSON + Twilio `provider_message_sid` in log row.

---

## Fix files

- `main.py` — `_send_vip_merchant_auto_alert`, sync hook after `cart_state_sync`, dev operational-truth endpoint
- `services/vip_merchant_alert.py` — truth logs, reason tags, `wa_trace_store_slug` on send
- `services/whatsapp_send.py` — `_MERCHANT_ONLY_WA_REASON_TAGS` skips 24h template enforcement

Commit: **`fix vip merchant whatsapp alert delivery truth`**
