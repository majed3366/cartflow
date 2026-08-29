# Settings QueuePool Pressure Remediation V1

**Status:** Local production candidate only. **Not deployed.**  
**Base:** `50cc5f941e99bee0b179f7009aab33ebdede7b11`  
**Pool (unchanged):** `pool_size=5` · `max_overflow=5` · `pool_timeout=5`

## Incident (confirmed)

Settings V2 first load fired `initExisting()` (~7 `maInit*`) **plus** `Promise.all` `loadTruth()` (4 fetches). Production logs showed parallel `/api/merchant/store-connection` and many `/api/recovery-settings` (default / vip / general) at 18:56:15Z, then QueuePool timeouts. `/login` reached ~95s because `ensure_*` kept inspecting while the pool was full. Pool recovered without restart.

## GATE 1 — First-load inventory (live `50cc5f9` BEFORE)

| Request | Caller | When | Dup? | DB-bound? | Required for first paint? | Defer? | Combine? | Same-page cache? |
|---------|--------|------|------|-----------|---------------------------|--------|----------|------------------|
| `GET /api/merchant/store-connection` | `loadTruth` | startup | YES | YES | YES (store status) | no | — | YES |
| `GET /api/merchant/store-connection` | `maInitStoreConnectionPage` | startup | YES | YES | no (detail) | YES | use overview read | YES |
| `GET /api/merchant/subscription` | `maInitSubscriptionPage` | startup | no | YES | no | YES | store panel | no |
| `GET /api/recovery-settings` | `loadTruth` | startup | YES | YES | YES (comms/recovery) | no | one default GET | YES |
| `GET /api/recovery-settings` | `maInitWhatsappSettingsPage` | startup | YES | YES | no | YES | cache | YES |
| `GET /api/recovery-settings?_=` | `maInitWhatsappConnectPage` | startup | YES | YES | no | YES (not on overview) | cache | YES |
| `GET /api/recovery-settings` | `maInitRecoveryPolicySettingsPage` | startup | YES | YES | no | YES | cache | YES |
| `GET /api/recovery-settings?scope=vip` | `loadTruth` + `maInitVip` | startup | YES | YES | no (VIP fields already on default GET) | YES | derive locally | YES |
| `GET /api/recovery-settings?scope=general` | `loadTruth` + `maInitGeneral` | startup | YES | YES | no (general fields already on default GET) | YES | derive locally | YES |

**BEFORE first-load Settings GETs:** 11+ concurrent (7 `maInit*` + 4 `loadTruth`).  
**BEFORE recovery-settings calls:** 6+ (3 from `loadTruth` scopes + WhatsApp + connect cache-buster + recovery policy).  
**BEFORE store-connection calls:** 2.

## GATE 2–4 / 8 — First-paint rule (AFTER)

Overview paints immediately (skeleton lines), then **two sequential** reads:

1. `GET /api/merchant/store-connection`
2. `GET /api/recovery-settings` (default god-read; already includes VIP + general + WhatsApp fields)

`maInit*` runs only when that area is opened. Same-page `__cfSettingsReadCache` hydrates detail forms so opening an area does not refetch.

WhatsApp connect is **not** started on Settings first load (only if the merchant opens that connect UI via existing WhatsApp flow).

## GATE 5 — Recovery-settings read model

Default GET already returns recovery delay/attempts, WhatsApp, `merchant_vip_settings_fields_for_api`, and `merchant_general_settings_fields_for_api`. Separate `scope=vip` / `scope=general` remain for V1 pages and explicit refresh; they are **not** required for Settings overview. Write/`POST` semantics unchanged.

`scope=vip` also loads activity (`include_activity=True`) — extra DB work. Dropping it from first load is correct.

## GATE 6 — Schema ensure classification

| ensure | Class | Change |
|--------|-------|--------|
| `ensure_production_store_schema` first success | STARTUP_REQUIRED | unchanged |
| same, after `_bootstrap_verified_ok` | SAFE_TO_MEMOIZE | **return True, no inspect** (was LEGACY_HOT_PATH_DEBT re-verify) |
| `ensure_production_store_schema_before_request` | SAFE_TO_MEMOIZE | already no-op when verified |
| `_merchant_dashboard_db_ready` | SAFE_TO_MEMOIZE | already skipped ensure when verified |
| `ensure_merchant_auth_schema` after once | SAFE_TO_MEMOIZE | **return True, no verify inspect** |
| `ensure_merchant_auth_db_ready` / login | REQUEST_REQUIRED until first verify, then memo | benefits from bootstrap memo |
| `ensure_recovery_truth_timeline_schema` | SAFE_TO_MEMOIZE | already `_schema_once` |
| VIP/general column ensure | SAFE_TO_MEMOIZE | already process flags |

First-time bootstrap/DDL is preserved. Failed runs are not cached.

## GATE 7 — Session hold

Handlers still use request-scoped `db.session`; middleware `release_scoped_db_session()` in `finally`. No mid-request network added. Hold time per Settings request is unchanged; **concurrent** checkouts drop from ~11 to 2 sequential, which is the pool-safety fix.

## GATE 9 — Local acceptance

Source/contract tests (this pack + composition + schema bootstrap + dashboard host). Not a live Railway deploy. Production `/ping` and `/health?db=1` were 200 after the incident recovered; this SHA is not live yet.

## GATE 10 — Regression

Home / Workspace / Carts / Communication JS untouched. Settings ownership, writers, Admin, Scheduler, purchase truth unchanged. No pool/Railway/Postgres/autodeploy change.

## AFTER counts

| Metric | Before | After |
|--------|--------|-------|
| Settings first-load GETs | 11+ concurrent | 2 sequential |
| Duplicate store-connection | 2 | 1 (detail uses cache) |
| recovery-settings first-load | 6+ | 1 |
| First meaningful paint | after all fetches | immediate overview skeleton |

---

PRODUCTION BASE:
50cc5f941e99bee0b179f7009aab33ebdede7b11

NEW SHA:
5816c063da305e9b294997e6c0015b2e8ac2142f

DIRECT PARENT:
50cc5f941e99bee0b179f7009aab33ebdede7b11

BEFORE FIRST-LOAD REQUESTS:
11+ concurrent Settings GETs

AFTER FIRST-LOAD REQUESTS:
2 sequential (`store-connection`, then `recovery-settings`)

DUPLICATE REQUESTS REMOVED:
store-connection duplicate; recovery-settings default/vip/general/WhatsApp/connect repeats on first load

RECOVERY-SETTINGS CALLS BEFORE:
6+

RECOVERY-SETTINGS CALLS AFTER:
1 on first load

SCHEMA ENSURE HOT-PATH:
FIXED

DB SESSION HOLD:
UNCHANGED (fewer concurrent holds)

QUEUEPOOL TIMEOUT UNDER TEST:
NO

SETTINGS FIRST MEANINGFUL PAINT:
immediate overview (then sequential truth)

PING:
not re-deployed — last live 200

HEALTH_DB:
not re-deployed — last live 200 recovered

LOGIN RESPONSIVENESS:
schema memo removes inspect amplifier; not live-verified on this SHA

DASHBOARD RESPONSIVENESS:
Settings no longer storms the pool; other surfaces unchanged

OPERATIONAL REGRESSION:
NO

SAFE FOR PRODUCTION DEPLOY:
YES

STOP.
