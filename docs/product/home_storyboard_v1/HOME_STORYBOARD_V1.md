# Home Storyboard V1

**Status:** Approved inputs ready — final gate before Home Constitution V2  
**Date (UTC):** 2026-07-27  
**Depends on:**  
- [`HOME_INFORMATION_BUDGET_V1.md`](../home_information_budget_v1/HOME_INFORMATION_BUDGET_V1.md) (incl. Executive Information Value Law)  
- [`HOME_SENTENCE_AUDIT_V1.md`](../home_sentence_audit_v1/HOME_SENTENCE_AUDIT_V1.md)  
- [`EXECUTIVE_HOME_RESEARCH_V1.md`](../executive_home_research_v1/EXECUTIVE_HOME_RESEARCH_V1.md)  

**Constraint:** Cognitive journey only. No UI. No layout. No cards. No colours. No implementation. No Home Constitution V2 in this deliverable.

**Home question (merchant’s job on arrival):**  
ماذا يجب أن أعرف الآن عن متجري؟

---

## Premise

In the first 30 seconds the merchant is not “browsing analytics.”  
They are forming a single executive stance:

> Is my store OK right now — and if not, what do I do next, and where?

Everything they understand must change (or deliberately hold) that stance.  
Anything that does not change what they do next is out of the journey.

---

## 0–5 seconds — What does the merchant understand immediately?

**Cognitive event:** Orientation + store state at a glance.

Inside the merchant’s mind:

1. “I am looking at **my store right now** — not history, not settings, not a report.”  
2. “The store is in one clear condition: calm / opportunity / needs me / urgent / not enough to judge.”  
3. If urgent or constrained: “Something is blocking me from running recovery properly.”  
4. If calm: “I do not need to intervene yet.”

**What must already be true in their head:**

- One health stance (not a list of metrics).  
- No need to decode counts, confidence, or technical status.  
- No second competing “main story.”

**Behavioural seed planted:**  
Either *stay calm* or *I will need to act* — not yet which page.

---

## 5–10 seconds — What attracts attention?

**Cognitive event:** The single sharpest interrupt wins attention.

Inside the merchant’s mind:

1. Attention locks on **one** thing that would change what they do next — usually:  
   - a blocked customer path (e.g. communication constrained), or  
   - a named product / checkout move that deserves a decision, or  
   - a calm confirmation that recovery is operating normally.  
2. Secondary domain signals (product / carts / communication) may register as **peripheral awareness** only if they carry a next-move meaning — never as bare inventory (“how many carts”).  
3. Anything that feels like reporting, history, or explanation is ignored or felt as noise.

**What attracts attention (allowed):**

- A directive or named subject: “review checkout…”, “Raven needs attention”, “communication is blocked”, “recovery is normal.”  

**What must not win attention:**

- Headcounts, timelines, confidence, operational history, raw observations.

**Behavioural seed strengthened:**  
“This is the thing that matters *now*.”

---

## 10–15 seconds — What becomes clear?

**Cognitive event:** Cause-of-attention resolves into meaning without full explanation.

Inside the merchant’s mind:

1. They can finish the sentence:  
   - “My store is ____, and the reason I’m looking here is ____.”  
2. They know whether today’s issue is primarily:  
   - a **decision** (judgment / prioritization), or  
   - a **domain follow-up** (carts ops / communication unblock / product signal).  
3. They still do **not** need evidence, alternatives, or impact math — only clarity of *what kind of next step* this is.  
4. Calm path: “Nothing is asking me for a decision; I can leave or skim once.”

**What becomes clear:**

- Health + the one primary executive thread are coherent (no calm-vs-urgent contradiction).  
- Domain teasers, if present, support that thread rather than starting a second story.

**Behavioural seed:**  
“I know what kind of work this is.”

---

## 15–20 seconds — What decision has already formed?

**Cognitive event:** Choice has formed — even if the merchant has not clicked yet.

Inside the merchant’s mind, one of these stances has already crystallized:

| Stance | Decision already formed |
|--------|-------------------------|
| **Act on the primary decision** | “I will open the place that explains and owns this decision.” |
| **Unblock operations** | “I will open the place that lets me fix the constraint (e.g. missing contact / carts that cannot be reached).” |
| **Inspect the named product signal** | “I will open product/decision ownership for that subject — not dig a table on Home.” |
| **Hold / no intervention** | “I will not chase carts or messages today; Home told me recovery is normal.” |

Rules for this moment:

- Only **one** primary decision stance.  
- Secondary awareness does not create a second equal decision.  
- “I need more proof” is **not** a Home decision — that impulse belongs after they leave Home.

**Behavioural seed:**  
“I already know what I’m going to do next.”

---

## 20–30 seconds — Which page should the merchant naturally open next? Why?

**Cognitive event:** Destination feels inevitable — not a menu search.

### Default destinations (by stance)

| If the formed decision was… | Natural next page | Why that page (constitutional owner) |
|-----------------------------|-------------------|--------------------------------------|
| Understand / take the top business decision | **Workspace** | Only Workspace owns why, evidence, impact, and the recommended action in depth |
| Unblock customer reach / communication constraint | **Communication** first, or **Carts** when the action is “affected customers” | Communication owns communication facts; Carts owns the operational list of affected carts/customers |
| Follow cart operational follow-up (no new business thesis) | **Carts** | Carts owns per-cart status and next operational action |
| Pursue a named product attention signal without deciding yet | **Products** (or Workspace if the signal *is* the primary decision) | Products owns product truth; Workspace owns decision explanation |
| Store not ready / connection incomplete | **Settings** (setup) | Settings owns working configuration |
| Hold / calm | **Stay or leave** — no forced page | Calm is a valid executive outcome; opening Workspace “just in case” is failure of the briefing |

### Why not elsewhere

- Opening **Workspace** for a bare cart count → wrong owner.  
- Opening **Carts** to “understand the decision” → explanation will be missing.  
- Opening **Products** for evidence/confidence → belongs in Workspace.  
- Staying on Home to read more explanation → Home overspent its budget.

**End state at 30 seconds:**

The merchant can say, without help:

1. What my store’s condition is.  
2. What (if anything) I will do next.  
3. Which page owns that next step — and they are already moving there (or deliberately not moving).

---

## Journey invariants (must hold every visit)

1. **One question** drives the 30 seconds — not many.  
2. **One primary thread** of attention — not a portfolio of equals.  
3. **Calm is allowed** — silence can change behaviour (no chase today).  
4. **Explanation never finishes on Home** — unfinished curiosity pulls to the owner page.  
5. **Counts and history never form the decision** — only executive meaning does.  
6. **Desktop and Mobile share this same mental journey** — only pacing of reading may differ, not the conclusion.

---

## Failure modes (journey broke)

| If at 30s the merchant… | The storyboard failed |
|-------------------------|------------------------|
| Still asks “what should I look at?” | No single attention thread |
| Opens a page “to find out what’s going on” without a stance | Home did not form a decision |
| Feels calm while knowing something urgent exists | Health and primary thread contradicted |
| Starts reading for proof/confidence on Home | Evidence leaked into the briefing |
| Remembers a number but not a next move | Value Law violated |

---

## Relationship to next artifact

This storyboard is the **final cognitive input** for Home Constitution V2.

Constitution V2 may only encode laws that make this 0–30s journey reliably true.  
It must not encode layout, visual design, or new surfaces.

---

## STOP

- Deliverable is **only** this document.  
- **Do not** write Home Constitution V2 until this storyboard is explicitly approved.  
- **Do not** implement or redesign Home from this document alone.

---

*End of Home Storyboard V1*
