# Product Investigation Registry

**Framework:** Product Investigation Framework V1  
**Opened (UTC):** 2026-07-15  
**Authority:** Architectural + product review (no auto-implementation)  
**ID policy:** Permanent. Never reuse. Closed cases remain archived.

---

## Active registry

| ID | Title | Severity | Category | Status | Owner | Depends on | Case file |
|----|-------|----------|----------|--------|-------|------------|-----------|
| INV-001 | Time Authority Drift | Critical | Architecture / Timeline | Ready for Fix (WP-6 approved; Checkpoint V2 pending review) | Architecture Board | — | [INV-001.md](./INV-001.md) · [INV-001_REVIEW.md](./INV-001_REVIEW.md) · [DoR Cert](./INV_001_DEFINITION_OF_READY_CERTIFICATION.md) |
| INV-002 | Merchant Identity Drift | Critical | Identity / Dashboard | Root Cause Confirmed | Architecture Board | — | [INV-002.md](./INV-002.md) · [INV-002_REVIEW.md](./INV-002_REVIEW.md) |
| INV-003 | Knowledge Surface Drift | High | Knowledge / Product | Open | Knowledge + Product | INV-001, INV-002 | [INV-003.md](./INV-003.md) |
| INV-004 | Attention Semantics Drift | High | UX / Dashboard | Open | Product + UX | INV-002, INV-003 | [INV-004.md](./INV-004.md) |
| INV-005 | Setup Lifecycle Drift | High | Operational / Product | Open | Product + Ops | INV-002 | [INV-005.md](./INV-005.md) |
| INV-006 | Attribution Semantics Drift | High | Purchase Truth / Trust | Open | Purchase Truth + Product | INV-001 | [INV-006.md](./INV-006.md) |
| INV-007 | Monthly Summary Materialisation Gap | Medium | Dashboard / Operational | Open | Dashboard | INV-001, INV-002 | [INV-007.md](./INV-007.md) |
| INV-008 | Visitor Truth Coverage Gap | Medium | Knowledge / Architecture | Open | Knowledge + Ingress | — | [INV-008.md](./INV-008.md) |
| INV-009 | WP-5 Cross-Surface Database Fixture Instability | Medium | Test Infrastructure / Time Authority | Open | Engineering + Architecture Board | — | [INV-009.md](./INV-009.md) |

---

## Status legend

| Status | Meaning |
|--------|---------|
| Open | Filed; awaiting investigation depth / review |
| Investigating | Evidence gathering and RCA in progress |
| Root Cause Confirmed | Architectural review proved RCA; **not** yet approved for implementation |
| Ready for Fix | DoR certified; WP engineering may start only after explicit WP authorization |
| Blocked | Waiting on parent investigation or external decision |
| Fixed | Code/config change landed (separate task) |
| Verified | Closure criteria proven with evidence |
| Closed | Archived; ID retained forever |

---

## Source mapping (Reality Lab trust audit → investigations)

| Lab ID | Lab issue | Investigation |
|--------|-----------|---------------|
| T1 | Merchant signup sees different empty store | INV-002 |
| T2 | Wall-clock Knowledge/KPIs zero for May history | INV-001 → INV-003 |
| T3 | Home “preparing understanding” skeleton | INV-002, INV-005 (symptom surfaces) |
| T4 | Attention question + empty/wait body | INV-004 |
| T5 | Setup readiness vs lived history | INV-005 |
| T6 | `likely_recovery` on simulated/organic purchases | INV-006 |
| T7 | Monthly summary absent | INV-007 |
| T8 | Visitor/checkout metrics unavailable | INV-008 |
| T9 | Hybrid timestamps (May first_seen / July last_seen) | INV-001 |
| T10 | Thin product catalog (7 SKUs) | Deferred — simulator fidelity, not product defect |

---

## Retired / unused IDs

None yet. Next ID to allocate: **INV-010**.

---

## Evidence corpus (shared)

| Artefact | Path / ID |
|----------|-----------|
| Reality Lab report | `REALITY_VALIDATION_LAB_V1_REPORT.md` |
| Identity isolation | `IDENTITY_ISOLATION_REPORT.md` |
| Phase 3 simulator report | `CARTFLOW_STORE_REALITY_SIMULATOR_PHASE_3_REPORT.md` |
| Lab evidence pack | `docs/architecture/reality_validation_lab_v1_small/` |
| Simulation run | `srs_0430adc995264cd5b7576dfdc10649f0` |
| Seed | `20260715` |
| Reality Score | **73.8** overall |
| Screenshots | `01_desktop_home.png` … `04_mobile_carts.png` |
| Knowledge contrast | `sim_now_knowledge.json` |
| Accounting | `lab_evidence.json` |

---

## Governance

1. No significant issue is treated as a bug until it is an Investigation Case.  
2. Child investigations must not be fixed before parent investigations (see dependency graph).  
3. “Ready for Fix” requires accepted root cause + verification plan + closure criteria.  
4. Implementation tasks are created **only after** architectural review approval.  
5. This registry is the permanent index; case files hold full RCA.
