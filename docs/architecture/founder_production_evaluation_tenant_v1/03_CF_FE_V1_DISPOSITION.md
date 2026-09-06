# `cf_fe_v1_*` disposition — Founder Production Evaluation Tenant V1

## Decision

**A — remain test-only / logic fixtures.**

| Concern | Verdict |
|---------|---------|
| Production evaluation eligibility | **NO** — slug prefix never unlocks production gate |
| Test / local merchandising logic | Allowed only with explicit `CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE=1` |
| Side-effect block | Still blocked (safety; does not imply feature eligibility) |

## Inventory

| Slug | Role |
|------|------|
| `cf_fe_v1_actionable` | Logic fixture |
| `cf_fe_v1_measuring` | Logic fixture |
| `cf_fe_v1_insufficient` | Logic fixture |
| `cf_fe_v1_price` | Logic fixture |
| `cf_fe_v1_quality` | Logic fixture |
| `cf_fe_v1_focus` | Logic fixture |

`integration_source`: `founder_evaluation_v1` (distinct from production `founder_production_evaluation_v1`).

## Regression

Production-shaped compose with `cf_fe_v1_*` + empty environ → merchandising suppressed (`merchandising_eval_tenant_gate`).
