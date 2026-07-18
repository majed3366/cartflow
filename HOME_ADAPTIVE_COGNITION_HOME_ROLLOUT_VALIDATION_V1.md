# Adaptive Cognition V2 — Merchant Home Rollout Validation

**Date (UTC):** 2026-07-18  
**Commit:** `b936c54` (PR #4 → `main`)  
**Production Home:** https://smartreplyai.net/dashboard#home  

---

## 1. Deploy status

| Check | Result |
|-------|--------|
| PR merged | **PASS** — https://github.com/majed3366/cartflow/pull/4 |
| `merchant_dashboard_home_v1.js` contains ACF | **PASS** — live JS matches `adaptive_cognition_v1` / `ma-ecc--acf-v2` / `maAcfSummaryQuery` |
| `merchant_dashboard_lazy.js` ACF query | **PASS** |
| `merchant_app.js` return trigger | **PASS** |
| `/api/dashboard/summary` without auth | Redirects to login (expected) |

---

## 2. Path matrix (engine + Home bridge)

Evidence: `HOME_ADAPTIVE_COGNITION_HOME_ROLLOUT_EVIDENCE_V1.json`  
Script: `scripts/_validate_acf_home_rollout_v1.py` → **PASS**

| Fixture | Path | First focus after Arrival/Health | Content preserved |
|---------|------|----------------------------------|-------------------|
| healthy | A | understanding | Yes |
| vip | C | todays_priority | Yes |
| operational | D | todays_priority | Yes |
| attention | B | todays_priority | Yes |
| pending | F | understanding | Yes |
| insufficient | E | timeline | Yes |

Stability: VIP session → `view_stable` → path unchanged **PASS**

---

## 3. Fixture URLs for Product Experience Review (logged-in merchant)

| Path | URL |
|------|-----|
| Healthy | https://smartreplyai.net/dashboard?acf_fixture=healthy#home |
| VIP | https://smartreplyai.net/dashboard?acf_fixture=vip#home |
| Operational | https://smartreplyai.net/dashboard?acf_fixture=operational#home |
| Attention | https://smartreplyai.net/dashboard?acf_fixture=attention#home |
| Pending | https://smartreplyai.net/dashboard?acf_fixture=pending#home |
| Insufficient | https://smartreplyai.net/dashboard?acf_fixture=insufficient#home |

**Verify in DevTools:** `#ma-home-experience-root .ma-ecc--acf-v2` has `data-acf-path` matching the fixture.

---

## 4. Screenshots / recordings

Merchant Home requires an authenticated session. Automated capture without credentials hits the login wall.

| Artifact | Status |
|----------|--------|
| Path matrix JSON evidence | **Delivered** |
| Live static asset proof | **Delivered** |
| Logged-in Home screenshots per fixture | **Requires Product merchant session** — use fixture URLs above |

Observation: this is intentional security for `/api/dashboard/summary`; sequencing is already proven in the bridge matrix and live JS.

---

## 5. Production observations

1. No Home card redesign — only `section_order` drives paint order.  
2. Fixture override changes **path only**, not section copy.  
3. Summary polling uses `view_stable` so cognition does not jump while reading.  
4. Leaving Home then returning sets `return_from_surface`.  
5. Merchant Home is now the first production consumer of Adaptive Cognition V2.

---

## 6. STOP

Await **Product Experience Review**.  
Do not begin Wireframe.  
No further Home improvements unless requested.
