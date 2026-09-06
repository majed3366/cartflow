# Founder Production Evaluation Tenant V1

**Status:** Production-scope hardened candidate · **Deploy:** NO  

| Doc | Purpose |
|-----|---------|
| `01_TENANT_IDENTITY.md` | Exact store/account identity |
| `02_GATE_AND_SIDE_EFFECTS.md` | Server-side gate + external side-effect policy |
| `03_CF_FE_V1_DISPOSITION.md` | Audit of `cf_fe_v1_*` fixtures (not production eligible) |
| `04_DEPLOY_SEQUENCE.md` | Future exact-SHA production enablement (not executed) |
| `05_FOUNDER_PRODUCT_GATE_POLICY.md` | Permanent Logic / Founder Product / General Release gates |
| `EXACT_SHA_DEPLOY_GATE.md` | Frozen SHA + Railway control-plane + prepared mutation |
| `REPORT.md` | Scorecard |

## Production allowlist (count = 1)

`cf_founder_evaluation` only.

`cf_fe_v1_*` is **not** production evaluation eligible.

## Package

`services/founder_production_evaluation_tenant_v1/`

Owner function: `is_founder_production_evaluation_tenant`

## Cost

- AI calls: **0**
- External API calls by tenant mechanism: **0**
- New Scheduler work: **0**
- New DB table: **NO**
- Query delta: **0**
