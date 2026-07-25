# Reality Validation — Production Evidence Report

**Status:** PENDING_DEPLOY → fill after production deploy + CEO console run  
**Host:** https://smartreplyai.net  
**Store:** `demo`

## Blocker diagnosis (pre-deploy)

| Check | Result | First divergence |
|-------|--------|------------------|
| `GET /dev/reality-validation-console` | **HTTP 404** | **FIRST:** code not on production `main` (local branch only) — deploy this PR |
| `GET /dev/living-store-reality-status` | 200, `status=idle`, no `simulation_run_id` | In-memory job per replica; fixed via durable job control `lsr_prod_job_control_v1` |
| Workspace «تعذر التحميل» | Observed in CEO session | Soft-fail + quiet paint + retry; projection API never hard-fails build; bind via `/dev/living-store-home-review` before Workspace |

## Required pipeline (must be identical)

```text
Browser
  → Living Store (POST via console)
  → Facts
  → Situations
  → Home
  → Workspace
  → Products
  → Carts
  → Communication
```

## Post-deploy certification checklist

1. Open https://smartreplyai.net/dev/reality-validation-console  
2. Click **Run Living Store** → wait `completed` → copy `simulation_run_id`  
3. Open https://smartreplyai.net/dev/living-store-home-review  
4. Open https://smartreplyai.net/dev/reality-validation-context?store=demo&format=html  

### Must show

```text
Status = CONSISTENT
CEO_REVIEW_SAFE = TRUE
```

### Identity (paste from certification JSON)

| Field | Value |
|-------|-------|
| environment | |
| database_environment | |
| store_slug | |
| merchant_id | |
| simulation_run_id | |
| living_store_profile | |
| last_simulation_timestamp | |
| observations | |
| facts | |
| situations | |
| home_projection | |
| workspace_projection | |
| products_projection | |
| carts_projection | |
| communication_projection | |

### Surface sameness

| Surface | store_slug | simulation_run_id | obs | facts | situations |
|---------|------------|-------------------|-----|-------|------------|
| Home | | | | | |
| Workspace | | | | | |
| Products | | | | | |
| Carts | | | | | |
| Communication | | | | | |

All five rows must match.

### Workspace load

| Check | Result |
|-------|--------|
| `/api/cart-workspace/v1/projection` returns `ok: true` | |
| UI does **not** show «تعذر التحميل» | |

## Verdict

- [ ] `CEO_REVIEW_SAFE = TRUE`
- [ ] `Status = CONSISTENT`
- [ ] Workspace loads
- [ ] Surfaces share one `simulation_run_id`

**Until checked:** no UX / Situations polish / Product Review.

## Deploy

PR: https://github.com/majed3366/cartflow/pull/111  
Commit: `77d55e7`  
Railway: _(fill after merge/deploy)_  
