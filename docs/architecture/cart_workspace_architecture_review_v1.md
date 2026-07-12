# Cart Workspace Architecture Review V1

**Type:** Architectural Integrity Review  
**Date (UTC):** 2026-07-12  
**Nature:** Prove that engineering can implement Cart Workspace exactly as the Product Foundation designed — without altering product behavior, operational governance, or runtime simplicity.  
**Not:** code review, implementation, performance tuning, UI design, or Product amendment.

---

## Permanent Architectural Principle

> **Architecture translates Product Truth. It never redefines Product Truth.**

Every architectural compromise must preserve approved product behavior.  
If architecture cannot support an approved product behavior, the issue returns to **Product Governance** for formal review.  
Architecture is **not authorized** to silently redefine product behavior.

---

## Constitutional inputs (read-only — not modified)

| Document | Role |
|----------|------|
| [`cart_workspace_constitution_v2.md`](../product/cart_workspace_constitution_v2.md) | Surface law |
| [`cart_workspace_constitutional_decisions_log_v1.md`](../product/cart_workspace_constitutional_decisions_log_v1.md) | Why law exists |
| [`cart_workspace_glossary_v1.md`](../product/cart_workspace_glossary_v1.md) | Vocabulary |
| [`merchant_decision_and_ownership_map_v1.md`](../product/merchant_decision_and_ownership_map_v1.md) | Dual-axis ownership + T1–T12 |
| [`decision_admission_matrix_v1.md`](../product/decision_admission_matrix_v1.md) | Binary Admit / compiled gates |
| [`cart_workspace_ux_blueprint_v1.md`](../product/cart_workspace_ux_blueprint_v1.md) | Zones, cards, attention |
| [`cart_workspace_operational_behavior_blueprint_v1.md`](../product/cart_workspace_operational_behavior_blueprint_v1.md) | Living runtime behavior |
| [`cart_workspace_ratification_v1.md`](../product/cart_workspace_ratification_v1.md) | Pack ratification |

**Derivation direction:** Product → Architecture → Engineering Spec → Implementation. Never reverse.

---

## Deliverables index

| Deliverable | Location |
|-------------|----------|
| Behavioral-to-Architecture Mapping | Part 1 |
| Runtime State Model | Part 2 |
| Rendering Architecture Review | Part 3 |
| Runtime Architecture | Part 4 |
| Data Ownership Review | Part 5 |
| Performance Readiness Review | Part 6 |
| Evolution compatibility | Part 7 |
| Constitutional integrity audit | Part 8 |
| Architectural Risk Register | Part 9 |
| Final Architecture Verdict | Part 10 |

---

# Part 1 — Behavioral Architecture

## 1.1 Architectural planes (where logic lives)

Product behavior is implemented by **four planes**. No plane may absorb another’s authority.

| Plane | Owns | Must never own |
|-------|------|----------------|
| **P0 Truth / Execution** | Lifecycle Truth peers, recovery execution, Signals→Evidence→Proof upstream | Workspace cards; merchant attention; Admit invention |
| **P1 Ownership Runtime** | Dual-axis holders (Execution Owner, Decision Owner); Override mode Active/Inactive; transition recording for T1–T12 | Rendering; ranking theater; Status-as-Decision |
| **P2 Admission Runtime** | Compiled Admit \| Do Not Admit predicates (Gates A–F / R01–R20); Evidence fingerprint; Admission audit fields | Live economics scoring; markdown governance I/O; UI |
| **P3 Workspace Projection** | Merchant-safe projection of **already-admitted** Decisions + peripheral C/D/E aggregates | Re-running Admission; inventing ownership; Action without Decision |
| **P4 Rendering** | How projection is shown under load/refresh/uncertainty (composition plan only) | Business logic; Admit; ownership transfer; zone membership |

**Compile rule (binding):** Ownership Economics, Ownership Stability, Admission Economics, and Rejection Stability are **design-time**. Runtime executes pre-compiled rules only — **Governance Must Compile Into Runtime Simplicity**.

## 1.2 Behavioral-to-Architecture Mapping

Every Operational Behavior Blueprint rule maps to exactly one primary architectural responsibility. **No behavioral orphan.**

### Lifecycle (WL / LC)

| Behavior rule | Architectural responsibility | Plane |
|---------------|------------------------------|-------|
| WL-0 Open / Reconcile | Read Ownership + open Decisions projection; **no** transition on view | P1 read + P3 |
| WL-1 Quiet Confidence | Projection empty for Zones A/B → Quiet composition | P3 → P4 |
| WL-2 Override Attention | Zone A list = Override-admitted Decision identities only | P2 Admit T2 + P3 |
| WL-3 Decision Attention | Zone B list = normal-admitted Decision identities | P2 Admit T1 + P3 |
| WL-4 Merchant Judgment | Focus lock on Decision identity; Action endpoint invokes T3 path | P3 + P1 write on Action |
| WL-5 Ownership Return | Transition recorder emits T3/T4/T5; projection removes Decision | P1 → P3 |
| WL-6 Calm Recovery | When open Decision set empty → Quiet plan | P3 → P4 |
| WL-7 Terminal Outcome | T10/T11 update completion rollup; never Admit | P0/P1 → P3 Zone D |
| LC-1 View ≠ transfer | Workspace open API is read-only for ownership | P1 |
| LC-2 Advances only on T* / Admit | Transition service is sole writer of ownership axes | P1/P2 |
| LC-3 Refresh/poll no advance | Idempotent reconcile; fingerprint dedupe | P1/P2 |
| LC-4 Quiet→Decision only via Admit | Card factory gated by Admit record | P2→P3 |
| LC-5 No silent delete | Card exit requires transition id | P1→P3 |
| LC-6 T8 alone no card | Override mode flag ≠ Decision row | P1 mode vs P2 Admit |

### Decision Card

| Behavior rule | Architectural responsibility | Plane |
|---------------|------------------------------|-------|
| Decision identity | Durable `decision_id` bound to Admission id + Evidence fingerprint | P2 |
| Card identity = Decision identity | Projection key = `decision_id`; 1:1 while Decision Owner = Merchant | P3 |
| Creation on T1/T2 only | Admit success creates Decision record + ownership write | P2+P1 |
| Do Not Admit → no card | Rejection leaves no Decision row | P2 |
| Update explanation only (AS-3) | Patch explanation fields; forbid second Admit | P2/P3 |
| Escalation = Admit transfer | Escalation is not a separate subsystem | P2+P1 |
| Merchant Action → T3 | Action handler closes Decision + returns Decision Owner to CartFlow | P1 |
| Disappearance only T3/T4/T5 | Delete/hide from active projection only after transition | P1→P3 |
| Reappear only new Evidence | Closed fingerprint cannot Admit again; new fingerprint → new `decision_id` | P2 |

### Zones A–E

| Behavior rule | Architectural responsibility | Plane |
|---------------|------------------------------|-------|
| Zone A appear/disappear | Derived: L0 Active ∧ count(Override Decisions)>0 | P3 derived |
| Multiple Override cards | Multiple Decision rows with override flag; R08 blocks dup Admit | P2+P3 |
| Zone A above B | Projection sort: override partition first | P3 |
| Zone B Admit-only | Filter Decision Owner=Merchant ∧ ¬override | P3 |
| Stable within-zone order | Persist `admitted_at` (or approved rank); no reshuffle on refresh | P3 |
| Merge = identity coalesce | Dedupe on fingerprint / open Decision (RJ-DUPLICATE) | P2 |
| Zone C reassurance | Aggregate Exec=CartFlow calm indicator — **not** per-cart list | P3 aggregate |
| Zone D compact | Bounded completion rollup / recent outcomes snapshot | P3 rollup |
| Zone E exceptional | Rare merchant-safe health flag; default absent; never Admin metrics | P3 exceptional |

### Attention / Live / Calm / Failure / Invariants

| Behavior rule | Architectural responsibility | Plane |
|---------------|------------------------------|-------|
| Focus A→B→C→D→E | Attention selector consumes projection order; Override may interrupt | P3→P4 |
| Never interrupt on retry/Status/Knowledge | Those events never create Decision rows | P0/P2 reject |
| Mid-judgment focus protect | Client/session focus lock; Override may break; refresh must not | P4 (+ session) |
| Live new Admit | Event → compiled Admit → Decision row → projection patch | P2→P3 |
| Live resolve / purchase | T3/T5/T10 writers → projection remove + Zone D bump | P1→P3 |
| Slow sync | Last-good projection hold; no flicker empty↔full | P4 |
| Calm Recovery sequence | Ordered projection events: resolve cue → next focus → Quiet | P3→P4 |
| BI-1…BI-15 | Enforced by plane boundaries + transition/Admit invariants | All |

**Orphan check:** Every Part 1–11 behavior rule in the Operational Behavior Blueprint has a plane owner above. **No orphan.**

## 1.3 Forbidden architectural patterns

| Pattern | Why forbidden |
|---------|----------------|
| Hidden Admit inside renderer | Redefines Product Truth in P4 |
| Second “priority queue” duplicating Zone A | Duplicate Override behavior |
| Implicit CartFlow→Merchant on Status change | Implicit transition (I15) |
| Client-only ownership | Diverges from P1 source of truth |
| Re-evaluating Constitution/markdown on request | Violates compile-into-simplicity |

---

# Part 2 — State Architecture

## 2.1 Design goals

- Avoid state explosion  
- Deterministic transitions  
- No duplicated state  
- No derived-state ambiguity  

## 2.2 Canonical Workspace State Model

### Source states (authoritative — store once)

These are the **minimum** durable runtime states. Workspace UI phases are **not** stored separately.

| State family | Canonical values | Writer | Notes |
|--------------|------------------|--------|-------|
| **Execution Owner** | `cartflow` \| `merchant` | P1 on T6/T7 | Exactly one |
| **Decision Owner** | `cartflow` \| `merchant` | P1 on T1–T5 | Exactly one |
| **Override mode** | `inactive` \| `active` | P1 on T8/T9 | Mode, not owner |
| **Journey phase** | `active` \| `completed` \| `archived` | P1 on T10/T11/T12 | Maps S1–S6 / S7 / S8 |
| **Decision record** (0..n open) | `{ decision_id, admission_id, evidence_fingerprint, path: normal\|override, primary_action, explanation_bundle, admitted_at, status: open\|resolving\|closed }` | P2 create; P1 close | Open ⇒ Decision Owner merchant for that journey |
| **Admission outcome ledger** | Admit/Reject + AA audit fields + fingerprint | P2 | Enables AS-1/AI-16 without re-Admit |

**Composite ownership postures S1–S9** are **derived** from the four axes above — not a parallel stored enum that can drift.

```text
S1 = Exec CF ∧ Dec CF ∧ Override inactive ∧ active
S2 = Exec CF ∧ Dec Merchant ∧ Override inactive ∧ open normal Decision
S3 = Exec CF ∧ Dec CF ∧ Override active ∧ no Override Decision yet   (transient)
S4 = Exec CF ∧ Dec Merchant ∧ Override active ∧ open Override Decision
S5/S6 = Exec Merchant ∧ … (T6)
S7/S8/S9 = journey phase / knowledge posture
```

### Derived workspace phases (not stored)

| Derived | Function of source |
|---------|-------------------|
| WL-1 Quiet | No open Decision records for merchant scope |
| WL-2 Override Attention | ≥1 open Decision with `path=override` |
| WL-3 Decision Attention | ≥1 open normal Decision ∧ zero Override open |
| WL-4 Judgment | Session focus on open `decision_id` (ephemeral) |
| WL-5/WL-6 | Transition events + empty open set |
| Zone visibility | Pure functions of open Decisions + aggregates |

**Rule:** If a value can be computed from source states, it must not be a second writable store.

### Transition determinism

Only **T1–T12** (Ownership Map) and compiled Admit/Reject may change source states.  
Refresh, poll, duplicate webhook, and UI navigation are **non-transitions**.

### Anti-explosion rule

Do **not** mint runtime states for: Signal types, Status labels, retry counts, Knowledge claims, Admin diagnostics, or motion classes. Those remain Evidence/Execution/presentation concerns.

---

# Part 3 — Rendering Architecture Review

## 3.1 Projection model

```text
Truth / Execution (P0)
    → Ownership + Admission (P1/P2)     [source]
    → Workspace Projection (P3)        [merchant-safe Decision lists + C/D/E aggregates]
    → Rendering Plan (P4)              [composition under load/refresh/uncertainty]
    → Presenters                       [paint only]
```

**Projection contents (conceptual):**

| Field | Source |
|-------|--------|
| `zone_a[]` | Open Decisions `path=override` ordered stably |
| `zone_b[]` | Open Decisions `path=normal` ordered stably |
| `zone_c` | Calm aggregate (Exec CF progressing) — optional peripheral |
| `zone_d` | Bounded completion rollup |
| `zone_e` | Optional exceptional merchant-safe flag |
| `attention_focus_decision_id` | Derived A-first then B; session may pin |
| `workspace_phase` | Derived WL-* |
| `freshness` | `final` \| `revalidating` \| `uncertain` (render only) |

## 3.2 Rendering ownership

| Role | Authority |
|------|-----------|
| **Workspace Rendering Owner** | Sole authority for merchant-visible Workspace composition from a Projection + freshness | 
| **Presenters** | Paint zones/cards from plan only |
| **Data ingress** | May propose projection updates; may not invent Admit/ownership |

**Law:** No rendering behavior may invent product behavior. No rendering layer owns business logic.

**Relation to existing Cart Page RSC:** Cart Page Rendering State Controller V1 owns **current `#carts` composition**. Cart Workspace is a **Decision Workspace** identity (Constitution). Architecture must treat Workspace rendering as a **separate rendering owner** consuming Decision projection — not a silent reuse of Status/queue composition that would redefine product identity. Migration from Cart Page V2 to Workspace is an Engineering Spec concern; this review forbids merging Status-taxonomy IA into Workspace rendering.

## 3.3 Card identity / list identity

| Identity | Rule |
|----------|------|
| **Card key** | `decision_id` (stable) |
| **List identity Zone A** | Ordered set of Override `decision_id`s |
| **List identity Zone B** | Ordered set of normal `decision_id`s |
| **Forbidden** | Keying cards by cart id alone (allows duplicate Decisions / Status drift); keying by Status |

## 3.4 Update strategy

| Strategy | Rule |
|----------|------|
| Create | Insert card when Decision record opens |
| Update in place | Patch explanation on same `decision_id` |
| Resolve | Mark resolving → remove from A/B after T3/T4/T5; emit Calm Recovery plan step |
| Revalidate | Soft revalidate must **not** clear last-good open Decisions (confidence / no flicker) |
| Refresh | Re-read projection; **no** ownership/Admit side effects |

Motion classes (Replace/Merge/Collapse/… ) are **projection event types**, not CSS.

---

# Part 4 — Runtime Architecture

## 4.1 Ownership transitions

| Requirement | Architecture |
|-------------|--------------|
| Deterministic T1–T12 | Single Ownership Transition service; every write records `from → to → gate → evidence/policy id` |
| No implicit transitions | Ingress adapters emit Signals/Evidence only; they do not set Decision Owner |
| Dual axes independent | Execution and Decision fields updated only by allowed gates (I16) |
| Override non-oscillation | T8 while already Active is no-op (OS-4) |

## 4.2 Admission execution

| Requirement | Architecture |
|-------------|--------------|
| Binary Admit/Reject | Compiled Decision Admission function; no free-form reasoning |
| Hot path | Predicates only — zero governance document I/O; zero live OE/AE scoring |
| Fingerprint | Evidence fingerprint stored; AS-1 / R17 / R14 enforced before Admit |
| Audit | AA-1…AA-5 fields written at decision time from rule ids |
| Fail closed | Unclassified → Do Not Admit (AI-15) |

## 4.3 Live updates

| Event class | Runtime path |
|-------------|--------------|
| Candidate for Admit | Evidence change → compiled Admit → maybe T1/T2 → projection patch |
| Open Decision observation | Explanation patch only |
| Completion / purchase | T10/T5 → close Decision if open → Zone D rollup |
| Duplicate / retry | Idempotent observe; no transition |

## 4.4 Refresh strategy

Merchant refresh = **projection re-read**.  
Must preserve: open Decisions, stable order, last-good under uncertainty.  
Must not: re-Admit, reorder thrash, clear cards, transfer ownership.

## 4.5 Concurrency & race resistance

| Risk class | Required control |
|------------|------------------|
| Double Admit same fingerprint | Unique constraint / ledger check on fingerprint+open Decision |
| Action vs completion race | Close Decision with single writer; completion wins via T5/T10; Action idempotent if already closed |
| T8 vs T2 ordering | Mode Active before Override Admit; card only after T2 |
| Projection vs source lag | Render last-good; never invent Quiet by omitting known open Decisions |
| Multi-tab Action | Server-side Decision close is authoritative; other tabs reconcile to closed |

**Runtime simplicity preserved:** concurrency controls are ordinary idempotency + single-writer gates — not a governance interpreter.

---

# Part 5 — Data Architecture (Data Ownership Review)

## 5.1 Single Source of Truth per visible element

| Visible element | Source of truth | Projection | Cache / snapshot | Presentation |
|-----------------|-----------------|------------|------------------|--------------|
| Zone A cards | Open Override Decision records (P1/P2) | `zone_a[]` | Optional read-model of open Decisions | Card presenter |
| Zone B cards | Open normal Decision records | `zone_b[]` | Same read-model | Card presenter |
| Card explanation | Admission audit + merchant-safe execution summary bound to `decision_id` | explanation bundle on Decision | May denormalize on Decision row | Fields 1–5 |
| Primary Action | Admitted Action id on Decision (AI-5) | action affordance | — | Control |
| Quiet empty | Absence of open Decisions | derived phase WL-1/WL-6 | — | Quiet copy |
| Zone C | Aggregate “Exec CF active” indicator (not per-cart Status) | calm aggregate | Lightweight counter/flag | Peripheral copy |
| Zone D | Completion / purchase truth rollups (L4) | bounded recent summary | Snapshot/rollup table | Compact summary |
| Zone E | Exceptional merchant-safe health assertion | optional flag | Rare | Exceptional banner |
| Attention focus | Derived from A/B + session pin | focus id | Session only | Highlight |
| Override mode | L0 Active flag on journey | used for Zone A eligibility with Admit | — | Not shown as owner |

## 5.2 Non-duplication rules

| Forbidden duplication | Why |
|-----------------------|-----|
| Second Admit store in UI | Diverges from P2 |
| Ownership mirrored only in client | Diverges from P1 |
| Zone membership stored independently of Decision rows | Derived-state ambiguity |
| Status board as parallel truth | Violates Decision Over Status |
| Knowledge claims copied as Decisions | R18 / S9 |

## 5.3 Layer distinction (binding)

| Layer | May |
|-------|-----|
| **Source** | Own write authority for a fact |
| **Projection** | Merchant-safe reshape of source for Workspace |
| **Cache** | Accelerate reads; must invalidate to source; never mint Admit |
| **Snapshot / rollup** | Bounded Zone D / calm aggregates; never L2 Decision truth |
| **Presentation** | Paint plan; never decide membership |

---

# Part 6 — Performance Architecture (Performance Readiness Review)

## 6.1 Law

> **Growth ≠ Runtime complexity** for merchant-facing Decision paths.

Historical accumulation (Signals, retries, archives, Knowledge) must not slow Zone A/B reads.

## 6.2 Required shape

| Concern | Architecture |
|---------|--------------|
| **Open Decision path** | O(open Decisions per merchant) — intentionally small (Attention Budget) |
| **Projections** | Maintain **open-Decision read model** updated on Admit/close — do not scan full cart history on Workspace open |
| **Caching** | Cache projection; soft revalidate; never block Quiet/Decision on full history |
| **Snapshots / rollups** | Zone D from precomputed bounded rollups; archive outside L2 |
| **Archive boundaries** | S8/history surfaces separate; Workspace never browses unbounded archive (Q4) |
| **Admission evaluation** | Run on Evidence-change paths with compiled predicates + fingerprint short-circuit — not on every dashboard poll |
| **Hot-path contamination** | Forbid loading governance docs, KL browsers, Admin metrics, or full Operational History into Workspace request |

## 6.3 Scalability verdict (architectural)

Architecture **can** satisfy long-term scale **if** Engineering Spec mandates open-Decision read model + Zone D rollups + archive separation.  
Scanning all recoveries to “find what needs decision” would violate this review and Product Quiet/Admission economics.

---

# Part 7 — Evolution Architecture

Future layers **consume** Workspace architecture; they must not redefine it.

| Future / peer layer | Consume rule | Must not |
|---------------------|--------------|----------|
| **Knowledge Layer** | Supplies claims/proof inputs upstream of Admission | Auto-create Workspace cards; become Decision Owner |
| **Observation Layer** | Emits Signals/Evidence | Transfer ownership alone |
| **Operational Excellence** | Measures Quiet rate, justified transfers avoided, attention outcomes | Optimize card impressions; redefine success as activity |
| **Operational Intelligence** | May propose Proof toward compiled Admit | Bypass Admission; invent Escalation |
| **Business Intelligence** | Reports outside Workspace | Become Workspace IA |
| **Autonomous Operations** | Strengthens Execution under CartFlow | Require merchant supervision surface |
| **Admin Operations** | Separate operator surface | Merge diagnostics into Zone E or Decision cards |

**Compatibility:** Constitution §8 + Ownership Map Part 9 already require this separation. Architecture preserves it via plane boundaries (Part 1).

---

# Part 8 — Architectural Integrity (constitutional audit)

Question: can any architectural *simplification* accidentally change ownership, admission, behavior, attention, or Calm Recovery?

| Tempting simplification | Product damage | Required architecture stance |
|-------------------------|----------------|------------------------------|
| Treat VIP as sort key in one list | Breaks Priority Override / Quiet coexistence | Zone A partition mandatory |
| Derive Decision Owner from “has card in UI” | Hidden reverse ownership | P1 is source; UI derives |
| Re-Admit on refresh “to be safe” | Oscillation; Attention burn | Fingerprint ledger; AS-2 |
| Client-side only Calm Recovery | Work appears to vanish if sync fails | Server T3 + last-good hold |
| Fold Zone C into per-cart Status | Supervision product | Aggregate-only Zone C |
| Use existing Status tabs as Workspace | Violates Decision Workspace identity | New projection model |
| Live attention-cost scoring | Hot-path governance | Compile AE/OE into static rules |
| Skip T8; Admit Override directly without mode | Blurs detection vs Admission (I8) | Keep T8 then T2 |
| Demote A→B on any L0 clear without policy | Product undefined (OQ) / oscillation risk | **Return to Product** for T9 demote policy; do not invent |

**Integrity result:** No approved product behavior requires an architecture that redefines Product Truth. Where Product left OQ-1/2/4 open, architecture exposes **hooks** (T4/T6/T12) and **forbids invention**.

---

# Part 9 — Architectural Risk Register

Only evidence-based risks from Product Foundation + plane analysis. No speculative catalog.

| ID | Risk | Evidence | Impact if untreated | Mitigation (architectural) |
|----|------|----------|---------------------|----------------------------|
| **AR-1** | **State duplication** — storing WL phase or zone membership separately from Decision/ownership | Behavior derives WL/zones; duplicate stores drift | Flicker; false Quiet; mysterious disappear | Derived-only WL/zones; single Decision open set |
| **AR-2** | **Rendering ownership ambiguity** — presenters or legacy Cart Page paths decide membership | Existing RSC owns `#carts` composition; Workspace is new identity | Status IA returns; product redefined in UI | Dedicated Workspace Rendering Owner; presenters paint-only |
| **AR-3** | **Admit/Action race** — completion vs merchant Action concurrent | Ownership Part 8; live purchase vs open Decision | Duplicate close; orphan Decision Owner | Single-writer close; idempotent Action; T5/T10 precedence rules in Eng Spec |
| **AR-4** | **Projection inconsistency** — cache shows closed Decision or hides open one | Confidence / slow sync rules | Merchant distrust; false interruption | Last-good open set; version/token reconcile; soft revalidate |
| **AR-5** | **Event ordering** — VIP detect (T8) vs Override Admit (T2) vs notification | I8; LC-6; Q1 | Card without Admit or Admit without mode clarity | Ordered pipeline: eligibility → T8 → Override Admit T2 → projection |
| **AR-6** | **Hot-path contamination** — Workspace open scans history / runs rich KL / Admin health | Growth≠complexity; AE/OE compile rule | Latency + noise; Quiet destroyed | Open-Decision read model; rollups for D; E exceptional only |
| **AR-7** | **Fingerprint gap** — Evidence fingerprint not durable | AS-1, AI-16, R17 | Duplicate cards; oscillation | Fingerprint + admission ledger as Admit precondition |
| **AR-8** | **Product OQ leakage into Eng** — implementers invent T4/T6/T12 triggers | Ownership OQ-1, OQ-2, OQ-4; Behavior Blueprint deferral | Silent product redefine | Eng Spec blocks those paths until Product closes OQs; architecture keeps hooks only |

**Not listed as architectural risks:** pixel choices, animation libraries, framework selection, premature microservices — out of scope / speculative.

---

# Part 10 — Architectural Readiness

## 10.1 Evidence for readiness

| Criterion | Evidence |
|-----------|----------|
| Every behavior maps to a plane | Part 1 mapping complete; no orphan |
| Minimum canonical states | Part 2 source states; WL/zones derived |
| Rendering cannot invent product | Part 3 projection → plan → paint |
| Runtime preserves compile-into-simplicity | Part 4 compiled Admit; no governance I/O |
| Single sources of truth | Part 5 SoT table |
| Scale path without history scan | Part 6 open-Decision read model |
| Future layers consume, not redefine | Part 7 |
| Simplifications that change product are banned | Part 8 |
| Risks are real and mitigable without redefining product | Part 9 |

## 10.2 Pre-implementation Product closures (do not block Architecture Ready)

These remain **Product Governance** items. Architecture is ready; **Engineering Spec for those transition paths** must wait:

| ID | Item | Architecture stance until closed |
|----|------|----------------------------------|
| OQ-1 | Exact T4 expiry / return / supersede events | Hook only; no invented timers |
| OQ-2 | T6 manual-execution minimum content | Hook only; no Status taxonomy |
| OQ-4 | T12 reopen evidence classes | Hook only; OS-5 terminal until governed |

Closing them does **not** require changing this Architecture Review’s plane model.

## 10.3 Final Architecture Verdict

# Verdict A — Architecture Ready

Cart Workspace can be engineered to faithfully implement the approved Product Foundation without altering ownership, admission, behavior, attention, or Calm Recovery — provided Engineering Spec obeys the plane boundaries, derived-state rules, open-Decision read model, and OQ hooks in this review.

Architecture translates Product Truth. It does not redefine it.

---

## Answers for future engineering

| Question | Answer |
|----------|--------|
| Where does logic live? | P1 Ownership + P2 compiled Admission; not in P4 |
| Where does state live? | Dual-axis owners, Override mode, journey phase, Decision records, admission ledger |
| Where does ownership live? | P1 sole writer of Execution/Decision owners |
| Where does admission live? | P2 compiled Admit/Reject + fingerprint ledger |
| Where does rendering live? | P4 Workspace Rendering Owner over P3 projection |
| What must not happen? | Silent product redefine; Status-as-Workspace; hot-path governance; history scan for Decisions |

---

## Derivation gate

| Stage | Status |
|-------|--------|
| Product Foundation (Pack → Ownership → Admission → UX → Behavior) | Inputs (read-only) |
| **Cart Workspace Architecture Review V1** | **Verdict A — Architecture Ready** |
| High-Fidelity UX/UI (Figma) | May proceed under Product + this architecture (behavior fixed; pixels still must not invent behavior) |
| Engineering Specification | Next — must encode planes, SoT, races, OQ gates |
| Implementation | Blocked until Engineering Spec |

---

## Change log

| Version | Change |
|---------|--------|
| **V1** | Architectural integrity review: planes P0–P4; behavioral mapping; canonical state model; rendering/data/runtime/performance/evolution; integrity audit; risk register AR-1…AR-8; permanent principle; **Verdict A**. |

---

**End of Cart Workspace Architecture Review V1.**
