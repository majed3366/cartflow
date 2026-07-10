# Merchant Pulse V1 — Projection Production Verification

**Status:** Projection phase verified (backend only — no frontend)  
**Date (UTC):** 2026-07-10  
**Production host:** `https://smartreplyai.net`  
**Flag:** `CARTFLOW_MERCHANT_PULSE_V1`  
**Modules:** `services/merchant_pulse_v1.py`, `services/merchant_pulse_v1_flag.py`  
**Wire-in:** `services/merchant_home_experience_activation_v1.py` → `finalize_dashboard_summary_payload`  
**Tests:** `tests/test_merchant_pulse_v1.py` (8 passed)  
**Probe:** `scripts/_merchant_pulse_v1_prod_verify.py`  
**Evidence:** `scripts/_merchant_pulse_v1_prod_verify_out/verify_report.json`

---

## 1. Verdict

| Gate | Result |
|------|--------|
| Unit / projection matrix (healthy, require, recommend-only, unknown, WA/store issue, loading) | **PASS** |
| `GET /api/dashboard/summary` Home payload intact (no UI regression) | **PASS** |
| Flag-off omits `merchant_pulse_v1` | **PASS** (code + live prod before enable) |
| Live prod `merchant_pulse_v1` present with all fields | **PENDING FLAG** — code not yet on production / flag not set at probe time |
| No new tables / no DB writes / no page-local intelligence | **PASS** (static review) |

**Overall for this phase commit:** **PASS** for projection correctness + safe default-off.  
**Live flag-on inspect:** re-run probe after deploy with `CARTFLOW_MERCHANT_PULSE_V1=1`.

---

## 2. Enable flag (ops)

```text
CARTFLOW_MERCHANT_PULSE_V1=1
```

Then restart/redeploy the API service so `finalize_dashboard_summary_payload` attaches Pulse.

**Rollback:**

```text
CARTFLOW_MERCHANT_PULSE_V1=0
```

(or unset). Summary omits `merchant_pulse_v1`; Home unchanged.

> Note: This verification environment could not set Railway variables (`railway` not linked / OAuth expired). Flag enable is an ops step after this commit is on `main`.

---

## 3. Inspect `GET /api/dashboard/summary`

### 3.1 Live production (pre-flag / pre-deploy of this commit)

| Check | Result |
|-------|--------|
| HTTP | 200, `ok: true` |
| `merchant_home_experience_v1` | present, `ok: true` |
| `merchant_pulse_v1` | **absent** (expected — flag default off / code not deployed yet) |

### 3.2 Required fields (when flag on)

After enable, `body.merchant_pulse_v1` must contain:

| Field | Required |
|-------|----------|
| `executive_brief` | yes — `{status, message, confidence, last_updated}` |
| `decision_summary` | yes — same slot shape |
| `cartflow_progress` | yes — same slot shape |
| `merchant_decision` | yes — same slot shape |
| `fork` | yes — `leave` \| `enter_work` |

Also present: `ok`, `version`, `projection` (`MerchantPulseV1`), `generated_at`, `status`, `sources`.

---

## 4. State matrix (same code path as API)

Validated via `build_merchant_pulse_v1_from_summary` (identical projection used by summary attach):

| State | fork | Overall / notes | Result |
|-------|------|-----------------|--------|
| **Healthy / leave** | `leave` | progress concrete; decision `no_action` | **PASS** |
| **Require action / enter_work** | `enter_work` | `critical_action` → Work; `merchant_decision.work_entry=carts` | **PASS** |
| **Recommend-only / leave** | `leave` | `suggested_action` does **not** enter Work | **PASS** |
| **Unknown** | `leave` | empty summary → unknown; no invented CTA | **PASS** |
| **WA / store connection issue** | `leave` | does **not** become Trust UI or false Work | **PASS** |
| **Loading** | `leave` | all four slots `loading` | **PASS** |

Evidence excerpt (require):

```json
"fork": "enter_work",
"merchant_decision": {
  "status": "require_action",
  "message": "احصل على رقم العميل",
  "confidence": "high"
}
```

Evidence excerpt (recommend-only):

```json
"fork": "leave",
"decision_summary": {
  "status": "no_action",
  "stance": "recommend_optional"
}
```

---

## 5. Governance confirmations

| Requirement | Evidence |
|-------------|----------|
| No duplicated business logic | Projection selects Brief/Home attention + WA/store fields only; does not mint LT-C1 / Decision / Purchase |
| No page-local intelligence | No frontend changes in this phase |
| No DB writes | Read-only compose on summary body |
| No new tables | No Alembic / models added for Pulse |
| No impact on current Home UI | Live summary still returns `merchant_home_experience_v1`; Pulse is additive JSON only |
| Flag-off removes projection | `attach_merchant_pulse_v1_to_summary` pops key when flag off; unit test `test_flag_off_*` |

---

## 6. Post-deploy checklist (ops)

1. Merge/push this phase to `main`.  
2. Set `CARTFLOW_MERCHANT_PULSE_V1=1` on production API.  
3. Restart service.  
4. Re-run:

```bash
set PYTHONPATH=.
python scripts/_merchant_pulse_v1_prod_verify.py
```

5. Expect `verdict.overall == "PASS"` and `production_pulse_present == true`.  
6. Spot-check JSON: four slots + `fork` on a real merchant session.  
7. Set flag `0` once → confirm key disappears → set `1` again if keeping enabled.

---

## 7. Out of scope (this phase)

- Frontend / CSS / Home layout  
- Pulse UI rendering  
- New Truth domains  

---

## 8. Closing

> Projection is correct, tested, and safe behind a default-off flag.  
> Production live presence awaits deploy + `CARTFLOW_MERCHANT_PULSE_V1=1`.  
> No frontend work in this phase.

---

*End of Merchant Pulse V1 Projection Production Verification.*
