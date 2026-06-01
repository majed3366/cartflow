# CartFlow Cart ID Truth Audit (Phase 0.5)

**Date:** 2026-06-01 (UTC)  
**Mode:** Read-only audit — no behavior changes  
**Context:** Production shadow confirmed `mismatch=true` when both `session_id` and `cart_id` are present: `current_rk = store:session_id`, `recommended_rk = store:cart_id`.

This document maps every **cart_id producer and consumer** and evaluates whether `cart_id` is stable enough to become the future journey identity (JID).

**Automated regression:** `tests/test_cart_id_truth_audit_v1.py`

---

## SECTION A — Current cart_id producers

### A1. Widget / browser (`static/cart_abandon_tracking.js`, `static/cartflow_widget.js`)

| Producer | Pattern | When created | Storage |
|----------|---------|--------------|---------|
| `getStableCartEventIdForTracking()` | `cf_cart_{uuid}` or timestamp fallback | First cart event in tab when no prior id | `sessionStorage` key `cartflow_cart_event_id` |
| Platform override | Any string | When merchant sets `window.CARTFLOW_CART_ID` | Page global (not persisted by CartFlow unless store sets it each load) |
| Demo store bootstrap | `cf_cart_*` via demo template | Demo checkout flow | `sessionStorage` (`templates/demo_store.html`) |

**Code priority:** `CARTFLOW_CART_ID` → sessionStorage → new UUID.

### A2. Server synthetic (`main.py`)

| Producer | Pattern | When created | Tied to |
|----------|---------|--------------|---------|
| `_ensure_cart_abandon_payload_has_cart_id()` | `cf_w_{sha256(rk)[:24]}` | Abandon upsert when payload has no cart_id | `recovery_key` (session-first today) |
| `_synthetic_zid_cart_id_from_recovery_key()` | Same `cf_w_*` | Merge lookup for `AbandonedCart` | `recovery_key` |

Deterministic: same `recovery_key` → same `cf_w_*`.

### A3. Session fingerprint fallback (`main.py`)

| Producer | Pattern | When created |
|----------|---------|--------------|
| `_session_part_from_payload()` | `fp:{sha256(cart_json)[:32]}` | No `session_id` and no `cart_id` in payload |

Used as **session segment** of RK, not as `AbandonedCart.zid_cart_id` directly unless later normalized.

### A4. Platform / webhook (`normalize_zid_cart_fields`, `zid_webhook_purchase_v2.py`)

| Source field paths | Persisted as |
|--------------------|--------------|
| `cart_id`, `id`, `data.cart_id`, `data.cart.id`, `data.abandoned_cart_id` | `AbandonedCart.zid_cart_id` via upsert |
| Zid purchase webhook: `zid_cart_id`, `external_cart_id`, nested `cart.id` | Often copied into **`session_id`** when session absent (`build_zid_purchase_truth_payload`) |

### A5. Platform integration gateway (`services/platform_integration_gateway.py`)

| Field | Value |
|-------|-------|
| `external_cart_id` | Both `session_id` and `cart_id` in core payload when present |
| Fallback | `platform:{platform}:{customer_id}` as session when no cart id |

**Status:** Scaffold — adapters return `None`; not live-wired for Salla/Shopify.

### A6. Demo / test identities

| Producer | Pattern | Purpose |
|----------|---------|---------|
| `demo_pi_fresh_session.new_demo_tracking_identity_pair()` | `cf_cart_{uuid}` | Clean demo PI session |
| `startNewMerchantTestLifecycle()` (JS) | `cf_tw_{uuid}` | Merchant test widget reset |
| Load tests / dev routes | Arbitrary strings | Synthetic traffic |

### A7. Test / integration constants

Examples: `s_integration_demo_cart`, `recon-c1`, admin load-test ids — stable **within test** only.

---

## SECTION B — Current cart_id consumers

### B1. Persistence

| Consumer | Field | Notes |
|----------|-------|-------|
| `AbandonedCart` | `zid_cart_id` **UNIQUE** | Canonical cart row key in DB |
| `AbandonedCart` | `recovery_session_id` | Separate; RK today prefers session |
| `RecoverySchedule` | `cart_id` | Denormalized; `recovery_key` is BID today |
| `CartRecoveryLog` | `cart_id` | Audit |
| `PurchaseTruthRecord` | `cart_id` | Evidence column; RK is primary |
| `LifecycleClosureRecord` | `cart_id` | Evidence column |

### B2. Merge / lookup

| Function | Uses cart_id for |
|----------|----------------|
| `_collect_abandoned_cart_rows_for_merge()` | Match by `zid_cart_id`, session, or `cf_w_*` from RK |
| `_abandoned_cart_try_upgrade_synthetic_zid()` | Upgrade `cf_w_*` → real id |
| `abandoned_carts_for_session_or_cart()` | OR query session + cart |
| `reconcile_purchase_with_active_recovery_carts()` | Bridge purchase by cart_id |
| `find_latest_abandoned_cart_for_customer_phone()` | Phone → cart row → ids |

### B3. Recovery / scheduling

| Consumer | Behavior |
|----------|----------|
| `_arm_recovery_schedule_from_saved_reason_payload` | Replays **stored** cart_id from abandon snapshot |
| `persist_recovery_schedule_durable()` | Stores cart_id on schedule row |
| Shadow resolver | Computes JID = `store:cart_id` when “stable” |

### B4. Dashboard / lifecycle reads

| Consumer | Behavior |
|----------|----------|
| `merchant_dashboard_recovery_resolve_v1.canonical_recovery_keys_for_cart()` | Generates RK **variants** including cart-based keys |
| `_abandoned_cart_canonical_recovery_key()` | Still session-first via `_recovery_key_from_payload` |
| Classifiers / purchased tab | Bulk truth keyed primarily by RK variants |

### B5. WhatsApp / replies

| Consumer | Behavior |
|----------|----------|
| `reply_intent_handling._recovery_key_for_abandoned_cart()` | Uses row's `zid_cart_id` in payload but RK remains session-first |

### B6. Journey identity (Phase 0 shadow)

| Consumer | Behavior |
|----------|----------|
| `journey_identity_resolver_v1` | Treats `cf_cart_*` as **stable** JID; excludes `cf_w_*`, `fp:*` |

---

## SECTION C — Stability matrix

Legend: **Y** stable, **N** not stable, **P** partial, **—** not applicable

| Source | Refresh same tab | New tab / sessionStorage cleared | Return-to-site (same tab) | Recovery schedule | Purchase truth | Process restart | Platform webhook same order |
|--------|------------------|----------------------------------|---------------------------|-------------------|----------------|-----------------|------------------------------|
| **`cf_cart_*` (widget)** | Y | N (new id) | Y (if storage intact) | Y (replayed from abandon) | P (RK still session; reconcile by cart_id) | Y (DB row) | N (platform id differs) |
| **`cf_w_*` (server)** | Y | Y (deterministic from RK) | Y | Y | P | Y | N until upgraded |
| **`fp:*` (fingerprint)** | P (cart contents) | P | P | — | — | — | N |
| **Platform / Zid id** | — (not from widget today) | — | — | P (if on row) | Y when present on payload | Y (DB) | Y (authoritative for order) |
| **`CARTFLOW_CART_ID` override** | Y if store re-injects | P | P | Y | Y | Y | Y (if merchant wires platform id) |
| **`cf_tw_*` (test reset)** | N (intentional) | N | N | N | N | — | — |

### Cross-namespace reality (production shadow finding)

A single customer journey can carry **two stable-but-different ids**:

1. Browser: `cf_cart_{uuid}` (widget)
2. Platform: Zid cart id (webhook / checkout)

Shadow logs show `mismatch=true` even when both are “stable” within their namespace because **recommended JID picks cart_id from payload**, which is usually the browser id, while purchase may arrive with platform id in a different field.

---

## SECTION D — Risks

| ID | Risk | Impact |
|----|------|--------|
| R1 | **Dual cart_id namespaces** (browser vs platform) | JID ambiguity; purchase on platform id, schedule on browser id |
| R2 | **`cf_cart_*` treated as stable JID** in shadow | Overstates readiness for cart-first RK; not equal to platform cart |
| R3 | **sessionStorage loss** (new tab, privacy mode, TTL) | New `cf_cart_*`; old `AbandonedCart` row orphaned unless merge by session |
| R4 | **`cf_w_*` upgrade collision** | `_abandoned_cart_try_upgrade_synthetic_zid` refuses if real id already taken |
| R5 | **Zid webhook session substitution** | `cart_id` field often empty; platform id lives in `session_id` |
| R6 | **RK remains session-first** | All durable truth keyed by BID while shadow recommends JID |
| R7 | **`AbandonedCart.zid_cart_id` UNIQUE** | Cannot represent two active ids for one journey without alias layer |
| R8 | **No live Salla/Shopify cart ingress** | Future platforms may introduce third id shapes |
| R9 | **Merchant store rarely sets `CARTFLOW_CART_ID`** | Production widget likely emits `cf_cart_*` only |

---

## SECTION E — Recommendation

### **C — Hybrid identity required**

Neither conclusion A nor B alone is sufficient for CartFlow today.

| Option | Verdict | Why |
|--------|---------|-----|
| **A) `cf_cart_*` stable enough alone** | **Reject** | Stable only within browser session scope; not platform-authoritative; breaks cross-channel purchase alignment |
| **B) Platform cart id stable enough alone** | **Reject** | Often absent at widget abandon; frequently mapped to `session_id` on webhook; not wired from storefront by default |
| **C) Hybrid identity required** | **Accept** | BID (`store:session_id`) + JID (`store:platform_cart_id` when known, else browser id) with explicit alias/promotion — matches Alias Design |
| **D) cart_id not suitable as primary identity** | **Reject** | Platform cart id **is** the correct long-term anchor when present; browser id is a bootstrap handle |

### Phase 0.5 policy implications (design only — no code change)

1. **Refine “stable cart_id” for JID:** distinguish `cf_cart_*` (browser bootstrap) vs platform ids (Zid/Salla) in shadow metrics before Phase 1.
2. **Promotion trigger:** when platform cart id first observed, promote browser BID → platform JID (not the reverse).
3. **Do not flip RK to cart-first globally** until dual-read proves cross-namespace purchase alignment.
4. **Wire `CARTFLOW_CART_ID`** from merchant storefront when platform exposes cart id (recommended merchant integration task, separate from this audit).

### Prerequisites before Alias Layer

- [ ] Production shadow soak with cart_id prefix breakdown (`cf_cart_` vs platform vs `cf_w_`)
- [ ] Zid live webhook sample: `% with cart_id field` vs `% session_id only`
- [ ] Decision: is browser `cf_cart_*` ever a valid JID, or only a BID companion until platform id arrives?

---

## Appendix — File map (producers / consumers)

| Area | Key files |
|------|-----------|
| Widget producers | `static/cart_abandon_tracking.js`, `static/cartflow_widget.js`, `templates/demo_store.html` |
| Server synthetic | `main.py` (`_ensure_cart_abandon_payload_has_cart_id`, `_synthetic_zid_cart_id_from_recovery_key`, `_abandoned_cart_try_upgrade_synthetic_zid`) |
| Upsert / merge | `main.py` (`upsert_abandoned_cart_from_payload`, `normalize_zid_cart_fields`, `_collect_abandoned_cart_rows_for_merge`) |
| Zid purchase | `services/zid_webhook_purchase_v2.py` |
| Platform gateway | `services/platform_integration_gateway.py`, `integrations/adapters/*.py` |
| Demo / test | `services/demo_pi_fresh_session.py`, merchant test lifecycle JS |
| Stability rules | `services/journey_identity_resolver_v1.py` |
| Model constraint | `models.py` (`AbandonedCart.zid_cart_id` unique) |

---

**Audit only. No behavior changes.**
