# 04 — Surface gap audit (live `480d7d52`)

Observed 2026-08-31 on `https://smartreplyai.net` with Living Store session.

| Surface | Current production (V2 default) | Approved visual system | Figma | Gap |
|---------|---------------------------------|------------------------|-------|-----|
| Home | `CartFlowUiV2Home`: kicker, CO rail, gravity, density, momentum | P1–P3, P7, P11–P14, P16 | Language primitives mapped | **NO_GAP** on V2 |
| Workspace | `CartFlowUiV2Workspace`: CO row, route, Decision Mass | P1–P3, P7, P12–P15 | Same | **NO_GAP** on V2 |
| Carts | Filters + rows + solid empty + detail | P2, P5–P7, P9–P11 | Ops grammar | **NO_GAP** on V2 |
| Communication | History/status, not inbox | P2, P4–P7, P9–P11 | Ops grammar | **NO_GAP** on V2 |
| Settings | Overview rows + detail | P2, P4–P9, P11 | Ops grammar | **NO_GAP** on V2 |

**Material gap (all five):** leftover cookie `cf_ui_v2=0` on the same live SHA rendered **V1** (`merchant_app.html`, `home_executive_summary_v1.js`, `merchant_frame_v1.css`). Class: **LEGACY_PATTERN_PRESENT** via silent selection — not a missing primitive on the V2 painters.

Mobile V2 (prior 90e28b8f / 480d7d52 review): structure preserved. **NO_GAP** when V2 is actually selected.
