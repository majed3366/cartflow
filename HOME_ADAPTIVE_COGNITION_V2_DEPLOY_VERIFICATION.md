# Home Adaptive Cognition V2 — Production Deploy Verification

**Date (UTC):** 2026-07-18  
**Surface:** `/dev/adaptive-cognition-lab` (validation lab only — **not** merchant Home)  
**Engine:** `services/home_cognitive_router_v1.py`  
**Merge:** PR #2 → `main` @ `4d79b93`  

---

## Production URL

https://smartreplyai.net/dev/adaptive-cognition-lab?fixture=vip

---

## What was hardened

| Item | Status |
|------|--------|
| Truth ownership principle documented + enforced in router payload | Yes |
| Session path lock | Yes |
| View ticks do not re-route | Yes |
| Governed re-eval triggers only | Yes |
| `periodic_poll` rejected | Yes |
| Merchant Home redesigned | **No** |
| Wireframe started | **No** |
| Governance baseline edited | **No** |
| Wireflow node meanings changed | **No** |

---

## Evidence (production 2026-07-18)

Raw JSON: `HOME_ADAPTIVE_COGNITION_V2_PROD_EVIDENCE.json`

### 1. Path selection

| Check | Expected | Result |
|-------|----------|--------|
| `POST .../start` fixture=`vip` | path **C** VIP | **PASS** — C / VIP |
| fixture=`healthy` | path **A** | **PASS** — A / Healthy |
| fixture=`operational` | path **D** | **PASS** — D / Operational |
| fixture=`attention` | path **B** | **PASS** — B / Attention |
| fixture=`insufficient` | path **E** | **PASS** — E / Insufficient |
| fixture=`pending` | path **F** | **PASS** — F / Pending |

Lab HTML: HTTP **200** at production URL.

### 2. Path stability

| Check | Expected | Result |
|-------|----------|--------|
| `POST .../view-tick` ×3 same VIP session | `path_unchanged` true; path still C | **PASS** — ticks 1/2/3 all `path_unchanged=true`, path C |
| No background reshuffle | Path unchanged without trigger | **PASS** |

### 3. Governed re-evaluation

| Check | Expected | Result |
|-------|----------|--------|
| `reeval` trigger=`periodic_poll` | rejected / ok false | **PASS** — `ok=false`, `error=ungoverned_trigger`, `rejected=true` |
| `reeval` trigger=`significant_business_state_transition` fixture=`vip_resolved` | C → A | **PASS** — previous C → new A |
| `reeval` trigger=`return_from_surface` | allowed; RETURN segment | **PASS** — segment RETURN, path A |
| `reeval` trigger=`manual_refresh` | allowed | **PASS** — Attention B → Healthy A |

---

## Local pre-deploy

| Check | Result |
|-------|--------|
| `pytest tests/test_home_cognitive_router_v1.py tests/test_home_adaptive_cognition_lab_v1.py` | **10 passed** |

---

## STOP

Production validation complete.  
Await Product Review.  
Do not begin Wireframe.  
Do not wire Adaptive Cognition into merchant Home until Product approval.
