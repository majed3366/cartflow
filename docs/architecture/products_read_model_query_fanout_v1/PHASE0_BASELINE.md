# Products V1.1 — Phase 0 DSE baseline

**Recorded before V1.1 code edits.**  
**UTC date:** 2026-09-08  
**DEPLOY:** NO

| Field | Value |
|-------|--------|
| Live API SHA (production, last observed) | `7096de1564c008ac83da6216c70aba22f328071a` |
| Candidate git HEAD | `0767835dec586bfd59123559bb59afbf3bf74f81` (docs tip; live SHA is ancestor) |
| Branch | `candidate/reality-to-ui-projection-recovery-v1` |
| Product read-model owner | `product_read_model_contract_v1` |
| Products compose owner | `products_commercial_truth_v1` |
| Endpoint | `GET /api/dashboard/products` (Products page only; not on summary) |
| Normal merchant query delta | **+4** |
| Lab merchant query delta | **+5** |
| N+1 | **0** |
| Endpoint latency | Not re-measured on live (DEPLOY: NO). Local compose is one bounded request; no per-product query. |
| Current founder shots | `docs/product/products_v1/founder_review/` (6 mobile) |

## Query owners (+4 / +5)

All scoped by authenticated `store_slug`. No per-product loop.

1. `ProductCatalogEntry` — identity / name / price (limit 40)
2. `CartLineSnapshot` outerjoin `AbandonedCart` — cart_count / cart_value (limit 400 link rows)
3. `ProductPurchaseMapping` grouped — purchases / revenue (0 is known zero)
4. `ProductHesitationMapping` grouped — product-scoped hesitation only
5. **Lab only:** `ProductSignalEvent` `product_viewed` + source `live_reality_lab_v2_synthetic_visit`

## Observed V1 presentation defects (founder pack)

- Most cards repeat `يحتاج انتباه` until the phrase is meaningless.
- Intro / store-governance card dominates the first viewport.
- Workspace CTA is a teal pill that competes with product truth.
- Exposure disclaimer is a long line on every card.
- Cards are visually identical despite different facts (hesitation vs unknown visits vs missing name).
