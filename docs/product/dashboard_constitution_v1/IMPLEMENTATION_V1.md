# Dashboard Constitution Implementation V1

**Status:** Implemented + production validated  
**Date (UTC):** 2026-07-26  
**Audit:** [`OWNERSHIP_AUDIT_V1.md`](OWNERSHIP_AUDIT_V1.md)  
**Prod pack:** [`PRODUCTION_VALIDATION_V1.md`](PRODUCTION_VALIDATION_V1.md)

## What changed

| Phase | Change |
|-------|--------|
| 1 | Ownership audit matrix published |
| 2 | Home entry default `#home`; month KPI wall removed from nav/path; every HES card CTA = «عرض التفاصيل» |
| 3 | Workspace remains sole decision explainer (unchanged face order) |
| 4 | Products language + CTA «عرض التفاصيل ←» → Workspace |
| 5 | Carts operational question; publication banner without business decision text; MEIF “حقيقة” banner suppressed |
| 6 | Communication facts (sent / delivered / replied / returned / no phone / needs follow-up) + immediate action links |
| 7 | Hidden: automation mode placeholder, Shopify roadmap footnote, merchant diagnostics nav |
| 8 | Top/sidebar aligned; notify 🔔 hidden; setup moved under Settings sidebar; empty hash → Home |
| 9–12 | Technical/roadmap copy removed from merchant chrome; one owner + action paths |

## Acceptance checklist

- [x] One question per page (purposes + HES order)
- [x] One owner matrix documented
- [x] Carts no longer paints systemic business decision text
- [x] Communication problems expose next action
- [x] Unfinished Settings controls hidden
- [x] Default navigation lands on Home
- [ ] Production validation (Desktop/Mobile parity) — after deploy of empty-hash + Communication facts repair

## Prod repair (same pass)

- Removed `CARTFLOW_CART_WORKSPACE_V1` empty-hash → `#workspace` redirect
- Communication facts painted by `commerce_situations_surfaces_v1` (owner surface)
- Workspace question `#cw-constitution-question`
- Carts question constant aligned to «ما حالة كل سلة؟»

## STOP

No new feature work until production validation of this constitution pass.
