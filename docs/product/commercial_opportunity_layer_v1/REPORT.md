# Commercial Opportunity Layer V1 — REPORT

**Date (UTC):** 2026-09-03  
**Mode:** Controlled real-product composition (flag-gated)  
**Deploy:** NOT authorized

## Scorecard

```
BASE LIVE SHA:                 033cdd482960c6b66f5f22c1027ce3b9ba9f485e
CANDIDATE SHA:                 (worktree uncommitted on cd319040 + COL V1)
WORKTREE:                      C:\Users\Toshiba\AppData\Local\Temp\cf-psg-impl-v1

HOME OWNERSHIP MAP:            PASS
OPERATIONAL vs COMMERCIAL SEPARATION: PASS
PRODUCTION TRUTH GATE:         PASS
SIMULATION LEAK:               0
PRIMARY COMMERCIAL OPPORTUNITY: shipping_friction (evidence-led)
SECONDARY OPPORTUNITIES:       ≤2 (price_hesitation / recovery_hesitation when evidence allows)
GENERIC ADVICE:                0
NO RECOMMENDATION WITHOUT EVIDENCE: PASS
NO REVENUE CLAIM WITHOUT MEASUREMENT: PASS
DECISION WORKSPACE COMPRESSION: PASS
EVIDENCE DISCLOSURE:           PASS
PRIORITY EXPLAINABILITY:       PASS
COST / SCALE:                  PASS
AI CALLS ON PAGE LOAD:         0
EXTERNAL API CALLS:            0
FAILURE TESTS:                 PASS (18/18)
FLAG OFF:                      PASS
FLAG ON:                       PASS
HOME:                          PASS
MOBILE:                        PASS
DESKTOP:                       PASS
SCREENSHOTS:                   12 / 12
FOUNDER REVIEW READY:          YES
PRODUCTION DEPLOY AUTHORIZED:  NO
PUBLIC RELEASE AUTHORIZED:     NO
```

## What shipped (candidate only)

| Piece | Path |
|--------|------|
| Flag (default OFF) | `CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1` |
| Package | `services/commercial_opportunity_layer_v1/` |
| Summary counts (already queried) | `merchant_reason_counts_week/month` on `/api/dashboard/summary` |
| Attach | after OGL inside HES attach + snapshot passthrough |
| Home UI | `merchant_ui_v2_home.js` + CSS — separate commercial strip |
| Workspace UI | compressed decision panel from `sessionStorage` focus |
| Tests | `tests/test_commercial_opportunity_layer_v1.py` |
| Docs | `docs/product/commercial_opportunity_layer_v1/` |
| Founder pack | `founder_review_v1/` (12 PNGs) |

## Laws held

- Operational Home question unchanged; commercial question is a separate strip.
- Flag OFF → no `commercial_opportunity_layer_v1` key; Home paint unchanged.
- SIMULATION_TRUTH / preview missions never enter `/dashboard` COL.
- No AI / external API on page load; path = summary truth → bounded candidates → rank → materialize.
- Preview route `/preview/commercial-intelligence` untouched.

## First real mission family

Chosen by production hesitation dominance thresholds (same MIN_* as OGL families):  
**shipping_friction** when shipping/delivery dominates store reason counts.

Discount / channel / cross-sell / merchandising lab missions are **not** forced into production.

## Founder pack

`docs/product/commercial_opportunity_layer_v1/founder_review_v1/`

1. `01_home_flag_off`
2. `02_home_flag_on`
3. `03_primary_opportunity`
4. `04_decision_workspace`
5. `05_evidence_expanded`
6. `06_no_valid_opportunity`

Each: `mobile_390.png` + `desktop_1280.png`.

Capture uses real `CartFlowUiV2Home.paint` + composed production-truth packages (not live deploy).

## STOP

No Railway deploy. Autodeploy remains OFF. Scheduler untouched.
