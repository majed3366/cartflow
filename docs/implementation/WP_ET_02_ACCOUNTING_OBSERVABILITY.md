# WP-ET-02 — Accounting + Observability Stubs + Gate A Harness

**Status:** Implemented — await review / approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-02 (Blueprint §11)  
**Dependencies:** WP-ET-00 + WP-ET-01 (approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) §1.1 C-04/C-05, §8, §9 Gate A, §11 WP-ET-02  

**Rollback point:** Stage 1 (disable/unused modules; clear process ledger; no DB migration)

---

## 1. Implemented Blueprint scope

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-04 Accounting skeleton + C-05 Observability stubs + Gate A harness |
| **Expected output** | Counters / reason codes; admin read path |
| **Verification** | Synthetic increment tests |
| **Not in scope** | Observation Normalizer (WP-ET-03), C-03, family publishers, Bundle Composer, consumer cutover, BFSV, Reality Validation, Gate F/G execution |

---

## 2. Touched components

| Path | Change |
|------|--------|
| `services/evidence_truth/accounting_v1.py` | **Added** — C-04 ledger, stage counters, reject/violation/ownership audits, silent-loss detector |
| `services/evidence_truth/observability_v1.py` | **Added** — C-05 §8 signal snapshot + admin diagnostics read path |
| `services/evidence_truth/gate_a_harness_v1.py` | **Added** — synthetic Gate A harness |
| `services/evidence_truth/__init__.py` | **Modified** — export WP-ET-02 surfaces |
| `tests/test_evidence_truth_wp_et_02_accounting_observability_v1.py` | **Added** — synthetic verification |
| `docs/implementation/WP_ET_02_ACCOUNTING_OBSERVABILITY.md` | **Added** — this report |

**Untouched:** `main.py`, routes, Business Findings, Knowledge, Bundle loaders, Widget, WhatsApp, Dashboard, Simulator.

---

## 3. Contracts exercised

| Contract / rule | How |
|-----------------|-----|
| ET-9 No Silent Evidence Loss | `detect_silent_loss()` trips P0 when `raw_in < observation_out + rejected + in_flight` |
| §7.1 reject reason codes | `record_reject(reason)` increments + audit sample |
| §8 accounting invariant | `check_invariants()` |
| §8 observability signals | health, freshness*, coverage*, latency*, volume, violations, rejected, missing ownership, accounting |
| Gate A | `run_gate_a_harness_v1()` synthetic pass/fail report |
| OE-1 (sample) | Contract violation counter accepts `OE-1` |

\*Freshness / coverage / latency remain **stub** until WP-ET-03+ publishers feed timestamps.

---

## 4. Runtime paths touched

| Path | Status |
|------|--------|
| Production ingress | **None** |
| EvidenceBundle / Knowledge / Findings | **None** |
| Merchant UI | **None** |
| HTTP admin route | **Not added** (avoids production activation); admin read path is the library callable below |
| Process-global ledger | Exists at **zero traffic** until later WPs call increment APIs |

**Admin read path:** `get_evidence_truth_admin_diagnostics_v1()` → `{ accounting, observability, zero_traffic }`.

---

## 5. Flags and defaults

| Item | State |
|------|-------|
| All `CARTFLOW_EVIDENCE_*` consumer flags | **OFF** (unchanged; WP-ET-02 adds none) |
| Gate F / Gate G `execution_authorized` | **False** |
| Gate A harness | Runnable for synthetic verification only |

---

## 6. Persistence impact

| Class | Impact |
|-------|--------|
| Canonical DB | **None** |
| Derived / ephemeral | In-process ledger + ring-buffer audit samples (max 200) |
| Projections / snapshots / caches | **None** |
| Migrations | **None** |

---

## 7. Observability impact

| Signal | WP-ET-02 behaviour |
|--------|-------------------|
| health | `up` / `degraded` / `down` from accounting invariants |
| volume | Live from stage counters |
| rejected evidence | By reason code |
| contract violations | By rule id |
| missing ownership | Counter |
| evidence accounting | Invariant report + silent_loss_trips |
| freshness / coverage / latency | Stub placeholders (`status=stub`) |
| merchant_visible | Always `false` |

Named ops dashboards listed in payload metadata only (not UI).

---

## 8. Verification

| Suite | Result |
|-------|--------|
| WP-ET-02 synthetic tests | **8 passed** |
| WP-ET-00 spine | **15 passed** |
| WP-ET-01 contract/registry | **10 passed** |
| Findings + merchant evidence registry | **25 passed** |
| Combined verification run | **58 passed** |
| Feature flags default OFF | Confirmed |
| No production-path imports of `evidence_truth` | Confirmed (services outside package, routes, `main.py`) |
| Gate F/G not authorized / not executed | Confirmed |
| Rollback point | Stage 1 — `reset_evidence_accounting_ledger_v1()` + remove new modules |
---

## 9. Rollback point

**Stage 1 / WP-ET-02:**

1. Stop calling accounting increment APIs (none wired in production yet).  
2. `reset_evidence_accounting_ledger_v1()`.  
3. Revert/remove `accounting_v1.py`, `observability_v1.py`, `gate_a_harness_v1.py` if needed.  

No DB rollback. No merchant behaviour rollback required.

---

## 10. Deferred work

| Package | Content |
|---------|---------|
| **WP-ET-03** | Observation Normalizer shadow dual-write + accounting linkage |
| **WP-ET-04** | C-03 Eligibility & Freshness Engine |
| **WP-ET-05+** | Family publishers incrementing accounting on real paths |
| **Later** | Optional HTTP admin diagnostics route (if Product/Ops requests) |
| **WP-ET-13** | Gate F/G (**not authorized**) |

---

## 11. Architectural deviations

**None.**

WP-ET-02 delivered C-04/C-05 skeletons, Gate A harness, counters/reason codes, and admin read path as a library diagnostics API without expanding into WP-ET-03 or consumer cutover.

---

## 12. STOP

WP-ET-02 complete pending review.

**Do not begin WP-ET-03** until approved.

---

*End of WP-ET-02 implementation report.*
