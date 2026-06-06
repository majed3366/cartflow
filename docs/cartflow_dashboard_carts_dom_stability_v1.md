# Dashboard Carts DOM Visibility & Stability Fix

**Date (UTC):** 2026-06-06  
**Commit:** `fix dashboard carts dom visibility stability`  
**Before baseline:** production gate `normal_time_to_visible_ms = 39,038` (isolated API ~4,204 ms)

---

## Root causes

### 1) 39s DOM visibility

| Factor | Effect |
|--------|--------|
| **Concurrent boot** | `bootLazyDashboard` fired 6 parallel API calls; `normal-carts` competed with `summary`, `vip-carts`, `messages`, etc. |
| **Refresh-token race** | `checkRefreshState` (5s interval) detected token drift during boot → `refreshCoreSections` re-fetched all sections while boot still in flight |
| **No fetch generation guard** | Slower/stale `normal-carts` responses could be ignored or superseded unpredictably |
| **Table paint deferred** | Rows only rendered when `applyNormalCarts` ran; partial-empty responses returned early without loading UI |
| **Isolated API ~4s vs DOM ~39s** | Server path is ~4s; client perceived latency was refresh duplication + late first successful paint |

### 2) Disappearing rows / false empty

| Factor | Effect |
|--------|--------|
| **Partial empty payload** | `dashboard_partial=true` + `merchant_carts_page_rows=[]` skipped render (retry only) — but a **later** full empty or stale response could still replace table |
| **No row retention** | `applyNormalCarts` always wrote empty-state HTML when `pageRows.length === 0` |
| **Count/row mismatch** | Empty API body with `filter_all > 0` cleared visible rows |
| **Concurrent refresh** | Token-changed refresh could deliver partial empty while user saw rows |

---

## Fix (frontend only — `static/merchant_dashboard_lazy.js`)

1. **`fetchNormalCarts` + generation counter** — stale responses skipped (`normal_carts_stale_skip`).
2. **Never clear rows on partial/timeout empty** — keep `lastNormalCartsPageRows`, schedule retry.
3. **Loading state** — `جاري تحميل السلال…` skeleton instead of «لا توجد سلال» during fetch/partial.
4. **Empty mismatch guard** — if `filter_all > 0` but rows empty, retry instead of empty state.
5. **Boot priority** — `fetchNormalCarts("boot_priority")` first; secondary sections after; suppress `checkRefreshState` refresh until boot completes.
6. **Defer token refresh** — skip `refreshCoreSections` while `merchantRefreshInFlight` or boot incomplete.

---

## Tests

`tests/test_dashboard_carts_dom_stability_v1.py` — JS regression guards + API count parity + shell skeleton.

---

## Verification

Re-run: `python scripts/_production_visual_gate.py`

Acceptance:
- 3 consecutive `#carts?tab=all` loads with rows visible
- No false empty state
- `filter_all === DOM rows`
- `time_to_visible_ms` materially below 39,038 ms

Evidence: `scripts/_production_visual_gate_out/stability/`

---

## Production verification (`7539e30` on smartreplyai.net)

| Metric | Before | After |
|--------|-------:|------:|
| Dashboard reload DOM visibility (3 runs) | ~39,038 ms (first paint) | **17.6 – 26.2 ms** |
| Isolated `normal-carts` API | ~4,204 ms | **3,685 – 3,819 ms** |
| False empty «لا توجد سلال» | intermittent | **none** (3/3 runs) |
| Count parity `filter_all` = DOM rows | mismatch risk | **3 = 3** (3/3) |
| `dashboard_partial` empty overwrite | yes | **no** |
| Deploy marker `boot_priority` | absent | **present** |

Screenshots: `scripts/_production_visual_gate_out/stability/stability_load_1.png` … `_3.png`

**Note:** Fresh cart after widget journey may still take longer to appear in the API row set until `merchant_dashboard_refresh_token` advances (server-side). Reload stability and existing-row retention are fixed; token-triggered `fetchNormalCarts` added for faster new-cart pickup.
