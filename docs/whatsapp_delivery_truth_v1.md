# WhatsApp Delivery Truth v1

## Problem

Today, a successful Twilio `messages.create` often logs:

```text
[WA SENT] … status=queued
[WA STATUS] queued
```

That means **the provider accepted the API request**, not that the customer received the message.

Treating `queued` as “delivered” contaminates:

- Attribution confidence and ROI narratives
- Merchant trust (“we sent it” vs “they got it”)
- Operational truth during outages or template failures

## Principle

**Provider acceptance ≠ delivery.**

| Signal | Meaning |
|--------|---------|
| `queued` / API `ok` | Accepted by provider |
| `sent` | Handed to carrier/network (Twilio-dependent) |
| `delivered` | Delivered to customer device (provider callback) |
| `read` | Read by customer (future; provider-dependent) |
| `failed` / `undelivered` | Failed delivery |

## `DeliveryTruth` model

Lightweight record keyed by **`message_sid`** (unique per provider message).

| Field | Role |
|-------|------|
| `provider` | e.g. `twilio` (Meta future) |
| `message_sid` | Provider message id |
| `customer_phone`, `store_slug`, `session_id`, `cart_id`, `recovery_key` | Context (filled at send when trace fields exist) |
| `send_status`, `delivery_status`, `read_status` | Last known provider statuses |
| `provider_error` | Error code/message from callback |
| `last_event_time` | Last status event |
| `truth_level` | Normalized truth (below) |

Persisted in table `whatsapp_delivery_truth` (see `models.WhatsAppDeliveryTruth`).

## Truth levels

1. **`accepted_by_provider`** — e.g. `queued`, `accepted`
2. **`sent_to_network`** — e.g. `sent`, `sending`
3. **`delivered_to_customer`** — e.g. `delivered`
4. **`read_by_customer`** — e.g. `read` (future emphasis)
5. **`failed_delivery`** — `failed`, `undelivered`
6. **`unknown`** — no record and no callback

If **status callbacks are absent**, never assume delivered. After send we only persist **`accepted_by_provider`** (from API status). Without a row and without callback → **`unknown`**.

## Logs

| Log | When |
|-----|------|
| `[WA DELIVERY EVENT]` | Raw provider status ingested (`provider`, `sid`, `delivery_status`, …) |
| `[WA DELIVERY TRUTH]` | Normalized `truth_level` + `reason` after persist |

Existing `[WA SENT]` / `[WA STATUS]` are unchanged; they remain send-path observability.

## Webhook

**`POST /webhook/whatsapp/status`**

- Accepts Twilio form posts (`MessageSid`, `MessageStatus`, `ErrorCode`, …) or JSON (tests).
- Normalizes → `ingest_twilio_status_callback` → upsert by `message_sid` (idempotent).
- **Does not** run recovery, lifecycle, queue workers, or attribution.

Configure in Twilio Console (Messaging / WhatsApp sender):

- Status callback URL: `https://<your-host>/webhook/whatsapp/status`
- Method: POST

## Send path (additive)

After successful `messages.create`, `record_provider_acceptance_from_send` records **`accepted_by_provider`** from the initial API status. Return value and recovery scheduling are unchanged.

## Attribution / ROI (compatibility)

**v1 does not change Purchase Attribution decisions.**

- Attribution must **not** use `queued` or `CartRecoveryLog.status=sent_real` alone as proof of delivery.
- Future hook: `customer_delivered_for_attribution_future(message_sid)` — `True` only when `truth_level >= delivered_to_customer`.

## Operational foundation (later)

Same table and logs can feed:

- Queued spike (many accepted, few delivered)
- Failed / undelivered spike
- Delivery degradation by store
- Provider outage detection

No admin UI in v1; persistence and logs only.

## Risks

| Risk | Mitigation |
|------|------------|
| Callback URL not configured | Truth stays `accepted_by_provider` or `unknown` — never promoted to delivered |
| Duplicate callbacks | Upsert by `message_sid`; rank only advances forward (except terminal `failed`) |
| Missing context on callback | Send-time trace fills `store_slug` / `session_id` when present |
| Signature validation | Not required for v1; add Twilio request validation in a later hardening pass |

## Future: read receipts

When Twilio/Meta emit `read`, map to **`read_by_customer`**. Attribution may later increase confidence for read; v1 only stores and logs.

## Verification (production)

1. Trigger real recovery → observe `[WA SENT]` with `status=queued`.
2. Ensure Twilio status callback hits `/webhook/whatsapp/status`.
3. Observe `[WA DELIVERY TRUTH] truth_level=delivered_to_customer` or `failed_delivery`.

**PASS** when `queued` is no longer interpreted as delivered anywhere in attribution or merchant-facing “delivered” claims.

Do not mark production PASS from tests alone; require a real callback after deploy.

## Code map

| Piece | Location |
|-------|----------|
| Core logic | `services/whatsapp_delivery_truth_v1.py` |
| Webhook route | `routes/whatsapp_delivery_webhook.py` |
| Model | `models.WhatsAppDeliveryTruth` |
| Schema ensure | `schema_widget.ensure_whatsapp_delivery_truth_schema` |
| Tests | `tests/test_whatsapp_delivery_truth_v1.py` |
