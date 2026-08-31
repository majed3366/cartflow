# 03 — Figma-to-runtime traceability

Every Visual System primitive has a runtime owner. None is documentation-only.

| Primitive | Visual System | Runtime | Surfaces | Mobile |
|-----------|---------------|---------|----------|--------|
| Commerce Object | P12 | `.cf2-co` / `.cf2-co-row` / `CartFlowUiV2Lang.commerceObject` | Home rail, Workspace header | Glyphs shrink; labels remain |
| Evidence Density | P13 | `.cf2-evfield` | Home, Workspace evidence node | Sparse bars stay |
| Momentum / Living Route | P14 | `.cf2-mtrace` Home; `.cf2-route` Workspace | Home if ≥2 real lanes; Workspace always | Route stacks; spine remains |
| Decision Mass | P15 | `.cf2-dmass` | Workspace decision beat | Weight retained |
| Open-start container | P1 | `.cf2-home__board`, `.cf2-dobj--primary` | Home, Workspace | Start-edge drops; organism stays |
| Directional edge / accent | P2 P3 | stance / mark | Home, Workspace | Mark may drop; copy stays |
| Selected row edge | P6 | `.is-selected` | Carts, Comms, Settings | List hides; detail is selection |
| Attention rail | P5 | `.is-needs` / Carts `.is-actionable` | Comms, Settings, Carts | Rail remains on rows |
| Quiet detail | P4 P9 | `__detail` | Carts, Comms, Settings | Full-page after list |
| Truth block | P10 | `__empty` solid | Carts, Comms | Same object, no dash |
| Truth surface | P7 | `body[data-cf-ui=v2]`, `.cf2-stage` | All | overflow-x hidden |

Figma file `1NnI69Jd7BhfnNdehmBq0Q` supports tokens. File `0YWwVn1cKxH45M6mLZfGJE` is asset library, not Merchant page SoT. Merchant page identity is Visual System V1 + `merchant_ui_v2_*` emitters.
