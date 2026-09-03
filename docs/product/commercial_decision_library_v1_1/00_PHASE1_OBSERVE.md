# Commercial Decision Library V1.1 — Phase 1 Observe Map

**Lab:** `/dev/revenue-reality-validation`  
**Base:** Commercial Decision Intelligence V1 on RRV  
**Date (UTC):** 2026-09-03  
**Code changes before this sheet:** none  

## Simulation truth classification

| Source | Classification | Notes |
|--------|----------------|-------|
| A. product-pair purchase relationships | DIRECT_TRUTH (sim) | `relationships.retention_sequences` A→B propensity 31% vs baseline ~6% |
| B. cart co-occurrence | DIRECT_TRUTH (sim) | A+B together 78 / 206 orders with A; strength=strong |
| C. shipping hesitation reasons | DIRECT_TRUTH (sim) | P02 hesitation: shipping 291, delivery 129, price 67 of 596 abandons |
| D. checkout/drop-off behavior | DERIVED_TRUTH | Inferred from high ATC + low purchase + abandon/hesitation mix — no explicit checkout-step events |
| E. product views and discovery | DIRECT_TRUTH (sim) | Per-product views aggregates (e.g. P01 567 vs peers ~2274) |
| F. product placement / category exposure | INSUFFICIENT | No homepage/category rank instrumentation in sim — placement experiments are hypothesized actions only |
| G. purchase conversion after exposure | DIRECT_TRUTH (sim) | ATC rate and purchase-of-ATC per product |

### Unsupported (do not invent)

- Real shipping carrier / free-shipping policy effects  
- Production margin from bundles  
- Automatic placement change telemetry  
- Paid acquisition for cross-sell  

## Mission readiness (pre-design)

| Family | Scenario seed | Supported outcome direction |
|--------|---------------|-----------------------------|
| Cross-sell / Bundle | E_bundle + G_retention | POST_PURCHASE_OFFER (stronger than blanket bundle discount) |
| Shipping friction | B_high_interest_low_conversion | Shipping **cost** friction > delivery-time; clarify cost message — not free shipping |
| Merchandising / placement | A_discovery | DISCOVERY/PLACEMENT problem; ONE category/homepage placement test (placement exposure = insufficient instrumentation → action is experiment) |

## Laws

- No recommendation without evidence: hold  
- No revenue claim without measurement: hold  

## Next

Controlled packs D/E/F + priority integration + founder pack.
