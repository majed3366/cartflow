# Merchant Platform Visual Identity Residual Closure V1

**Date (UTC):** 2026-08-31  
**Base candidate:** `011f7d8b1c12942f863527366fcae7847a6313aa`  
**Production SHA:** `2bf18ebcdff069a1b16a7a896b6f6ecb494b92e8`  
**Mode:** narrow residual closure of R1/R2/R3 from the real-device review. No deploy.

## Residuals closed (CSS only)

| Residual | Surface | Change |
|----------|---------|--------|
| R1 | Carts selected row | Teal inset + navy full outline removed. Selection is a navy open-start edge. Queue rows use open-start radius. Attention (`is-actionable`) stays a distinct teal border on unselected rows. |
| R2 | Communication desktop | List rows unboxed (transparent, start-edge). Detail is no longer a white pane; one quiet navy start-edge relates list to history. Mobile detail stays borderless. Not an inbox. |
| R3 | Settings overview | Rows lose filled-card surface/radius. Selected = navy start; needs = amber start. Detail M3 and inner `.setting-card` unchanged. |

## Not changed

Home, Decision Workspace, merchant shell, product semantics, mobile list→detail→back ownership, Carts/Communication/Settings fetch paths, QueuePool, Settings `Promise.all` absence, session ownership.

Cache tokens keep `assim1` / `qpool1` / `nvis1-fanout1` and add `resid1`.
