# Environment Mismatch Verification — Observation Admission Bridge

**Date (UTC):** 2026-07-25  
**Status:** DEFECT CONFIRMED — closing via production demo seed + demo-primary Home session

---

## 1. Where was `living_store_reality_v1.py` executed?

| Question | Answer (objective) |
|----------|-------------------|
| Environment | **Local** |
| Staging | No |
| Production | **No** (until `/dev/living-store-reality-run`) |
| Database | `C:\Users\Toshiba\AppData\Local\Temp\cartflow_living_store_v1_20260725.db` (SQLite tempfile) |
| Store that received mass | **`demo`** (`store_slug=demo`) |
| Evidence file | `docs/product/living_store_reality_v1/observation_capture.json` → `db_path`, `auth.lab_session_bind.store_slug` |

Script hard-sets:

```python
os.environ["DATABASE_URL"] = "sqlite:///.../cartflow_living_store_v1_20260725.db"
# ...
"store_slug": "demo"
```

Observation compose used **`FixedAsOf(2026-05-31)`**. Production Home uses **wall clock**.

---

## 2. Admitted observations after Living Store (local `demo`)

From `after_verification.json` (compose against local DB + FixedAsOf):

| # | Capability | Product |
|---|------------|---------|
| 1 | high_interest_low_conversion | Raven — حزام جلد للساعة |
| 2 | shipping_stronger_than_price | TrueSound Air / TrueSound |
| 3 | repeated_return_without_purchase | Raven — حزام جلد للساعة |
| 4 | no_quality_issue_evidence | Horizon Steel / TrueSound Pro |

Reconciliation claimed: foundation 4 → ORV 4 → Home 4 → Workspace 3.

---

## 3. What did the **Home API** return in the same lab run?

Same capture → `dashboard_summary_probe`:

| Field | Value |
|-------|-------|
| `orv_findings_on_summary` | **0** |
| observations `summary_ar` | insufficient-evidence empty |
| observations `empty` | true |

**First divergence (lab):**  
`build_observation_reality_validation_v1("demo")` / direct HES compose → 4 findings.  
`GET /api/dashboard/summary` for the signed-up merchant session → **empty**.

Cause: `resolve_authenticated_store_slug` reads **`MerchantUser.primary_store_id`** (signup store). Lab bind owns demo alongside primary but **does not** change primary (by design).

---

## 4. What does production Home return (before prod seed)?

Probe: `prod_home_probe_before.json` (fresh signup on smartreplyai.net):

| Field | Value |
|-------|-------|
| `store_slug` | `oab-11756f-e5b206` (signup store — **not** `demo`) |
| observations | empty / insufficient-evidence |
| `text_has_raven` | false |

Production `GET /dev/observation-reality-validation?store=demo` (pre-seed):

| Field | Value |
|-------|-------|
| `findings_count` | **1** (not 4) |
| `present_capabilities` | `["high_interest_low_conversion"]` |

Living Store mass was **never** written to production.

---

## 5. Path trace — where reality diverges

```
Living Store (LOCAL sqlite) ──writes──► store_slug=demo (LOCAL)
        ↓
Observation Foundation (LOCAL demo) ✓ 4 ready
        ↓
ORV admission (LOCAL demo) ✓ 4 admitted
        ↓
Direct HES compose(demo) ✓ Home-visible=4   ← report measured HERE
        ↓
──────── DIVERGENCE 1 ────────
Home API session primary ≠ demo  ✗ empty
        ↓
──────── DIVERGENCE 2 ────────
Production demo never received Living Store mass  ✗ findings_count=1
        ↓
Browser on production signup store  ✗ empty
```

**Why “Home-visible = 4” while production still empty:**  
The count was computed against **local `demo` compose**, not against **production `/api/dashboard/summary` for the browser session under review**.

---

## 6. Closure path (code)

| Endpoint | Role |
|----------|------|
| `POST /dev/living-store-reality-run` | Async Living Store on **connected DB** `demo`, **wall-clock trailing** calendar |
| `GET /dev/living-store-reality-status` | Job + observation reconciliation |
| `POST /dev/living-store-home-review-session` | Review merchant with **primary=`demo`** |
| `GET /dev/living-store-home-review` | Cookie + redirect → `/dashboard#home` |

Verify script: `scripts/_living_store_prod_home_verify_v1.py`  
After evidence: `prod_home_verify_after.json`, `prod_after_desktop_home.png`, `prod_after_mobile_home.png`.

Until those show non-empty Product Observations on production Home for `store_slug=demo`, the task stays **OPEN**.
