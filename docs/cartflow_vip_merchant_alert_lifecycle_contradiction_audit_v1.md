# VIP Merchant Alert Delivery + Lifecycle Contradiction Audit v1

**Date (UTC):** 2026-06-07  
**Environment:** https://smartreplyai.net (production only)  
**Script:** `scripts/_vip_merchant_alert_lifecycle_contradiction_audit.py`  
**Artifacts:** `scripts/_vip_merchant_alert_lifecycle_audit_out/`

## Executive summary

A fresh production VIP cart (1299 SAR) reproduces **both** reported issues:

1. **Merchant WhatsApp alert:** Backend records `sent_real` + Twilio SID, but that proves **Twilio API acceptance only** — not confirmed delivery to the merchant device. `CartRecoveryLog.sent_at` remains null; no delivery callback evidence in DB.

2. **Lifecycle UI contradiction:** The same cart appears in **`GET /api/dashboard/normal-carts`** (not VIP-only) with four conflicting lines on one card — reproduced with operational JSON evidence. Root cause class: **D) multiple state layers merged incorrectly** (VIP lane lifecycle + customer-recovery follow-up clarity + normal-carts augment leak).

---

## Part 1 — VIP merchant alert path (operational evidence)

### Fresh production cart (2026-06-07)

| Field | Value |
|-------|-------|
| **cart_id** | `cf_cart_7516b3232f99` |
| **store_slug** | `viplc-2e18f0-92abf7` |
| **session_id** | `s_vip_lc_7516b3232f99` |
| **recovery_key** | `viplc-2e18f0-92abf7:cf_cart_7516b3232f99` |
| **cart_value** | 1299 |
| **vip_threshold** | 500 |
| **vip_notify_enabled** | `true` |
| **VIP decision** | `cart_state_sync` → `is_vip=true` → `_vip_merchant_auto_alert_if_newly_entering` |
| **merchant phone resolved** | `966579706669` (`store_whatsapp_number`) |
| **Twilio `to` (normalized)** | `whatsapp:+966579706669` (`services/whatsapp_send._normalize_twilio_whatsapp_to`) |
| **WhatsApp provider** | Twilio |
| **send attempt** | `try_send_vip_merchant_whatsapp_alert` → `send_whatsapp(reason_tag=vip_merchant_alert)` |
| **Twilio SID** | `SM5de0308d9fac6f1d963c704db27c8fb5` |
| **CartRecoveryLog id** | 1057 |
| **Log status** | `sent_real` |
| **Log phone** | `966579706669` |
| **message_preview** | `تنبيه VIP 🚨` — سلة عالية القيمة: 1299 ريال |
| **sent_at** | `null` |
| **VIP dashboard row** | Present (`merchant_vip_page_rows`, id=4153) |

### Decision → Send → Phone → Provider → SID → Final status

```
VIP detected (cart_state_sync, cart_total=1299 >= threshold=500)
  → vip_notify_enabled=true
  → resolve_merchant_whatsapp_phone → 966579706669
  → send_whatsapp → Twilio messages.create
  → SID SM5de0308d9fac6f1d963c704db27c8fb5
  → resolve_whatsapp_recovery_log_status → sent_real
  → CartRecoveryLog persisted (reason_tag=vip_merchant_alert)
```

### Where exactly did the VIP merchant alert go?

**Operational answer (no assumptions beyond DB + dev endpoint):**

| Step | Evidence |
|------|----------|
| **Decision** | Alert not skipped; `latest_alert_status=sent_real` |
| **Send attempt** | Yes — log row 1057 with `provider_message_sid` |
| **Phone** | `966579706669` on log row; Twilio target `whatsapp:+966579706669` |
| **Provider** | Twilio (non-empty SID) |
| **SID** | `SM5de0308d9fac6f1d963c704db27c8fb5` |
| **Final status in DB** | `sent_real` |

**What `sent_real` means in code:** `resolve_whatsapp_recovery_log_status` returns `sent_real` when `wa_result.ok` and Twilio returns a **SID** — i.e. provider **accepted** the outbound request. It does **not** mean the merchant phone displayed the WhatsApp message.

**What is NOT in evidence:**

- No `sent_at` timestamp on the alert log row
- No persisted Twilio delivery status (`delivered` / `failed`) for this merchant alert in the audited payload
- No device-level receipt proof

**Prior audit cart (`cf_cart_2c731a63905b`)** showed the same pattern: `sent_real` + SID `SMc2cc34be8379f5ef30993344a729e96f` — closure report treated SID as delivery proof; this re-audit separates **provider acceptance** from **merchant device receipt**.

---

## Part 2 — Lifecycle contradiction (operational evidence)

### Reproduced UI strings on one card (`GET /api/dashboard/normal-carts`)

Same cart `cf_cart_7516b3232f99` — JSON row from production:

| UI line (Arabic) | API field | Value |
|------------------|-----------|-------|
| تحتاج تدخل | `customer_lifecycle_label_ar` | `تحتاج تدخل` |
| تحتاج تدخل | `merchant_status_label_ar` | `تحتاج تدخل` |
| تم إرسال ١ من ١ | `merchant_followup_progress_ar` | `تم إرسال ١ من ١` |
| اكتملت سلسلة المتابعة — بانتظار تفاعل العميل | `merchant_followup_sequence_line_ar` | `اكتملت سلسلة المتابعة — بانتظار تفاعل العميل` |
| بانتظار تفاعل العميل | `merchant_business_state_ar` | `بانتظار تفاعل العميل` |
| بانتظار تفاعل العميل | `merchant_next_action_ar` | `تم إرسال الرسالة — ننتظر تفاعل العميل.` |

Additional lifecycle fields:

- `customer_lifecycle_state`: `needs_intervention`
- `merchant_followup_sent_count`: **1**
- `merchant_followup_configured_count`: **1** (from `Store.recovery_attempts=1`)
- `merchant_coarse_status`: `sent` (phase key treats sent log present)

### Source-of-truth state

| Layer | Source | State for this cart |
|-------|--------|---------------------|
| **Operational lane** | `is_vip_cart(1299, threshold=500)` | VIP |
| **Customer lifecycle (authoritative for badge)** | `classify_customer_lifecycle_state_v1(is_vip_lane=true)` | `needs_intervention` |
| **Sent count (dashboard)** | `_cart_recovery_sent_real_count_for_abandoned` | **1** (counts `vip_merchant_alert` `sent_real`) |
| **Follow-up clarity (display)** | `attach_merchant_followup_clarity(sent_count=1, cap=1)` | progress + sequence-complete copy |
| **VIP tab** | `_vip_priority_cart_alert_list` | Row present; label `بانتظار التواصل` only |

### Timeline / log events

| Event | Log / record |
|-------|----------------|
| Cart created VIP | `cart_state_sync` → `AbandonedCart` id=4153, `vip_mode=true` |
| Reason saved | `POST /api/cartflow/reason` (price + phone) |
| Merchant alert | `CartRecoveryLog` id=1057, `reason_tag=vip_merchant_alert`, `status=sent_real`, SID above |
| Customer recovery send | **None** — `recovery_schedule_row_count=0`, `schedule_rows=[]` |
| Customer WhatsApp | **None** to customer phone |

`dev/recovery-operational-truth` for this recovery_key:

- `sent_count`: 1
- `cart_recovery_log_sent_count`: 1
- `configured_count`: 1
- `decision`: `stop_sequence`
- `dashboard_bucket`: `attention`

### Classification decision path

1. **`_needs_intervention(..., is_vip_lane=True)`** always returns true (`services/customer_lifecycle_states_v1.py` L602–603) → **`needs_intervention` / «تحتاج تدخل»**.

2. **`_cart_recovery_sent_real_count_for_abandoned`** counts **all** `CartRecoveryLog` rows with `status in (sent_real, mock_sent)` for session/cart — **includes `vip_merchant_alert`** (no `reason_tag` exclusion) → `sent_count=1`.

3. **`attach_merchant_followup_clarity`** with `sent_count=1`, `configured_count=1` (`recovery_attempts`) → **`تم إرسال ١ من ١`** and **`اكتملت سلسلة المتابعة — بانتظار تفاعل العميل`** (`services/merchant_followup_clarity_v1.py` L100–115).

4. **UI render** merges both blocks in `customerLifecycleExplanationHtml` + `merchantFollowupClarityHtml` (`static/merchant_dashboard_lazy.js`).

### Why VIP cart is on normal-carts at all

Primary SQL filter excludes `cart_value >= vip_threshold`, but **`_augment_abandoned_candidates_with_active_recovery_signals`** calls **`_ensure_abandoned_cart_for_active_recovery_signal`** after `POST /api/cartflow/reason` — appends the VIP row **without re-applying the VIP threshold filter** (`main.py` L17798–17814). Cart then flows through normal-carts lifecycle enrichment.

### Verdict: A / B / C / D?

| Option | Verdict |
|--------|---------|
| A) UI wrong alone | **Partial** — UI faithfully renders conflicting backend fields |
| B) Lifecycle classification wrong | **Partial** — `needs_intervention` for VIP is intentional, but applied on normal-carts row |
| C) Timeline wrong | **No** — timeline/logs consistent; no customer send occurred |
| **D) Multiple states merged incorrectly** | **Yes — primary root cause** |

**D breakdown:**

1. VIP merchant alert log counted as **customer recovery send** (`sent_count`).
2. Customer-recovery **follow-up clarity** copy applied to VIP merchant-only alert.
3. VIP lifecycle **`needs_intervention`** combined with **sequence-complete** customer copy on same card.
4. VIP cart **leaked** into normal-carts list via active-signal augment path.

---

## Screenshots

- `scripts/_vip_merchant_alert_lifecycle_audit_out/01_vip_dashboard.png`
- `scripts/_vip_merchant_alert_lifecycle_audit_out/02_normal_carts_intervention.png`

---

## Acceptance checklist

| Requirement | Status |
|-------------|--------|
| Fresh VIP cart on production | ✅ `cf_cart_7516b3232f99` |
| Alert path traced with evidence | ✅ dev endpoint + CartRecoveryLog |
| Lifecycle contradiction explained with evidence | ✅ normal-carts JSON row |
| No TestClient proof | ✅ Playwright + production APIs only |
| No local proof | ✅ smartreplyai.net only |

**Open operational gap:** Merchant device WhatsApp receipt is **not proven** by `sent_real` + SID alone; delivery truth requires Twilio status callback / `sent_at` / human device confirmation.

---

## Recommended fix direction (out of scope for this audit commit)

1. Exclude `reason_tag in (vip_merchant_alert, vip_phone_capture_merchant)` from `_cart_recovery_sent_real_count_for_abandoned`.
2. Skip `attach_merchant_followup_clarity` when `is_vip_lane` (or on VIP-only rows).
3. Block VIP-threshold carts from `_ensure_abandoned_cart_for_active_recovery_signal` augment path.
4. Persist Twilio delivery status / `sent_at` for merchant alerts; surface delivery truth separately from `sent_real`.

Commit: **`audit vip merchant alert delivery and lifecycle contradiction`**
