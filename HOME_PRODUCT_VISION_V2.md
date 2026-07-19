# Home Product Vision V2

**Document type:** Constitutional reference (executive purpose of Home)  
**Status:** **Approved / Locked — Constitutional**  
**Date (UTC):** 2026-07-19  
**Ratified (UTC):** 2026-07-19 — [`HOME_EXECUTIVE_CONSTITUTION_V1.md`](HOME_EXECUTIVE_CONSTITUTION_V1.md)  
**Authority:** Binding purpose, IA, ownership, disclosure, and hierarchy law for every future Home implementation  

**Governing constitution:** [`HOME_EXECUTIVE_CONSTITUTION_V1.md`](HOME_EXECUTIVE_CONSTITUTION_V1.md)  

**Out of scope until Executive Home Implementation V1 is opened:**

- UI improvements · component redesign · spacing · wording polish  
- CSS · frontend · engineering implementation  
- Commercial Knowledge Expansion V1  
- Wiring new engines to Home  

**Companions in this constitutional pack:**

| # | Artifact | File |
|---|----------|------|
| 1 | Vision (this document) | `HOME_PRODUCT_VISION_V2.md` |
| 2–7 | Executive IA, questions, ownership, order, disclosure, hierarchy | §§2–7 below |
| 3′ | Executive Question Registry (extract) | [`HOME_EXECUTIVE_QUESTION_REGISTRY_V2.md`](HOME_EXECUTIVE_QUESTION_REGISTRY_V2.md) |
| 8–10 | Remove/Merge/Introduce · Current→New map · Transition | §§8–10 below + [`HOME_PRODUCT_VISION_V2_TRANSITION.md`](HOME_PRODUCT_VISION_V2_TRANSITION.md) |

---

## 0. The only question

> **If a merchant opens CartFlow for 30 seconds every morning, what should they understand before doing anything else?**

Everything on Home exists **only** because it helps answer that question.  
Anything that does not is not Home — regardless of how true, useful, or hard-won it is for engineering.

---

## 1. Home Product Vision V2

### 1.1 What Home becomes

Home is the merchant’s **morning executive brief**.

In thirty seconds, the merchant should leave knowing:

1. Whether the business is healthy today  
2. The single highest-value action today  
3. The biggest opportunity today  
4. What CartFlow learned about the business today  
5. Whether that understanding is confident enough to act on  
6. What decision to make next (and where to make it)

They should never feel they are reading an **engineering dashboard**, a **recovery console**, or a **trace of the platform’s internal reasoning**.

### 1.2 What Home is for

| Home is | Meaning |
|---------|---------|
| **Executive altitude** | Business outcomes, not system internals |
| **Daily commercial orientation** | Today’s health, attention, opportunity, and decision |
| **Trusted understanding** | What CartFlow believes — stated as merchant meaning |
| **Decision pointer** | Names the decision; routes the work elsewhere |
| **Progressive truth** | Evidence and “how we know” available on demand |

### 1.3 What Home is not

| Home is not | Why |
|-------------|-----|
| Recovery dashboard | Carts and recovery execution have their own surfaces |
| Engine diary | Intermediate calculations are not merchant understanding |
| Evidence warehouse | Evidence supports conclusions; it does not lead |
| Investigation lab | Deep “why” belongs in Decision Workspace / owned pages |
| Analytics explorer | Exploration is not a 30-second morning job |
| Implementation status board | Loader states, pipelines, field names are engineering |

### 1.4 The executive shift (vision, not layout)

| From (current product habit) | To (Vision V2) |
|------------------------------|----------------|
| Platform reasoning on display | Merchant daily understanding on display |
| Explanation before decision | Decision before evidence |
| Evidence always visible | Evidence on demand |
| Engine thinking readable by default | Engine reasoning collapsed / merchant-readable if opened |
| Internal counters as proof | Commercial meaning as proof |
| “Here is what the system computed” | “Here is what your business needs today” |

### 1.5 Constitutional evolution (explicit)

| Locked Constitution V2 | Vision V2 refinement |
|------------------------|----------------------|
| Mission: *What should I know about my store right now?* | Mission: *What must I understand in 30 seconds before I act today?* |
| Home summarizes; awareness only | Home still does **not execute** — but it **names the decision of the day** with executive clarity |
| Five awareness questions | Six executive outcomes (health · action · opportunity · learning · confidence · next decision) |
| Chronology never primary | Unchanged — change is a brief, not a feed |
| No owned business logic | Unchanged — Home remains a **governed consumer** of truth |

Vision V2 does **not** turn Home into Decision Workspace.  
It makes awareness **executive** — not operational, not investigative, not explanatory-first.

### 1.6 Trust (non-negotiable)

Aligned with [`MERCHANT_TRUST_CONSTITUTION_V1.md`](MERCHANT_TRUST_CONSTITUTION_V1.md):

- Evidence before speech  
- Silence is legal  
- No fake intelligence  
- Insufficient confidence is a first-class answer  
- Never scare the merchant into action with engineering urgency theater  

---

## 2. Executive Information Architecture

Blank-page model. **Not** the current seven Brief sections. **Not** the current card stack.

Home has **six executive bands**. Each band answers exactly one commercial question. Bands are cognitive, not visual components.

```text
┌─────────────────────────────────────────────────────────┐
│  E1  BUSINESS HEALTH TODAY                              │
│      Is my business healthy today?                      │
├─────────────────────────────────────────────────────────┤
│  E2  DECISION OF THE DAY                                │
│      What decision should I make today?                 │
│      (+ highest-value action — one only)                │
├─────────────────────────────────────────────────────────┤
│  E3  BIGGEST OPPORTUNITY TODAY                          │
│      What opportunity am I about to miss?               │
├─────────────────────────────────────────────────────────┤
│  E4  WHAT CARTFLOW UNDERSTANDS TODAY                    │
│      What does CartFlow understand about my business?   │
├─────────────────────────────────────────────────────────┤
│  E5  CONFIDENCE TO ACT                                  │
│      Is this understanding strong enough?               │
├─────────────────────────────────────────────────────────┤
│  E6  WHAT CHANGED                                       │
│      What changed since yesterday? (brief, not feed)    │
└─────────────────────────────────────────────────────────┘
         ↓ progressive disclosure (any band)
┌─────────────────────────────────────────────────────────┐
│  D*  HOW WE REACHED THIS  ·  WHY IT MATTERS  ·  ROUTE   │
│      Collapsed by default · merchant language only      │
└─────────────────────────────────────────────────────────┘
```

### 2.1 Band definitions

| Band | ID | Merchant question | One-sentence job | May contain | Must never contain |
|------|----|-------------------|------------------|-------------|--------------------|
| **Business Health Today** | E1 | Is my business healthy today? | State of the store at executive altitude | Health verdict · pressure theme · calm qualifier | Raw counters, KPI grids, engine status |
| **Decision of the Day** | E2 | What decision should I make today? | The single highest-value decision + action pointer | One decision · why now · if ignored · route | Multiple competing CTAs · investigation |
| **Biggest Opportunity Today** | E3 | What opportunity am I about to miss? | The best constructive upside today | One opportunity · commercial meaning · optional route | Duplicate of E2 · fear framing |
| **What CartFlow Understands Today** | E4 | What does CartFlow understand about my business today? | The day’s commercial understanding (not ops trivia) | 1–3 merchant-readable understandings | Field dumps · finding IDs · pipeline talk |
| **Confidence to Act** | E5 | Is confidence sufficient? | Whether to trust the above enough to act | Clear confidence stance · what would strengthen it | Internal scores, thresholds, variable names |
| **What Changed** | E6 | What changed since yesterday? | Orientation delta — not a timeline product | Short change brief (or honest “nothing material”) | Event logs, raw activity streams |

### 2.2 Ownership rules

1. **One primary decision (E2).** If two issues compete, Home chooses one; the other may appear only as secondary context inside disclosure — never as a second peer CTA.  
2. **Opportunity (E3) ≠ Decision (E2).** Opportunity is upside; Decision is the act that protects or captures value today. They may share a commercial root but must not duplicate wording or CTA.  
3. **Understanding (E4) has no primary CTA.** It informs; it does not commandeer the day.  
4. **Confidence (E5) is first-class.** Weak confidence is a valid executive answer — not a failure state to hide behind more cards.  
5. **Change (E6) is brief.** If nothing material changed, say so. Do not invent motion.  
6. **Health (E1) frames; it does not list.** Health is a verdict, not a dashboard of parts.

### 2.3 Empty / insufficient states (executive)

| Condition | Merchant experience |
|-----------|---------------------|
| New store / thin evidence | Health: still learning · Decision: none required or setup-owned · Confidence: not yet · Understanding: what we cannot yet claim |
| Conflicting truth | Do not resolve on Home · Show that confidence is limited · Route to the owning surface |
| Platform degradation | Merchant-impact language only (“some insights unavailable”) — never loader/pipeline names |

---

## 3. Merchant Question Registry (Executive)

This registry is the **Vision V2 executive question set**.  
It sits *above* [`COMMERCIAL_QUESTION_REGISTRY_V1.md`](COMMERCIAL_QUESTION_REGISTRY_V1.md): CQ-* answers are **inputs** that may fuel a band; they are not automatically Home sections.

### 3.1 Primary executive questions (must appear as bands)

| ID | Question | Band | Success when merchant can say… |
|----|----------|------|--------------------------------|
| **EQ-01** | Is my business healthy today? | E1 | “I know if today is fine, strained, or needs attention.” |
| **EQ-02** | What decision should I make today? | E2 | “I know the one decision that matters most today.” |
| **EQ-03** | What is the highest-value action today? | E2 (paired with EQ-02) | “I know what to do first — and where.” |
| **EQ-04** | What opportunity am I about to miss? | E3 | “I know the upside I should not ignore.” |
| **EQ-05** | What does CartFlow understand about my business today? | E4 | “I know what CartFlow believes — in my language.” |
| **EQ-06** | Is confidence sufficient to act? | E5 | “I know whether to act, wait, or gather more truth.” |
| **EQ-07** | What changed since yesterday? | E6 | “I know if the story moved — without reading a log.” |

### 3.2 Disclosure questions (never primary bands)

| ID | Question | Default |
|----|----------|---------|
| **EQ-D1** | Why does this deserve attention now? | Collapsed |
| **EQ-D2** | What happens if I ignore this? | Collapsed |
| **EQ-D3** | How did CartFlow reach this understanding? | Collapsed |
| **EQ-D4** | What evidence supports this? | Collapsed |
| **EQ-D5** | Where do I go to act or investigate? | Visible as route only when a decision/opportunity exists |

### 3.3 Admission law (executive)

An insight may appear on Home **only if**:

1. It answers one **EQ-*** (or fuels one without becoming its own band)  
2. It carries merchant **meaning** (not a metric dump)  
3. It carries a **confidence stance** (including “not enough yet”)  
4. It does **not** require the merchant to interpret engineering artifacts  
5. It is not a duplicate of another admitted band’s job  

**Forbidden on the executive surface (even if true):**

- `hesitation_total=0`, `returns=0`, and peer internal counters as merchant copy  
- Evidence pipeline / loader / snapshot / admission diagnostics  
- Canonical field names, finding type IDs, engine stage names  
- “How the engine thought” as default-visible content  
- Implementation terminology (“fixture”, “projection”, “slim row”, “namespace”, …)

Those belong to engineering, admin, labs, and investigation — never to the morning brief.

### 3.4 Relationship to Commercial Question Registry V1

| Layer | Role |
|-------|------|
| **EQ-*** (this Vision) | What the merchant must understand on Home |
| **CQ-*** (Commercial Question Registry V1) | Which commercial questions CartFlow can answer with evidence across the platform |
| Mapping | CQ answers are **candidates** to fill E1–E6; they do not each get a Home card |

Example: CQ-C01 (missing contact blocking recovery) may fuel **E2 Decision of the Day** — it must not appear as a raw contact metric strip plus a parallel “understanding” essay plus a learning card saying the same thing.

---

## 4. Section ownership

| Band | Owns | Does not own | Routes to (when action exists) |
|------|------|--------------|--------------------------------|
| **E1 Health** | Today’s business health verdict | Decisions, opportunities, timelines | — (orientation only) |
| **E2 Decision** | The single decision + highest-value action | Opportunity framing, deep evidence, cart execution | Decision Workspace / Carts / Communication / Settings as ownership requires |
| **E3 Opportunity** | Best constructive upside today | The primary “do this now” CTA (unless Product explicitly merges E2+E3 for a day — rare) | Owning surface for capture |
| **E4 Understanding** | What CartFlow understands today | Action CTAs, health verdict | Optional deepen route — never primary action |
| **E5 Confidence** | Sufficiency of understanding to act | The decision itself | May suggest waiting or gathering truth — not fake urgency |
| **E6 Change** | Material delta since yesterday | Full history, activity feed | Timeline/history surfaces if merchant asks for more |
| **D* Disclosure** | Why / evidence / how-we-know / ignore-cost | Primary narrative | Same routes as parent band |

**One owner per commercial fact.**  
If Health, Decision, and Understanding would all narrate “missing contact,” only **Decision** speaks the action; Health may reflect pressure; Understanding may state the commercial lesson — **different jobs, different sentences, no triple CTA**.

---

## 5. Reading order

Natural executive reading for a 30-second morning:

```text
E1 Health
  → E2 Decision of the Day  (includes highest-value action)
    → E3 Opportunity
      → E4 Understanding
        → E5 Confidence
          → E6 What changed
            → (optional) open D* on the band that matters
```

### 5.1 Order principles

| Principle | Rule |
|-----------|------|
| **State before act** | Health before Decision |
| **Decision before opportunity** | Protect/capture priority before upside |
| **Understanding before confidence detail** | Know the claim before judging its strength — but Confidence remains visible, not buried in footnotes |
| **Change last among primaries** | Delta orients; it does not lead |
| **Disclosure never leads** | “How we know” never appears above the conclusion |
| **Adaptive sequencing later** | Cognitive Router may reorder **admitted bands** for path (VIP / attention / insufficient) **without inventing new band jobs** |

### 5.2 Thirty-second contract

By second 30 the merchant must be able to answer EQ-01, EQ-02/03, EQ-04, EQ-05, EQ-06 without scrolling into disclosure.  
EQ-07 may be a single line.  
D* is never required for the 30-second pass.

---

## 6. Progressive disclosure strategy

### 6.1 Layers of depth

| Depth | Name | Default | Content |
|-------|------|---------|---------|
| **L0** | Executive claim | Always visible | Verdict / decision / opportunity / understanding / confidence / change — merchant language |
| **L1** | Commercial why | Collapsed | Why now · why it matters · if ignored — still merchant language |
| **L2** | How we know | Collapsed | Merchant-readable evidence narrative — **no raw internals** |
| **L3** | Engineering / investigation | **Never on Home** | Field names, pipelines, counters-as-API, diagnostics — admin/labs only |

### 6.2 “How did we reach this understanding?”

Becomes **L2 progressive disclosure**:

- Collapsed by default  
- Readable by merchants  
- Speaks in outcomes and observed business patterns  
- Never exposes: raw implementation values, internal variable names, engineering diagnostics, engine stage labels  

### 6.3 Evidence law

| Rule | Meaning |
|------|---------|
| Decision before evidence | E2 states the decision before any evidence block |
| Evidence on demand | L1/L2 open by merchant choice |
| Evidence is not the hero | Opening evidence must not replace the executive claim |
| Insufficient evidence is speakable | “We do not know enough yet” is L0-valid under E5 / E4 |

---

## 7. Information hierarchy

### 7.1 Priority of attention (admission & ranking)

When multiple truths compete for a band:

1. **Merchant harm / revenue at risk today**  
2. **Decision urgency (cost of delay)**  
3. **Confidence sufficiency**  
4. **Freshness of the underlying truth**  
5. **Strategic opportunity**  
6. **Orienting change**  

Chronology is **never** the primary ranker.

### 7.2 Visual hierarchy (product intent only — not UI spec)

| Rank | Content |
|------|---------|
| 1 | E2 Decision of the Day (the point of opening CartFlow) |
| 2 | E1 Health (frame for the day) |
| 3 | E3 Opportunity |
| 4 | E4 Understanding |
| 5 | E5 Confidence |
| 6 | E6 Change |
| 7 | Disclosure controls |

Note: **Reading order** (Health → Decision) and **visual gravity** (Decision as hero) can differ. The merchant may *see* Decision most prominently while still *encountering* Health first in the cognitive sequence. Implementation must honor both intents without inventing a seventh peer band.

### 7.3 Density budget

| Budget | Rule |
|--------|------|
| Primary decisions | **1** |
| Primary opportunities | **0–1** |
| Understanding claims | **1–3** (not a catalog) |
| Change lines | **1 short brief** |
| Always-visible metrics | **None** as a strip; numbers only inside merchant meaning when essential |

---

## 8. Remove / Merge / Introduce

| Current / habitual Home element | Decision | Rationale |
|---------------------------------|----------|-----------|
| Engineering / diagnostic copy (`returns=0`, field names, pipeline talk) | **Remove** from Home | Violates executive altitude |
| Default-visible “how the engine reasoned” | **Remove** from L0 | Becomes L2 disclosure |
| Multiple peer CTAs across sections | **Remove** pattern | One Decision of the Day |
| KPI / quick-indicator strips as peers | **Remove** or demote to disclosure | Not executive questions |
| Full business timeline / activity feed on Home | **Remove** as primary band | Replace with E6 brief; deep history elsewhere |
| Duplicate narrations of same contact/recovery fact | **Merge** into one owner (usually E2) | Semantic dedup becomes vision law, not a patch |
| “Learning progress” as a peer essay card | **Merge** into E4 + E5 | Learning is understanding + confidence, not a third stage |
| Risk card + Priority card saying the same act | **Merge** into E2 | Risk informs Decision; it is not a second homepage |
| Business Health | **Keep → E1** | Reframe as verdict, not multi-widget health |
| Today’s Priority / Attention | **Keep → E2** | Elevate to Decision of the Day |
| Biggest Opportunity | **Keep → E3** | Keep constructive; forbid fear twin of E2 |
| Business Understanding | **Keep → E4** | Strip ops trivia; commercial understanding only |
| Confidence chips buried in prose | **Introduce as E5** | First-class executive question |
| Material change since yesterday | **Introduce as E6** (brief) | Replaces timeline-as-Home |
| Progressive disclosure shell (D*) | **Introduce** | Universal pattern for why / evidence / how-we-know |
| EQ registry (executive questions) | **Introduce** | Sits above CQ registry for Home admission |

---

## 9. Mapping — current Home → Vision V2 Home

| Current production Brief / habit | Vision V2 band | Map rule |
|----------------------------------|----------------|----------|
| `business_health` / صحة العمل | **E1** | Keep job; forbid internal proof language; health = verdict |
| `biggest_revenue_risk` / أكبر خطر | **→ E2 (input)** or disclosure under E2 | Risk is not a peer homepage; it feeds Decision |
| `biggest_opportunity` / أكبر فرصة | **E3** | Keep if distinct from E2; else suppress |
| `todays_priority` / أولوية اليوم | **E2** | Rename job to Decision of the Day + single action |
| `business_understanding` / فهم العمل | **E4** | Keep; no CTA; no raw evidence lead |
| `learning_progress` / تقدّم الفهم | **E4 + E5** | Split: what we understand vs whether it’s enough |
| `business_timeline` / سجل العمل | **E6** (brief only) or **off Home** | No feed; material change or silence |
| Adaptive Cognition path focus | **Sequencing only** | May reorder E1–E6 admission; must not invent band jobs |
| Commercial Intelligence (CQ → sections) | **Fuel for E1–E6** | Admit by EQ ownership; diversity by band, not by card count |
| Semantic dedup / composition | **Enforcement layer** | Continues under Vision as law for one-owner-per-fact |
| CIL / missing-contact interpretation | **Typically E2** | Decision + route; not triple-projected |
| Setup / activation leftovers | **Off executive brief** or single setup decision under E2 | Setup is not a permanent seventh band |

Detailed transition sequencing: [`HOME_PRODUCT_VISION_V2_TRANSITION.md`](HOME_PRODUCT_VISION_V2_TRANSITION.md).

---

## 10. Success criteria (Product Review)

Vision V2 is successful when a merchant can leave Home and honestly say:

| # | Understanding | Without… |
|---|---------------|----------|
| 1 | Current health of the business | Reading a metrics wall |
| 2 | Highest-value action today | Choosing among three peer CTAs |
| 3 | Biggest opportunity today | Confusing opportunity with alarm |
| 4 | What CartFlow learned today | Reading engine vocabulary |
| 5 | Whether confidence is sufficient | Decoding score mathematics |
| 6 | What decision to make next | Feeling inside an engineering dashboard |

And when Home **never** shows: internal counters as copy, evidence pipelines, loader states, canonical field names, or default-visible engine thinking.

---

## 11. STOP

- No implementation  
- No UI coding · no CSS · no components  
- No Commercial Knowledge Expansion V1  

**Ratified** under [`HOME_EXECUTIVE_CONSTITUTION_V1.md`](HOME_EXECUTIVE_CONSTITUTION_V1.md).  
**Await kickoff** of Executive Home Implementation V1 — this Vision pack is the single implementation reference when that phase opens.
