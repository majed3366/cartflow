# 03 — Review / preview parity contract

Living Store review must use the **same** Merchant UI runtime as production `/dashboard`, or declare a difference.

## Contract

| Axis | Production `/dashboard` | `/dev/living-store-home-review` | Local review |
|------|-------------------------|----------------------------------|--------------|
| Template | `merchant_app_v2.html` | 302 → same | same when `?cf_ui=v2` or default |
| Renderer | `merchant_ui_v2` | forces `cf_ui_v2=1` then same | same |
| Shell | CF2 UtilityRow / Upbar / Ctx | same | same |
| Home painter | `CartFlowUiV2Home` | same | same |
| Workspace painter | `CartFlowUiV2Workspace` | same | same |
| CSS/JS family | `merchant_ui_v2_*` | same | same |
| Data | summary + workspace projection | Living Store **tenant** (`store_slug=demo`) | local DB / flag-dependent |
| Flags | production env | production env | local default Workspace OFF unless `CARTFLOW_CART_WORKSPACE_V1=true` |

## MERCHANT-UI-INV-CONFIG-01 (binding)

Automated gate: `MERCHANT_UI_PRODUCTION_CONFIG_PARITY_REGRESSION_GATE`
(`services/merchant_ui_config_parity_v1.py`).

Compares **effective** material Merchant UI flags (not raw string spelling):

- `CARTFLOW_CART_WORKSPACE_V1`
- `CARTFLOW_MERCHANT_UI_V2`
- `CARTFLOW_CARTS_V2_UI`

Required: `REVIEW EFFECTIVE CONFIG = PRODUCTION EFFECTIVE CONFIG`.

Unresolved effective values → **fail closed**.

Merchant visual deploy authorization (`services/merchant_visual_deploy_authorization_v1.py`)
requires config parity **PASS** alongside visual contracts, semantic regression, and
real-device review. Otherwise **SAFE FOR EXACT-SHA DEPLOY = NO**.

## Allowed difference (documented)

**Data tenant only.** Review bind sets `primary_store_id=demo` so Home/Workspace read Living Store truth. That is not a renderer change.

Local review must match production **effective** Workspace ON — set
`CARTFLOW_CART_WORKSPACE_V1=true` **or** unset + `RAILWAY_GIT_COMMIT_SHA` (Railway-equivalent).
If unset locally without Railway SHA, Workspace 404 `feature_flag_off` is a **local flag difference**,
not a production renderer difference — and the config parity gate **FAIL**s.

## Forbidden silent differences

Review bind must not land on V1 because a leftover `cf_ui_v2=0` cookie exists. The bind now writes `cf_ui_v2=1`.

## Parity verdict (this repo)

**PASS** — review bind and default `/dashboard` share renderer family, shell family, UI version, Home painter, Workspace painter.

Live SHA `90e28b8f` (pre-this-closure) already served the same V2 template when no V1 cookie was present. The bind did **not** clear a V1 cookie until this closure. That residual is documented in `06_PRODUCTION_PROOF.md`.
