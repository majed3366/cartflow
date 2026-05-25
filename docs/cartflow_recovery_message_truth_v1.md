# Recovery Message Context & Truth Layer v1

## Problem

Recovery WhatsApp messages could appear on the **Messages** page while the **Carts** page showed a different lifecycle state. Logs often lacked a durable link to `cart_id`, `session_id`, and `recovery_key`, and message text could be generic even when cart/reason context existed.

## Canonical object

`services/recovery_message_context_v1.py` defines **`RecoveryMessageContext`** — built before persist and stored on `CartRecoveryLog`:

| Field | Purpose |
|--------|---------|
| `recovery_key` | Stable session/cart key (`store:session` or `store:session:cart`) |
| `store_slug`, `cart_id`, `session_id` | Cart linkage |
| `customer_phone`, `cart_value`, `items_count`, `product_names` | Merchant-safe cart snapshot |
| `reason_tag`, `message_body`, `message_type` | Dynamic copy source |
| `attempt`, `source` | Step + pipeline (`recovery_sequence`, `whatsapp_queue`) |
| `provider`, `provider_message_sid`, `send_status`, `sent_at` | Send truth (no provider logic change) |
| `context_status` | `ok` \| `context_missing` \| `legacy_context_missing` |

Persisted columns on **`cart_recovery_logs`** (optional DDL via `schema_recovery_message_context.py`):  
`recovery_key`, `reason_tag`, `context_status`, `context_json`, `message_type`, `source`, `provider`, `provider_message_sid`.

## Message body rules

1. Explicit body from recovery run (after templates / multi-slot) — `message_type=explicit`
2. Reason templates when `reason_tag` + store allow — `reason_template`
3. Safe generic fallback only when templates unavailable — `generic_fallback` (never pretend cart-specific data exists)

## Lifecycle agreement

- **`derive_messages_page_status`** — from log status + `context_status`
- **`derive_carts_page_status`** — from phase/coarse + `sent_ct` + log
- **`detect_truth_mismatch`** — surfaces `messages_sent_carts_not_sent`, `message_missing_cart_context`, etc.
- **`enrich_cart_row_truth_fields`** — attached to normal cart rows via `merchant_recovery_lifecycle_truth` (API data only; no widget change)

When `CartRecoveryLog.status` is `sent_real` or `mock_sent` and logs match the cart (`session_id` / `cart_id` / `recovery_key`), carts derive **`first_message_sent`** → coarse **`sent`** → merchant label **تم الإرسال**.

## Diagnostics

`GET /api/dashboard/recovery-message-truth-debug?recovery_key=...`

Returns: `cart`, `recovery_schedule`, `cart_recovery_logs`, `message_context`, `derived_cart_status`, `messages_page_status`, `carts_page_status`, `mismatch_detected`, `mismatch_reason`.

## Legacy rows

Old logs without `context_json` are **not deleted**. They are labeled `legacy_context_missing` and may show `admin_context_warning_ar` on message history for support (merchant-safe copy).

## Out of scope (v1)

- WhatsApp provider transport / Twilio API changes
- Queue timing / retry policy
- Dashboard widget markup (truth-first; UI consumes API fields)

## Tests

`tests/test_recovery_message_context_v1.py` — context classification, persist round-trip, messages/carts agreement, missing context, debug payload, generic fallback.
