# Reality Validation Report — Gate 2B

**Date (UTC):** 2026-07-24  
**Scope:** Decision Composition against operational truth + findings (no PI).

## Scenario matrix

| Scenario | Expected | Unit status |
|----------|----------|-------------|
| 43 active carts without phone | Publish recoverability_gap with business meaning | **PASS** |
| Waiting needing merchant action | Publish waiting_recovery_work | **PASS** |
| Waiting handled by automation | Suppress normal_state | **PASS** |
| Sufficient verified product finding | Publish with product id/name | **PASS** |
| Product identity unavailable | Suppress subject_unidentified | **PASS** |
| Insufficient evidence | Suppress with reason | **PASS** |
| Duplicate candidates | Suppress duplicate | **PASS** (pipeline dedupe) |
| Stale findings | Suppress stale_finding | **PASS** (composer) |
| No valid decisions | Quiet / teaser 0 | **PASS** |
| Multiple candidates priority | Deterministic sort | **PASS** |
| Home teaser parity | count/title match CW | **PASS** |

## Reality Simulator hooks

Use `services/store_reality_simulator` scenarios:

- `anonymous_no_phone` → recoverability gap input  
- `S03_shipping_cost_hesitation` / `S04_product_high_atc_low_purchase` → verified finding path  

Production organic signup probe documents live Workspace presentation after deploy.
