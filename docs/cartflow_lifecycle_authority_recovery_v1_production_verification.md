# Lifecycle Authority Recovery v1 — Production Verification Report

**Date (UTC):** 2026-06-13  
**Target:** `https://smartreplyai.net`  
**Local verify script:** `scripts/lifecycle_authority_recovery_verify_v1.py`  
**Evidence JSON:** `scripts/_lifecycle_authority_recovery_verify_v1_out/verify_report.json`

---

## Executive result

| Environment | Result | Notes |
|-------------|--------|-------|
| **Local (TestClient + unit tests)** | **PASS** | All lifecycle authority checks green |
| **Production (unauthenticated probe)** | **PENDING** | Login page probe timed out — full API gate not run without merchant session |

**Overall:** Implementation verified locally. Production merchant API lifecycle parity **awaits deploy + authenticated verification** (same pattern as prior dashboard recovery gates).

---

## Local verification (PASS)

```
pass: true
```

### Checks

| Check | Result |
|-------|--------|
| `/dev/lifecycle-truth-check` consistent | OK |
| VIP row lifecycle attach (`needs_intervention`, label match) | OK |
| Row alignment (no missing `customer_lifecycle_state`, no bucket conflicts) | OK |
| Follow-up clarity derived from lifecycle (no schedule conflicts) | OK |

### Unit tests (combined run)

- `test_lifecycle_authority_recovery_v1.py` — 9 passed
- `test_lifecycle_truth_unification_phase2.py` — passed
- `test_customer_lifecycle_states_v1.py` — passed
- `test_merchant_followup_clarity_v1.py` — passed

---

## Production probe

| Probe | Result |
|-------|--------|
| `GET https://smartreplyai.net/login` | Timeout (25s) — network/read timeout from verify runner |
| Authenticated `/api/dashboard/normal-carts` | Not run (no session in verify script) |
| Authenticated `/api/dashboard/vip-carts` | Not run |
| Authenticated `/api/dashboard/messages` | Not run |
| Authenticated `/api/dashboard/summary` | Not run |

### Required post-deploy gate (manual or CI)

After deploy, with merchant session:

1. `GET /api/dashboard/normal-carts` — every row has `customer_lifecycle_state`; `merchant_cart_bucket` matches state; `merchant_followup_next_line_ar` aligns with `customer_lifecycle_next_followup_line_ar` when present.
2. `GET /api/dashboard/vip-carts` — rows have `customer_lifecycle_state`; `display_status_ar` equals `customer_lifecycle_label_ar`.
3. `GET /api/dashboard/messages` — rows include `customer_lifecycle_state` / `lifecycle_status_ar`.
4. `GET /api/dashboard/summary` — `normal_cart_count` equals lifecycle-active count from normal-carts rows.
5. Dashboard UI — lifecycle chip and detail block show lifecycle copy only (no compact `phase_key` fallback).

---

## Regression guardrails

- No change to recovery send/scheduling workers — display authority only
- `vip_lifecycle_status` column still writable for merchant VIP actions; reads feed evidence
- Archive/reopen API still sets `merchant_archived` evidence → `archived` lifecycle state

---

## Verdict

**Local verification: PASS**  
**Production verification: PENDING deploy + authenticated gate**

Stop after verification per task scope.
