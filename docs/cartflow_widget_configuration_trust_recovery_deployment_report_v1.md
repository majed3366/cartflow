# Widget Configuration Trust Recovery Deployment Report v1

**Date (UTC):** 2026-06-11  
**Type:** Deployment and production verification only — no new fixes  
**Commit:** `a7fc6d174b349bb2ea22a1295fa5c1ad8324971e` (`a7fc6d1`)  
**Branch:** `origin/main`  
**Production host:** [https://smartreplyai.net](https://smartreplyai.net)  
**Reference storefront:** [https://4hz49e.zid.store/](https://4hz49e.zid.store/)

---

## Executive summary

**Widget Configuration Trust Recovery v1 is deployed to production.**

Railway picked up `a7fc6d1` within ~40s of push. Production verification confirms:

- Trust diagnostics route **exists** (HTTP 401 unauthenticated — was **404** pre-deploy)
- Unresolved identity **fail-closed** (HTTP **422** `store_identity_unresolved`)
- Reference Zid storefront **no `demo` slug** in widget API calls
- Static assets include Recovery v1 guards (`isProductionStorefrontContext`, client cache bust)

**Admin-authenticated trust JSON body** was not captured in this deploy verification — `CARTFLOW_ADMIN_PASSWORD` in the deploy environment did not establish an admin session (`/admin/operations/login?e=1`). Route presence is proven; full payload verification is recommended in Closure Audit v2 with valid admin credentials.

---

## Phase 1 — Pre-deploy check

| Check | Result |
|-------|--------|
| Trust recovery files staged (15 files) | PASS — no unrelated lifecycle/visual-gate files in commit |
| Trust diagnostics service | Included — `services/widget_configuration_trust_v1.py` |
| Admin route | Included — `routes/admin_operations.py` |
| Tests | Included — `tests/test_widget_configuration_trust_recovery_v1.py` |
| Unrelated working-tree changes | Left unstaged (lifecycle, screenshots, etc.) |

---

## Phase 2 — Test verification

| Suite | Result |
|-------|--------|
| `tests/test_widget_configuration_trust_recovery_v1.py` | **PASS** (9 tests) |
| `tests/test_widget_settings_runtime_truth_audit_v1.py` | **PASS** (10 tests) |
| `tests/test_cartflow_widget_runtime_public_config.py` | **PASS** (6 tests) |
| `tests/test_widget_public_store_canonical_v1.py` | **PASS** (3 tests) |

**Total:** 28 passed

---

## Phase 3 — Commit

```
a7fc6d174b349bb2ea22a1295fa5c1ad8324971e
Widget Configuration Trust Recovery v1
```

**Root causes in commit message:** RC1, RC3, RC4, RC5, RC6, RC7

---

## Phase 4 — Push and deployment

| Step | Result |
|------|--------|
| `git push origin main` | SUCCESS (`8a7100f..a7fc6d1`) |
| Railway deploy detected | ~20–40s after push (poll iteration 1) |

**Deploy poll evidence:**

| Iteration | `isProductionStorefrontContext` | `cache_invalidated` in fetch.js | Trust route | Unresolved slug |
|-----------|--------------------------------|--------------------------------|-------------|-----------------|
| 0 (pre) | false | false | **404** | HTTP 200, `ok: true` |
| 1 (post) | **true** | **true** | **401** | HTTP **422**, `store_identity_unresolved` |

---

## Phase 5 — Production route verification

| Endpoint | Pre-deploy | Post-deploy |
|----------|------------|-------------|
| `GET /api/admin/operations/widget-configuration-trust?storefront_slug=4hz49e` | **404 Not Found** | **401 Unauthorized** (route registered; auth required) |

**Interpretation:** Route deployment **PASS**. Unauthenticated 401 confirms handler exists; 404 pre-deploy confirmed it was missing.

**Authenticated JSON body:** Not captured — admin login returned `?e=1` (invalid password for this environment). Re-verify in Closure Audit v2 with working admin session.

---

## Phase 6 — Storefront probe (`4hz49e.zid.store`)

**Script:** `scripts/_zid_storefront_widget_truth_probe.py`  
**Output:** `scripts/_zid_probe_out.json`  
**Result:** `PROBE_OK store_slug=4hz49e`

### Network capture

```
GET .../public-config?store_slug=4hz49e&_rt=v2-zid-cart-sync-v1
GET .../ready?store_slug=cartflow-42b491&session_id=cf-...
```

| Check | Result |
|-------|--------|
| `store_slug=demo` in requests | **NO** |
| `fallback_demo` in slug resolution | **NO** |
| Widget API slugs | `4hz49e`, `cartflow-42b491` |
| Identity assertions | `passed: true` |

### Public-config body (reference store)

| Field | Value |
|-------|-------|
| `request_store_slug` | `4hz49e` |
| `canonical_store_slug` | `cartflow-42b491` |
| `widget_name` | `CARTFLOW` |
| `widget_primary_color` | `#F2712C` |
| `cartflow_widget_enabled` | `true` |

---

## Phase 7 — Trust Recovery v1 validation (production)

### 1. Unresolved identity — **PASS**

```
GET /api/cartflow/public-config?store_slug=cf-trust-deploy-probe-v1
→ HTTP 422
→ {"ok": false, "error": "store_identity_unresolved", "canonical_store_slug": null}
```

No silent defaults. No demo substitution.

### 2. Canonical slug handling — **PASS**

```
GET /api/cartflow/public-config?store_slug=4hz49e
→ request_store_slug=4hz49e, canonical_store_slug=cartflow-42b491
→ ready uses cartflow-42b491 (storefront probe)
```

### 3. Cache invalidation (static deploy) — **PASS**

Production `cartflow_widget_fetch.js` contains `cache_invalidated` and canonical-change cache bust logic (post-deploy poll).

Behavioral re-test after merchant alias change: defer to Closure Audit v2.

### 4. Trust diagnostics endpoint — **PASS (route)**

Endpoint registered on production. Full operational JSON pending valid admin auth.

---

## Files deployed (15)

| Area | Files |
|------|-------|
| Server identity/cache | `services/widget_config_cache.py`, `services/dashboard_store_context.py`, `services/merchant_general_settings.py` |
| Trust diagnostics | `services/widget_configuration_trust_v1.py` |
| Routes | `routes/cartflow.py`, `routes/admin_operations.py` |
| Storefront runtime | `static/cartflow_storefront_store_slug.js`, `static/cartflow_widget_runtime/*.js` (config, fetch, flows, shell) |
| Tests | `tests/test_widget_configuration_trust_recovery_v1.py`, `tests/test_widget_settings_runtime_truth_audit_v1.py` |
| Docs | `docs/cartflow_widget_configuration_trust_recovery_report_v1.md`, `docs/SYSTEM_SUMMARY.md` |

---

## Deployment result

| Item | Status |
|------|--------|
| Commit pushed | SUCCESS |
| Railway deploy | SUCCESS |
| Fail-closed identity on prod | VERIFIED |
| Trust route on prod | VERIFIED (401, not 404) |
| Reference storefront identity | VERIFIED (no demo) |
| Admin trust JSON payload | NOT VERIFIED (auth env) |

---

## Stop line

Deployment complete. **Do not run Closure Audit v1 again** — next step is **Widget Configuration Trust Closure Audit v2** (post-deploy, with admin auth + full behavioral matrix).

No roadmap work in this task.
