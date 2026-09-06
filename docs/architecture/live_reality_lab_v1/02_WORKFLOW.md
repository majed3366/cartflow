# Live Reality Lab V1 — Canonical Founder Workflow

From this point forward:

**LOGIC PASS ≠ PRODUCT PASS**

## Permanent sequence

1. **Implement candidate** (feature work)
2. **Run tests** (unit/integration + lab failure suite)
3. **Freeze clean runtime SHA**
4. **Exact-SHA production deploy** (API only; Scheduler untouched unless authorized)
5. **Apply reality scenario** to `cf_live_reality_lab`  
   `POST /api/live-reality-lab/v1/apply` `{ "scenario_id": "R7_…" }` as lab merchant
6. **Founder logs into** `https://smartreplyai.net/dashboard` as `reality.lab@cartflow.local`
7. **Founder reviews** real mobile/desktop product (Priority Surface lanes, etc.)
8. **Falsify** if product fails comprehension / truth
9. **Fix + repeat** from step 1–7
10. **Close feature** only after lab + founder pass
11. **Only later** consider general merchant release

## Lab controls (authenticated lab session only)

| Route | Purpose |
|-------|---------|
| `POST /api/live-reality-lab/v1/ensure` | Idempotent tenant ensure |
| `GET /api/live-reality-lab/v1/scenarios` | Manifest list |
| `POST /api/live-reality-lab/v1/reset` | Lab-owned data cleanup |
| `POST /api/live-reality-lab/v1/apply` | Reset + seed scenario |
| `POST /api/live-reality-lab/v1/verify` | Compare observed vs manifest |

## First feature to validate in lab

**Priority Surface Contract V1** via scenario **R7** (commercial + operational coexistence).

Deploy of this lab package: **NOT in this task** — candidate ready for Exact-SHA gate next.
