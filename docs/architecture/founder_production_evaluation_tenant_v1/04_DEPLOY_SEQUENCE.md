# Future deploy sequence — Founder Production Evaluation Tenant V1

**This task does not execute deployment.**

## Expected future flow

1. Clean exact-SHA runtime candidate
2. Deploy production API to that SHA only (`serviceInstanceDeployV2`)
3. Merchandising remains OFF for all merchants except `cf_founder_evaluation`
4. Ops: `ensure_founder_production_evaluation_tenant_v1()`; rotate password; founder logs in
5. Prove `/dashboard` mobile + desktop on `smartreplyai.net`
6. Founder reviews real production Merchant UI V2
7. Only then consider general merchant release (separate explicit gate — not slug prefix, not this env release shortcut)

## Post-deploy review plan

1. Exact-SHA deploy
2. Prove live SHA
3. Prove Scheduler unchanged
4. Log into `cf_founder_evaluation` on smartreplyai.net
5. Open real `/dashboard`
6. Verify merchandising missions
7. Capture real iPhone/mobile + desktop evidence
8. Founder reviews real production
9. General merchants remain unchanged

## Rollback

- Code: redeploy prior live SHA
- Product: founder-only remains gated by exact slug allowlist (count = 1)
