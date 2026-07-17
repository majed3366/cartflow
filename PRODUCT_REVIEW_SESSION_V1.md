# Product Review Session V1

**Document type:** Product review (not engineering, not architecture)  
**Status:** **Product decisions recorded**  
**Input:** [`MERCHANT_REALITY_VALIDATION_V1.md`](MERCHANT_REALITY_VALIDATION_V1.md) — verdict **NOT READY**  
**Evidence:** [`docs/architecture/merchant_reality_validation_v1/mv1_session_capture.json`](docs/architecture/merchant_reality_validation_v1/mv1_session_capture.json) · [`mv1_home_sections.json`](docs/architecture/merchant_reality_validation_v1/mv1_home_sections.json)  
**Defects in scope:** MV1-D01 … MV1-D12 only  
**Review date (UTC):** 2026-07-17  

> **Mission:** Transform CartFlow from **NOT READY** to a product that a merchant can trust after one session — by deciding correct merchant experience, not by inventing new issues.  
> **Review rule:** Product experience only. No implementation. No architecture. No code.

**STOP:** No engineering tasks. No UI redesign in this session. Await Product Owner approval before opening the implementation backlog.

---

## Executive Summary

### Final decision

# READY FOR IMPLEMENTATION

### One-sentence verdict

MV-1 proved the store truth is reachable and Knowledge is honest; this review **locks the merchant product contract** for Home, Knowledge, Daily Brief, and Timeline — every recorded defect now has desired behavior, acceptance criteria, and measurable READY outcomes — so product decisions are complete and implementation may open **only after Product Owner approval**.

### Scope of truth used

| Source | Used |
|--------|------|
| MERCHANT_REALITY_VALIDATION_V1.md | Yes — scores, walkthrough, trust, defect register |
| Session evidence pack | Yes — counts, copy, empty sections, badges |
| Home sections capture | Yes — attention/understanding empty states |
| Screenshots | **None in evidence pack** — review uses recorded merchant-visible payloads only |
| Hypothetical issues | **Excluded** |

### Product problem (root)

CartFlow **knows** the store in Knowledge, then **mis-speaks** that knowledge on Home / Daily Brief / Timeline: priorities inverted, understanding silenced, duplicates and placeholders, wrong cart count chrome, Timeline not a story.

### Product goal (READY)

After one attached merchant session on the same evidence shape as MV-1 (5 carts without phone, demand up 5→0, thin recovery/visitor data), a merchant must be able to answer yes to:

> “I understand my store better after opening CartFlow.”

Observable proof: Home answers the six merchant questions; Attention and Understanding are non-empty when Knowledge has the matching facts; Brief and Timeline agree with Home without duplicates or placeholders; cart chrome matches cart truth.

---

## Product Findings

### Finding F1 — Priority inversion (trust breaker)

**Evidence:** Attention items = 0; empty message says nothing needs attention; while-away/achievements include «5 حالات — السبب محفوظ — بانتظار رقم العميل…».  
**Root product problem:** Blocked recovery is treated as completed background work, not today’s ask.  
**Merchant effect:** Merchant leaves Home believing they can ignore the store.

### Finding F2 — Understanding silence (trust breaker)

**Evidence:** Knowledge has 6 insights with full Arabic explanations; Home `store_understanding.items = []` with “لا توجد استنتاجات كافية بعد”.  
**Root product problem:** Home denies understanding that Knowledge already holds.  
**Merchant effect:** Surfaces disagree; merchant trusts neither.

### Finding F3 — Speech collapse and duplication

**Evidence:** 13 while-away / achievement items; titles repeat; detail is «ملخص Knowledge Layer…» or «—»; Knowledge messages are not shown on Home/Brief/Timeline.  
**Root product problem:** Downstream surfaces strip explanation and double-list the same fact.  
**Merchant effect:** Looks unfinished or automated spam.

### Finding F4 — Operational chrome mismatch

**Evidence:** Knowledge `cart_count = 5`; quick-nav active carts `badge_count = 0`.  
**Root product problem:** Navigation count does not match store activity the merchant just read about.  
**Merchant effect:** Immediate distrust of every number on Home.

### Finding F5 — Timeline is not a story

**Evidence:** Activity Timeline = same while-away list; one recovery-truth `scheduled` event exists but is not narrated; event time `2026-07-17` vs brief day `2026-05-04` unexplained.  
**Root product problem:** Timeline repeats Brief noise instead of sequencing what happened to carts.  
**Merchant effect:** No continuity; unexplained time jump.

### Finding F6 — Knowledge is the reference product surface

**Evidence:** Knowledge alone passes observation / evidence / confidence / insufficient-evidence checks; no unsupported recommendations.  
**Root product problem:** Not a Knowledge defect — inheritance failure.  
**Merchant effect:** Merchant must leave Home to understand the store.

### Finding F7 — Thin-data framing is wrong on Home/Brief

**Evidence:** Insufficient-sample / unavailable-data insights appear as “while away / achievements completed.”  
**Root product problem:** Limits are framed as wins.  
**Merchant effect:** Merchant thinks CartFlow finished work it did not do.

---

## Per-Surface Review

### Home

#### What Home must always answer

On every open (same day / brief date the merchant sees), Home must make these six answers **visible without opening Knowledge**:

| # | Question | Observable answer form |
|---|----------|------------------------|
| H1 | What is happening today? | Dated greeting + short while-away summary of real completed or monitored activity (or honest empty) |
| H2 | What requires my attention? | Attention list; empty **only** when no blocked/actionable store fact exists |
| H3 | What improved? | At least one understanding or while-away card with a before/after or direction when Knowledge has a trend with numbers |
| H4 | What became worse / is blocked? | Attention or understanding card when recovery is blocked or health is poor |
| H5 | What evidence supports this? | Merchant-readable detail with counts or case counts — never «ملخص…» / «—» |
| H6 | What should I do next? | At least one attention item with a clear next step when blocked recovery exists |

#### What Home must never say

| Forbidden when… | Forbidden speech |
|-----------------|------------------|
| Any carts are blocked waiting for contact (MV-1: 5) | «لا أمور تتطلب انتباهك الآن» / calm attention empty |
| Knowledge has ≥1 insight with confidence ≠ empty and a merchant-readable message | «لا توجد استنتاجات كافية بعد» as the only understanding content |
| A claim is shown | Detail that is only «ملخص Knowledge Layer للفترة المحددة» or «—» |
| Carts exist on the store the merchant is viewing | Active-carts badge `0` |
| Insight is “insufficient / unavailable” | Framed as “completed while you were away” win |

#### What Home must inherit from Knowledge

| Inherit | From MV-1 Knowledge |
|---------|---------------------|
| Explanatory sentence | Full insight `message` (e.g. 5 vs 0 demand; most carts without phone) |
| Confidence honesty | Show or preserve that evidence is high / low / insufficient — do not upgrade |
| Counts | cart_count, phones, trend deltas used in the message |
| Insufficient-evidence stance | Keep “we cannot conclude yet” — do not invent actions |

#### What Home must summarize

- Today’s attention (max few items; MV-1 shape: contact gap first).  
- Today’s store understanding (max few cards; MV-1 shape: demand up + store health / contact gap).  
- While-away: only true completions or calm monitoring — not the full Knowledge dump.

#### What Home must leave to other surfaces

| Leave to | Content |
|----------|---------|
| Knowledge | Full insight set, metrics table, confidence pedagogy, long explanations |
| Daily Brief | Day package / printable day review consistent with Home |
| Timeline | Ordered cart/recovery story and evidence continuity |
| Carts workspace | Per-cart actions after Home names the priority |

#### Home READY (observable)

1. With MV-1 evidence shape: Attention count ≥ 1 and includes the 5-case contact wait.  
2. Understanding count ≥ 1 and includes demand trend **or** store health with Knowledge’s numbers/message.  
3. No duplicate titles in while-away for the same insight.  
4. No placeholder detail strings.  
5. Active-carts badge equals Knowledge cart_count for that session (5).  
6. Greeting shows a non-empty date matching brief_date the merchant sees (`2026-05-04` in MV-1).  
7. Attention empty message appears **only** when obtain-contact count = 0 and no other attention-class fact exists.

---

### Knowledge

#### What belongs in Knowledge

- Full observations with messages, confidence, sample size.  
- Explicit insufficient / unavailable evidence.  
- Metrics that prove the messages (cart_count, phones, recovery counts, visitor availability).  
- No unsupported recommendations (keep MV-1 pass).

#### What should move to Home

| Knowledge fact (MV-1) | Home destination |
|-----------------------|------------------|
| obtain-contact / 5 carts no phone / store health “most carts without phone” | **Attention** (primary) + short understanding support |
| traffic_cart_demand_trend (5 vs 0, up) | **Understanding** (improved / direction) |
| insufficient / unavailable insights | **Not** while-away wins; optional Understanding “limits” card **or** Knowledge-only |

#### What should remain explainable only (Knowledge)

- Full visitor/checkout gap pedagogy.  
- Hesitation/recovery sample thresholds and why confidence is insufficient.  
- Source-level “how we know” depth beyond one sentence.  
- Any insight that adds no new merchant action beyond what Home already summarized — still available when merchant opens Knowledge.

#### Knowledge READY (observable)

1. Same six insights (or equivalent) remain honest with confidence labels.  
2. Opening Knowledge after Home: no contradiction on cart_count, phone gap, or demand direction.  
3. Merchant can find the longer explanation for every Home card in Knowledge.  
4. Still no unsupported “do X to grow sales” claims without evidence.

---

### Daily Brief

#### Merchant expectations

- “What happened on this day?”  
- “What changed?”  
- “What should I prioritize?”  
- Same store story as Home — not a second conflicting product.

#### Daily value

| Value | Observable |
|-------|------------|
| Day stamp | `brief_date` visible and matches Home greeting date |
| Priorities | Attention section non-empty when Home attention is non-empty; same lead item |
| Changes | Demand up (5 vs 0) stated once with numbers |
| Completions | Only true completed/monitoring items — not insufficient-data as achievements |
| Depth | Each item has merchant-readable why (Knowledge sentence or count) |

#### Required consistency with Home

| Rule | Test |
|------|------|
| Same day | brief_date ≡ Home date |
| Same priority #1 | Brief attention lead ≡ Home attention lead |
| Same understanding facts | Brief does not claim empty understanding while Home shows cards (and vice versa) |
| One card per insight | No decision_* + raw `*:7d` duplicate pair |
| No calm-empty lie | Brief attention empty only under the same condition as Home |

#### Daily Brief READY (observable)

1. Achievement count does not exceed unique merchant facts (MV-1 must not show 13 for ~6 insights + 1 contact cluster).  
2. Attention count ≥ 1 on MV-1 evidence shape.  
3. Zero items with why = «ملخص…» or «—».  
4. Contact gap is attention, not achievement.  
5. Opening Brief then Home: merchant sees the same top priority and same demand direction.

---

### Timeline

#### Required narrative

Timeline must answer, in order a merchant can follow:

1. What started (cart / recovery intent).  
2. What the system did (e.g. scheduled).  
3. What is waiting (e.g. missing phone).  
4. What is blocked or next.

It must **not** be a second achievements list.

#### Evidence continuity

- Every Timeline story beat that claims a recovery action must be joinable to a merchant-visible evidence event (MV-1: the `scheduled` event for a demo cart).  
- Counts in Timeline (“5 cases”) must match Home/Brief/Knowledge.

#### Merchant readability

- One headline + one plain why per beat.  
- No duplicate titles.  
- No unexplained calendar jump: if the day the merchant is reviewing is `2026-05-04`, every visible event time must be coherent with that day **or** labeled so the merchant understands lab/simulation time (merchant-visible label required when times disagree — product decision below).

#### Product decision — time honesty (from MV1-D07)

**Decision:** When event times and the merchant’s brief day disagree, Timeline (and Home if it shows event times) **must show a merchant-visible day/context label** for the reviewed day; silent mixed clocks are forbidden.  
**Acceptance:** Merchant can state which day they are reviewing without guessing.

#### Timeline READY (observable)

1. Activity Timeline item count ≠ dump of all Brief achievements (MV-1: must not be the same 13-item list as while-away).  
2. At least one beat references the scheduled recovery evidence when such an event exists.  
3. Contact wait appears as a waiting/blocked beat, consistent with Home attention.  
4. No placeholder detail.  
5. No unexplained dual calendar (May 4 brief vs July 17 event) without merchant-visible context.

---

### Merchant journey

Required journey after READY:

```text
Home → sees dated today, attention (contact gap), understanding (demand / health)
    → knows next step
    → opens Knowledge only for depth (optional)
    → Daily Brief matches Home priorities for the day
    → Timeline shows the cart/recovery story behind the attention item
```

**Journey READY:** Merchant completes this path without encountering a contradiction on store activity, priority, or counts.

---

### Cross-surface consistency

| Dimension | READY rule |
|-----------|------------|
| Store | One store story for the session |
| Cart count | Home badge = Knowledge cart_count = Brief source facts |
| Top priority | Home attention #1 = Brief attention #1 = Timeline blocked/waiting beat |
| Demand direction | Home understanding and Brief and Knowledge agree (5 vs 0 up) |
| Insufficient evidence | Same stance everywhere; never a “win” on Home/Brief while-away |
| Empty calm | Allowed only when truly nothing needs the merchant |

---

### Merchant trust

Trust READY when the merchant can honestly say yes to all:

1. Home did not hide a blocked recovery.  
2. Home did not deny Knowledge’s understanding.  
3. Numbers on Home match Knowledge.  
4. Brief did not reinvent a different day story.  
5. Timeline explained what happened without mystery time.  
6. Placeholders and duplicate spam are gone.

---

## Ready Criteria

### Surface READY definitions (no vague wording)

#### Home READY

| ID | Must be true (merchant can check) |
|----|-----------------------------------|
| HR-1 | Attention section shows the contact-wait fact when ≥1 cart lacks phone and recovery cannot proceed (MV-1: 5). |
| HR-2 | Attention empty copy is **absent** in that situation. |
| HR-3 | Understanding shows ≥1 card carrying Knowledge’s demand or health message with numbers. |
| HR-4 | Understanding empty copy is **absent** when Knowledge has ≥1 such insight. |
| HR-5 | While-away has ≤1 card per unique merchant fact; no title twins. |
| HR-6 | No card detail equals «ملخص Knowledge Layer للفترة المحددة» or «—». |
| HR-7 | Active-carts badge = Knowledge cart_count. |
| HR-8 | Greeting date non-empty and equals brief_date shown that session. |
| HR-9 | When contact wait exists, at least one attention item states a next step the merchant can act on (e.g. obtain customer contact / open waiting carts). |

#### Knowledge READY

| ID | Must be true |
|----|--------------|
| KR-1 | Insights still state confidence and insufficient evidence where sample is thin. |
| KR-2 | Messages still include proving numbers for demand and phone gap. |
| KR-3 | No contradiction with Home on cart_count, phone gap, demand direction. |
| KR-4 | No unsupported recommendation added. |

#### Daily Brief READY

| ID | Must be true |
|----|--------------|
| BR-1 | Attention non-empty under MV-1 evidence shape; lead = Home attention lead. |
| BR-2 | Contact wait is **not** listed under achievements. |
| BR-3 | Unique merchant facts only — no duplicate pairs for the same insight. |
| BR-4 | Every visible item has a non-placeholder why. |
| BR-5 | brief_date equals Home greeting date. |

#### Timeline READY

| ID | Must be true |
|----|--------------|
| TR-1 | Not identical to Home while-away dump. |
| TR-2 | Includes a readable beat for scheduled recovery when evidence event exists. |
| TR-3 | Blocked/waiting beat aligns with Home attention. |
| TR-4 | Merchant-visible day/context when clocks would otherwise disagree. |
| TR-5 | No placeholder detail; no duplicate titles. |

#### Trust / journey READY

| ID | Must be true |
|----|--------------|
| JR-1 | Merchant can name today’s top priority from Home alone. |
| JR-2 | Merchant can name one improvement or direction from Home alone when Knowledge has a trend. |
| JR-3 | Merchant walking Home → Knowledge → Brief → Timeline finds **zero** count/priority contradictions. |
| JR-4 | Merchant answers yes to “I understand my store better after opening CartFlow.” |

---

## Defect → Product Contract

For every MV-1 defect: problem, trust loss, desired behavior, acceptance, ready criteria.

### MV1-D01 — Attention empty while contact wait exists (Critical)

| Field | Product decision |
|-------|------------------|
| **Problem** | Obtain-contact (5) shown as achievement/while-away; attention empty. |
| **Why merchant loses trust** | Product says “nothing needs you” while recovery is blocked. |
| **Desired behavior** | Contact wait is **Attention #1** on Home and Brief; while-away does not claim it as completed win. |
| **Acceptance criteria** | On MV-1 evidence: `attention_today.count ≥ 1`; lead headline mentions waiting for customer number / contact; attention empty message not shown. |
| **Ready criteria** | HR-1, HR-2, HR-9, BR-1, BR-2. |

### MV1-D02 — Understanding empty despite Knowledge insights (Critical)

| Field | Product decision |
|-------|------------------|
| **Problem** | Home understanding empty; Knowledge has 6 insights. |
| **Why merchant loses trust** | Home contradicts Knowledge’s existence of understanding. |
| **Desired behavior** | Home Understanding inherits Knowledge messages for demand trend and store health (at minimum); empty understanding copy only when Knowledge has no merchant-usable insight. |
| **Acceptance criteria** | On MV-1 evidence: `store_understanding.items ≥ 1` including demand (5 vs 0) and/or “most carts without phone”; empty copy not shown. |
| **Ready criteria** | HR-3, HR-4, KR-3. |

### MV1-D03 — Duplicate cards (Major)

| Field | Product decision |
|-------|------------------|
| **Problem** | Same insight appears twice (decision wrapper + raw). |
| **Why merchant loses trust** | Looks broken / spammy. |
| **Desired behavior** | One merchant card per unique fact across Home while-away, Brief, Timeline. |
| **Acceptance criteria** | No two visible items share the same merchant title+fact for the same insight key in one surface list. |
| **Ready criteria** | HR-5, BR-3, TR-5. |

### MV1-D04 — Placeholder detail (Major)

| Field | Product decision |
|-------|------------------|
| **Problem** | Detail/why is «ملخص…» or «—». |
| **Why merchant loses trust** | Claim without evidence. |
| **Desired behavior** | Every card uses Knowledge’s explanatory sentence or an equivalent count-backed sentence. |
| **Acceptance criteria** | Zero merchant-visible details equal those two placeholders. |
| **Ready criteria** | HR-6, BR-4, TR-5. |

### MV1-D05 — Carts badge 0 vs 5 carts (Major)

| Field | Product decision |
|-------|------------------|
| **Problem** | Quick-nav active carts badge 0; Knowledge cart_count 5. |
| **Why merchant loses trust** | Chrome number disagrees with store truth. |
| **Desired behavior** | Badge shows the same active/abandoned cart count Knowledge uses for that session. |
| **Acceptance criteria** | Badge = 5 on MV-1 evidence shape. |
| **Ready criteria** | HR-7. |

### MV1-D06 — Timeline not a story (Major)

| Field | Product decision |
|-------|------------------|
| **Problem** | Timeline = achievements dump; evidence event not narrated. |
| **Why merchant loses trust** | Cannot follow what happened. |
| **Desired behavior** | Ordered narrative beats; scheduled evidence appears as a beat; blocked wait aligns with attention. |
| **Acceptance criteria** | Timeline ≠ 13-item while-away clone; ≥1 beat tied to scheduled evidence; waiting/blocked beat present. |
| **Ready criteria** | TR-1, TR-2, TR-3. |

### MV1-D07 — Unexplained time jump (Major)

| Field | Product decision |
|-------|------------------|
| **Problem** | Event time July 17 vs brief day May 4 with no merchant bridge. |
| **Why merchant loses trust** | Timeline feels arbitrary. |
| **Desired behavior** | Merchant-visible day/context for the reviewed period; no silent mixed clocks. |
| **Acceptance criteria** | Merchant can identify the reviewed day from Timeline chrome/labels without ops tools. |
| **Ready criteria** | TR-4. |

### MV1-D08 — Empty greeting date (Minor)

| Field | Product decision |
|-------|------------------|
| **Problem** | `date_ar` empty; brief_date = 2026-05-04. |
| **Why merchant loses trust** | “Today” is unanchored. |
| **Desired behavior** | Greeting date always shows the same day as Brief. |
| **Acceptance criteria** | Non-empty date_ar matching brief_date. |
| **Ready criteria** | HR-8, BR-5. |

### MV1-D09 — Limits framed as achievements (Minor)

| Field | Product decision |
|-------|------------------|
| **Problem** | Insufficient/unavailable insights listed as while-away completions. |
| **Why merchant loses trust** | Product celebrates not knowing. |
| **Desired behavior** | Limits appear as Understanding “still learning / not visible yet” or Knowledge-only — never as while-away wins. |
| **Acceptance criteria** | Zero insufficient/unavailable insights in while-away/achievements framed as completed work. |
| **Ready criteria** | HR-5 (content class), BR-2 class rule extended to limits. |

### MV1-D10 — Browser Home without Attach (Observation)

| Field | Product decision |
|-------|------------------|
| **Problem** | Browser `/dashboard` without Attach activation not accepted in MV-1. |
| **Why merchant loses trust** | Risk of empty signup store vs demo truth if demoed wrong. |
| **Desired behavior** | Product acceptance of READY **requires** the same attached session path as MV-1 until browser path shows the same merchant outcomes. |
| **Acceptance criteria** | READY retest uses attached Lab session (or equivalent merchant-visible attach). Browser-only without attach is **out of READY scope**. |
| **Ready criteria** | Journey tested on attached path only (JR-3). |

### MV1-D11 — Generic «متجرك» (Observation)

| Field | Product decision |
|-------|------------------|
| **Problem** | Greeting name generic. |
| **Why merchant loses trust** | Mild — not a truth breaker in MV-1. |
| **Desired behavior** | Prefer store display name when available; not required to exit NOT READY. |
| **Acceptance criteria** | Optional; not on critical READY checklist. |
| **Ready criteria** | Backlog P3 only. |

### MV1-D12 — Preserve Knowledge messages on Home (Enhancement → now required)

| Field | Product decision |
|-------|------------------|
| **Problem** | Messages not carried to Home. |
| **Why merchant loses trust** | Same as D02/D04. |
| **Desired behavior** | Inheritance of full insight message is **required** for Understanding/Attention cards — not optional polish. |
| **Acceptance criteria** | Home card detail contains the proving numbers from Knowledge messages. |
| **Ready criteria** | HR-3, HR-6. |

---

## Product Readiness Checklist

Single checklist. Every item measurable, testable, merchant-observable. Retest on **MV-1 evidence shape** (attached session, 5 carts no phone, demand 5 vs 0, thin visitor/recovery samples, ≥1 scheduled recovery evidence event).

| # | Checklist item | Pass if merchant observes… | Maps to |
|---|----------------|----------------------------|---------|
| C01 | Attention tells the truth | Contact-wait for 5 cases is in Attention; calm empty attention text is not shown | D01 |
| C02 | Understanding tells the truth | ≥1 Understanding card with demand 5 vs 0 and/or most carts without phone | D02, D12 |
| C03 | No duplicate spam | Each insight/contact fact appears once per surface list | D03 |
| C04 | No placeholder why | Zero «ملخص Knowledge Layer…» or «—» as card detail | D04 |
| C05 | Cart chrome matches store | Active-carts badge = 5 | D05 |
| C06 | Home has a dated today | Greeting date shown = brief date `2026-05-04` (session day) | D08 |
| C07 | Next step exists | Attention item states what to do about missing contact | D01 |
| C08 | Brief matches Home priority | Brief attention lead = Home attention lead; contact wait not an achievement | D01, Brief |
| C09 | Brief not a duplicate dump | Brief unique facts ≈ Knowledge insights + contact cluster (not 13 twins) | D03, D09 |
| C10 | Limits not celebrated | Insufficient/unavailable not in while-away as completions | D09 |
| C11 | Timeline is a story | Ordered beats; includes scheduled evidence; includes waiting/blocked | D06 |
| C12 | Timeline time is honest | Merchant can name the reviewed day/context; no silent July vs May clash | D07 |
| C13 | Knowledge still honest | Confidence + insufficient evidence + numbers unchanged in spirit | Knowledge |
| C14 | Cross-surface counts agree | Home badge, Knowledge cart_count, Brief contact count (5) agree | Journey |
| C15 | Trust sentence | Independent reviewer answers **yes** to “I understand my store better after opening CartFlow.” | Trust |

**Product READY** = **C01–C15 all Pass** on a bounded retest.  
**NOT READY** remains until then.

---

## Priority Matrix

| Priority | Defects / work | Why first |
|----------|----------------|-----------|
| **P0 — Trust critical** | D01, D02, D12, D04 | Stops lying by silence / empty / placeholder |
| **P1 — Operational truth** | D05, D03, D09, Brief consistency | Stops wrong counts and spam |
| **P2 — Story continuity** | D06, D07, D08 | Timeline + dated today |
| **P3 — Polish** | D11 | Name personalization |
| **P4 — Scope control** | D10 | Keep acceptance on attached path until browser parity |

---

## Product Iteration Backlog

Ordered for implementation **after PO approval**. Product outcomes only (no tech design).

| ID | Backlog item | Priority | Exit when |
|----|--------------|----------|-----------|
| PIB-1 | Attention truth: blocked contact = Attention #1; never calm-empty in that case | P0 | C01, C07 |
| PIB-2 | Understanding inheritance: carry Knowledge messages/numbers for demand + health | P0 | C02 |
| PIB-3 | Ban placeholder why; require count-backed sentence on every card | P0 | C04 |
| PIB-4 | Deduplicate one fact → one card on Home, Brief, Timeline | P1 | C03, C09 |
| PIB-5 | Reframe insufficient/unavailable: not while-away wins | P1 | C10 |
| PIB-6 | Cart badge = Knowledge cart_count | P1 | C05 |
| PIB-7 | Brief ≡ Home on day, priority, contact classification | P1 | C08, C14 |
| PIB-8 | Timeline narrative + evidence beat + waiting beat | P2 | C11 |
| PIB-9 | Merchant-visible day/context for reviewed period | P2 | C12 |
| PIB-10 | Greeting date = brief date | P2 | C06 |
| PIB-11 | Optional: store display name in greeting | P3 | D11 |
| PIB-12 | READY retest (MV-1 shape) + trust sentence | Gate | C15 + all C01–C14 |

---

## Final Recommendation

### Decision

| Field | Value |
|-------|--------|
| **Decision** | **READY FOR IMPLEMENTATION** |
| **Meaning** | All required product decisions for MV-1 defects and the four surfaces are made; measurable READY checklist exists |
| **Does not mean** | CartFlow is merchant READY today (still **NOT READY** until C01–C15 pass) |
| **Authorizes after PO approval** | Opening the **implementation backlog** against PIB-1…PIB-12 |
| **Does not authorize** | Starting engineering in this session · skipping PO approval · INV-002 closure · pilot claims · browser-only acceptance without attach |

### Why not “READY FOR PRODUCT ITERATION”

Product iteration (deciding what Home must say, what Brief must prioritize, what Timeline must narrate) is **complete in this document**. Remaining work is execution against locked criteria — that is implementation after PO approval, not further open-ended product discovery.

### Why implementation is still gated

STOP rule: **Await Product Owner approval** before opening the implementation backlog. Until C01–C15 pass on retest, product status remains **NOT READY**.

---

## Appendix — Decisions locked this session

1. Contact wait / blocked recovery → **Attention**, never achievement win.  
2. Knowledge messages with numbers → **required** on Home Understanding/Attention.  
3. One fact → one card.  
4. Placeholder why → **forbidden**.  
5. Badge → equals Knowledge cart_count.  
6. Insufficient/unavailable → not while-away completions.  
7. Timeline → narrative + evidence continuity, not achievements clone.  
8. Mixed clocks → merchant-visible day/context required.  
9. Greeting date → equals brief date.  
10. READY acceptance path → attached Lab session (MV-1 path) until browser parity is separately proven.  
11. Store display name → optional P3.  
12. Product READY = checklist C01–C15 all Pass + trust sentence yes.
