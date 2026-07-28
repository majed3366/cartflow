# Decision Workspace Information Budget V1

**Status:** Product research only — awaiting approval  
**Date (UTC):** 2026-07-28  
**Surface:** Decision Workspace (`#workspace`)  
**Basis:** [`Decision Workspace Constitution V1`](../decision_workspace_constitution_v1/DECISION_WORKSPACE_CONSTITUTION_V1.md) · Product Constitution V1 §4.2 · Principle 7 · Home Information Budget V1 (parallel method, different surface)  
**Constraint:** Information budget only. **No Storyboard. No UI. No implementation. No coding.**

---

## Mission (locked for budgeting)

Decision Workspace is **not** a report.

Decision Workspace is an **executive meeting**.

| The merchant must feel | The merchant must not feel |
|------------------------|----------------------------|
| “There is a **decision** waiting for me.” | “There is a **report** waiting to be read.” |

Every budget rule below exists to protect that feeling.

---

## The Question (locked)

> What decision should I make now, and why?

Any element that does not advance this answer is **out of budget**.

---

## Executive Information Value Law

**Constitutional for this surface.** Same test as Home; different owner depth.

A piece of information earns space on Decision Workspace **only if it changes the merchant’s next decision**.

| The question is NOT | The question IS |
|---------------------|-----------------|
| “Is this correct / interesting / complete?” | “Will this change what the merchant decides next?” |

If **NO** → it belongs **somewhere else** (Home teaser, Carts, Communication, Products, Settings, Admin) — or it is deleted from merchant surfaces entirely.

### Test before paint

For every candidate sentence, number, panel, or link on Workspace:

> If removing it would not change Understand → Trust → Decide → Act, it is over budget.

---

## Budget law

Workspace may spend attention only on information that:

0. Satisfies the **Executive Information Value Law**, and  
1. Serves the **single page question**, and  
2. Fits the **Primary / Next / Wait** hierarchy (Constitution §§5, 11–13), and  
3. Fits the **reading budget** and **action budget** below, and  
4. Is classified **KEEP / REWRITE / REMOVE / MERGE / MOVE** — nothing is automatically allowed.

Anything that fails (0)–(4) is **out of budget**.

---

## 1. Executive Information Budget

### 1.1 What may occupy the page (content classes)

| Slot | Class | Budget role | Dominates? |
|------|-------|-------------|------------|
| P0 | **Page purpose** (the Question, once) | Orients the meeting | No — chrome |
| P1 | **Primary Decision** (full structure §1.2) | The meeting agenda item | **Yes — must dominate** |
| P2 | **Next Decisions** (limited queue) | “After I finish the first…” | No — secondary |
| P3 | **Domain presence** (optional, non-KPI) | “Is there a decision in Shipping / Pricing / …?” — not counts | No |
| — | Everything else | **Waits** or **lives on another page** | Forbidden on paint |

Silence is allowed: empty domains and empty next-queue slots must not be filled with reports.

### 1.2 Primary Decision — internal information budget

The Primary Decision may spend space **only** on the constitutional structure, in order:

| Step | Allowed content | Budget note |
|------|-----------------|-------------|
| 1 Diagnosis | What is happening (one clear statement) | Opens the meeting |
| 2 Why | Why CartFlow believes this (short) | Trust — not essay |
| 3 Evidence | Minimum evidence for confidence | Not raw logs |
| 4 Business Impact | What happens if nothing changes | Decision stake |
| 5 Recommended Action | **Exactly one** next action | Action budget |
| 6 Expected Outcome | What improvement is expected | Closes the case for acting |

No parallel panels that restate Diagnosis / Evidence / Recommendation under another label.

### 1.3 Five-second recognition

Within **≤5 seconds**, the merchant must know:

1. There is a decision waiting  
2. What the Primary Decision is (Diagnosis-level)  
3. Where to start (Primary dominates)

If not → the page has failed the information budget (and the Decision Law).

---

## 2. Maximum number of visible decisions

| Limit | Value | Rule |
|-------|-------|------|
| **Primary decisions visible** | **1** | Hard maximum. Never competing primaries. |
| **Next decisions visible** | **≤3** | Soft maximum for the secondary queue. Prefer **1–2** when Primary is heavy. |
| **Total decision cards competing for attention** | **≤4** | 1 Primary + ≤3 Next |
| **Everything else** | **0 on paint** | Candidate / Waiting / Resolved / Archived / lower priority — **wait** (Termination + Saturation Laws) |
| **Domain chips / rows that are not decisions** | **0 as KPI wall** | Domain may show presence of a decision, not volume |

**Why ≤3 Next:** Saturation Law — if ten are valid, CartFlow still prioritizes. A long “next” list recreates the report feeling.

**Why not “show all valid”:** Validity ≠ entitlement to screen space.

---

## 3. Maximum reading budget

Reading the page must take **less effort than executing the decision**.

If reading becomes the task, the page has failed.

| Budget | Value | Definition |
|--------|-------|------------|
| **Glance (recognize Primary)** | **≤5 seconds** | Know “start here” + Diagnosis gist |
| **Primary Decision read-through** | **≤60 seconds** | Diagnosis → Why → Evidence → Impact → Action → Outcome |
| **Full page including Next queue** | **≤90 seconds** | Primary + skim of Next titles only |
| **Evidence lines in Primary** | **≤5 short lines / bullets** | Minimum for confidence; expand elsewhere only if needed later (not this pack) |
| **Why block** | **≤3 short sentences** | Belief rationale, not research paper |
| **Impact block** | **≤2 short sentences** | Stake if nothing changes |
| **Outcome block** | **≤2 short sentences** | Expected improvement |

**Failure modes (over reading budget):**

- Essay-length Why  
- Evidence dumps / timelines / logs  
- Restating Home’s executive line then restating it again as Diagnosis  
- Equal-weight stack of four “full” decisions  

---

## 4. Executive attention budget

Attention is spent in layers. Lower layers may not steal attention from higher layers.

| Priority | Attention share (target) | May interrupt Primary? |
|----------|--------------------------|------------------------|
| **1 — Primary Decision** | **~70–80%** of first viewport / first meeting attention | N/A — it *is* the focus |
| **2 — Single Recommended Action** | Embedded in Primary; visually unmistakable | Must not compete with a second CTA |
| **3 — Next Decisions** | **~15–25%** — titles + one-line stakes only | No |
| **4 — Domain presence / navigation** | **≤5%** — optional | No |
| **5 — Waiting / Archived / Reports** | **0%** on this page’s primary attention | Forbidden |

### Attention rules

- Primary must **dominate** the first viewport.  
- Next Decisions must feel like a **queue after**, not a second meeting.  
- No KPI wall, ops statistics strip, or technical banner may sit above or beside Primary as a peer.  
- Home already spent executive introduction attention — Workspace must not re-spend it (Principle 7).

---

## 5. Action budget

| Limit | Value | Rule |
|-------|-------|------|
| **Actions per decision** | **Exactly 1** clear Recommended Action | Never multiple competing actions |
| **Primary CTAs on page** | **1** | The Primary’s Recommended Action |
| **Secondary CTAs** | **0 competing** | Next items may be “open when ready” affordances only — not parallel “do this now” buttons fighting Primary |
| **Deep links to Carts / Communication / Settings** | Allowed **as the one action** or as execution after decide | Must not become a menu of ops tasks |

Starting a decision with “Review… / Check… / Improve… / Consider…” is out of budget (Constitution §7) — those are not clear single actions after Diagnosis.

---

## 6. Classification matrix — Keep / Rewrite / Remove / Merge / Move

Nothing is automatically allowed. Every visible class must be classified.

### 6.1 KEEP (in budget — if Value Law passes)

| Element | Why KEEP |
|---------|----------|
| Page question (once) | Locks the meeting agenda |
| One Primary Decision block (structure 1–6) | Dominates; answers the question |
| ≤3 Next Decision **titles** (+ optional one-line stake) | Queue after Primary |
| Minimum evidence for confidence | Enables Trust |
| Exactly one Recommended Action + Expected Outcome | Enables Decide → Act |
| Honest insufficient / conflicting evidence states | Prevents false action |
| Domain presence when it means “decision exists here” | Navigation of decision domains — not KPIs |

### 6.2 REWRITE (same owner, wrong form)

| Element | Rewrite toward |
|---------|----------------|
| Home-duplicated executive headline | Explanation under Diagnosis / Why — not a second introduction |
| Soft openings (“Review shipping…”) | Diagnosis-first language |
| Long evidence / proof essays | ≤5 confidence bullets |
| Multiple CTAs (“Fix cost” + “Open carts” + “See report”) | Exactly one Recommended Action |
| Domain rows with counts (“Shipping · 12”) | “Shipping — decision waiting” / silence |
| Equal card stack of decisions | One Primary + limited Next queue |
| Technical confidence (“87% model”) | Merchant trust language tied to Evidence |
| “Open recommendations” that never end | Terminal lifecycle language (Resolved / Waiting / Archived…) |

### 6.3 REMOVE (fails Value Law or Constitution)

| Element | Why REMOVE |
|---------|------------|
| Duplicated diagnosis (same meaning twice) | Extraneous load; report smell |
| Duplicated evidence | Reading becomes the task |
| Duplicated recommendations | Competing actions |
| KPI walls / metric grids | Not a decision meeting |
| Operational statistics (cart counts, message volumes as page job) | Carts / Communication own ops |
| Technical wording / implementation details | Admin / Dev; not merchant decision |
| Raw logs, timelines as primary content | Report, not meeting |
| Permanent open recommendation lists | Violates Termination / “no forever” |
| Analytics / dashboard chrome | Wrong surface identity |
| Second Primary Decision | Hierarchy violation |

### 6.4 MERGE

| Elements often separate today | Merge into |
|-------------------------------|------------|
| Diagnosis + synonym hero + status tag saying the same thing | One Diagnosis statement |
| Why + Evidence overlapping sentences | Why = belief; Evidence = proof lines only |
| Impact + Outcome fluff | Impact = if nothing changes; Outcome = if you act |
| Multiple “related” recommendations | One Recommended Action; rest Wait or Next |

### 6.5 MOVE TO ANOTHER PAGE

| Element | Move to |
|---------|---------|
| Executive one-line “Shipping needs attention” without explanation | Already Home’s job — do not re-host; Workspace explains |
| Cart tables / recovery queues | Carts |
| Message history / delivery logs | Communication |
| Product funnels / catalogs | Products |
| Connection / API / configuration | Settings |
| Situation IDs, registry keys, simulation IDs, scoring math | Admin / Dev |
| Full historical report of all past decisions | Archive view later (not Primary space) — out of this budget’s paint |
| Collector / evidence-gap engineering tasks | Never merchant Workspace |

---

## 7. Forbidden (hard)

Do **not** show on Decision Workspace (information budget):

- Duplicated diagnosis  
- Duplicated evidence  
- Duplicated recommendations  
- KPI walls  
- Operational statistics (as the page’s job)  
- Technical wording  
- Implementation details  

These are **automatic REMOVE** unless a future amendment reclassifies them with Value Law proof (unlikely for KPI walls / technical / implementation).

---

## 8. Budget summary card (norms)

| Budget dimension | Norm |
|------------------|------|
| **Visible Primary decisions** | **1** |
| **Visible Next decisions** | **≤3** (prefer 1–2) |
| **Total decision attention objects** | **≤4** |
| **Recommended actions per decision** | **1** |
| **Primary CTAs on page** | **1** |
| **Glance / recognize Primary** | **≤5 s** |
| **Primary read-through** | **≤60 s** |
| **Full page skim** | **≤90 s** |
| **Evidence lines (Primary)** | **≤5** |
| **Attention share — Primary** | **~70–80%** |
| **Classification** | Every element: KEEP / REWRITE / REMOVE / MERGE / MOVE |

---

## 9. Success criteria for this budget

The budget succeeds when Decision Workspace feels like an **executive meeting** with a **decision waiting**, and fails when it feels like a **report to read**.

Per **Executive Commitment Law** (Decision Workspace Constitution): the merchant must leave with **one clear commitment** — one committed business action — not more knowledge, reports, or ideas.

| Pass | Fail |
|------|------|
| Merchant knows Primary in ≤5 s | Merchant browses equal cards |
| Reading effort < execution effort | Reading is the work |
| One action → one commitment | Competing actions / more ideas |
| Limited Next; rest wait | Infinite or long decision list |
| Explain Home; don’t repeat Home | Duplicate executive introduction |
| Leaves committed | Leaves only more informed |

---

## 10. Explicit stop

**Deliverable complete for Decision Workspace Information Budget V1.**

- No Storyboard  
- No UI  
- No implementation  

Await approval before any Workspace redesign or Storyboard work.

**STOP.**
