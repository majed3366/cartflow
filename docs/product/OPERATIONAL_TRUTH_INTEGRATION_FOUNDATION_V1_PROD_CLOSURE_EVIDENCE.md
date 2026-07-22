# Operational Truth Integration Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-22  
**Status:** PENDING live probe after deploy  
**Flag:** `CARTFLOW_OPERATIONAL_TRUTH_V1`  
**Probe:** `GET /dev/operational-truth?store=demo`

---

## 1. Implementation

| Item | Value |
|------|-------|
| Registry | `otreg_v1` — 6 truths from durable counts only |
| Packages | severity / visibility / stability / explainability |
| SCF seam | `SOURCE_OPERATIONAL_TRUTH` + `evaluate_operational_truth_composition_v1` |
| Forbidden | AI, Guidance, Knowledge, page redesign, page-owned ops calc |

---

## 2. Local tests

```bash
pytest tests/test_operational_truth_v1.py -q
```

Expected: 9 passed.

---

## 3. Production verification (fill after deploy)

```bash
python scripts/_verify_operational_truth_v1.py --base https://smartreplyai.net --store demo
python scripts/merchant_experience_validation_v3.py
```

| Field | Expected | Actual |
|-------|----------|--------|
| `ok` | true | _pending_ |
| `deterministic` | true | _pending_ |
| `scf_integration.inputs_include_ot` | true | _pending_ |
| Home/Decision OT visible | true when Demo has durable ops | _pending_ |

**Merge tip:** _pending_

---

## 4. STOP

Only after `ok: true` and Reality Validation V3: proceed to Time Authority Binding (or next Capability Gap).
