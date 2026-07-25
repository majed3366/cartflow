# Gate — Commerce Situation Engine V1

## Goal

Stop publishing merchant cards from Facts / Observations / OT / Recommendations.
Publish from **Commerce Situations** only.

## CEO Reality Validation (merchant understanding — pass/fail)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Home paints **3–5 distinct** Situation cards (`situation_id`) | IMPLEMENTED — awaiting Living Store CEO session |
| 2 | Workspace expands **same** Situation + evidence | IMPLEMENTED — awaiting CEO session |
| 3 | Products page shows products in Situation | IMPLEMENTED (`#page-products`) |
| 4 | Carts shows carts participating | IMPLEMENTED (ops banner + scope) |
| 5 | Communication shows customers participating | IMPLEMENTED (ops banner + scope) |
| 6 | Every page references same `situation_id` | IMPLEMENTED in UI attrs |
| 7 | No duplicated explanations | Home drops Decisions/Facts dual when portfolio present |
| 8 | Rename-only = FAIL | Portfolio replaces teaser rename |

**Verdict until CEO Living Store session: NOT CLOSED.**

## Engineering acceptance

| Criterion | Status |
|-----------|--------|
| Entity-bound compose `(kind, subject.id)` | DONE |
| Many facts → one situation (e.g. conversion + return) | DONE |
| Home Situation portfolio (not single teaser) | DONE |
| Workspace cards from Situations + visible `situation_id` | DONE |
| Facts atoms-only on Home slim transport | DONE |
| Themes stripped from Home transport | DONE |
| DCE attaches `commerce_situations_v1` | DONE |
| Products / Carts / Communication merchant consumers | DONE |
| Probe `GET /dev/commerce-situations` | DONE |
| Tests anti-Theme + Home portfolio | DONE |
| No PI / no recommendations | DONE |

## Surfaces (same Situation, different responsibility)

| Surface | Role |
|---------|------|
| Home | Introduce |
| Decision Workspace | Explain + act |
| Products | Affected product scope |
| Carts | Operational cart scope |
| Communication | Communication status |

## Out of scope

- Product Intelligence
- Gates 3–7
- Theme redesign as publisher
