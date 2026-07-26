# Merchant Understanding Report V1

**Status:** POST–Reality Validation Certification · evidence only · no redesign · no fixes  
**Host:** `https://smartreplyai.net`  
**Store:** `demo` · merchant `429`  
**Living Store run:** `srs_32dca83c60b045639d530ac1ba841e9e` (completed 2026-07-26T03:57:07Z)  
**Identity:** `Status = CONSISTENT` · `CEO_REVIEW_SAFE = TRUE` (certification page after `/dev/living-store-home-review`)  
**Evidence pack:** `docs/product/merchant_understanding_v1/`  
**Rule:** Observe what the merchant naturally concludes — not what CartFlow intended.

---

## Verdict (30 seconds)

After 30 seconds inside CartFlow on Living Store reality, a merchant **cannot** reliably answer all five understanding questions.

Reality is consistent across surfaces. **Understanding is not.**

| # | Question | Answer after 30s |
|---|----------|------------------|
| 1 | What is happening in my store today? | **Unclear** — Home says calm / no critical problems while also listing five work situations; Carts shows active groups and counts. |
| 2 | What is my highest-priority commercial problem? | **Unclear** — competing “firsts”: calm health, Raven interest, TrueSound shipping, recovery without contact, operations needing human attention. |
| 3 | Why is it happening? | **Unclear** — many “why” lines restate the claim; several situations use circular evidence. |
| 4 | What should I do first? | **Unclear** — Priority 1 and Priority 2 share the same decision sentence; Home/Carts often imply no merchant action. |
| 5 | What outcome should I expect? | **Unclear** — outcomes are generic (“increase recovery opportunities”) without a merchant-sized result. |

Failure belongs to the product presentation of understanding, not to the merchant.

---

## Surface observations

For every surface: exactly two sections — what the merchant immediately understands, and what they still do not.

### Home

--------------------------------------------------

Merchant immediately understands:

- The store is labeled **هادئ** and told **لا توجد مشكلات تجارية حرجة ظاهرة.**
- Named product situations exist: Raven (اهتمام دون شراء), TrueSound (احتكاك الشحن), Horizon Steel (طلب المنتج).
- Communication and carts teasers read as quiet: **لا مهام / 0** and **تواصل العملاء يسير بشكل طبيعي.**
- There is a list titled **مواقف العمل الآن** with five items and links to expand in Decision Workspace.

--------------------------------------------------

Merchant still does not understand:

- Whether the store is actually calm, or has commercial problems requiring attention (calm label vs five situations).
- Which single problem is highest priority among the five equal-looking situation cards.
- Why Horizon Steel’s “طلب المنتج” statement is **لا توجد أدلة حالية على مشكلة جودة** (demand framed as absence of quality evidence).
- What to do first today without leaving Home.
- What outcome to expect if they act — or if they do nothing.
- What the exposed technical ids (`cs:…`) mean for their business.
- How Home “no cart tasks” relates to Living Store cart activity visible elsewhere.

--------------------------------------------------

### Decision Workspace

--------------------------------------------------

Merchant immediately understands:

- The page asks **ماذا يجب أن أقرر الآن، ولماذا؟**
- Counters say **يحتاج إجراء الآن: 2** and **يحتاج قرارك: 6**.
- Domain chips mark **الاسترجاع** and **التشغيل** as having a decision; other domains say **لا إجراء مطلوب.**
- Priority cards expose a structured template: القرار / لماذا؟ / لماذا الآن؟ / الأدلة / الإجراء الموصى به / الأثر المتوقع.
- The same named situations from Home appear again (Raven, TrueSound, recovery opportunity, Horizon Steel).

--------------------------------------------------

Merchant still does not understand:

- What the single highest-priority commercial problem is (Priority 1 recovery vs Priority 2 operations vs product situations vs Home calm).
- Why Priority 1 and Priority 2 share the same decision text: **راجع تجربة إتمام الشراء ومتابعة العملاء.**
- Why the **الشحن** chip says **لا إجراء مطلوب** while a shipping-friction situation is present and marked مرتفع.
- Why the **التواصل** chip says **لا إجراء مطلوب** while Priority 1 evidence is **غياب وسيلة تواصل صالحة.**
- Why Home said no carts need follow-up while Workspace Priority 1 is about cart follow-up failure.
- Why “evidence” for several situations restates the title instead of explaining a cause.
- What concrete first step to take in the next five minutes (open cases without contact vs shipping review vs Raven conversion).
- What measurable outcome to expect after that first step.
- Why Horizon Steel remains a decision item when its statement is “no quality evidence.”

--------------------------------------------------

### Products

--------------------------------------------------

Merchant immediately understands:

- The page is about **المنتجات المشاركة في المواقف**.
- Three products are listed: Raven — حزام جلد للساعة, TrueSound — سماعة لاسلكية, Horizon Steel — ساعة يد ستانلس.
- Each row points back to Decision Workspace (**وسّع في مساحة القرار**).
- The surface claims **بلا تفسير جديد** (participation only).

--------------------------------------------------

Merchant still does not understand:

- What is happening commercially for each product beyond a situation title.
- Why Horizon Steel is listed under product demand with a quality-absence statement.
- Which product problem is highest priority.
- Why interest without purchase is happening (cause), not only that it is named.
- What to do first from Products.
- What outcome to expect after expanding a row.
- What the technical `cs:…` strings mean.

--------------------------------------------------

### Carts

--------------------------------------------------

Merchant immediately understands:

- Cart groups and counts are visible (e.g. الكل 25، تفاعل العملاء، تردد بسبب الشحن 7 سلة، بانتظار الإرسال 15 سلة، عادوا وأكملوا الشراء 10 سلة).
- Shipping hesitation is a real pattern for some carts (**7 عميلًا تردّدوا بسبب الشحن.**).
- A selected cart can say **لا حاجة لإجراء — CartFlow يتابع تلقائياً.**
- Carts participate in Raven / TrueSound situations (participation banner).

--------------------------------------------------

Merchant still does not understand:

- How this reconciles with Home **لا توجد سلال تحتاج متابعة حالياً** / **لا مهام**.
- Whether they must act: detail says no action; Workspace Priority 1–2 say action now; group copy mentions **لا يوجد جدول استرجاع فعّال في النظام لهذه السلة.**
- How “WhatsApp sent according to hesitation reason” can coexist with “no effective recovery schedule.”
- What the highest-priority cart problem is among shipping hesitation, waiting to send, and waiting for customer reply.
- Why Priority 1 (missing valid contact) is not visible as the cart story here.
- What outcome to expect if they follow “no action needed.”

--------------------------------------------------

### Communication

--------------------------------------------------

Merchant immediately understands:

- The section exists with nav: الرسائل / قوالب الاسترجاع / أسباب التردد.
- Subtitle intent: **ما حدث في التواصل، وما يحتاج متابعة.**
- A participation line mentions **تغطية التواصل**.

--------------------------------------------------

Merchant still does not understand:

- What happened in communication today in merchant language (body is largely `cs:communication_coverage|store:demo` plus identity debug text).
- Whether communication is healthy (Home: يسير بشكل طبيعي) or broken (Workspace Priority 1: غياب وسيلة تواصل صالحة).
- What needs follow-up right now.
- What to do first.
- What outcome to expect.
- How templates / hesitation reasons relate to today’s commercial problem.

--------------------------------------------------

---

## Misunderstanding register

No solutions. Severity: **Critical** = blocks answering a core question in ≤30s · **High** = forces wrong or contradictory conclusion · **Medium** = leaves a core question fuzzy · **Low** = noise that slows understanding.

### M-01 — Calm store vs active problems

- **Surface:** Home (conflicts with Workspace + Carts)
- **Question the merchant failed to answer:** What is happening in my store today?
- **Evidence:** Home paints **حالة المتجر / هادئ** and **لا توجد مشكلات تجارية حرجة ظاهرة** beside five **مواقف العمل الآن** cards including interest-without-purchase and shipping friction. Carts shows non-empty groups (25 / 7 / 15 / 10). Screenshots: `mu_v1_home.png`, `mu_v1_carts.png`.
- **Why the current presentation failed:** The executive altitude and the situation portfolio contradict each other in the first viewport; the merchant cannot form one store story.
- **Severity:** Critical

### M-02 — No single highest-priority problem

- **Surface:** Home + Decision Workspace
- **Question the merchant failed to answer:** What is my highest-priority commercial problem?
- **Evidence:** Home lists five situations without a sole #1. Workspace shows **يحتاج إجراء الآن: 2** and **يحتاج قرارك: 6**, then Priority 1 recovery, Priority 2 operations, plus separate commercial situations (Raven, TrueSound, recovery opportunity, Horizon). Domain chip **الشحن = لا إجراء مطلوب** while shipping friction exists. `mu_v1_home.png`, `mu_v1_workspace.png`.
- **Why the current presentation failed:** Multiple parallel “first” signals (calm health, urgency counters, priorities, situations, domain chips) prevent a single commercial ranking.
- **Severity:** Critical

### M-03 — Identical first actions for different priorities

- **Surface:** Decision Workspace
- **Question the merchant failed to answer:** What should I do first?
- **Evidence:** Priority 1 (الاسترجاع) and Priority 2 (التشغيل) both state decision **راجع تجربة إتمام الشراء ومتابعة العملاء.** `mu_v1_workspace.png` + workspace text capture.
- **Why the current presentation failed:** Distinct urgency ranks collapse into one interchangeable instruction, so “first” is not decidable.
- **Severity:** Critical

### M-04 — Why is circular / non-causal

- **Surface:** Decision Workspace (also Home situation bodies)
- **Question the merchant failed to answer:** Why is it happening?
- **Evidence:** Shipping situation evidence repeats the claim (“يبدو أن الشحن يضعف إتمام الشراء…”). Recovery opportunity evidence repeats “فرص الاستعادة محدودة اليوم.” Horizon “طلب المنتج” body is quality-absence, not demand cause. Raven evidence restates weak conversion.
- **Why the current presentation failed:** Labels named “أدلة / لماذا؟” do not add a cause beyond the headline, so the merchant cannot explain the business.
- **Severity:** High

### M-05 — Expected outcome is not merchant-sized

- **Surface:** Decision Workspace
- **Question the merchant failed to answer:** What outcome should I expect?
- **Evidence:** Outcomes such as **زيادة فرص استعادة المبيعات عبر مسار الاسترجاع** and **تقليل الفرص العالقة وزيادة إتمام الشراء** with confidence مرتفع, without a concrete merchant-visible result tied to today’s cases.
- **Why the current presentation failed:** Outcome language stays aspirational and process-shaped; a merchant cannot picture success after the first action.
- **Severity:** High

### M-06 — Contact/recovery urgency vs communication “normal”

- **Surface:** Home + Workspace + Communication
- **Question the merchant failed to answer:** What is happening in my store today? / What should I do first?
- **Evidence:** Home communication teaser: **تواصل العملاء يسير بشكل طبيعي** / لا مهام. Workspace Priority 1 evidence: **غياب وسيلة تواصل صالحة** and start step **افتح حالات بلا تواصل**. Communication page body: technical participation `cs:communication_coverage|store:demo` + identity line. `mu_v1_home.png`, `mu_v1_workspace.png`, `mu_v1_communication.png`.
- **Why the current presentation failed:** The same reality is narrated as healthy on Home/Communication and as the top urgent recovery blocker in Workspace.
- **Severity:** Critical

### M-07 — Carts action story contradicts Home and detail pane

- **Surface:** Carts (conflicts with Home + Workspace)
- **Question the merchant failed to answer:** What should I do first? / What is happening in my store today?
- **Evidence:** Home: **لا توجد سلال تحتاج متابعة حالياً.** Carts: groups with 7 shipping-hesitation carts and 15 waiting-to-send; selected cart **لا حاجة لإجراء — CartFlow يتابع تلقائياً**; group operational line also includes **لا يوجد جدول استرجاع فعّال**. Workspace simultaneously demands recovery/operations action now. `mu_v1_carts.png`.
- **Why the current presentation failed:** “No tasks / no action / act now / schedule missing” coexist without a single operational truth the merchant can trust.
- **Severity:** Critical

### M-08 — Horizon Steel situation does not answer its own question

- **Surface:** Home + Workspace + Products
- **Question the merchant failed to answer:** Why is it happening? (and partly: What is happening today?)
- **Evidence:** Title **طلب المنتج — Horizon Steel**; business question **ماذا نعرف عن طلب Horizon Steel…؟**; statement/evidence **لا توجد أدلة حالية على مشكلة جودة**. Products lists it as a participating product with the same frame.
- **Why the current presentation failed:** The situation name promises demand understanding; the body answers a different topic (quality evidence absence), so the merchant cannot form a product conclusion.
- **Severity:** High

### M-09 — Products participates without teaching

- **Surface:** Products
- **Question the merchant failed to answer:** What is happening… / What should I do first? / What outcome…
- **Evidence:** Page promise **المنتجات المشاركة في مواقف العمل — بلا تفسير جديد**; rows are situation title + product name + `cs:…` + expand link. `mu_v1_products.png`.
- **Why the current presentation failed:** By design the surface withholds interpretation, so a 30-second Products visit adds names without understanding.
- **Severity:** Medium

### M-10 — Communication surface is not merchant-readable

- **Surface:** Communication
- **Question the merchant failed to answer:** All five questions from this surface alone
- **Evidence:** Active page text centers on **تغطية التواصل — عملاء في مسار التواصل الحالي. cs:communication_coverage|store:demo** and **CONSISTENT · store=demo · run=srs_… · situations=5**. Subtitle asks what happened / what needs follow-up; body does not answer in commercial language. `mu_v1_communication.png`.
- **Why the current presentation failed:** Merchant-facing Communication paints identity/participation strings instead of a communication business story.
- **Severity:** Critical

### M-11 — Technical identity strings compete with business language

- **Surface:** Home, Workspace, Products, Carts, Communication
- **Question the merchant failed to answer:** What is happening… (clarity / confidence)
- **Evidence:** Merchant-visible `cs:interest_without_purchase|DEMO-WATCH-BAND:demo`, `cs:shipping_friction|b|demo_earbuds|…`, CEO banner fields (`Status`, `CEO_REVIEW_SAFE`, obs/facts/situations counts) on Home/Workspace; Communication shows run id line.
- **Why the current presentation failed:** System identity and situation keys are presented at merchant altitude, stealing attention from commercial meaning.
- **Severity:** Medium

### M-12 — Shipping domain chip denies the shipping situation

- **Surface:** Decision Workspace
- **Question the merchant failed to answer:** What is my highest-priority commercial problem? / Why is it happening?
- **Evidence:** Category grid **الشحن → لا إجراء مطلوب** while situation **احتكاك الشحن — TrueSound** appears with الثقة مرتفع and action **راجع تجربة الشحن…**. `mu_v1_workspace.png`.
- **Why the current presentation failed:** Domain summary and situation portfolio disagree about whether shipping is a problem.
- **Severity:** High

---

## Cross-surface contradiction map (evidence)

| Signal A | Signal B |
|----------|----------|
| Home: هادئ / لا مشكلات حرجة | Home: 5 مواقف عمل incl. interest + shipping |
| Home: لا سلال تحتاج متابعة / لا مهام | Carts: 25 carts · 7 shipping hesitation · 15 waiting send |
| Home/Comm: التواصل يسير بشكل طبيعي | Workspace P1: غياب وسيلة تواصل صالحة |
| Workspace chip: الشحن لا إجراء | Situation: احتكاك الشحن (مرتفع) |
| Workspace chip: التواصل لا إجراء | Workspace P1 recovery about contact capture |
| Cart detail: لا حاجة لإجراء | Workspace: يحتاج إجراء الآن: 2 |
| Cart group: رسالة واتساب أُرسلت | Same group line: لا يوجد جدول استرجاع فعّال |

---

## Session gate notes (not understanding fixes)

- Living Store was re-run for this mission; observation used the new run id above.
- Identity Certification HTML: **CONSISTENT** + **CEO_REVIEW_SAFE = TRUE**.
- Same bound session painted a Home/Workspace banner **CEO_REVIEW_SAFE = FALSE** while certification remained TRUE — recorded as merchant-visible noise under M-11, not as an identity divergence (`divergences` empty on certification).

---

## Success criteria check

> Success is when a merchant can naturally explain their own business after 30 seconds inside CartFlow.

**Result:** Not met.

The report above explains exactly why: contradictory store altitude, no sole commercial priority, interchangeable first actions, circular why/evidence, non-merchant Communication, and Carts/Home/Workspace action disagreement — while Reality Validation identity remains certified consistent.

**STOP.** No redesign. No rewrite. No new engine. No fix before this report is reviewed.
