# Commerce Signals V1 — Production Verification

**Status:** **FAIL_PENDING_OPS** (not PASS)  
**Date (UTC):** 2026-07-10  
**Production host:** `https://smartreplyai.net`  
**Target commit:** `5e4038d` (`feat: feed Merchant Pulse from Recovery and Purchase Signals`)  
**Flag:** `CARTFLOW_COMMERCE_SIGNALS_V1` (must be `1` for live consumption)  
**Modules:** `services/commerce_signals_v1.py`, `services/commerce_signals_v1_flag.py`, `services/merchant_pulse_v1.py`  
**Probe:** `scripts/_commerce_signals_v1_prod_verify.py`  
**Evidence:** `scripts/_commerce_signals_v1_prod_verify_out/verify_report.json`

> **Law checked:** Signals feed Pulse **what happened** only (`executive_brief` / `cartflow_progress`).  
> Decision Summary, Merchant Decision, and fork stay on governed Decision inputs.

---

## 1. Verdict

| Gate | Result |
|------|--------|
| Local consumption matrix (all 5 signal types + require stability + flag-off fallback) | **PASS** |
| Live `GET /api/dashboard/summary` HTTP 200 | **PASS** |
| Live `merchant_pulse_v1` present (deployed wiring) | **PASS** |
| Live Pulse `sources` includes `commerce_signals_used` / `commerce_signal_types` | **PASS** (deploy confirmed) |
| Confirm `CARTFLOW_COMMERCE_SIGNALS_V1=1` active | **BLOCKED** — Railway CLI unauthorized |
| Live `commerce_signals_used = true` | **FAIL** |
| Live `commerce_signals_v1` attached on summary | **FAIL** — never attached in live path |
| Live signal types when applicable | **PENDING** (blocked by attach + flag) |
| Live Decision / fork unchanged under Signals | **PENDING** live; **PASS** in local matrix |
| Flag-off fallback (`commerce_signals_used = false`, legacy progress) | **PASS** local; live currently behaves as unused |

**Overall:** **FAIL_PENDING_OPS**

---

## 2. Blockers (must close for PASS)

### A. Railway flag not confirmable from this agent

```text
railway whoami → Unauthorized (OAuth token expired)
```

Cannot set or read `CARTFLOW_COMMERCE_SIGNALS_V1` on production.

### B. Summary does not attach Signals

Pulse reads `body.commerce_signals_v1` only when present.

Live probe:

| Field | Value |
|-------|-------|
| `has_commerce_signals_on_summary` | `false` |
| `commerce_signals_used` | `false` |
| `commerce_signal_types` | `[]` |

**Implication:** Even after `CARTFLOW_COMMERCE_SIGNALS_V1=1`, live `commerce_signals_used` stays `false` until a read-only attach puts store-scoped Signals on the summary (separate wiring task — not done in `5e4038d`).

---

## 3. Live probe (2026-07-10)

From `verify_report.json` → `live`:

| Check | Result |
|-------|--------|
| Summary HTTP | 200, `ok: true` |
| `merchant_home_experience_v1` | present |
| `merchant_pulse_v1` | present |
| `commerce_signals_v1` on summary | **absent** |
| `sources.commerce_signals_used` | **false** |
| `sources.commerce_signal_types` | `[]` |
| `fork` | `leave` |
| Decision / merchant decision | `no_action` (legacy calm path) |

UI / carts: not redesigned; no console-error gate failure in prior flag-off verify.

---

## 4. Local matrix (PASS) — what production should do once attach + flag exist

With `CARTFLOW_COMMERCE_SIGNALS_V1=1` and injected `commerce_signals_v1.signals`:

| Signal type | `commerce_signals_used` | Brief/progress from Signal | Decision / fork |
|-------------|-------------------------|----------------------------|-----------------|
| `recovery_started` | true | yes | unchanged (`leave` / `no_action` on calm body) |
| `recovery_progressed` | true | yes | unchanged |
| `recovery_completed` | true | yes | unchanged |
| `recovery_blocked` | true | yes (fact only) | **never** Enter Work |
| `purchase_confirmed` | true | yes | unchanged |
| Require Decision + `purchase_confirmed` | true | progress from Signal; brief stays Require | fork=`enter_work`, Decision Require unchanged |

Flag off with same injected Signals:

| Check | Result |
|-------|--------|
| `commerce_signals_used` | **false** |
| Progress | legacy while-away text restored |
| Decision / fork | unchanged |

---

## 5. Ops steps to close (required)

### 5.1 Enable flag (interactive)

```powershell
railway login
cd C:\Users\Toshiba\Desktop\cartflow
railway link
# project authentic-motivation / production / service smart-reply-ai

railway variable set CARTFLOW_COMMERCE_SIGNALS_V1=1 --service smart-reply-ai
railway redeploy --service smart-reply-ai -y
```

### 5.2 Attach gap (engineering — required for live used=true)

Until summary includes store-scoped `commerce_signals_v1`, live verification of §1 “used=true” **cannot** pass.

Minimum attach (future task, not this doc):

- Read-only build from Recovery Timeline + Purchase Truth for current store keys  
- Attach under `finalize_dashboard_summary_payload` when flag on  
- No Decision/WA/MI migration; no UI; no new families  

### 5.3 Re-run probe

```powershell
set PYTHONPATH=.
python scripts/_commerce_signals_v1_prod_verify.py
```

Expect:

```json
"live_commerce_signals_used_true": true,
"live_signals_payload_attached": true,
"overall": "PASS"
```

Then inspect authenticated `GET /api/dashboard/summary`:

- `commerce_signals_v1.signals` present when store has Recovery/Purchase facts  
- `merchant_pulse_v1.sources.commerce_signals_used === true` when applicable  
- `executive_brief` / `cartflow_progress` carry `signal_type` when used  
- `decision_summary` / `merchant_decision` / `fork` match pre-Signal Decision behavior  

### 5.4 Fallback verify

```powershell
railway variable set CARTFLOW_COMMERCE_SIGNALS_V1=0 --service smart-reply-ai
railway redeploy --service smart-reply-ai -y
```

Expect live:

```text
commerce_signals_used = false
```

Pulse brief/progress return to legacy Home/Brief inputs.

---

## 6. Acceptance for PASS

All must be true:

1. `CARTFLOW_COMMERCE_SIGNALS_V1=1` confirmed on production  
2. Summary attaches `commerce_signals_v1` when flag on  
3. `commerce_signals_used = true` when applicable Signals exist  
4. Applicable types among: `recovery_started`, `recovery_progressed`, `recovery_completed`, `recovery_blocked`, `purchase_confirmed`  
5. Brief/progress from Signals where applicable; Decision + fork unchanged  
6. Flag off → `commerce_signals_used = false` + legacy Pulse  

**Current status does not meet PASS.**

---

## 7. Non-goals (this verification)

- No UI changes  
- No new Signal families  
- No copy redesign  
- No Product / Traffic work  
