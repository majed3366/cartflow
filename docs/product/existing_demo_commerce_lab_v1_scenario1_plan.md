# Existing Demo Commerce Lab V1 — Scenario 1 Implementation Plan

**Status:** Implementation plan only (no code in this document)  
**Date (UTC):** 2026-07-10  
**Authority:** [`existing_demo_commerce_lab_v1_audit.md`](existing_demo_commerce_lab_v1_audit.md)  
**Out of scope:** New demo, new tables, new architecture, UI redesign, Traffic/Product Signals, merchant_activation Lab runs

> **Law:** One reset. One scenario. Store `demo` only. Product `hp_pro` @ **449 SAR**.  
> Reuse existing sandbox APIs. Keep the change small enough to roll back by disabling the runner and resetting demo.

---

## 0. Fixed constants (Scenario 1)

| Constant | Value |
|----------|--------|
| `store_slug` | `demo` |
| Product key | `hp_pro` |
| Product path | `/demo/store/product/1` (`SANDBOX_PRODUCT_NUM_BY_KEY["hp_pro"] == 1`) |
| Unit price | **449** SAR |
| Reason | `price` / `price_high` (existing demo path) |
| Lab phone | `CARTFLOW_DEMO_TEST_PHONE` (canonical QA phone; never a real merchant customer) |
| Scenario id | `lab_v1_recovery_to_purchase` |
| Catalog | Existing 13-SKU sandbox — **no catalog edits required** for Scenario 1 |

**Identity strategy (deterministic per run, not random at assert time):**

| Field | Strategy |
|-------|----------|
| `session_id` | Fixed pattern for the run: `s_lab_v1_s1` **or** minted once at Lab Reset and held constant through all steps |
| `cart_id` | `cf_cart_lab_v1_s1` **or** minted once at Lab Reset and held constant |
| `recovery_key` | Always `demo:{session_id}` (store prefix required for Signals isolation) |
| Timestamps | Real clock allowed; waits **bounded** (e.g. ≤30s for schedule/timeline). Assertions are **order + presence**, not absolute wall-clock equality |

No random product, phone, price, or store.

---

## 1. Authoritative Lab Reset (`lab_reset_v1`)

**Single entry** for Scenario 1. Compose existing purge + browser reset. Do **not** call merchant `new-lifecycle`.

### 1.1 Scope gate (hard fail before any write)

| Check | Required |
|-------|----------|
| `store_slug == "demo"` | Yes — reject `demo2` for Scenario 1 runner (isolation twin is out of scope) |
| `merchant_activation` | Must be **false** / absent |
| Target Store `zid_store_id` | Must resolve to `demo` only |
| Phone | Lab phone only; purge keyed by that phone |

If any check fails → **no DB writes**, return error `lab_reset_rejected`.

### 1.2 Exact data cleared (demo + Lab phone only)

Reuse and **extend** `purge_demo_recovery_rows_for_test_phone` patterns so a Lab run starts empty. Cleared for matching Lab phone / derived `session_id` / `cart_id` / `recovery_key` on `demo`:

| Cleared | Notes |
|---------|--------|
| `AbandonedCart` (+ linked `MessageLog`, `RecoveryEvent`, `MerchantFollowupAction`) | Existing purge |
| `CartRecoveryLog` | Existing purge |
| `CartRecoveryReason` | Existing purge |
| `AbandonmentReasonLog` | Existing purge (by session) |
| `RecoverySchedule` rows for Lab `recovery_key` / sessions | **Must include** (gap in today’s purge — Lab Reset adds this, still no new tables) |
| `RecoveryTruthTimelineEvent` for Lab `recovery_key` | **Must include** for clean Signals |
| `PurchaseTruthRecord` for Lab `recovery_key` | **Must include** for clean purchase_confirmed |
| Browser: `demo_cart`, session/recovery client keys, `cartflow_converted` | Equivalent of `reset_demo=1` client wipe |

### 1.3 Exact data preserved

| Preserved | Why |
|-----------|-----|
| `Store` row `demo` | Catalog seed, settings |
| `cf_product_catalog_json` / sandbox catalog | 13 SKUs unchanged |
| All non-`demo` stores and merchants | Isolation |
| Other phones’ rows on `demo` | Only Lab phone purged |
| Schema / migrations | No production schema changes |
| Feature flags / env | Unchanged by reset |

### 1.4 Properties

| Property | How |
|----------|-----|
| Demo-only | Gate + purge filters |
| Idempotent | Second reset with same phone → empty counts / still clean |
| Safe to repeat | No merchant slug paths; no global truncate |
| Never merchant_activation | Explicit reject |
| Never real merchants | No writes where `zid_store_id != demo` |

### 1.5 Post-reset verify (must pass before Scenario 1)

- No open `AbandonedCart` for Lab phone on `demo`
- No `PurchaseTruthRecord` for Lab `recovery_key`
- No timeline events for Lab `recovery_key`
- Commerce Signals for Lab key → `[]`
- Client cart empty

---

## 2. Scenario 1 runner (`lab_v1_recovery_to_purchase`)

**Form:** One script (Playwright or API-orchestrated) — **no UI changes**.  
**Precondition:** Lab Reset succeeded; flags needed for asserts: `CARTFLOW_COMMERCE_SIGNALS_V1=1`, Pulse available on summary as in prod.

```text
Lab Reset
  → Visit
  → Product view
  → Add to cart
  → Leave (+ reason)
  → Recovery starts
  → Customer returns
  → Purchase confirmed
  → Assert success
```

### 2.1 Step contract

| Step | API / Route Used | Truth Expected | Signal Expected | Home/Pulse Expected | Cart Page Expected |
|------|------------------|----------------|-----------------|---------------------|--------------------|
| **0. Reset** | Lab Reset (compose purge + `reset_demo` client) | Lab phone rows gone on `demo` | `[]` for Lab key | N/A (or empty calm) | No Lab cart |
| **1. Visit** | `GET /demo/store?store_slug=demo&cf_test_phone=…` (no `merchant_activation`) | Store page 200; identity = Lab session/cart | none yet | unchanged | empty |
| **2. Product view** | `GET /demo/store/product/1` | PDP for `hp_pro` 449 | none required (no Traffic Signal in V1) | unchanged | empty |
| **3. Add to cart** | Client cart + optional `POST /api/cart-event` (`cart_state_sync` / abandon prep) | Line item `hp_pro` @ 449 in client (and sync if used) | none yet | unchanged | may show draft / not yet abandoned |
| **4. Leave** | `POST /api/cart-event` abandon (+ `POST /api/cartflow/reason` or recovery reason with `price` / `price_high`) + `cf_test_phone` | `AbandonedCart` exists; reason recorded; phone on session | pending until timeline | may still be quiet until schedule | active / waiting cart **449** |
| **5. Recovery starts** | Existing scheduler / arm path (same as sandbox); wait bounded | `RecoverySchedule` and/or timeline status in started set (`scheduled` / `delay_started`) | **`recovery_started`** (optional `recovery_progressed` if send occurs) | Pulse progress/brief may reflect recovery started (business language) | same active cart |
| **6. Customer returns** | Reopen `/demo/store` same identity; `cartflow_return_tracker` / passive return on `POST /api/cart-event` | Return recorded (session/return path) | optional progressed only | still not completed | cart still visible / returned |
| **7. Purchase confirmed** | Checkout COD → `POST /api/conversion` (`purchase_completed: true`, `store_slug=demo`, Lab session/cart) | Purchase Truth `purchase_detected`; recovery stop/complete path | **`purchase_confirmed`** + **`recovery_completed`** | Pulse: recovered purchase / leave; **no** require-action fork | cart **completed** / purchased |

---

## 3. Hard safety gates

Enforce at **Lab Reset** and **every runner step** (fail closed):

| Gate | Rule |
|------|------|
| Store | `store_slug` **must** equal `demo` |
| Reject non-demo | Any other `zid_store_id` / slug → abort |
| Reject merchant_activation | Query/body/context must not enable activation mode |
| No random IDs | Product, phone, price fixed; session/cart either fixed constants or single mint at reset |
| Fixed recovery_key | `demo:{session_id}` only |
| Clock | Bounded waits; no flaky “sleep forever”; no dependency on wall-clock equality |
| No cross-store writes | All POSTs include `store_slug=demo`; server coerce must not rewrite to a merchant slug |
| No new tables | Extend existing purge queries only |
| No UI changes | Runner is script/API; sandbox HTML unchanged for V1 |

---

## 4. Scenario success assertions

All must pass after step 7 (and Lab Reset before next run):

| # | Assertion |
|---|-----------|
| A1 | `purchase_confirmed` Signal exists for Lab `recovery_key` (store-scoped) |
| A2 | `recovery_completed` Signal exists for same key (started + purchase) |
| A3 | Commerce Signals payload present on summary path used by Lab verify (`commerce_signals_v1` when flag on) |
| A4 | Pulse `commerce_signals_used` truthy; what-happened reflects recovered / confirmed purchase (not internal jargon) |
| A5 | **449 SAR** visible on cart/completed surface and/or purchase amount fields for this cart (Pulse may use Commerce Language without inventing a second amount — if Pulse line lacks SAR, cart/completed amount **must** show 449) |
| A6 | Cart moved to **completed** / purchased lifecycle visibility (not active waiting) |
| A7 | No merchant **require** action remains for this cart (Pulse fork `leave` / decision no require) |
| A8 | **No duplicate** `purchase_confirmed` or `recovery_completed` for the same evidence (dedupe holds) |
| A9 | No rows written under any non-`demo` store for this run |

**Explicit non-goals for Scenario 1 asserts:** Traffic/Product Signals; Arabic copy redesign; UI layout.

---

## 5. Rollback

| Action | Effect |
|--------|--------|
| Run Lab Reset | Clears Lab phone truth on `demo` |
| Disable runner | Env/flag or simply do not invoke script — no merchant impact |
| Revert code (if shipped) | Remove Lab Reset wrapper + runner only |
| Schema | **None** — no migrations to roll back |
| Production merchants | Untouched if gates held |

---

## 6. Implementation shape (when approved — still small)

| Piece | Suggested form | Reuses |
|-------|----------------|--------|
| Lab Reset | `services/demo_lab_reset_v1.py` (or thin wrapper) + optional `POST` **demo-only** admin/dev route **or** script-only | `purge_demo_recovery_rows_for_test_phone`, timeline/purchase/schedule deletes by key, `reset_demo` client |
| Runner | `scripts/_demo_lab_v1_scenario1.py` (Playwright) | `/demo/store*`, cart-event, reason, conversion, summary probe |
| Tests | Unit: reset gates + purge scope; optional e2e marked demo-only | Existing demo tests patterns |
| Flags | No new architecture flags required beyond existing Signals/Pulse | — |

**Do not:** new demo host, new catalog service, new Signal families, merchant dashboard UI, `pvgate` merchants.

---

## 7. Delivery phases (code later)

| Phase | Deliverable | Done when |
|-------|-------------|-----------|
| **P1** | Lab Reset + gates + idempotent verify | Reset twice → clean; merchant slug rejected |
| **P2** | Scenario 1 runner steps 1–7 | Manual or scripted green on `demo` |
| **P3** | Success assertions A1–A9 | Automated pass; rollback proven |

---

## 8. Acceptance of this plan

- [x] One authoritative reset (cleared / preserved / demo-only / idempotent)  
- [x] One deterministic Scenario 1 runner  
- [x] Per-step Truth / Signal / Pulse / Cart table  
- [x] Hard safety gates  
- [x] Success assertions including 449 SAR + no duplicates  
- [x] Rollback without schema changes  
- [x] No implementation in this document  

**Next (when approved):** implement **P1 Lab Reset** only, then **P2 runner**, then **P3 asserts** — still no new demo.
