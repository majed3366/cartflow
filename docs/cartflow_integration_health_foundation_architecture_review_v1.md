# Integration Health Foundation — Architecture Review v1

**Date (UTC):** 2026-06-10  
**Type:** Architecture review only — no implementation, no fixes, no dashboards, no alerts  
**Principle:** Every Integration Must Have Health  
**Horizon:** Pre-pilot and scale — define the safest minimal path before building

---

## Executive summary

CartFlow already has **partial, scattered integration signals** (store OAuth columns, Zid webhooks, widget beacons, WhatsApp provider readiness, widget health section, operational health JSON). What is missing is a **unified integration health model** with consistent states, diagnosis codes, source-of-truth ownership, and admin read-only aggregation.

**Critical finding:** Zid operates on a **live legacy stack** (`zid_client`, `/webhook/zid`, OAuth, widget install) while Salla/Shopify and the normalized adapter/gateway layer remain **scaffold-only**. Integration health must distinguish **“connected in production today”** from **“adapter contract ready for future wiring.”**

### Final verdict

**B. APPROVED WITH CONDITIONS**

Integration Health Foundation v1 may proceed **after** the conditions in §14 are accepted. The architecture is sound in direction; implementation must not duplicate truth or conflate operational health with integration health.

---

## Section 1 — Integration inventory

| Integration | Current status | Owner module(s) | Source of truth | Health signals available today | Missing signals |
|-------------|----------------|-----------------|-----------------|--------------------------------|-----------------|
| **Zid — OAuth / store connection** | **Live (merchant OAuth)** | `merchant_store_connection_v1.py`, `integrations/zid_client.py`, `main.py` (`/auth/zid`, `/auth/callback`) | `Store.access_token`, `refresh_token`, `token_expires_at`, `connected_at`, `integration_source` | `is_merchant_store_platform_connected()`; `GET /api/merchant/store-connection` | Token expiry health; refresh failure; OAuth callback error rate; per-store `last_oauth_success_at` |
| **Zid — dev OAuth** | **Live (flag-gated)** | `zid_dev_oauth_v1.py` | Same `Store` columns | `GET /dev/zid-dev-store-status` (readonly, no token) | Production merchant parity; unified diagnosis codes |
| **Zid — webhooks** | **Live** | `main.py` `POST /webhook/zid`, `zid_client.verify_webhook_signature`, `zid_webhook_purchase_v2.py` | `RecoveryEvent` audit rows; `AbandonedCart` upserts; `PurchaseTruthRecord` via ingest | Webhook receipt logs; signature pass/fail; PT ingest success | `last_webhook_at` per store; webhook type breakdown; stale webhook detection; registered vs receiving |
| **Zid — storefront widget install** | **Live (Partner Snippet path)** | `zid_storefront_widget_install_v1.py` | `Store.widget_installation_status`, `widget_installed_at`, `widget_install_error` | Status enum: `pending_partner_snippet`, `installing`, `installed`, `failed`, `unsupported` | Distinguish partner snippet pending vs merchant action; install verification age |
| **Storefront widget runtime** | **Live** | `widget_health_v1.py`, `storefront_runtime_truth_gate_v1.py`, `POST /api/storefront/widget-seen` | `Store.widget_last_seen_at`, `widget_last_beacon_json`, `widget_runtime_truth_*` | Admin widget health section; issue keys (`widget_not_seen`, `runtime_beacon_missing`, etc.) | Merchant-safe summary; unified integration diagnosis codes |
| **Cart events (widget path)** | **Live** | `main.py` `POST /api/cart-event` | `AbandonedCart`, `CartRecoveryReason`, recovery logs | Cart counts per store/window; audit traces | `last_cart_event_at` per store; event rate vs baseline; silence detection |
| **Product identity `lines[]`** | **Live (capture)** | Widget runtime + `product_cart_snapshots_v1.py` | `AbandonedCart.raw_payload` (widget); `cart_line_snapshots` (foundation) | Product Data Health (`GET /api/product-data/health`); Knowledge product bridge | Integration-level “identity flowing” signal separate from foundation readiness |
| **Purchase / order signals** | **Partially live** | `cartflow_purchase_truth.py`, `purchase_truth.py`, Zid webhook mapper, reply-claim ingest | `PurchaseTruthRecord` (durable) | Purchase truth gap visibility in operational health; KL attribution counts | Order webhook vs widget-only purchase path; payment failure class (not built) |
| **Platform adapter gateway** | **Scaffold — not wired** | `platform_integration_gateway.py`, `integrations/adapters/*.py` | N/A (no production ingress) | Gateway log prefixes `[PLATFORM EVENT *]` | Adapter health per platform; signature verification readiness |
| **Salla** | **Planned scaffold** | `integrations/adapters/salla.py` | None | Adapter returns `None` / `False` | OAuth, webhooks, store map, event flow — all missing |
| **Shopify** | **Planned scaffold** | `integrations/adapters/shopify.py` | None | UI note “Shopify قريباً” in store connection | Same as Salla |
| **WhatsApp / Twilio** | **Live (Twilio-first)** | `whatsapp_send.py`, `cartflow_provider_readiness.py`, delivery webhook | Env config + send logs + `WhatsAppDeliveryTruth` | `get_whatsapp_provider_readiness()`; failure classes; operational health WhatsApp summary | Per-store send success rate in integration health layer |
| **WhatsApp / Meta production** | **Blocked / stub** | `get_meta_readiness()` stub, `whatsapp_production_reality_v2.py` | Platform snapshot (read-only) | Meta readiness returns not-ready; production reality v2 snapshot | Must be labeled **production blocked**, not **failed** |
| **WhatsApp — merchant connection** | **Live (architecture readiness)** | `merchant_whatsapp_connection_readiness_v1.py` | Canonical connection states + onboarding flags | `GET /api/admin/whatsapp/connection-readiness`; merchant card | Consolidation into integration health JSON |
| **Payment / checkout friction** | **Not implemented** | N/A | Hesitation reasons (`CartRecoveryReason`) only | Hesitation buckets (price, shipping, etc.) | Payment declined, insufficient funds, checkout abandoned as distinct signal classes |
| **Admin integrations page** | **Placeholder** | `routes/admin_operations.py` `GET /admin/integrations` | None | “قريباً” | Entire integration health surface |

---

## Section 2 — Health model

Common states for Integration Health Foundation v1:

| State | Meaning | Required evidence | Suggested operator action |
|-------|---------|-------------------|---------------------------|
| **healthy** | Integration connected and recent successful activity within expected window | OAuth token present (if applicable); recent event or beacon within SLA; no critical diagnosis codes | Monitor only |
| **degraded** | Connected but partial function or stale activity | Token valid but no events N hours; widget seen but no cart events; PT gaps; provider intermittent failures | Investigate signal path; check merchant storefront traffic |
| **disconnected** | No valid connection | Missing `access_token`; WhatsApp `not_connected`; no OAuth completion | Merchant action: complete connection flow |
| **misconfigured** | Connection exists but CartFlow or merchant config prevents function | Wrong webhook secret; widget settings mismatch; missing env vars; identity mismatch | CartFlow ops or merchant settings fix depending on `action_owner` |
| **stale** | Was working; no recent success | `last_success_at` older than threshold; webhook silence; beacon silence | Check provider status, merchant theme changes, snippet removal |
| **unknown** | Insufficient evidence to classify | New store; no window data; probe failed open | Wait for first event or run admin diagnostic |
| **provider_unavailable** | External provider outage or rate limit | Provider readiness `provider_unavailable` / `provider_rate_limited`; repeated 5xx | Retry later; escalate to provider status page |
| **merchant_action_required** | Merchant must act in their platform | Partner snippet not applied; OAuth not started; WhatsApp setup incomplete; sandbox recipient not joined | Show simple merchant copy (§11) |
| **cartflow_action_required** | CartFlow platform/config issue | Missing `ZID_WEBHOOK_SECRET`; Meta production not enabled; scheduler misconfiguration affecting ingest | CartFlow ops fix env, deployment, or partner configuration |

**Mapping rule:** One integration may expose **multiple sub-states** (e.g., Zid OAuth `healthy` + widget `stale` + webhooks `unknown`). Top-level health = worst sub-state by severity rank, with sub-components listed in evidence.

---

## Section 3 — Zid health

### Current signal paths

| Layer | Signal | SoT | Can diagnose today? |
|-------|--------|-----|---------------------|
| OAuth | Store connected | `Store.access_token` non-empty | **Yes** — Zid not connected |
| OAuth | Token expiry | `Store.token_expires_at` | **Partial** — field exists; no health aggregation |
| Widget install | Partner snippet / probe | `widget_installation_status` | **Partial** — honest statuses including `pending_partner_snippet` |
| Widget runtime | Loader on storefront | `widget_last_seen_at`, beacon JSON | **Yes** — via `widget_health_v1` |
| Cart events | Widget → `/api/cart-event` | `AbandonedCart.first_seen_at` | **Partial** — counts exist; no integration-level stale signal |
| Product identity | `lines[]` in payload / snapshots | `cart_line_snapshots`, product-data health | **Partial** — foundation health, not Zid-specific |
| Purchase | Zid webhook + widget paths | `PurchaseTruthRecord`, `RecoveryEvent` | **Partial** — PT gaps visible operationally |
| Webhooks | `/webhook/zid` | Signature + `RecoveryEvent` | **Partial** — receipt logged; no per-store last webhook timestamp surfaced |

### Distinction matrix (required for v1)

| Scenario | Target diagnosis | Evidence |
|----------|------------------|----------|
| Zid not connected | `zid_not_connected` | No `access_token` |
| Zid connected but no events | `zid_cart_events_missing` | OAuth OK; no `AbandonedCart` in window; no webhook events |
| Widget installed but not sending | `widget_runtime_missing` or `widget_not_seen` | `widget_installation_status=installed` but no beacon / no cart-event |
| Webhooks missing / stale | `zid_webhook_stale` | OAuth OK; no `RecoveryEvent` type zid webhook in window; cart events only from widget |
| Purchase truth missing | `zid_purchase_events_missing` | Orders expected (merchant report) but no PT rows; optional Zid webhook PT path silent |
| CartFlow issue vs Zid issue | `action_owner` field | Misconfig (secret, snippet, env) → `cartflow_action_required`; merchant OAuth/snippet → `merchant_action_required`; Zid API down → `provider_unavailable` |

**Gap:** Today these distinctions require **manual correlation** across store-connection API, widget health, operational health, and DB queries. Integration Health Foundation v1 must **compose** existing readers — not invent parallel stores.

**Dual-stack note:** Normalized `ZidAdapter` is empty; live health must tag **`integration_path: legacy_zid`** until gateway wiring ships.

---

## Section 4 — Salla / Shopify health (planned model)

No production wiring exists. Define **minimum required signals** for when adapters go live:

| Signal category | Salla minimum | Shopify minimum |
|-----------------|---------------|-----------------|
| **Adapter readiness** | `normalize_event` non-null for fixture payloads; `verify_signature` true for test vectors | Same |
| **OAuth readiness** | OAuth URL + callback + token columns populated | Same + shop domain binding |
| **Webhook readiness** | Registered webhook URL reachable; signature secret configured; `last_webhook_at` | HMAC verification; GDPR shop redact handlers (future) |
| **Event flow readiness** | Normalized cart_abandoned + purchase events routed through gateway | Same |
| **Product/order signal readiness** | Line items in normalized event; purchase truth ingest | Variant/SKU identity tiers |

**v1 architecture stance:** Salla/Shopify appear in integration health as **`status: not_implemented`** with diagnosis `platform_adapter_scaffold_only` — not `failed`. Prevents false red alerts before pilot.

**Owner module (future):** `integrations/adapters/{salla,shopify}.py` + `platform_integration_gateway.py` + platform-specific OAuth modules (not yet created).

---

## Section 5 — WhatsApp / Meta health

### Separate concerns (mandatory)

| Layer | Question | Module | Production today? |
|-------|----------|--------|-------------------|
| **WhatsApp architecture health** | Can CartFlow attempt sends per policy? | `cartflow_provider_readiness.py`, `whatsapp_send.py`, connection readiness | Twilio path: yes (env-dependent) |
| **Meta production approval reality** | Is Meta Cloud API production approved? | `get_meta_readiness()` stub, `whatsapp_production_reality_v2.py` | **No — blocked by design** |

**Rule:** Meta incomplete → state **`production_blocked`** (or diagnosis `meta_production_blocked`), **not** `provider_unavailable` or `failed`.

### WhatsApp health sub-components

| Sub-component | Signals | Failure classes (existing) |
|---------------|---------|----------------------------|
| Provider configured | Twilio env vars | `provider_not_configured` |
| Merchant connected | `merchant_whatsapp_connection_readiness_v1` states | `not_connected`, `setup_required`, `action_required` |
| Template readiness | Template approval flags | `template_not_approved` |
| 24h policy readiness | Session window / reply path | Implicit in send path; not surfaced as integration health yet |
| Send capability | Recent `sent_real` logs | `provider_auth_failed`, `provider_rate_limited`, `provider_unavailable` |
| Callback / webhook status | `/webhook/whatsapp`, `/webhook/whatsapp/status` | Delivery truth ingest |
| Failure taxonomy | `cartflow_provider_readiness.py` | Full `_MERCH` mapping for merchant-safe copy |

**v1 recommendation:** Integration health exposes **platform WhatsApp** block (provider + Meta production gate) and **per-store WhatsApp** block (connection readiness + recent send outcome) as separate JSON sections.

---

## Section 6 — Payment / order signal health (future architecture)

Today CartFlow conflates **customer hesitation** (widget reason tags) with **commerce outcomes** (purchase truth). Payment/checkout friction is **not yet modeled**.

### Proposed signal classes (architecture only)

| Signal class | Meaning | Must not confuse with |
|--------------|---------|------------------------|
| **Customer hesitation** | Widget-captured reason (price, shipping, thinking) | Payment failure |
| **Checkout friction** | Checkout started but not completed (timeline hints) | Hesitation reason alone |
| **Payment failed** | Provider/gateway declined payment | Price objection |
| **Payment declined** | Issuer decline | Insufficient funds |
| **Insufficient funds** | Specific decline code | Generic “price” hesitation |
| **Checkout abandoned** | Session ended at payment step | Cart abandoned without checkout signal |
| **Purchase confirmed** | Durable `PurchaseTruthRecord` | Recovery attribution |

**Integration health role:** Report **signal readiness** (`payment_signal_missing`, `checkout_signal_missing`) — not intelligence or recommendations.

**SoT (future):** Normalized platform events + payment webhooks → append-only audit; hesitation remains `CartRecoveryReason`; purchase remains `PurchaseTruthRecord`.

---

## Section 7 — Source of truth

| Question | Owner (single SoT) | Do NOT duplicate in |
|----------|-------------------|---------------------|
| Is store connected? | `Store.access_token` via `is_merchant_store_platform_connected()` | Ad-hoc checks in dashboards |
| Is widget active on storefront? | `Store.widget_last_seen_at` + beacon JSON | Cart event counts alone |
| Are cart events flowing? | `AbandonedCart.first_seen_at` per store (widget path) + `RecoveryEvent` (webhook path) | Knowledge metrics |
| Are purchase events flowing? | `PurchaseTruthRecord.purchase_time` | Lifecycle closure alone |
| Is WhatsApp send allowed? | `evaluate_whatsapp_connection_readiness()` + `get_whatsapp_provider_readiness()` | Onboarding card only |
| Are templates approved? | Provider/template config (Twilio/Meta future) | Recovery message builder |
| Is provider failing? | Recent send logs + `get_whatsapp_provider_readiness()` | Merchant-facing “ready” card without provider check |
| Is Zid webhook receiving? | `RecoveryEvent` filtered by zid source (or dedicated webhook audit) | Assumption from OAuth alone |
| Widget install complete? | `Store.widget_installation_status` | OAuth connected flag |

**Composition rule:** Integration Health Foundation **reads** these SoTs via existing service functions. It does **not** write new truth columns in v1 except optional cached `last_*_at` timestamps if added later (out of v1 scope).

---

## Section 8 — Health endpoint architecture

### Decision: extend operational health, do not fragment

| Option | Pros | Cons |
|--------|------|------|
| **A. New `GET /api/admin/integrations/health`** | Clear ownership | Another admin endpoint; duplicates auth/composition |
| **B. Add `integrations` section to `GET /api/admin/operational-health`** | Single admin truth center; matches existing pattern | Larger payload |
| **C. Merchant `GET /api/integrations/health`** | Merchant visibility | Violates v1 scope (admin read-only); jargon risk |

**Recommendation:** **Option B for v1** — add additive `integrations` block to `GET /api/admin/operational-health` composed by new `services/integration_health_v1.py`. Optionally expose the same builder at `GET /api/admin/integrations/health` later if payload size requires split — **not required for v1**.

### Proposed JSON shape (read-only)

```json
{
  "integrations": {
    "generated_at": "ISO8601",
    "platform": {
      "zid": { "health_status": "degraded", "diagnosis_codes": [], "action_owner": "merchant", "last_success_at": null, "last_failure_at": null, "evidence": {} },
      "salla": { "health_status": "unknown", "implementation": "scaffold_only" },
      "shopify": { "health_status": "unknown", "implementation": "scaffold_only" },
      "whatsapp": { "health_status": "healthy", "sub": { "provider": {}, "meta_production": { "status": "production_blocked" } } }
    },
    "stores": [
      {
        "store_slug": "...",
        "zid": { "connected": true, "widget": {}, "cart_events": {}, "webhooks": {}, "purchase_signals": {} },
        "whatsapp": { "connection_state": "connected", "diagnosis_codes": [] }
      }
    ],
    "widget_event_flow": { "health_status": "...", "diagnosis_codes": [] },
    "purchase_order_readiness": { "health_status": "...", "diagnosis_codes": [] }
  }
}
```

**No UI. No alerts. No writes.**

---

## Section 9 — Diagnosis codes

Namespace: `integration_*` or platform-prefixed (align with existing `operational_control_unavailable`, `KL_*` patterns).

### Zid

| Code | Meaning | action_owner |
|------|---------|--------------|
| `zid_not_connected` | No OAuth token | merchant |
| `zid_oauth_expired` | Token past expiry | merchant |
| `zid_oauth_missing_scopes` | Token present but API probe fails (future) | merchant / cartflow |
| `zid_webhook_stale` | No webhook activity in window | merchant / cartflow |
| `zid_webhook_signature_misconfigured` | Secret missing or verify fails | cartflow |
| `zid_cart_events_missing` | Connected but no cart activity | merchant |
| `zid_purchase_events_missing` | Sales activity expected, no PT | merchant / cartflow |
| `zid_widget_pending_partner_snippet` | Awaiting partner snippet | cartflow |
| `zid_widget_install_failed` | Install probe failed | merchant / cartflow |

### Widget / event flow

| Code | Meaning |
|------|---------|
| `widget_runtime_missing` | No runtime beacon |
| `widget_not_seen` | No widget-seen |
| `widget_identity_lines_missing` | Cart events without `lines[]` / snapshots |
| `widget_settings_mismatch` | Dashboard vs runtime truth |
| `store_identity_mismatch` | Storefront slug resolution failed |

### WhatsApp / Meta

| Code | Meaning |
|------|---------|
| `whatsapp_provider_missing` | Twilio/env not configured |
| `whatsapp_merchant_not_connected` | Merchant setup incomplete |
| `whatsapp_template_not_ready` | Template not approved |
| `meta_production_blocked` | Meta production not approved — **not a failure** |
| `whatsapp_webhook_stale` | No inbound/status callbacks |

### Platform / provider

| Code | Meaning |
|------|---------|
| `platform_adapter_scaffold_only` | Salla/Shopify not live |
| `provider_rate_limited` | Rate limit detected |
| `provider_unavailable` | Provider outage |
| `payment_signal_missing` | No payment-class events (future) |
| `checkout_signal_missing` | No checkout timeline hints |

---

## Section 10 — Failure isolation

| If integration X fails… | Should stop? | Current behavior | Target |
|---------------------------|--------------|------------------|--------|
| Zid webhook down | Recovery for that store? | Widget cart-event path may still work | **Isolated** — degrade Zid webhook diagnosis; widget path independent |
| Widget not loading | Recovery? | No new carts; existing schedules may continue | **Isolated per store** |
| WhatsApp provider down | Recovery sends? | Send fails; schedules retry/fail per policy | **Isolated** — fail-closed send, not global app down |
| Knowledge layer inputs missing | Dashboard? | KL shows insufficient; dashboard loads | **Isolated** — already true post KL v1 |
| One store OAuth broken | Other stores? | Other stores unaffected | **Isolated** — required |
| Operational control unavailable | Sends? | Fail-closed gates (implemented) | **Platform-wide gate only** — intentional |

**Architecture requirement:** Integration health reporting must **never** throw platform-wide 500 because one store probe fails. Per-store sections fail open to `unknown` with evidence.

---

## Section 11 — Mobile first / merchant simplicity

| Admin diagnosis | Merchant copy (Arabic) | When |
|-----------------|------------------------|------|
| `zid_not_connected` | يحتاج ربط المتجر | OAuth missing |
| `zid_cart_events_missing` | ننتظر أول حدث من المتجر | Connected, no activity |
| `whatsapp_merchant_not_connected` | واتساب يحتاج إكمال الربط | Setup incomplete |
| `zid_purchase_events_missing` | هناك مشكلة في استقبال الطلبات | PT path silent |
| `widget_not_seen` | الودجت غير ظاهر للعملاء | No beacon |
| `meta_production_blocked` | *(Admin only in v1)* | Do not show Meta jargon to merchants |

**v1 scope:** Merchant copy definitions only — **no new merchant integration health UI**. Existing store-connection and WhatsApp cards remain; integration health is **admin JSON** first.

---

## Section 12 — Integration Health Foundation v1 scope

### In scope

- Admin read-only health composition service (`integration_health_v1.py`)
- Additive `integrations` section on `GET /api/admin/operational-health`
- Zid health foundation (OAuth, widget install, widget runtime, cart events, webhooks, purchase signal readiness)
- WhatsApp health summary (provider + per-store connection; Meta as `production_blocked`)
- Widget / event flow signals (reuse `widget_health_v1` issue keys mapped to diagnosis codes)
- Purchase / order **signal readiness** (not payment intelligence)
- Diagnosis codes + `action_owner` + `last_success_at` / `last_failure_at` where evidence exists
- Per-store health where applicable

### Explicitly out of scope (v1)

- External alerting, Slack, email
- Auto-repair, reconnect flows
- Full integration dashboards (`/admin/integrations` remains placeholder until v2)
- Salla/Shopify production implementation
- Meta production completion
- Merchant-facing integration health page
- Payment intelligence
- Product intelligence

### Safest minimal implementation path

1. **Define** `integration_health_v1.py` as pure read-only composer (no new tables in v1).
2. **Map** existing SoT readers (store connection, widget health, provider readiness, cart/PT timestamps).
3. **Attach** to operational health JSON additively.
4. **Add tests** mirroring `test_operational_control_fail_closed_v1.py` patterns.
5. **Defer** cached timestamps / webhook registry tables to v1.1 if query cost requires.

---

## Section 13 — Out of scope (explicit)

- External alerting
- Slack / email notifications
- Auto-repair and reconnect flows
- Full integration dashboards
- Product intelligence
- Payment intelligence
- Salla / Shopify production implementation
- Meta production completion
- UI redesign
- Changes to recovery send paths, purchase truth writes, or lifecycle classification

---

## Section 14 — Final verdict and conditions

### Verdict: **B. APPROVED WITH CONDITIONS**

Integration Health Foundation v1 is architecturally sound and aligned with CartFlow’s existing health patterns (Knowledge Layer health, operational health diagnosis, product readiness). Implementation may proceed once conditions are met.

### Conditions (must accept before build)

| ID | Condition |
|----|-----------|
| **IH-C1** | **Single composer** — `integration_health_v1.py` reads existing SoTs; no duplicate truth columns in v1 |
| **IH-C2** | **Dual-stack honesty** — Zid health labels `integration_path: legacy_zid` until gateway/adapters are wired |
| **IH-C3** | **Meta separation** — `meta_production_blocked` distinct from provider failure states |
| **IH-C4** | **Hesitation ≠ payment** — payment/checkout codes must not reuse hesitation reason tags |
| **IH-C5** | **Fail isolated** — per-store probe errors return `unknown`, never break platform operational health |
| **IH-C6** | **Extend operational health first** — additive JSON section before standalone dashboard |
| **IH-C7** | **Salla/Shopify scaffold** — report `not_implemented`, not `failed` |
| **IH-C8** | **Merchant simplicity reserved** — admin JSON only in v1; Arabic copy table is spec, not UI work |

### Post-v1 (not blocking)

- Dedicated `GET /api/admin/integrations/health` if payload splitting needed
- Webhook registry + `last_webhook_at` materialized fields
- Normalized adapter health when gateway goes live
- Merchant integration status card (simple copy from diagnosis mapping)

---

## Appendix — Related existing health surfaces

| Surface | Route | Scope |
|---------|-------|-------|
| Operational Truth Center | `GET /api/admin/operational-health` | Scheduler, OC, lifecycle, purchase gaps, WhatsApp summary |
| Scheduler | `GET /health/scheduler` | Ownership, backlog |
| Product data | `GET /api/product-data/health` | Merchant payload/foundation readiness |
| Knowledge | `GET /api/knowledge/health` | Merchant KL health |
| Widget (admin section) | Embedded in admin operations | Per-store widget issues |
| WhatsApp admin | `GET /api/admin/whatsapp/connection-readiness` | Per-store connection architecture |

Integration Health Foundation **composes** these; it does not replace them.

---

*Review complete. No code changes. Ready for Integration Health Foundation v1 implementation planning.*
