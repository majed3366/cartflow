# Decision Storytelling Constitution V1

**Status:** **FROZEN** — Decision Intelligence Framework V1 production baseline.  
**Date (UTC):** 2026-07-28  
**Object:** Decision Story (the continuous operational narrative CartFlow presents across surfaces)  
**Non-goals of original pack:** No UI. No implementation. No design. No component work. No copy polishing.

**Authority:** Binding law for **how CartFlow tells the merchant what matters next**.  
**Related (peer / upstream):**  
- Product Constitution V1 · Principle 0 · Principle 7  
- [`Decision Playbooks Constitution V1`](../decision_playbooks_constitution_v1/DECISION_PLAYBOOKS_CONSTITUTION_V1.md)  
- [`Executive Compression Engine V1`](../executive_compression_engine_v1/EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md)  
- [`Execution Methodology V1`](../execution_methodology_v1/EXECUTION_METHODOLOGY_V1.md) (**EM-001** · **EM-002**)  
- Decision Workspace / Cards / Home Constitution V2 · Diagnostic Reasoning Foundation V1  

A surface presentation that violates this Constitution is **unconstitutional**, even if diagnostically correct or visually polished.

**Constitutional amendments in this pack:** **DS-009** Story Truth Law.

Companion: [`STORYTELLING_QUALITY_RULES_V1.md`](./STORYTELLING_QUALITY_RULES_V1.md).

---

## 1. Mission

The merchant must never feel that they are reading **independent cards**.

The entire product must behave as **one continuous operational story**.

| Beat | Surface role |
|------|----------------|
| **Begins** | Home |
| **Explains** | Decision Workspace |
| **Continues** | Execution surfaces (Products · Carts · Communication · Settings / platform locus as routed) |
| **Closes** | Reality Validation |

The merchant should feel they are **progressing through today’s work** — not navigating pages.

---

## 2. Constitutional Principle

CartFlow does **not** present information.

CartFlow presents **today’s operational narrative**.

Every decision answers:

> **Why is this appearing now?**

**before** answering:

> **What should I do?**

---

## 3. Final Constitutional Principle

CartFlow does not organize information into pages.

It guides the merchant through a **single operational story** that:

1. begins with **attention**  
2. leads to the **right decision**  
3. continues through **execution**  
4. ends with **measurable business impact**

---

## 4. Relationship to other constitutions

| Layer | Owns |
|-------|------|
| Diagnostic Reasoning | Truth of what is happening |
| Decision Playbooks | Whether an executable task may exist (**PBL-001** / **PBL-002**) |
| Execution Methodology | Readiness · locus · EM-002 close loop |
| Executive Compression | Minimum merchant-visible content |
| **Decision Storytelling** (this pack) | Cross-surface **narrative order**, ranking, continuity, identity, language altitude |
| Surface UX (Home / Workspace / …) | Layout that **consumes** the story — must not invent a second story |

**Hard rule:** Storytelling **consumes** engine output. It never exposes the engine.

---

## 5. Story Order Law (**DS-001**)

Every operational story follows **exactly one** sequence.

```
1. Why this matters now   (Priority)
  ↓
2. Observation
  ↓
3. Meaning
  ↓
4. Decision
  ↓
5. Execution              (only if READY)
  ↓
6. What happens next      (Story Completion)
```

### 5.1 Why this matters now (Priority)

Explain why this deserves attention **today**.

Illustrative shape (not production copy):

- هذا القرار يمثل أعلى فرصة لتحسين التحويل اليوم.  
- هذا أكثر مكان يخسر فيه المتجر عملاء اليوم.  
- هذا أول قرار لأن أكبر عدد من العملاء توقفوا هنا.  

| Required | Forbidden |
|----------|-----------|
| Begin with **priority** | Begin with instructions |
| Evidence-linked “why now” | Generic urgency without store basis |

### 5.2 Observation

**Only** observable reality.

Illustrative shape:

- يغادر العملاء بعد خطوة الشحن.  
- العملاء يفتحون الرسالة الأولى ولا يعودون.  
- يكتمل الدفع غالبًا بعد التواصل.  

| Required | Forbidden |
|----------|-----------|
| Observable fact | Diagnosis lecture |
| Store-specific reality | Recommendation / action |

### 5.3 Meaning

Convert observation into **business impact**.

Illustrative shape:

- هذا يؤثر مباشرة على إتمام الشراء.  
- هذا يحد من استرجاع الإيرادات.  
- هذا قد يخفض معدل التحويل.  

| Required | Forbidden |
|----------|-----------|
| Business impact in merchant language | Engine terms |
| Distinct from Observation | Internal identifiers |

### 5.4 Decision

**One sentence. Exactly one action** (or an honest wait).

Illustrative shape:

- لا تغيّر سياسة الشحن الآن.  
- راجع الرسالة الأولى للاسترجاع.  
- افتح إعدادات الشحن في زد.  

Multiple competing actions in one story unit = fail.

### 5.5 Execution

**Only if readiness = READY** (or an explicitly executable EM-001 state that allows merchant action — never when **NEEDS_MORE_EVIDENCE** pretends to be ready).

If **not** executable:

| Must | Must not |
|------|----------|
| Omit execution block | Fake destination |
| Omit button / CTA | Artificial “go somewhere” |
| State wait honestly | Invent a task to fill space |

Illustrative wait close (not production copy):

- سنخبرك عندما تصبح الأدلة كافية.

---

## 6. Story Completion Law (**DS-002**)

Every story must **naturally end**.

| Forbidden endings | Required ending |
|-------------------|-----------------|
| العودة للملخص (as the story’s close) | Merchant understands **what happens next** |
| انتهى | Forward operational posture |

Illustrative completion shapes (not production copy):

- يواصل CartFlow التحقق وسينقل هذا القرار تلقائيًا إلى التنفيذ عند اكتمال الأدلة.  
- بعد تنفيذ الخطوة سيقيس CartFlow أثرها ويحدّث القرار تلقائيًا.  

Completion aligns with **EM-002** (Action Evidence → Reality Validation → Decision Update) without naming the engine.

---

## 7. Story Ranking Law (**DS-003**)

Stories are ordered by **operational importance**.

**Never** by type, category, domain label, or card taxonomy.

| Rank group | Merchant meaning |
|------------|------------------|
| **Priority 1** | Do first |
| **Priority 2** | Do after Priority 1 |
| **Monitor** | No action now — observe only |
| **Later** | Not today’s work |

The merchant thinks in **workload**, not categories.

Surfaces may show at most one Priority 1 as the primary story beat; Priority 2 follows; Monitor / Later must not compete as equals with Priority 1.

---

## 8. Story Continuity Law (**DS-004**)

Stories **never restart**.

If the merchant opens another page, **the same story continues**.

```
Home
  ↓
Decision Workspace
  ↓
Execution surface (as routed)
  ↓
Reality Validation
```

| Continuity requires | Continuity forbids |
|---------------------|--------------------|
| Same decision identity | Rewriting the story per page |
| Same priority posture | Home says A, Workspace says B |
| Recognizable wording | Page-local “new” recommendation language |

Editorial altitude may shorten (teaser vs explain). Meaning must not fork.

---

## 9. Story Identity Law (**DS-005**)

Each decision owns **one narrative**.

Its wording must remain **recognizable** across every surface.

The merchant should immediately recognize:

> “This is the same decision.”

Identity is carried by: priority reason · observation · meaning · decision sentence · (when present) execution locus — not by internal IDs shown to the merchant.

---

## 10. Language Law (**DS-006**)

Write like an **operations director**.

Never like an engineer.

### Forbidden (merchant-facing labels / voice)

Examples of banned system / abstract labels:

- Opportunity  
- Execution  
- Observation  
- Diagnostic  
- Situation  
- Signal  
- Operational Meaning  
- Knowledge  

(Equivalent Arabic engineer/system labels that expose the stack are also forbidden.)

### Allowed (merchant workload / action voice)

Illustrative allowed posture words:

- الأولوية الأولى  
- بعدها  
- راقب  
- لاحقًا  
- افتح…  
- راجع…  
- انتظر…  
- أوقف…  
- ابدأ…  

Operational Language UX and Executive Compression must conform to this altitude after approval — they do not override it.

---

## 11. Engine Isolation Law (**DS-007**)

Storytelling never exposes internal architecture.

**Never display** (non-exhaustive):

- ORV  
- `cs:` / situation identifiers as merchant content  
- Diagnostic IDs  
- Pipeline names  
- Knowledge routing  
- Engine stages  
- Confidence calculations  
- Internal collectors  
- Playbook validation ledgers / PBL metadata  
- Family IDs / publication gates  

Decision Storytelling **consumes** engine output.  
It **never** exposes the engine.

---

## 12. Cognitive Load Law (**DS-008**)

The merchant should understand the decision within **five seconds**.

If reading requires effort → **the story failed**.

Aligns with Executive Compression’s 15-second page test; the **decision unit** itself must clear in ≤5 seconds.

---

## 13. DS-009 — Story Truth Law

**The operational story must never be predetermined.**

CartFlow does **not** tell the same story every day.

The story is generated from the **current operational reality**.

### 13.1 Core principle

**The merchant’s store determines the story.**

| Determines the story | Does not determine the story |
|----------------------|------------------------------|
| Current operational reality | Templates |
| Evidence-backed priority | Fixed page order |
| Diagnosis + readiness + context | Predefined scenarios |

### 13.2 Story generation

Every operational story is generated from:

```
Current evidence
  ↓
Current diagnosis
  ↓
Current business priority
  ↓
Execution readiness
  ↓
Current merchant context
```

The story **changes whenever operational truth changes**.

### 13.3 Truth before story

Storytelling **never decides** what is important.

Storytelling **only explains** what the platform has already determined.

| Priority comes from | Priority never comes from |
|---------------------|---------------------------|
| Operational evidence | UI layout |
| Upstream diagnosis / playbook gates | Static ordering |
| Current readiness | Presentation templates |

### 13.4 Illustrative evolution (not production copy)

| Day | Operational truth | Story begins with |
|-----|-------------------|-------------------|
| **Day 1** | Shipping is the largest customer bottleneck | Shipping |
| **Day 7** | Shipping stabilizes; Recovery Messages are the strongest opportunity | Recovery Messages |
| **Day 30** | No immediate execution; evidence collection is highest priority | Observation — **no artificial action** |

### 13.5 Story evolution

Stories **evolve**. They never remain static by default.

A story may: **Start · Grow · Split · Merge · Pause · Resume · Finish**.

Every transition must be caused by **operational truth**.

**Never** by presentation logic alone.

### 13.6 Story consistency under change

Although the story changes, the merchant must **never feel lost**.

When priorities change, CartFlow explains **naturally** why today’s first priority differs from yesterday’s — without restarting as an unrelated product tour (**DS-004** / **DS-005** still apply to the active story identity).

### 13.7 Binding rule

| If | Then |
|----|------|
| Operational truth **changes** | The story **changes** |
| Operational truth **does not change** | The story **remains stable** |

### 13.8 Final principle (DS-009)

**Reality writes the story.**

**CartFlow only tells it.**

---

## 14. Success Criteria

Decision Storytelling succeeds when:

1. Merchant instantly understands **why this is today’s priority**.  
2. Merchant knows **exactly what to do** — or clearly understands that **no action is needed yet**.  
3. Navigation feels like **continuing one task**, not switching between pages.  
4. **No** internal system language is visible.  
5. The story remains **consistent** from Home through Validation **for the current decision identity**.  
6. Merchant feels: *“The platform understands what changed in my store today.”* — not *“The same dashboard every day.”* (**DS-009**)

---

## 15. Constitutional IDs

| ID | Title |
|----|--------|
| **DS-001** | Story Order Law — Priority → Observation → Meaning → Decision → Execution(if ready) → What happens next |
| **DS-002** | Story Completion Law — natural “what happens next”; no dead-end “back to summary” as the story close |
| **DS-003** | Story Ranking Law — Priority 1 / Priority 2 / Monitor / Later by operational importance |
| **DS-004** | Story Continuity Law — same story across Home → Workspace → Execution → Validation |
| **DS-005** | Story Identity Law — one recognizable narrative per decision |
| **DS-006** | Language Law — operations director voice; forbid engineer/system labels |
| **DS-007** | Engine Isolation Law — never expose architecture |
| **DS-008** | Cognitive Load Law — understand in ≤5 seconds |
| **DS-009** | Story Truth Law — reality writes the story; never predetermined / template-driven |

---

## 16. Approval checklist

- [ ] Mission + Constitutional Principles accepted  
- [ ] Story Order (DS-001) accepted — priority before action  
- [ ] Completion (DS-002) accepted  
- [ ] Ranking (DS-003) accepted — workload not categories  
- [ ] Continuity + Identity (DS-004 / DS-005) accepted  
- [ ] Language + Engine Isolation (DS-006 / DS-007) accepted  
- [ ] Cognitive Load (DS-008) accepted  
- [ ] **Story Truth (DS-009)** accepted — store reality writes the story  
- [ ] Quality Rules accepted as publish gate  
- [ ] **No UI / no implementation / no design / no copy polishing until approved**

---

## 17. STOP

**Frozen** in Decision Intelligence Framework V1.

No further Decision Storytelling constitutional amendments except the DIF exception gate.

Next work: implementation / UX refinement that **consumes** this law.
