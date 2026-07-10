# Demo Commerce Lab P2 — Production Run + Visual Verification Report

**Date (UTC):** 2026-07-10  
**Verdict:** **BLOCKED on production deploy** — Lab P1/P2 not on `origin/main`. Local Scenario 1 API report **PASS**. Product language gap confirmed from Lab Pulse payload.

---

## 1) Deploy confirmation

| Check | Result |
|-------|--------|
| Lab files committed on `main` | **NO** — untracked: `services/demo_lab_reset_v1.py`, `services/demo_lab_scenario1_v1.py`, `scripts/_demo_lab_v1_scenario1.py`, tests |
| Present on `origin/main` | **NO** (HEAD = `8cd9652` confidence cleanup) |
| Deployed to `https://smartreplyai.net` | **NO** |
| `python scripts/_demo_lab_v1_scenario1.py` hits production | **NO** — script uses local `TestClient` + local SQLite, not prod DB |

**Gate 1 FAIL.** Production Scenario 1 run was not possible without commit + deploy + a prod execution path (Railway run or HTTP Lab endpoints).

---

## 2) Scenario 1 structured report (local Lab runner — only executable path today)

Command equivalent: `run_lab_scenario1_v1(store_slug="demo")` via TestClient.

**Overall: PASS**

| Assertion | Result |
|-----------|--------|
| overall PASS | yes |
| `purchase_confirmed` exists | yes (count=1) |
| `recovery_completed` exists | yes (count=1) |
| amount = 449 SAR | yes (`cart_value=449.0`) |
| exactly one purchase signal | yes |
| exactly one recovery_completed signal | yes |
| Merchant Pulse consumes Signals | yes (`commerce_signals_used=true`) |
| cart completed | yes (`status=recovered`, lifecycle closed) |
| no merchant action remains | yes (`fork=leave`) |

Artifacts:
- `scripts/_demo_lab_v1_scenario1_out/local_report.json`
- `scripts/_demo_lab_v1_scenario1_out/local_api_summary.json`

---

## 3) What the API / Pulse payload says (after Scenario 1)

From Lab Pulse build (Signals on):

| Slot | Message |
|------|---------|
| executive_brief | **اكتمل مسار استرجاع بعد تأكيد الشراء.** |
| cartflow_progress | **اكتمل مسار استرجاع بعد تأكيد الشراء.** |
| decision_summary | غير معروف بعد — لن نخترع عملاً. |
| merchant_decision | لا قرار واحد واضح بعد. |
| fork | `leave` |
| recovered amount (truth) | **449.0** SAR on cart / recovered_purchase |

Signals: `recovery_started`, `purchase_confirmed`, `recovery_completed` (one each).

---

## 4) Production screenshots (baseline — fresh merchant, no Lab run)

Captured on `https://smartreplyai.net` after signup (new store ≠ `demo`):

| Shot | File |
|------|------|
| Home desktop | `scripts/_demo_lab_v1_scenario1_out/prod_visual/01_home_desktop.png` |
| Home mobile | `scripts/_demo_lab_v1_scenario1_out/prod_visual/02_home_mobile.png` |
| Carts desktop | `scripts/_demo_lab_v1_scenario1_out/prod_visual/03_carts_desktop.png` |
| Carts mobile | `scripts/_demo_lab_v1_scenario1_out/prod_visual/04_carts_mobile.png` |
| Completed tab | `scripts/_demo_lab_v1_scenario1_out/prod_visual/05_carts_completed_desktop.png` |
| Demo storefront | `scripts/_demo_lab_v1_scenario1_out/prod_visual/06_demo_storefront.png` |

### What Home shows (production, empty new store)

Pulse present, Signals **not** used (`commerce_signals_used=false`, signal_count=0):

- ماذا يحدث: «CartFlow يتابع متجرك — سنُظهر الإنجازات هنا عند توفرها.»
- ماذا أنجز CartFlow: «لا إنجازات للعرض بعد — المتابعة الروتينية مستمرة.»
- fork: leave

**Does not** show «خلال غيابك تم استرداد عملية شراء واحدة بقيمة 449 SR» (expected — Lab not run on this merchant store).

### What Cart page shows (production)

- Completed tab empty: «لا توجد سلال مكتملة حالياً ضمن نطاق متجرك»
- No 449 SAR row
- No Lab cart (store isolation — new merchant ≠ `demo`)

---

## 5) Product language gap (report only — no copy fix)

| Surface | Observed | Desired | Gap |
|---------|----------|---------|-----|
| Lab Pulse after Scenario 1 (API) | «اكتمل مسار استرجاع بعد تأكيد الشراء.» | «خلال غيابك تم استرداد عملية شراء واحدة بقيمة 449 SR» (or equivalent) | **FAIL** — internal recovery-path wording; **no 449**; no “while you were away / one recovered purchase” framing |
| Production Home (live) | Calm empty Pulse (no Lab outcome) | Same desired after Lab on merchant-visible store | Cannot verify Lab outcome on prod until deploy + merchant-visible `demo` (or linked) store |
| Cart completed (Lab truth) | `status=recovered`, amount 449 in API cart_state | Completed cart with 449 visible | API has 449; merchant Cart UI not verified for Lab cart on prod |

**Where product language still fails (definitive from Lab Pulse payload):**

1. Pulse uses Signal fact string `_SIGNAL_FACT_AR[recovery_completed]` = «اكتمل مسار استرجاع بعد تأكيد الشراء.»
2. That is process/internal language, not merchant outcome language.
3. Amount **449** exists in cart/purchase truth but is **not** rendered into Pulse brief/progress.

No copy changes made (per task).

---

## 6) What is required to complete a true production Lab visual

1. **Commit + push** Lab P1/P2 to `main` (deploy).
2. Run Scenario 1 **against production DB** (Railway shell / `DATABASE_URL`, or add demo-only HTTP Lab reset+runner). Local `TestClient` is not production.
3. Open a merchant session whose store is **`demo`** (or whose summary includes Lab recovery_key) — a fresh signup will not see `demo` Lab carts.
4. Re-capture Home/Cart desktop+mobile after that run.

---

## Summary

| Item | Status |
|------|--------|
| Lab deployed | **NO** |
| Production Scenario 1 run | **NOT DONE** (blocked) |
| Local Scenario 1 API PASS | **YES** |
| Pulse consumes Signals (Lab) | **YES** |
| Product language 449 outcome | **FAIL** (shows internal path copy only) |
| Prod screenshots (baseline) | **YES** (empty merchant, not Lab outcome) |
