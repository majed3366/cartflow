# Cart Workspace Operational Behavior Blueprint V1

**Status:** Behavioral architecture — last Product document before Architecture Review  
**Date (UTC):** 2026-07-12  
**Nature:** Living operational behavior of Cart Workspace when operational truth changes.  
**Not:** visual design, pixels, CSS, animation specs, React/components, APIs, or database schemas.

**Governance parents (every behavioral rule must trace here):**  
- [`cart_workspace_constitution_v2.md`](cart_workspace_constitution_v2.md)  
- [`merchant_decision_and_ownership_map_v1.md`](merchant_decision_and_ownership_map_v1.md)  
- [`decision_admission_matrix_v1.md`](decision_admission_matrix_v1.md)  
- [`cart_workspace_ux_blueprint_v1.md`](cart_workspace_ux_blueprint_v1.md)  
- [`cart_workspace_glossary_v1.md`](cart_workspace_glossary_v1.md)  
- [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md)  

**Derivation law:** No behavior may be invented independently. If a transition, appearance, disappearance, interruption, or calm state cannot cite Constitution + Ownership + Admission + UX Blueprint, it is forbidden.

**Open policy detail (do not invent):** Ownership Map OQ-1 (exact T4 expiry/return/supersede events), OQ-2 (T6 manual-handoff minimum content), OQ-4 (T12 reopen evidence classes). This blueprint binds the *workspace response* to those gates once policy defines them; it does not invent the timers or evidence classes.

---

## Deliverables index

| Deliverable | Location in this document |
|-------------|---------------------------|
| Workspace Lifecycle Model | Part 1 |
| Decision Card Behavior Specification | Part 2 |
| Zone Behavior Specification | Part 3 |
| Attention / Ownership / Live / Motion / Confidence / Failure / Calm | Parts 4–10 |
| Behavioral Invariants | Part 11 |
| Operational Behavior Validation Report | Part 12 |

---

# Part 1 — Workspace Lifecycle Model

The workspace lifecycle is **deterministic**. Same ownership + admission posture → same workspace phase. Refresh, poll, and duplicate observation never advance the lifecycle by themselves (Ownership OS-3, OST-9; Admission AS-2, AI-16).

## 1.1 Canonical lifecycle

```text
Workspace Opens
    ↓
Reconcile operational truth (Ownership state × Admission outcomes)
    ↓
Evaluate admitted Decisions (normal T1 / Override T2 only)
    ↓
Determine attention order (Zone A → B → C → D → E)
    ↓
Display operational truth (Decisions + peripheral confidence only)
    ↓
Merchant acts (exactly one primary Action per Decision)  — or —
Merchant leaves Decision open (Decision Owner remains Merchant until T3/T4/T5)
    ↓
Ownership transition fires (T3 / T4 / T5 / T6 / T7 / T9 / T10 / T11 / T12 as applicable)
    ↓
Workspace updates (card resolve / promote / demote / calm — never teleport)
    ↓
Returns to calm when no admitted Decisions remain
```

## 1.2 Lifecycle phases

| Phase ID | Name | Entry condition | Exit condition | Merchant experience |
|----------|------|-----------------|----------------|---------------------|
| **WL-0** | Open / Reconcile | Merchant enters Workspace | Reconciliation complete | Workspace reflects current S1–S9 posture; no ownership change from open alone |
| **WL-1** | Quiet Confidence | No Zone A, no Zone B (Decision Owner CartFlow for all in-scope journeys) | T1 or T2 Admit appears | Canonical Quiet (§6.11); Zones C/D peripheral |
| **WL-2** | Override Attention | ≥1 Override-admitted Decision (S4 / Gate F / R07) | All Override Decisions closed (T3/T4/T5) and no remaining Zone A | Immediate attention on Zone A; Zone B may exist but never above A |
| **WL-3** | Decision Attention | ≥1 normally admitted Decision (S2 / T1) and Zone A empty | All Zone B Decisions closed or Override appears → WL-2 | Primary attention on Zone B |
| **WL-4** | Merchant Judgment | Merchant is reading/acting on an admitted Decision | Action completes (T3) or policy close (T4/T5) or inactivity continues | Explain Before Asking context + one Action; no re-Admit nag (R14) |
| **WL-5** | Ownership Return | T3 / T4 / T5 (or T7 if scoped exec closes) | Card resolved; posture → S1 or terminal | Visible return: CartFlow resumed; not “work vanished” |
| **WL-6** | Calm Recovery | No remaining admitted Decisions | New Admit → WL-2/WL-3; or leave Workspace | Quiet confidence restored |
| **WL-7** | Terminal Outcome | Journey → S7/S8 (T10/T11) | Governed reopen T12 only | Compact Zone D update; never new Decision without fresh Admission |

## 1.3 Determinism rules

| Rule | Statement | Governance |
|------|-----------|------------|
| **LC-1** | Opening Workspace never transfers ownership | Ownership non-transition: views ≠ transfer |
| **LC-2** | Lifecycle advances only on Ownership Transition Matrix events (T1–T12) or compiled Admission outcomes | Ownership Part 4; Admission binary |
| **LC-3** | Duplicate Signal / refresh / poll never advances phase | OS-3, AS-2, AI-16 |
| **LC-4** | From Quiet, only Admit (T1/T2) enters Decision phases | I4, I5, AE-2 |
| **LC-5** | After Action, path is Return → Calm (or Terminal), never silent delete | T3 + UX flow Part 8 |
| **LC-6** | Override detection alone (T8 → S3) does not show a Decision Card until Override Admission (T2) | I8, R07 vs detection |

---

# Part 2 — Decision Card Behavior Specification

Applies to Zone A and Zone B. One card = one Decision (Constitution §6.7; UX-1).

## 2.1 Identity

| Concept | Rule |
|---------|------|
| **Decision identity** | Stable identity for one admitted Decision (bound to Admission id / Evidence fingerprint class per AS-1) |
| **Card identity** | Exactly one visible card per Decision identity while Decision Owner = Merchant |
| **Forbidden** | Second card for same Evidence fingerprint; second Admit while Decision open (AI-10, R14, AS-1) |

## 2.2 Creation

| When | Behavior |
|------|----------|
| Admission **Admit** via T1 | Create **one** Zone B card; Decision Ownership → Merchant (S2) |
| Admission **Admit** via T2 | Create **one** Zone A card; Decision Ownership → Merchant (S4); never queue behind Zone B |
| Do Not Admit | **No card** |
| Notification delivered / merchant opens Workspace | **No creation** (ownership already set at Admission) |

**Required at creation (Explain Before Asking):** Why appeared → What CartFlow did → Why automation stopped → Expected Action → Expected outcome after Action (Constitution §6.6; UX Part 4).

**Governance:** AI-5 (one Action); AA-3 audit fields; AE-1 (Admit is costly).

## 2.3 Update

| Trigger | Allowed update | Forbidden update |
|---------|----------------|------------------|
| New observation while Decision open | Update **explanation material** only (AS-3) | Second Admit; second card; Action change that creates a second Decision |
| Same Evidence fingerprint re-observed | No visible change required; must not flicker | Re-create card; “new alert” |
| Ownership unchanged | Card remains in same zone | Teleport Zone B ↔ A without T8/T2 or T9 policy |

**Stability:** Cards update in place. They do not disappear and reappear for the same Decision identity.

## 2.4 Escalation

**Escalation** (Glossary) = Decision Ownership CartFlow → Merchant after Admission.

| Path | Workspace behavior |
|------|--------------------|
| Normal Escalation (T1) | Card appears in Zone B; attention may move to that Decision if no Zone A |
| Override Escalation (T2) | Card appears in Zone A; may interrupt Zone B attention (Part 4) |
| Non-escalation events | Customer reply, provider failure under retry, Status tick, Knowledge claim → **no Escalation**, no card (R04, R12, R16, R18) |

Escalation is exceptional; Automation is default (Constitution §6.2).

## 2.5 Ownership transfer (card-visible)

| Transition | Card behavior |
|------------|---------------|
| **T1 / T2** (CF → Merchant Decision) | Card **appears** (creation) |
| **T3** (resolved) | Card **resolves** then leaves active Decision surface; calm cue that CartFlow resumed |
| **T4** (expired / returned / superseded) | Card **closes** with governed reason (policy per OQ-1 — not invented here); no mysterious vanish |
| **T5** (leave L2) | Card leaves Decision surface; journey may appear compactly in Zone D if Completed Outcome |
| **T6** (Exec → Merchant) | Does not create a Decision by itself; if Decision already open, card may reflect scoped manual Execution posture without becoming a second Decision (OQ-2 bounds content) |
| **T7** (Exec → CartFlow) | Manual scope closed; Execution reassurance returns to CartFlow without inventing a new Decision |
| **T8** (L0 Active) | Mode only — **no card** until T2 |
| **T9** (L0 clear) | If Override Decision still open under policy, may demote posture Zone A→B only when governance says Override Decision becomes normal Decision; otherwise close per T4 — **no oscillation** (OS-4) |
| **T10 / T11** | No Decision Card; Zone D compact / history outside L2 |
| **T12** | Reopen → S1 then full Admission pipeline; card only if fresh Admit |

## 2.6 Merchant action

| Rule | Behavior |
|------|----------|
| Primary Action | Exactly one; executes the admitted Decision |
| On Action complete | Fire **T3**; Decision Ownership → CartFlow |
| Secondary Action | Only if constitutionally justified and non-competing (UX-13); never a second Decision |
| Inactivity | Decision Owner stays Merchant; **no re-Admit**, no nag card (R14, OST-1) |

## 2.7 Resolution

Resolution is **visible and governed**:

1. Outcome of Action (or T4/T5 policy close) is acknowledged in workspace behavior.  
2. Decision Ownership returns to CartFlow (T3/T4/T5).  
3. Card leaves Zone A/B through a defined motion class (Part 7: Resolve → Fade / Collapse — behavioral, not animation).  
4. If no other admitted Decisions remain → Quiet (WL-6).

## 2.8 Disappearance

A card may leave the active Decision surface **only** when:

| Cause | Gate |
|-------|------|
| Merchant completed Action | T3 |
| Policy expiry / return / supersede | T4 (OQ-1) |
| Journey left L2 (complete/archive exit) | T5 / T10 / T11 |
| Supersede by conflicting governed Proof under T4 | T4 — still explainable |

**Forbidden disappearances:** refresh; poll; duplicate webhook; temporary sync lag (show uncertainty posture instead — Part 9); “sorted away”; zone compaction that deletes Decisions.

**Invariant:** Cards never disappear mysteriously (Part 11 BI-2).

## 2.9 Reappearance policy

| Condition | Behavior |
|-----------|----------|
| Same Evidence fingerprint after close | **No reappearance** (AS-1, AS-4, AI-16) |
| New Evidence after return to CartFlow | Full Admission pipeline; **new** Decision identity if Admit=Yes |
| Completed (S7) / Archived (S8) | No Decision reappearance without **T12** + full pipeline (OS-5, AI-8, R20) |
| Merchant reopen of history browse | Not Decision Ownership (I10); no card from browse alone (R19) |

**Invariant:** Cards never duplicate; never oscillate (BI-3, BI-4).

---

# Part 3 — Zone Behavior Specification

Zones appear from governance state, not navigation (UX Part 3).

## 3.1 Zone A — Priority Override

| Question | Behavior |
|----------|----------|
| **When does it appear?** | L0 Active **and** ≥1 Override-admitted Decision (T2 / R07 / S4). Dedicated Override surface allowed (Ratification Q6) but remains Cart Workspace identity. |
| **When does it disappear?** | No Override-admitted Decisions remain (all closed via T3/T4/T5) **and** either L0 cleared (T9) or no Override Decisions pending. Zone A absent when L0 inactive (UX Zone A). |
| **What may interrupt it?** | Nothing in Workspace outranks Zone A. New Override-admitted Decision may join Zone A (see coexistence). Non-Override events must not bury or delay Zone A. |
| **Can multiple VIP / Override cases coexist?** | **Yes.** Multiple Override-admitted Decisions may coexist as separate cards (One Card = One Decision). Duplicate VIP detect while already Active does **not** create another Admit (R08, OS-4, RJ-OVERRIDE-DUP). |
| **How are they ordered?** | All Zone A cards remain above all Zone B cards (I6, UX-9). Within Zone A, order is **stable** (no oscillation on refresh). Relative order among Override cards may follow value-justified stable ranking only if compiled from governance — this blueprint does **not** invent a scorer; until one exists, use stable admission-time order (first admitted remains first unless a governed promote rule fires). |
| **What must never happen?** | Override Decision waiting behind Zone B; VIP as “higher sort in same list” without Override isolation; card from T8 alone. |

## 3.2 Zone B — Needs Your Decision

| Concern | Behavior |
|---------|----------|
| **Admission behavior** | Card enters only on Admit=Yes normal path (T1). Do Not Admit → invisible. Fail closed (AI-15). |
| **Sorting behavior** | Strictly below Zone A. Within Zone B: **stable order** (no reshuffle on poll/refresh). Optional value-justified stable ranking must not thrash (OS-1, confidence Part 8). Default: stable by admission time until a governed ranker is approved. |
| **Replacement behavior** | New Admit adds a new card; it does not replace an unrelated open Decision. Same Decision identity updates in place (AS-3). |
| **Merge behavior** | **No merge of distinct Decisions into one multi-purpose card** (§6.7). “Merge” means only: coalesce duplicate identity attempts into the existing card (RJ-DUPLICATE) — never combine two business Decisions. |
| **Empty** | Zone B empty is success when combined with Quiet (UX Part 7). |

## 3.3 Zone C — CartFlow Working

| Question | Behavior |
|----------|----------|
| **When does reassurance appear?** | When Decision Owner is CartFlow for the merchant’s recovery context (S1 Quiet path) and Workspace needs confidence that automation continues — typically when Zone A and B are empty, or as peripheral calm while Decisions exist **without competing** for attention (UX Part 6 Peripheral). |
| **When does it disappear?** | It may reduce to silent peripheral when Zone A/B demand full attention — reassurance must never compete with Decisions (UX-4). It must not become a queue that “disappears work.” |
| **When should it remain silent?** | When showing it would create supervision pressure; when it would list per-cart Statuses; when Attention Cost ≥ value (AE-1, §6.9). Prefer Quiet copy over activity theater. |
| **Must never** | Invite Action; list Signals; imply merchant must watch CartFlow (UX-14, UX-6). |

## 3.4 Zone D — Completed Outcomes

| Concern | Behavior |
|---------|----------|
| **Refresh behavior** | Compact summary may update when T10/T11 records Completed Outcomes. Refresh of Workspace alone does not invent completions. |
| **Collapse behavior** | Remains compact by default; expanding into full history browser is **forbidden** in Workspace (CDR-010, Q4, UX Zone D). Deep history belongs outside L2. |
| **Retention policy** | Show recent compact proof of completion for confidence — not unbounded archive. Exact retention windows are engineering/history policy downstream; behaviorally: **bounded, compact, non-Decision**. |
| **Purchase completed** | R11 Do Not Admit; may increment Zone D; never create Decision Card (UX-10). |

## 3.5 Zone E — Operational Health

| Question | Behavior |
|----------|----------|
| **When is merchant awareness justified?** | Only exceptional issues where awareness Human Gain > Attention Cost **and** content is merchant-relevant to trust/decision ability — not Admin diagnostics (UX Zone E; Constitution never-become #5/#11). |
| **What must remain hidden?** | Stack traces, pool metrics, provider dashboards, scheduler internals, retry loops as theater, Admin Ops surface. Provider failure under retry (R12) stays hidden as Decision; Execution continues. |
| **Default** | Hidden (fail closed). Always-on health rejected (UX Cognitive Load Audit). |

---

# Part 4 — Attention Behavior

Attention hierarchy is strict: **A → B → C → D → E** (UX Parts 5–6).

## 4.1 What receives focus first?

| Condition | First focus |
|-----------|-------------|
| Zone A non-empty | Highest-value / stable-first Override Decision in Zone A |
| Zone A empty, Zone B non-empty | Highest-value / stable-first admitted Decision in Zone B |
| A and B empty | Quiet confidence (C + D); no Decision focus |

## 4.2 When does focus change?

| Event | Focus change? |
|-------|---------------|
| New Override Admit (T2) | **Yes** — may move focus to Zone A (justified interruption) |
| New normal Admit (T1) while Zone A empty | **Yes** — to new/primary Zone B Decision if no current judgment in progress; if merchant mid-Action on another card, do not yank focus (preserve judgment continuity) |
| New normal Admit while Zone A active | **No steal from A** — new card enters B below A |
| Decision resolved (T3) | Focus moves to next remaining A then B Decision; else Quiet |
| Refresh / poll | **Never** |

## 4.3 Can focus move automatically?

**Yes, only** for governed high-value interruptions:

- Override Admission (T2)  
- Resolution of current Decision revealing next admitted Decision  
- Entry into Quiet when none remain  

**No** for Status ticks, retries, duplicate webhooks, Knowledge claims, customer silence, provider blips under automation capability.

## 4.4 What events deserve interruption?

| Event | Interrupt? | Why |
|-------|------------|-----|
| Override-admitted Decision | **Yes** | L0 / I6 / Gate F |
| Normally admitted Decision when Quiet | **Yes** (primary, not Override-level) | T1 Human Gain > Cost |
| Merchant already mid-Action | Prefer **not** to interrupt mid-judgment except Override | Attention Budget; Merchant Time First |

## 4.5 What events must never interrupt?

| Event | Rule |
|-------|------|
| Provider retry / failure under retry | R12; Execution continues |
| Duplicate webhook / same Evidence | AS-2, OS-3 |
| Customer reply answerable by automation | R04 |
| Customer inactive / silence | R15; Wait strategy |
| Message sent / Status | R16; §6.5 |
| Knowledge claim without Admit | R18 |
| Dashboard refresh | OST-9 |
| VIP detect duplicate while L0 Active | R08 |

---

# Part 5 — Ownership Behavior

Translate Ownership Map into **visible** workspace behavior. No hidden transitions (I14, I15).

## 5.1 Dual-axis visibility

| Ownership change | Merchant-visible workspace effect |
|------------------|-----------------------------------|
| Decision CF → Merchant (T1/T2) | Decision Card appears (Zone B or A) |
| Decision Merchant → CF (T3/T4/T5) | Card resolves/leaves; calm / Quiet if none left |
| Execution CF → Merchant (T6) | Scoped manual posture becomes visible **only** as part of existing governed Decision or explicit handoff affordance — never as Status taxonomy (OQ-2) |
| Execution Merchant → CF (T7) | Manual scope closed; reassurance that CartFlow executes again |
| L0 Inactive → Active (T8) | Mode armed; **no Decision Card yet** |
| L0 Active → Inactive (T9) | Override isolation lifts per policy; no flap |
| → S7 Completed (T10) | Leave L2 Decisions; Zone D compact |
| → S8 Archive (T11) | Outside Decision Workspace |
| S8 → S1 (T12) | Quiet automation posture; Admit only via fresh pipeline |

## 5.2 Named behavioral paths

### CartFlow → Merchant (Decision)

**Trigger:** T1 or T2.  
**Workspace:** Escalation appears as card creation + Explain Before Asking.  
**Feel:** “CartFlow needs your judgment on this one case.”

### Merchant → CartFlow (Decision)

**Trigger:** T3 / T4 / T5.  
**Workspace:** Calm Recovery (Part 10).  
**Feel:** “CartFlow has resumed ownership.”

### Override

**Trigger:** T8 then T2.  
**Workspace:** Zone A card; immediate attention eligibility; Execution stays CartFlow (I7).  
**Feel:** “Exceptional case — decide now; CartFlow still runs recovery.”

### Completion

**Trigger:** T10.  
**Workspace:** No Decision; Zone D may update; Quiet for that journey.  
**Feel:** “Recovered / finished — not a task left open.”

### Archive

**Trigger:** T11.  
**Workspace:** Not an active Decision surface (I10).  
**Feel:** History elsewhere; Workspace stays Decision-focused.

### Knowledge

**Trigger:** Claim published (S9 / R18).  
**Workspace:** **No card**, no Escalation.  
**Feel:** Knowledge remains upstream; Workspace silence is correct.

---

# Part 6 — Live Update Behavior

Live operational truth updates the workspace **without chaos**. Confidence > novelty (Part 8).

| Live event | Admission / Ownership | Workspace behavior |
|------------|----------------------|--------------------|
| **New Decision admitted** | T1 or T2 | Insert card in correct zone; stable order; Override may shift attention |
| **Decision resolved** | T3 | Resolve card → ownership return cue → next Decision or Quiet |
| **Purchase completed** | T10; R11 No | Remove any open Decision for that journey via T5/T10 path; compact Zone D; **no** celebration-as-Decision |
| **VIP / Override detected** | T8 | Arm Override mode; wait for T2 before card; no duplicate if already Active |
| **VIP Override admitted** | T2 / R07 | Zone A card; interrupt hierarchy honored |
| **Customer replied** | Signal only unless R05 Admit | Usually no Workspace change; if automation can answer (R04) stay Quiet; if business exception Admit → one Zone B card |
| **Provider recovered / retry succeeded** | Execution only | Stay Quiet; no “all clear” Decision; Zone E stays hidden unless exceptional awareness rule fires |
| **Provider failure (retryable)** | R12 No | Hidden; CartFlow retries; no card |
| **Provider failure (automation exhausted)** | R13 Yes | One Zone B card |
| **Duplicate event** | OS-3 / AS-2 | Idempotent; zero visible thrash |
| **Slow synchronization** | Temporary uncertainty | Hold prior stable truth; do not flicker empty↔full (Part 9) |

**Preservation rules:**

- Never create visual chaos: batch identity-stable updates; no alert storms.  
- Never re-Admit on live tick alone.  
- Explanation fields may update in place while Decision open (AS-3).

---

# Part 7 — Motion Philosophy

**Behavioral movement only** — not animation, easing, or pixels. These names describe *what the workspace does to truth*, not how it draws.

| Motion class | Meaning | When appropriate | When forbidden |
|--------------|---------|------------------|----------------|
| **Replace** | One Decision identity’s content superseded by governed new Proof under same open Decision, or T4 supersede closes old and policy admits new identity | Supersede policy with new evidence | Replacing unrelated Decisions; replace on refresh |
| **Merge** | Duplicate Admit attempt coalesces into existing card | RJ-DUPLICATE / AS-1 | Merging two distinct Decisions |
| **Collapse** | Reduce peripheral density (Zone D compact; Quiet after last Decision) | Calm Recovery; Zone D default | Collapsing away open Decisions |
| **Expand** | Reveal Explain Before Asking detail for the focused Decision | Merchant inspects a card | Expanding Zone C/D into workload/history product |
| **Promote** | Decision moves attention upward (e.g. enters Zone A via Override Admit) | T2 / L0 path | Promoting Status to Decision without Admission |
| **Demote** | Override isolation ends and remaining Decision continues under normal path **only if policy defines that path**; else close | Governed T9 + policy | Demote on duplicate VIP; random reorder |
| **Highlight** | Attention marks the Decision that deserves focus now | Focus rules Part 4 | Highlighting retries, Status, Knowledge |
| **Fade** | Card leaves after governed resolution while ownership-return meaning remains briefly intelligible | T3/T4/T5 Calm Recovery | Fade without resolution reason; fade on sync blip |

**Principle:** Motion communicates ownership and admission changes. Motion never invents urgency.

---

# Part 8 — Confidence Behavior

The workspace must continuously answer: **“Can I trust what I am seeing?”**

| Confidence behavior | Rule | Governance |
|---------------------|------|------------|
| **No flickering** | Same Evidence → same visible posture; no rapid appear/disappear | OS-1, AI-18, AS-2 |
| **No disappearing without explanation** | Every card exit ties to T3/T4/T5 (or equivalent leave-L2) | I14, BI-2 |
| **No unexpected reordering** | Zone order fixed A→B; within-zone order stable across refresh | UX-4, OS-3 |
| **No repeated alerts** | One Admit per Decision identity; no nag on inactivity | AS-1, R14, AE-4 |
| **Quiet means success** | Empty A+B is confidence, not failure | §6.11, UX-8 |
| **Explain before Action** | Action never appears without context | §6.6, UX-11 |
| **Post-Action resume** | Merchant sees CartFlow ownership return | T3, UX Part 8 |
| **Uncertainty honesty** | When sync lag / temporary uncertainty, prefer last stable truth + non-alarming uncertainty over false empty or false Decision | Part 9; fail closed on Admit |
| **One explanation truth** | Why this Decision exists matches Admission audit (AA-5) | AA-1…AA-5 |

---

# Part 9 — Failure Behavior

Ownership remains deterministic under failure (Ownership Part 8). Workspace must keep merchant confidence.

| Scenario | Ownership | Workspace behavior |
|----------|-----------|---------------------|
| **Provider outage** | Exec CF; Dec unchanged unless R13 Admit | Prefer Quiet + hidden retries; Zone E only if merchant awareness exceptionally justified; if Admit=Yes after exhausted retries → one Decision Card (R13) |
| **Retry / retry loop** | Axes unchanged (OST-4) | No cards; no interruption; no progress theater as Decisions |
| **Duplicate events** | Unchanged (OST-5/6) | Idempotent; no second card; no highlight storm |
| **Slow synchronization** | No fake transitions | Hold last reconciled truth; do not flash Quiet then Decision then Quiet; do not invent Do Not Admit flips |
| **Temporary uncertainty** | Fail closed on new Admit if Proof insufficient (AI-1, AI-15) | Do not show Decision without Proof; do not hide an already-admitted open Decision because sync is slow |
| **Merchant inactivity** | Dec stays Merchant (OST-1) | Card remains; no re-Admit; no shame/urgency inflation |
| **Customer inactivity** | Stay Quiet unless already admitted | No Escalation from silence (R15) |

**Merchant confidence contract during failure:** CartFlow still owns Execution; Workspace does not become a status monitor; when human judgment is truly required, exactly one clear Decision appears.

---

# Part 10 — Calm Recovery

Defining behavior after the merchant acts.

## 10.1 Sequence

```text
Merchant completes primary Action
    ↓
T3 — Decision Ownership → CartFlow
    ↓
Card resolves (Fade/Collapse behavioral class) with ownership-return meaning
    ↓
If other admitted Decisions remain → attention to next (A then B)
    ↓
If none remain → Quiet Confidence (canonical calm)
    ↓
Zone C may reassure: CartFlow continues recovery
    ↓
Zone D may reflect outcome if completion occurred
```

## 10.2 Required merchant feeling

| Must feel | Must not feel |
|-----------|---------------|
| CartFlow has resumed ownership | Work has vanished without reason |
| Their judgment mattered and closed | They are still supervising a queue |
| Quiet is success | Empty is a system error |
| Next interruption will be justified | Anything might pop randomly |

## 10.3 Calm Recovery invariants

| ID | Rule |
|----|------|
| **CR-1** | Resolution is visible before Quiet |
| **CR-2** | Ownership return is intelligible (T3 path) |
| **CR-3** | No immediate re-Admit on same Evidence (AS-4, OE-5) |
| **CR-4** | Calm is Quiet by Default copy/meaning when A+B empty |
| **CR-5** | Peripheral C/D may remain; they must not reintroduce the closed Decision as active work |

---

# Part 11 — Behavioral Invariants

| ID | Invariant |
|----|-----------|
| **BI-1** | Cards never teleport between meanings/zones without a governed ownership/admission gate. |
| **BI-2** | Cards never disappear without T3/T4/T5 (or leave-L2 equivalent). |
| **BI-3** | Cards never duplicate for the same Decision identity / Evidence fingerprint. |
| **BI-4** | Priority / Override never oscillates on duplicate detection (OS-4). |
| **BI-5** | Attention never jumps without cause (Part 4 allow-list only). |
| **BI-6** | Ownership changes remain visible (appear / resolve / calm). |
| **BI-7** | Behavior follows operational truth (Ownership × Admission), not UI navigation. |
| **BI-8** | Workspace calms instead of accumulating noise (AE-4, OE-4, Quiet). |
| **BI-9** | No Status taxonomy as Workspace IA (§6.5, UX-2). |
| **BI-10** | No Decision without Admission (UX-7; peripheral C/D/E are not Decisions). |
| **BI-11** | Override never waits behind normal Decisions (I6, UX-9). |
| **BI-12** | Completed Outcomes never presented as active Decisions (UX-10). |
| **BI-13** | Merchant never supervises automation (UX-6). |
| **BI-14** | One Card = One Decision = One primary Action (§6.7, AI-5). |
| **BI-15** | Fail closed: unclassified → no card (AI-15). |

---

# Part 12 — Operational Behavior Validation Report

Every major behavioral rule validated against Constitution, Ownership Map, Admission Matrix, and UX Blueprint.

## 12.1 Validation matrix

| Behavioral rule | Governing principle | Ownership rule | Admission rule | UX Blueprint |
|-----------------|---------------------|----------------|----------------|--------------|
| Lifecycle Quiet when no Admit | §6.11 Quiet; §6.8 Automation Confidence | S1; I5 | AE-2 default No; Do Not Admit rows | Parts 7–8 empty=confidence |
| Card creation only on Admit | §6.2; Decision Admission def | T1/T2; I4 | Admit=Yes; AI-11 | UX-7; Decision Card Part 4 |
| Override card in Zone A immediately | §6.3 Priority Override | T2; I6; I8; S4 | Gate F; R07 | Zone A; UX-9; hierarchy rank 1 |
| No card on VIP detect alone | §6.3 still requires Admission | T8 ≠ Decision transfer | R08; AI-4 | Zone A “only when Override-admitted” |
| Explanation before Action | §6.6 | Merchant authority after Admit | AA-3 | Card fields 1–5; UX-11 |
| One Action per card | §6.7 | Merchant resolves one Decision | AI-5 | UX-1, UX-3 |
| Update in place, not second card | Attention Budget; Quiet | OS-1, OS-3 | AS-3, AI-10, R14 | Card invariants |
| Disappear only on T3/T4/T5 | §7 ownership transitions | T3/T4/T5; I14 | Closure ends Admit surface | Flow Decide→Calm |
| No reappear on same Evidence | OE-5; OS-1 | AS-4 | AI-16; AS-1 | Confidence / no repeated alerts |
| Zone B sort stable / below A | §6.9; Merchant Time First | I6 | Matrix does not define chaos rank | UX-4; Attention Architecture |
| Zone C reassurance not queue | §6.2 Automation Before Escalation | S1 Exec CF | Do Not Admit path | Zone C; UX-14 |
| Zone D compact completions | L4; never-become analytics | S7; T10; I9 | R11 No | Zone D; UX-10 |
| Zone E rare / hidden default | §6.1; never-become monitor | — | Awareness > cost or hide | Zone E; UX-15 |
| Focus A then B | §6.3; §6.9 | I6 | Gate F before normal queue | Parts 5–6 |
| Never interrupt on retry | §6.5 Decision Over Status | OST-4; Exec stays CF | R12 RJ-NOISE | Hidden tier |
| Customer reply ≠ auto card | §6.5; §6.12 | Signal non-transition | R04 vs R05 | Hidden unless Admit |
| Purchase → D not Decision | L4; §6.10 | T10; OS-5; I9 | R11; AI-8 | UX-10; Part 8 |
| Provider outage calm | Automation default | Part 8 failure table | R12 / R13 split | Failure ≠ status board |
| Calm Recovery after Action | §2 philosophy; Quiet | T3 → S1 | No immediate re-Admit | Part 8 flow; confidence |
| Knowledge never Escalates | §8 adjacent; never-become #12 | S9; I15 | R18 RJ-KNOWLEDGE | Reject knowledge cards in B |
| Archive not Decision surface | Q4; L4 | S8; I10 | R19 | History outside Workspace |
| Duplicate live events idempotent | Quiet; Attention Budget | OS-3; OST-6 | AS-2; R17 | No chaos live updates |
| Manual exec rare | §6.4 dual ownership | T6/T7; S5/S6 | Gate B allows; not auto | No Status IA for handoff |
| Mid-judgment focus protect | §6.1 Merchant Time First | OE-1 interruption cost | AE-1 | Attention Part 6 |
| Fail closed unclassified | Automation Confidence | I15 no implicit | AI-15 RJ-UNCLASSIFIED | UX-7 |

## 12.2 Orphan / invention check

| Check | Result |
|-------|--------|
| Behaviors without Constitution cite | **None** in Parts 1–11 |
| Behaviors that redefine Ownership types | **None** — only CartFlow/Merchant axes + L0 mode |
| Behaviors that change Admit outcomes | **None** — Matrix Part 4 unchanged |
| Behaviors that invent pixels/CSS/animation | **None** — motion is behavioral classes only |
| Behaviors that invent T4/T6/T12 policy detail | **None** — OQ-1/2/4 explicitly deferred |
| Conflicts with UX Blueprint zones | **None** |
| Conflicts with Quiet ↔ Override coexistence | **None** — Override Admit ≠ L3 noise |

## 12.3 Scenario walkthroughs (behavioral)

| Scenario | Expected workspace behavior |
|----------|-----------------------------|
| Open Workspace, all Quiet | WL-1 Quiet Confidence; no Decision cards; C/D peripheral |
| Normal Admit while Quiet | Zone B card appears; focus to B; Explain + one Action |
| Merchant acts | T3; Calm Recovery; Quiet if last Decision |
| VIP Override Admit | Zone A card; focus A; never behind B |
| Duplicate VIP while Active | No new card; no oscillation |
| Customer reply (automation can answer) | No card |
| Provider retry loop | No card; no interruption |
| Purchase while Decision open | Leave L2 via completion path; Zone D compact; no Decision |
| Refresh spam | No ownership change; no reorder thrash; no re-Admit |
| Reopen archive without new Evidence | No Decision card |

## 12.4 Verdict

| Criterion | Result |
|-----------|--------|
| Designer can implement experience without inventing runtime behavior | **Pass** — zones, cards, attention, calm, failure covered |
| Engineer can encode transitions without inventing ownership/admission | **Pass** — bound to T1–T12 + Admit binary + AS/OS |
| No independent philosophy introduced | **Pass** — derivation-only |
| Ready as final Product gate before Architecture Review | **Pass** — pending product approval of this blueprint |

**Overall:** Cart Workspace Operational Behavior Blueprint V1 is **complete as behavioral architecture**. After approval, product foundation for Cart Workspace is complete; next authorized stages are Architecture Review → High-Fidelity UX/UI (Figma) → Engineering Specification → Implementation.

---

## Derivation gate

| Stage | Status |
|-------|--------|
| Governance Pack | Ratified |
| Ownership Map V1.1 | Parent |
| Decision Admission Matrix V1.1 | Parent |
| Cart Workspace UX Blueprint V1 | Parent |
| **Cart Workspace Operational Behavior Blueprint V1** | **This document — last Product document before Architecture Review** |
| Architecture Review | **Blocked** until this blueprint approved |
| High-Fidelity UX/UI (Figma) | **Blocked** until Architecture Review path allows (still after product approval of behavior) |
| Engineering Specification / Implementation | **Blocked** |

---

## Change log

| Version | Change |
|---------|--------|
| **V1** | Full operational behavior: lifecycle WL-0…7; Decision Card creation→reappearance; Zones A–E behavior; attention; ownership visibility; live updates; motion philosophy; confidence; failure; Calm Recovery; invariants BI-1…15; validation report. |

---

**End of Cart Workspace Operational Behavior Blueprint V1.**
