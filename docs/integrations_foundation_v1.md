# Integrations Foundation v1

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add integrations foundation adapter layer v1`

Prepare CartFlow Core for Zid / Salla / Shopify **without** implementing any live platform connection in this release.

## Core vs adapters

```text
Platform webhook/API
        ↓
PlatformAdapter (Zid / Salla / Shopify)
        ↓
NormalizedPlatformEvent
        ↓
platform_integration_gateway
        ↓
Existing CartFlow Core (cart-event, Purchase Truth, phone cache, …)
```

**CartFlow Core stays independent.** Marketplace-specific JSON never bypasses normalization.

## NormalizedPlatformEvent

Defined in `integrations/normalized_platform_event.py`.

| Field | Role |
|-------|------|
| `platform` | `zid` / `salla` / `shopify` / … |
| `store_slug` | CartFlow merchant store key |
| `external_*` | Platform-native ids (no guessing) |
| `event_type` | Normalized type (see below) |
| `customer_phone` / `customer_email` | Optional; missing phone does not fail event |
| `items`, `cart_total`, `currency`, `checkout_url` | Optional commerce context |
| `raw_payload` | Original body (audit only) |
| `confidence`, `source` | Adapter metadata |

### Supported `event_type` values

1. `cart_created`  
2. `cart_updated`  
3. `cart_abandoned`  
4. `checkout_started`  
5. `order_created`  
6. `order_paid`  
7. `order_cancelled`  
8. `customer_updated`  

## PlatformAdapter (interface only)

`integrations/adapters/base.py`:

- `normalize_event(raw_payload)`
- `verify_signature(headers, raw_body)`
- `map_store`, `extract_customer`, `extract_cart`, `extract_order`

### Scaffold adapters (no live APIs)

| Adapter | File | Status |
|---------|------|--------|
| Zid | `integrations/adapters/zid.py` | `normalize_event` → `None` |
| Salla | `integrations/adapters/salla.py` | scaffold |
| Shopify | `integrations/adapters/shopify.py` | scaffold |

Existing `integrations/zid_client.py` remains; **not** wired into adapters in v1.

## Gateway

`services/platform_integration_gateway.py`

| Responsibility | Behavior |
|----------------|----------|
| Validate | Required fields per type; at least one `external_*` identity |
| Idempotency | In-process key; duplicate → `[PLATFORM EVENT SKIPPED] reason=duplicate_external_event` |
| `cart_abandoned` | Existing `handle_cart_abandoned` + `should_process_cart_event_burst` |
| `order_paid` / `order_created` | `ingest_purchase_truth_payload` (unchanged Purchase Truth rules) |
| `checkout_started` | `lifecycle_truth_future_hook` only (no lifecycle mutation) |
| `customer_updated` | `record_recovery_customer_phone` when phone present |
| `cart_created` / `cart_updated` | `upsert_abandoned_cart_from_payload` only (no recovery dispatch) |

### Logs

- `[PLATFORM EVENT RECEIVED]`
- `[PLATFORM EVENT NORMALIZED]`
- `[PLATFORM EVENT ROUTED]`
- `[PLATFORM EVENT SKIPPED] reason=…`
- `phone_present=false` when phone absent

## Intentionally NOT implemented (v1)

- Zid / Salla / Shopify OAuth or app install  
- Live HTTP calls from adapters  
- Webhook route changes (`/webhook/zid` unchanged)  
- Widget, merchant dashboard, recovery, WhatsApp, lifecycle, or Purchase Truth rule changes  
- Shared Redis idempotency (in-process only)  
- Automatic store mapping DB  

## Risks

| Risk | Mitigation |
|------|------------|
| Multi-worker duplicate delivery | Future: Redis idempotency + DB dedupe table |
| Incomplete platform payload | Skip with `missing_required_field` — no guessing |
| Wrong `store_slug` mapping | Future: `map_store` + merchant linking table |
| Gateway imports `main` | Lazy import only on route; not loaded at app startup |

## Future integration sequence

1. Implement `ZidAdapter.normalize_event` + signature verification (reuse `zid_client`).  
2. Map Zid store id → `store_slug` (config table).  
3. Point `/webhook/zid` to: verify → adapter → gateway (behind feature flag).  
4. Repeat for Salla, Shopify.  
5. Move idempotency to durable store.  
6. Add admin “integration health” read-only panel.  

## Verification

```bash
python -m pytest tests/test_integrations_foundation_v1.py -q
python -c "import main; print('ok')"
```

**Deploy:** No new public routes in v1 — runtime behavior unchanged until webhooks call the gateway.
