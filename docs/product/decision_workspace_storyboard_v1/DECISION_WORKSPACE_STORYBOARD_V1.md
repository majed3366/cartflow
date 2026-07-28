# Decision Workspace Storyboard V1

**Status:** Product design only — cognitive journey  
**Date (UTC):** 2026-07-28  
**Surface:** Decision Workspace (`#workspace`)  
**Depends on:**  
- [`Decision Workspace Constitution V1`](../decision_workspace_constitution_v1/DECISION_WORKSPACE_CONSTITUTION_V1.md) (incl. Termination, Saturation, Executive Commitment Law)  
- [`Decision Workspace Information Budget V1`](../decision_workspace_information_budget_v1/DECISION_WORKSPACE_INFORMATION_BUDGET_V1.md)  
- Home Constitution V2 / Home Storyboard V1 (arrival context)  
- Product Constitution V1 §4.2 · Principle 7  

**Constraint:** Merchant journey only. **No UI. No wireframes. No layout. No cards. No colours. No implementation. No coding.**

**Workspace question (merchant’s job on arrival):**  
What decision should I make now, and why?

---

## Premise

The merchant must never feel they are reading a report.

The merchant must feel they are participating in a **two-minute executive decision meeting**.

| Meeting feeling | Report feeling (forbidden) |
|-----------------|----------------------------|
| “There is a decision I am committing to.” | “There is a document I should finish reading.” |
| Understand → Trust → Commit → Execute | Read → Read more → Scroll → Read again |

Duration target for the Primary meeting: **about two minutes** (orientation through commitment). Next Decisions appear only after that meeting closes mentally.

---

## Starting state — arrival from Home

The merchant arrives from Home.

Home already answered:

> What should I know?

**Cognitive carry-forward (already in their head):**

1. “Something needs my attention” (or calm — rare path into Workspace).  
2. Often a named thread (e.g. shipping / a product / communication) — **executive introduction only**.  
3. They chose Workspace to **decide**, not to be briefed again.

**Workspace must never repeat Home.**

It **continues the conversation** — from knowing → to committing.

**Forbidden on arrival:** Restating Home’s executive summary as a new opening speech.

---

## The Journey

### STEP 1 — Immediate Orientation (≤3 seconds)

**Cognitive event:** Commitment target locks before explanation.

Inside the merchant’s mind:

1. “This is the decision I am committing to.”  
2. “I know where the meeting starts.”  
3. Not yet: evidence, full why, or the action itself.

**Present:** Identity of the Primary Decision (commitment target).  
**Not yet:** Evidence. Explanations. Next Decisions. KPI context.

**Behavioural seed:**  
“I am in a decision meeting — not reading a report.”

**Budget echo:** ≤3s orientation (stricter than Home’s 5s glance; Information Budget ≤5s still bounds recognition).

---

### STEP 2 — Diagnosis

**Cognitive event:** Reality named.

Inside the merchant’s mind:

1. They can answer: **What is happening?**  
2. They still must **not** be pushed to “what should you do?” — that comes at Commitment.  
3. Diagnosis continues Home’s thread without reprinting Home’s line.

**Present:** What is happening.  
**Not yet:** Recommended action as the lead.

**Behavioural seed:**  
“I understand the situation CartFlow is putting on the table.”

---

### STEP 3 — Reasoning

**Cognitive event:** Belief becomes legible.

Inside the merchant’s mind:

1. They can answer: **Why does CartFlow believe this?**  
2. Only the reasoning required for trust — not every observation.  
3. Soft, vague, or technical “model said so” language fails this step.

**Present:** Necessary why.  
**Not:** Exhaustive observation dump. Executive essays.

**Behavioural seed:**  
“This isn’t random — there’s a reason to take it seriously.”

---

### STEP 4 — Evidence

**Cognitive event:** Confidence strengthens without overwhelm.

Inside the merchant’s mind:

1. Evidence supports the Diagnosis (and only that).  
2. Confidence goes up — cognitive load does not.  
3. Raw logs, timelines, and technical IDs feel like the wrong meeting.

**Present:** Minimum evidence for confidence.  
**Not:** Evidence walls. Duplicate proof of the same fact. Duplicated diagnosis under another label.

**Behavioural seed:**  
“I trust this enough to decide.”

---

### STEP 5 — Business Consequence

**Cognitive event:** Urgency becomes personal and commercial.

Inside the merchant’s mind:

1. They can answer: **What happens if I ignore this?**  
2. Urgency is understood — not as panic chrome, as business stake.  
3. “Interesting to know” without consequence fails this step.

**Present:** Cost of inaction / business impact.  
**Not:** Generic urgency badges without stake.

**Behavioural seed:**  
“Leaving this alone has a cost I accept or reject deliberately.”

---

### STEP 6 — Commitment

**Cognitive event:** One committed business action.

Inside the merchant’s mind:

1. Exactly **ONE** action is on the table.  
2. They leave **mentally committed** — not merely informed.  
3. Not more knowledge. Not more reports. Not more ideas.  
4. Honest insufficient evidence may commit them to **wait / not act yet / gather what is missing** — still one commitment.

**Present:** The single Recommended Action + expected outcome of acting.  
**Not:** Competing CTAs. “Review / Check / Consider” as the meeting climax.

**Behavioural seed (Executive Commitment Law):**  
“I know what I am committing to do.”

**Meeting close:** The two-minute Primary meeting ends here.

---

### STEP 7 — Next Decisions (only after commitment)

**Cognitive event:** Queue awareness without competition.

Inside the merchant’s mind:

1. “I’ll do these after finishing the first.”  
2. Remaining decisions do **not** reopen the Primary meeting.  
3. They never feel like a second equal stack of reports.

**Present:** Limited Next Decisions (Information Budget: ≤3).  
**Not:** Competing primaries. Long lists. Re-explaining the Primary.

**Behavioural seed:**  
“There is a queue — but I already committed to the first.”

---

## Journey map (cognitive only)

```
Home: What should I know?
        ↓ (continue — never restart)
Workspace STEP 1: This is the decision I commit to (≤3s)
        ↓
STEP 2: What is happening? (Diagnosis)
        ↓
STEP 3: Why believe this? (Reasoning)
        ↓
STEP 4: Evidence that strengthens confidence
        ↓
STEP 5: What if I ignore this? (Consequence)
        ↓
STEP 6: One action — Commit
        ↓
STEP 7: Next Decisions (after commitment only)
        ↓ (continue — never restart)
Products / Carts / Communication (execution owners as needed)
```

Success path:

```
Understand → Trust → Commit → Execute
```

Failure path (forbidden experience):

```
Read → Read more → Scroll → Read again
```

---

## Transitions — continuous conversation

No page may **restart** the conversation. Each surface continues the prior altitude.

| From | To | Continuation meaning |
|------|----|----------------------|
| **Home** | **Workspace** | From “what I should know” → “what I commit to now, and why.” Never re-brief the Home summary. |
| **Workspace** | **Products** | From committed product/pricing/catalog decision → product depth / execution of that commitment. |
| **Products** | **Carts** | From product-level commitment → cart / recovery operational execution when that is the next work. |
| **Carts** | **Communication** | From cart ops → customer contact execution when communication is the committed next step. |

Workspace may deep-link into Products / Carts / Communication / Settings **as the committed action’s execution**, not as a tour of reports.

If the merchant returns to Workspace mid-queue, the story resumes at **Active Primary** (Termination Law) — it does not replay Home.

---

## Forbidden (journey killers)

These break the meeting and recreate a report:

- Repeated diagnosis  
- Repeated Home summary  
- KPI walls  
- Executive essays  
- Duplicated recommendations  
- Technical language  
- Implementation details  

Also forbidden in journey timing:

- Evidence or explanations before orientation (STEP 1)  
- Recommended action before Diagnosis / Reasoning / Evidence / Consequence  
- Next Decisions competing with Primary before Commitment  

---

## Storyboard success

| Pass | Fail |
|------|------|
| Feels like a ~2-minute executive decision meeting | Feels like reading a report |
| Continues Home’s conversation | Restarts with Home’s summary |
| Understand → Trust → Commit → Execute | Read → Read more → Scroll → Read again |
| One commitment | More knowledge / ideas / competing actions |
| Next only after commit | Equal stack of decisions from the start |

---

## Explicit stop

**Deliverable complete for Decision Workspace Storyboard V1.**

- Merchant journey only  
- No UI  
- No wireframes  
- No implementation  

**STOP.**
