# VIP Dashboard Refresh Row Stability — Task 1 Final Fix

**Date (UTC):** 2026-06-06  
**Commit message:** `fix vip dashboard refresh row stability`

---

## 1. Root cause (confirmed from audit)

| Finding | Detail |
|---------|--------|
| DB | VIP rows not lost |
| API | Eventually returns rows (`ok: true`) |
| Frontend | Full reload wipes `#ma-tbody-vip-page` to skeleton; VIP fetch was **deferred** behind `fetchNormalCarts("boot_priority")`; **no sessionStorage cache** unlike normal carts |
| User impact | ~14s window with 0 data rows after refresh |

See `docs/cartflow_vip_disappearing_rows_audit_v1.md`.

---

## 2. Files changed

| File | Change |
|------|--------|
| `static/merchant_dashboard_lazy.js` | VIP SWR cache (`ma_vip_carts_cache_v1`), `hydrateVipCartsCache` / `persistVipCartsCache`, `fetchVipCarts`, guarded `applyVipCarts`, parallel boot fetch (not blocked by normal-carts), `#vip` hash priority |
| `tests/test_dashboard_vip_refresh_stability_v1.py` | Static + shell tests |
| `scripts/_vip_refresh_stability_gate.py` | Production 3× refresh gate |
| `docs/cartflow_vip_refresh_row_stability_v1.md` | This report |
| `docs/SYSTEM_SUMMARY.md` | §10 changelog |

---

## 3. Fix summary

1. **Stale-while-revalidate:** Cache last good VIP payload in `sessionStorage`; hydrate synchronously at boot before any fetch.
2. **Independent VIP fetch:** `fetchVipCarts("boot_parallel")` or `boot_vip_hash` when `#vip` — no longer inside `fetchNormalCarts().finally()`.
3. **False empty guards:** Partial/error/`ok:false`/empty mismatch keeps `lastVipPageRows`; loading row only when no cache; `vipPageEmptyHtml` only via `renderVipCartsTables` on confirmed empty with no retained rows.
4. **Generation guard:** `vipCartsAppliedGen` prevents stale slower responses from overwriting newer paint.

---

## 4. Tests

```bash
python -m pytest tests/test_dashboard_vip_refresh_stability_v1.py tests/test_dashboard_carts_dom_stability_v1.py -q
```

**Result:** 14 passed

---

## 5. Production gate

```bash
python scripts/_vip_refresh_stability_gate.py
```

Evidence: `scripts/_vip_refresh_stability_gate_out/`

---

## 6. Before / after

| | Before | After |
|---|--------|-------|
| Post-refresh DOM | Skeleton ~14s | Cached rows immediate (<1s) |
| VIP fetch start | After normal-carts boot (~5–14s) | Parallel with boot (~0ms after hydrate) |
| Empty on transient API | `applyVipCarts` cleared to empty HTML | Retain cache + retry |

Screenshots: see gate output directory after production run.
