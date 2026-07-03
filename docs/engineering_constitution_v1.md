# CartFlow Engineering Constitution v1

**Status:** Ratified baseline — the official, highest-level engineering standard for CartFlow.
**Date (UTC):** 2026-07-04
**Scope:** Defines **how** CartFlow is engineered — the objective, methodology, rules, and decision process — not **what** has been built.
**Authority:** This document supersedes tribal knowledge. Where practice and this document disagree, this document wins (until formally amended per §11).
**Audience:** Every current and future developer, maintainer, owner, technical lead, and CTO of CartFlow.

**Purpose:** CartFlow has developed a consistent, evidence-driven engineering methodology across its truth layers, recovery engine, dashboard, and governance work. This constitution captures that methodology so it survives changes of developers, maintainers, and owners. A future engineer must be able to read this and know how CartFlow decisions are made, how new systems are introduced, and when work is complete — without asking anyone.

> **Note on intent:** Nothing in this document introduces a new engineering philosophy. It **formalizes the methodology CartFlow has already followed** throughout its evolution, so that methodology becomes durable, transferable, and understandable to whoever comes next.

**Canonical precedents (this constitution is descriptive of real CartFlow practice, not aspirational):**
- Truth ownership + automated enforcement — Lifecycle Truth LT-C1 (`services/customer_lifecycle_states_v1.py`, `scripts/lifecycle_truth_enforcement_v1.py`, `docs/lifecycle_truth_enforcement_v1.md`); Purchase Truth (`PurchaseTruthRecord`, `services/cartflow_purchase_truth.py`).
- Governance-before-optimization — `docs/data_growth_governance_v1.md` (C-DATA-*), `docs/snapshot_generation_governance_v1.md` (SG-*).
- Audit-before-refactor — `docs/dashboard_snapshot_generation_audit_v1.md`, `docs/cartflow_*_audit_v1*.md`.
- Composition-not-ownership — Architecture Consolidation V1 (`docs/architecture_consolidation_v1.md`, `services/recovery_orchestration/*`, R-01→R-05).
- Independent review — `docs/cartflow_architecture_review_board_v2.md`, `_v3.md`.
- Institutional memory — `docs/institutional_memory/*` (decision, failure, ownership, dependency, deferred registries + future-maintainer guide).
- Production validation — `docs/*_deploy_verification.md` + `scripts/*_deploy_verify_*`, `docs/production_reality_validation_v1.md`, `docs/platform_readiness_review_v1.md`.

---

## Section 1 — Engineering Objective

The purpose of CartFlow engineering is **not simply to ship features**. The purpose is to build a platform that remains, after years of growth and changes of developers, maintainers, or ownership:

| Property | Meaning | It is failing when… |
|---|---|---|
| **Understandable** | A new engineer can reason about the system from documentation and code, without tribal knowledge. | Only one person knows why something works. |
| **Governable** | Every important behavior has explicit rules that can be reviewed and enforced. | Behavior exists that no rule describes or constrains. |
| **Scalable** | The system's cost and correctness hold as merchants, traffic, and data grow. | A subsystem's cost grows with history/age rather than with real work. |
| **Operable** | The platform can be run, monitored, recovered, and rolled back safely by an operator. | Failures are silent, or recovery requires the original author. |
| **Maintainable** | Future changes are safe, local, and low-fear. | Changing one thing risks breaking unrelated things. |

**The prime directive:**

> **Every engineering decision must improve at least one of these five properties and must not silently weaken another.**

"Silently" is the operative word. A decision may deliberately trade one property for another **if the trade is stated, justified, and recorded** (e.g. accepting more code to gain governability, as in Architecture Consolidation). What is forbidden is weakening a property *without acknowledgement* — because unacknowledged erosion is how platforms decay past the point of repair. This objective is the "why" that every later section serves: the philosophy (§2) states the beliefs that protect these properties, the decision hierarchy (§3) resolves conflicts between them, and the lifecycle, gates, and maturity model exist to make them durable.

---

## Section 2 — Engineering Philosophy

CartFlow is a system whose value is **trustworthy automated action on real merchant money**. These principles protect that trust and serve the Engineering Objective (§1). They are ordered; earlier principles constrain later ones.

### 2.1 Truth Before Intelligence
Establish the single, correct answer to a question (Did the customer buy? What lifecycle state is this cart in?) **before** building features that reason on top of it. Intelligence built on unreliable truth amplifies error. *Precedent:* Purchase Truth and Lifecycle Truth were closed as owned, single-source layers before recovery decisioning was allowed to depend on them.

### 2.2 Governance Before Optimization
Write the rules a subsystem must obey **before** optimizing it. Optimization without governance produces fast, unbounded, unaccountable behavior. *Precedent:* Snapshot Generation Governance (SG-1…SG-12) was ratified *before* any snapshot generation optimization — deliberately, to prevent inventing ad-hoc behavior.

### 2.3 Audit Before Refactor
Understand the current behavior with evidence **before** changing it. A refactor that is not preceded by an audit is a guess. *Precedent:* the Dashboard Snapshot Generation Audit established *why* the table grows (clock-driven, append-only) before any change was proposed.

### 2.4 Measure Before Optimize
Quantify the problem with production evidence **before** choosing a solution. Numbers, not intuition, decide where effort goes. *Precedent:* the ~42k rows/day / 99.66%-superseded measurement targeted optimization at *generation*, not retention.

### 2.5 Architecture Before Features
A feature that violates the architecture is a liability regardless of its user value. Structure is decided first; features live inside it. *Precedent:* recovery orchestration was extracted into a cohesive package (R-01→R-05) so `main.py` composes rather than owns.

### 2.6 Simplicity Before Cleverness
Prefer the boring, legible solution. Cleverness that a future maintainer cannot safely modify is technical debt disguised as sophistication. A solution is only "good" if the next engineer can change it without fear.

### 2.7 Evidence Before Assumptions
Every claim — "it's fixed," "it's ready," "it scales" — must be backed by verifiable evidence (code citation, test, production probe). Assumptions are labeled as assumptions. *Precedent:* Production Reality Validation explicitly separated code reality, committed production evidence, and unverifiable live state — and refused to assert the latter.

### 2.8 Fail Safe, Fail Loud
When uncertain, fail **closed** (block the risky action) and fail **observably** (emit a signal). Silent failure is the most expensive failure because it destroys trust invisibly. *Precedent:* scheduler role verification fails closed; readiness checks surface blocking issues rather than proceeding.

---

## Section 3 — Engineering Decision Hierarchy

Principles sometimes conflict (a faster path may weaken correctness; a convenient shortcut may bypass governance). When two engineering choices conflict, resolve them with this **priority order** — higher wins:

| Priority | Value | Protects (Objective §1) |
|---|---|---|
| 1 | **Correctness** | Understandable, all |
| 2 | **Truth ownership** | Governable |
| 3 | **Operational safety** | Operable |
| 4 | **Reliability** | Operable |
| 5 | **Scalability** | Scalable |
| 6 | **Maintainability** | Maintainable, Understandable |
| 7 | **Performance** | Scalable |
| 8 | **Features** | (product value) |
| 9 | **Convenience** | (developer speed) |

**Three inviolable consequences of this order:**
- **Performance must never sacrifice correctness.** A fast wrong answer is worse than a slow right one.
- **Features must never weaken truth ownership.** No feature may introduce a second owner for a question that already has one (§7).
- **Convenience must never bypass governance.** "It was easier this way" is not a valid reason to skip an audit, a contract, or a gate.

**How to apply it:** when a trade-off appears, identify which value each option maximizes, and choose the option that wins at the highest conflicting priority. Then **record the trade** (§1 prime directive) so the sacrifice of a lower value is deliberate, not silent. *Precedents:* LT-C1 placed **truth ownership above feature convenience** (developers may propagate but not mint lifecycle state); the fail-closed scheduler placed **operational safety above availability/convenience**; Snapshot Governance placed **correctness + governance above the convenient time-driven write** (SG-1/SG-2). This hierarchy is not new policy — it is the ranking these decisions already followed, made explicit.

---

## Section 4 — The CartFlow Engineering Lifecycle

Every significant subsystem passes through nine stages **in order**. The order is not bureaucratic — each stage produces the input the next stage depends on. Skipping a stage means a later stage operates on unverified ground.

| # | Stage | What happens | Produces | Why it must come here |
|---|-------|--------------|----------|-----------------------|
| 1 | **Audit** | Establish current behavior with evidence (code + production data). No changes. | An audit doc: how it actually works, measured. | You cannot govern or fix what you have not understood. |
| 2 | **Governance** | Define the rules the subsystem must obey (principles + contracts). | A governance doc (e.g. C-DATA-*, SG-*). | Rules must exist before implementation so implementation has something to comply with. |
| 3 | **Contracts** | Turn governance into specific, verifiable statements with IDs. | A contract set (SG-1…, LT-ENF-1…). | Vague rules cannot be enforced or reviewed; contracts make compliance checkable. |
| 4 | **Implementation** | Build the change, complying with the contracts. Behavior-preserving where required. | Code + tests. | Only now is there a governed target to build toward. |
| 5 | **Metrics** | Make the subsystem's cost and behavior observable. | Operational metrics / logs / thresholds. | Unmeasured behavior silently regresses; §2.4/§7 require observability. |
| 6 | **Enforcement** | Where possible, make violations fail automatically (CI gate, guard). | An automated gate (e.g. LT-C1 CI gate). | Governance that relies on memory decays; enforcement makes drift impossible without a red build. |
| 7 | **Institutional Memory** | Record the decision, its rationale, alternatives, owner, and any deferrals. | Entries in `docs/institutional_memory/*`. | Knowledge that lives only in a person's head dies when the person leaves. |
| 8 | **Production Validation** | Verify the real production environment reflects intent, with evidence. | A deploy-verification / reality-validation doc. | "Merged" ≠ "true in production"; only evidence closes this gap. |
| 9 | **Closure** | Declare complete against the Definition of Done (§6); classify residual risk. | A closure note + updated SYSTEM_SUMMARY. | Prevents "abandoned in progress"; makes the completion criteria explicit and checkable. |

**Why the order matters:** Audit → Governance → Contracts is the *understand-then-constrain* spine; implementing before it produces ungoverned behavior. Metrics → Enforcement → Memory is the *make-it-durable* spine; without it a correct implementation quietly rots. Production Validation before Closure is the *reality gate*; closing on assumptions is how regressions ship. Every stage is cheap insurance against a much more expensive later failure.

**Right-sizing:** the lifecycle is mandatory for *significant* subsystems (truth layers, recovery, dashboard generation, scheduler, growth). Trivial changes (copy, one-line fixes) require only the relevant closure steps (tests + SYSTEM_SUMMARY if behavior changed). Judgment is expected; the default for anything touching truth, money, growth, or hot paths is the full lifecycle.

---

## Section 5 — Engineering Maturity Model

The lifecycle (§4) is what a subsystem *goes through once*; the maturity model is *where a subsystem stands over its whole life*. Every major subsystem should progress deliberately through these levels. **No subsystem is complete merely because it works** — "Working" is only Level 1 of the seven levels (0–6).

| Level | Name | The subsystem… | Exit criteria (advance when) | Illustrative CartFlow example |
|---|---|---|---|---|
| **0** | **Experimental** | exists as a prototype/spike; behavior not trusted. | intended behavior is defined and demonstrable. | an early spike before contracts. |
| **1** | **Working** | produces correct behavior in normal cases. | behavior is verified by tests, incl. edge/parity. | a feature that "works" but has no governance. |
| **2** | **Governed** | has written rules/contracts it must obey. | a governance doc + IDed contracts exist. | Snapshot generation (SG-1…SG-12 written). |
| **3** | **Measured** | exposes its cost/behavior as observable metrics. | metrics/thresholds are live and readable. | Data growth (measured row rates + thresholds). |
| **4** | **Enforced** | fails automatically when its contracts are violated. | an automated gate/guard blocks violations. | Lifecycle Truth (LT-C1 CI gate). |
| **5** | **Institutionalized** | is recorded in institutional memory: decision, owner, alternatives, deferrals. | decision/ownership/failure registries updated. | Recovery orchestration (owned, documented, deferred items registered). |
| **6** | **Production Proven** | is verified against real production with evidence, over time. | production-validation evidence confirms intended behavior in the live environment. | Durable restart-safe recovery core (validated in prod). |

**Rules of the model:**
- **Levels build on each other.** A subsystem cannot be "Enforced" (4) before it is "Governed" (2) and "Measured" (3) — there is nothing to enforce or observe otherwise. Advancement is deliberate, not accidental.
- **The engineering goal is not "Working." The goal is "Production Proven."** Stopping at Level 1 leaves behavior ungoverned, unmeasured, and unverified — exactly the decay the Objective (§1) forbids.
- **A subsystem may legitimately sit below Level 6** if that is a *recorded, deliberate* decision (e.g. "Governed, enforcement deferred as P2"). What is not acceptable is *believing* a subsystem is complete when it is only Working.
- **The current maturity level of each subsystem is tracked elsewhere, not here.** This section defines the *model*; live status belongs in `SYSTEM_SUMMARY.md`, review boards, and institutional memory (this constitution describes HOW, not WHAT — see §11). The examples above are illustrative of the levels, not an authoritative status ledger.

---

## Section 6 — Definition of Done

A subsystem is **NOT complete** until all of the following are true. "It works on my machine" and "the PR merged" are not on this list. (This is the checklist form of reaching Level 6, §5.)

| Criterion | Satisfied when | Canonical form |
|---|---|---|
| **Behavior verified** | Tests prove the intended behavior and parity where behavior must be preserved. | Parity tests (R-01→R-05), enforcement tests. |
| **Governance written** | The rules the subsystem obeys are documented. | `docs/*_governance_*.md`, contract docs. |
| **Contracts defined** | Rules are expressed as verifiable, IDed contracts. | SG-*, C-DATA-*, LT-ENF-*. |
| **Metrics available** | The subsystem's cost/behavior is observable in production. | Operational metrics, `[DASHBOARD PERF]`, growth KPIs. |
| **Documentation complete** | A future engineer can understand and safely modify it. | Subsystem doc + code anchors. |
| **Institutional memory updated** | Decision, rationale, alternatives, owner recorded. | `docs/institutional_memory/decision_registry.md`. |
| **Production validated** | Real production evidence confirms intended behavior. | Deploy-verification / reality-validation doc. |
| **Known risks classified** | Residual risks are ranked (P0–P3) and either fixed or explicitly deferred. | `deferred_items_registry.md`, risk tables. |
| **Ownership documented** | The owning module/person for the subsystem is named. | `docs/institutional_memory/ownership_map.md`. |

**Rule:** If any box is unchecked, the work is *in progress*, not done — regardless of whether code shipped. Partial completion must be stated honestly (e.g. "PARTIALLY CLOSED — infra deployed, effect pending") as in Production Reality Validation.

---

## Section 7 — Engineering Rules

Permanent, non-negotiable rules. These are the invariants that keep CartFlow trustworthy at scale. Each maps to an enforcing practice or precedent.

| Rule | Meaning | Enforced / evidenced by |
|---|---|---|
| **One source of truth per question** | Each important question (bought? lifecycle? which store?) has exactly one owning module that *mints* the answer. | LT-C1 (`customer_lifecycle_states_v1`), Purchase Truth. |
| **Every critical layer has an owner** | No orphan authority. Truth, recovery, dashboard, scheduler each name an owner. | `ownership_map.md`. |
| **Mint once, propagate freely** | Only the owner may create a truth value; everyone else may read/forward but never invent it. | LT-C1 enforcement gate (LT-ENF-1…4). |
| **No hidden writes** | Every write to durable state is discoverable and attributable. No side-effect writes on read/hot paths. | Snapshot writes only in the builder (SG-4 generation_reason); hot-path guard. |
| **Archive before delete** | Operational history is archived, never silently deleted. | C-DATA-2. |
| **`main.py` composes, never owns** | The entry module wires and delegates; business logic lives in owned services. | Architecture Consolidation V1 (`recovery_orchestration/*`). |
| **Hot paths never scan history** | Merchant/API/widget reads touch latest/bounded data only — never cold or historical rows. | C-DATA-1, SG-3, hot slice budgets. |
| **Every growth path is measurable** | Any table/structure that grows with activity has a measured rate and thresholds. | `data_growth_governance_v1.md` §6, growth measurement scripts. |
| **Every operational decision is observable** | Kill switches, skips, dispatches, failures emit signals. | `/health/scheduler`, operational metrics, `generation_reason`. |
| **Every deferred decision is documented** | Intentional non-action is recorded with rationale and revisit conditions — not forgotten. | `deferred_items_registry.md`. |
| **Generation follows change, not the clock** | Time alone never justifies rewriting identical data. | SG-1, SG-2, SG-6. |
| **Fail closed on uncertainty** | Ambiguous safety/authority state blocks the risky action. | Scheduler role fail-closed; readiness blocking issues. |
| **Evidence over assertion** | Claims of "done/ready/safe" cite verifiable evidence; unverifiable state is labeled. | Production Reality Validation tiers. |
| **Behavior-preserving unless intended** | Refactors/extractions must prove identical behavior; behavior changes are explicit and reviewed. | Parity tests, regression classification. |

---

## Section 8 — Architecture Decision Process

Every significant architecture decision follows this sequence. Each arrow is a gate: you may not proceed until the prior artifact exists. When options conflict at any step, resolve with the Decision Hierarchy (§3).

```
Problem        — stated precisely: what question/risk are we answering?
   ↓
Evidence       — code citations + production data establishing the current reality
   ↓
Audit          — documented analysis of how it actually works today (no changes)
   ↓
Governance     — the rules/contracts any solution must satisfy
   ↓
Implementation — the change, complying with governance, behavior-preserving where required
   ↓
Measurement    — observable metrics proving the change did what was intended
   ↓
Validation     — production evidence that reality matches intent
   ↓
Closure        — Definition of Done met; residual risk classified; memory + SYSTEM_SUMMARY updated
```

**Operating rules for the process:**
- **No skipping forward.** If governance does not exist, you are not ready to implement. If there is no evidence, you are not ready to audit conclusions.
- **Backtracking is allowed and expected.** If implementation reveals the audit was wrong, return to Audit. The process is a spine, not a straitjacket.
- **Each step leaves an artifact.** A decision with no written trail did not happen. The artifact is the decision.
- **Independent review at high-risk junctions.** Major structural decisions pass an Architecture Review Board pass (precedent: V2, V3) that may hold or defer (e.g. R-06 deliberately deferred).
- **Deferral is a valid outcome.** Choosing *not* to act, documented with revisit conditions, is a legitimate decision — not an omission.

---

## Section 9 — Engineering Quality Gates

Mandatory gates before **any major work is closed**. All must pass; a failed gate blocks closure.

| Gate | Question it answers | Evidence artifact |
|---|---|---|
| **Architecture Review** | Does this fit the intended structure and not increase coupling/complexity unjustifiably? | Review board note / verdict + grade. |
| **Behavior / Regression Classification** | Did behavior change only where intended? Are any test deltas explained (new failure vs pre-existing baseline)? | Parity tests + regression classification vs baseline. |
| **Production Validation** | Does real production reflect intent (not just merged code)? | Deploy-verification / reality-validation doc with dated evidence. |
| **Operational Readiness** | Can it be run, monitored, recovered, and rolled back safely? | Readiness report; kill switches; rollback note. |
| **Metrics Present** | Is its cost/behavior observable going forward? | Operational metrics / growth KPIs wired. |
| **Known-Risk Classification** | Are residual risks ranked P0–P3 and fixed-or-deferred? | Risk table + deferred registry entry. |
| **Institutional Memory Update** | Will the next engineer understand this without asking? | `decision_registry` / `ownership_map` / `failure_registry` update. |
| **SYSTEM_SUMMARY Update** | Is the single high-level record current? | `SYSTEM_SUMMARY.md` §10 changelog row + affected sections (per `.cursor/rules/system-summary-always-update.mdc`). |

**Gate rule:** Gates are AND, not OR. "Mostly done" fails the gate. A gate may be *satisfied by explicit deferral* (e.g. "monitoring deferred, tracked as P1-6"), but silence is failure.

---

## Section 10 — Engineering Anti-Patterns

Practices CartFlow **explicitly rejects**. Each is banned because it has a demonstrated cost; the antidote is named.

| Anti-pattern | Why it's rejected | Antidote (rule/section) |
|---|---|---|
| **Vibe coding** (changing behavior without evidence) | Guesswork on money-handling systems destroys trust. | Audit Before Refactor (§2.3), Evidence Before Assumptions (§2.7). |
| **Multiple truth owners** | Two answers to one question = irreconcilable state. | One source of truth per question (§7); LT-C1. |
| **Hidden coupling** | Invisible dependencies break silently under change. | Dependency map; composition not ownership (§7). |
| **Time-driven rewrites** | Clock-driven regeneration causes unbounded, valueless growth. | Generation follows change (§7); SG-1/SG-2; Snapshot Governance. |
| **Silent failures** | Invisible errors are the most expensive; trust erodes unseen. | Fail Safe, Fail Loud (§2.8); observability (§7). |
| **Unbounded growth** | Anything that grows without a measured bound eventually takes the system down. | Every growth path is measurable (§7); Data Growth Governance. |
| **Business logic in composition layers** | Logic in `main.py`/wiring can't be owned, tested, or governed. | `main.py` composes, never owns (§7). |
| **Closing work without production validation** | "Merged" is not "true in production." | Production Validation gate (§9); Reality Validation precedent. |
| **Optimizing before governing** | Fast + unaccountable = fast to fail. | Governance Before Optimization (§2.2). |
| **Undocumented deferral** | Forgotten decisions resurface as incidents. | Every deferred decision is documented (§7); deferred registry. |
| **History on the hot path** | Reading cold/historical data on live requests degrades and destabilizes. | Hot paths never scan history (§7); SG-3, C-DATA-1. |
| **Inflated status** ("ready" without evidence) | Overstated readiness ships regressions and misleads owners. | Evidence Before Assumptions (§2.7); honest partial-closure. |
| **Silently weakening a property** (§1) to gain another | Unacknowledged erosion accumulates until the platform is unmaintainable. | Prime directive (§1); record every trade (§3). |
| **Stopping at "Working"** | Ungoverned, unmeasured, unproven behavior is not complete. | Maturity Model (§5); Definition of Done (§6). |

---

## Section 11 — Future Evolution & Documentation Principle

This constitution is a living standard, but it evolves under discipline — not by drift.

**11.1 What may be added freely.** New **governance domains** (like Data Growth or Snapshot Generation) may be introduced at any time by following the Engineering Lifecycle (§4). New contracts, metrics, and enforcement gates are encouraged. Adding governance never requires amending this constitution.

**11.2 What requires formal amendment.** **All normative sections — the Objective (§1), Philosophy (§2), Decision Hierarchy (§3), Lifecycle (§4), Maturity Model (§5), Definition of Done (§6), Engineering Rules (§7), Decision Process (§8), Quality Gates (§9), and Anti-Patterns (§10)** — may only be changed by a **formal supersession**: a new versioned constitution (`engineering_constitution_v2.md`) that (a) states exactly which prior clause it changes, (b) gives the evidence/rationale, and (c) is recorded in `SYSTEM_SUMMARY.md` and `docs/institutional_memory/decision_registry.md`. Until then, v1 clauses remain binding.

**11.3 Consistency requirement.** New standards must remain **consistent** with existing principles unless they formally supersede them. A new rule that contradicts §1–§3 without an explicit amendment is invalid, not an update. This prevents governance fragmentation where each subsystem quietly invents its own philosophy.

**11.4 Precedence.** In a conflict: a **formal amendment** > this constitution > subsystem governance docs > individual PR conventions. Lower levels may add detail but may not contradict higher levels.

**11.5 Review cadence.** This constitution should be re-read at every Architecture Review Board pass and whenever a new governance domain is added, to confirm the new work is consistent with it. If the constitution is repeatedly inconvenient in the same way, that is a signal to consider a formal amendment — not to ignore it.

**11.6 Long-term documentation principle (this is the highest-level engineering document).**
- Treat this constitution as the **primary reference describing HOW CartFlow engineering works.** It sits above all other engineering documents.
- **Avoid creating additional foundational engineering documents** unless a genuinely new engineering domain emerges. If one does, it enters via §11.1 and is cross-referenced here — it does not become a second "how we engineer" document.
- All other documents — governance, audits, institutional memory, reviews, metrics, enforcement — **complement this constitution; they never replace or duplicate it.** They describe *specific domains or implementations* (the WHAT/WHERE); the constitution describes the *method* (the HOW).
- When in doubt about where a rule belongs: if it is *how CartFlow engineers*, it belongs here (by amendment); if it is *how a specific subsystem behaves*, it belongs in that subsystem's governance/doc, referencing this constitution.

---

## Success — what a future engineer now knows

Reading this document, a future engineer (or CTO) can understand, without tribal knowledge:

- **What CartFlow engineering is for** — keeping the platform understandable, governable, scalable, operable, and maintainable over years (§1).
- **How CartFlow is engineered** — truth first, governed, audited, measured, evidence-based (§2).
- **How conflicts are resolved** — the Decision Hierarchy (§3): correctness > truth ownership > operational safety > reliability > scalability > maintainability > performance > features > convenience.
- **How architectural decisions are made** — Problem → Evidence → Audit → Governance → Implementation → Measurement → Validation → Closure (§8), with independent review at high-risk junctions.
- **How new systems are introduced and matured** — via the nine-stage lifecycle (§4) and the seven-level maturity model (Levels 0–6, §5), whose goal is "Production Proven," not "Working."
- **How work is considered complete** — the Definition of Done (§6) and the quality gates (§9); "merged" is not "done," and "done" is evidence-backed.
- **What CartFlow refuses to do** — the anti-patterns (§10).
- **How the standard itself changes** — additively for new domains, by formal supersession for core clauses, and always as the single highest-level engineering reference (§11).

This document defines the engineering culture of CartFlow. It is the standard future development must implement.

---

## Appendix — Constitution-to-practice index

| Constitutional element | Living instance in the repo |
|---|---|
| Truth ownership + enforcement | `services/customer_lifecycle_states_v1.py`, `scripts/lifecycle_truth_enforcement_v1.py`, `docs/lifecycle_truth_enforcement_v1.md` |
| Governance domains | `docs/data_growth_governance_v1.md`, `docs/snapshot_generation_governance_v1.md` |
| Audit-before-refactor | `docs/dashboard_snapshot_generation_audit_v1.md`, `docs/cartflow_*_audit_v1*.md` |
| Composition not ownership | `docs/architecture_consolidation_v1.md`, `services/recovery_orchestration/*` |
| Independent review | `docs/cartflow_architecture_review_board_v2.md`, `_v3.md` |
| Metrics / measurement | `docs/operational_metrics_v1.md`, `scripts/_data_growth_measurement_v1_out/` |
| Maturity: Enforced | LT-C1 CI gate + `.github/workflows/lifecycle_truth_gate.yml` |
| Institutional memory | `docs/institutional_memory/{decision_registry,failure_registry,ownership_map,dependency_map,deferred_items_registry,future_maintainer_guide}.md` |
| Production validation | `docs/*_deploy_verification.md`, `docs/production_reality_validation_v1.md`, `docs/platform_readiness_review_v1.md` |
| SYSTEM_SUMMARY discipline | `docs/SYSTEM_SUMMARY.md` §10, `.cursor/rules/system-summary-always-update.mdc` |
