# Merchant V2 Dashboard Startup Fan-Out Remediation V1

BASE SHA: `adac492a513f8270b3df9f5bfc96e757bbb74b34`

NEW SHA: `590f26a7003a07664cb6ed74b7fc444272edcb16`

DIRECT PARENT: `adac492a513f8270b3df9f5bfc96e757bbb74b34`

ROOT CAUSE CONFIRMED: YES

A Merchant V2 `/dashboard` document hosts all five surface modules plus Settings helper scripts. Canonical surface truth is `location.hash` via `currentHash()` in `static/merchant_ui_v2_app.js`. The router already called only the active `loadAndPaint`, but two leaks stacked pool pressure:

1. `merchant_subscription.js` always issued `GET /api/merchant/subscription` on `DOMContentLoaded`, even when Settings was inactive.
2. `loadSection` re-issued the active surface's full startup reads on every `hashchange` and every return visit, with no initialized-state. Rapid same-document navigation (and a second viewport) left previous surface requests in flight against pool 5+5.

`POST /dev/living-store-home-review-session` is not the root cause.

## BEFORE STARTUP REQUEST MAP

Canonical source: `location.hash` → `currentHash()`.

| Surface | DOMContentLoaded | Bootstrap | API calls | Runs while inactive | Can run more than once | Navigation trigger | Cache / initialized |
|---|---|---|---|---|---|---|---|
| HOME | `merchant_ui_v2_app.js` → `loadSection(currentHash())` | `CartFlowUiV2Home.loadAndPaint` | `GET /api/dashboard/summary` | No (router) | Yes — every hash visit / same-hash click | `hashchange` / `go("home")` | None |
| WORKSPACE | same router | `CartFlowUiV2Workspace.loadAndPaint` | `GET /api/cart-workspace/v1/projection` | No (router) | Yes — every visit | `hashchange` / `go("workspace")` | Paint cache is server-side only |
| CARTS | same router | `CartFlowUiV2Carts.loadAndPaint` | `GET /api/dashboard/normal-carts` | No (router) | Yes — every visit | `hashchange` / `go("carts")` | In-module `state` only; always refetch |
| COMMUNICATION | same router | `CartFlowUiV2Comms.loadAndPaint` | `Promise.all`: messages, followups, summary | No (router) | Yes — every visit | `hashchange` / `go("comms")` | `fetchGen` only |
| SETTINGS | same router **plus** `merchant_subscription.js` `bind()` | `CartFlowUiV2Settings.loadAndPaint` + subscription bind | Settings-active: store-connection, recovery-settings (sequential). **Always:** subscription | **YES — subscription on every dashboard load** | Yes — every Settings visit + every page load for subscription | `hashchange` / `go("settings")` / Settings hash aliases | `__cfSettingsReadCache` for detail; overview refetch every visit |

Fresh Home document before this change:

- `GET /api/dashboard/summary`
- `GET /api/merchant/subscription` (inactive Settings leak)

Opening other surfaces added their startup sets immediately, without cancelling prior in-flight work.

## AFTER STARTUP REQUEST MAP

| Active surface | Startup product GETs |
|---|---|
| HOME | `GET /api/dashboard/summary` |
| WORKSPACE | `GET /api/cart-workspace/v1/projection` |
| CARTS | `GET /api/dashboard/normal-carts` |
| COMMUNICATION | `GET /api/dashboard/messages` + `followups` + `summary` (`Promise.all`, preserved) |
| SETTINGS | `GET /api/merchant/subscription` + `GET /api/merchant/store-connection` + `GET /api/recovery-settings` |

Inactive surfaces: zero product-data startup requests.

Return to an already initialized surface: zero extra startup GETs. Same-hash click remains an explicit refresh (`loadSection(..., { force: true })`).

Evidence: `docs/ops/merchant_v2_dashboard_startup_fanout_remediation_v1/REQUEST_MAP.json` from `_request_map.js`.

HOME ACTIVE ONLY: PASS

WORKSPACE ACTIVE ONLY: PASS

CARTS ACTIVE ONLY: PASS

COMMUNICATION ACTIVE ONLY: PASS

SETTINGS ACTIVE ONLY: PASS

INACTIVE SURFACE REQUESTS: 0

SETTINGS QUEUEPOOL REMEDIATION PRESERVED: YES

`merchant_ui_v2_settings.js` unchanged: `settings-queuepool-pressure-remediation-v1`, sequential store-connection then one recovery-settings, no `Promise.all`, no `maInit*` on overview, no `scope=vip` / `scope=general` overview reads. Subscription now fires only when Settings is the active surface.

COMMUNICATION ACTIVE-SURFACE CONCURRENCY: SAFE

Three parallel GETs against pool 5+5 cannot saturate the pool by themselves. The contract already marked this AT LIMIT. Not rewritten.

WORKSPACE PROJECTION DB HOLD: CONTENTION_ARTIFACT (incident 10–35s while other surfaces were also in flight). Alone: paint-cache / durable-snapshot path is bounded; `enrich_fallback` remains a QUERY_PATH_PROBLEM if cache+snapshot miss. No external HTTP while holding the session was found. Not optimized in this task.

COMMUNICATION MESSAGES DB HOLD: CONTENTION_ARTIFACT for the incident 10–35s stacked holds. Alone: EXPECTED_QUERY_COST — `_merchant_recovery_message_history_rows` reads a bounded sent-log window (limit 40, scan cap 200) plus refresh-state. No external work while DB held. Not optimized in this task.

DUPLICATE INITIALIZATION: NO

QUEUEPOOL TIMEOUT DURING VALIDATION: NO

HEALTH_DB: PASS — `GET /health?db=1` → 200, `ok` (TestClient)

LOGIN: PASS — `GET /login` → 200, auth form rendered

DASHBOARD: PASS — V2 template hosted; only the active surface initializes product data; `/ping` → 200 `ok`

DESKTOP: PASS

MOBILE: PASS

No visual composition changes. Hash aliases, GlobalUpbar, contextual drawer, and Settings QueuePool cache tokens (`qpool1`, `nvis1`) preserved. Admin boundary untouched.

OPERATIONAL REGRESSION: NO

SAFE FOR PRODUCTION RECONCILIATION: YES

SAFE TO RESUME VISUAL ASSIMILATION AFTER LIVE VERIFICATION: YES

STOP.

Do not deploy.
Do not begin visual assimilation.
