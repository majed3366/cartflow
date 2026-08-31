# Canonical Merchant Runtime & Render Parity Closure V1

**Status:** CLOSED  
**Production SHA at closure:** `90e28b8f142635887df9a78a1024f88946697c0a`  
**Mode:** architectural / diagnostic — no visual redesign  
**Production UI changed:** NO (not deployed from this closure)

## Law

Future Merchant UI visual approval is valid **only** when all of these are proven on the reviewed session:

1. Canonical route  
2. Canonical renderer  
3. Expected feature flags  
4. Expected shell  
5. Expected data contract  
6. Real rendered output  

A SHA, a CSS file, a static hash, a landing page, a local harness, or a dev bind **alone** is not a visual PASS.

## Canonical runtime

| Field | Value |
|-------|--------|
| Route | `/dashboard` |
| Template | `merchant_app_v2.html` |
| Renderer | `merchant_ui_v2` |
| UI version | `v2` |
| Shell | UtilityRow → GlobalUpbar → ContextualSidebar → PageStage |
| Home painter | `CartFlowUiV2Home` |
| Workspace painter | `CartFlowUiV2Workspace` |
| Home data | `GET /api/dashboard/summary` → `home_executive_summary_v1` |
| Workspace data | `GET /api/cart-workspace/v1/projection` |

## Documents

| File | Role |
|------|------|
| `01_ROUTE_INVENTORY.md` | Every Merchant UI path |
| `02_CANONICAL_RUNTIME.md` | Source of truth |
| `03_REVIEW_PARITY_CONTRACT.md` | Dashboard vs Living Store vs local |
| `04_VERSION_SELECTION.md` | V1/V2 selectors |
| `05_VERIFICATION_LAW.md` | How to approve visuals |
| `06_PRODUCTION_PROOF.md` | Live 90e28b8f observations |

## Diagnostics

- HTML: `window.CARTFLOW_MERCHANT_RUNTIME` + `meta[name=cartflow-runtime-*]`  
- Headers: `X-CartFlow-Merchant-*` + `X-CartFlow-Git-Sha` on `/dashboard`  
- JSON: `GET /dev/merchant-runtime-identity`  
- Review bind: `GET /dev/living-store-home-review` → `/dashboard#home` **and** forces `cf_ui_v2=1`

## Not Merchant UI

`GET /` is the public landing page. It must never be used as Merchant Dashboard proof.