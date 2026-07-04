# CartFlow Value Validation Foundation V1

**Date (UTC):** 2026-07-04  
**Status:** Foundational contract — documentation only  
**Scope:** Defines **how CartFlow proves value to merchants** — not how features are built  
**Authority:** This document is the bridge between **Engineering Excellence** (constitution, truth layers, governance) and **Commercial Success** (retention, expansion, pricing, trust).  
**Explicitly out of scope:** Merchant Intelligence implementation, Knowledge Layer implementation, dashboard UI changes, code, migrations, refactors.

**Relationship to other docs:**

| Document | Role |
|----------|------|
| [`engineering_constitution_v1.md`](engineering_constitution_v1.md) | **How** CartFlow is engineered |
| **This document** | **Why** merchants pay and **how** CartFlow proves it |
| [`cartflow_merchant_decision_summary_v1.md`](cartflow_merchant_decision_summary_v1.md) | Current decision-confidence audit (evidence of gaps) |
| [`platform_readiness_review_v1.md`](platform_readiness_review_v1.md) | Platform readiness vs. commercial promise |

---

## Executive summary

CartFlow sells **confident daily commerce decisions backed by evidence** — not dashboards, widgets, or WhatsApp sends.

Merchants pay to answer business questions about lost revenue, customer behavior, product friction, store health, and what to do next. CartFlow must prove its value through **evidence categories** grounded in **truth layers** already under engineering governance. Every future feature must trace to at least one **value domain**, one **proof category**, and one **measurable outcome**.

This document does not design intelligence. It defines the **permanent value contract** that intelligence, UX, and packaging must eventually satisfy.

---

## Step 1 — Merchant Questions

These are the questions merchants **actually pay to answer**. They are decision questions, not engineering questions.

### 1.1 Revenue & recovery

| Question | Merchant decision |
|----------|-------------------|
| Why are customers leaving? | Should I change messaging, timing, or offer? |
| Which abandoned carts are worth acting on first? | Where do I spend limited time today? |
| Did recovery actually bring money back? | Is CartFlow paying for itself? |
| Which recovery efforts actually worked? | What should I keep, stop, or repeat? |
| What revenue am I losing right now? | How urgent is this problem? |

### 1.2 Customer understanding

| Question | Merchant decision |
|----------|-------------------|
| Who is stuck and why? | Do I call, wait, or let automation run? |
| Which customers came back but didn't buy? | Is there a follow-up worth doing? |
| What changed in customer behavior this week? | Is something new happening in my store? |
| Does this cart need me or the system? | Do I open the dashboard or ignore it? |

### 1.3 Product understanding

| Question | Merchant decision |
|----------|-------------------|
| Which products lose the most sales? | Should I fix price, stock, description, or shipping? |
| What objections block which products? | Which product-page change would help most? |
| Are hesitation reasons product-specific or store-wide? | Is this a catalog problem or a policy problem? |

### 1.4 Store health & operations

| Question | Merchant decision |
|----------|-------------------|
| Is my store set up correctly for recovery? | Can I trust automation to run? |
| Is WhatsApp / widget / platform connection working? | Do I need support before I lose carts? |
| What broke or degraded since yesterday? | What do I fix before it costs sales? |
| Can I trust what the dashboard shows? | Should I act on this number? |

### 1.5 Decision support

| Question | Merchant decision |
|----------|-------------------|
| What should I do first today? | Priority under time pressure |
| What changed this week? | Focus vs. noise |
| What happens if I do nothing? | Urgency and acceptable inaction |
| Is this cart finished? | Close mentally; stop revisiting |

### 1.6 Questions CartFlow must NOT optimize for (engineering-only)

Examples to explicitly deprioritize in merchant value framing:

- What is the snapshot fingerprint?
- Which CI gate failed?
- What is the pool checkout count?
- How many rows did the builder write?

These belong in engineering governance — not in merchant value proof.

---

## Step 2 — Value Domains

Six permanent value domains. Every future feature must support **at least one**.

### 2.1 Revenue Recovery

**Why merchants care:** Abandoned carts are lost revenue. Merchants pay CartFlow to **recover money they would otherwise lose**, with proof — not hope.

**What CartFlow proves:**

- Recovery messages were sent at the right time to the right carts
- Customers returned or purchased after recovery (with honest attribution)
- Recovered revenue is measurable in SAR and attributable to CartFlow actions
- VIP and high-value carts are surfaced before they are lost

**Evidence today (engineering foundation):** Purchase Truth, recovery logs, `RecoverySchedule`, attributed purchase mapping (Product Foundation), lifecycle states for post-recovery outcomes.

---

### 2.2 Customer Understanding

**Why merchants care:** Merchants cannot manually watch every session. They need to know **who needs attention, who is waiting, and who is done** — in plain language.

**What CartFlow proves:**

- Each cart has a truthful lifecycle state (not a guess from UI labels)
- The merchant sees what happened, what the system did, and what comes next
- Return-to-site and engagement signals are visible when evidence exists
- VIP and intervention scenarios are distinguishable from routine automation

**Evidence today:** Lifecycle Truth (LT-C1), customer lifecycle states v1, merchant decision frame («ماذا حدث؟ / ماذا فعل النظام؟ / التالي / تدخل التاجر»), return tracker signals.

---

### 2.3 Product Understanding

**Why merchants care:** Store-wide averages hide product-level leaks. Merchants need to know **which products drive abandonment and which objections attach to which SKUs**.

**What CartFlow proves:**

- Cart line identity is captured when the widget/platform provides it
- Hesitation reasons can be linked to products (foundation tables exist)
- Purchase outcomes can be linked to products (purchase mapping foundation)
- Insights about products are labeled with confidence when data is incomplete — never fabricated

**Evidence today:** Product Data Foundation (cart line snapshots, catalog normalization, hesitation mapping, purchase mapping), Knowledge Layer product bridge (read-only health metrics only — not full product intelligence).

**Honest gap:** Product-level merchant decisions are **foundation-ready, not merchant-served**. Value proof requires future surfacing — not assumptions.

---

### 2.4 Store Health

**Why merchants care:** Recovery cannot work on a broken store. Merchants need confidence that **widget, WhatsApp, platform connection, and templates** are alive before they trust automation.

**What CartFlow proves:**

- Setup readiness is truthful (not cosmetic checkmarks)
- Integration signals report real connection state
- Widget configuration matches what the storefront receives
- Degradation is visible before silent failure

**Evidence today:** Merchant onboarding reality, integration health foundation, widget configuration trust, storefront runtime truth gate, setup experience / activation journey.

---

### 2.5 Operational Confidence

**Why merchants care:** Merchants will not renew a product they do not trust. They need to know **the system is running, messages are real, and the dashboard is current**.

**What CartFlow proves:**

- Sends are logged with acceptance and delivery truth separated
- Scheduler and recovery engine are operating (not stuck silently)
- Dashboard data freshness is bounded and explainable when stale
- Failures have an owner and a visible state — not silent drops

**Evidence today:** Provider Reliability foundation, operational metrics, dashboard read model governance, snapshot generation governance, data growth governance, lifecycle reconciliation.

---

### 2.6 Decision Support

**Why merchants care:** Merchants have minutes, not hours. They pay for **priority, clarity, and actionable next steps** — not another analytics portal.

**What CartFlow proves:**

- The most important 3–5 things today are ranked and explained
- Each insight answers: what happened, why, what to do
- Recommended actions are eligible (merchant can actually perform them)
- Inaction consequences are stated when automation will (or will not) continue

**Evidence today (partial):** Knowledge Layer OIA cards (Observation / Impact / Action), lifecycle next-action copy, merchant decision inventory (documents gaps: **C− composite confidence**).

**Honest gap:** Decision Support is the **least proven domain today**. Engineering truth exists; merchant-grade decision confidence does not yet.

---

## Step 3 — Proof Categories

Every future insight, metric, card, or report must belong to **exactly one primary proof category**. Secondary categories are allowed when evidence supports both.

| Proof category | What it proves to the merchant | Primary value domains |
|----------------|--------------------------------|----------------------|
| **Recovery Proof** | Money and carts were recovered because of CartFlow actions | Revenue Recovery |
| **Understanding Proof** | The merchant understands customers, products, or patterns from evidence | Customer Understanding, Product Understanding |
| **Decision Proof** | The merchant knows what to do next and why | Decision Support |
| **Operational Proof** | The platform and integrations are working; data is trustworthy | Store Health, Operational Confidence |

### 3.1 Classification rules

1. **Recovery Proof** requires a recoverable outcome chain: abandon → action → measurable return or purchase (with attribution honesty).
2. **Understanding Proof** requires explanatory evidence — not counts alone. «12 abandons» is not proof; «12 abandons, 7 cited shipping, 3 returned» is closer.
3. **Decision Proof** requires an eligible action or explicit «no action needed» with consequence.
4. **Operational Proof** requires system-state evidence — connection health, send disposition, freshness, setup completeness.

### 3.2 Anti-patterns (not proof)

| Display | Why it fails |
|---------|--------------|
| Vanity KPI wall | No decision, no evidence chain |
| Unattributed «recovered revenue» | Violates Purchase Truth honesty |
| Lifecycle label without explanation | Understanding without proof |
| «Sent» without delivery truth | Operational lie (acceptance ≠ delivery) |
| Product insight without line identity | Assumption, not evidence |

---

## Step 4 — Value Evidence

Acceptable evidence sources. **No assumptions. Evidence only.**

### 4.1 Evidence registry

| Evidence type | What it truthfully answers | Engineering owner (today) | Merchant-visible today |
|---------------|------------------------------|---------------------------|------------------------|
| **Purchase Truth** | Did the customer buy? When? Attributable to recovery? | `cartflow_purchase_truth.py`, `PurchaseTruthRecord` | Partial — purchase visible; attribution honest in KL health, not yet daily brief |
| **Lifecycle Truth** | What state is this cart in? Is it finished? | LT-C1, `customer_lifecycle_states_v1.py` | Yes — lifecycle block on cart rows |
| **Recovery Truth** | Was recovery scheduled, sent, accepted, delivered, replied? | Recovery logs, schedules, provider reliability truth | Partial — row copy; delivery truth not merchant-surfaced |
| **Provider Truth** | Did WhatsApp provider accept and deliver? | Provider Reliability foundation | No — ops/dev only today |
| **Behavior Truth** | Did the customer return, hesitate, engage? | Return tracker, reason capture, widget events | Partial — reasons yes; behavioral timeline not merchant-grade |
| **Product Truth** | Which products were in cart / purchased / hesitated? | Product Data Foundation tables | No — foundation only |
| **Knowledge Layer** | What patterns exist across store evidence? | `knowledge_layer_v1.py`, `/api/knowledge/report` | Partial — home insight cards when data sufficient |
| **Integration Truth** | Are platform + WhatsApp + widget connected? | Integration health, onboarding reality, widget trust | Partial — setup cards, not unified health brief |
| **Read Model Truth** | Is dashboard data fresh and complete? | Dashboard read model, snapshot governance | Partial — stale flags internal; merchant sees symptoms not freshness contract |

### 4.2 Evidence hierarchy (for proof construction)

When building merchant proof, evidence must compose in this order:

```
Primary truth (Purchase, Lifecycle, Recovery, Provider)
        ↓
Derived understanding (Knowledge Layer, Product mappings)
        ↓
Presentation (dashboard copy, daily brief, cards)
```

Presentation **must never invent** what primary truth does not support.

### 4.3 Evidence honesty rules

1. **Insufficient data is a valid state** — say so; do not interpolate.
2. **VIP lane is isolated** — VIP evidence must not pollute normal-lane recovery proof (KL-C4 precedent).
3. **Attribution is conservative** — recovered revenue claims require Purchase Truth + explicit attribution path.
4. **Acceptance ≠ delivery** — Recovery Proof for «message reached customer» requires Provider Truth delivery evidence.
5. **Future evidence (Behavior Truth at scale)** is listed but **not counted** until governed and measured.

---

## Step 5 — Merchant Daily Brief

The ideal daily merchant experience. This is a **product contract**, not a UI spec.

### 5.1 Format

| Constraint | Rule |
|------------|------|
| **Volume** | Maximum **3–5** important insights per day |
| **Density** | Never a dashboard full of charts |
| **Language** | Merchant Arabic decision copy — not engineering vocabulary |
| **Tone** | Calm, evidence-backed, actionable |

### 5.2 Required structure per insight

Every insight in the daily brief must answer:

| Field | Merchant question | Example (illustrative) |
|-------|-------------------|------------------------|
| **What happened?** | What changed or needs attention? | «3 سلال VIP جديدة تحتاج متابعة اليوم» |
| **Why?** | What evidence supports this? | «قيمة السلال فوق عتبتك — لم يُرسل استرداد بعد بسبب رقم مفقود» |
| **What should I do?** | Eligible next step | «أضف رقم العميل أو انتظر حتى يكمل الودجيت» |

Optional when relevant:

| Field | Merchant question |
|-------|-------------------|
| **If I do nothing?** | What will the system do without me? |
| **Proof category** | Internal tag — Recovery / Understanding / Decision / Operational |
| **Confidence** | High / medium / insufficient data |

### 5.3 Daily brief composition rules

1. **Rank by merchant money and urgency** — VIP, blocked sends, and attributed wins beat aggregate trends.
2. **One insight per decision** — do not combine unrelated signals into one card.
3. **Suppress noise** — routine «waiting for reply» carts do not belong in the brief unless count or value is exceptional.
4. **Prefer Decision Proof** — if the merchant cannot act, downgrade priority or move to operational/setup surfaces.
5. **Never duplicate the carts table** — the brief is **curated**, not a filtered list.

### 5.4 Relationship to current dashboard

Today, `#home` Overview partially approximates this via Knowledge Layer cards («ماذا يحدث في متجري الآن؟»). The daily brief contract is **stricter**:

- Fewer items (3–5 hard cap vs. current flexible card count)
- Mandatory why + action on every item
- Explicit proof category and confidence
- No chart walls on the home surface

Closing the gap is **future product work** governed by this contract.

---

## Step 6 — Value Measurement

How CartFlow measures **its own value** — internally and, eventually, merchant-facing.

### 6.1 Primary value metrics

| Metric | Definition | Proof category | Honest measurement today |
|--------|------------|----------------|----------------------------|
| **Revenue recovered (SAR)** | Purchase Truth rows attributed to CartFlow recovery within defined window | Recovery Proof | Partial — attribution module exists; not merchant KPI |
| **Recovery conversion rate** | Purchases / recovery-eligible abandons (denominator-defined) | Recovery Proof | Partial — KL metrics; VIP excluded |
| **Merchant actions taken** | Count of eligible actions executed (phone add, manual send, archive, reopen, settings change) | Decision Proof | Weak — actions not uniformly instrumented |
| **Problems discovered** | Setup/integration/recovery blockers surfaced before merchant complaint | Operational Proof | Partial — ops/pilot foundation; not merchant-scored |
| **Problems solved** | Blockers cleared within SLA (connection fixed, phone captured, send succeeded) | Operational Proof | Not systematically measured |
| **Time saved** | Estimated minutes not spent checking carts manually | Decision Proof | Not measured — future survey + behavior proxy |
| **Operational confidence score** | Merchant self-report or proxy: «I trust today's dashboard» | Operational Proof | Not measured — decision summary grades C− |

### 6.2 Measurement principles

1. **Denominator-based rates** — follow Provider Reliability and operational metrics precedent; never bare counts as KPIs.
2. **Merchant-visible metrics must match internal definitions** — no marketing number without engineering equivalent.
3. **Measure value before optimizing UX** — constitution «Measure Before Optimize» applies to commercial proof too.
4. **Pilot merchants first** — validate metrics with hand-onboarded stores before fleet-wide claims.

### 6.3 Value scorecard (internal)

CartFlow should track a monthly internal scorecard:

| Domain | Example leading indicator | Example lagging indicator |
|--------|---------------------------|---------------------------|
| Revenue Recovery | Recovery sends delivered | Attributed SAR recovered |
| Customer Understanding | Lifecycle block completeness | Intervention resolution rate |
| Product Understanding | Lines capture rate | Product-linked reason coverage |
| Store Health | Setup readiness pass rate | Time-to-first-live-recovery |
| Operational Confidence | Dashboard freshness P90 | Provider delivery rate |
| Decision Support | Brief items with eligible actions | Merchant weekly active + action rate |

---

## Step 7 — Commercial Impact

How each value domain supports commercial outcomes.

### 7.1 Impact matrix

| Value domain | Retention | Expansion | Pricing | Referrals | Trust |
|--------------|-----------|-----------|---------|-----------|-------|
| **Revenue Recovery** | **Primary** — ROI justifies renewal | Upsell to Growth/Pro for multi-message, VIP | Core value anchor for 99–399 SAR tiers | «It paid for itself» stories | Must be honestly attributed |
| **Customer Understanding** | Reduces daily anxiety — «I know what's happening» | Pro tier intelligence modules | Supports Growth tier | Word-of-mouth from clarity | Broken lifecycle copy destroys trust |
| **Product Understanding** | Sticky when merchants fix catalog issues | **Primary** Pro expansion driver | Premium intelligence pricing | Rare — niche referral | High risk if product IDs wrong |
| **Store Health** | Prevents churn from «it doesn't work» | Faster activation → faster upgrade | Justifies onboarding support | Low | **Primary** trust builder for new merchants |
| **Operational Confidence** | Silent failures cause churn | Enterprise readiness narrative | Supports higher tiers | Operator referrals | **Primary** — acceptance≠delivery kills trust |
| **Decision Support** | **Primary** daily habit driver | Pro / future Decision Engine | Highest tier differentiation | «It tells me what to do» | Empty recommendations worse than no product |

### 7.2 Packaging alignment (existing tiers)

| Package | Value promise (merchant language) | Domains emphasized |
|---------|-----------------------------------|-------------------|
| **Starter (99 SAR)** | Capture why customers leave; recover automatically; see your carts | Revenue Recovery, Store Health, partial Customer Understanding |
| **Growth (199 SAR)** | Prioritize high-value carts; customize recovery; understand weekly patterns | + VIP Revenue Recovery, Understanding Proof via KL, Operational Confidence |
| **Pro (399 SAR)** | Operational insights; early intelligence; advanced recovery logic | + Product Understanding, Decision Support, future domains |

**Rule:** No tier may claim a proof category the evidence layer cannot support.

### 7.3 Commercial anti-patterns

| Claim | Risk |
|-------|------|
| «Guaranteed ROI» | Violates attribution honesty |
| «AI-powered decisions» without Decision Proof | Intelligence without value validation |
| Feature checklist marketing without proof category | Sells widgets, not outcomes |
| Fake recovered-revenue counters | Destroys trust permanently |

---

## Step 8 — Roadmap Alignment

Maps **completed engineering foundations** to **future merchant value**. Arrows show direction of value unlock — not shipped merchant features.

### 8.1 Foundation → proof → domain

```
Purchase Truth
    └──► Recovery Proof ──► Revenue Recovery
              │
              └──► attributed SAR, honest win stories

Lifecycle Truth (LT-C1)
    └──► Understanding Proof ──► Customer Understanding
              │
              └──► daily brief cart states, «finished?» clarity

Product Data Foundation
    └──► Understanding Proof ──► Product Understanding
              │
              └──► product-level objections & loss (future surfacing)

Provider Reliability
    └──► Operational Proof ──► Operational Confidence
              │
              └──► «message actually arrived» trust

Integration Health + Widget Trust
    └──► Operational Proof ──► Store Health
              │
              └──► «your store is ready» brief items

Knowledge Layer v1
    └──► Understanding Proof ──► Customer + Product Understanding
              │
              └──► weekly patterns, bottlenecks (not Decision Engine)

Dashboard Read Model + Observability
    └──► Operational Proof ──► Operational Confidence
              │
              └──► trustworthy dashboard → merchant acts on data

Snapshot Generation Optimization
    └──► Operational Proof ──► Reliable Knowledge inputs
              │
              └──► fresh evidence without stale/bloated reads

Data Growth Governance
    └──► Operational Proof ──► long-term platform sustainability
              │
              └──► merchant trust that system scales

Merchant Decision Layer (audited, not implemented)
    └──► Decision Proof ──► Decision Support
              │
              └──► eligible actions, inaction consequences

Operational Metrics
    └──► Operational Proof ──► internal value scorecard
              │
              └──► measure CartFlow health → protect merchant outcomes
```

### 8.2 Engineering → merchant value maturity

| Foundation | Engineering maturity (approx.) | Merchant value maturity | Gap to close |
|------------|----------------------------------|-------------------------|--------------|
| Purchase Truth | Governed / closed | Partial — wins visible, attribution not daily brief | Surface attributed SAR |
| Lifecycle Truth | Enforced (CI) | Good — row-level understanding | Decision actions + inaction copy |
| Product Foundation | Governed / foundation | None — merchant-facing | Product insights with confidence |
| Provider Reliability | Measured / activation deferred | None — merchant-facing | Delivery truth in recovery proof |
| Knowledge Layer | Closed v1 | Partial — home cards | Stricter daily brief contract |
| Dashboard Read Model | Governed / measured | Implicit — fast loads | Freshness transparency |
| Decision Layer audits | Documented gaps | Weak (C−) | Executable actions |

### 8.3 Feature proposal gate (future)

Before any feature ships, it must declare:

1. Which **merchant question** (Step 1) it helps answer  
2. Which **value domain** (Step 2) it strengthens  
3. Which **proof category** (Step 3) it produces  
4. Which **evidence types** (Step 4) it consumes — not invents  
5. Which **value metric** (Step 6) it moves  
6. Which **commercial outcome** (Step 7) it supports  

If any answer is «none» or «assumption», the feature belongs in engineering — not merchant value.

---

## Step 9 — Future Domains

Major domains **not designed here** — purpose only. Each must enter through the engineering lifecycle (audit → governance → implementation) **and** this value contract.

| Future domain | Purpose (why it would exist) | Value domain served | Depends on |
|---------------|------------------------------|---------------------|------------|
| **Merchant Understanding** | Learn how *this merchant* operates — risk tolerance, response patterns, upgrade readiness | Decision Support, retention | Behavior Truth, operational history |
| **Behavior Truth** | Governed timeline of customer actions (return, hesitate, engage, purchase) | Customer Understanding | Movement foundation, widget/tracker evidence |
| **Knowledge Layer (V2+)** | Deeper cross-store patterns with product linkage and honest confidence | Product + Customer Understanding | Product Foundation, KL-C1..C4 |
| **Product Intelligence** | Product-level loss, objection, and recovery effectiveness | Product Understanding, Revenue Recovery | Product Truth, hesitation + purchase mappings |
| **Revenue Intelligence** | Forecasting, leakage quantification, ROI modeling | Revenue Recovery, Decision Support | Purchase Truth + attribution + Recovery Truth |
| **Decision Engine** | Rank and recommend merchant actions with eligibility checks | Decision Support | Decision Layer implementation, Lifecycle Truth, action matrix |
| **Explainability** | Show *why* CartFlow recommended an action or insight | Trust across all domains | All proof categories with evidence chains |

**Boundary rule:** None of these domains may ship merchant-visible claims until the corresponding **proof category** and **evidence types** are governed — same standard as Purchase Truth and LT-C1.

---

## Appendix A — Traceability to merchant decision framework

CartFlow's merchant decision audits (`cartflow_merchant_decision_inventory_v1.md`, `cartflow_merchant_decision_summary_v1.md`) established six product questions per cart state. This value foundation maps them to domains:

| Decision question | Primary value domain | Primary proof category |
|-------------------|----------------------|------------------------|
| What happened? | Customer Understanding | Understanding Proof |
| Why did it happen? | Product + Customer Understanding | Understanding Proof |
| Does this require me? | Decision Support | Decision Proof |
| What should I do? | Decision Support | Decision Proof |
| What if I do nothing? | Decision Support | Decision Proof |
| Is this cart finished? | Customer Understanding | Understanding Proof + Lifecycle Truth |

Current grade **C−** for daily decision confidence is the baseline this foundation aims to improve — through evidence and proof, not through more dashboard widgets.

---

## Appendix B — Document maintenance

| Event | Action |
|-------|--------|
| New truth layer closed | Update Step 4 evidence registry + Step 8 alignment |
| New merchant-facing surface shipped | Verify proof category + daily brief rules |
| Pricing/packaging change | Update Step 7 alignment |
| Value metric instrumented | Update Step 6 honest measurement column |

**Versioning:** V1 is the initial contract. Supersession requires explicit V2 with changelog — same discipline as Engineering Constitution amendments.

---

## Success criteria (this document)

At completion, CartFlow should know:

| Question | Answer location |
|----------|-----------------|
| Why do merchants pay CartFlow? | Step 1 + Step 2 |
| How does CartFlow prove value? | Step 3 + Step 4 + Step 5 |
| How does engineering connect to merchant value? | Step 8 |
| How does every future feature contribute to business outcomes? | Step 3 gate + Step 6 + Step 7 + Step 9 boundary |
| What is explicitly NOT in scope? | Header + Step 9 (design deferred) |

This document is the **permanent bridge** between engineering excellence and commercial success. Implementation follows — governed, measured, and evidence-backed.
