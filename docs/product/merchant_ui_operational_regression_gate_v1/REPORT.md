# Merchant UI — Operational Regression Gate V1

**Date (UTC):** 2026-08-09  
**Living Store deploy:** `d1662e1b6d63da653589771f18118173b9c821ec`  
**Mode:** Read-only validation · no UI redesign · no mutations · no outbound WhatsApp  
**Probe:** `scripts/_merchant_ui_operational_regression_gate_v1.py`

## Scope

Prove recent Merchant Shell / Workspace presentation work did not damage operational capability.

Closed product surfaces were **not** redesigned in this task.

## Gate summary

| Gate | Outcome |
|------|---------|
| 1 Runtime health | Pass (minor: landing `/api/landing/event` 400) |
| 2 Network / requests | Pass — no scroll storms; bounded nav fetches |
| 3 API truth | Pass — summary + projection HTTP 200 |
| 4 Home truth | Pass — stable after round-trip |
| 5 Workspace truth | Pass — UI matches live projection |
| 6 Cart / attention | Pass — no client classifiers/writers |
| 7 Purchase Truth | Pass — no purchase APIs from V2 UI |
| 8 Scheduler / recovery | Pass — no outbound / schedule calls |
| 9 Navigation state | Pass — one active page; shell intact |
| 10 Responsive truth | Pass — same decision/confidence 1440→390 |
| 11 Legacy runtime | Pass — no ACTIVE colliding remnants |
| 12 Performance sanity | Pass — switches ~1s; DOM +42; binders stable |

## Evidence artifacts

- `runtime_console_capture.json`
- `request_summary.json`
- `endpoint_truth_probe.json`
- `responsive_truth_probe.json`
- `navigation_state_probe.json`
- `legacy_runtime_inventory.json`
- `performance_sanity.json`
- `gate_bundle.json`

---

VERDICT:
OPERATIONALLY_SAFE_WITH_MINOR_FINDINGS

OPERATIONAL CAPABILITY IMPACT:
None proven. Merchant UI V2 remains a presentation layer over existing Home summary and Workspace projection APIs. Navigation, shell, and Workspace composition changes did not alter recovery, purchase, or scheduler execution paths.

PROVEN REGRESSIONS:
None.

MINOR FINDINGS:
1. Console network error on `/api/landing/event` → HTTP 400 during public `/` boot before dashboard session — unrelated to Merchant UI V2 painters; not a pageexception.
2. `loadSection` intentionally re-fetches Home/Workspace on each `go()` (expected refresh, not a storm); scroll does not fetch.

UI-ONLY CHANGES CONFIRMED:
Shell integration, Workspace composition/hierarchy/CIM footprint CSS, and V2 static assets. No Merchant UI V2 calls into purchase truth, scheduler, or WhatsApp outbound.

BACKGROUND OPERATIONS CONFIRMED UNAFFECTED:
Scheduler process separation, outbound recovery orchestration, purchase-truth records, and lifecycle classification remain server-side and were not invoked by the validated UI sequence.

LEGACY COLLISION RISK:
None ACTIVE. Rejected experiments (global panel, page-chrome, ownership panel, section pills) classify as REMOVED / UNREACHABLE / DEAD.

SAFE TO CONTINUE PRODUCT DEVELOPMENT:
YES

NEXT ACTION:
Proceed with the next approved product surface (e.g. Products / Carts / Communication) under the protected shell — without reopening closed Workspace/shell composition unless a new visual task is issued.

---

## STOP

Validation complete. No fixes. No redesign. No mutations.
