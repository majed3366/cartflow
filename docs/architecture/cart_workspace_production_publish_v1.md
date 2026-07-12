# Cart Workspace — Production Publish V1 (pre-launch)

**Date (UTC):** 2026-07-12  
**Scope:** Controlled pre-launch production validation — **not** public commercial rollout.  
**Verdict:** **PUBLISHED** on `https://smartreplyai.net`

## Identity

| Field | Value |
|-------|--------|
| Commit SHA (full) | `1fff0c23c80c333c180b176576ad722c098775fd` |
| Commit SHA (short) | `1fff0c2` |
| Prior publish commit | `60258c6` (primary entry + railway.toml) |
| Production host | `https://smartreplyai.net` |
| Primary path | `/dashboard#workspace` |
| Reference/rollback path | `/dashboard#carts` |
| Widget runtime | `v2-widget-reason-post-detach-v1-6` (unchanged) |

## Enablement

| Mechanism | Value |
|-----------|--------|
| Flag | `CARTFLOW_CART_WORKSPACE_V1` |
| `railway.toml` `[env]` | `true` |
| Observed on prod | `enabled=true`, `env_raw=null`, `railway_deploy_default_on=true` |
| Local / non-Railway unset | **OFF** |
| Explicit `false` / `0` / `off` | **OFF** (rollback) |

## Verification (production)

| Check | Result |
|-------|--------|
| Deploy live | Pass — APIs return Workspace (not `feature_flag_off`) |
| Flag ON | Pass — `merchant_surface=enabled` |
| Default entry `#workspace` | Pass — signup lands `/dashboard#workspace` |
| `#carts` available | Pass — nav + page shell active |
| Zones A–E | Pass — A=1 VIP card, B=1 decision, C present, D completed=1, E null (healthy) |
| Desktop/mobile same structure | Pass — matching zone counts / labels / mission (in-memory version may bump between requests) |
| Console errors | Pass — 0 |
| Cart truth page | Pass — `#carts` loads with filter shell |

### Evidence

- `docs/architecture/cart_workspace_production_publish_v1_evidence/01_desktop_workspace.png`
- `docs/architecture/cart_workspace_production_publish_v1_evidence/02_desktop_carts_reference.png`
- `docs/architecture/cart_workspace_production_publish_v1_evidence/03_mobile_workspace.png`
- `docs/architecture/cart_workspace_production_publish_v1_evidence/verification_report.json`

## Rollback

1. Set `CARTFLOW_CART_WORKSPACE_V1=false` (or `0` / `off`) on the Railway API service.  
   **Required:** on Railway, unset defaults to ON — must set explicit false.
2. Redeploy / restart.
3. Confirm `GET /api/cart-workspace/v1/projection` → 404 `feature_flag_off`.
4. `#carts` remains intact; primary path returns to `/dashboard#carts`.

Unit proof: `test_flag_explicit_off_rolls_back_on_railway`.

## Safety

- `#carts` page **not** deleted  
- Feature flag **not** removed  
- No Ownership / Admission / Projection / Rendering contract changes  
