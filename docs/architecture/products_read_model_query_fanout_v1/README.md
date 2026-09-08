# PRODUCTS_READ_MODEL_QUERY_FANOUT_V1

**Status:** OPEN — controlled performance debt  
**Not done. Not closed. Not hidden.**

| Field | Value |
|-------|--------|
| DEBT ID | `PRODUCTS_READ_MODEL_QUERY_FANOUT_V1` |
| CURRENT BASELINE | normal = **+4** · lab = **+5** |
| OWNER | Products server read-model (`products_commercial_truth_v1`) |
| N+1 | 0 |
| AI / external / Scheduler / new table | 0 / 0 / 0 / NO |

## Why temporarily accepted

V1 / V1.1 / V1.2 are a visual + contract surface. The four (five on lab) queries are **bounded group-bys**, not N+1, and are not attached to `/api/dashboard/summary`.

This is **acceptable for this visual refinement only**. It is **not** a permanent acceptable architecture.

## Non-regression rule

Products V1.1 / V1.2 **MUST NOT** increase query count above:

- normal ≤ +4
- lab ≤ +5

If either increases: **FAIL and STOP.**

## Closure condition

Before Products is generally release-ready / scale-ready, run a dedicated query consolidation audit and either:

**A)** safely reduce the fanout, or  
**B)** prove with measured production economics that the existing bounded fanout meets CartFlow cost and latency guardrails.

Do not close this debt by adding hidden caches, duplicated snapshots, frontend aggregation, or denormalized uncontrolled JSON.

## Remasurement (V1.1 and V1.2, still OPEN)

| | Baseline | V1.1 | V1.2 |
|--|----------|------|------|
| Normal query Δ | +4 | +4 | +4 |
| Lab query Δ | +5 | +5 | +5 |
| N+1 | 0 | 0 | 0 |

No regression. Debt remains **OPEN**. No consolidation performed. V1.2 added no queries.

## Safe consolidation note (not executed in V1.1)

A later audit may consider one store-scoped SQL with grouped subqueries / CTEs for catalog + carts + purchases + hesitation (+ lab visits). That is architectural expansion and is **out of scope** for V1.1.
