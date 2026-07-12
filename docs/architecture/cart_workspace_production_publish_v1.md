# Cart Workspace — Production Publish V1 (pre-launch)

**Date (UTC):** 2026-07-12  
**Scope:** Controlled pre-launch production validation — **not** public commercial rollout.

## Intent

Make Cart Workspace (`#workspace` / مساحة القرار) the **primary** merchant experience in the current pre-launch production environment, while keeping `#carts` available as a temporary rollback/reference path.

## Enablement

| Mechanism | Value |
|-----------|--------|
| Flag | `CARTFLOW_CART_WORKSPACE_V1` |
| `railway.toml` `[env]` | `true` (config-as-code intent) |
| Railway deploy when unset | **ON** (pre-launch — `RAILWAY_GIT_COMMIT_SHA` present) |
| Local / non-Railway unset | **OFF** |
| Explicit `false` / `0` / `off` | **OFF** (rollback) |

## Primary entry

When flag ON:

- Login / signup / normal-carts merchant redirects → `/dashboard#workspace`
- Empty dashboard hash → `#workspace`
- Top nav: **مساحة القرار** + **السلال** (reference)

When flag OFF:

- Primary path returns to `/dashboard#carts`
- Workspace UI/API gated off

## Rollback

1. Set `CARTFLOW_CART_WORKSPACE_V1=false` (or `0` / `off`) on the Railway API service — **required** even if `railway.toml` says true, if dashboard overrides; or change `railway.toml` to `false`.
2. Redeploy / restart so the process picks up the env.
3. Confirm `GET /api/cart-workspace/v1/projection` → 404 `feature_flag_off`.
4. `#carts` remains intact throughout.

Note: On Railway, leaving the variable **unset** enables Workspace (pre-launch publish). Rollback must set an explicit false.

## Safety

- `#carts` page **not** deleted
- Feature flag **not** removed
- No Ownership / Admission / Projection / Rendering contract changes

## Verification results

_Filled after deploy._
