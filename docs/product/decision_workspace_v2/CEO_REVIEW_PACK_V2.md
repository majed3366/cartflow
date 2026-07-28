# Decision Workspace Refinement V1 — CEO Review Pack V2

**Status:** After Refinement V1 production deploy. No polish after this pack.  
**Store:** Living Store `demo` · `cf.living.store.review@smartreplyai.net`  
**Bind:** https://smartreplyai.net/dev/living-store-home-review  
**Workspace:** https://smartreplyai.net/dashboard#workspace  
**Perf probe:** `/dashboard?workspace_perf=1#workspace` then `window.__CW_WORKSPACE_PERF_V1`

---

## What changed (vs V2 prototype)

| WP | Change |
|----|--------|
| WP-1 | Ownership language — CartFlow vs merchant responsibilities |
| WP-2 | Advisor conversation tone (not report / BI / academic) |
| WP-3 | Narrative: Diagnosis → Why → Confidence → Consequence → CartFlow role → Commitment → Outcome |
| WP-4 | Commitment never asks merchant to investigate / review / collect evidence |
| WP-5 | Diagnostic Primary aligns with Home; Products is execution, not re-explanation |
| WP-6 | CTA → «متابعة التنفيذ» or «العودة للملخص» when waiting; less intermediate chrome |
| WP-7 | 45s paint cache; DCE cache-first; `?workspace_perf=1` timeline |
| WP-8 | Next cards compact; Primary dominates; fewer repeated fields |

---

## 1. Desktop review

| Asset | Path |
|-------|------|
| Before (V2 prototype Workspace) | [`prod_desktop_workspace.png`](./prod_desktop_workspace.png) |
| After Home | [`refine_v1_desktop_home.png`](./refine_v1_desktop_home.png) |
| After Workspace | [`refine_v1_desktop_workspace.png`](./refine_v1_desktop_workspace.png) |
| After target | [`refine_v1_desktop_target.png`](./refine_v1_desktop_target.png) |

---

## 2. Mobile review

| Asset | Path |
|-------|------|
| After Home | [`refine_v1_mobile_home.png`](./refine_v1_mobile_home.png) |
| After Workspace | [`refine_v1_mobile_workspace.png`](./refine_v1_mobile_workspace.png) |
| After target | [`refine_v1_mobile_target.png`](./refine_v1_mobile_target.png) |

---

## 3. Performance measurements

Fill after deploy (cold then warm):

| Probe | Cold | Warm (cache) |
|-------|------|----------------|
| Server `total_ms` (`_workspace_perf_timeline_v1`) | | |
| `workspace_paint_cache_hit` | false | true |
| Client `client_fetch_ms` | | |
| Client `client_paint_ms` | | |
| Home warm `api_ms` (reference) | ~200–270 | |

---

## 4. Cross-page journey

```
Home (diagnostic teaser)
  ↓
Workspace (same diagnostic Primary — advisor narrative)
  ↓ متابعة التنفيذ / العودة للملخص
Products or Home (execution / wait — not re-diagnosis)
```

---

## 5. Remaining concerns (do not fix yet)

_Filled after visual capture._

| # | Concern |
|---|---------|
| | |

---

## Explicit stop

Wait for CEO visual review. No further Workspace work until feedback.
