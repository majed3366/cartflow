# Merchant Story Discovery V1

**Document type:** Product architecture discovery (no code, no UI, no services)  
**Date (UTC):** 2026-07-25  
**Status:** Discovery complete — core law **ratified** as [`EXECUTIVE_EDITORIAL_EXCLUSIVITY_V1.md`](EXECUTIVE_EDITORIAL_EXCLUSIVITY_V1.md) (Product Constitution Principle 7). Implementation of Executive Brief Composition still requires separate authorization.  
**Inputs:** Business Theme Engine Production Reality Validation (`REMOVE / REDESIGN`); Living Store `demo`; Gate 2X Merchant Understanding; Home Executive Summary Constitution; benchmark research (Shopify Analytics, Stripe-class dashboards, HubSpot/Salesforce executive views, Datadog executive dashboards, Linear/Notion-style summaries, GitHub Insights, Microsoft Viva Insights)  
**Out of scope:** Product Intelligence · Theme Engine patches/renames · new aggregation layers · page redesign  

---

## 0. The question this document must answer

> What is the smallest architectural change that would make a merchant genuinely feel that CartFlow understands the store?

**Short answer (preview):**  
Not another fact-aggregation layer.  
The smallest change is **editorial exclusivity of one commercial situation on Home** — compose existing Business Facts + Store Executive Understanding into a single high-altitude brief, and forbid sibling Home cards from restating that same situation. Decision Workspace keeps depth. No new Theme Engine.

---

## 1. Why Business Theme Engine failed

Production evidence (PR #106 → `d34b552`; CEO pack `docs/product/business_themes_v1/CEO_VISUAL_REVIEW.md`):

| Observation | Implication |
|-------------|-------------|
| 6 Business Facts → 6 Themes (collapsed_ratio **1.0**) | Themes did not create understanding; they **relabeled** facts by taxonomy |
| Home teaser = reworded Raven conversion fact | Merchants hear the same truth, not a deeper one |
| Count badge rose 4 → 6 | Aggregation by type *increased* cognitive load |
| «قرارات اليوم» and «مواضيع المتجر» both pointed at checkout/conversion pressure | Parallel cards restated one commercial situation |
| Decision Workspace (declared primary owner) failed to load Themes | The layer did not complete its own ownership model for the merchant |

**Root cause (product, not engineering):**

Business Theme Engine assumed merchants organize reality as **typed buckets** (conversion, shipping, recovery…).  

Merchants organize reality as **situations**:

> “Something is wrong / interesting with how people buy Raven today.”

Shipping friction, return behaviour, and weak conversion on the same product are not three themes to a merchant — they are **one situation with multiple facts**.

Themes answered an engineering question (“can we group facts?”) instead of a merchant question (“what is going on in my store?”).

**Verdict stands:** REMOVE / REDESIGN. Do not patch. Do not rename. Do not add another synonym layer.

Themes are **removed from the target architecture** until a better model is proven.

---

## 2. What merchants actually perceive as “understanding the business”

Gate 2X already states the desired feeling:

> «I understand my store.» — not — «I understand what CartFlow is doing.»

From Living Store Home (Facts era and Themes era), merchants can already retrieve fragments:

- Store condition (recovery limited)  
- A decision teaser (review checkout / follow-up)  
- A product fact (Raven conversion)  
- Carts / communication status  

Yet they still feel repetition. That means **retrieval of true fragments ≠ understanding**.

Understanding, for an owner-operator, is the ability to answer in **one breath**:

1. **What is the situation?** (one sentence)  
2. **Why does it matter now?** (stakes)  
3. **Where do I go next?** (one owned surface)  

Everything else is evidence — valuable, but secondary.

If three Home cards require the merchant to *mentally merge* “recovery limited,” “review checkout,” and “Raven converts poorly,” CartFlow has outsourced composition to the human. That is the opposite of executive understanding.

---

## 3. Why valid Business Facts fail to become one coherent understanding

Business Facts are the right **truth atoms**. They failed to become coherence for three structural reasons:

### 3.1 Facts are multi-select; Home is multi-broadcast

Facts correctly emit several truths (Raven conversion, TrueSound shipping, Raven returns, Horizon quality absence, store health, communication).  

Home then **broadcasts several of those truths in parallel section slots** (health / decisions / observations), each with its own sentence.  

Coherence requires **selection**, not emission.

### 3.2 Taxonomy ≠ mental model

Grouping by `fact_type` / `theme_type` matches the data model.  
Merchant mental model groups by **customer journey situation** (interest → hesitation → cart → purchase) and **entity** (product / store).

So “conversion fact” + “return behaviour fact” on Raven stay separate in the system while they are one story in the merchant’s head.

### 3.3 Surfaces compete for the same meaning

Home Constitution already says Home is executive summary only; Workspace owns decisions.  

In practice, Home still paints overlapping commercial meaning across:

- حالة المتجر  
- قرارات اليوم  
- مواضيع / حقائق المنتجات  

That is an **editorial ownership failure**, not a missing fact type.

---

## 4. Is the missing layer editorial, narrative, briefing, context — or something else?

| Candidate | What it usually means | Fit for CartFlow now |
|-----------|----------------------|----------------------|
| **Aggregation / Themes** | Group facts by type | **Rejected in Production** |
| **Business context** | Shared definitions, entity, time window | Already partially present (OT, ORV, Facts, TABF) — necessary but not sufficient |
| **Narrative / story engine** | Long multi-paragraph story of the store | High risk of fiction / AI theater; overlaps PI; too heavy |
| **Business Narratives (as a new service)** | Themes with better copy | Likely Themes 2.0 — **reject** unless selection problem is solved first |
| **Executive Stories** | Named story objects across surfaces | Useful metaphor; dangerous as a new durable layer before selection works |
| **Editorial / Executive Brief** | Choose one primary situation; write once; route once; demote rest | **Best fit** — matches Datadog “altitude,” Shopify/Stripe executive KPI focus, and Gate 2X |

**Conclusion:** The missing capability is **editorial composition** (selection + exclusivity + altitude), not a new fact taxonomy and not Product Intelligence.

Name for discovery clarity (not a service yet):

> **Executive Brief Composition** — a publication policy that turns many Business Facts into one high-altitude brief for Home, with exclusive ownership of that situation’s sentence.

This is closer to how executives actually read businesses than “Themes.”

---

## 5. Benchmark research — how peers create executive understanding

Goal studied: **transformation of information → executive understanding**, not visual design.

### Patterns that recur

1. **Altitude separation** (Datadog executive dashboards)  
   High-altitude answers “Are we on track?”  
   Lower-altitude answers “Why / what next?”  
   Same data, different questions — linked, not restated.

2. **Few signals, not many truths** (Shopify / executive KPI practice)  
   5–7 decision-grade signals; if a card does not change a decision, remove it.  
   CartFlow Home already has five slots — the failure is that multiple slots narrate one situation.

3. **Question-shaped composition** (Datadog, Linear-style issue focus)  
   Each widget/card exists to answer one written question.  
   CartFlow pages already have one question each (Gate 2X). Home *sections* currently violate that discipline among themselves.

4. **Brief / digest over collage** (Notion AI summaries, modern executive digests, Viva-style insights)  
   Leaders prefer a short briefing paragraph over a gallery of synonymous cards.  
   Dashboards show; briefs explain. CartFlow Home is constitutionally a brief — it currently behaves like a gallery of briefs.

5. **Progressive disclosure** (Stripe / HubSpot / Salesforce operational → executive)  
   Summary on the front; evidence and action depth behind one owned drill-down.  
   CartFlow has the links («عرض التفاصيل») but still spends the summary budget on overlapping sentences.

6. **Semantic consistency before storytelling** (HubSpot/Stripe analytics stacks)  
   One definition of a metric/situation across surfaces.  
   CartFlow’s Facts are that semantic layer for commercial truth. Themes tried to sit *above* Facts as another semantic layer and added little.

### What peers do *not* do

They do not invent a second synonym taxonomy for every KPI (“Revenue Theme,” “Churn Theme”) and show both the KPI and the Theme on the same executive page.

---

## 6. What composition model better explains the store

### Recommended model: Executive Brief (editorial), not Theme Engine

```text
Operational Truth
        ↓
Observation Foundation
        ↓
Business Facts                 ← truth atoms (KEEP)
        ↓
Business Understanding         ← store meaning (existing Gate 2F path)
        ↓
Merchant Understanding (2X)    ← publication gate (KEEP)
        ↓
Executive Brief Composition    ← NEW POLICY (smallest change; not a Theme service)
        ↓
Home (high altitude: one situation)
        ↓
Decision Workspace (low altitude: evidence + decide)
```

**Business Theme Engine stays out of the target architecture.**

### How an Executive Brief differs from a Theme

| | Theme Engine (failed) | Executive Brief (proposed direction) |
|--|----------------------|--------------------------------------|
| Unit | Theme type bucket | **One commercial situation** (entity + journey pressure) |
| Input rule | Many facts → one type | Many facts → **one selected situation**; others deferred |
| Home role | Teaser of top theme + count of themes | **One sentence situation** + status; no sibling restatement |
| Workspace role | Cards per theme type | Depth for the selected situation (+ ranked alternatives without Home echo) |
| Success metric | Taxonomy coverage | Merchant can restate the store in one breath |

### Example (Living Store, conceptual — not implementation)

Facts present:

- Raven: high interest, weak conversion  
- Raven: repeated return without purchase  
- TrueSound: shipping stronger than price  
- Horizon: no quality issue evidence  
- Store health / communication healthy signals  

**Executive Brief (Home):**  
One situation — e.g. “Raven attracts attention but buyers stall before purchase.”  
Health/Decisions/Observations must not each invent a parallel sentence about the same stall.

**Workspace:**  
Owns why / evidence / confidence / what to decide about that situation (and may list secondary situations without Home repeating them).

TrueSound shipping becomes either:

- supporting evidence inside the Raven/checkout situation, or  
- a *secondary* Workspace situation — **not** a third Home paragraph.

---

## 7. Advantages

- Aligns with proven executive altitude patterns without inventing PI.  
- Preserves Business Facts (the layer Production proved valuable).  
- Attacks the real pain: **repetition across Home cards**, not “not enough types.”  
- Smallest change path can be **policy inside existing Home Executive Summary composition**, not a new microservice.  
- Strengthens Gate 2X (“understand the store”) instead of competing with it.  
- Clear kill criteria later: if Home still feels repetitive after exclusivity rules, revisit — without Theme residue.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Editorial selection hides secondary truths | Workspace must remain the depth owner; Home never claims completeness |
| Over-compression invents causality (“shipping caused Raven stall”) without evidence | Brief may only bind facts that already share entity/capability evidence; no PI inference |
| Renaming “Brief” into Themes 2.0 | Forbid type-bucket engines; success metric is exclusivity, not taxonomy |
| Engineers add a new durable `merchant_stories` table prematurely | Prefer composition policy + tests on Home payload before persistence |
| Workspace load failures (seen in Theme validation) | Orthogonal reliability issue — must not be “solved” by another Home card restating Workspace |

---

## 9. Architectural impact

### Keep

- Operational Truth  
- Observation Foundation / ORV  
- **Business Facts**  
- Business Understanding / Store Executive Thinking (Gate 2F path)  
- Merchant Understanding (Gate 2X)  
- Decision Composition → Workspace  
- Home Executive Summary as the only Home paint path  

### Remove from target architecture

- Business Theme Engine (until a *different* model is proven — this discovery is that different model’s brief, not a patch)

### Possibly add later (only after acceptance)

- **Executive Brief Composition** as an explicit, tested publication policy (likely inside `home_executive_summary_v1` / activation pipeline — discovery does not prescribe files)

### Do not add now

- Story/Narrative/Theme microservices  
- Product Intelligence  
- UI redesigns justified only by Themes failure  

---

## 10. Are existing layers sufficient?

**Mostly yes.**

CartFlow already has:

- Truth (OT / Observations)  
- Meaning atoms (Business Facts)  
- Store-level executive language (Gate 2F)  
- Merchant publication gate (Gate 2X)  
- Executive Home shell (HES)  
- Decision depth surface (Workspace)  

What is insufficient is **cross-section exclusivity**: nothing currently guarantees that health, decisions, and product teasers are not three angles on the same situation.

So:

- A **new durable Theme-like layer is not justified**.  
- A **thin editorial composition policy is justified**.  
- Calling that policy a full “Merchant Story Engine” is optional and should wait until the policy proves MX value in Production — otherwise we repeat Themes.

---

## 11. Is a new layer actually justified?

| Option | Justified? |
|--------|------------|
| New Business Theme / Story / Narrative service | **No** — Production falsified this class of layer |
| New Product Intelligence | **No** — locked; not required to fix repetition |
| Editorial Executive Brief policy on Home (+ Workspace depth ownership) | **Yes — smallest justified change** |
| “Do nothing; Facts alone” | Insufficient — Facts are good atoms; Home still multi-broadcasts |

**Decision rule for later implementation authorization:**

Implement only the smallest change that enforces:

> **One commercial situation may own at most one Home sentence.**

If that alone makes merchants feel CartFlow understands the store, stop.  
Do not build a Story Engine for sport.

---

## 12. Answers to the discovery questions

### 1. Why does the merchant still feel that Home repeats the same idea?

Because Home sections are independently authored from overlapping upstream meaning. The merchant must merge “recovery limited,” “review checkout,” and “Raven converts poorly” into one situation. Themes renamed the product slot; they did not stop the merge tax.

### 2. Why do multiple valid Business Facts fail to become one coherent business understanding?

Because coherence requires **selection of a situation**, not **classification of facts**. Facts answer “what is true?” Understanding answers “what is the story of the store right now?” Those are different jobs. Themes performed classification.

### 3. Is the missing layer editorial / narrative / briefing / context / other?

**Primary: editorial executive briefing** (selection + exclusivity + altitude).  
**Supporting: business context** already largely exists via Facts/OT.  
**Not:** another aggregation taxonomy.  
**Not yet:** a durable Narrative/Story engine.  
**Never as a substitute for this:** Product Intelligence.

---

## 13. Recommended evolution path (name only — no implementation)

Evolve CartFlow toward:

> **Executive Brief Composition** (editorial), consuming Business Facts + existing Business/Merchant Understanding,

**not** toward Business Themes, Business Narratives-as-services, or Executive Stories-as-objects — until the exclusivity policy is proven in Production.

If a future name is needed after proof, prefer **Executive Brief** over **Story Engine** to avoid Theme-shaped expectations.

---

## 14. Success criterion for this discovery

We can answer confidently:

### What is the smallest architectural change that would make a merchant genuinely feel that CartFlow understands the store?

**Enforce one commercial situation per Home paint:**  
select the highest-priority situation from existing Business Facts + Store Executive Understanding; express it once; route detail to Decision Workspace; forbid other Home sections from restating that situation.

That is editorial composition — not a Theme Engine, not PI, and not a new abstraction stack.

---

## 15. STOP

- Do not implement until this discovery is accepted.  
- Do not revive Business Theme Engine under another name.  
- Do not start Product Intelligence from this document.  
- Next step after acceptance: a narrowly scoped Executive Brief Composition design (still no PI), with Living Store MX kill criteria equal in rigor to the Theme validation.
