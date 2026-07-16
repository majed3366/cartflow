# Investigation Dashboard

**As of (UTC):** 2026-07-16  
**Framework:** Product Investigation Framework V1  
**Phase status:** Reality Validation Checkpoint V2 + Admin Investigation Dashboard V1 submitted — do **not** start WP-7 until Architecture/Product review

---

## Status counts

| Status | Count | IDs |
|--------|------:|-----|
| Open | 8 | INV-002 … INV-009 |
| Investigating | 0 | — |
| Root Cause Confirmed | 0 | — |
| Ready for Fix | 1 | INV-001 (WP-6 approved; Checkpoint V2 pending) |
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
| INV-002 | Merchant Identity Drift | Critical | Open | Architecture Board | — | — |
| INV-003 | Knowledge Surface Drift | High | Open | Knowledge + Product | INV-001, INV-002 | — |
| INV-004 | Attention Semantics Drift | High | Open | Product + UX | INV-002, INV-003 | — |
| INV-005 | Setup Lifecycle Drift | High | Open | Product + Ops | INV-002 | — |
| INV-006 | Attribution Semantics Drift | High | Open | Purchase Truth + Product | INV-001 | — |
| INV-007 | Monthly Summary Materialisation Gap | Medium | Open | Dashboard | INV-001, INV-002 | — |
| INV-008 | Visitor Truth Coverage Gap | Medium | Open | Knowledge + Ingress | — | — |
| INV-009 | WP-5 Cross-Surface Database Fixture Instability | Medium | Open | Engineering + Architecture Board | — | [INV-009.md](./INV-009.md) |

---

## Next action (human)

1. Review **Reality Validation Checkpoint V2** (`REALITY_VALIDATION_CHECKPOINT_V2_REPORT.md`).  
2. Review **Admin Investigation Dashboard V1** (`/admin/investigations`).  
3. On dual approval only: authorize **WP-7** (Timeline + Movement write stamps).  
4. INV-009 remains Open (fixture) — not a WP-6 regression.
