# CartFlow Merchant Experience Cohesion Program V1

**Status:** Ratified program plan — product experience only  
**Date (UTC):** 2026-07-05  
**Scope:** Unify **emotional continuity** across all merchant-facing surfaces — not ownership, routing, or features  
**Authority:** First product-quality program after Merchant Experience Migration Program V1 and Merchant Experience Review Board V1; subordinate to [`merchant_experience_foundation_v1.md`](merchant_experience_foundation_v1.md)  
**Audience:** Product, design, commercial, engineering (as consumers of the standard)  

**Explicitly out of scope:** Implementation, UI redesign, architecture, routing, pricing, AI, notifications build, code changes.

---

## Executive summary

Merchant Experience Migration Program V1 unified **knowledge ownership** — every certified surface consumes one governed pipeline.

Merchant Experience Cohesion Program V1 unifies **feeling** — every surface must read as the same operational companion continuing one conversation.

| Era | Program | Question answered |
|-----|---------|-------------------|
| Infrastructure | Merchant Knowledge Infrastructure | *Who owns truth and knowledge?* |
| Migration | Merchant Experience Migration V1 | *Do surfaces consume without re-deciding?* |
| **Cohesion** | **This program** | *Does the merchant feel one product?* |

Review Board V1 verdict (**B−**) identified the core cohesion fracture: **Home whispers; Carts shouts.** Migration succeeded architecturally; cohesion is the next merchant-facing obligation.

**Program complete** when a merchant moving Home → Cart Detail → Knowledge Layer → Setup → WhatsApp never experiences an emotional reset — and future surfaces (Weekly Brief, Notifications) are gated by this standard before ship.

---

## Section 1 — Mission

**Every merchant-facing surface should feel like one continuous conversation.**

The merchant should never feel they moved into another product. Every screen should continue the same story.

CartFlow is not a dashboard suite. CartFlow is **one calm operational companion** that:

1. Reports what it already did.
2. Surfaces only what needs the merchant.
3. Explains in one voice.
4. Invites drill-down without panic.

---

## Section 2 — Program principle

```
Merchant Experience is measured by emotional continuity.

Not by feature count.
Not by dashboard density.
```

| Wrong success signal | Right success signal |
|----------------------|----------------------|
| More cards, tabs, metrics | Same tone on every screen |
| Feature parity across nav items | Story continuity across nav items |
| Operational completeness | Merchant calm at every step |
| Engineering certification pass | Merchant never thinks *"this page feels different"* |

Cohesion does not replace Migration certification. A surface may be a **certified routing consumer** and still **fail cohesion** if it shouts while Home whispers.

---

## Section 3 — Cohesion principles (MEC-1…MEC-7)

Permanent. Every merchant surface, sub-surface, and future cadence **must implement** these alongside Experience Foundation ME-1…ME-8.

### MEC-1 — One voice

Every surface speaks the **same language**.

- Arabic merchant copy follows one vocabulary registry (recovery, sent, delivered, attention, achievement, understanding).
- No surface invents alternate labels for the same lifecycle moment.
- Internal product names («Knowledge Layer», «OIA», provider codes) never appear in merchant UI.

### MEC-2 — One story

The merchant should feel that **Home continues into Cart Detail**, Cart Detail into **Knowledge Layer**, Knowledge Layer into **Weekly Brief** (future), without changing tone.

- Section semantics stay stable: *what happened → what CartFlow did → what needs you → what it means*.
- Navigation is a **chapter change**, not a **genre change**.
- Summary on Home must not contradict detail on Carts.

### MEC-3 — One level of calm

No screen should become operationally noisy.

- No KPI walls on daily paths.
- No alert-red density without a matching critical decision.
- Empty and waiting states stay reassuring, never accusatory.

### MEC-4 — One attention model

Always, everywhere:

```
Achievements
    ↓
Attention
    ↓
Understanding
    ↓
Navigation
```

Never the opposite. Never metrics-first on a daily path. Never problems-before-wins on first paint.

### MEC-5 — One explanation style

Merchant wording must remain consistent across every surface.

- Cart Detail, Brief headlines, KL cards, proof footnotes, and setup next-steps use the **same explanation contract** (`merchant_explanation_v1` tone — plain Arabic, no diagnostics).
- Proof appears as *why we know*, not as engineering audit trail.
- Confidence and evidence labels use registry vocabulary only.

### MEC-6 — No emotional reset

Changing screens must never feel like entering another application.

- Visual rhythm may adapt to task (list vs story vs form) but **density, tone, and hierarchy** stay in family.
- Setup and WhatsApp are **chapters of the same book**, not separate admin consoles.
- Returning to Home after Carts should feel like *resuming the briefing*, not *leaving a tool*.

### MEC-7 — Complexity stays inside CartFlow

Clarity always belongs to the merchant.

- Provider paths, template approval, sandbox vs production — CartFlow absorbs complexity; merchant sees **next action + expected outcome**.
- Tables, filters, and timelines serve verification — they do not become the primary voice of the product.

---

## Section 4 — The Whisper Principle

> **Home whispers. Every surface should whisper too. CartFlow should never shout.**

| Whisper (required) | Shout (forbidden on daily path) |
|--------------------|----------------------------------|
| Short headlines | Paragraph stacks |
| Achievements first | Problem walls |
| One primary action | Button forests |
| Calm empty states | Manufactured urgency |
| Scoped attention (≤5 daily) | Unbounded lists as homepage |
| Story lists | KPI grids as greeting |

**Whisper does not mean hide truth.** It means truth arrives in **merchant-scannable form**. Drill-down may be denser — but the **first screenful** of every surface must pass the whisper test.

Review Board finding: **Carts list is the primary shout violation today.**

---

## Section 5 — Success metric

### Primary metric (qualitative)

A merchant should **never** think:

> *"This page feels different."*

A merchant should **always** feel:

> *"I'm still inside CartFlow."*

### Secondary signals (program tracking)

| Signal | Cohesion pass |
|--------|---------------|
| Terminology drift | Zero conflicting labels for same state across audited surfaces |
| Attention order | Achievements before attention on every daily entry surface |
| Cross-surface story | Home summary matches Cart Detail for same `knowledge_id` / cart |
| Emotional reset count | No surface rated **Shout** on first paint in cohesion audit |
| Setup → Home transition | First achievement on Home feels like continuation of setup story |

### Anti-success (automatic fail)

- Dashboard wall added to a daily surface «for convenience»
- New surface with its own priority vocabulary
- Technical wording visible to merchants on happy path
- Repeated full explanations of the same event on adjacent surfaces

---

## Section 6 — Anti-patterns

Cohesion violations — **forbidden** in new work; **scheduled for retirement** in existing surfaces:

| Anti-pattern | Why it breaks cohesion | Example today |
|--------------|------------------------|---------------|
| **Different terminology** | Merchant re-learns per screen | *تم استردادها* vs *تم إرسال رسالة* |
| **Different priorities** | Trust in Home undermined in Carts | Problem-first table sort vs achievement-first Home |
| **Different explanation styles** | Same cart feels like two products | Lifecycle block vs Brief headline tone drift |
| **Different emotional tone** | Emotional reset | Calm Home → alarmist empty cart tab |
| **Dashboard walls** | Shout | Month KPI grid acceptable; daily overview not |
| **Information dumping** | Reading load | Expand row shows proof + timeline + actions + labels at once |
| **Repeated explanations** | Attention waste | Same «why» on Home attention item and Cart Detail |
| **Technical wording** | Merchant anxiety | Provider, callback, sandbox exposed on happy path |
| **Operational panic** | Breaks MEC-3 | Red badges without critical decision class |

---

## Section 7 — Cohesion audit framework

Every surface review uses the same ten dimensions. Rate each **Whisper / Neutral / Shout** for first paint, plus **Pass / Partial / Fail** for continuity.

| Dimension | Question |
|-----------|----------|
| **Voice** | Same vocabulary as Home? |
| **Tone** | Same emotional register (calm companion)? |
| **Attention** | Achievements → attention → understanding order respected? |
| **Calmness** | First screenful scannable in ≤10 seconds? |
| **Navigation** | Feels like next chapter, not new app? |
| **Explanation** | Same style as `merchant_explanation_v1` / Brief? |
| **Visual rhythm** | Single-column story or justified density? |
| **Reading effort** | Minimal scroll to answer «what now»? |
| **Merchant confidence** | Platform-in-control feeling? |
| **Operational continuity** | Story matches adjacent surfaces? |

### Audit grades

| Grade | Meaning |
|-------|---------|
| **Cohesion Pass** | Whisper or Neutral; no emotional reset; continuity Pass |
| **Cohesion Partial** | One dimension Shout or continuity Partial — program work required |
| **Cohesion Fail** | Multiple Shout dimensions or continuity Fail — blocks program phase sign-off |

---

## Section 8 — Surface cohesion reviews (baseline)

Baseline audit from Merchant Experience Review Board V1 + product inspection. **Not a re-certification of routing** — emotional continuity only.

### 8.1 Merchant Home

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Pass** | Greeting, achievements, attention — companion Arabic |
| Tone | **Whisper** | Calm loading; reassuring empties |
| Attention | **Pass** | MEC-4 enforced in composition |
| Calmness | **Pass** | No KPI wall on overview |
| Navigation | **Pass** | Quick nav as epilogue |
| Explanation | **Pass** | Routed copy; truncated |
| Visual rhythm | **Pass** | Single column, max-width story |
| Reading effort | **Pass** | ~30s daily comprehension |
| Merchant confidence | **Pass** when achievements exist | Empty setup weakens |
| Operational continuity | **Anchor surface** | Reference for all other surfaces |

**Cohesion grade: Pass** — **reference whisper surface.**

---

### 8.2 Daily Brief

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Pass** | Same routing headlines as Home attention |
| Tone | **Whisper** | Hero + queue; calm empty |
| Attention | **Pass** | Achievements in Composer V2 path |
| Calmness | **Pass** | ≤5 items; truncated copy |
| Navigation | **Pass** | Embedded in Home — not separate island |
| Explanation | **Pass** | Action-first headlines |
| Visual rhythm | **Partial** | Hero + grid differs from Home story-list |
| Reading effort | **Pass** | |
| Merchant confidence | **Pass** | |
| Operational continuity | **Pass** with Home | Same feed |

**Cohesion grade: Pass (Partial visual rhythm)** — align card/grid shapes with Home over program phases.

---

### 8.3 Cart Detail (expanded row)

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Pass** | `merchant_explanation_v1` + projection |
| Tone | **Neutral** | Denser than Home; not alarmist |
| Attention | **Partial** | Explanation-led; proof block adds weight |
| Calmness | **Partial** | Expand reveals many blocks at once |
| Navigation | **Pass** | Expected drill-down from Home/Carts |
| Explanation | **Pass** | Unified explanation layer |
| Visual rhythm | **Partial** | Multi-block stack vs Home single story |
| Reading effort | **Partial** | Proof steps + lifecycle + action |
| Merchant confidence | **Pass** | Proof builds trust when calm |
| Operational continuity | **Pass** with Brief | Same knowledge_ids |

**Cohesion grade: Partial** — whisper the **first expanded screenful**; collapse proof by default.

---

### 8.4 Knowledge Layer

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Pass** | Registry evidence labels |
| Tone | **Neutral** | OIA cards slightly more «report» than Home |
| Attention | **Partial** | Understanding-only — correct layer but card shape differs |
| Calmness | **Pass** on Home slice | Dedicated KL path denser |
| Navigation | **Pass** | `#ma-home-understanding` anchor |
| Explanation | **Pass** | Routed projection |
| Visual rhythm | **Partial** | Cards vs Home story-list |
| Reading effort | **Pass** on capped slice | |
| Merchant confidence | **Pass** | Confidence + source per card |
| Operational continuity | **Pass** with Home | Home-routed slice |

**Cohesion grade: Partial** — unify **card → story-item** visual family on Home path.

---

### 8.5 Carts list (`#carts` workspace)

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Partial** | Lifecycle labels good; tab/filter vocabulary ops-heavy |
| Tone | **Shout** | Table, badges, filters, tabs — classic dashboard |
| Attention | **Fail** | Rows problem/status-first; not achievement-first |
| Calmness | **Fail** | High density first paint |
| Navigation | **Partial** | Context sidebar helps; still mode shift from Home |
| Explanation | **Pass** on expand | List itself not explanatory |
| Visual rhythm | **Fail** | Grid/table vs Home column |
| Reading effort | **Fail** for «what now» | Requires scan + filter literacy |
| Merchant confidence | **Partial** | Proof on expand helps; list anxiety remains |
| Operational continuity | **Fail** with Home | Review Board: «older cousin» |

**Cohesion grade: Fail** — **Priority 1 program target.** Whisper the list header and row summary; defer density to expand.

---

### 8.6 Store Setup (`#home-setup`)

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Partial** | Multiple modules — readiness %, activation, onboarding |
| Tone | **Neutral → Shout** | Progress OK; three narratives = noise |
| Attention | **Fail** | Setup-first, not achievement-first |
| Calmness | **Partial** | Each card calm; aggregate not calm |
| Navigation | **Partial** | Sub-page isolation from overview story |
| Explanation | **Partial** | Action-first cards exist; duplicated across modules |
| Visual rhythm | **Partial** | Stacked setup cards |
| Reading effort | **Fail** for «am I done?» | Three progress stories |
| Merchant confidence | **Partial** | Honest readiness; fragmented |
| Operational continuity | **Fail** with Home | Empty Home vs busy Setup — emotional reset |

**Cohesion grade: Fail** — **Priority 2.** One setup chapter until first achievement; then Home forever.

---

### 8.7 WhatsApp (`#whatsapp`, `#whatsapp-connect`)

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Partial** | Action-first V2 improved; path/journey vocabulary still heavy |
| Tone | **Neutral** | Commercial connect page better; settings still technical |
| Attention | **Partial** | Action-first card good; multiple sub-states |
| Calmness | **Partial** | Journey steps calm; provider dimension leaks |
| Navigation | **Partial** | Feels like settings app chapter |
| Explanation | **Partial** | Presentation V1/V2 strips diagnostics — good direction |
| Visual rhythm | **Partial** | Distinct from Home story |
| Reading effort | **Partial** | Merchant must understand sandbox vs production |
| Merchant confidence | **Partial** | «قيد التجهيز بواسطة CartFlow» OK; Meta/Twilio literacy required |
| Operational continuity | **Partial** with Setup | Same blockers, different framing |

**Cohesion grade: Partial** — **Priority 3.** WhatsApp as *companion task*, not *integration console*.

---

### 8.8 Recovery Timeline (cart row / movement line)

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Partial** | Movement events merchant-facing; some internal tokens sanitized |
| Tone | **Neutral** | Chronological — appropriate for verify path |
| Attention | **N/A** | Subordinate to Cart Detail — must not lead |
| Calmness | **Partial** | Timeline can feel busy on long recoveries |
| Navigation | **Pass** | Verify drill-down |
| Explanation | **Partial** | Steps align with proof surface |
| Visual rhythm | **Partial** | Vertical event list — distinct from Home |
| Reading effort | **Partial** | Power users only |
| Merchant confidence | **Pass** | Shows platform worked |
| Operational continuity | **Pass** with Cart Detail | Same recovery_key story |

**Cohesion grade: Partial** — timeline **collapsed by default**; whisper summary line first.

---

### 8.9 Completed Recoveries (`#completed` tab)

| Dimension | Baseline | Notes |
|-----------|----------|-------|
| Voice | **Partial** | Mixes wins, exhaustion, dismissals — semantic overload |
| Tone | **Neutral** | Not panic — but unclear |
| Attention | **Fail** | Archive + recovered + stopped — no achievement framing |
| Calmness | **Partial** | Tab calm; meaning not calm |
| Navigation | **Partial** | «مكتملة» ambiguous |
| Explanation | **Partial** | Row detail OK; tab purpose unclear |
| Visual rhythm | **Shout** when combined with carts table |
| Reading effort | **Fail** for «what succeeded» |
| Merchant confidence | **Partial** | Wins buried in mixed bucket |
| Operational continuity | **Fail** with Home achievements | Home celebrates wins; tab mixes outcomes |

**Cohesion grade: Fail** — **Priority 4.** Separate **wins** whisper from **closed** archive; align language with Home achievements.

---

### 8.10 Future Weekly Brief (greenfield gate)

| Dimension | Program requirement |
|-----------|---------------------|
| All dimensions | **Must Pass before ship** |
| Tone | **Whisper** — pattern reflection, not daily rehash |
| Attention | Weekly achievements → weekly attention → weekly understanding |
| Continuity | Same voice as Home; deeper time window only |
| Anti-pattern | Must not become «seven daily briefs stacked» |

**Cohesion grade: N/A — gated by MEC-1…MEC-7 sign-off checklist.**

---

### 8.11 Future Notifications (greenfield gate)

| Dimension | Program requirement |
|-----------|---------------------|
| All dimensions | **Must Pass before ship** |
| Tone | **Whisper** — one action or one awareness line |
| Attention | Interrupt-only; never duplicate Brief |
| Continuity | Same headline vocabulary as routed attention item |
| Anti-pattern | Must not shout on lock screen |

**Cohesion grade: N/A — gated by MEC-1…MEC-7 sign-off checklist.**

---

## Section 9 — Cohesion gap map (program phases)

Program phases are **product experience work** — presentation, copy, layout, navigation framing. Not routing. Not truth.

```
Phase 0 — Cohesion standard (this document) ─────────────────────┐
Phase 1 — Carts workspace whisper ─────────────────── Priority 1 ──┤
Phase 2 — Setup one-chapter story ───────────────── Priority 2 ──┤
Phase 3 — Cart Detail + KL visual family ─────────── Priority 3 ──┤
Phase 4 — WhatsApp companion chapter ───────────── Priority 4 ──┤
Phase 5 — Completed / wins separation ───────────── Priority 5 ──┤
Phase 6 — Future surface gate (Weekly, Notifications) ───────────┘
```

| Phase | Target surfaces | Cohesion outcome |
|-------|-----------------|------------------|
| **0** | All | MEC-1…MEC-7 ratified; audit framework baseline recorded |
| **1** | Carts list, filters, tabs | List **whispers** summary; shout deferred to expand |
| **2** | Store Setup | **One** setup narrative until first Home achievement |
| **3** | Cart Detail, KL, Daily Brief visual | Story-list / card family aligned with Home |
| **4** | WhatsApp | Action-first companion; no provider console tone |
| **5** | Completed tab | Wins aligned with Home achievements; archive separate semantics |
| **6** | Weekly Brief, Notifications | Greenfield — cohesion checklist before implementation |

**Phase 1 must not increase feature count.** Simplification and framing only.

---

## Section 10 — Phase certification checklist

A phase is **cohesion-certified** when:

| Check | Required |
|-------|----------|
| All target surfaces re-audited on ten dimensions | Yes |
| No surface **Shout** on first paint (daily path) | Yes |
| MEC-4 attention order on daily entry surfaces | Yes |
| Terminology drift resolved for touched surfaces | Yes |
| Cross-surface continuity **Pass** for same story | Yes |
| Migration routing certification **unchanged** | Yes — cohesion must not reintroduce surface selection |
| Review Board success metric spot-check | Merchant script: «Does this feel like the same CartFlow?» |

---

## Section 11 — Relationship to other standards

| Document | Relationship |
|----------|--------------|
| [`merchant_experience_foundation_v1.md`](merchant_experience_foundation_v1.md) | ME-* defines experience architecture; MEC-* defines emotional continuity |
| [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) | Migration **complete** — prerequisite for this program |
| [`merchant_experience_review_board_v1.md`](merchant_experience_review_board_v1.md) | Baseline grades and «Home whispers; Carts shouts» finding |
| [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md) | MEC-5 input — explanation style source |
| [`merchant_evidence_registry_foundation_v1.md`](merchant_evidence_registry_foundation_v1.md) | MEC-1 input — voice registry |
| Permanent Architectural Rule | Cohesion **never** creates a second knowledge pipeline |

---

## Section 12 — Program rules

### COH-1 — Cohesion never bypasses infrastructure

Whispering must not hide truth. Calm presentation consumes governed knowledge — it does not simplify by re-minting.

### COH-2 — Cohesion reduces; it does not add

Phases succeed by **removing** emotional reset and **aligning** surfaces — not by new merchant-facing features.

### COH-3 — Home is the tone reference

When two surfaces conflict, **Home tone wins** on daily paths unless the surface is explicitly a monthly/verify depth path.

### COH-4 — Future features gate on cohesion

Weekly Brief, Notifications, Mobile, Executive, AI — **no implementation** until Phase 6 checklist exists and pass criteria are assigned.

### COH-5 — Commercial surfaces whisper too

Plans comparison and subscription cards follow the same calm voice — no urgency marketing on daily dashboard.

---

## Section 13 — Program complete criteria

**Merchant Experience Cohesion Program V1 is complete when:**

| Criterion | Target |
|-----------|--------|
| Carts workspace | Cohesion **Pass** (not Fail) |
| Store Setup | Cohesion **Pass** |
| Cart Detail + KL + Brief | Cohesion **Pass** (visual family aligned) |
| WhatsApp | Cohesion **Pass** |
| Completed / wins | Cohesion **Pass** |
| Future surface gate | Checklist published and referenced |
| Review Board re-read | Overall product grade **≥ B** on Consistency dimension |

When complete:

- Merchant Experience Era enters **cohesion-certified** daily operations.
- Every subsequent feature proposal includes **MEC compliance line**.
- Architecture work remains subordinate to merchant feeling on product decisions.

---

## Section 14 — Merchant Experience Cohesion Declaration

**CartFlow merchant-facing work shall preserve one continuous conversation.**

Knowledge ownership is unified. **Emotional continuity is the next obligation.**

Surfaces that shout while Home whispers are **cohesion debt** — not legacy charm.

Future CartFlow capabilities must pass the whisper test:

> *I'm still inside CartFlow.*

---

## Related documents

| Document | Role |
|----------|------|
| [`merchant_experience_review_board_v1.md`](merchant_experience_review_board_v1.md) | Product baseline B− |
| [`merchant_home_experience_v1.md`](merchant_home_experience_v1.md) | Whisper reference surface |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Brief story source |
| [`cart_detail_migration_v1.md`](cart_detail_migration_v1.md) | Cart Detail consumer pattern |
| [`knowledge_layer_migration_v1.md`](knowledge_layer_migration_v1.md) | KL consumer pattern |
| [`cartflow_merchant_experience_audit_v1.md`](cartflow_merchant_experience_audit_v1.md) | First-visit friction history |

---

*End of Merchant Experience Cohesion Program V1.*
