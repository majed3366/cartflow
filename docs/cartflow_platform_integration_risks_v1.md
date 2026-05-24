# CartFlow Platform Integration Risks v1

**Date (UTC):** 2026-05-19  
**Companion:** `docs/cartflow_integration_foundation_audit_v1.md`  
**Purpose:** Top risks before building real Zid / Salla / Shopify adapters.

---

## P0 — Must address before “full platform integration”

| # | Risk | Why it hurts | Mitigation direction |
|---|------|--------------|----------------------|
| 1 | **Dual truth paths (widget vs platform)** | Platform `order_paid` and widget `conversion` can disagree or arrive in different order → duplicate or late recovery stop. | Single ingress via gateway; document precedence; durable idempotency keys per order id. |
| 2 | **Zid webhook bypasses gateway** | `/webhook/zid` only upserts `AbandonedCart` — operators assume webhook = full integration (`main.py` L15802–15838). | Wire webhook → `ZidAdapter` → gateway behind flag; deprecate raw upsert-only path gradually. |
| 3 | **In-process idempotency only** | Gateway `_seen_external_events` is per-process (`platform_integration_gateway.py` L31–33). Multi-worker duplicates platform events. | DB or Redis dedupe table keyed by `build_idempotency_key`. |
| 4 | **`store_slug` mapping** | Zid `store_id` ≠ CartFlow slug unless explicitly mapped (`merchant_store_connection` uses OAuth on authenticated store). | Mapping table: `external_store_id` → `store_slug`; reject events without mapping. |

---

## P1 — High operational risk

| # | Risk | Detail |
|---|------|--------|
| 5 | **Session id = platform cart id assumption** | `normalized_event_to_core_payload` uses `external_cart_id` as `session_id` when present — wrong if platform reuses or rotates ids. |
| 6 | **Phone optional on platform events** | Gateway skips phone path silently (`phone_present=false`); recovery may stall in `waiting_for_phone` until another source fills phone. |
| 7 | **OAuth token expiry** | Connected store requires `access_token`; no audited refresh flow in integration layer — silent “connected” UI drift. |
| 8 | **Late purchase after send** | Purchase truth stops **future** recovery; cannot unsend WhatsApp if conversion only arrives from delayed platform webhook. |
| 9 | **Abandon not from platform** | Without `cart_abandoned` normalized event, platform-only merchants never enter recovery unless widget fires abandon. |

---

## P2 — Medium (scale / clarity)

| # | Risk | Detail |
|---|------|--------|
| 10 | **Salla / Shopify empty adapters** | False confidence if routes added before `normalize_event` implemented. |
| 11 | **`checkout_started` observation-only** | Gateway routes to `lifecycle_truth_future_hook` — no widget suppress parity (`integrations_foundation_v1.md`). |
| 12 | **RecoveryEvent log without routing** | Zid webhook stores payload in `RecoveryEvent` but does not drive recovery — ops grep noise. |
| 13 | **VIP vs normal path on mixed payloads** | Platform cart totals may trigger VIP branch if thresholds met — adapter must tag channel. |
| 14 | **Attribution without platform order id** | `purchase_attribution_v1` may lack `order_id` until platform fields populated consistently. |

---

## P3 — Lower (document / test)

| # | Risk | Detail |
|---|------|--------|
| 15 | **Test / demo phone paths** | `cf_test_phone` and demo slugs must not leak into production merchant analytics. |
| 16 | **Webhook signature env drift** | Zid secret rotation without deploy coordination → 401 storm. |
| 17 | **Arabic merchant copy on connection UI** | Salla/Shopify “coming soon” — manage expectations before marketing integrations. |

---

## Risk acceptance (today)

| Area | Accept for now? |
|------|-----------------|
| Widget-led recovery on demo + pilot merchants | **Yes** |
| Zid OAuth + webhook as **connection + catalog sync hint** only | **Yes**, with clear docs |
| Marketing “full Zid integration” | **No** |
| Salla / Shopify production | **No** |

---

## Recommended sequence (from `integrations_foundation_v1.md`, unchanged)

1. Implement `ZidAdapter.normalize_event` + signature (reuse `zid_client`).  
2. Store id → `store_slug` mapping.  
3. Feature-flag gateway on `/webhook/zid`.  
4. Durable idempotency.  
5. Salla, then Shopify.  
6. Integration health panel (read-only).
