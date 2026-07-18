# Home Adaptive Cognition V2 — Production Deploy Verification

**Date (UTC):** 2026-07-18  
**Surface:** `/dev/adaptive-cognition-lab` (validation lab only — **not** merchant Home)  
**Engine:** `services/home_cognitive_router_v1.py`  

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

## Evidence (to be filled after Railway deploy)

### 1. Path selection

| Check | Expected | Result |
|-------|----------|--------|
| `POST /dev/adaptive-cognition-lab/start` fixture=`vip` | `selected_path` = **C**, label VIP | _pending deploy_ |
| fixture=`healthy` | path **A** | _pending deploy_ |
| fixture=`operational` | path **D** | _pending deploy_ |

### 2. Path stability

| Check | Expected | Result |
|-------|----------|--------|
| `POST .../view-tick` ×3 same session | `path_unchanged` true; path still C | _pending deploy_ |
| No background reshuffle | Path unchanged without trigger | _pending deploy_ |

### 3. Governed re-evaluation

| Check | Expected | Result |
|-------|----------|--------|
| `reeval` trigger=`periodic_poll` | `ok` false / ungoverned | _pending deploy_ |
| `reeval` trigger=`significant_business_state_transition` fixture=`vip_resolved` | previous C → new A | _pending deploy_ |
| `reeval` trigger=`return_from_surface` | allowed; RETURN segment | _pending deploy_ |
| `reeval` trigger=`manual_refresh` | allowed | _pending deploy_ |

---

## Local pre-deploy

| Check | Result |
|-------|--------|
| `pytest tests/test_home_cognitive_router_v1.py tests/test_home_adaptive_cognition_lab_v1.py` | **10 passed** (2026-07-18) |

---

## STOP

After production evidence is recorded: await Product Review.  
Do not begin Wireframe. Do not wire Adaptive Cognition into merchant Home until Product approval.
