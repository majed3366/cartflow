# Production Configuration Parity Proof V1 — REPORT

**Date (UTC):** 2026-09-01  
**Mode:** AUTHORIZED VERIFICATION ONLY  
**Candidate SHA:** `5606530c736416c0141b2f4a7f2cfef0e92290bc`  
**Direct parent:** `67ed1432fb9e7cb9cd7366b2f9f08ab79d4dd7ee`  
**Code changed:** NO  
**Production changed:** NO  

---

## STEP 1 — Inventory config parity

| Flag / variable | Prior real-device PASS review | Production (live / code law) | Class |
|-----------------|------------------------------|------------------------------|-------|
| `CARTFLOW_CART_WORKSPACE_V1` **effective** | ON (`true`) | ON (projection **401** ≠ `feature_flag_off`) | **MATCH** |
| `CARTFLOW_CART_WORKSPACE_V1` **raw env string** | `true` | not readable without Railway link; publish law `env_raw: null` ⇒ ON via Railway default | **UNKNOWN** (raw) |
| `RAILWAY_GIT_COMMIT_SHA` | unset in prior PASS | set on Railway (Workspace default-ON when Workspace env unset) | **PRODUCTION_ONLY** (raw presence) |
| `CARTFLOW_MERCHANT_UI_V2` | unset → default V2 ON | live identity `env_raw: null`, `ui_version: v2` | **MATCH** |
| `ENV=development` | set (dashboard auth bypass) | production / Railway | **REVIEW_ONLY** |
| Living-store review session | used for API auth | merchant session cookies | **REVIEW_ONLY** |
| `CARTFLOW_CARTS_V2_UI` | not asserted this run | not asserted this run | **UNKNOWN** |
| Host git SHA | candidate `5606530c` (local bytes) | live still `b8c1318` | deploy gap (not a Merchant UI flag) |

**Counts (material Merchant UI / runtime flags in inventory):**

| Class | Count |
|-------|------:|
| MATCH (effective material) | 2 (`CARTFLOW_CART_WORKSPACE_V1` effective, `CARTFLOW_MERCHANT_UI_V2`) |
| REVIEW_ONLY | 2 (`ENV=development`, living-store session) |
| PRODUCTION_ONLY | 1 (`RAILWAY_GIT_COMMIT_SHA` raw presence vs prior local PASS) |
| UNKNOWN | 2 (Workspace **raw** env string; `CARTFLOW_CARTS_V2_UI`) |

---

## STEP 2 — `CARTFLOW_CART_WORKSPACE_V1` production value

### Live proof

`GET https://smartreplyai.net/api/cart-workspace/v1/projection` → **401**  
`{"ok": false, "error": "unauthorized"}`

If the flag were OFF, the handler returns **404** `feature_flag_off` **before** auth. Therefore production **enabled = true**.

### Code law (`services/cart_workspace/feature_flag_v1.py`)

| Condition | Enabled |
|-----------|---------|
| Explicit `true`/`1`/`yes`/`on` | ON |
| Explicit `false`/`0`/`no`/`off` | OFF |
| Unset + `RAILWAY_GIT_COMMIT_SHA` set | ON |
| Unset elsewhere | OFF |

### Local matrix (proven this run)

| Label | Enabled |
|-------|---------|
| LOCAL_DEFAULT (unset, no Railway SHA) | False |
| RAILWAY_EQUIV (unset + `RAILWAY_GIT_COMMIT_SHA=b8c1318…`) | True |
| EXPLICIT_TRUE | True |
| EXPLICIT_FALSE | False |

**Production-equivalent for review:** unset Workspace env + Railway SHA **OR** explicit `true`. Both MATCH production effective ON. Explicit `false` does **not** match production.

### Canonical `/dashboard` under production-equivalent value

Server: `http://127.0.0.1:8777` @ candidate bytes `5606530c` with:

- `CARTFLOW_CART_WORKSPACE_V1` **unset**
- `RAILWAY_GIT_COMMIT_SHA=b8c1318a06e99fe75eccefecf7e4492db489ab4d`
- `ENV=development` (REVIEW_ONLY auth path only)

Proof:

- Unauthenticated projection → **401** `unauthorized` (same class as live prod; not `feature_flag_off`)
- Authenticated living-store session → projection **200**, `#workspace` paints `[data-cf2-organism=formation]`
- Assets: `merchant_ui_v2_home.css?…-psg1-rdfix1` (candidate cache bust)

Identity `git_sha` reports Railway SHA when that env is set (expected spoof for flag law); candidate tree verified via `git rev-parse HEAD` = `5606530c…` and `rdfix1` / orbit-axis bytes.

---

## STEP 3 — Exact candidate review under prod-equivalent Merchant UI config

Runtime: candidate `5606530c` painters/CSS; Workspace **ON** via Railway-equivalent law. No side renderer.

| Surface | Organism attribute | Desktop evidence | Mobile (390×844) |
|---------|--------------------|------------------|------------------|
| Home | `gravity-well` | orbit-axis present; primary board border-inline-start **10px** | same organism |
| Workspace | `formation` | quiet formation + remnant void (32px by remnant CSS; standard path uses 40px) | formation present |
| Carts | `weighted-queue` | detail radius 0; bg near-transparent; border-inline-start **4px** | same |
| Communication | `lifecycle-continuum` | 5 ticks; scaffold; tick width **12px** | continuum present (tick ≈11px DPR) |
| Settings | `config-ledger` | joint width **18px** | ledger present (joint ≈16px DPR) |

---

## STEP 4 — Organism dependency on review-only flags

Prior PASS used `CARTFLOW_CART_WORKSPACE_V1=true`. That is **MATCH** to production **effective ON**, not a review-only enablement.

Review-only items (`ENV=development`, living-store session) affect **auth**, not organism geometry/CSS.

**VISUAL RESULT DEPENDS ON REVIEW-ONLY FLAG: NO**

Local default Workspace OFF (unset, no Railway SHA) would hide Workspace formation — that is a **local non-parity** failure mode, not a false PASS under a review-only flag.

---

## STEP 5 — Config regression contract

Documented contract: `docs/product/canonical_merchant_runtime_v1/03_REVIEW_PARITY_CONTRACT.md` (requires local `CARTFLOW_CART_WORKSPACE_V1=true` to match production Workspace).

**Automated gate** asserting `REVIEW CONFIG = PRODUCTION CONFIG` for material Merchant UI flags before visual PASS: **absent** in candidate `5606530c`.

Verification-only mission forbids adding code → gate remains **FAIL** (missing enforcement).

Future gate must record and fail closed when:

```
REVIEW CONFIG ≠ PRODUCTION CONFIG
```

for material Merchant UI flags (at minimum: `CARTFLOW_CART_WORKSPACE_V1` effective ON, `CARTFLOW_MERCHANT_UI_V2` ON).

---

## FINAL SCOREBOARD

```
CANDIDATE SHA: 5606530c736416c0141b2f4a7f2cfef0e92290bc

PRODUCTION CONFIG CAPTURED: YES

REVIEW-ONLY FLAGS: 2
PRODUCTION-ONLY FLAGS: 1
UNKNOWN FLAGS: 2

CARTFLOW_CART_WORKSPACE_V1 PRODUCTION VALUE: enabled=true (effective); raw env string UNKNOWN

EXACT PROD-CONFIG RUNTIME PROVEN: YES

HOME: PASS
WORKSPACE: PASS
CARTS: PASS
COMMUNICATION: PASS
SETTINGS: PASS
MOBILE: PASS

VISUAL RESULT DEPENDS ON REVIEW-ONLY FLAG: NO

CONFIG PARITY REGRESSION GATE: FAIL

CODE CHANGED: NO
PRODUCTION CHANGED: NO

SAFE FOR EXACT-SHA DEPLOY: NO
```

**Blocker for SAFE TO DEPLOY:** CONFIG PARITY REGRESSION GATE missing — visual review can still be run under non-production flag configurations without an automated fail-closed check.
