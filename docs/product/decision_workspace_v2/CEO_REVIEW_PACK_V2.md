# Decision Workspace Refinement V1 — CEO Review Pack V2

**Status:** Production deployed (`77f84f3`). No polish after this pack.  
**Store:** Living Store `demo` · `cf.living.store.review@smartreplyai.net`  
**Bind:** https://smartreplyai.net/dev/living-store-home-review  
**Workspace:** https://smartreplyai.net/dashboard#workspace  
**Perf probe:** `/dashboard?workspace_perf=1#workspace` → `window.__CW_WORKSPACE_PERF_V1`

---

## What changed (vs V2 prototype)

| WP | Change |
|----|--------|
| WP-1 | Ownership language — CartFlow vs merchant responsibilities |
| WP-2 | Advisor conversation tone (not report / BI / academic) |
| WP-3 | Narrative: Diagnosis → Why → Confidence → Consequence → CartFlow role → Commitment → Outcome |
| WP-4 | Commitment never asks merchant to investigate / review / collect evidence (Primary) |
| WP-5 | Diagnostic Primary aligns with Home shipping story; Products is execution when focused |
| WP-6 | CTA → «العودة للملخص» when waiting; «متابعة التنفيذ» otherwise |
| WP-7 | 45s paint cache; DCE cache-first; `?workspace_perf=1` timeline |
| WP-8 | Next cards compact; Primary dominates |

---

## 1. Desktop review

| Asset | Path |
|-------|------|
| Before (V2 prototype Workspace) | [`prod_desktop_workspace.png`](./prod_desktop_workspace.png) |
| After Home | [`refine_v1_desktop_home.png`](./refine_v1_desktop_home.png) |
| After Workspace | [`refine_v1_desktop_workspace.png`](./refine_v1_desktop_workspace.png) |
| After target (wait → Home) | [`refine_v1_desktop_target.png`](./refine_v1_desktop_target.png) |

**Observed Primary (after):** Shipping-stage insufficient evidence (matches Home Top Decision).  
**Commitment:** «لا تغيّر السياسة الآن. انتظر حتى يُكمل CartFlow الأدلة…»  
**CTA:** العودة للملخص

---

## 2. Mobile review

| Asset | Path |
|-------|------|
| After Home | [`refine_v1_mobile_home.png`](./refine_v1_mobile_home.png) |
| After Workspace | [`refine_v1_mobile_workspace.png`](./refine_v1_mobile_workspace.png) |
| After target | [`refine_v1_mobile_target.png`](./refine_v1_mobile_target.png) |

---

## 3. Performance measurements (Living Store prod)

| Probe | Cold | Warm (cache) |
|-------|------|----------------|
| Server `total_ms` | **3365** | **79** |
| `workspace_paint_cache_hit` | false | **true** |
| Dominant stage | enrich_compose_budget **3321 ms** | identity_stamp ~78 ms |
| Client `client_fetch_ms` | **3586** | **382** |
| Client `client_paint_ms` | **3590** | — |
| Home warm reference | ~200–270 ms api | — |

Warm Workspace is now in Home-class range. Cold still pays full enrich once per ~45s TTL.

---

## 4. Cross-page journey

```
Home (shipping insufficient-evidence teaser)
  ↓
Workspace (same diagnostic Primary — advisor narrative)
  ↓ العودة للملخص
Home (wait commitment — no false product execution)
```

When evidence is sufficient, CTA becomes «متابعة التنفيذ» → Products/Carts/Communication as execution only.

---

## 5. Remaining concerns (do not fix yet)

| # | Concern |
|---|---------|
| 1 | Cold enrich still ~3.3s (ORV/facts/situations) — cache masks warm path only |
| 2 | Home recommendation still says «واصل جمع الأدلة» (assigns CartFlow work in Home copy) |
| 3 | Some Next-card commitments still leak investigative phrasing (e.g. «افتح حالات بلا تواصل…») |
| 4 | Why line can still echo Diagnosis closely on shipping family |
| 5 | Sidebar chrome «شرح القرار والأدلة…» still feels report-like |

---

## Explicit stop

Wait for CEO visual review. No further Workspace work until feedback.
