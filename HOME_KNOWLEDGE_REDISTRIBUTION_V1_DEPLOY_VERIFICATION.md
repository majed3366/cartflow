# Home Knowledge Redistribution V1 — Production Verification

**Date (UTC):** 2026-07-17  
**Production:** https://smartreplyai.net/dashboard#home  
**Commits on `main`:**  
- `279ea55` — feat(home): redistribute Home knowledge — one section, one question  
- `0fd3ce5` — fix(home): end Today/Timeline duplication and soften merchant Arabic  

## Section ownership (merchant questions)

| Section | Question | Owner |
|---------|----------|--------|
| Today In Your Store | What changed today? | One-line summary only |
| Knowledge Layer | What did we learn? | Observation → Evidence → Explanation → Confidence (no action) |
| Attention Center | What needs a decision? | Why now / why important / if ignored / action |
| Quick Indicators | Improving or declining? | Directional KPIs only |
| Recent Activity | What actually happened? | Pure timeline event list |

## Duplication closed

- Today no longer re-lists Timeline events (`ma-ecc-today-list` removed).
- Knowledge explains; Attention decides (different wording for the same commercial fact).
- No engineering «طابور قرارات»; product-name monitoring copy softened to merchant Arabic.

## Merchant review

Script: `scripts/_home_redistribution_prod_merchant_review_v1.py`  
Evidence: `scripts/_home_redistribution_prod_review_out/`  
Result: **`ok: true`**, `fails: []`

## STOP

No additional pages. No PIB-4. Await product acknowledgment before expanding beyond Home.
