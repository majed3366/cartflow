# Merchant Experience Validation — Hardening (MEH V1)

**Date (UTC):** 2026-07-22
**Status:** COMPLETE

## Comparison

| Run | Readiness |
|-----|----------:|
| V1 | 28 |
| V2 | 72 |
| Hardening | **86** |
| Delta vs V2 | **14** |

- Chapter outcome: **chapter_closed**
- Materially improved vs V2: **True**
- Legacy leakage: **0**

## Unresolved (Capability Gaps only)

```json
[
  {
    "finding_id": "MEV1-H03",
    "category": "B",
    "gap_ids": [
      "CG-MEH-01"
    ],
    "status": "capability_gap",
    "partial_a": null
  },
  {
    "finding_id": "MEV1-D02",
    "category": "B",
    "gap_ids": [
      "CG-MEH-02"
    ],
    "status": "capability_gap",
    "partial_a": null
  },
  {
    "finding_id": "MEV1-C01",
    "category": "B",
    "gap_ids": [
      "CG-MEH-03"
    ],
    "status": "capability_gap",
    "partial_a": "forbid_please_wait_and_ops_fact_banner"
  },
  {
    "finding_id": "MEV1-C02",
    "category": "B",
    "gap_ids": [
      "CG-MEH-02"
    ],
    "status": "capability_gap",
    "partial_a": null
  },
  {
    "finding_id": "MEV1-M02",
    "category": "B",
    "gap_ids": [
      "CG-MEH-04"
    ],
    "status": "capability_gap",
    "partial_a": "communication_activity_facts"
  },
  {
    "finding_id": "MEV1-K03",
    "category": "B",
    "gap_ids": [
      "CG-MEH-01"
    ],
    "status": "capability_gap",
    "partial_a": "surface_as_of_and_window_cue"
  },
  {
    "finding_id": "MEV1-G01",
    "category": "B",
    "gap_ids": [
      "CG-MEH-05"
    ],
    "status": "capability_gap",
    "partial_a": null
  }
]
```

## STOP

Remaining issues are Capability Gaps — see
`docs/architecture/merchant_experience_capability_gap_register.md`.
