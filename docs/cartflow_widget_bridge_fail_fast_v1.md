# Widget Fast Path V1 — Bridge Ensure Fail-Fast Repair

**Status:** REPAIR APPLIED — production acceptance pending  
**Date (UTC):** 2026-07-11  
**Runtime:** `v2-widget-bridge-fail-fast-v1`

---

## Root cause branch removed

`ensureCartTruthBeforeReason` previously called `readAndPersist({ source_hint: "ensure_before_reason", allowFreshAfterInFlight: true })`, which:

1. Marked the call as a **priority** trigger  
2. **Awaited** any in-flight cart-event POST, then re-ran  
3. Could also run a full cart-event POST on the reason critical path  

Prod evidence (invest V1): **bridge_ensure P50 ≈ 3391 ms** — first over-budget stage.

---

## Smallest repair

| Path | Behavior |
|------|----------|
| `cart_persisted` | Return immediately (`already_persisted`) |
| Stable session + (cart id \| last normalized \| prior post ok) | Return immediately; schedule **non-blocking** bg persist (`ensure_before_reason_bg`) after reason can start |
| Session only | Same — reason scopes by `store_slug` + `session_id` |
| No session | `missing_identity` → widget retry error (no wait) |

Also removed `ensure_before_reason` from `isPriorityAddTrigger` so bg hints never chain-wait.

**Not changed:** empty-retry ladder for normal add flows, phone save path, lifecycle, persistence semantics, persist-then-advance.

---

## Safety

- Event durability: background `readAndPersist` still scheduled (coalesce, not await)  
- Identity: reason still uses stable session (+ cart_id when available)  
- Orphan flag retained when cart not yet persisted  
- Duplicate reason writes: in-flight lock unchanged  
- Missing identity: clear retry UI  

---

## Acceptance targets

| Metric | Target | Before |
|--------|--------|--------|
| bridge_ensure P50 | &lt;100 ms | 3391 ms |
| reason → phone P50 | &lt;500 ms | 6346 ms |

Probe: `scripts/_widget_bridge_fail_fast_v1_prod.py`
