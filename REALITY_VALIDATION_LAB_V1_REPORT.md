# Reality Validation Lab V1 — Small Reality Report

**Status:** COMPLETE — STOP for architectural and product review  
**Date (UTC):** 2026-07-15  
**Profile:** Small Reality (3 historical days)  
**Simulation run:** `srs_0430adc995264cd5b7576dfdc10649f0`  
**Seed:** `20260715`  
**Target:** `demo` only · SimulationClock · no providers · no merchant notifications  
**Evidence:** `docs/architecture/reality_validation_lab_v1_small/`  
**Commit of lab tooling/report:** (see git after this report lands)

> Mission reminder: every output is guilty until proven trustworthy.  
> This lab documents **why a merchant might lose confidence**. No product fixes were made.

---

## 1. Executive Summary

We ran a governed 3-day Small Reality store (27 customers, 7 catalog products, 250 planned events) through the Store Reality Simulator into real CartFlow pipelines.

**Platform truth was written** (carts, reasons, schedules, mock WhatsApp, Purchase Truth under `demo`, movement, timeline).

**Merchant-facing surfaces largely failed the trust test:**

1. A newly signed-up merchant is **not bound to the demo simulation store** — Home/Carts show another empty store.
2. Knowledge / KPIs evaluated on **wall-clock “last 7 days”** report **zero carts / zero purchases**, even when queried for `demo`, because durable history is dated **May 2026** while review ran **July 2026**.
3. When Knowledge is rebuilt with `now` at the end of the simulated window, rich insights appear — proving data exists but **time windows hide it**.
4. Screenshots of Home show prolonged skeleton (“CartFlow is preparing your store’s understanding…”) and Carts show wait/empty — not a store that feels understood.

**Verdict:** Simulator behaviour is believable enough for a small merchant. CartFlow’s **merchant confidence layer is not yet trustworthy** against historical reality. The strongest failure modes are **store scoping** and **temporal blindness**, not missing rows in the database.

---

## 2. Reality Run Overview

| Item | Value |
|------|-------|
| Duration | 3 days (`2026-05-01` → `2026-05-03`) |
| Lab scale | ~9 journeys/day → **27 customers / 27 sessions** |
| Products used | **7** (demo sandbox catalog roles; below 10–20 ideal) |
| Planned events | 250 (108 supported + 116 unsupported markers + misc) |
| Execute status | `completed` · 13 batches · 0 failures · ~78s wall |
| Purchase Truth (`demo`) | **20** rows |
| Abandoned carts on demo | **27** |
| Reasons | **17** (price 5, shipping 3, thinking 3, quality 3, delivery 2, other 1) |
| Mock WA logs | **13** |
| Schedules | **13** |
| Movement snapshots | **31** |
| Timeline events | **26** |
| Reality Score (internal) | **73.8** overall |

Scenarios mixed: baseline, shipping hesitation, low conversion, WA return/success, widget ignore, reason mix, ignore-all, multi-return, organic, ambiguous influence, VIP, insufficient data.

Unsupported markers (page/scroll/dwell/widget_open) were planned honestly — not faked into platform tables.

---

## 3. Merchant Walkthrough

Reviewed as a first paying merchant after signup (`متجر واقع صغير`):

| Surface | What the merchant saw | Trust |
|---------|----------------------|-------|
| Home | Skeleton + “يجّهز فهم متجرك…”; setup readiness ~20% | Low |
| Store Readiness | Still pushes connection / WhatsApp / widget steps | Confusing vs “I already have carts” |
| Cart Workspace | Attention question visible; body “يرجى الانتظار قليلاً” / empty counts | Low |
| Knowledge (API @ wall clock) | All insights `insufficient`; cart_count=0 | Broken trust |
| Knowledge (@ sim end) | Real patterns (price hesitation, conversion, recovery bottleneck) | Strong *if* time-aligned |
| Timeline | Events exist on demo keys; not surfaced in empty UI | Invisible |
| Monthly Summary | No snapshot row | Missing |
| Attention | Empty (“لا يوجد ما يحتاج انتباهك”) despite 27 carts on demo | Contradictory |
| Completed carts | Not visible under signup store | Invisible |

---

## 4. Dashboard Review

**Does CartFlow feel like it understands the store?**  
**No** — for the merchant session used in review.

Observations:

- Home remains in **preparation skeleton**, not an operating centre with evidence.
- KPIs from `/api/dashboard/summary` for the merchant session: abandoned **0**, recovered **0**, WA **0**, revenue **0**.
- Meanwhile DB on `demo` holds 27 carts and 20 purchases.
- Setup card still dominates (“أكمل ربط متجرك”) — readiness narrative fights the idea that reality already happened.
- Date chrome shows **15 July 2026** (wall), not simulated May — merchant has no cue that history was generated in the past.

Feels closer to an **empty onboarding metrics shell** than a brain that watched three days of store life.

---

## 5. Cart Workspace Review

API `GET /api/dashboard/normal-carts` under signup merchant:

- `merchant_carts_page_rows`: **0**
- All filter counts **0**
- Merchant Intelligence groups **empty**

Screenshot (`03_desktop_carts.png`): Attention hero asks “ما الذي يحتاج انتباهك الآن؟” while the queue says wait / empty.

**Trust damage:** The product asks for attention while asserting there is nothing to attend to — and while durable carts exist on another identity.

---

## 6. Knowledge Review

### Wall-clock query (`now` = lab execution day)

All six default insights were `confidence: insufficient`:

- visitor data unavailable  
- conversion funnel gaps / no carts  
- hesitation sample 0  
- recovery sample 0  
- store health: not enough cart data  

`metrics_snapshot`: `cart_count=0`, `purchase_count=0`, `hesitation_total=0`, `purchase_truth_rows=0` for the wall window — **despite** 27 carts / 20 PT rows on `demo`.

### Same DB, `now=2026-05-04T12:00Z` (end of simulated window)

| Signal | Value |
|--------|-------|
| cart_count | 27 |
| purchase_count | 18 |
| hesitation_total | 17 |
| Notable insights | cart→purchase high; top reason **price**; recovery bottleneck **no_reply**; traffic trend up |

**Why generated (sim-aligned):** Real reason distribution + Purchase Truth + schedules.

**Would a merchant believe wall-clock Knowledge?** No — it denies evidence that exists.  
**Would they believe sim-aligned Knowledge?** Partially yes — but visitor/checkout gaps remain honest; recovery “no_reply” may over-claim given mock WA and automation skips.

---

## 7. Timeline Review

- Simulator wrote timeline rows (`scheduled`, `provider_sent`, plus recovery reconcile side-effects).
- Some timeline timestamps during purchase reconcile drifted to **wall clock** while cart `first_seen_at` stayed May — **mixed temporal authority**.
- Merchant UI never surfaced timeline because carts never appeared under the signup store.

---

## 8. Monthly Summary Review

- No `monthly_summary` dashboard snapshot row for `demo`.
- Merchant “الملخص العام” has nothing trustworthy to show from this lab.
- Gap: historical Small Reality does not materialise monthly read models automatically.

---

## 9. Purchase Truth Review

**Positive:** After Phase 3.1, all lab Purchase Truth rows stayed on `store_slug=demo` (no Zid escape).

**Trust issues:**

- Attribution logs during execute claimed `likely_recovery` / medium confidence for purchases that were **simulator-planned** (including organic scenarios) — language a merchant could misread as CartFlow influence.
- Purchase times are May; wall-clock Knowledge ignores them.
- Count asymmetry: planned purchase events 10 vs PT rows 20 (lifecycle/reconcile duplication or multi-key writes) — needs product clarity, not hidden.

---

## 10. Recovery Review

- 13 schedules + 13 mock sends — outbound suppressed correctly (no providers).
- Resume/reconcile path logged `skipped_resume_unsafe` / `automation_disabled` / delay gates — operationally noisy.
- Merchant never sees recovery state because carts are invisible on their store.
- Recovery realism score high internally; merchant-visible recovery story is absent.

---

## 11. Attention Review

Home Attention empty; Carts Attention asks a question with no queue.  
Merchant takeaway: “CartFlow doesn’t know what needs me” *or* “CartFlow is stuck loading.” Both erode trust.

---

## 12. Performance Review (measure only)

| Metric | Observation |
|--------|-------------|
| Execution wall | ~78s for 13 batches / ~134 processed events |
| Last batch wall | ~7.0s (SQLite + purchase reconcile / DB READY noise) |
| Failures | 0 |
| Pool | NullPool (lab SQLite) — no QueuePool pressure signal |
| Memory probe | unavailable on Windows lab host |
| Scheduler | Due scanner disabled in lab server; resume scan touched schedules |
| Dashboard API | Summary/carts 200; carts payload empty for signup store; stage timings multi-second under warm |

No optimisation performed.

---

## 13. Reality Score

Internal only (`merchant_facing: false`):

| Dimension | Score |
|-----------|------:|
| customer_diversity | 80 |
| traffic_realism | 80 |
| purchase_realism | 76 |
| product_realism | 72 |
| recovery_realism | 90 |
| knowledge_realism | 80 |
| timeline_realism | 50 |
| session_realism | 55 |
| behaviour_realism | 85 |
| execution_fidelity | 70 |
| **overall** | **73.8** |

Low timeline/session scores match unsupported chrome events and mixed timestamp authority.

---

## 14. Trust Audit

| # | Issue | Severity |
|---|-------|----------|
| T1 | Simulation data on `demo`; merchant signup sees a **different empty store** | Critical |
| T2 | Wall-clock Knowledge/KPIs report **zero** for historical May reality | Critical |
| T3 | Home stuck in “preparing understanding” skeleton | High |
| T4 | Carts Attention question + empty/wait body | High |
| T5 | Setup readiness narrative contradicts “store already lived 3 days” | High |
| T6 | Attribution `likely_recovery` on simulated/organic purchases | High |
| T7 | Monthly summary absent | Medium |
| T8 | Visitor/checkout metrics permanently unavailable → persistent “insufficient” notices | Medium |
| T9 | Hybrid timestamps (May first_seen vs July last_seen from reconcile) | Medium |
| T10 | Product count only 7 — thin catalog story for “real merchant” | Low–Med |

---

## 15. Why would a merchant lose trust?

1. **“I ran reality and my dashboard is empty.”** — identity scoping failure.  
2. **“CartFlow says it has no carts while the database has 27.”** — temporal window / query semantics.  
3. **“It keeps preparing to understand me and never finishes.”** — skeleton without evidence.  
4. **“It asks what needs attention, then shows nothing.”** — contradictory Attention UX.  
5. **“It claims recovery influence I don’t believe.”** — attribution wording.  
6. **“Setup still treats me like day zero.”** — readiness vs lived history.  
7. **“Knowledge only apologises.”** — wall-clock insufficiency theatre.  
8. **“No monthly story after three days of life.”** — missing summary.

---

## 16. What exceeded expectations?

- **Identity isolation held** for Purchase Truth (`demo` only) after Phase 3.1.  
- **Governed behaviour** produced plausible reason mix and purchase volume without random noise.  
- **Safe delivery** — mock WA only; no provider calls.  
- **When time-aligned**, Knowledge produced concrete, evidence-backed insights (price share, conversion rate, no_reply bottleneck) without injection from the simulator.  
- Reality Engine completed without event failures.

**Should never change:** demo-only simulation pin; no injection of Knowledge/Dashboard conclusions; tagged cleanup; honest unsupported markers.

**Flagship candidate (if fixed):** Time-aligned Knowledge that turns lived store history into Arabic merchant understanding — the sim-aligned report already feels like the product promise.

---

## 17. Architectural Findings (no fixes)

1. **Merchant store ≠ simulation store** after signup — lab/demo linkage gap.  
2. **Read models keyed to wall-clock windows** ignore SimulationClock history.  
3. **Purchase reconcile mutates `last_seen_at` with wall clock** → hybrid timelines.  
4. **Unsupported storefront events** block visitor truth permanently.  
5. **Monthly summary not generated** from source events alone.  
6. **Dashboard store resolution** follows onboarding store, not demo alias for lab merchants.  
7. **Attribution pipeline** runs on mock recovery + purchase without merchant-safe labelling for simulation.  
8. **Snapshot loop disabled** in lab server — monthly/home freshness depends on paths not exercised.

---

## 18. Product Findings (no fixes)

- Empty/loading states need **evidence of what is missing** (wrong store? wrong window? still warming?).  
- Attention must not ask a question when the queue is empty for that merchant.  
- Setup readiness should not dominate when durable cart reality already exists (for the store being viewed).  
- Knowledge “insufficient” is honest for missing visitors — dishonest when carts exist outside the window.  
- Organic vs assisted purchase language must stay conservative on merchant surfaces.

---

## 19. Recommended priorities (DO NOT IMPLEMENT NOW)

1. **P0 — Merchant visibility of simulated/`demo` reality** (store binding + window honesty).  
2. **P0 — Temporal contract** for historical simulation vs wall-clock KPIs/Knowledge.  
3. **P1 — Attention empty-state integrity** (no contradictory question).  
4. **P1 — Attribution copy guardrails** for non-production / organic paths.  
5. **P2 — Monthly summary materialisation** after historical runs.  
6. **P2 — Expand durable event coverage** (or permanently hide visitor claims).  
7. **P3 — Richer product catalog breadth** for Small Reality (10–20 SKUs).

---

## 20. Screenshots

Stored under `docs/architecture/reality_validation_lab_v1_small/`:

| File | Viewport | Observation |
|------|----------|-------------|
| `01_desktop_home.png` | Desktop | Home skeleton / “preparing understanding” |
| `02_mobile_home.png` | Mobile | Same preparation state |
| `03_desktop_carts.png` | Desktop | Attention hero + wait/empty queue |
| `04_mobile_carts.png` | Mobile | Carts empty/wait |

Supporting artefacts:

- `lab_evidence.json` — full API + counts + scores  
- `sim_now_knowledge.json` — wall vs sim-aligned Knowledge contrast  
- `srs_…/simulation_manifest.json` — replay manifest  

---

## Success criteria check

| Criterion | Result |
|-----------|--------|
| Behaves like a real small merchant (source events) | **Mostly yes** (thin product set) |
| Weaknesses exposed honestly | **Yes** |
| Trust issues documented | **Yes** |
| No production logic changes | **Yes** |
| No product fixes | **Yes** |
| Know strengths vs gaps | **Yes** |

---

## STOP

Do **not** fix issues from this report.  
Do **not** start Phase 4.  
Do **not** run another simulation until product/architecture review.

Await review.
