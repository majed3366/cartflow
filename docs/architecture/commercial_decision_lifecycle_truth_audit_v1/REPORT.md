# Commercial Decision Lifecycle Truth Audit V1 — Report

**Date (UTC):** 2026-09-05  
**Mode:** READ-ONLY  
**Decision Console V1.1:** FROZEN / visually approved (untouched)  
**COL / intelligence / production:** UNCHANGED  
**IMPLEMENTATION AUTHORIZED:** NO  
**DEPLOY:** NO  

Docs:

- `00_EXISTING_LIFECYCLE_INVENTORY.md`
- `01_REUSE_MATRIX.md`
- this `REPORT.md`

---

## Executive verdict

CartFlow already has **strong lifecycle machinery for recovery carts, schedules, purchase closure, timeline, and business findings**.

It does **not** have a persisted **commercial decision lifecycle** that can truthfully support:

action chosen → under measurement → recheck due → won/lost/learned.

CDA arcs and Decision Console modes that *look* like those states are **UI paint / COL-derived presentation**, not authoritative truth.

**Audit before extension: PASS.**  
**Reuse before invention: COL readiness + compositional keys + BFL patterns; invent only a narrow commitment record later.**  
**No new state machine without proof: do not implement now.**

---

## Phase answers (compressed)

### Existing lifecycle / state models

Recovery archive; RecoverySchedule; PurchaseTruth + Closure + Attribution; CustomerLifecycle classifier; RecoveryTruthTimeline; Followup/Delivery/Logs; BusinessFindings + BFL; DCE; Merchant Decision Registry; Cart Workspace shadow; OGL; COL; CDA/Console; product metrics/diagnostics/surfaces.

### Authoritative vs derived

- **Persisted authoritative:** schedules, purchase/closure, timeline, archive, findings/BFL, logs/delivery, abandoned cart, product metrics, …
- **Derived authoritative (merchant cart):** CustomerLifecycleStatesV1
- **Derived commercial readiness:** COL truth classes, OGL objects
- **UI-only:** CDA arcs, Console modes, sessionStorage COL focus, shadow workspace decisions

### Reuse vs separate

- Recovery / cart / schedule / purchase systems: **domain-specific — keep separate**
- COL readiness + `opportunity_id`: **reuse as evidence/soft key**
- Findings/BFL: **reuse patterns; do not overload as action commitment**
- Console/CDA: **never SoT**

### Minimum safe extension (future only)

Narrow persisted **commercial decision commitment** (Option C) with action time, baseline, measure window — owned by merchant write API; measurement/recheck preferably derived; outcomes deferred.

---

## FINAL SCORECARD

EXISTING LIFECYCLE SYSTEMS:  
14+ inventoried (see inventory)

AUTHORITATIVE PERSISTED:  
9+

AUTHORITATIVE DERIVED:  
5+

UI-ONLY STATES:  
3+ (CDA/Console, COL focus, cart workspace shadow)

SCHEDULER STATES:  
2+ (RecoverySchedule, provider retry)

COMMERCIAL DECISION STABLE IDENTITY EXISTS:  
PARTIAL  
(COL/OGL/finding compositional IDs; no persisted commitment across action→outcome)

MEASUREMENT TRUTH EXISTS:  
NO  
(copy fields + unrelated attribution/metric tables only)

RECHECK TRUTH EXISTS:  
PARTIAL  
(`recheck_ar` / OGL condition text + CDA paint; no persisted due/fired truth)

OUTCOME ATTRIBUTION EXISTS:  
PARTIAL  
(purchase attribution for recovery carts ≠ commercial decision WON)

LEARNING MEMORY EXISTS:  
NO  
(finding resolve/supersede ≠ LEARNED)

DIRECTLY REUSABLE SYSTEMS:  
COL truth gate + `opportunity_id` soft key; store-isolation conventions; BFL advance/idempotency patterns; timeline append pattern; metrics/purchase as measurement *inputs*

PARTIALLY REUSABLE SYSTEMS:  
Business Findings status vocabulary; OGL/COL measure/recheck contracts; Decision Console as derived presentation

DO-NOT-REUSE SYSTEMS:  
RecoverySchedule statuses; CustomerLifecycle waiting_*; CDA arcs as SoT; cart archive reopen; purchase_completed as WON; cart workspace shadow; RRV/sim missions

MINIMUM NEW PERSISTED TRUTH REQUIRED:  
Open commercial decision **commitment** row (action_chosen_at, baseline snapshot, measure_until, opportunity_key, store_slug) — only when implementation is authorized

RECOMMENDED V1 COMMERCIAL STATES:  
INSUFFICIENT_EVIDENCE (derived), READY (derived), ACTION_CHOSEN (persisted), UNDER_MEASUREMENT (derived), RECHECK_DUE (derived)

DEFERRED STATES:  
DISCOVERED, WON, LOST, LEARNED

SCHEDULER IMPACT IF IMPLEMENTED:  
LOW / MEDIUM  
(optional due scan for RECHECK_DUE)

DB IMPACT IF IMPLEMENTED:  
LOW

EXPECTED QUERY COST:  
O(1) attach by store + opportunity_key; no new hot scans on recovery path

SCALE RISK:  
LOW  
(if one open commitment per opportunity key)

RECOMMENDED ARCHITECTURE OPTION:  
**C** — narrow commercial decision commitment record; COL remains evidence composer; Console remains derived paint; do not overload recovery or findings machines

IMPLEMENTATION AUTHORIZED:  
NO

DEPLOY:  
NO

STOP.
