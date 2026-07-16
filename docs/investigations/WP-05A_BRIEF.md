# Work Package Brief — WP-5A

| Field | Value |
|-------|-------|
| Investigation ID | INV-001 |
| Work Package ID | WP-5A |
| Title | Controlled KPI Time Extraction from main.py |
| Branch | `feature/inv001-wp5a` |
| Depends on | WP-1…WP-4 approved; WP-5 BLOCKED |
| Date opened (UTC) | 2026-07-16 |

## Objective

Extract legacy merchant KPI temporal/projection logic from `main.py` into `services/dashboard_kpi_time_v1.py` with thin call sites only. Preserve production semantics exactly. Do **not** migrate to Time Authority (that remains WP-5).

## Out of scope

WP-5 Time Authority migration; Reality Replay Gate A; WP-6; Knowledge; Brief; UI.
