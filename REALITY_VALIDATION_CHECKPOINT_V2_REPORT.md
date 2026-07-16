# Reality Validation Checkpoint V2 Report

**Status:** COMPLETE — STOP for Architecture and Product Review  
**Date (UTC):** 2026-07-16  
**Branch:** `feature/reality-checkpoint-v2-admin-investigations`  
**Scope:** Validate Time Authority WP-1…WP-6 against Reality Lab V1 Small Reality. **No fixes. No WP-7.**  
**Evidence:** `docs/architecture/reality_validation_checkpoint_v2/`  
**Runner:** `scripts/reality_validation_checkpoint_v2.py`

> Validation only. Findings are classified; issues are not repaired in this task.

---

## 1. Replay configuration

| Item | Value |
|------|-------|
| store_slug | `demo` |
| Seed | `20260715` (identical to Lab V1) |
| Historical range | `2026-05-01` → `2026-05-03` (3 days) |
| Sim-aligned probe `now` | `2026-05-04T12:00:00Z` |
| Scenarios | Same `LAB_SCENARIOS` as Lab V1 (13 scenarios) |
| Scale | Small Reality — 9 journeys/day, max 500 events |
| Checkpoint run id | `srs_d40d845d67314f7ba108bfc07d400020` |
| Lab V1 run id (baseline) | `srs_0430adc995264cd5b7576dfdc10649f0` |
| DB | Temp SQLite `%TEMP%\cartflow_reality_lab_v1_20260715.db` (recreated) |

### Differences from Lab V1 (documented)

1. New `simulation_run_id` each checkpoint run (not forced to V1 id).  
2. Added Time Authority probes: ambient production vs `simulation_scope(start=SIM_END)`.  
3. Daily Brief + cross-surface window equality probes (post WP-6).  
4. Merchant signup→demo bind still attempted (INV-002 may still apply to walkthrough).  
5. Screenshots captured on port `8766` into checkpoint evidence folder.

### Durable counts (demo) — matches V1 class

| Metric | Checkpoint V2 | Lab V1 |
|--------|--------------:|-------:|
| Abandoned carts | 27 | 27 |
| Purchase Truth | 20 | 20 |
| Reasons | 17 | 17 |
| Schedules | 13 | 13 |
| Mock WA logs | 13 | 13 |
| Movement snapshots | 31 | 31 |
| Timeline events | 26 | 26 |

---

## 2. Before / after comparison (Lab V1 findings)

| Prior finding | Classification | Notes |
|---------------|----------------|-------|
| Wall-clock Knowledge/KPI mismatch (T2) | **Improved** (not fully Resolved for merchant UI) | Under `simulation_scope`, Knowledge `cart_count=27`. Ambient production still `cart_count=0`. Windows now share one authority when QTC is set. |
| Home “preparing understanding” (T3) | **Unchanged** (merchant walkthrough) | Desktop/mobile Home screenshots still show skeleton + “CartFlow يجهز فهم متجرك”. Service compose for `demo` under sim has non-empty while-away; UI session still empty/skeleton. |
| Knowledge Surface Drift (INV-003) | **Improved** | Sim-aligned Knowledge rich again (9 insights, 2 insufficient visitors). Ambient still insufficient theatre. |
| Monthly Summary time gap (T7 / INV-007) | **Unchanged** | Still no monthly summary snapshot row. |
| Attention semantics (T4 / INV-004) | **Unchanged** | Attention counts 0 on composed Home/Brief despite carts on demo. |
| Setup lifecycle feeling (T5 / INV-005) | **Unchanged** | Setup nav still present; readiness narrative vs lived history unresolved (identity). |
| Attribution wording (T6 / INV-006) | **Unchanged** | Still emits `likely_recovery` on simulator purchases. |
| Hybrid timestamps (T9) | **Unchanged** | Reconcile path still writes wall-clock `last_seen` / attribution times (July) beside May history — WP-7+ write stamps. |
| Visitor/checkout insufficient (T8 / INV-008) | **Unchanged** | Visitor insights remain insufficient. |
| Merchant store ≠ demo (T1 / INV-002) | **Unchanged** | Walkthrough screenshots show empty Home while demo DB is rich. |
| Cross-surface window recipes | **Resolved** (under shared QTC) | Brief ≡ Knowledge ≡ Dashboard window bounds when probed under the same simulation context (`equal: true`). |
| Evidence counts across KPI vs Knowledge | **Not yet testable / remaining** | Under sim QTC: Knowledge carts=27 but Dashboard KPI `abandoned_total=0` (likely `last_seen` hybridized out of May window). Explained by T9 field choice — not a window-recipe split. |

---

## 3. Home review

| Probe | Result |
|-------|--------|
| Merchant UI screenshots | Skeleton + preparing understanding (July date chrome) |
| `build_merchant_home_experience_api_payload(demo)` ambient | `brief_date=2026-07-16`, while_away=12, understanding=0, attention=0 |
| Same under simulation QTC | `brief_date=2026-05-04`, `generated_at=2026-05-04T12:00:00Z`, while_away=18 |

**Verdict:** Service-level Home stamps follow Time Authority. Merchant-visible Home walkthrough still fails trust (identity + presentation path).

---

## 4. Knowledge review

| Context | cart_count | purchase_count | Insights |
|---------|----------:|---------------:|----------|
| Lab V1 wall | 0 | 0 | all insufficient |
| Lab V1 sim-now | 27 | 18 | rich |
| Checkpoint ambient | **0** | **0** | 6 insufficient |
| Checkpoint simulation QTC | **27** | **18** | 9 insights (2 visitor insufficient) |

**Verdict:** WP-4 Time Authority path works when QTC is simulation-aligned. Ambient merchant requests without as-of/sim context still hide May history.

---

## 5. Daily Brief review

| Context | brief_date | generated_at | achievements | time_window |
|---------|------------|--------------|-------------:|-------------|
| Ambient | 2026-07-16 | wall QTC | 12 | July last-7d |
| Simulation | **2026-05-04** | **2026-05-04T12:00:00Z** | 18 | May window matching Knowledge |

**Verdict:** WP-6 migration confirmed — Brief windows/stamps consume shared authority; under sim QTC Brief agrees with Knowledge dates.

---

## 6. Cross-surface time equality

| Context | Knowledge ≡ Dashboard ≡ Brief windows |
|---------|----------------------------------------|
| Simulation QTC | **Yes** (`cross_surface_equal.equal = true`) |
| Ambient successive resolves | Microsecond drift between calls (`equal: false`) — **explained**: each resolve samples `authority_now()` independently; same recipe, not divergent ownership. Fixed/`now=` probes remain equal (unit suite). |

Evidence counts (Knowledge carts vs Dashboard KPI abandoned) are **not** identical under sim QTC (27 vs 0) — explained by hybrid `last_seen` (T9), not window recipe divergence.

---

## 7. Merchant trust findings

1. **Platform can now tell a coherent temporal story under QTC** (Knowledge + Brief + window recipes).  
2. **Merchant UI walkthrough still does not feel like it understands the store** (skeleton Home, July chrome, empty carts surface).  
3. **Confidence / recommendations:** Sim-aligned Knowledge insights remain evidence-backed; ambient path still apologises with insufficient.  
4. **Temporal contradictions still merchant-visible:** wall date chrome; hybrid reconcile stamps; Attention empty vs DB carts (identity).

---

## 8. Remaining weaknesses

| Weakness | Owner investigation |
|----------|---------------------|
| Merchant session ≠ demo | INV-002 |
| Ambient HTTP has no historical as-of for review | INV-001 (presentation / WP-11) |
| Hybrid last_seen / reconcile wall stamps | INV-001 → WP-7+ |
| Attention empty | INV-004 (+ parents) |
| Monthly summary absent | INV-007 |
| Attribution `likely_recovery` on sim purchases | INV-006 |
| Visitor metrics | INV-008 |
| WP-5 DB fixture flake | INV-009 |

---

## 9. Performance findings

| Check | Result |
|-------|--------|
| Simulation wall | ~55.4s (V1 class ~78s — no regression) |
| Pool | `NullPool`; `pool_exhausted=false` |
| Scheduler | Not started for checkpoint; due-scanner ownership blocked in capture helper |
| Query growth | No new merchant query shapes introduced by checkpoint probes |
| Uncontrolled sim growth | Bounded Small Reality profile; temp DB deleted/recreated |

**Dashboard latency:** Checkpoint did not run a production load test; structural probes show no new joins. No evidence of merchant-request degradation from WP-6 in this pack.

---

## 10. Investigation impact

| ID | Impact of Checkpoint V2 |
|----|-------------------------|
| INV-001 | Reader migration WP-4…6 **validated under QTC**. Merchant-visible closure **not** claimed. Status remains Ready for Fix; WP-7 not started. |
| INV-002 | Reconfirmed as primary walkthrough blocker. |
| INV-003 | Partial improvement when QTC correct; Open remains. |
| INV-004…008 | Unchanged classifications. |
| INV-009 | Filed for WP-5 DB fixture instability (independent). |

**No investigation statuses forcibly closed by this checkpoint.**

---

## 11. Screenshots — Mobile and Desktop

### Merchant (checkpoint replay)

| File | Surface |
|------|---------|
| `docs/architecture/reality_validation_checkpoint_v2/01_desktop_home.png` | Home desktop — preparing understanding |
| `docs/architecture/reality_validation_checkpoint_v2/02_mobile_home.png` | Home mobile |
| `docs/architecture/reality_validation_checkpoint_v2/01_desktop_carts.png` | Carts desktop |
| `docs/architecture/reality_validation_checkpoint_v2/02_mobile_carts.png` | Carts mobile |

### Admin Investigation Dashboard V1

| File | Surface |
|------|---------|
| `docs/architecture/reality_validation_checkpoint_v2/admin_investigations/admin_investigations_desktop.png` | List desktop |
| `docs/architecture/reality_validation_checkpoint_v2/admin_investigations/admin_investigations_mobile.png` | List mobile |
| `docs/architecture/reality_validation_checkpoint_v2/admin_investigations/admin_inv009_detail_desktop.png` | INV-009 detail |

Machine evidence: `docs/architecture/reality_validation_checkpoint_v2/checkpoint_evidence.json`

---

## 12. Recommendation

**Continue to WP-7** — after Architecture/Product review of this checkpoint.

Rationale:

- WP-4…WP-6 reader Time Authority contract holds under shared QTC (windows equal; Knowledge sim-aligned; Brief stamps aligned).  
- Remaining hybrid write-stamp / reconcile wall clocks are **exactly** what WP-7 (Timeline + Movement writers) is sequenced to address.  
- Merchant Home emptiness is primarily **INV-002** (and presentation), not a reason to reverse WP-6.  
- Do **not** treat ambient `cart_count=0` as a WP-6 regression — it is correct production window behaviour against May history without as-of context.

**Explicit:** Do not begin WP-7 until this report is reviewed. Do not implement fixes from this checkpoint in the same change set.

---

## Primary questions (answers)

| Question | Answer |
|----------|--------|
| Does Home now see historical activity? | **Service/demo under sim QTC: partial yes. Merchant UI walkthrough: no.** |
| Does Knowledge use the same historical window? | **Yes, when QTC is shared.** |
| Does Daily Brief agree with Home and Knowledge? | **Windows/stamps yes under sim QTC. Presentation counts differ by surface content.** |
| Same evidence counts across surfaces? | **Not yet** (KPI `last_seen` vs Knowledge carts under hybrid stamps). |
| Has “preparing understanding” disappeared where evidence exists? | **No** on merchant screenshots. |
| Confidence / recommendations evidence-backed? | **Yes under sim-aligned Knowledge; ambient still insufficient.** |
| Feel like CartFlow understands the store? | **Not in merchant walkthrough. Yes in sim-aligned API probes.** |
| Temporal contradictions still merchant-visible? | **Yes** (date chrome, hybrid stamps, empty UI vs demo DB). |
