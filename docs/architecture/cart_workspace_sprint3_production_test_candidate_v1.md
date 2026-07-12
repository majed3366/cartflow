# Cart Workspace Sprint 3 — Production-Test Candidate V1

**Date (UTC):** 2026-07-12  
**Purpose:** Prepare Sprint 3 build for Product Validation only.  
**Merchant rollout:** **NOT authorized** — flag remains OFF by default.

## Scope

| Item | Value |
|------|--------|
| Candidate | Cart Workspace Sprints 1–3 + Silent Success facilitator pack |
| Feature flag | `CARTFLOW_CART_WORKSPACE_V1` default **OFF** |
| Silent Success flag | `CARTFLOW_CART_WORKSPACE_SILENT_SUCCESS` default **OFF** |
| Merchant surface | No `#workspace` when flag OFF |
| Existing carts | `#carts` / RSC unchanged |

## Identity

| Field | Value |
|-------|--------|
| Commit SHA (full) | `e2160e46fabceeeae1f46b5ccf80113e988b4a9d` |
| Commit SHA (short) | `e2160e4` |
| Branch | `main` → `origin/main` (`https://github.com/majed3366/cartflow.git`) |
| Production host | `https://smartreplyai.net` |
| Widget runtime version | `v2-widget-reason-post-detach-v1-6` (unchanged; not part of this candidate) |
| Process role | `api` (`/health/scheduler` compliance ok) |
| Public process `git_sha` | Not exposed on `/health` (same as prior prod verifications) |

## Deploy path

1. Commit `e2160e4` on local `main`
2. `git push origin main` (`7c26b4b..e2160e4`)
3. Production picked up candidate via GitHub→Railway auto-deploy (Railway CLI OAuth on this machine was expired; no manual `railway redeploy` required)
4. **No** env change: `CARTFLOW_CART_WORKSPACE_V1` was **not** set ON

## Gates

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | Commit | **Pass** | `e2160e4` — *feat: Cart Workspace Sprint 3 production-test candidate (flag OFF)* |
| 2 | Push | **Pass** | `origin/main` = `e2160e46fabceeeae1f46b5ccf80113e988b4a9d` |
| 3 | Deploy | **Pass** | `/health` 200; `/ping` 200; new `/api/cart-workspace/v1/*` live; Workspace static assets 200 |
| 4 | SHA match | **Pass** | Byte-identical SHA-256 for Workspace statics + `merchant_app.js` vs local HEAD `e2160e4` (public HTTP has no process `git_sha`) |
| 5 | Flag default OFF | **Pass** | `GET /api/cart-workspace/v1/projection` → 404 `feature_flag_off`, `flag.enabled=false`, `flag.default=false`, `merchant_surface=disabled` |
| 6 | `#carts` unchanged | **Pass** | Prod `merchant_app.js` still contains `#carts` / `page-carts`; login HTML has no Workspace surface |
| 7 | Internal-only | **Pass** | Commands + demo-seed → 404 `feature_flag_off`; login has no `page-workspace` / مساحة القرار / Workspace scripts |

### Flag-off API samples (production)

```json
{
  "ok": false,
  "error": "feature_flag_off",
  "flag": {
    "flag": "CARTFLOW_CART_WORKSPACE_V1",
    "enabled": false,
    "default": false,
    "merchant_surface": "disabled",
    "shadow_pipeline": "available_dev_only"
  }
}
```

### Static identity (sample)

| File | Prod status | SHA-256 match vs HEAD |
|------|-------------|------------------------|
| `static/cart_workspace_merchant_v1.js` | 200 | yes |
| `static/cart_workspace_merchant_v1.css` | 200 | yes |
| `static/cart_workspace_decision_card_v1.js` | 200 | yes |
| `static/cart_workspace_grid_v1.js` | 200 | yes |
| `static/cart_workspace_projection_version_v1.js` | 200 | yes |
| `static/cart_workspace_render_controller_v1.js` | 200 | yes |
| `static/merchant_app.js` | 200 | yes |

Probe artifact: `docs/architecture/_sprint3_prod_probe_out.json`

## What was NOT done

- Did **not** set `CARTFLOW_CART_WORKSPACE_V1=ON` on Railway
- Did **not** enable Silent Success on production
- Did **not** perform merchant rollout
- Did **not** change `#carts` behavior

## Verdict

**Production-test candidate READY** for Product Validation (internal flag-ON sessions only).  

Sprint 3 engineering is **committed, pushed, deployed, and verified flag-OFF**.  
**Merchant enablement / rollout remains unauthorized.**
