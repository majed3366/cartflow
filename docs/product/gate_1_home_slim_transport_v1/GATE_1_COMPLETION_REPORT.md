# Gate 1 Completion Report — Home Slim Transport

**Gate:** Gate 1 — P1 Home Slim Transport  
**Date (UTC):** 2026-07-24  
**Authorization:** CEO Authorization — Gate 1 (Authorized Execution)  
**Flag:** `CARTFLOW_HOME_SLIM_TRANSPORT_V1` (default **ON**; `0` restores fat path)  
**Law:** [`../PRODUCT_CONSTITUTION_V1.md`](../PRODUCT_CONSTITUTION_V1.md) · [`../CONSTITUTIONAL_MIGRATION_PLAN_V1.md`](../CONSTITUTIONAL_MIGRATION_PLAN_V1.md)

---

## 1. Recommendation

| Decision | Status |
|----------|--------|
| **CLOSE Gate 1** | **Eligible after CEO visual approval** — engineering C-1…C-3 met on production |
| **Keep Gate 1 OPEN** | **YES until CEO records C-4…C-6** |

**Engineering recommendation:** Gate 1 is **DEPLOYED + VALIDATED** on production (`f556a5d`, Railway Success). Keep Gate 1 **OPEN** until the CEO completes visual review and explicitly approves closure. Gates 2–7 remain **LOCKED**.

---

## 2. Executive payload definition

Home constitutional transport (only):

```text
home_teaser_inputs_v1:
  schema: "home_teaser_inputs_v1"
  health: { watching: bool, abandoned_carts?: int }
  decisions: { count: int, top_title_ar?: str }
  observations: { count: int, top?: { product_name_ar, statement_ar } }  # no action/confidence
  carts: { count: int }
  communication: { sent: int, schedules: int, activity: bool }

home_executive_summary_v1:   # painted sections from teasers
home_surface_mode: "executive_summary_v1"
home_slim_transport_v1: true
merchant_home_experience_v1: { ok, store_slug, slim_transport, version }  # stub only
```

**Removed from Home summary (slim ON):**

| Key | Owner page / concern |
|-----|----------------------|
| `merchant_experience_integration_v1` | Decision / multi-page MEIF |
| `observation_reality_validation_v1` | Observation detail (stripped; teasers only) |
| `merchant_daily_brief_v1` | Legacy Daily Brief |
| `merchant_pulse_v1` / `commerce_signals_v1` | Pulse |
| `home_adaptive_cognition_v1` / `adaptive_cognition_v1` | ACF |

**UI law:** Observation View Details → `#workspace`. No in-place PI expand / `recommended_action_ar` on Home.

---

## 3. Implementation summary

| Change | Location |
|--------|----------|
| Slim flag + teaser extract + heavy strip | `services/home_executive_summary_v1/slim_transport_v1.py` |
| HES compose from teasers; ORV stub on attach | `compose_v1.py` |
| Finalize skips MEIF/ORV/ACF/Pulse; extract→HES→strip | `merchant_home_experience_activation_v1.py` |
| Live builder skips fat home + MEIF when slim | `main.py` |
| No in-place obs expand | `static/home_executive_summary_v1.js` |
| Boot: no `/normal-carts` or `/messages` on `#home` | `static/merchant_dashboard_lazy.js` |
| Tests | `tests/test_home_slim_transport_v1.py` + HES updates |
| Perf probe | `scripts/_home_slim_transport_perf_probe_v1.py` |

---

## 4. Before / after performance comparison

Probe: organic signup → `#home` → `GET /api/dashboard/summary` (+ boot network sample).

| Metric | Before (prod fat) | After (prod slim) | Δ |
|--------|-------------------|-------------------|---|
| Summary `body_bytes` | **56,314** | **4,001** | **−93%** |
| Heavy packages present | MEIF, ORV, Pulse, commerce_signals (**4**) | **0** | cleared |
| `meif_bytes` | **19,665** | **0** | −100% |
| `home_slim_transport_v1` | false | **true** | — |
| `home_teaser_inputs_v1` | absent | **present** | — |
| Summary `fetch_ms` (client) | **1,126** | **161** | **−86%** |
| Boot `normal-carts` calls on `#home` | **9** | **0** | deferred |
| Boot `messages` calls on `#home` | **1** | **0** | deferred |
| Finalize stages | meif / ACF / orv / hes / pulse | teaser_extract + hes only | slim path |

**Before evidence:** `before_perf.json`, `before_desktop_home.png`, `before_mobile_home.png`  
**After evidence:** `after_perf.json`, `after_desktop_home.png`, `after_mobile_home.png`

---

## 5. Production evidence

| Item | Status |
|------|--------|
| PR / merge SHA | [PR #77](https://github.com/majed3366/cartflow/pull/77) → **`f556a5d`** |
| Railway Success | **Success** (`cartflow` + `smartreplyai.net`) |
| After Desktop/Mobile shots | `after_desktop_home.png` / `after_mobile_home.png` |
| After probe (`after_perf.json`) | **ok=true** — five sections, slim flag, no heavy keys |

---

## 6. Gate Closure Checklist

| # | Requirement | Status |
|---|-------------|--------|
| C-1 | Implementation complete (slim transport DoD) | **DONE** |
| C-2 | Production deployment complete | **DONE** (`f556a5d`) |
| C-3 | Validation (no action on Home; pages own APIs; rollback flag) | **DONE** (unit + prod probe) |
| C-4 | Visual CEO review (Desktop/Mobile) | **OPEN** — evidence ready |
| C-5 | Explicit CEO approval recorded | **OPEN** |
| C-6 | Gate Register → CLOSED | **OPEN** — status DEPLOYED / VALIDATED |

### Implementation DoD

- [x] Slim payload tested  
- [x] Fat stages skipped on slim finalize  
- [x] No double MEIF on slim live path  
- [x] No eager carts/messages on `#home`  
- [x] Obs → `#workspace`  
- [x] Before baseline captured  
- [x] After baseline captured on production  
- [ ] CEO approval  

---

## 7. Governance

- Gates **2–7 remain LOCKED**.  
- Product Intelligence V1 remains frozen until Gate 7 CLOSED.  
- Rollback: `CARTFLOW_HOME_SLIM_TRANSPORT_V1=0`.
