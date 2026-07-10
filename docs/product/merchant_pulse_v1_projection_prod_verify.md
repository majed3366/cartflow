# Merchant Pulse V1 — Projection Production Verification

**Status:** Live payload **BLOCKED** on Railway auth (not PASS yet)  
**Date (UTC):** 2026-07-10  
**Production host:** `https://smartreplyai.net`  
**Target commit:** `e8fb7d3` (`feat: add Merchant Pulse V1 summary projection behind flag`)  
**GitHub `main` HEAD:** `e8fb7d3` confirmed  
**Flag:** `CARTFLOW_MERCHANT_PULSE_V1`  
**Modules:** `services/merchant_pulse_v1.py`, `services/merchant_pulse_v1_flag.py`  
**Wire-in:** `finalize_dashboard_summary_payload`  
**Tests:** `tests/test_merchant_pulse_v1.py` (8 passed)  
**Probe:** `scripts/_merchant_pulse_v1_prod_verify.py`  
**Evidence:** `scripts/_merchant_pulse_v1_prod_verify_out/verify_report.json`

---

## 1. Verdict (current)

| Gate | Result |
|------|--------|
| Unit / projection matrix (healthy, require, recommend-only, unknown, WA/store issue, loading) | **PASS** |
| `GET /api/dashboard/summary` Home payload intact | **PASS** |
| Flag-off omits `merchant_pulse_v1` (code + pre-enable live) | **PASS** |
| Commit `e8fb7d3` on GitHub `main` | **PASS** |
| Confirm `e8fb7d3` running on production runtime | **UNVERIFIED** (no public build SHA endpoint; Railway CLI unauthorized) |
| Set `CARTFLOW_MERCHANT_PULSE_V1=1` on Railway | **BLOCKED** — `railway login` required (token expired; non-interactive login impossible) |
| Live `production_pulse_present = true` | **FAIL / PENDING** — probe: `has_pulse: false` |
| Live fields: executive_brief, decision_summary, cartflow_progress, merchant_decision, fork | **PENDING** flag + deploy |

**Overall live Sprint 1A close:** **NOT PASS** until ops completes §2.

---

## 2. Ops steps to close (required)

Run locally (interactive):

```powershell
railway login
cd C:\Users\Toshiba\Desktop\cartflow
railway link
# Select project authentic-motivation / production / service smart-reply-ai (API)

railway variable set CARTFLOW_MERCHANT_PULSE_V1=1 --service smart-reply-ai
railway redeploy --service smart-reply-ai -y
```

Wait for deploy healthy, then:

```powershell
set PYTHONPATH=.
python scripts/_merchant_pulse_v1_prod_verify.py
```

Expect:

```json
"production_pulse_present": true,
"overall": "PASS"
```

Then inspect authenticated `GET /api/dashboard/summary` → `merchant_pulse_v1` contains all five required keys.

**Rollback:**

```powershell
railway variable set CARTFLOW_MERCHANT_PULSE_V1=0 --service smart-reply-ai
railway redeploy --service smart-reply-ai -y
```

---

## 3. Live probe evidence (2026-07-10, pre-flag)

From `scripts/_merchant_pulse_v1_prod_verify_out/verify_report.json`:

| Check | Result |
|-------|--------|
| HTTP summary | 200, `ok: true` |
| `merchant_home_experience_v1` | present, `ok: true` |
| `merchant_pulse_v1` | **absent** |
| `production_pulse_present` | **false** |
| Probe overall | `PASS_PENDING_FLAG` |

---

## 4. State matrix (same code path as API) — PASS

| State | fork | Result |
|-------|------|--------|
| Healthy / leave | `leave` | **PASS** |
| Require / enter_work | `enter_work` | **PASS** |
| Recommend-only / leave | `leave` | **PASS** |
| Unknown | `leave` | **PASS** |
| WA / store issue | `leave` (no false Work) | **PASS** |
| Loading | `leave` | **PASS** |

---

## 5. Governance confirmations

| Requirement | Evidence |
|-------------|----------|
| No projection logic change in this close-out | Docs/ops only |
| No new fields | — |
| No frontend | — |
| No Home UI change | Live Home still intact |
| No DB writes / no new tables | Projection-only |

---

## 6. After flag-on (fill when PASS)

| Field | Live present? |
|-------|----------------|
| `executive_brief` | _pending_ |
| `decision_summary` | _pending_ |
| `cartflow_progress` | _pending_ |
| `merchant_decision` | _pending_ |
| `fork` | _pending_ |

When filled and probe PASS, change §1 overall to **PASS** and date the close.

---

## 7. Closing

> Projection is correct and shipped to `main` (`e8fb7d3`).  
> Live Sprint 1A cannot be marked PASS until Railway sets `CARTFLOW_MERCHANT_PULSE_V1=1` and the probe reports `production_pulse_present=true`.  
> No frontend work.

---

*End of Merchant Pulse V1 Projection Production Verification.*
