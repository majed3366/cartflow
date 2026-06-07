# VIP Operational Truth Closure v1

**Date:** 2026-06-07 UTC  
**Commit:** `fix vip operational truth closure`

## Executive summary

Production re-audit proved VIP merchant alerts reached Twilio (SID + `sent_real`) but **did not prove merchant device delivery**, and the same alert **contaminated customer recovery lifecycle** on `normal-carts` cards.

This closure fixes the full operational chain in one pass:

| Issue | Root cause | Fix |
|-------|------------|-----|
| Merchant alert counted as customer send | `_cart_recovery_sent_real_count_for_abandoned` + batch `sent_real_count` counted all `sent_real` logs | Exclude `reason_tag ∈ {vip_merchant_alert, vip_phone_capture_merchant}` |
| «تم إرسال X من Y» on VIP rows | `attach_merchant_followup_clarity` applied on `is_vip_lane` rows | Skip follow-up clarity when `vip_lane=true` |
| VIP carts in normal-carts | `_ensure_abandoned_cart_for_active_recovery_signal` augment leak | Block VIP-lane carts in ensure + augment + normal-carts payload loop |
| `sent_real` treated as delivery | Provider acceptance ≠ device delivery | VIP logs use `vip_merchant_alert_*` statuses; post-send Twilio poll + `WhatsAppDeliveryTruth` |
| Destination ambiguity | Only store fields resolved | `resolve_vip_alert_destination`: store WhatsApp → support URL → `CARTFLOW_VIP_ALERT_DESTINATION` |

## Part B — Alert delivery path

```
VIP cart detected (cart_state_sync)
  → resolve_vip_alert_destination(store)
  → merchant_vip_notify_enabled check
  → try_send_vip_merchant_whatsapp_alert (send_whatsapp, merchant-only gate bypass)
  → poll_twilio_vip_alert_delivery_truth (up to 30s)
  → CartRecoveryLog status: vip_merchant_alert_accepted | vip_merchant_alert_delivered | vip_merchant_alert_failed
  → GET /dev/vip-merchant-alert-operational-truth (delivery_truth + normalized phone)
```

**Acceptance:** `delivered_to_device=true` on dev endpoint **and** merchant/support WhatsApp screenshot on configured destination.

## Part C — Lane isolation proof

- `services/vip_operational_truth_v1.py` — single source for merchant-only log exclusion
- `sent_logs_for_store` — merchant alert logs no longer trigger normal-carts augment
- `_last_provider_sent_at_utc` — excludes merchant-only logs from customer engagement window

## Part D — Lifecycle contradiction

Root cause **D (projection merge)** — not classifier alone. VIP lane still shows `needs_intervention` (correct for merchant action) but no longer shows customer follow-up sequence copy.

## Verification

- Unit tests: `tests/test_vip_operational_truth_closure_v1.py` (6 tests)
- Production script: `scripts/_vip_operational_truth_closure_audit.py`
- Manual: save merchant WhatsApp screenshot to `scripts/_vip_operational_truth_closure_out/merchant_whatsapp_alert_screenshot.png`

## Regression safety

No changes to Purchase Truth, Template Runtime, RecoverySchedule, Delay Engine, customer WhatsApp recovery send path, widget flow, dashboard DOM stability, store identity, or product intelligence.
