# CartFlow Merchant App Frontend Recomposition V1

## Status

**Frame rebuild in progress — Acceptance Gate 1.**

Rejected direction (stopped): stacking brand/assimilation CSS on the legacy merchant shell.

## Objective

Recompose the real merchant SPA around the approved CartFlow visual system (Figma 25–34), without changing backend/product truth.

## Source of truth

Figma file `0YWwVn1cKxH45M6mLZfGJE`:

- 25 — Visual Constitution V1
- 26 — Design System V1
- 29 — Signature System V1
- 31 — Brand Assimilation Implementation V1
- 33 — System Assimilation Across Real Surfaces V1
- 34 — Blind Recognition Validation V1

## Architecture (live)

| Layer | Asset | Role |
|---|---|---|
| Frame | `static/merchant_frame_v1.css` | App shell geometry, rail, topbar, mobile drawer, content width |
| Design System | `static/merchant_ds_v1.css` | Buttons, tabs, badges, inputs, panels/cards, empty/loading/error, modal |
| Grammar | `static/merchant_grammar_v1.css` + `cf_signature_primitives_v1.*` | Structural visual grammar (truth-bound) |
| Router | `static/merchant_app.js` | Unchanged IA/hash routing + `syncFrameChrome` |
| Template | `templates/merchant_app.html` | `data-cf-frame="v1"`; rail owns primary nav; stage owns content |

## Shell model

**Desktop**

- Full-height chrome **rail** (brand + 6 primary sections + contextual secondary nav)
- Content **stage** fills remaining viewport (no 840px Family-A choke)
- Slim utility topbar inside the stage (section/page labels + account)

**Mobile**

- Compact app bar: menu · CartFlow mark · account
- No desktop section pills in the header
- Account / plans / logout in the drawer footer

## Obsolete override stack (unlinked, kept offline)

- `platform_shell_visual_assimilation_v1.css`
- `merchant_shell_identity_v1.css`
- `merchant_visual_identity_v1.css`
- `merchant_responsive_layout_v1.css`
- `merchant_workspace_expansion_v1.css`
- `merchant_pds_compliance_v1.css`
- `merchant_typography_certification_v1.css`
- `merchant_card_system_v1.css`
- `merchant_icon_language_v1.css`
- `merchant_spacing_certification_v1.css`

## Acceptance

Gate 1 (frame): real Living Store `/dashboard` — Home + Decision Workspace, desktop + mobile.

Question: does the frame feel rebuilt around CartFlow, and is usable workspace width improved?

Do **not** declare completion from CSS alone. Do **not** proceed to page-specific UX redesign until Gate 1 passes.
