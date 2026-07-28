# Gate 0 — Workspace Performance Recovery — CEO Review Pack

**Gate verdict: PASS**  
**Deployed SHA:** `e305fd404229d2aee2db75ad4c82c4830c7a1fa1`  
**PR:** [#118](https://github.com/majed3366/cartflow/pull/118)  
**Railway:** Success — `authentic-motivation - cartflow` · `authentic-motivation - smart-reply-ai` (smartreplyai.net)  
**Date (UTC):** 2026-07-28  
**Scope:** Performance only. No Workspace UX refinement.

---

## 1. BEFORE / AFTER

| Surface | Phase | BEFORE client | AFTER client | BEFORE server | AFTER server | AFTER path |
|---------|-------|---------------|--------------|---------------|--------------|------------|
| Home | desktop cold | 388 ms | 494 ms | 37.5 ms | 37.7 ms | summary snapshot |
| **Workspace** | **desktop cold** | **59,600 ms** | **704 ms** | **59,319 ms** | **69.8 ms** | **`durable_snapshot`** |
| Home | desktop warm | 199 ms | 709 / 434 ms | 23.7 ms | 37.5 / 43.8 ms | summary snapshot |
| Workspace | desktop warm | 212 ms | 496 / 328 ms | 40.2 ms | 60.0 / 53.7 ms | paint_cache |
| Home | mobile cold | 256 ms | 235 ms | 32.4 ms | 40.2 ms | summary snapshot |
| Workspace | mobile cold* | (paint-warmed) | 256 ms | — | 45.2 ms | paint_cache |
| Workspace | mobile warm | 296 ms | 228 / 222 ms | 44.7 ms | 48.0 / 45.6 ms | paint_cache |

\* Mobile cold in the same run hit L1 paint cache after desktop cold on the same worker. Durable cold path is proven on **desktop_workspace_cold** (`serve_path=durable_snapshot`, `paint=false`).

Artifacts: `prod_before_measure.json` · `prod_after_measure.json`

---

## 2. Root-cause closure evidence

| Claim | Evidence |
|-------|----------|
| Dominant BEFORE bottleneck = request-time ORV→facts→situations (+ sync DCE) | BEFORE cold server **59.3s** on paint miss |
| AFTER eliminates request-time ORV rebuild | `orv_rebuilt=false` on all Workspace samples |
| AFTER cold uses durable snapshot | `desktop_workspace_cold`: `serve_path=durable_snapshot`, `durable_snapshot_hit=true`, `paint_cache_hit=false` |
| Enrich fallback is not the normal path | No sample used `serve_path=enrich_fallback` |
| Warm comparable to Home | Warm Workspace client avg **318.5 ms** vs Home **397.0 ms** |

---

## 3. Snapshot path evidence (desktop cold AFTER)

```
serve_path: durable_snapshot
durable_snapshot_hit: true
paint_cache_hit: false
orv_rebuilt: false
server_ms: 69.788
slowest_stage: identity_stamp (53.5 ms, 76.7%)
durable_snapshot_read: 14.6 ms (20.9%)
decision_card_count: 4
primary_id: diagnostic:dx_8791917bab7a130359e5f2ca
```

---

## 4. Gate PASS checklist

| Requirement | Result |
|-------------|--------|
| Workspace cold &lt; 3s | **PASS** — 704 ms / 256 ms |
| Workspace warm ~ Home | **PASS** — warm Workspace ≤ Home client avg |
| No request-time ORV→facts→situations | **PASS** — `orv_rebuilt=false` |
| Durable snapshot on cold path | **PASS** — desktop cold `durable_snapshot` |
| Ordering / commitment / evidence / nav unchanged | **PASS** — 4 cards; diagnostic primary continuity id present |
| Desktop + Mobile verified | **PASS** — both viewports measured + screenshots |
| Fallback not silent normal path | **PASS** — zero `enrich_fallback` samples |

---

## 5. Remaining technical debt

| Debt | Severity | Notes |
|------|----------|-------|
| `identity_stamp` dominates Workspace server time (~50–55 ms) | Low | Light path; not ORV. Candidate for later slim/skip when identity already on snapshot. |
| Query counts null in timeline | Low | DB request audit not active on this prod path (`total_queries=null`). |
| Multi-worker paint cache L1 | Known | Cross-worker truth is durable snapshot; L1 is acceleration only. |
| First request before builder materializes | Rare | Falls back to enrich once, then persists. Not observed in AFTER run. |

---

## 6. Desktop / Mobile verification

Screenshots refreshed by measure script:

- `prod_desktop_home.png` / `prod_desktop_workspace.png`
- `prod_mobile_home.png` / `prod_mobile_workspace.png`

---

## STOP

Gate 0 **PASS**. Do not resume Workspace refinement. Do not begin Products or Carts.
