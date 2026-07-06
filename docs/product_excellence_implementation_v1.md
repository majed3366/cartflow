# Product Excellence Implementation V1

## Summary

Replaces the legacy merchant dashboard presentation layer with the approved **Product Excellence V2** visual system on the real `/dashboard` app — not isolated preview routes.

## Scope delivered

| Surface | Change |
|---------|--------|
| **Merchant Home** | `static/merchant_home_experience.js` renders V2 hero, single attention card, whisper understanding, quick nav from `merchant_home_experience_v1` |
| **Carts workspace** | `#page-carts` uses work-queue cards (`#ma-carts-queue-v2`) + desktop conversation panel (`#ma-carts-panel-v2`) + mobile CTA |
| **Cart detail / story** | `merchantPeV2ConversationHtml` — guided flow: what happened → CartFlow → next → merchant action; timeline in `<details>` |

## Non-changes (by design)

No changes to Truth, Evidence, Proof, Decision Layer, Explanation producers, Knowledge Routing, recovery/lifecycle logic, API contracts, or business rules. All copy comes from existing payloads (`merchant_home_experience_v1`, `merchant_explanation_v1`, `cart_detail_projection_v1`).

## Files

- `static/merchant_pe_v2.css` — V2 design system scoped for dashboard pages
- `static/merchant_home_experience.js` — V2 home renderer
- `static/merchant_dashboard_lazy.js` — queue + conversation composition
- `static/merchant_app.js` — filter applies to queue items
- `templates/merchant_app.html` — `#page-home` / `#page-carts` shells
- `tests/test_product_excellence_implementation_v1.py` — presentation contract

## Legacy fallback

Hidden `#ma-tbody-all-carts` sync rows preserve filter/count compatibility and completed-tab DOM extraction. Completed tab (`#page-completed`) keeps compact table rows without inline story walls.

## Visual verification

Screenshots captured locally: `scripts/_product_excellence_implementation_v1_out/` (home/carts mobile + desktop; cart detail when queue has rows).

**Before:** legacy stacked sections + 6-column carts table (see `scripts/_product_excellence_visual_rebuild_v2/before_*`).

**After:** matches approved V2 preview structure (`/preview/product-excellence-v2/*`) using live payloads.

Run: `python scripts/_product_excellence_implementation_v1_screenshots.py` (set `CARTFLOW_PROD_EMAIL` / `CARTFLOW_PROD_PASSWORD` for production store with carts).

## Approval gate

- [x] Tests pass
- [x] Production dashboard wired to V2 presentation
- [ ] Screenshots attached (run capture script with auth)
- [ ] Product owner visual sign-off
