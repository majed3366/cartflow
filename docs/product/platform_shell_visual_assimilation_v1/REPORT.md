# CartFlow Platform Shell Visual Assimilation V1

## Objective

One shared merchant application shell that all six surfaces inherit — frozen CartFlow identity as product foundation, not page-by-page skins.

## Scope

Shared shell only. Internal business content of Home / Workspace / Products / Carts / Communication / Settings was not redesigned.

## What changed

| Area | Change |
|---|---|
| Shared CSS | New `static/platform_shell_visual_assimilation_v1.css` — platform source of truth |
| Brand | Canonical CF mark visible on **all** merchant surfaces |
| Chrome | Navy→teal topbar + sidebar globally; green chrome dialect remapped |
| Tokens | Legacy `--green*` aliases → navy/teal; PDS sidebar + shell fallbacks → navy |
| Controls | Buttons, inputs, filters, pills, tables, modals, skeletons, focus/hover/disabled |
| Workspace CSS | Chrome/logo removed from DWA; workspace keeps content hierarchy only |

## What remained unchanged

Routing · APIs · permissions · merchant actions · page IA · decision/cart/product/comms/settings business logic · Landing

## Legacy dialect removed (shared)

- Forest-green topbar/sidebar paint sources
- Green PDS sidebar token / shell teal-forest fallback
- Green filter-active / WA pill / status-ok chips / modal primary CTAs
- Soft-circle / glow hero leftovers
- Text-only logo (mark now global)
- Workspace-only chrome duplication

## Visual proof

| # | File |
|---|---|
| 1 | `after_home_desktop.png` |
| 2 | `after_workspace_desktop.png` |
| 3 | `after_products_desktop.png` |
| 4 | `after_carts_desktop.png` |
| 5 | `after_comms_desktop.png` |
| 6 | `after_settings_desktop.png` |
| 7 | `shared_topbar_closeup.png` |
| 8 | `shared_sidebar_closeup.png` |
| 9 | `shared_buttons_states_sample.png` |
| 10 | `before_after_shell_comparison.png` |

Capture: `scripts/_capture_platform_shell_visual_assimilation_v1.py`

## Probe (live)

- Shell CSS loaded
- Mark `display:block` · `cartflow_cf_mark.png`
- Topbar/sidebar: navy chrome gradient
- `--green` remapped to `#082048`

## STOP

Await shell visual approval before page-specific assimilation (Home → Workspace → Products → Carts → Communication → Settings).
