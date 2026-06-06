# Production Visual Verification (after `6c6c0db`)

**Audit UTC:** 2026-06-06T15:52:15Z  
**Target:** `https://smartreplyai.net` only — no localhost, TestClient, or isolated DB.  
**Git HEAD (local at run):** `6c6c0db` — `audit production truth before further fixes`  
**Re-run:** `python scripts/_production_visual_gate.py`  
**Machine evidence:** `scripts/_production_visual_gate_out/production_visual_gate_report.json`

---

## Deploy markers (production static assets)

| Asset | Bytes | `applyLegacyPriceSubCategoryDefault` | `CF RECOVERY FLOW COMPLETE CLOSE` | `normal_carts_partial_retry` |
|-------|------:|:--:|:--:|:--:|
| `cartflow_widget_fetch.js` | 16,291 | **YES** | — | — |
| `cartflow_widget_flows.js` | 28,074 | — | **YES** | — |
| `merchant_dashboard_lazy.js` | 104,050 | — | — | **YES** |

Production is running the fixes from `a77bdcf` + `5541e5c` bundled in `6c6c0db`.

---

## Auth & store

| Field | Value |
|-------|-------|
| Mode | Fresh signup (no env credentials) |
| Email | `cf.pvgate.1d307c0284@smartreplyai.net` |
| Store slug | `pvgate-1d307c-435a51` |

**VIP prerequisite:** Fresh merchants show threshold `500` as a **placeholder** until saved. Gate script saves VIP settings (`threshold=500`, notify enabled) before the VIP cart journey. Screenshots: `vip_flow/00_vip_settings_before_save.png`, `vip_flow/00_vip_settings_after_save.png`.

---

## A) VIP flow — one fresh cart (`#p-watch_pro`, 1299 SAR)

| Step | Result | Screenshot |
|------|--------|------------|
| 1. Add product | PASS — Horizon Steel added | `vip_flow/02_after_add_cart.png` |
| 2. Choose السعر | PASS — price reason selected | `vip_flow/05_after_price.png` |
| 3. Enter phone | PASS — `0598877660` entered | `vip_flow/06_phone_entered.png` |
| 4. Phone save succeeds | PASS — `POST /api/cartflow/reason` **200**, `sub_category: price_discount_request`, `customer_phone: 966598877660` | `vip_flow/07_after_phone_save.png` |
| 5. Widget stays closed | PASS — `suppress: 1`, no `CF V2 SHOW YESNO` after save; `08_after_22s_widget.png` shows closed shell | `vip_flow/08_after_22s_widget.png` |
| 6. VIP row appears | PASS — row in VIP tab, amount **1299** | `vip_flow/10_dashboard_final.png` |
| 7. Phone available | PASS — جوال **متوفر** ✓, `has_phone: true` | `vip_flow/10_dashboard_final.png` |
| 8. Manual contact available | PASS — **تواصل يدوي (VIP)** button + `wa.me/966598877660` href | `vip_flow/10_dashboard_final.png` |
| 9. Merchant notification path | PASS — VIP notify enabled, threshold 500 saved, alert state «سلال VIP نشطة: 2», manual path copy «أنت تراجع وتتواصل بنفسك» | `vip_flow/10_dashboard_final.png` |

| Identifier | Value |
|------------|-------|
| `cart_id` | `cf_cart_259d5330-c027-478f-9db8-c5fe98034e92` |
| `session_id` | `s_3760fe11-fc70-40ee-bdb5-ee1d2ee1e6e7` |
| `AbandonedCart.id` | 4133 |
| `cart-event is_vip` | **true** (after threshold saved) |

**Earlier failed run (same session, pre-threshold-save):** 1299 cart classified `is_vip: false` → VIP tab empty. Root cause: unsaved placeholder threshold, not phone/widget regression.

---

## B) Normal flow — one fresh cart (`#p-perfume_velvet`, 149 SAR)

| Check | Result | Evidence |
|-------|--------|----------|
| Cart in dashboard | PASS | `normal_flow/10_dashboard_final.png` — 149 ر row visible |
| Time add-to-cart → visible | **39,038 ms** (dashboard nav → DOM row) | report `normal_time_to_visible_ms` |
| API response time (isolated) | **4,204 ms** | report `normal_isolated_fetch_ms` |
| `dashboard_partial` | **false** | isolated + all boot fetches |
| `dashboard_timeout_stage` | **null** (no `payload_row` timeout) | isolated fetch |
| Count parity | **PASS** — `filter_all=3`, `table_rows_dom=3` | `normal_flow/10_dashboard_final.png` |

| Identifier | Value |
|------------|-------|
| `cart_id` | `cf_cart_037a3077-2623-4cce-b82b-05b0eeb85ec7` |
| `session_id` | `s_c7490cc4-37ba-4134-be41-289afa196bd2` |
| `AbandonedCart.id` | 4134 |
| Phone POST | **200**, `merchant_has_customer_phone: true` |
| Widget reopen | **NO** |

Screenshots: `normal_flow/01_test_widget_store.png` … `normal_flow/10_dashboard_final.png`.

---

## C) Dashboard performance audit (normal carts)

Production JSON does **not** expose server `[DASHBOARD STAGE]` spans (`candidates_loaded`, `batch_reads`, `payload_row`). Measurable production truth is **client wall time**.

| Metric | Value | Notes |
|--------|------:|-------|
| First boot `normal-carts` fetch | **8,216 ms** | Concurrent dashboard boot |
| Isolated `normal-carts` fetch | **4,204 ms** | Single request, no partial |
| DOM visibility | **39,038 ms** | Lazy boot defers table paint |
| `dashboard_partial` | false | All boot + isolated calls |
| `dashboard_timeout_stage` | null | Under 12s wall budget |
| Wall budget | 12 s | Unchanged |

**Bottleneck (inferred, no budget increase):**

1. **Server:** `batch_reads` + per-group `payload_row` loop dominate isolated ~4.2s wall time (code path in `main.py` `_merchant_light_normal_recovery_batch_api`).
2. **Client:** Concurrent dashboard boot (summary + VIP + normal-carts + followups) serializes perceived latency; first boot fetch ~8.2s while DOM paint waits ~39s.

No `payload_row` timeout observed on production after `6c6c0db` deploy.

---

## Acceptance summary

| Criterion | Status |
|-----------|--------|
| VIP flow end-to-end (visual) | **PASS** |
| Normal cart without dashboard timeout | **PASS** |
| Counts match rows | **PASS** (3 = 3) |
| No widget reopen after phone save | **PASS** (VIP + normal) |
| Production screenshots required | **PASS** — `scripts/_production_visual_gate_out/` |

```json
{ "pass": true, "failures": [] }
```

---

## Artifacts

| Path | Role |
|------|------|
| `scripts/_production_visual_gate.py` | Playwright gate (VIP threshold save + journeys) |
| `scripts/_production_visual_gate_out/vip_flow/*.png` | VIP step screenshots |
| `scripts/_production_visual_gate_out/normal_flow/*.png` | Normal step screenshots |
| `scripts/_production_visual_gate_out/production_visual_gate_report.json` | Full network/console/timing JSON |
