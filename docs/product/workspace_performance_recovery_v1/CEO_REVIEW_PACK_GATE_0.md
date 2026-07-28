# Gate 0 — Workspace Performance Recovery — CEO Review Pack

**Status:** Implementation complete locally. **Await deploy + AFTER remeasure for final gate pass.**  
**Date (UTC):** 2026-07-28  
**Scope:** Performance only. No Workspace UX / language / navigation / visual refinement.

---

## 1. Before / After timings

### BEFORE (production Living Store — measured 2026-07-28, current `main`)

| Surface | Phase | Client ms | Server ms | Path |
|---------|-------|-----------|-----------|------|
| Home | desktop cold | **388** | 37.5 | snapshot read |
| Home | desktop warm | 199 | 23.7 | snapshot read |
| **Workspace** | **desktop cold** | **59,600** | **59,319** | enrich (paint miss) |
| Workspace | desktop warm | 212 | 40.2 | paint cache hit |
| Home | mobile cold | 256 | 32.4 | snapshot read |
| Workspace | mobile warm | 296 | 44.7 | paint cache hit |

Artifact: `prod_before_measure.json`

**Verdict (BEFORE):** Workspace first paint is a release blocker (~60s). Warm path only feels fine because of a 45s in-process paint cache — not architectural parity with Home.

### AFTER (post-deploy — re-run)

```bash
python scripts/_workspace_performance_recovery_prod_v1.py
```

Expected AFTER warm+cold:

| Surface | Client ms (target) | Server ms (target) | Snapshot |
|---------|-------------------|--------------------|----------|
| Home | ~200–400 | ~25–40 | durable summary hit |
| Workspace | ~200–500 | ~30–80 | durable `decision_workspace` hit (or paint L1) |

Pass criteria in script: cold Workspace &lt; 3s · warm &lt; 2s · no ORV rebuild on warm.

---

## 2. Full stage timing table (instrumentation)

Opt-in: `GET /api/cart-workspace/v1/projection?workspace_perf=1`

Stages recorded (elapsed ms, % of total, cache, query delta):

| Stage | Role |
|-------|------|
| `auth_ready` | Auth slug resolved |
| `paint_cache_lookup` | L1 in-process paint cache |
| `durable_snapshot_read` | L2 durable `dashboard_snapshots` type `decision_workspace` |
| `shadow_projection` | Fallback only |
| `enrich_compose_budget` | Fallback only |
| → `dce_compose_or_cache` | DCE package get/compose |
| → `package_reuse_situations` | **Reuse** facts/situations from DCE |
| → `orv_facts_situations_rebuild` | Last resort only (incomplete package) |
| → `project_situation_cards` | Card projection (CPU, no ORV) |
| → `publication_apply` | Publication stamp / dedupe |
| → `v2_budget_hydrate` | Budget + narrative hydrate |
| `durable_snapshot_write` | Persist after fallback |
| `identity_stamp` | Light identity stamp |
| `serialization` | Response assemble |

Home reference: `?home_perf=1` → `_home_perf_timeline_v1`.

---

## 3. Root cause (evidence only)

**Why is Workspace slower than Home?**

Home request path = **read persisted snapshot** + light finalize. Explicit ban: no ORV / facts / situations recompose on snapshot path (`finalize_dashboard_summary_payload` → `hes_snapshot_passthrough` / `snapshot_path_no_orv`).

Workspace request path (BEFORE) = **compose/enrich on every paint-cache miss**:

1. `compose_decisions_v1` (often sync-compose on empty portfolio)
2. **Then rebuild** `build_observation_reality_validation_v1` → facts → situations **again**
3. Publication + v2 budget

Dominant bottleneck on cold: **request-time duplicated Observation→Facts→Situations orchestration** (plus sync DCE), measured at **~59.3s server** on Living Store desktop cold.

Not fixed by longer paint-cache TTL (that only hides warm repeats).

---

## 4. Why the fix works architecturally

Same contract as Home:

1. **Off-request materialization** — dashboard snapshot builder writes `decision_workspace` projection alongside summary/diagnostics.
2. **On-request read** — `paint cache → durable snapshot → enrich fallback`.
3. **Single source of truth** — enrich **reuses** `business_facts_v1` / `commerce_situations_v1` already inside the DCE package; no second ORV rebuild when package complete.
4. **Invalidation on command** — merchant commands mark durable snapshot invalidated + clear paint cache (correctness preserved).

This removes duplicated pipeline and moves heavy orchestration off the merchant GET.

---

## 5. Remaining technical debt

| Item | Notes |
|------|-------|
| First request before builder has written `decision_workspace` | Still falls back to enrich once, then persists. Rare after builder cadence. |
| Multi-worker paint cache | L1 is per-process; L2 durable snapshot is the cross-worker source of truth. |
| Enrich fallback still can sync-compose on true DCE miss | Correctness path; should be rare when builder + DCE cache healthy. |
| JSON cap 256KB for workspace snapshot | Monitor oversized portfolios. |

---

## 6. Production measurements

- **BEFORE:** `prod_before_measure.json` (cold Workspace **59.6s**).
- **AFTER:** re-run script post-deploy → `prod_parity_measure.json`.
- Screenshots: `prod_desktop_*.png`, `prod_mobile_*.png` (visual continuity only; no UX change intended).

---

## 7. Desktop and Mobile verification

Script covers both viewports (1440×900 and 390×844).

Regression audit (behaviour — not UX polish):

| Concern | Expectation |
|---------|-------------|
| Decision ordering | Unchanged publication priority + v2 budget |
| Decision publication | Same `merchant_publication_v1` envelope |
| Commitment | Same commitment fields / diagnostic primary inject |
| Navigation | Same `#workspace` / commitment hrefs |
| Evidence | Same situation/diagnostic evidence on cards |
| Confidence | Same confidence narrative fields |
| Cross-page continuity | Diagnostic primary still injected from diagnostic snapshots |

Unit proof of no ORV rebuild on package reuse: `tests/test_workspace_performance_recovery_v1.py` (4 passed).

---

## STOP

Do not continue Workspace refinement. Do not begin Products or Carts.  
**Await CEO approval of this gate after AFTER production measure.**
