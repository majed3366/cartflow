# 02 — Canonical Merchant runtime

This is the source of truth for all future Merchant UI verification.

| Field | Canonical value |
|-------|-----------------|
| CANONICAL ROUTE | `/dashboard` |
| CANONICAL TEMPLATE | `merchant_app_v2.html` |
| CANONICAL RENDERER | `merchant_ui_v2` |
| CANONICAL UI VERSION | `v2` |
| CANONICAL SHELL | UtilityRow + GlobalUpbar + ContextualSidebar + PageStage (`cf2-shell-v1`) |
| CANONICAL HOME PAINTER | `CartFlowUiV2Home` (`static/merchant_ui_v2_home.js`) |
| CANONICAL WORKSPACE PAINTER | `CartFlowUiV2Workspace` (`static/merchant_ui_v2_workspace.js`) |
| CANONICAL FEATURE FLAGS | `CARTFLOW_MERCHANT_UI_V2` unset or truthy (default ON). Workspace: `CARTFLOW_CART_WORKSPACE_V1` ON in Railway production. |
| CANONICAL DATA CONTRACTS | Home: `GET /api/dashboard/summary` → `home_executive_summary_v1`. Workspace: `GET /api/cart-workspace/v1/projection`. |

## Identity proof (required)

A session is canonical only if:

- `data-cf-ui="v2"`  
- `meta[name=cartflow-runtime-ui][content=v2]`  
- `X-CartFlow-Merchant-Ui: v2`  
- `X-CartFlow-Merchant-Renderer: merchant_ui_v2`  
- `X-CartFlow-Merchant-Role: canonical`  
- HTML includes `merchant_ui_v2_home.js` and `merchant_ui_v2_workspace.js`  
- HTML does **not** include `home_executive_summary_v1.js` as the Home painter  

`X-CartFlow-Git-Sha` on `/` (landing) is **not** Merchant runtime proof. Use `/dashboard` headers or `GET /dev/merchant-runtime-identity`.

## Explicitly not canonical

- `merchant_app.html` / `HomeExecutiveSummaryV1` / V1 rail  
- `?cf_ui=v1` or `cf_ui_v2=0`  
- `CARTFLOW_MERCHANT_UI_V2=0`  
- Landing `/`  
- Isolated `/preview/*` and `/dev/cart-workspace-render`  
