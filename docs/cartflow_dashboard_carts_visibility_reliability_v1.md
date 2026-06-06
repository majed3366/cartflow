# Dashboard Carts Visibility Reliability

**Commit:** `fix dashboard carts visibility reliability`

## Root causes

### Old/existing carts sometimes missing until refresh

1. **Stale-response discard bug:** `applyNormalCarts` rejected any response where `fetchGen !== normalCartsFetchGen`. A slower successful boot response was discarded when a faster retry/token fetch had already incremented the generation counter — API returned rows but DOM never updated.

2. **No instant paint on reload:** Empty skeleton shown until network completed; slow/partial responses left table blank even when session had prior rows.

3. **Token refresh deferred without refetch:** `checkRefreshState` skipped token update when `merchantRefreshInFlight`, so subsequent polls never aligned.

4. **Hash navigation without re-render:** Navigating to `#carts?tab=all` did not re-apply in-memory rows or filters.

### New cart delay

1. Same stale-generation race after `refreshCoreSections` / token refetch.
2. Refresh token advanced server-side but dashboard only polled every 5s via `refresh-state`.
3. No targeted poll for `sessionStorage.cartflow_cart_event_id` after widget flow.

## Fix (`static/merchant_dashboard_lazy.js`)

| Mechanism | Purpose |
|-----------|---------|
| `normalCartsAppliedGen` | Only skip responses **older than last successful apply** |
| `hydrateNormalCartsCache` + `persistNormalCartsCache` | Stale-while-revalidate on boot |
| `rerenderCartsFromMemory` on partial/empty mismatch | API degraded but DOM keeps valid rows |
| `scheduleNormalCartsTokenRefetch` | Token change → `fetchNormalCarts` (not full section storm) |
| `startPendingNewCartWatcher` | Poll until new `cart_id` appears |
| `syncCartsPageOnHashChange` | Re-render on `#carts` navigation |
| `visibilitychange` + 2.5s refresh poll | Faster pickup after tab focus |

## Verification

`python scripts/_production_visual_gate.py`

Evidence: `scripts/_production_visual_gate_out/stability/`, `new_carts/`
