# Investigation Dashboard

**As of (UTC):** 2026-07-16  
**Framework:** Product Investigation Framework V1  
**Phase status:** INV-002 **Root Cause Confirmed** (architecture review) — do **not** implement; do **not** open Work Packages until DoR

---

## Status counts

| Status | Count | IDs |
|--------|------:|-----|
| Open | 7 | INV-003 … INV-009 |
| Investigating | 0 | — |
| Root Cause Confirmed | 1 | INV-002 |
| Ready for Fix | 1 | INV-001 (WP-6 approved; Checkpoint V2 reviewed; WP-7 gated separately) |
| Implementation | 0 | — |
| Verification | 0 | — |
| Blocked | 0 | — |
| Closed | 0 | — |
| **Total registered** | **9** | Next ID: INV-010 |

---

## Severity counts

| Severity | Count |
|----------|------:|
| Critical | 2 |
| High | 4 |
| Medium | 3 |
| Low | 0 |

---

## Board

| ID | Title | Severity | Status | Owner | Blocked by | Review |
|----|-------|----------|--------|-------|------------|--------|
| INV-001 | Time Authority Drift | Critical | Ready for Fix | Architecture Board | — | [DoR Cert](./INV_001_DEFINITION_OF_READY_CERTIFICATION.md) |
| INV-002 | Merchant Identity Drift | Critical | Root Cause Confirmed | Architecture Board | — | [INV-002_REVIEW.md](./INV-002_REVIEW.md) |
| INV-003 | Knowledge Surface Drift | High | Open | Knowledge + Product | INV-001, INV-002 | — |
| INV-004 | Attention Semantics Drift | High | Open | Product + UX | INV-002, INV-003 | — |
| INV-005 | Setup Lifecycle Drift | High | Open | Product + Ops | INV-002 | — |
| INV-006 | Attribution Semantics Drift | High | Open | Purchase Truth + Product | INV-001 | — |
| INV-007 | Monthly Summary Materialisation Gap | Medium | Open | Dashboard | INV-001, INV-002 | — |
| INV-008 | Visitor Truth Coverage Gap | Medium | Open | Knowledge + Ingress | — | — |
| INV-009 | WP-5 Cross-Surface Database Fixture Instability | Medium | Open | Engineering + Architecture Board | — | [INV-009.md](./INV-009.md) |

---

## Next action (human)

1. Architecture Board accept **INV-002_REVIEW.md** (Root Cause Confirmed).  
2. Only then: authorize **INV-002 Definition of Ready / Implementation Architecture** (separate task).  
3. Do **not** begin INV-002 code fixes from this phase.  
4. INV-001 WP-7 remains separately gated (Timeline/Movement writers) — not started by this review.  
5. Reality Lab merchant walkthrough trust is now dominated by INV-002, not Time Authority windows.
