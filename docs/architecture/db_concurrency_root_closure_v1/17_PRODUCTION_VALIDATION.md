# Phase 16 — Production validation

**NOT RUN. NOT AUTHORIZED TO DEPLOY.**

After exact-SHA deploy only:

| Stage | Action | Required |
|-------|--------|----------|
| 0 | Idle | no timeout; `checked_out` idle; no unexpected IIT |
| 1 | Single mobile | same |
| 2 | Single desktop | same |
| 3 | Mobile + desktop | same |
| 4 | Normal navigation | auth + dashboard responsive |
| 5 | Heavy route | admit or complete; pool returns to baseline |

Stop at first failed stage.
