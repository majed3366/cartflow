# Widget Configuration Trust Recovery Report v1

**Date:** 2026-06-11 (UTC)  
**Scope:** Close findings from Widget Configuration Trust Investigation v1. No UI, Pilot, WhatsApp, or Operational Visibility expansion.

**Mission:** Prove `Merchant Configuration = Runtime Behavior` across Merchant Save → Public Config → Runtime → Observed Storefront Behavior.

---

## Executive summary

Widget configuration trust was recovered through **fail-closed identity**, **dashboard→public-config parity enforcement**, **V2 runtime execution of previously ignored settings**, **cache invalidation on canonical slug change**, and **operator trust diagnostics** (JSON foundation only).

**Closure recommendation:** **HOLD FOR CLOSURE AUDIT** — implementation complete; formal closure audit should confirm production storefront probes (0× `store_slug=demo` on platform hosts) and repeat parity gate in prod.

---

## Files changed

| File | Change |
|------|--------|
| `services/widget_config_cache.py` | Fail-closed unresolved identity; no silent `build_snapshot_from_store_row(None)` for unknown slugs; unresolved snapshots not cached |
| `routes/cartflow.py` | `GET /public-config` and `GET /ready` return HTTP 422 when identity unresolved |
| `services/dashboard_store_context.py` | `dashboard_recovery_store_row()` — shared dashboard store resolver |
| `services/merchant_general_settings.py` | General settings save uses dashboard store row (not `Store.id DESC`) + cache refresh |
| `static/cartflow_storefront_store_slug.js` | Production/embed contexts never demo fallback |
| `static/cartflow_widget_runtime/cartflow_widget_fetch.js` | Production context guard; canonical slug cache bust; fail-closed public-config fetch |
| `static/cartflow_widget_runtime/cartflow_widget_config.js` | Exit-intent template fields on merchant config |
| `static/cartflow_widget_runtime/cartflow_widget_flows.js` | Exit-intent copy from merchant config (exit-intent triggers) |
| `static/cartflow_widget_runtime/cartflow_widget_shell.js` | `widget_style` → `cf-widget-style-*` classes |
| `services/widget_configuration_trust_v1.py` | **New** — RC validation, parity report, visibility diagnostics, closure criteria |
| `routes/admin_operations.py` | `GET /api/admin/operations/widget-configuration-trust` |
| `tests/test_widget_configuration_trust_recovery_v1.py` | **New** — parity + fail-closed + RC structure tests |
| `tests/test_widget_settings_runtime_truth_audit_v1.py` | Updated for V2 style/exit-intent wiring |

---

## Phase 1 — Root cause validation (RC1–RC7)

| RC | Issue | Status | Evidence |
|----|--------|--------|----------|
| **RC1** | Client demo fallback | **Fixed** | `isProductionStorefrontContext()` in slug resolver + fetch; demo only on non-production pages; platform/embed → empty slug + blocked fetch |
| **RC2** | Missing platform permalink resolution | **Fixed** | Hostname extractors for `.zid.store`, `.salla.sa`, `.salla.store` (unchanged; validated in prod probe 2026-06-11) |
| **RC3** | Identity alias gaps → silent defaults | **Fixed** | `build_unresolved_identity_snapshot()` + HTTP 422; unresolved snapshots not cached |
| **RC4** | Dual enable ownership | **Fixed** | General settings save now targets `dashboard_recovery_store_row()`; syncs `widget_enabled` + `cartflow_widget_enabled` on save |
| **RC5** | Runtime execution gaps (`widget_style`, exit copy) | **Fixed** | Phase 5 **Option A — fully support** (see below) |
| **RC6** | Cache stickiness | **Partially fixed** | Client cache bust on canonical slug change; server 8s refresh throttle retained; unresolved not cached |
| **RC7** | Canonical slug split | **Fixed** | Canonical from public-config + cache invalidation when request slug ≠ canonical |

Automated RC structure: `validate_root_causes_v1()` in `services/widget_configuration_trust_v1.py`.

---

## Phase 5 — Execution gap decision

**Decision: A — Fully support**

- `widget_style` → V2 shell applies `cf-widget-style-minimal|modern|bold` via `applyChromeStyleClasses`.
- `exit_intent_custom_text` / tone / mode → V2 flows use `getExitIntentOpeningText()` for exit-intent trigger tags.

**Reasoning:** Merchant-visible settings must never be ignored at runtime; legacy widget already honored these fields; removing from dashboard would be a product regression.

---

## Phase 3 & 7 — Parity verification

**Composer:** `build_configuration_parity_report()` compares dashboard bundle vs live `public-config` for 13 critical fields (enabled, delays, triggers, VIP, style, exit copy, name, color).

**Tests (local):**

```
tests/test_widget_configuration_trust_recovery_v1.py — 9 passed
tests/test_widget_settings_runtime_truth_audit_v1.py — 10 passed
tests/test_cartflow_widget_runtime_public_config.py — 6 passed
```

**Sample parity gate:** After merchant-widget-settings save, `parity_pass=true` for dashboard store slug.

---

## Phase 6 — Cache trust

| Layer | Behavior |
|-------|----------|
| Server memory | Unresolved identity not written to `_store_snapshots`; dashboard save updates all alias keys via `update_from_dashboard_store_row` |
| Client session | `_sessionPublicConfigCached` cleared when `canonical_store_slug` differs from prior or from `request_store_slug` |
| Failed identity | Client marks ready blocked; does not cache `ok:false` payloads |

---

## Phase 8 — Trust diagnostics (foundation)

**Endpoint:** `GET /api/admin/operations/widget-configuration-trust?storefront_slug=<slug>` (admin auth)

**Answers:**

- `visibility_diagnostics.would_show_widget` / `blockers` / `why_not`
- `configuration_parity.mismatches`
- `root_cause_validation` RC statuses
- `closure_criteria.checks` + `closure_recommendation`

**Dev parity:** `GET /dev/widget-runtime-truth` (existing) still compares dashboard vs public-config vs beacon.

---

## Phase 9 — Trust recovery audit

| Area | Result |
|------|--------|
| Identity | Unresolved slugs fail closed (422); sandbox `demo`/`demo2`/`default` still intentional |
| Config delivery | Dashboard general save → same store row as GET recovery-settings |
| Runtime execution | Style + exit-intent template wired in V2 |
| Cache | Canonical slug change busts client cache; unresolved not server-cached |
| Parity verification | Automated tests + admin JSON report |

---

## Phase 10 — Closure criteria

| # | Criterion | Local verification |
|---|-----------|-------------------|
| 1 | 0 production storefront requests use `store_slug=demo` | Code guards in place; **prod re-probe required** for closure sign-off |
| 2 | Public config matches merchant configuration | Parity tests pass after cache warm |
| 3 | Runtime matches public config | Existing runtime truth + new V2 fields |
| 4 | Observed behavior matches runtime | Beacon/truth gate unchanged; style/exit copy now configurable |
| 5 | No unresolved slug serves defaults silently | 422 + `store_identity_unresolved` |
| 6 | No merchant-visible setting ignored | RC5 closed (style + exit copy) |
| 7 | Parity verification passes | `test_widget_configuration_trust_recovery_v1.py` |
| 8 | Trust diagnostics explain behavior | Admin JSON endpoint |

**Recommendation:** **HOLD FOR CLOSURE AUDIT** — run production storefront probe + admin trust JSON on reference store (`4hz49e` / `cartflow-42b491`) before final CLOSE.

---

## Root causes remaining

None in code paths covered by this recovery. **RC6** server refresh throttle (8s) remains by design; merchant changes propagate immediately on dashboard save via `update_from_dashboard_store_row`.

---

## No regression statement

Did not modify: Purchase Truth, Lifecycle Truth, Scheduler Ownership, Operational Visibility Foundation, Recovery Engine, WhatsApp Engine, Merchant Dashboard UI, Store Setup UI.

---

## Stop line

Roadmap / Pilot work **not** continued. Await **Widget Configuration Trust Closure Audit**.
