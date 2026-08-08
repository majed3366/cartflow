# Merchant UI V2 — Home Desktop Stage Closure V1

**Scope:** Home only (stage relationship)  
**Deploy:** `71cf4e3`  
**Living Store:** https://smartreplyai.net/dashboard?cf_ui=v2#home

## What changed

- Board fills the authored Home stage surface (`boardWidth: 1240`, `boardShareStage: 1`)
- RTL-biased outer margins (`rightMargin ≈ 22`, deliberate `leftVoid ≈ 178`)
- V1.3 internal board preserved (scene → evidence → stance → monitoring)
- Primary reading measure capped; monitoring uses full board width
- Commerce Object structurally attached to the decision lead

## Gate (Living Store)

- Desktop `boardShareViewport ≈ 0.86` (was ≈ 0.54 in V1.3)
- Laptop usable (`boardWidth ≈ 1218`)
- Mobile `noOverflow: true`, scene + monitor present

## Confirmations

- No board redesign / no return to 67/33
- No new content, copy, primitives, or fake metrics
- No Workspace / Products / Carts / Communication / Settings changes
- Mobile sequencing preserved
- Real Living Store validated (`X-CartFlow-Git-Sha` `71cf4e3`)

## Captures

| # | File |
|---|------|
| 1 | [01_desktop_1440_full.png](01_desktop_1440_full.png) |
| 2 | [02_desktop_board_relationship.png](02_desktop_board_relationship.png) |
| 3 | [03_desktop_primary_path.png](03_desktop_primary_path.png) |
| 4 | [04_laptop_viewport.png](04_laptop_viewport.png) |
| 5 | [05_mobile_regression_check.png](05_mobile_regression_check.png) |
| 6 | [06_grayscale_logo_hidden.png](06_grayscale_logo_hidden.png) |
| 7 | [07_v13_vs_stage_closure.png](07_v13_vs_stage_closure.png) |

## STOP

Await visual approval. Do not begin Workspace.
