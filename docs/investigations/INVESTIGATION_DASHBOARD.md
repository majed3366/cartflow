# Investigation Dashboard

**As of (UTC):** 2026-07-16  
**Framework:** Product Investigation Framework V1  
**Phase status:** INV-001 **WP-3 complete (pending Architecture Review)** — do **not** start WP-4

---

## Status counts

| Status | Count | IDs |
|--------|------:|-----|
| Open | 7 | INV-002 … INV-008 |
| Investigating | 0 | — |
| Root Cause Confirmed | 0 | — |
| Ready for Fix | 1 | INV-001 (WP-3 pending Architecture Review) |
| Blocked | 0 | — |
| Fixed | 0 | — |
| Verified | 0 | — |
| Closed | 0 | — |
| **Total registered** | **8** | Next ID: INV-009 |

---

## Board

| ID | Title | Severity | Status | Owner | Blocked by | Review |
|----|-------|----------|--------|-------|------------|--------|
| INV-001 | Time Authority Drift | Critical | Ready for Fix | Architecture Board | — | [DoR Cert](./INV_001_DEFINITION_OF_READY_CERTIFICATION.md) |
| INV-002 | Merchant Identity Drift | Critical | Open | Architecture Board | — | — |
| INV-003 | Knowledge Surface Drift | High | Open | Knowledge + Product | INV-001, INV-002 | — |
| INV-004 | Attention Semantics Drift | High | Open | Product + UX | INV-002, INV-003 | — |
| INV-005 | Setup Lifecycle Drift | High | Open | Product + Ops | INV-002 | — |
| INV-006 | Attribution Semantics Drift | High | Open | Purchase Truth + Product | INV-001 | — |
| INV-007 | Monthly Summary Materialisation Gap | Medium | Open | Dashboard | INV-001, INV-002 | — |
| INV-008 | Visitor Truth Coverage Gap | Medium | Open | Knowledge + Ingress | — | — |

---

## Next action (human)

1. Architecture Review of **WP-3** (`docs/investigations/WP-03_REVIEW.md`).  
2. On approval only: authorize **WP-4** (Knowledge migration).  
3. INV-002 review when ready (separate).
