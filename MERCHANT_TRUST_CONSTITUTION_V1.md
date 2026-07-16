# CartFlow Merchant Trust Constitution V1

**Status:** Proposed for Product + Architecture ratification  
**Date (UTC):** 2026-07-16  
**Authority:** Permanent product constitution for all merchant-facing speech  
**Scope:** When CartFlow may speak, stay silent, guide, or admit uncertainty  
**Out of scope:** Implementation · UI · engineering · investigations · Work Packages  

**Born from:** Reality Validation Lab V1 · Checkpoint V2 · Phase Review V1 · INV-001 · INV-002  

> CartFlow may know the truth internally.  
> This constitution governs whether the merchant may be told that CartFlow knows.

---

## Preamble

CartFlow does not ask the merchant to trust it.

CartFlow **earns** trust by showing only what evidence can support — and by remaining humble where evidence cannot.

**False confidence is a constitutional violation.**  
**Silent honesty is not a product failure.**  
**“We are still learning” is a legitimate product state — not a defect to hide.**

This document is binding on Home, Dashboard, Cart Workspace, Knowledge, Daily Brief, Timeline, WhatsApp surfaces, Widget merchant messaging, Store Setup, Navigation chrome that asserts status, and every future merchant-facing surface.

---

## I. Foundational question

### How does CartFlow earn trust instead of asking for trust?

| Asking for trust (forbidden pattern) | Earning trust (required pattern) |
|--------------------------------------|----------------------------------|
| “We understand your store” without evidence | Show what was observed, then name the pattern |
| “Preparing understanding…” as endless theatre | State learning stage + what event would change it |
| Recommendations before patterns stabilize | Withhold guidance until evidence threshold is met |
| Confidence labels without visible basis | Attach confidence to countable evidence |
| Empty queues that still demand attention | Never ask for attention when nothing qualifies |
| Setup incompleteness that denies lived history | Speak only about the store the merchant is actually viewing |

**Prime directive**

> CartFlow earns trust by **progressive disclosure of earned understanding** — never by claiming understanding in advance of evidence.

---

## II. Constitutional principles (MT-1…MT-12)

| ID | Principle | Meaning |
|----|-----------|---------|
| **MT-1** | Evidence Before Speech | CartFlow may assert only what current evidence supports for the **active merchant store context**. |
| **MT-2** | Identity Before Understanding | Understanding claims are invalid if the merchant is not viewing the store whose evidence is cited. |
| **MT-3** | Silence Is Legal | Withholding guidance is preferable to inventing guidance. |
| **MT-4** | Uncertainty Must Be Named | Unknown stays unknown (aligns CP-5 / PV-5). Soft apology that hides the reason is forbidden. |
| **MT-5** | Confidence Is Earned | Confidence language tracks evidence grade — never marketing ambition. |
| **MT-6** | Guidance Is a Privilege | Recommendations appear only after recognizing patterns with sufficient evidence. |
| **MT-7** | No Fake Intelligence | Loading, skeleton, and “brain” metaphors must not imply cognition that has not occurred. |
| **MT-8** | No Fear Sales | CartFlow must not manufacture urgency, shame, or threat to force action. |
| **MT-9** | One Store Story | All surfaces for a session must narrate the same store’s reality — or clearly label a different view. |
| **MT-10** | Progressive Trust | Speech rights expand only as Trust Ladder stage advances. |
| **MT-11** | Explainability Before Authority | If CartFlow guides, it must show why in merchant language. |
| **MT-12** | Partnership Over Performance | CartFlow is a careful partner in learning the business — not an oracle performing certainty. |

---

## III. Answers to the ten constitutional questions

### 1. When may CartFlow say: “We understand your store.”

Only when **all** are true:

1. Active store context is unambiguous (MT-2).  
2. Trust Ladder stage ≥ **T3 — Pattern Recognition** (see §IV).  
3. At least one **stable pattern** is evidenced (not a single anecdote).  
4. The claim is scoped (e.g. “we understand what is happening with abandoned carts this week”) — not global omniscience.  
5. Evidence can be shown on request or inline (counts, reasons, time window).

**Global** “we understand your store” (unscoped) requires stage **T4 — Guided Operations** or higher, with multiple domains evidenced (carts + recovery or purchase outcomes + at least one hesitation or return pattern).

### 2. When must CartFlow instead say: “We are still learning.”

When any of:

- Trust Ladder ≤ **T2 — First Signals**  
- Evidence grade is **Insufficient** or **Thin** (§VI)  
- Patterns are unstable or contradictory  
- Required domains for the claim are missing (e.g. visitors for traffic claims)  
- The merchant just connected / first opened with little activity  

“Still learning” must name **what is missing** when known (e.g. “waiting for more cart activity”).

### 3. When are recommendations allowed?

Only when:

- Stage ≥ **T3** for soft suggestions; ≥ **T4** for operational “do this next” guidance  
- A governed decision or published knowledge item exists (CartFlow does not invent recommendations in the UI)  
- Evidence grade ≥ **Adequate** for that recommendation’s domain  
- The recommendation is actionable by the merchant (or honestly marks “CartFlow is handling this”)  
- Confidence is not **Insufficient**

### 4. When must recommendations be withheld?

- Stage ≤ **T1**  
- Evidence grade **Insufficient** or **Thin** for that domain  
- Identity/context mismatch risk (MT-2)  
- Recommendation would require guessing (§X)  
- Attention/action framing would contradict empty queues (no “what needs attention?” with nothing to attend)  
- Setup-only merchants with no store activity — teach connection, do not prescribe commercial strategy

### 5. How much evidence is required before guidance?

Guidance requires **Adequate** evidence in the **same domain** as the guidance (see §VI). Cross-domain leaps (e.g. traffic advice from cart-only data) are forbidden.

### 6. What is sufficient evidence?

**Adequate** or higher (§VI): enough independent observations that a calm merchant would accept the pattern without special pleading — typically repeated events of the same kind inside a clear time window, not a lone outlier.

### 7. What is insufficient evidence?

**Insufficient:** no relevant events, or domain explicitly unsupported (e.g. visitor truth unavailable).  
**Thin:** some events exist but not enough to stabilize a pattern (sample too small, one-off, or window too short for the claim).

### 8. How should uncertainty be communicated?

- Prefer concrete gaps: “Not enough cart activity yet,” “Visitor data is not available,” “Still learning return patterns.”  
- Prefer learning stage labels from the Trust Ladder.  
- Never use uncertainty as decorative fog (“something may be wrong”).  
- Never use endless “preparing understanding” without a stage and a next-evidence cue.

### 9. How should confidence be communicated?

| Grade | Merchant language (examples) | May guide? |
|-------|------------------------------|------------|
| Insufficient | “Not enough evidence yet” | No |
| Thin | “Early signal — still learning” | No (observe only) |
| Adequate | “Based on recent store activity…” | Soft suggestion (T3+) |
| Strong | “Clear pattern in this period…” | Operational guidance (T4+) |
| Contested | “Signals conflict — we will not guess” | No |

Confidence must never outrun evidence grade.

### 10. What must never be guessed?

- Purchase attribution certainty without evidence  
- Visitor/traffic conclusions without visitor truth  
- “Customers feel X” without behavioral evidence  
- Fake recovery success  
- Store understanding claims for the wrong store context  
- Urgency (“act now or lose everything”) without a governed critical decision  
- Invented recommendations not derived from published knowledge/decisions  
- That silence means failure — silence may mean compliance with this constitution

---

## IV. Merchant Trust Ladder

Progression is **earned by evidence in the active store context**, not by time alone and not by UI completion checkboxes.

| Stage | Name | What CartFlow has earned | Speech rights |
|-------|------|--------------------------|---------------|
| **T0** | **Connected** | Store identity exists; merchant can open the product | Welcome; setup honesty; no store-understanding claims |
| **T1** | **Listening** | Instrumentation paths exist; awaiting first meaningful events | “We are listening for store activity”; never “we understand” |
| **T2** | **First Signals** | Some events arrived; no stable pattern yet | Describe raw activity carefully; “still learning”; no recommendations |
| **T3** | **Pattern Recognition** | Adequate evidence for ≥1 domain pattern | Name the pattern + show evidence; soft guidance only |
| **T4** | **Guided Operations** | Adequate/Strong evidence across the merchant’s active work domains | Prioritized next actions; Attention may ask for focus |
| **T5** | **Trusted Partnership** | Repeated correct guidance; merchant operational rhythm established | Broader “we understand how your store behaves in X”; still scoped, still evidenced |

**Rules**

- Stages do not skip because Setup checklists complete.  
- Stages can **regress** if evidence disappears or context changes.  
- Different domains may sit at different sub-levels; the **global** stage is the minimum across domains CartFlow is currently speaking about.  
- Claiming T4/T5 language at T0–T2 is a constitutional breach.

---

## V. First-open experience (time horizons)

For each horizon: what CartFlow knows / does not know / may say / must never say — assuming a typical new merchant unless noted.

### First minute

| | |
|--|--|
| **Knows** | Merchant identity; which store context is active; whether basic connection exists |
| **Does not know** | Patterns, recommendations, “how the store behaves” |
| **May say** | Welcome; what CartFlow will watch; honest Setup status; “listening” / T0–T1 language |
| **Must never say** | “We understand your store”; invent KPIs; demand attention with empty queues; endless “preparing understanding” without stage |

**Feel:** Orientation and calm partnership — not intelligence theatre.

### First hour

| | |
|--|--|
| **Knows** | Whether first events arrived; Setup progress; empty vs first-signal state |
| **Does not know** | Stable patterns (usually) |
| **May say** | “First activity received” or “still waiting for carts/reasons/messages”; T1–T2 |
| **Must never say** | Strategic recommendations; fake urgency; that lack of data is merchant failure |

**Feel:** “CartFlow is carefully learning my business.”

### First day

| | |
|--|--|
| **Knows** | Early activity counts if any; which domains remain empty |
| **Does not know** | Reliable “why customers leave” unless hesitation sample is Adequate |
| **May say** | Activity summary without overclaim; name missing domains |
| **Must never say** | Global understanding; Confident recovery ROI; Attention theatre |

**Feel:** Still learning — possibly first signals.

### First week

| | |
|--|--|
| **Knows** | Possibly first Adequate patterns (T3) if traffic warrants |
| **Does not know** | Long-cycle trends; monthly story |
| **May say** | One clear pattern with evidence; soft suggestion if earned |
| **Must never say** | “Fully understands”; contested attribution as fact |

**Feel:** First moment of “I understand my store better” **only if** a real pattern is shown.

### First month

| | |
|--|--|
| **Knows** | Multi-week patterns where evidence exists; operational priorities if T4 |
| **Does not know** | Domains still unsupported (e.g. visitors) remain unknown |
| **May say** | Guided operations language where earned; still-learning where not |
| **Must never say** | Omniscience; hide ongoing gaps behind confidence |

**Feel:** Partnership — mixed understanding and learning by domain.

---

## VI. Evidence grades (sufficient / insufficient)

| Grade | Definition | Speech |
|-------|------------|--------|
| **None** | Domain not instrumented or zero events | Stay silent on that domain or say unavailable |
| **Insufficient** | Too little to support any pattern claim | “Not enough evidence yet” |
| **Thin** | Early / unstable sample | “Early signal — still learning” |
| **Adequate** | Stable enough for a scoped pattern claim | Pattern + evidence; soft guidance (T3+) |
| **Strong** | Repeated, consistent, time-scoped | Operational guidance (T4+) |
| **Contested** | Contradictory signals | Refuse to guess; name the conflict |

**Sufficient evidence** = Adequate or Strong for the specific claim.  
**Insufficient evidence** = None, Insufficient, Thin, or Contested for that claim.

---

## VII. Product language principles

### Forbidden

- Artificial certainty (“always,” “customers hate X” without evidence)  
- Technical residue in merchant speech (pipeline jargon as the headline)  
- Hidden assumptions (implying the merchant sees the same store CartFlow analyzed internally)  
- Fear-based wording  
- Fake intelligence (“preparing understanding” as a substitute for a Trust Ladder stage)  
- Attention questions with empty answers  

### Required

- Evidence-first sentences  
- Humility when stage is low  
- Transparency about gaps  
- Progressive confidence  
- Explainability when guiding  
- Calm Arabic-first merchant tone (no panic)  

### Approved speech families

| Family | Example intent |
|--------|----------------|
| Listening | “CartFlow is watching for store activity.” |
| Learning | “We are still learning this part of your store.” |
| Observing | “Here is what happened in this period.” |
| Recognizing | “A pattern is becoming clear: …” |
| Guiding | “Based on this evidence, the next useful step is …” |
| Handling | “CartFlow is already following these cases.” |
| Uncertain | “We will not guess — here is what is missing.” |

---

## VIII. Knowledge constitution (trust layer)

Knowledge is not decoration. It is **earned speech about the store.**

| Topic | Rule |
|-------|------|
| **When Knowledge appears** | From T1 as a learning frame; content claims only from T2+ with matching evidence grade |
| **When it expands** | As domains reach Adequate; never by inventing cards to fill layout |
| **When it remains hidden** | Domains at None/Insufficient may show a single honest gap — not a wall of empty insight theatre |
| **Recommendation graduation** | Observation → evidenced pattern (T3) → soft suggestion → operational recommendation (T4) — never reverse |
| **Confidence evolution** | Tracks evidence grade; may only rise with new evidence; must fall if evidence thins |
| **Evidence presentation** | Merchant-visible counts, reasons, or time scope accompany any pattern claim |

Knowledge may show its **method** (how CartFlow thinks) at low stages.  
Knowledge may not show **conclusions** at low stages.

---

## IX. Empty states constitution

Empty pages must never feel abandoned — and must never feel omniscient.

| Situation | Required meaning | Forbidden meaning |
|-----------|------------------|-------------------|
| No data | “Nothing received yet for this store.” | “You are failing.” / fake sample data |
| Not enough evidence | “Still learning — need more of X.” | Fake charts / placeholder insights as facts |
| Learning in progress | Trust Ladder stage + next evidence cue | Infinite “preparing understanding” |
| Waiting for events | Name the event type awaited | Imply intelligence already formed |
| Waiting for purchases | Honest gap in purchase truth | Invented conversion stories |
| Waiting for patterns | Thin → learning language | Pattern language |

**Hard rule:** If CartFlow asks “What needs your attention now?”, the body must present attendable work or must not ask.

---

## X. Merchant experience outcomes

### When the merchant should feel: “I understand my store better.”

- Stage ≥ T3  
- At least one evidenced pattern is shown with explainability  
- Active store context matches the evidence  
- No contradictory empty Attention theatre  

### When the merchant should feel: “CartFlow is carefully learning my business.”

- Stages T0–T2  
- Or higher stages in domains still Thin/Insufficient  
- After first connect / first day with sparse activity  

### Never

- Feel “CartFlow understands everything” without evidence  
- Feel blamed for CartFlow’s missing instrumentation  
- Feel rushed by fake urgency  

Both “understand better” and “carefully learning” are **successful** product emotions.  
**False confidence is not.**

---

## XI. Product philosophy

| Pillar | Constitutional stance |
|--------|------------------------|
| **Truth** | Owned upstream; Trust Constitution never invents it |
| **Evidence** | The only currency that buys speech rights |
| **Knowledge** | Published understanding — projected, not performed |
| **Recommendations** | Privileges granted by evidence + stage |
| **Confidence** | A report of evidence grade, not a brand adjective |
| **Humility** | Default posture until T3+ |
| **Learning** | A first-class product state with dignity |
| **Merchant partnership** | CartFlow walks beside the merchant; it does not lecture from a pedestal |

---

## XII. Relationship to other constitutions

| Document | Relationship |
|----------|--------------|
| **Engineering Constitution** | Owns how systems are built; Trust owns what merchants may be *told*. MT aligns with Truth Before Intelligence (CP-1) and Unknown Stays Unknown (CP-5). |
| **Proof of Value Foundation** | Owns what may be commercially claimed; Trust owns day-to-day product speech. Evidence Before Claims (CP-2) is shared blood. |
| **Merchant Experience Foundation** | Owns how knowledge is composed across the workday; Trust constrains **when** experience may assert understanding. Experience expresses Trust; it never overrides it. |
| **Cart Workspace / Cart Page Constitutions** | Own cart-page decisions and density; Trust forbids attention/recommendation speech that violates evidence and stage. |
| **Knowledge Infrastructure / Knowledge constitutions** | Own production and routing of knowledge; Trust owns **graduation into merchant speech** (appear / expand / hide / recommend). |
| **Design / Experience Design Language** | Own visual and verbal craft; Trust owns which emotional claims are legal. Beauty must not smuggle false confidence. |
| **Merchant Intelligence Authority** | Owns intelligence grouping rules; Trust forbids intelligence theatre without published decisions/knowledge. |
| **Future Product Constitution** | Must inherit MT-1…MT-12; may refine ladder thresholds with amendment, not silent UI drift. |

**Conflict rule:** If a surface design wants stronger certainty than this constitution allows, **Trust wins** until an explicit amendment is ratified.

---

## XIII. Amendments

- Amendments require Product + Architecture approval.  
- Silent UI drift that violates MT-1…MT-12 is a constitutional breach.  
- Investigation findings (e.g. INV-002) may **motivate** amendments or implementations; they do not themselves change this text.

---

## XIV. Closing

CartFlow’s intelligence is worthless if the merchant cannot trust its voice.

This constitution exists so that every future surface asks first:

> Have we earned the right to say this?

If not — CartFlow stays silent, names the gap, and keeps learning.

That is how CartFlow becomes a platform merchants believe — not a dashboard that asks to be believed.

---

**STOP.**  
Do not begin INV-002 Architecture from this document.  
Await Product and Architecture ratification.
