# Commercial Decision Intelligence V1 — Phase 1 Observe Sheet

**Lab:** `/dev/revenue-reality-validation`  
**Base:** Revenue Intelligence Model V1 on RRV  
**Date (UTC):** 2026-09-02  
**Code changes before this sheet:** none  

## Mission A — Discount / margin protection

| Field | Current |
|-------|---------|
| Evidence | Promo days: purchases 86, revenue ~11000; SIMULATION-ONLY contribution −2408 vs non-promo +6020; conversion up, economics worse; cost labeled SIMULATION-ONLY |
| Diagnosis | Raising conversion via discount weakens simulated economics |
| Recommendation | Stop current discount or replace with offer that doesn’t crush simulated contribution |
| Measurement | After stop: purchase conversion, revenue, simulated contribution if present |
| Recheck | After 14 days; reopen if conversion pressure returns without revenue improvement |

**Gaps**

- Generic: “stop or redesign” without choosing *which* redesign and why it beats a bare stop
- Shallow: little on eligibility / duration / segment alternatives
- Language risk: “هامش” / margin-ish wording must not imply production margin truth
- Priority: urgency is clear; economics explanation can be sharper (active leakage now)
- Unsupported stronger actions: real margin claim, permanent price change, invented uplift

## Mission B — Argan discovery / merchandising

| Field | Current |
|-------|---------|
| Evidence | Views 567 vs peers ~2274; add-to-cart when seen 28% vs ~13.7%; purchase after add 43.4%; revenue despite scarcity ~13550 |
| Diagnosis | Discovery/distribution opportunity — not immediate price problem |
| Recommendation | Test homepage + category emphasis 7–14 days before any price change |
| Measurement | Views, cart adds, purchases, product revenue vs 30-day baseline |
| Recheck | After 14 days or ~+40% views with stable add quality |

**Gaps**

- Still slightly dual (“homepage and category”) — need ONE bounded placement experiment
- Must state explicitly: problem is reach, not persuasion
- Must reject price cut and ad-channel leap without channel evidence for this product
- Merchant language still slightly metric-list on measure line

## Mission C — TikTok vs Google

| Field | Current |
|-------|---------|
| Evidence | TikTok: views 2893, add 21.7%, purchase/add 33.6%, avg order ~176; Google: views 1289, add 8.2%, purchase/add 0.0%, avg order 0; simulation-only, not category law |
| Diagnosis | Channel quality differs for this product in sample |
| Recommendation | Limited acquisition share test TikTok vs search control |
| Measurement | Per channel: adds, purchases, avg order, revenue |
| Recheck | 14 days or sample under threshold → stop |

**Gaps**

- Still reads as soft “try TikTok” without exact commercial hypothesis
- Mentions “budget” without supported budget truth — remove
- Must emphasize *this store / this product* quality gap, not “TikTok is better”
- Priority currently للمراقبة — OK for urgency vs discount leakage, but decision text must be distinctive

## Priority economics (among the three)

1. **A Discount** — active commercial motion may be leaking value *now*  
2. **B Discovery** — growth option, reversible merchandising test, less urgent than active leakage  
3. **C Channel** — bounded acquisition test; do not outrank active leakage or clear merchandising under-reach without ad spend truth  

## Laws check (observe)

- No recommendation without evidence: hold  
- No revenue claim without measurement: hold; sim-only contribution must stay labeled  

## Next

Controlled minimal implementation: distinctive commercial decision packs for A/B/C only; Home/Workspace language; falsifiers; founder capture.
