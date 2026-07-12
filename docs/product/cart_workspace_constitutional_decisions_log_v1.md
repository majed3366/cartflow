# Cart Workspace — Constitutional Decisions Log V1

**Status:** Permanent governance memory — Cart Workspace Governance Pack  
**Date (UTC):** 2026-07-12  
**Authority:** Records *why* Cart Workspace constitutional law exists  
**Law (what):** [`cart_workspace_constitution_v2.md`](cart_workspace_constitution_v2.md)  
**Glossary:** [`cart_workspace_glossary_v1.md`](cart_workspace_glossary_v1.md)  
**Ratification:** [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md) — **Verdict A**  
**Validation:** [`cart_workspace_constitution_v2_validation.md`](cart_workspace_constitution_v2_validation.md)

---

## Document purpose

The Constitution defines the law.

This log preserves the **reasoning** behind the law so future contributors do not reopen settled product philosophy.

- Not a product specification  
- Not an implementation guide  
- Not an architecture document  

**Amendment rule:** Constitutional philosophy must not be silently rewritten. Future changes **add a new Constitutional Decision Record (CDR)**; they do not erase or overwrite prior CDRs.

---

## Index

| ID | Title |
|----|--------|
| [CDR-001](#cdr-001-merchant-time-is-the-primary-resource) | Merchant Time is the Primary Resource |
| [CDR-002](#cdr-002-automation-before-escalation) | Automation Before Escalation |
| [CDR-003](#cdr-003-decision-workspace) | Decision Workspace |
| [CDR-004](#cdr-004-decision-over-status) | Decision Over Status |
| [CDR-005](#cdr-005-priority-override) | Priority Override |
| [CDR-006](#cdr-006-execution-ownership-vs-decision-ownership) | Execution Ownership vs Decision Ownership |
| [CDR-007](#cdr-007-quiet-by-default) | Quiet by Default |
| [CDR-008](#cdr-008-one-card--one-decision) | One Card = One Decision |
| [CDR-009](#cdr-009-attention-budget) | Attention Budget |
| [CDR-010](#cdr-010-operational-history-separation) | Operational History Separation |
| [CDR-011](#cdr-011-wait-is-operational-strategy-not-decision) | Wait is Operational Strategy, not Decision |
| [CDR-012](#cdr-012-cart-workspace-constitutional-precedence) | Cart Workspace Constitutional Precedence |
| [CDR-013](#cdr-013-operational-history-outside-l2) | Operational History Outside L2 |
| [CDR-014](#cdr-014-dedicated-override-surface-allowed) | Dedicated Override Surface Allowed |

---

## CDR-001 — Merchant Time is the Primary Resource

### Question

What scarce resource should Cart Workspace optimize for — merchant attention, or platform activity visibility?

### Alternatives Considered

1. **Activity-first:** Maximize visible recovery events so merchants “see CartFlow working.”  
2. **Completeness-first:** Show every cart, signal, and status so nothing is hidden.  
3. **Attention-first:** Spend merchant time only when expected business value exceeds attention cost.

### Final Decision

Merchant attention is the primary operational resource. Platform activity is never the optimization target of Cart Workspace.

Constitutional anchors: Mission (§1), Merchant Time First (§6.1), Attention Budget (§6.9), Operational Success (§6.10).

### Why

Recovered revenue depends on scarce human judgment applied at the right moments. Showing more system activity increases cognitive load without necessarily improving decisions. If the merchant’s attention is treated as free, the product drifts into a monitor and destroys the trust that automation is handling the journey.

### Rejected Alternatives

- **Activity-first** rejected because it incentivizes noise and makes silence look like failure.  
- **Completeness-first** rejected because completeness is an engineering/ops concern, not a merchant Decision Workspace concern.

### Long-Term Consequences

Five years out, CartFlow can add channels, models, and automations without forcing merchants to watch them. New features must justify attention cost, not merely ship visibility. Prevents “dashboard gravity” from pulling the product into operational theater.

### Governance Impact

Inherited by: Merchant Decision & Ownership Map; Decision Admission Matrix; UX Blueprint; Operational Excellence metrics (success = decisions avoided / attention preserved); Admin Operations (must not dump ops noise into merchant Workspace).

---

## CDR-002 — Automation Before Escalation

### Question

Who owns recovery by default, and when may the merchant be interrupted?

### Alternatives Considered

1. **Merchant-supervised recovery:** Merchant reviews most carts; automation assists.  
2. **Shared continuous ownership:** Merchant and CartFlow jointly “watch” every cart.  
3. **Automation-default with exceptional escalation:** CartFlow executes unless Decision Admission proves human judgment is required.

### Final Decision

Automation owns the recovery journey by default (Execution Ownership). The merchant is never expected to supervise CartFlow. Escalation exists only when human judgment is expected to add measurable value (or Priority Override policy requires immediate Decision eligibility).

Constitutional anchors: Philosophy (§2), Automation Before Escalation (§6.2), Automation Confidence (§6.8), Human Judgment (§6.12), Decision Admission (§4).

### Why

If merchants must supervise, CartFlow is not a recovery platform — it is a task list with a bot. Trust requires that CartFlow supervise itself. Escalation without Admission converts every Signal into an interruption and bankrupts Attention Budget.

### Rejected Alternatives

- **Merchant-supervised** rejected: contradicts self-supervising automation and scales with cart volume, not with judgment value.  
- **Shared continuous ownership** rejected: creates dual Decision Ownership and permanent ambiguity about who must act.

### Long-Term Consequences

Admission becomes the hard gate for all future AI, messaging, and playbooks. “Helpful” interruptions without Admission are unconstitutional. Enables high automation rates while preserving a clean human path for exceptions.

### Governance Impact

Inherited by: Decision Admission Matrix; Merchant Decision Engine (may score, may not bypass Admission); Ownership Map; UX Blueprint (no “always visible queue”); Knowledge Layer (claims ≠ auto-escalation).

---

## CDR-003 — Decision Workspace

### Question

What product identity does the merchant carts surface have?

### Alternatives Considered

1. CRM for customer relationships  
2. Inbox for messages  
3. Dashboard for KPIs  
4. Reporting page for analytics  
5. Generic cart list / database browser  
6. Notification center  
7. **Decision Workspace:** only admitted human decisions

### Final Decision

Cart Workspace is a Decision Workspace. It exists only to present human Decisions that answer: **ما يحتاج قرارك؟**

It is not CRM, Inbox, Dashboard, Reporting page, Cart list, or Notification center.

Constitutional anchors: Definition (§1.2–1.3), Core mission (§3), Boundaries (§9).

### Why

Identity determines every future feature fight. If the surface is allowed to be “a bit of everything,” it becomes none of them well and loses the only scarce resource it was built to protect. A single mission question forces ruthless exclusion of non-decision content.

### Rejected Alternatives

Each rejected identity optimizes a different stakeholder goal (support, analytics, ops, engineering debug) and would reintroduce status/signal organization. Mixing them guarantees multi-purpose cards and Attention Budget failure.

### Long-Term Consequences

Feature proposals that “just add a panel” can be rejected by identity alone. Sibling surfaces (Admin Ops, Knowledge, History) must stay separate rather than merging into Workspace for convenience.

### Governance Impact

Inherited by: UX Blueprint (layout = Decisions + calm empty state); Admin Operations (separate console); Knowledge Layer (not a Workspace browser); Observation Layer (upstream only); Ownership Map (only admitted Decisions appear).

---

## CDR-004 — Decision Over Status

### Question

Should the merchant-facing organization of Cart Workspace be built from operational statuses/signals or from Decisions?

### Alternatives Considered

1. **Status taxonomy:** Buckets such as Message Sent, Phone Missing, Customer Replied, Waiting.  
2. **Hybrid:** Status columns plus decision CTAs.  
3. **Decision taxonomy:** Organize solely by admitted Decisions; statuses may appear only as explanation inside a Decision.

### Final Decision

Statuses and signals serve the platform. Workspace organization is built around Decisions. Examples such as Message Sent, Phone Missing, Customer Replied, and Waiting are **operational signals/statuses**, not Workspace categories.

Constitutional anchors: Definitions (§4), Decision Over Status (§6.5), Explain Before Asking (§6.6).

### Why

Status buckets train merchants to supervise pipelines. Decision buckets train merchants to judge exceptions. Hybrid designs inevitably elevate status into the primary IA and smuggle monitoring back in. Explanation still needs status language — but as context under a Decision, not as the map of the page.

### Rejected Alternatives

- **Status taxonomy** rejected: violates Quiet, Attention Budget, and Decision Workspace identity.  
- **Hybrid** rejected: two organizing principles compete; the louder (status counts) wins over time.

### Long-Term Consequences

Prevents “phone missing board,” “waiting queue,” and similar CRM-shaped views from becoming the default. Future signal types can be added in L3 without new L2 categories.

### Governance Impact

Inherited by: Decision Admission Matrix (Admission reasons ≠ status tabs); UX Blueprint (no status-primary nav); Ownership Map; Merchant Decision Governance vocabulary; Observation/Evidence pipelines (feed proof, not Workspace IA).

---

## CDR-005 — Priority Override

### Question

Is VIP “higher priority in the same decision queue,” or a different operational mode?

### Alternatives Considered

1. **Queue priority:** VIP sorts above normal cards in one list.  
2. **VIP = stop automation entirely and hand all ownership to merchant.**  
3. **Priority Override (L0):** Different policy — immediate notification; immediate Decision Ownership on Override Admission; CartFlow keeps Execution Ownership; never waits behind normal Decision queues.

### Final Decision

VIP is Priority Override — a constitutional operational layer (L0), not higher sort order. On VIP detection: immediate merchant notification; customer-service notification if configured; Merchant becomes Decision Owner immediately upon Override Admission; CartFlow remains Execution Owner and continues observation / policy-constrained execution. Override carts never wait behind normal Decision queues.

Constitutional anchors: Priority Override (§6.3), Layers (§5), Ownership (§7); Validation Scenario D; Q1/Q5 resolutions in validation pack.

### Why

“Higher priority in the same queue” still treats VIP as the same kind of work with a better rank — which collapses under load and fights Quiet by Default. Stopping all CartFlow execution on VIP abandons the journey and creates unsupervised manual chaos. Override mode preserves automation’s hands on execution while guaranteeing human judgment is invited immediately under a separate policy path (L0 → L1 override Admission → L2).

### Rejected Alternatives

- **Queue priority** rejected: same ontology, wrong urgency model; still blocked by normal Admission backlog.  
- **Full ownership handoff** rejected: conflates Execution and Decision Ownership; loses CartFlow observation and deterministic return paths.

### Long-Term Consequences

Future “override” policies (fraud, legal, strategic accounts) can reuse L0 without inventing new product identities. Normal Quiet remains intact for non-override contexts.

### Governance Impact

Inherited by: Decision Admission Matrix (override path); Ownership Map (immediate Decision transfer, Execution stays CartFlow); UX Blueprint (dedicated Override surface allowed — CDR-014); notification policy; Merchant Decision Engine ranking (cannot bury override behind normal scores).

---

## CDR-006 — Execution Ownership vs Decision Ownership

### Question

Can “one owner per cart” survive VIP and exception flows where CartFlow must keep working while the merchant decides?

### Alternatives Considered

1. **Single operational owner always:** One party owns everything; handoff is total.  
2. **Ambiguous shared ownership:** Both “responsible” without axes.  
3. **Dual-axis ownership:** Separate Execution Ownership from Decision Ownership; never dual on the same axis.

### Final Decision

Ownership is split:

- **Execution Ownership** — who runs recovery work now (default CartFlow).  
- **Decision Ownership** — who owes the next business judgment (CartFlow until Admission; Merchant after Admission / Override Admission).

Execution may continue while Decision Ownership transfers. This resolves the paradox of “CartFlow observes” and “human intervention starts immediately.”

Constitutional anchors: Definitions (§4), Dual ownership (§6.4), Transitions (§7); Constitution V2 change C1.

### Why

A single-owner model cannot describe override and exception reality without lying (either automation stops incorrectly, or the merchant is falsely told they own execution). Shared ownership without axes creates dual responsibility and missed actions. Dual-axis ownership makes transitions deterministic and explainable.

### Rejected Alternatives

- **Single owner** rejected: forces false total handoffs; breaks VIP architecture.  
- **Ambiguous shared** rejected: fails “never both / never neither” on a single responsibility axis.

### Long-Term Consequences

All future handoff designs must declare which axis moves. Prevents “merchant owns the cart” slogans from accidentally disabling automation. Enables clear audit of who was supposed to decide vs who was supposed to run.

### Governance Impact

Inherited by: Merchant Decision & Ownership Map (mandatory dual columns); Decision Admission Matrix (gates Decision axis only); UX Blueprint (merchant actions = Decision axis); Admin Operations / OE (execution telemetry ≠ Decision cards).

---

## CDR-007 — Quiet by Default

### Question

What is the correct Workspace state when nothing requires human judgment?

### Alternatives Considered

1. **Always populated:** Show background activity so the page never looks empty.  
2. **Soft noise:** Tips, counts, and “recent events” when idle.  
3. **Quiet success:** Calm empty state affirming automation continues.

### Final Decision

Silence is preferred to operational noise. When Decision Admission admits nothing, Workspace is calm. Canonical meaning:

> لا يوجد ما يحتاج قرارك الآن. CartFlow يتابع عمليات الاسترداد تلقائيًا.

“Nothing requires your decision” is a **successful** Workspace state.

Constitutional anchors: Quiet by Default (§6.11); Validation Scenarios A, B, E, F.

### Why

Empty-looking monitors get filled with junk to reassure stakeholders. That junk becomes the product. Declaring calm as success aligns incentives with Automation Before Escalation and Attention Budget. Merchants learn that interruption is meaningful.

### Rejected Alternatives

- **Always populated** rejected: manufactures supervision.  
- **Soft noise** rejected: still spends Attention Budget without Decision value.

### Long-Term Consequences

Protects against “engagement” metrics that punish healthy automation. Future growth in L3 activity does not obligate L2 chrome.

### Governance Impact

Inherited by: UX Blueprint (empty state is first-class); OE / success metrics; Decision Admission Matrix (reject = quiet, not “show something anyway”); notification systems (must not invent Workspace noise).

---

## CDR-008 — One Card = One Decision

### Question

May a Workspace card combine multiple purposes, explanations, or primary actions?

### Alternatives Considered

1. **Multi-purpose cards:** Contact + archive + timeline + upsell on one tile.  
2. **Primary + many equal secondaries:** Competing CTAs.  
3. **One card = one Decision:** One purpose, one explanation contract, one primary Action.

### Final Decision

Every card represents exactly one business Decision: one purpose, one explanation, one primary Action. Multi-purpose cards are prohibited.

Constitutional anchors: One Card = One Decision (§6.7); Explain Before Asking (§6.6).

### Why

Multiple primaries recreate status boards and force the merchant to design the workflow themselves. One Decision keeps Admission honest: if you need two judgments, you need two Admissions (or one clearer Decision). Cognitive load drops; decision quality rises.

### Rejected Alternatives

- **Multi-purpose** rejected: violates Attention Budget and Decision identity.  
- **Many equal CTAs** rejected: smuggles multi-purpose through the footer.

### Long-Term Consequences

UX and API contracts stay simple. “Add another button” requires proving it is not a second Decision in disguise. Sibling cart-page primary-decision rules yield to Pack precedence (CDR-012).

### Governance Impact

Inherited by: UX Blueprint; Decision Admission Matrix (one admitted Decision → one card); Ownership Map; action registries (secondary controls cannot compete with primary).

---

## CDR-009 — Attention Budget

### Question

Is more information on Cart Workspace always better?

### Alternatives Considered

1. **Information abundance:** More context always improves decisions.  
2. **Unlimited cards:** If Admission is loose, show everything “just in case.”  
3. **Attention Budget:** Every card and every field must earn its place; reducing unnecessary merchant decisions is itself a product KPI.

### Final Decision

Information abundance reduces operational quality on this surface. Every card must earn its place by decision value. Reducing merchant decisions avoided / attention preserved is a first-class success measure — not card count or event count.

Constitutional anchors: Attention Budget (§6.9), Operational Success (§6.10), Merchant Time First (§6.1).

### Why

Beyond a small number of concurrent judgments, merchants slow down, mis-prioritize, or ignore the surface. Extra fields that do not change the Decision are pure cost. Making “decisions avoided” a KPI aligns engineering with Automation Before Escalation.

### Rejected Alternatives

- **Abundance** rejected: confuses evidence completeness (upstream) with Workspace density.  
- **Unlimited cards** rejected: Admission without budget is not Admission.

### Long-Term Consequences

Prevents KPI theater (more widgets = more value). Future AI summaries must compress toward the Decision, not expand toward encyclopedias on the card.

### Governance Impact

Inherited by: OE / product KPIs; Decision Admission Matrix (capacity and reject rules); UX Blueprint (field-level earning); Merchant Decision Engine (ranking under budget, not maximizing volume); Knowledge Layer (detail lives elsewhere).

---

## CDR-010 — Operational History Separation

### Question

Where does operational history, timelines, and completed recovery truth belong relative to Cart Workspace?

### Alternatives Considered

1. **History inside Workspace:** Active decisions and archives share one primary surface.  
2. **Workspace as timeline viewer:** Chronology is the product.  
3. **Separation:** Active Decisions only in Workspace (L2); history/completed outcomes in Operational History / Knowledge / L4 surfaces — not as active Decision noise.

### Final Decision

History belongs to Operational History / Knowledge (and L4 completed-outcome) surfaces, not to the active Cart Workspace Decision surface. Workspace focuses only on active admitted Decisions (plus calm empty state). Automatic completion must not enter Workspace as a Decision (Validation Scenario E).

Constitutional anchors: Layers L2 vs L4 (§5), Boundaries (§9.7 timeline-as-identity), Validation Scenario E; Q4 partially resolved.

### Why

Mixing history with active Decisions turns the page into a CRM/timeline and dilutes ما يحتاج قرارك؟ Completed success is not a request for judgment. Knowledge and history systems already exist to hold depth; Workspace must not absorb them for convenience.

### Rejected Alternatives

- **History inside Workspace** rejected: destroys Quiet and One Card = One Decision under volume.  
- **Timeline-as-product** rejected: explicitly banned identity (§9).

### Long-Term Consequences

Clear split lets History/Knowledge grow rich without taxing Attention Budget. Full archive/reopen scope closed at ratification (CDR-013 / Ratification Q4).

### Governance Impact

Inherited by: Knowledge Layer; Observation / proof history; UX Blueprint (no history-primary IA); Admin Operations; L4 completed-outcome design; Ownership Map (exit L2 on completion).

---

## CDR-011 — Wait is Operational Strategy, not Decision

### Question

Is Wait an admitted merchant Decision on Cart Workspace, or CartFlow operational strategy?

### Alternatives Considered

1. **Wait as default Decision:** Merchant always chooses Wait vs Act.  
2. **Wait as Workspace category:** Organize the surface around Waiting carts.  
3. **Wait as operational strategy:** CartFlow may wait without interrupting; Waiting is Status, not category; merchant Wait Action only if separately admitted.

### Final Decision

Wait is **operational strategy / Status**, not a Workspace organizing Decision. CartFlow may wait as Decision Owner without merchant interruption. A merchant-facing Wait Action requires separate Decision Admission and Human Gain. Sibling “Wait as primary” language yields under Pack precedence (CDR-012).

Constitutional anchors: §6.5; Glossary Status/Decision; Ratification Q2.

### Why

Treating Wait as a category recreates status IA and bankrupts Quiet by Default. Automation must be allowed to wait silently when that is the best recovery strategy.

### Rejected Alternatives

- Default Wait Decision and Waiting category rejected as Attention Budget and Decision Over Status violations.

### Long-Term Consequences

Admission Matrix must not invent a permanent “Wait queue.” Ownership Map treats wait-as-CartFlow as Decision Owner = CartFlow.

### Governance Impact

Inherited by: Ownership Map; Admission Matrix; UX Blueprint; Cart Page Product Constitution subordination on this point.

---

## CDR-012 — Cart Workspace Constitutional Precedence

### Question

Which law wins when Cart Workspace Constitution V2 conflicts with Cart Page Product Constitution?

### Alternatives Considered

1. **Cart Page wins** (five-question model).  
2. **Coequal unresolved.**  
3. **Cart Workspace Pack wins** on Workspace identity and Decision-surface conflicts; truth/evidence/engineering peers unchanged.

### Final Decision

**Cart Workspace Governance Pack prevails** on Workspace identity, mission question, Decision vs Status, Quiet, Attention Budget, and Override semantics. Truth-minting and engineering peers remain peers.

Constitutional anchors: §0, §1.3, §9; Ratification Q3.

### Why

Two equal product laws on one surface guarantee permanent ambiguity. Singular identity requires one Workspace constitution.

### Rejected Alternatives

- Cart Page supremacy and unresolved coequality rejected.

### Long-Term Consequences

Cart-page docs amend to subordinate wording or defer to Pack on conflicts. No dual mission for the same surface.

### Governance Impact

Inherited by all downstream Workspace specs; Cart Page Product Constitution maintainers.

---

## CDR-013 — Operational History Outside L2

### Question

Are Completed / Archive / Purchased / history inside Decision Workspace scope?

### Alternatives Considered

1. **Inside L2** under One Card rules.  
2. **Ambiguous hybrid.**  
3. **Outside L2:** L4 / history / Knowledge surfaces; Completed Outcomes are not Decisions.

### Final Decision

Operational History is **outside L2**. Archive/reopen/purchased may be adjacent surfaces; they must not reintroduce status taxonomy into Workspace or treat completions as Decisions.

Constitutional anchors: §5 L4; CDR-010; Glossary Completed Outcome; Ratification Q4; Scenario E.

### Why

History inside Workspace destroys Quiet and Attention Budget. Completions are outcomes, not judgments.

### Rejected Alternatives

- L2 history and hybrid ambiguity rejected.

### Long-Term Consequences

Ownership Map exits L2 on completion. History products grow without Workspace identity drift.

### Governance Impact

Inherited by: L4 design; Knowledge; UX (no history-primary Workspace); archive/reopen specs.

---

## CDR-014 — Dedicated Override Surface Allowed

### Question

Must Override Decisions share one list with normal Decisions, or may they use a dedicated VIP surface?

### Alternatives Considered

1. **Same list only.**  
2. **Separate product** (VIP app).  
3. **Dedicated Override surface allowed** while remaining Cart Workspace under the Pack.

### Final Decision

A **dedicated VIP / Override surface is allowed** and remains Cart Workspace (same mission, Glossary, Admission, One Card). Same-list isolation is also allowed. Separate product identity is forbidden. Override must never wait behind normal queues.

Constitutional anchors: §5, §6.3, §1.3; Glossary Priority Override / Workspace; Ratification Q6.

### Why

Isolation can protect Attention Budget and Override urgency without creating a second product. Forbidding dedicated surface would over-constrain UX without constitutional gain.

### Rejected Alternatives

- Separate VIP product rejected (identity breach). Same-list-only mandate rejected as unnecessary.

### Long-Term Consequences

UX Blueprint may choose dedicated or same-list isolation; Architecture must preserve Override Admission path and dual ownership.

### Governance Impact

Inherited by: UX Blueprint; Ownership Map; Admission Matrix (override path); notification design.

---

## Maintenance

| Rule | Requirement |
|------|-------------|
| New philosophy | Add **CDR-NNN**; do not edit prior CDR “Final Decision” silently |
| Clarifications | Prefer additive notes under a new CDR that references prior IDs |
| Conflicts with Constitution text | Amend Constitution explicitly; log reasoning in a new CDR |
| Ratification | **Verdict A** — [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md). Philosophy reopen requires amendment process therein. |

---

**End of Constitutional Decisions Log V1.**
