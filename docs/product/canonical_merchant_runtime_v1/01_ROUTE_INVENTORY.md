# 01 — Canonical route inventory

Routes that can present Merchant UI, plus lookalikes that must not be used as proof.

## Merchant UI (can render the dashboard)

| ROUTE | PURPOSE | TEMPLATE | RENDERER | UI | FLAGS / COOKIES | SHELL | DATA | CLASS |
|-------|---------|----------|----------|----|-----------------|-------|------|-------|
| `/dashboard` | Canonical merchant app | `merchant_app_v2.html` (default) or `merchant_app.html` (rollback) | `merchant_ui_v2` / `merchant_ui_v1` | v2 default | `?cf_ui=` · `cf_ui_v2` · `CARTFLOW_MERCHANT_UI_V2` | CF2 shell / V1 rail | `/api/dashboard/summary` · `/api/cart-workspace/v1/projection` | **PRODUCTION** |
| `/dashboard?cf_ui=v2` | Explicit canonical | `merchant_app_v2.html` | `merchant_ui_v2` | v2 | query persists cookie | CF2 | same | **CANONICAL** |
| `/dashboard?cf_ui=v1` | Explicit rollback | `merchant_app.html` | `merchant_ui_v1` | v1 | query persists `cf_ui_v2=0` for 14d | V1 rail | same APIs, V1 painters | **ROLLBACK_ONLY** |
| `/dev/living-store-home-review` | Bind Living Store session | none (302) | n/a | forces v2 cookie | session + `cf_ui_v2=1` | n/a | n/a | **DEV / REVIEW BIND** |
| `/dev/merchant-ui-v2` | Clear V1 cookie | 302 → `/dashboard#home` | n/a | sets v2 | cookie | n/a | n/a | **DEV_ONLY** |
| `/dev/merchant-ui-v1` | Force rollback | 302 → `/dashboard?cf_ui=v1#home` | n/a | sets v1 | cookie | n/a | n/a | **ROLLBACK_ONLY** |
| `/dashboard#home` … `#settings` | Same document, client hash | same as `/dashboard` | same | same | same | same | page painters | **PRODUCTION** |

Legacy `/dashboard/*` paths (settings, carts, vip, messages) **redirect** into `/dashboard#…`. They do not own a second renderer.

`/dashboard/analytics` and `/dashboard/normal-carts/operations` are **legacy operational** pages, not the canonical Merchant UI V2 shell. Do not use them for Home/Workspace visual proof.

## Not Merchant UI

| ROUTE | PURPOSE | CLASS |
|-------|---------|-------|
| `/` | Public marketing landing | **NOT MERCHANT** |
| `/login` `/signup` | Auth | **NOT MERCHANT** |
| `/preview/product-excellence*` | Isolated preview | **DEV / LEGACY** |
| `/preview/executive-knowledge` | Isolated preview | **DEV / LEGACY** |
| `/dev/cart-workspace-render` | Workspace fixture HTML | **DEV_ONLY** |
| Admin `/admin/*` | Operator UI | **NOT MERCHANT** |

## Living Store review

`GET /dev/living-store-home-review` does **not** render a private template. It issues a demo-primary session cookie, **forces canonical V2**, and redirects to `/dashboard#home`.

`POST /dev/living-store-home-review-session` is the JSON equivalent (session only). The browser must still open `/dashboard`.
