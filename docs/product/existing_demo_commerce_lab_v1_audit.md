# Existing Demo → Commerce Lab V1 Audit

**Status:** Audit only (no implementation)  
**Date (UTC):** 2026-07-10  
**Scope:** Existing Commerce Sandbox (`/demo/store*`) only — do **not** create a new demo  
**Out of scope:** Code, new architecture, production merchant data changes, new product families

> **Law:** Reuse before adding. Upgrade the sandbox into a **Commerce Lab** — a repeatable, resettable, deterministic place to prove Truth → Signals → Pulse → merchant language.  
> Do not invent a second application.

**Canonical today:** `docs/SYSTEM_SUMMARY.md` §3.2.1 · catalog `services/demo_sandbox_catalog.py` · UI `templates/demo_store.html`

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Is there already a demo? | **Yes** — Commerce Sandbox v1 |
| Can it become a Commerce Lab without a new demo? | **Yes** — with a thin scenario + reset contract on top of existing assets |
| Smallest safe path? | **Reuse** catalog + storefront + real APIs; **add** one deterministic scenario runner and one authoritative reset; **do not** share Lab runs with real merchant slugs |

---

## 2. Current demo inventory

### 2.1 Storefront & routes

| Asset | Location | Role |
|-------|----------|------|
| Store UI | `templates/demo_store.html` | Catalog grid, PDP, cart, COD checkout |
| Public sandbox | `GET /demo/store*` | Default `store_slug=demo`, cart key `demo_cart` |
| Isolation twin | `GET /demo/store2*` | `demo2` / `demo2_cart` |
| Merchant test path | `GET /dashboard/test-widget` → `/demo/store?store_slug={merchant}&merchant_activation=1&reset_demo=1` | Same UI, **merchant’s** Store row |
| Demo panel APIs | `routes/demo_panel.py` (`/demo/cartflow/*`) | Sequence preview, WA preview, last logs (`demo`/`demo2` only) |
| Guide / panel JS | `static/cartflow_demo_guide.js`, `cartflow_demo_panel.js` | Guide + scenario helpers; panel DOM largely orphaned |

### 2.2 Catalog (products & prices)

Source: `services/demo_sandbox_catalog.py` — **13 SKUs**, picsum images, related/cheaper keys. Seeded into `Store.cf_product_catalog_json` for `demo`/`demo2` via `services/cartflow_demo_catalog_seed.py`.

| Key | Name (short) | Price (SAR) |
|-----|--------------|-------------|
| `hp_pro` | TrueSound Pro headphones | 449 |
| `earbuds` | TrueSound earbuds | 199 |
| `hp_air` | TrueSound Air | 119 |
| `hp_stick` | SoundStick wired | 59 |
| `watch_pro` | Horizon Steel watch | 1299 |
| `watch_sport` | Pulse Sport watch | 449 |
| `perfume` | Amber Oud | 289 |
| `perfume_velvet` | Velvet Musk | 149 |
| `charger` | Nano 20W charger | 75 |
| `watch_band` | Raven watch band | 85 |
| `wallet` | Mira travel wallet | 65 |
| `hoodie_essentials` | Essentials hoodie | 89 |
| `hoodie` | Luxe hoodie | 149 |

Default scenario seed today: **`hp_pro` (449)** via `cartflowStartDemoScenario`.

### 2.3 Carts, customers, visits/events

| Capability | Today |
|------------|--------|
| Carts | Browser `localStorage` + real `AbandonedCart` via `POST /api/cart-event` |
| Customers | Phone string only (`cf_test_phone` / `CARTFLOW_DEMO_TEST_PHONE`); no named personas |
| Visits | No first-class page-view log; return via `cartflow_return_tracker.js` → cart-event |
| Widget | V2 forced on `/demo/store*`; reason capture → recovery arm |
| WhatsApp / recovery | **Real** scheduler + logs (mock or live send by env) |
| Purchase | Checkout COD / panel → `POST /api/conversion` (`purchase_completed: true`) → Purchase Truth |

### 2.4 Reset tools (multiple, overlapping)

| Tool | Scope | Notes |
|------|-------|-------|
| `?reset_demo=1` | Browser identity (+ server IDs); `demo` or merchant_activation | `services/demo_store_reset_demo.py` — **not** on store2 |
| `?fresh=1&cf_test_phone=` | DB purge for phone on `demo`/`demo2` | `services/demo_pi_fresh_session.py` (legacy-tagged) |
| `POST /api/test-widget/new-lifecycle` | Merchant test-widget fresh keys | Production merchant slug |
| Panel `resetDemoSession` | Client reload | Orphaned UI |

### 2.5 Isolation reality

- **Same production DB tables** as merchants; isolation is **row-level** by `store_slug` / `zid_store_id`.
- `demo` / `demo2` are real `Store` rows (auto-provisioned).
- Merchant activation writes to the **merchant** Store — not `demo`.
- Production startup **skips resume** of sandbox schedules; it does **not** stop new demo abandons from scheduling.
- `cf_test_phone` override in production: **`demo` only** (not `demo2`).

---

## 3. Gap table

| Capability | Exists Today? | Reusable? | Missing Piece | Risk |
|------------|---------------|-----------|---------------|------|
| Multi-page storefront | Yes | **Yes** | — | Low |
| Static catalog (13 SKUs) | Yes | **Yes** (trim roles, don’t rebuild) | Lab role tags on 6–10 SKUs | Low |
| Mixed prices | Yes | **Yes** | Explicit Lab role map | Low |
| Real cart-event / abandon | Yes | **Yes** | Deterministic fixed IDs for Lab run | Medium if IDs collide |
| Widget reason → recovery | Yes | **Yes** | Scripted leave + reason | Medium (real schedules) |
| Return-to-site | Partial | **Yes** | Explicit “return” step in scenario | Low |
| Purchase / Purchase Truth | Yes | **Yes** | Fixed conversion after return | Medium (truth rows) |
| Commerce Signals on summary | Yes (flagged) | **Yes** | Lab must produce Recovery/Purchase facts | Low |
| Merchant Pulse / Home | Yes | **Yes** | Language must follow Commerce Language | Low |
| Cart page visibility | Yes | **Yes** | Assert completed/archived after purchase | Low |
| Page-view / visit truth | **No** | N/A | Optional thin “view” event **or** treat PDP open as visit for V1 | Low if deferred |
| Named customer personas | **No** | N/A | Not required for scenario 1 (phone enough) | — |
| Single authoritative reset | **No** | Partial pieces | One Lab reset = browser + demo-slug DB + no merchant slug | **High** if wrong slug |
| Deterministic scenario runner | **No** | Panel helpers partial | One ordered script: Visit→…→Purchase | Medium |
| Demo panel UI | Broken/orphan | JS reusable | Restore or drop; don’t block Lab | Low |
| Isolation from real merchants | Partial | Strengthen | Lab runs **only** on `demo` (or dedicated lab slug later) — never merchant_activation | **High** if ignored |
| Non-random data | Mostly | **Yes** | Freeze product, phone, amounts, timings | Low |
| Production truth mutation outside demo | Possible today | Constrain | Forbid Lab on merchant slugs; document no `pvgate` in Lab | **High** |

---

## 4. Minimum realistic catalog (reuse current demo)

**Do not add SKUs.** Assign Lab roles to **8** existing products (hide or ignore the rest in Lab docs/UI later if needed).

| Role | Key | Price | Why this SKU |
|------|-----|-------|--------------|
| **Strong conversion** | `earbuds` | 199 | Mid price, clear value, easy complete |
| **High interest / low purchase** | `watch_pro` | 1299 | High attention, hesitation-prone |
| **Price-sensitive** | `hp_pro` | 449 | Already default abandon + cheaper alts (`earbuds` / `hp_air`) |
| **Shipping-sensitive** | `perfume` | 289 | Physical goods; natural shipping objection |
| **Low traffic** | `wallet` | 65 | Accessory; rarely the hero |
| Mixed mid | `watch_sport` | 449 | Alternate mid cart |
| Mixed low | `charger` | 75 | Add-on / basket filler |
| Mixed apparel | `hoodie` | 149 | Non-electronics diversity |

**Scenario 1 product (fixed):** `hp_pro` @ **449 SAR** (already wired; cheaper alternatives exist).  
**Do not randomize** product, price, or phone for scenario 1.

---

## 5. First deterministic scenario (only)

**Name:** `lab_v1_recovery_to_purchase`  
**Store:** `demo` only  
**Product:** `hp_pro` (449 SAR)  
**Customer:** fixed `cf_test_phone` (env `CARTFLOW_DEMO_TEST_PHONE` or canonical QA phone)  
**No randomness.** Same steps every run.

```text
1. Visit          → open /demo/store?reset_demo=1&cf_test_phone=…
2. Product view   → /demo/store/product/{hp_pro num}
3. Add to cart    → add hp_pro
4. Leave          → abandon (+ reason price) → recovery starts
5. Recovery starts→ schedule / timeline fact exists (started)
6. Customer returns → return-to-site / reopen store with same identity
7. Purchase confirmed → checkout COD → POST /api/conversion
```

### 5.1 Expected changes (contract)

| Layer | After leave / recovery start | After return | After purchase |
|-------|------------------------------|--------------|----------------|
| **Operational truth** | `AbandonedCart` + reason; `RecoverySchedule` / timeline **started** (and progressed if send occurs) | Return recorded (passive return / session) | Purchase Truth `purchase_detected`; recovery stop / completed path |
| **Commerce Signals** | `recovery_started` (± `recovery_progressed`) | (optional progressed) | `purchase_confirmed` + `recovery_completed` when started+purchase |
| **Merchant Pulse / Home** | Progress / brief may show recovery started (Commerce Language) | Still open cart / attention as applicable | Leave-friendly: purchase recovered — **not** “CartFlow completed…” |
| **Cart page** | Active / waiting cart for `hp_pro` 449 | Same cart visible / returned | Completed / purchased / archived per lifecycle rules |
| **Completed state** | Not completed | Not completed | Completed via Purchase Truth |
| **Merchant-facing language** | “A customer left a 449 SAR cart” / recovery started in business terms | “The customer returned” | “A purchase worth 449 SAR was recovered” (Commerce Language Foundation) |

**Forbidden on surfaces:** Signal, Truth, Evidence, Confidence, Lifecycle, Decision Class, recovery_key, pipeline jargon.

---

## 6. Isolation & safety (must hold)

| Rule | How |
|------|-----|
| Demo data cannot affect real merchants | Lab scenario **only** `store_slug=demo` (optionally verify `demo2` isolation separately). **Never** run Lab under `merchant_activation=1`. |
| Repeatable | Fixed product, phone, reason (`price`), ordered steps, no random UUIDs in the **contract** (generated IDs allowed if reset clears them). |
| Resettable | One Lab reset before each run (below). |
| No random data | No random catalog picks; no random amounts. |
| No production truth mutation outside demo scope | No writes to merchant `zid_store_id`; no `pvgate` signup merchants as part of Lab; purge only `demo`/`demo2` rows for the Lab phone. |

---

## 7. Reset strategy (authoritative for Lab)

**Goal:** One button/script meaning “Lab ready” — compose existing tools; do not invent a second DB.

**Lab Reset V1 (proposed contract — not implemented):**

1. **Scope gate:** refuse unless `store_slug ∈ {demo, demo2}` (Lab default: `demo`).  
2. **Browser:** equivalent of `reset_demo=1` (clear cart key, session/recovery client keys, converted flag).  
3. **Server:** purge recovery rows for Lab phone on that slug only (`purge_demo_recovery_rows_for_test_phone` pattern).  
4. **Identity:** mint fresh `session_id` / `cart_id` / `recovery_key` pair.  
5. **Verify empty:** no open Lab cart for that phone; Signals empty or pre-scenario baseline.

Deprecate parallel resets for Lab docs: prefer this path over ad-hoc `fresh=1` vs panel vs new-lifecycle mix.

---

## 8. Reuse plan

| Keep as-is | Thin upgrade | Do not do |
|------------|--------------|-----------|
| `demo_store.html` + routes | Scenario runner script/docs binding existing APIs | New demo app / new host |
| `demo_sandbox_catalog.py` | Role map for 8 SKUs (metadata/docs first) | New catalog system |
| Real cart-event / conversion / recovery | Fixed step order + asserts | Fake parallel Truth store |
| Signals + Pulse flags | Assert Signal types + Pulse language | New architecture layers |
| `demo` / `demo2` slug isolation | Lab = `demo` only | Merchant-activation Lab runs |
| Existing purge/reset pieces | Unify into Lab Reset | Broad production wipes |

---

## 9. Missing pieces (minimal)

1. **Scenario contract runner** (deterministic steps + pass/fail asserts).  
2. **Lab Reset** (single entry composing existing purge + browser reset).  
3. **Catalog role map** (docs → later optional display tags).  
4. **Optional:** restore or remove orphaned demo panel DOM (clarity only).  
5. **Optional V1.1:** explicit product-view event if visit must be Truth-backed (not required if PDP open is accepted as Visit for scenario 1).

---

## 10. Implementation phases (later — not this doc)

| Phase | Outcome | Safe because |
|-------|---------|--------------|
| **P0 — Contract** | This audit accepted; Lab = `demo` only | Docs only |
| **P1 — Reset** | One Lab Reset path on `demo` | Reuses purge + `reset_demo` |
| **P2 — Scenario 1** | Automated Visit→…→Purchase with asserts on Truth / Signals / Pulse / carts / language | No new architecture |
| **P3 — Catalog roles** | 8-SKU role map visible in Lab docs (and optionally UI badges) | No new SKUs |
| **P4 — Harden isolation** | Guardrails refusing Lab tools on merchant slugs | Prevents prod merchant pollution |

---

## 11. Acceptance for this audit

- [x] Current demo assets inventoried  
- [x] Gap table with reuse / missing / risk  
- [x] 6–10 product Lab catalog from **existing** SKUs  
- [x] One deterministic scenario defined  
- [x] Expected Truth / Signals / Pulse / carts / language documented  
- [x] Isolation + reset strategy stated  
- [x] Phases listed — **no code in this document**

**Next (when approved):** implement P1 Reset + P2 Scenario 1 only — still no new demo.
