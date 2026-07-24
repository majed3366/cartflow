# Gate 1-B — Executive Summary Composition Report

**Gate:** Gate 1 (OPEN until CEO CLOSE) — subtask **1-B**  
**Date (UTC):** 2026-07-24  
**Depends on:** Gate 1-A Home Slim Transport (`f556a5d`)  
**Out of scope:** Product Intelligence · Gate 2 · redesign  

---

## 1. Objective

Complete Gate 1 by making Home a true Executive Summary: every card answers *why the merchant should care*, routes via **عرض التفاصيل →**, and never invents recommendations or ships PI.

## 2. What changed

| Card (id) | Title (AR) | Composition rule | View Details |
|-----------|------------|------------------|--------------|
| `health` | **حالة المتجر** (was صحة العمل) | Operational store state from light counts / connection — stable / needs follow-up / setup | `#carts` or `#home-setup` |
| `decisions` | قرارات اليوم | Evidence-backed decision title only; else constitutional insufficient copy | `#workspace` |
| `observations` | ملاحظات المنتجات | Product name + statement when teaser evidence exists; else approved empty | `#workspace` |
| `carts` | السلال | Waiting / no-phone / active conditions — not bare totals | `#carts` |
| `communication` | التواصل | Waiting follow-up / no-phone / sent / no tasks | `#communication` |

**Teaser enrichment** (`home_teaser_inputs_v1`): reads light summary fields (`merchant_store_cart_counts`, nav badges, KPIs, WA readiness, store connection) without attaching MEIF/ORV/Pulse.

**Still forbidden on Home:** `recommended_action_ar`, confidence, PI expand, fabricated “راجع تكلفة الشحن” without decision evidence.

## 3. Ownership map (constitutional)

```text
حالة المتجر      → Carts (#carts) / Setup (#home-setup)
قرارات اليوم     → Decision Workspace (#workspace)
ملاحظات المنتجات → Decision Workspace (#workspace)
السلال           → Carts (#carts)
التواصل          → Communication (#communication)
```

Payload field: `home_executive_summary_v1.section_ownership_href`.

## 4. Before / after (production)

| | Before (1-A) | After (1-B) |
|--|--------------|-------------|
| Store card title | صحة العمل | حالة المتجر |
| Empty store tone | Generic “انتظر أدلة / فارغ / بانتظار” | Executive: لا مشكلات ظاهرة / لا مهام / أدلة غير كافية للقرار |
| Transport | Slim (unchanged) | Slim (unchanged) |

Evidence files:

- `before_verification.json` + `before_desktop_home.png` / `before_mobile_home.png`
- `after_verification.json` + `after_desktop_home.png` / `after_mobile_home.png` _(after deploy)_

## 5. Validation checklist

- [x] Five executive sections retained  
- [x] Generic health title removed  
- [x] No invented decisions  
- [x] Observation empty = constitutional copy  
- [x] Carts/communication describe conditions when counts exist  
- [x] Each card has View Details → owning page  
- [x] Slim heavy packages still stripped  
- [ ] Production after screenshots  
- [ ] CEO visual review  

## 6. Recommendation

Keep **Gate 1 OPEN** until CEO approves 1-B visually. Gates 2–7 remain **LOCKED**.
