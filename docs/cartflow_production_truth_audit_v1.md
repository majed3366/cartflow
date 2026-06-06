# Production Truth Audit (before further fixes)

**Audit UTC:** 2026-06-06T15:35:19Z  
**Method:** Read-only. No application code changes. Playwright + HTTP fingerprinting on **local `127.0.0.1:8011`** and **production `https://smartreplyai.net`**.  
**Machine evidence:** `scripts/_production_truth_audit_out/production_truth_audit.json`  
**Re-run:** `python scripts/_production_truth_audit.py`

---

## A) Production Version Truth

### 1. Latest commit on GitHub (`main`)

| Field | Value |
|-------|-------|
| SHA | `246000d9c8e048b01e92c65419004dbd9a7f069e` |
| Short | **`246000d`** |
| Message | `fix real runtime identity phone visibility and schema drift` |
| Date | 2026-06-06T12:33:38Z |
| URL | https://github.com/majed3366/cartflow/commit/246000d9c8e048b01e92c65419004dbd9a7f069e |

### 2. Latest commit on local workstation (not on GitHub)

| Field | Value |
|-------|-------|
| SHA | `5541e5ce52a38ad6422563f4097f5d3ed307a4c2` |
| Short | **`5541e5c`** |
| **Ahead of `origin/main` by** | **2 commits** |
| Unpushed | `a77bdcf` — fix v2 price reason phone persistence |
| Unpushed | `5541e5c` — fix complete demo widget phone dashboard flow |

### 3. Latest commit actually running on smartreplyai.net

Railway UI was not API-accessible from this environment (`gh` unauthenticated). **Runtime fingerprinting** infers deployed build:

| Asset (production) | Bytes | Marker: `applyLegacyPriceSubCategoryDefault` (commit `a77bdcf`) | Marker: `CF RECOVERY FLOW COMPLETE CLOSE` (commit `5541e5c`) | Marker: `normal_carts_partial_retry` (commit `5541e5c`) |
|--------------------|------:|:--:|:--:|:--:|
| `cartflow_widget_fetch.js` | 15,376 | **NO** | — | — |
| `cartflow_widget_flows.js` | 27,303 | — | **NO** | — |
| `merchant_dashboard_lazy.js` | 103,473 | — | — | **NO** |

| Asset (local `5541e5c` on `:8011`) | Bytes | Same markers |
|------------------------------------|------:|:--:|:--:|:--:|
| `cartflow_widget_fetch.js` | 16,291 | **YES** | — | — |
| `cartflow_widget_flows.js` | 28,074 | — | **YES** | — |
| `merchant_dashboard_lazy.js` | 107,171 | — | — | **YES** |

**Inferred production deploy SHA:** **`246000d` or equivalent** (matches GitHub `main`, lacks both unpushed fix commits).

### 4. Mismatch explanation

| Layer | SHA / state | Notes |
|-------|-------------|-------|
| GitHub `main` | `246000d` | Latest **pushed** commit |
| Local git | `5541e5c` (+2 unpushed) | Agent-reported fixes **`a77bdcf`** and **`5541e5c`** never reached GitHub/Railway |
| Railway ACTIVE (user report) | Older than local fixes | Consistent with production static assets missing `a77bdcf` / `5541e5c` markers |
| smartreplyai.net runtime | ≈ `246000d` | Phone POST for `reason=price` returns **`400 sub_category_required_or_invalid`** — exact failure mode fixed in **`a77bdcf`** but not deployed |

**Screenshots**

- Production login wall (no dev dashboard bypass): `scripts/_production_truth_audit_out/production/D_dashboard_carts.png`
- Local dashboard after journey: `scripts/_production_truth_audit_out/local_8011/D_dashboard_carts.png`

---

## B) VIP Truth Audit (one brand-new cart each)

### Production (`smartreplyai.net`)

| Field | Value |
|-------|-------|
| `cart_id` | `cf_cart_1725ef76-ff17-46ed-baec-91f225b2de2c` |
| `session_id` | `s_464f5929-f22a-43a0-b3dc-8bcd35eb520e` |
| `recovery_key` | `demo:cf_cart_1725ef76-ff17-46ed-baec-91f225b2de2c` |

| Step | Result | Evidence |
|------|--------|----------|
| 1. Phone received (widget UI) | YES | User entered `0598877660` in phone_optional view |
| 2. Phone saved (API) | **NO** | `POST /api/cartflow/reason` → **400** |
| 3. Phone persisted in DB | **Not verified** (no DB access on Railway) | Request lacked `sub_category` |
| 4. VIP dashboard row | **Not reachable** | `/dashboard` → login page (no dev bypass in production) |
| 5. Manual contact decision | **N/A** | Dashboard API not captured (auth required) |

**Failed request body (production):**

```json
{
  "store_slug": "demo",
  "session_id": "s_464f5929-f22a-43a0-b3dc-8bcd35eb520e",
  "reason": "price",
  "merchant_activation": false,
  "customer_phone": "966598877660"
}
```

**Response:**

```json
{ "ok": false, "error": "sub_category_required_or_invalid" }
```

**Console:**

```
[CF REASON_PHONE_SAVE_START V2] {reason_key: price}
[CF SHELL MINIMIZE] {mode: launcher}
[CF REASON_PHONE_SAVE_FAILED V2] {trace: server_reject}
```

### Local (`127.0.0.1:8011`, commit `5541e5c`)

| Field | Value |
|-------|-------|
| `cart_id` | `cf_cart_cf4e0f71-3ff1-4945-a756-2a326cda5b73` |
| `session_id` | `s_9eb4a22b-0d11-4bfe-8277-e38ca9517e0e` |
| `recovery_key` | `demo:cf_cart_cf4e0f71-3ff1-4945-a756-2a326cda5b73` |
| `AbandonedCart.id` | **24** |
| `customer_phone` (DB) | **966598877660** |

| Step | Result |
|------|--------|
| Phone POST | **200** with `sub_category: price_discount_request` |
| DB phone | **966598877660** |
| Normal carts row | `merchant_has_customer_phone: true`, `merchant_phone_line_ar: رقم العميل متوفر` |
| VIP API row match | `vip_count: 0` in captured response (cart is VIP lane; dev bypass session did not return vip rows in this capture window) |

### Why production still shows «لا يوجد رقم عميل متاح»

**Proven chain on production:**

1. V2 price path posts `reason=price` **without** `sub_category` (no `applyLegacyPriceSubCategoryDefault` in deployed `cartflow_widget_fetch.js`).
2. API rejects with **`sub_category_required_or_invalid`** → phone **never** written to `AbandonedCart.customer_phone`.
3. VIP projection reads empty phone → `has_phone=false` → UI copy **`لا يوجد رقم عميل متاح`** and manual contact unavailable.

This is **not** a projection-only bug on production; it is **phone save rejected at API** on the deployed build.

---

## C) Normal Carts Truth Audit

### Production

- Dashboard requires merchant login → **no** `/api/dashboard/normal-carts` JSON captured in browser session.
- Screenshot: login page (`production/D_dashboard_carts.png`).

### Local (`5541e5c`) — timed network captures

| # | `dashboard_partial` | `dashboard_timeout_stage` | rows returned | Notes |
|---|:--:|-------------------------:|:--:|-------|
| 1 | true | `payload_row` | 9 | First boot fetch under concurrent dashboard load |
| 2 | true | `candidates_loaded` | 16 | Retry / second fetch; flag still true |

**Wall budget in response:** `dashboard_wall_budget_s: 12.0` (commit `5541e5c` server guard).

**UI timing:** Screenshot at 12s on `#carts?tab=all` still shows empty placeholder `...` and filter chips **(0)** — **delayed paint / partial-first race** remains observable even with retry logic.

**Exact delay stages (server logs from prior runs on `:8011`):**

```
[DASHBOARD STAGE] stage=candidates_loaded elapsed_ms=561.7
[DASHBOARD STAGE] stage=batch_reads_done elapsed_ms=3067.0
[DASHBOARD STAGE] stage=payload_rows_start elapsed_ms=3067.3
[DASHBOARD STAGE] stage=payload_rows_done elapsed_ms=6718.6
```

Under concurrent boot (summary + normal-carts + vip + messages + followups + widget_panel), first `normal-carts` request can exceed cooperative deadline at **`payload_row`** or **`candidates_loaded`**, returning `dashboard_partial=true` before row loop completes.

---

## D) Widget Lifecycle Truth Audit

### Local (`5541e5c`) — PASS for reopen

```
[CF REASON_PHONE_SAVE_SUCCESS V2]
[CF RECOVERY FLOW COMPLETE CLOSE]
[CF SHELL MINIMIZE]
```

After 22s: `suppress: "1"`, **no** `[CF V2 SHOW YESNO]` after phone success.  
Exit intent after close: **`recently_dismissed`** (blocked).

### Production (`≈246000d`) — unstable / incomplete close

```
[CF REASON_PHONE_SAVE_FAILED V2] {trace: server_reject}
[CF SHELL MINIMIZE]   ← minimize without recovery-flow finalize
```

After phone attempt: `suppress: null` ( **`markWidgetDismissed` / recovery finalize not in deployed flows.js** ).

At ~20s after add-to-cart:

```
[CF HESITATION TIMER FIRED] {hesitation_after_seconds: 20, ...}
[CF V2 SHOW NOW]
[CF TRIGGER FIRED] {source: add_to_cart, timer: hesitation_anchor}
[CF HESITATION DISPATCH] ...
[CF SHELL EXPAND] {}
[CF V2 SHOW CONTINUATION]   ← widget re-surfaces (not YESNO, but flow reopens)
```

| Question | Production answer |
|----------|-------------------|
| Does widget close? | Minimizes launcher after failed save |
| Does it reopen? | **YES** — hesitation anchor fires; shell expands to continuation |
| Timer | `hesitation_anchor` (20s `after_cart_add`) |
| Function | `fireCartRecoveryAfterHesitation` → `Hooks.fireCartRecovery("cart_hesitation_timer")` |
| Why suppress failed | Phone save failed → old `gracefulCloseWidget()` path (no timer clear, no `cartflow_cf_suppress_after_dismiss`) |

---

## E) Cost Accountability

| Commit | Claimed fix | Verified working (where) | Still broken (where) | Root cause |
|--------|-------------|--------------------------|----------------------|------------|
| `2bda097` | Archive destination + VIP phone prefers `AbandonedCart.customer_phone` | Code present on `246000d` | VIP «لا يوجد رقم» on **production** | Upstream phone never saved when price POST lacks `sub_category` |
| `19d006a` | Warm path offline; demo phone/cart visibility | TestClient + local dev DB | **Production** manual flow | Fixes on GitHub `main` but phone price path still broken without `a77bdcf`; production DB/API not exercised in tests |
| `246000d` | Canonical `recovery_key` on `cart_id` | GitHub `main`, production ≈ this SHA | VIP phone on production | Identity fix does not add price `sub_category` default |
| `a77bdcf` | V2 price `sub_category=price_discount_request` fallback | **Local only** (unpushed) | **Production** | **Never deployed** — production `fetch.js` lacks `applyLegacyPriceSubCategoryDefault` |
| `5541e5c` | Widget reopen suppress + dashboard 12s budget + partial retry | **Local only** (unpushed) | **Production** widget + dashboard | **Never deployed** — production static assets lack markers |

**Why tests passed but manual failed**

| Pattern | Detail |
|---------|--------|
| Tests ≠ production deploy | `a77bdcf` / `5541e5c` committed locally, **not pushed**; Railway still on `246000d` |
| Tests ≠ browser | TestClient skips hesitation timer, sessionStorage, concurrent dashboard boot |
| Tests ≠ merchant auth | Production dashboard needs login; dev bypass only on `ENV=development` |
| Tests used aligned payloads | E2E sends `sub_category` explicitly; production V2 UX path omits it without `a77bdcf` |

---

## Verdict (audit only — no fixes in this document)

**Primary production gap:** GitHub/Railway/smartreplyai.net are on **`246000d`**. Reported fixes **`a77bdcf`** (phone save) and **`5541e5c`** (widget lifecycle + dashboard partial handling) exist **only on the local workstation** and were **never pushed**.

Manual symptoms match undeployed code:

- VIP no phone → production `400 sub_category_required_or_invalid`
- Widget reappears → production lacks recovery-flow timer suppress (`5541e5c`)
- Dashboard empty/delayed → production lacks partial retry + 12s budget (`5541e5c`)

**Next step (out of scope for this audit):** Push `a77bdcf` + `5541e5c` to `main`, confirm Railway ACTIVE SHA, re-run this audit script against production.
