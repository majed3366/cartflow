# Snapshot Generation Governance v1

**Program:** CartFlow Operational Governance — Snapshot Phase
**Date (UTC):** 2026-07-04
**Status:** Baseline — governance only. **No production behavior changes, no scheduler changes, no archive changes, no code.**
**Objective:** Establish the permanent architectural contracts that any future `dashboard_snapshots` generation change MUST comply with — *before* any optimization is implemented.

**Elevates snapshot generation to a governed truth domain, alongside:** Purchase Truth, Lifecycle Truth (LT-C1, `docs/lifecycle_truth_enforcement_v1.md`), Data Growth (`docs/data_growth_governance_v1.md`), Institutional Memory (`docs/institutional_memory/`).

**Direct basis:** `docs/dashboard_snapshot_generation_audit_v1.md` (2026-07-04) — which established, with production evidence, that generation is clock-driven not change-driven, append-only, rewrites identical payloads, and that archive limits retention but does not reduce generation.

**Related:** `docs/data_growth_governance_v1.md` §5, `docs/cartflow_dashboard_governance_v1.md`, `docs/cartflow_performance_governance_v1.md`, `docs/production_reality_validation_v1.md` (P0-2), `docs/cartflow_scheduler_governance_v1.md`.

**Non-goals (this phase):** implementing content hashing, event triggers, per-type policies, or adaptive scheduling; changing the builder loop, TTLs, archive, or read path. This document defines *what must be true*; it does not build it.

> **Implementation status (2026-07-04):** This governance is now **implemented** — see `docs/snapshot_generation_optimization_v1.md`. Delivered: SG-6 semantic fingerprint (`services/dashboard_snapshot_change_v1.py`), SG-2 identical-rewrite gate + SG-7 in-place freshness touch at the production write path, SG-5/SG-11 per-type policy, SG-9 derived `dashboard_cards`→`summary` coupling, and SG-4 generation metrics. Behavior-neutral for merchants; no migration. **SG-1 fully event-driven generation** and the **SG-2 static enforcement gate** remain future work (the fingerprint gate already guarantees "no time-only write"). The append→touch evolution below is ratified under SG-12.

---

## 0. Why this governance exists

The audit proved the current generation model is **architecturally expected but structurally unbounded**: a scheduler loop rewrites all ~6 snapshot types for every eligible store on a fixed ~45s rotation via an append-only writer with **no data-change comparison**. Result (prod, 2026-07-03): ~42k rows/day, **99.66% immediately-superseded history**, only 468 rows ever read.

Without governance, any "optimization" risks inventing *new* ad-hoc behavior. This document freezes the rules so future work **implements the governance rather than re-litigating the design** — exactly as LT-C1 froze lifecycle ownership.

**Governance principle above all others:** *A snapshot exists to serve the latest read. Generation must be justified by a change to what that read would return — never by the passage of time.*

---

## 1. Governance principles

Each principle is stated, then justified. These are binding intent; §2 turns them into verifiable contracts.

### P1 — Generation must be driven by meaningful data changes, not elapsed time alone
A rebuild is only warranted when the content a merchant would read has actually changed. **Justification:** the audit showed time-driven rotation produces ~42k writes/day of which 99.66% are dead history; the clock carries no information about whether data changed.

### P2 — Identical snapshot payloads must never be rewritten
If a freshly built payload is semantically identical to the current latest row, no new row may be created. **Justification:** identical rewrites are the single largest source of growth and add zero read value.

### P3 — Each snapshot type owns its own freshness policy
`normal_carts`, `summary`, `store_connection`, etc. have different volatility and different staleness tolerance; one global cadence is wrong for all of them. **Justification:** `store_connection` changes ~never while `normal_carts` changes per cart-event — coupling them wastes writes on the stable ones and under-serves the volatile ones.

### P4 — Generation cost must always be measurable
Every generated snapshot must record *why* it was generated, and generation rate must be observable per type and per store. **Justification:** the current model emits `[DASHBOARD SNAPSHOT WRITE]` but no *reason*; growth was only quantifiable by external measurement. Cost that cannot be seen cannot be governed.

### P5 — Archive is containment, not generation control
Archive/retention prunes rows *after* they exist; it cannot lower the generation rate. **Justification:** per `docs/production_reality_validation_v1.md`, 30-day archive cannot act until ~2026-07-30 while the table crosses critical ~2026-07-11. Retention is downstream of the problem.

### P6 — Scheduler cadence alone must never justify rewriting identical data
"The loop ticked" is not a valid reason to write. A tick may *trigger a check*; only a detected change may trigger a *write*. **Justification:** decouples the trigger (cheap check) from the effect (expensive, growth-causing write).

### P7 — Snapshot generation must remain bounded under unlimited historical growth
The number of writes per unit time must be independent of how many historical rows already exist. **Justification:** generation cost must not degrade as the table grows; the append count must be a function of *change events*, not of table size or age.

### P8 — Operational hot paths must never depend on snapshot history
Merchant/API/widget reads consume only the latest row per `(store_slug, snapshot_type)`; no hot path may scan historical versions. **Justification:** already a Data-Growth rule (C-DATA-1/§5); reaffirmed here so generation changes never introduce a history dependency.

### P9 — Freshness requirements must be explicit per snapshot type
Each type declares its max acceptable staleness and its failsafe rebuild age as first-class, documented policy — not implicit TTL constants scattered in code. **Justification:** freshness is a product/UX contract; it must be legible and reviewable.

### P10 — Generation policies must be independently evolvable
Changing one type's policy (e.g. make `summary` event-driven) must not require touching another type's policy or the shared writer. **Justification:** enables incremental, low-risk migration and prevents a single change from destabilizing all types.

---

## 2. Architectural contracts (SG-*)

Binding contracts. Any future PR that touches snapshot generation must satisfy every applicable contract; a reviewer must be able to verify each.

| ID | Contract | Enforces | Verification |
|----|----------|----------|--------------|
| **SG-1** | **Generation follows change.** A write occurs only when a meaningful change (§4) is detected for that `(store, type)`. A scheduler tick may trigger a *check*, never a *write* by itself. | P1, P6 | Every write correlated to a change signal or fingerprint delta; no write path keyed solely on tick. |
| **SG-2** | **No identical rewrite.** Before persisting, compare the candidate payload's semantic fingerprint (§4.3) to the current latest row; equal ⇒ no new row. | P2 | Fingerprint gate present at the single write point; test proving identical payload does not append. |
| **SG-3** | **History never drives hot reads.** Reads fetch only the latest row per `(store_slug, snapshot_type)`; no hot path queries prior versions. | P8 | Read path audit; latest-row-only query (already `fetch_latest_snapshot_row`). |
| **SG-4** | **Every generated snapshot has a measurable reason.** Each write records a `generation_reason` (e.g. `lifecycle_change`, `purchase`, `settings_change`, `failsafe`, `first_build`) and emits it in the write log/metric. | P4 | `generation_reason` present on every write; reason distribution observable. |
| **SG-5** | **Generation policies are independently configurable per type.** Each snapshot type has its own trigger mode, freshness policy, and enable flag, changeable without altering other types. | P3, P10 | Per-type policy table (§3) is the source of truth; no shared hardcoded cadence gates all types. |
| **SG-6** | **Fingerprint over canonical semantic content.** The change/identity fingerprint is computed over a canonicalized projection that **excludes volatile, non-semantic fields** (e.g. `generated_at`, "as of now" timestamps, key ordering, float/whitespace formatting). | P2, P1 | Fingerprint spec documents excluded fields; test proving volatile-only differences do not count as change. |
| **SG-7** | **Schedule is a failsafe, not the primary trigger.** Any time-based rebuild exists only as a safety net (missing/absent snapshot, correctness backstop) with an explicit, documented failsafe age — never as the routine generation mechanism. | P1, P6 | Failsafe age documented per type; schedule-triggered writes are a small, labeled minority of `generation_reason`. |
| **SG-8** | **Generation is bounded independent of history size.** Write rate is a function of change events, not of existing row count, table age, or rotation position. | P7 | No write path whose frequency scales with historical row count; growth KPI tracked (§6). |
| **SG-9** | **Derived snapshots are not independently generated.** A snapshot that is a pure projection of another (e.g. `dashboard_cards` ⊂ `summary`) is produced from, and only when, its source changes — never on its own clock. | P1, P3 | Derived-type mapping documented (§3); derived write occurs iff source write occurs. |
| **SG-10** | **Change detection must be cheaper than the build it gates.** The mechanism that decides whether to write must cost materially less than performing the write, or it defeats its purpose. | P4, P7 | Fingerprint/decision cost bounded (e.g. reuse already-built payload; hash, not re-query). |
| **SG-11** | **Freshness is an explicit, documented per-type contract.** Max acceptable staleness and failsafe age are declared in this document and mirrored in code, not implied by scattered TTL constants. | P9 | §3 freshness columns authoritative; code TTLs cross-referenced. |
| **SG-12** | **Governance is a reviewable artifact.** Adding a snapshot type, changing a trigger mode, or relaxing a freshness policy is a deliberate, documented change to this file (versioned like LT-C1). | P4, P10 | This doc is updated in the same PR; classification/policy table diff is reviewable. |

**Reserved for future enforcement:** contracts SG-1, SG-2, SG-6, SG-9 are candidates for an automated gate analogous to the LT-C1 CI gate (a "no time-only write path" / "fingerprint gate present" static check) once implemented. Not built in this phase.

---

## 3. Snapshot classification

Every snapshot type is classified by **importance** (critical / operational / informational) and assigned a **trigger mode** (event-driven / schedule-driven / hybrid) with justification and an explicit freshness policy.

**Definitions:**
- **Critical** — drives merchant decisions and recovery visibility; staleness materially misleads.
- **Operational** — supports live dashboard function; moderately time-sensitive.
- **Informational** — status/context; low sensitivity to staleness.
- **Event-driven** — regenerate on a meaningful change signal (§4).
- **Schedule-driven** — regenerate on a (low-frequency) timer; only valid where change signals are unavailable or where content is inherently time-bucketed.
- **Hybrid** — event-driven for correctness + a low-frequency failsafe/backstop (SG-7).

### 3.1 Actively generated today (the 6 the builder writes)

| Snapshot type | Class | Target trigger mode | Change signals | Freshness (max staleness / failsafe) | Why |
|---|---|---|---|---|---|
| **`normal_carts`** | **Critical** | **Hybrid** (event + failsafe) | cart-event mutation, reason capture, lifecycle change, purchase, archive/reopen | 45s / 300s | The live cart list merchants act on. Highest volatility and highest cost; already has a parity guard (the only content brake today) that SG-2 generalizes. |
| **`summary`** | **Critical/Operational** | **Hybrid** (event + time-bucket failsafe) | lifecycle change, purchase, reply, new cart, settings; **time-window rollover** (today/7d/30d boundary) | 60s / 300s | KPIs and counts. Mostly event-driven, but time-bucketed aggregates legitimately change at window boundaries even with no new data (the one justified schedule reason — SG-7). |
| **`dashboard_cards`** | **Operational** | **Derived from `summary`** (SG-9) | *none of its own* — it is `_extract_dashboard_cards(summary)` | Same as `summary` | Pure projection of `summary`. Must never be generated on its own clock; regenerate iff `summary` regenerates. |
| **`refresh_state`** | **Operational** | **Event-driven** | presence of newer underlying data (the very thing "refresh" signals) | 30s / 300s | Represents "is there newer data"; if nothing changed there is nothing to refresh — a textbook case where time-only writes are pure waste. |
| **`widget_panel`** | **Informational/Operational** | **Event-driven** | merchant widget/settings change, widget enable/disable, display config | 60s / long failsafe | Widget config changes rarely and only on merchant action. Scheduled rebuilds are almost entirely redundant. |
| **`store_connection`** | **Informational** | **Event-driven** | Zid connection/OAuth status change, reconnect, settings | 120s / long failsafe | Connection status changes almost never. Longest TTL today; the clearest case of scheduled waste. |

### 3.2 Defined but not currently generated by the builder (reserved types)

These constants exist in `dashboard_snapshot_v1.py` with TTL defaults but are not written by `build_store_dashboard_snapshots`. Classified now so future generation complies from day one.

| Snapshot type | Class | Target trigger mode | Why |
|---|---|---|---|
| **`monthly_summary`** | Operational/Informational | **Hybrid** (purchase/lifecycle event + month-boundary schedule) | Monthly aggregates change on conversions and at month rollover; low frequency. |
| **`whatsapp_readiness`** | Operational | **Event-driven** | Changes on provider/template/settings changes; not on a clock. |
| **`abandoned_candidates`** | Operational | **Event-driven** | Changes on cart-event / candidate detection. |

**Rule:** No reserved type may be brought online with a pure schedule-driven, always-write pattern; it must ship compliant with SG-1/SG-2/SG-5.

---

## 4. Meaningful-change definition

The heart of SG-1/SG-2. "Meaningful change" is what *justifies* a write.

### 4.1 Qualifies as meaningful change (write warranted)

| Signal | Affects types |
|---|---|
| **Lifecycle state changed** (any `customer_lifecycle_state` transition — LT-C1) | normal_carts, summary, dashboard_cards, refresh_state |
| **Purchase detected** (Purchase Truth record created) | normal_carts, summary, monthly_summary |
| **Reply received** (inbound customer reply) | normal_carts, summary, refresh_state |
| **New / mutated abandoned cart** (cart-event sync changing visible data) | normal_carts, summary, abandoned_candidates, refresh_state |
| **Merchant settings changed** (automation mode, VIP, widget, WhatsApp settings) | widget_panel, summary, whatsapp_readiness |
| **Widget config changed** (enable/disable, display name) | widget_panel |
| **Store connection status changed** (Zid connect/disconnect/OAuth) | store_connection |
| **Provider/template readiness changed** | whatsapp_readiness |
| **KPI counter delta** crossing the display projection (a count a card actually shows changed) | summary, dashboard_cards |
| **Time-window boundary rollover** (today/7d/30d/month bucket advanced) — *only* for inherently time-bucketed aggregates | summary, monthly_summary |
| **First build / missing snapshot** (no latest row exists) | all (failsafe) |

### 4.2 Does NOT qualify (write forbidden by SG-1/SG-2)

| Non-signal | Rationale |
|---|---|
| **Scheduler tick / builder rotation reached this store** | Time carries no change information (P6). |
| **TTL/`expires_at` elapsed with no data change** | Staleness age ≠ data change; freshness may be refreshed in place, not by a new row. |
| **Identical payload** (semantic fingerprint equal to latest row) | Zero read value (P2, SG-2). |
| **Unchanged counters / aggregates** | No card content differs. |
| **Volatile-only differences** — `generated_at`, embedded "now" timestamps, key ordering, float/whitespace formatting, non-semantic serialization noise | These are excluded from the fingerprint (SG-6); they must never register as change. |
| **Rebuild triggered purely to reset `expires_at`** | Freshness bookkeeping is not content change; handle via in-place touch or read-side policy, not a new version. |

### 4.3 Semantic fingerprint (SG-6) — definitional requirements (not an implementation)

A compliant fingerprint MUST:
1. Be computed over a **canonical projection** of the payload (stable key order, normalized number/formatting).
2. **Exclude** the volatile fields listed in §4.2 (timestamps, "as of now", version, generation metadata).
3. Represent **exactly the content a read would return** to the merchant — so that "fingerprint unchanged" provably means "the merchant sees the same thing."
4. Be **cheaper to compute than the write it gates** (SG-10).

The fingerprint is the objective definition of "identical payload" for SG-2. Its excluded-field list is itself governed (SG-12): changing it is a reviewable decision.

---

## 5. Future implementation options (trade-offs only — do NOT implement)

Options a future optimization MAY choose from. This section explains trade-offs; it selects nothing and builds nothing.

### 5.1 Content hash / payload fingerprint (satisfies SG-2, SG-6)
- **Approach:** hash the canonical semantic projection; store the hash on the latest row; skip write when equal.
- **Pros:** directly kills identical rewrites (the 99.66%); localized to the write point; type-agnostic; testable.
- **Cons:** must define the excluded-field set carefully (a leaky projection makes everything "changed"); adds a hash + one comparison read per candidate; needs a freshness story for the "no-write but TTL expired" case (touch `expires_at` in place vs accept read-side staleness/hot-slice).
- **Risk if done wrong:** volatile fields left in the projection ⇒ zero reduction; over-aggressive exclusion ⇒ missed real changes (stale reads).

### 5.2 Per-type generation policy (satisfies SG-5, SG-3, SG-11)
- **Approach:** a policy object per snapshot type (trigger mode, freshness, enable flag, failsafe age) driving the builder.
- **Pros:** stops co-writing 6 types when one changed (SG-9); lets stable types (`store_connection`, `widget_panel`) drop to near-zero writes; independently evolvable (P10).
- **Cons:** more configuration surface; requires the builder to consult policy per type rather than a single loop.
- **Risk if done wrong:** inconsistent policies across types; policy drift from this document (mitigated by SG-12).

### 5.3 Event-driven generation (satisfies SG-1, SG-7)
- **Approach:** emit change signals from the sources in §4.1 (lifecycle, purchase, reply, cart-event, settings) and rebuild the affected types on signal.
- **Pros:** generation rate tracks real activity; near-zero writes for quiet stores; strongest alignment with P1.
- **Cons:** highest integration effort; must guarantee no missed signal (hence the hybrid failsafe, SG-7); ordering/debounce needed to avoid write storms on bursty carts.
- **Risk if done wrong:** missed signal ⇒ stale dashboard (mitigated by failsafe backstop); signal storm ⇒ re-introduces volume (mitigated by SG-2 fingerprint gate downstream — even bursts collapse to one write per real change).

### 5.4 Adaptive scheduling (partial; supports SG-7)
- **Approach:** vary rebuild/check cadence by observed volatility (active stores checked more often; dormant stores rarely).
- **Pros:** cheap to add on top of the current loop; reduces checks on idle stores.
- **Cons:** still time-driven at heart; without SG-2 it only reduces *checks*, not identical *writes*; heuristic tuning burden.
- **Risk if done wrong:** treated as a substitute for change-detection (it is not) — must be paired with SG-2.

### 5.5 In-place freshness touch (supports the SG-2 "no-write but expired" case)
- **Approach:** when content is unchanged but the row is TTL-expired, update `expires_at`/`generated_at` on the existing row instead of inserting a new version.
- **Pros:** preserves freshness semantics with zero row growth.
- **Cons:** turns an append into an update (one write, no new row) — must be reconciled with the append-only invariant in Data-Growth C-DATA-6 (a deliberate, documented evolution, not a silent one).
- **Risk if done wrong:** breaking the versioning/rollback assumptions elsewhere — requires SG-12 review.

> **SG-12 ratification (2026-07-04):** the in-place freshness touch is **adopted**. When a rebuild produces content semantically identical to the current latest row *and* that row is TTL-stale, `services/dashboard_snapshot_v1.touch_dashboard_snapshot_freshness` refreshes `generated_at`/`expires_at`/`updated_at` on the existing row instead of appending a new version. This is a scoped, reviewed evolution of Data-Growth **C-DATA-6**: the latest-row read contract (SG-3) is unchanged, no historical version is mutated, and `version` is not advanced. Identical-but-fresh rebuilds write nothing at all.

**Recommended targeting order (from the audit):** generation first (5.1 + 5.2 + 5.3), scheduling second (5.4), retention/archive as containment only (P5). This section does not authorize building any of them.

---

## 6. Risks of violating governance

| Violated | Consequence | Severity |
|---|---|---|
| **SG-1 / SG-6 (write on tick / leaky fingerprint)** | Recurrence of ~42k/day identical-rewrite growth; P0-2 returns. | **High** |
| **SG-2 (identical rewrite)** | Table crosses critical thresholds before archive can act (see `production_reality_validation_v1.md`); DB bloat/pressure. | **High** |
| **SG-3 / SG-8 (history in hot reads / size-coupled generation)** | Latest-row index bloat; dashboard read latency degrades as history grows; pool exhaustion. | **High** |
| **SG-4 (no measurable reason)** | Growth becomes invisible again; regressions only found by external measurement; no way to attribute cost. | **Medium** |
| **SG-5 / SG-9 (coupled types / independent derived writes)** | 6× write amplification persists; changing one type destabilizes all; `dashboard_cards` doubles `summary` cost. | **Medium** |
| **SG-7 (schedule as primary trigger)** | Silent drift back to clock-driven generation even with events present. | **Medium** |
| **SG-10 (expensive change detection)** | The gate costs more than it saves; net regression. | **Medium** |
| **SG-11 / SG-12 (implicit / unreviewed policy)** | Freshness contracts drift from product intent; ad-hoc behavior re-invented per PR. | **Medium** |

**Cross-references:** these map to Data-Growth risks §7 (`dashboard_snapshots` "High") and to Platform risk **P0-2**.

---

## 7. Migration guidance

How a future implementation adopts this governance **without production behavior change**, in reversible, low-risk phases. (Guidance only — nothing is executed here.)

**Phase 0 — Freeze (this document).** Governance ratified; classification and contracts are the reference. No code.

**Phase 1 — Observability (behavior-neutral).** Add `generation_reason` + semantic fingerprint **in shadow**: compute and log/emit them on every existing write (SG-4, SG-6 spec) without gating anything yet. Establishes the reason distribution and the "% identical" baseline. Fully reversible; no read/write behavior change.

**Phase 2 — Identical-rewrite gate (SG-2), read-neutral.** Introduce the fingerprint skip at the single write point. Because reads only ever need the latest *content*, not-writing an identical payload is read-equivalent — with one caveat: handle the "unchanged but TTL-expired" case via §5.5 in-place touch or an explicit read-side freshness policy, decided under SG-12. Ship behind a per-type flag (default off) → enable per type after verifying parity. This is the single highest-leverage, lowest-risk step.

**Phase 3 — Per-type policy (SG-5, SG-9).** Externalize each type's trigger mode / freshness / enable flag (§3). Split derived `dashboard_cards` to follow `summary` (SG-9). Enable low-volatility types (`store_connection`, `widget_panel`) to skip routine rebuilds first (safest, biggest quiet-store win).

**Phase 4 — Event-driven triggers (SG-1, SG-7).** Wire §4.1 change signals to targeted rebuilds; demote the schedule to a labeled failsafe (SG-7). The SG-2 fingerprint gate remains downstream so even bursty signals collapse to one write per real change.

**Phase 5 — Automated enforcement (optional).** A static gate (LT-C1-style) asserting "no time-only write path" / "fingerprint gate present" / "derived types not independently generated," so drift fails CI.

**Backward-compatibility invariants across all phases:** latest-row read contract unchanged (SG-3); no hot-path history reads; freshness contracts per §3 honored; archive untouched (P5); any append→touch change to `expires_at` is a documented SG-12 evolution of Data-Growth C-DATA-6, not silent.

---

## 8. Success criteria (this phase)

| Criterion | Status |
|---|---|
| Snapshot generation elevated to a governed truth domain | ✅ (this doc) |
| 10 principles defined and justified | ✅ §1 |
| Architectural contracts (SG-1…SG-12) defined and verifiable | ✅ §2 |
| Every snapshot type classified (importance + trigger mode) | ✅ §3 |
| Meaningful change explicitly defined (qualifies / does not) | ✅ §4 |
| Future implementation options with trade-offs (no build) | ✅ §5 |
| Risks of violating governance enumerated | ✅ §6 |
| Reversible, behavior-neutral migration path | ✅ §7 |
| No production/scheduler/archive/code changes made | ✅ (documentation only) |

**Outcome:** future snapshot optimization must *implement this governance*, not invent new behavior — the same posture as Purchase Truth, Lifecycle Truth (LT-C1), and Data Growth.

---

## Appendix — Code anchors (for future implementers)

| Concern | Module / anchor |
|---|---|
| Single write point (append-only) | `services/dashboard_snapshot_v1.py` → `upsert_dashboard_snapshot` (:335) |
| Type constants + TTLs (freshness) | `services/dashboard_snapshot_v1.py` → `SNAPSHOT_TYPE_*` (:25-33), `snapshot_ttl_seconds` (:116) |
| Latest-row read contract (SG-3) | `services/dashboard_snapshot_v1.py` → `fetch_latest_snapshot_row` (:297) |
| Builder (6-type co-write; SG-9 target) | `services/dashboard_snapshot_builder_v1.py` → `build_store_dashboard_snapshots` (:152) |
| Only existing content brake (SG-2 precedent) | `dashboard_snapshot_normal_carts_parity_v1.build_and_guard_normal_carts_snapshot_write` |
| Loop cadence (SG-1/SG-7 target) | `services/dashboard_snapshot_loop_v1.py` (:155-175), `snapshot_build_store_limit` (:100) |
| Derived-type source (SG-9) | `dashboard_snapshot_builder_v1._extract_dashboard_cards` (:137) |
| Change signal sources (§4.1) | lifecycle: `services/customer_lifecycle_states_v1.py` (LT-C1); purchase: `services/cartflow_purchase_truth.py`; cart-event: `main.handle_cart_abandoned` / `services/recovery_orchestration/coordinator_v1.py` |
| Growth KPI / measurement | `docs/data_growth_governance_v1.md` §6; `scripts/_data_growth_measurement_v1_out/` |
| Model (no key uniqueness) | `models.py:829-861` (`DashboardSnapshot`) |
