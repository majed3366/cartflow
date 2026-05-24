# CartFlow Integration Foundation Audit v1

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit — source of truth per lifecycle stage before live Zid / Salla / Shopify adapters.  
**Commit message:** `docs: add integration foundation audit v1`  
**Related:** `docs/integrations_foundation_v1.md`, `services/platform_integration_gateway.py`, `integrations/adapters/*`

**No OAuth, webhook, widget, recovery, purchase truth, lifecycle, or auth behavior changes in this deliverable.**

---

## Executive summary

CartFlow **Core** is designed as:

```text
Platform (future) → PlatformAdapter → NormalizedPlatformEvent → platform_integration_gateway → Core APIs
```

**Today in production paths**, Core is driven primarily by:

- Storefront **widget / tracking scripts** → `POST /api/cart-event`
- **Merchant Zid OAuth** (store connection) + **`POST /webhook/zid`** (audit + `AbandonedCart` upsert only)
- **Twilio** `POST /webhook/whatsapp` (inbound replies)
- **`POST /api/conversion`** (purchase evidence)

The **gateway and adapters exist in code** but **adapters return `None`** and **no HTTP route calls the gateway** yet (`docs/integrations_foundation_v1.md`).

---

## Part 1 — Integration ownership map (by lifecycle stage)

### 1. Customer adds to cart

| Question | Answer (evidence) |
|----------|-------------------|
| **Owner** | **Storefront / platform cart** (source of items). **CartFlow** observes via embedded scripts. |
| **Platform?** | Future: `cart_created` / `cart_updated` via gateway (`platform_integration_gateway` → `upsert_abandoned_cart_from_payload` only — no recovery dispatch). |
| **Widget?** | V2 runtime + legacy widget; `cart_state_sync` with `reason=add` on `POST /api/cart-event` (`main.py` ~9911–9954). |
| **Webhook?** | Zid: `POST /webhook/zid` → `upsert_abandoned_cart_from_payload` (`main.py` L15802–15838) — **not** the normalized gateway. |
| **Both?** | Demo/store may use **both** platform cart pages and CartFlow scripts; truth for **recovery session** is CartFlow `session_id` + `cart_id` in payload, not platform cart id unless mapped later. |

**Source of truth (today):** Browser/session payload + `AbandonedCart` row after upsert; **not** platform cart API as authoritative for recovery scheduling.

---

### 2. Customer abandons

| Question | Answer (evidence) |
|----------|-------------------|
| **Owner** | **`POST /api/cart-event`** with `event=cart_abandoned` → `handle_cart_abandoned` (`main.py` L9955–9982). |
| **Widget?** | Indirect — `cart_abandon_tracking.js` / `cartflow_return_tracker.js` / widget flows fire abandon (`static/cart_abandon_tracking.js` L786–819; `cartflow_return_tracker.js` beforeunload path). |
| **Platform?** | **Not wired** — gateway `_route_cart_abandoned` exists (`platform_integration_gateway.py` L226+) but unused by `/webhook/zid`. |
| **Behavior / timeout?** | Abandon is **event-driven** (script triggers), not server-side idle timeout in Core. Store-level idle rules live in front-end tracking scripts. |
| **Fallback** | Missing reason → `waiting_for_reason`; missing phone → `waiting_for_phone` (`handle_cart_abandoned` / `_execute_cart_abandon_recovery_schedule_continue`). |

**Source of truth:** CartFlow **`recovery_key`** + `RecoverySchedule.due_at` + in-process asyncio delay; durable schedule survives restart (`recovery_restart_survival.py`).

---

### 3. Customer returns to site

| Question | Answer (evidence) |
|----------|-------------------|
| **Owner** | **`cartflow_return_tracker.js`** → `POST /api/cart-event` with `user_returned_to_site` / return visit fields (`static/cartflow_return_tracker.js` L267–279). |
| **Return tracker?** | **Yes** — primary client signal. |
| **Platform?** | No dedicated platform return webhook in Core today. |
| **Session?** | `sessionStorage` / `localStorage` (`cartflow_recovery_flow_started`, converted flags). |
| **Purchase?** | If converted, return tracker **no-ops** (`isConverted()` in return tracker). |

**Source of truth (layered):**

1. **Memory / behavioral** — `_recovery_resolve_user_returned_for_send` checks behavioral state, logs, `AbandonedCart` (`main.py` L5606+, L7358+).
2. **Durable log** — `CartRecoveryLog.status=returned_to_site` (`main.py` L2384 `_DURABLE_RETURN_TO_SITE_LOG_STATUS`).
3. **Not** purchase truth (return ≠ purchase).

---

### 4. Customer purchases

| Question | Answer (evidence) |
|----------|-------------------|
| **Owner** | **`purchase_truth_records`** (durable) via `ingest_purchase_truth_payload` / `cartflow_purchase_truth.py`. |
| **Platform order?** | Future: `order_paid` / `order_created` → gateway → same ingest (`platform_integration_gateway.py` L178–188). |
| **Webhook?** | Zid webhook **does not** call purchase truth today (only `upsert_abandoned_cart` + `RecoveryEvent`). |
| **Checkout event?** | **`POST /api/conversion`** with evidence flags (`main.py` L10071–10108; `extract_purchase_evidence` in `cartflow_purchase_truth.py` L77–89). |
| **Widget?** | `sessionStorage` `cartflow_converted` suppresses further abandon/return (`return_tracker`, widget paths). |

**Source of truth (precedence):** **`purchase_truth_records`** > session memory mirror > `CartRecoveryLog.stopped_converted` (session truth hardening reads DB on miss).

**Accepted evidence keys (code):** `purchase_completed`, `order_paid`, `checkout_completed`, `order_created`, matching `event` names, `user_converted=true`.

---

### 5. Customer replies (WhatsApp)

| Question | Answer (evidence) |
|----------|-------------------|
| **Owner** | **`POST /webhook/whatsapp`** (`main.py` L154–179) → `run_inbound_whatsapp_reply_intent_hook` + positive reply handlers. |
| **Provider webhook?** | **Twilio** (inbound message body). |
| **Continuation layer?** | `services/reply_intent_handling.py`, `whatsapp_positive_reply`, recovery follow-up suppress (`skipped_followup_customer_replied`). |

**Source of truth:** Inbound message text → reply intent; durable hints in `CartRecoveryLog` + behavioral flags; **not** platform order state.

---

## Source of truth map (summary table)

| Event / stage | Primary owner (today) | Durable store | Fallback | Risk if missing |
|---------------|----------------------|---------------|----------|-----------------|
| Cart contents / add | Storefront + `cart_state_sync` | `AbandonedCart` (partial) | Payload on abandon | Wrong totals in messages |
| `cart_abandoned` | `POST /api/cart-event` | `RecoverySchedule` + logs | None — no abandon | No recovery |
| Return to site | Return tracker → cart-event | Behavioral + `CartRecoveryLog` | Memory flags | Unwanted follow-up send |
| Purchase | `/api/conversion` + purchase truth | `purchase_truth_records` | Session converted flag | Recovery continues after buy |
| Reply | Twilio webhook | Logs + behavioral | — | Over-messaging |
| Platform order (future) | Gateway (not live) | Would → purchase truth | Widget conversion | Duplicate/conflict until unified |

---

## Part 2 — Platform dependency map

Evidence: `integrations/adapters/*.py`, `integrations/zid_client.py`, `services/merchant_store_connection_v1.py`, `main.py` `/webhook/zid`, `docs/integrations_foundation_v1.md`.

### Zid

| Capability | Available today | Evidence | Limitation |
|------------|-----------------|----------|------------|
| **Auth (OAuth)** | **YES** (merchant) | `merchant_store_connection_v1.py`, Zid connect URL, token on `Store.access_token` | App-level webhooks separate from merchant dashboard OAuth |
| **Webhook** | **PARTIAL** | `POST /webhook/zid`, `verify_webhook_signature` (`zid_client.py`) | Logs `RecoveryEvent`, upserts `AbandonedCart` only — **no** `platform_integration_gateway` |
| **Cart** | **PARTIAL** | `upsert_abandoned_cart_from_payload` on raw Zid JSON | Schema mapping implicit in upsert helper; not `NormalizedPlatformEvent` |
| **Order** | **NO** (into Core) | Adapter `normalize_event` → `None` | Order paid does not stop recovery from webhook |
| **Customer phone** | **PARTIAL** | If present in Zid payload → upsert path | Not guaranteed on all webhook types |
| **Order status** | **NO** | — | — |
| **Purchase confirmation** | **NO** (webhook path) | Use `/api/conversion` or future gateway | Merchants relying only on Zid webhook miss purchase truth |

### Salla

| Capability | Available today | Evidence |
|------------|-----------------|----------|
| **Auth** | **NO** | `SallaAdapter` scaffold; `salla_connect_available` in connection UI |
| **Webhook** | **NO** | No `/webhook/salla` route |
| **Cart / order / phone** | **NO** | `normalize_event` → `None` |

### Shopify

| Capability | Available today | Evidence |
|------------|-----------------|----------|
| **Auth** | **NO** | Scaffold only; `shopify_note_ar` in merchant connection status |
| **Webhook** | **NO** | No Shopify webhook route |
| **Cart / order / phone** | **NO** | `normalize_event` → `None` |

---

## Part 3 — Failure map

| Failure | Current fallback | YES / PARTIAL / NO | Evidence |
|---------|------------------|-------------------|----------|
| **Webhook missing** | Widget/cart-event still drives abandon; schedule may exist without platform sync | **PARTIAL** | Core does not require platform webhook for demo/widget path |
| **Phone missing** | `waiting_for_phone`; resolve from `AbandonedCart` / reason rows later | **PARTIAL** | `handle_cart_abandoned`, phone resolution chain in recovery |
| **Order delayed (late platform order)** | If conversion event arrives later, `ingest_purchase_truth_payload` stops recovery | **PARTIAL** | Purchase truth durable; race: send may occur before conversion if only widget path |
| **Purchase arrives late** | `stop_if_purchased` + session truth DB fallback on wake | **YES** (after evidence ingested) | `cartflow_purchase_truth`, `cartflow_session_truth` |
| **Platform outage** | CartFlow continues on last known browser/session state | **PARTIAL** | No platform pull/sync loop in production |
| **OAuth expired** | `is_merchant_store_platform_connected` false; onboarding shows disconnected | **PARTIAL** | `merchant_store_connection_v1.py`; **no** automatic token refresh documented in audit |
| **Webhook signature fail** | `401` on `/webhook/zid` | **YES** | `zid_webhook` L15805–15806 |
| **Invalid platform payload** | Gateway would skip `missing_required_field` (when used) | **YES** (gateway) | `validate_minimum_fields` — not on live Zid route |
| **Multi-worker duplicate** | DB claim + WA idempotency | **PARTIAL** | See `docs/cartflow_queue_worker_maturity_audit_v1.md` |

---

## Part 4 — Integration readiness verdict

### CartFlow Core (widget + cart-event + recovery + purchase truth)

| Use case | Verdict |
|----------|---------|
| **Widget-only / embedded script merchants** | **Production-viable** for controlled rollout — Core path is mature (recovery schedule, purchase truth, session truth, health endpoints). |
| **Manual / dev conversion + cart-event** | **Production-viable** for same stores when conversion POST or storefront scripts are wired. |

### Partial integrations (today)

| Integration | Verdict |
|-------------|---------|
| **Zid** | **Partial** — OAuth store connection + signed webhook + abandoned cart upsert + event logging. **Not** full adapter: no normalized events, no order-paid → purchase truth, no platform-driven abandon. |
| **Salla** | **Not ready** — scaffold only. |
| **Shopify** | **Not ready** — scaffold only. |

### Production platform integrations (orders + abandon from marketplace)

| Verdict | **Not ready** until: |
|---------|----------------------|
| | 1. `ZidAdapter.normalize_event` + store_slug mapping |
| | 2. `/webhook/zid` → verify → adapter → **gateway** (feature flag) |
| | 3. Durable idempotency (not in-process only) |
| | 4. Salla/Shopify adapters + webhooks |

**Honest one-line answer:** CartFlow Core is **safe for widget-led recovery today**; **unsafe to treat Zid webhook alone as full integration**; **do not launch Salla/Shopify** until adapters ship.

---

## Part 5 — Target architecture (Core + adapters)

```text
                    ┌─────────────────────┐
                    │   CartFlow Core     │
                    │ cart-event, truth,  │
                    │ recovery, WhatsApp  │
                    └──────────▲──────────┘
                               │
                    ┌──────────┴──────────┐
                    │ platform_integration│
                    │ _gateway            │
                    └──────────▲──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
       │ ZidAdapter  │  │SallaAdapter │  │ShopifyAdapt.│
       └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
              │                │                │
       webhook/API      (future)         (future)
```

**Rule:** Adapters translate; Core never parses raw Zid/Salla/Shopify JSON in recovery logic.

---

## Verification references

```bash
python -m pytest tests/test_integrations_foundation_v1.py -q
rg "platform_integration_gateway|normalize_event" integrations services
```

---

## Document control

| Item | Value |
|------|--------|
| Runtime changes | **None** |
| New routes | **None** |
