# CartFlow Experience V1 — Unified Merchant Experience Foundation

**Status:** Permanent experience foundation (documentation only)  
**Date (UTC):** 2026-07-10  
**Authority:** Product experience law before Observation Layer. Aligns with and does not replace:

- [`commerce_language_foundation_v1.md`](../architecture/commerce_language_foundation_v1.md) — what CartFlow **says**
- [`cartflow_product_design_system_v1.md`](../cartflow_product_design_system_v1.md) — how value is **visually** expressed
- [`merchant_experience_foundation_v1.md`](../merchant_experience_foundation_v1.md) — how merchants **consume** knowledge
- [`cartflow_experience_foundation_v1.md`](../cartflow_experience_foundation_v1.md) — broader CXF contracts (hero/card/nav)

**Audience:** Product, design, engineering, future maintainers  

**Explicitly out of scope:** UI redesign, CSS cleanup, HTML/JS changes, Observation Layer implementation, new pages, copy decks, Signal/Truth changes.

> **Mission:** A merchant must feel that every page belongs to the same product.  
> Moving Home → Carts → Messages → WhatsApp → Settings must feel like one journey — not different applications.

---

## 1. What this is

**CartFlow Experience V1** is the permanent **unified merchant experience foundation**.

It answers:

| Question | Answer |
|----------|--------|
| What is one product journey? | One question per page, one rhythm, one visual language, one Commerce Language |
| What must be true before Observation? | No page invents structure, wording, or visual grammar |
| What is not this document? | Not a redesign brief, not a CSS pass, not Observation |

```text
Truth → Evidence → Signals → Brain → Decision
                                      ↓
                            Commerce Language
                                      ↓
                         CartFlow Experience V1   ← this document
                                      ↓
                              Page surfaces
                                      ↓
                         Observation Layer (future)
```

| Owns | Does not own |
|------|----------------|
| One question per page | Layout pixels / CSS |
| Shared page rhythm | Truth, Signals, Decision |
| Shared visual language **rules** | Token files / component code |
| Page ownership and merge candidates | Observation implementation |
| Experience gates before Observation | Feature shipping |

---

## 2. Experience principles

| ID | Principle | Meaning |
|----|-----------|---------|
| **CX-1** | **One product** | Every surface must feel like CartFlow — same journey, same grammar |
| **CX-2** | **One question per page** | Each major page answers exactly one merchant question |
| **CX-3** | **One rhythm** | Hero → purpose sentence → primary content → supporting details → optional actions |
| **CX-4** | **One visual language** | Hero, cards, type, spacing, empty/success/warning, CTA placement are shared |
| **CX-5** | **Commerce Language owns wording** | No page invents technical or conflicting terminology |
| **CX-6** | **Messages & WhatsApp are the visual reference** | Home and Carts evolve toward them — not the reverse |
| **CX-7** | **Merge before multiply** | If two pages answer the same question, merge or demote one |
| **CX-8** | **Calm by default** | Urgency is earned by Decision — never by page chrome |
| **CX-9** | **No Observation until unity** | Observation Layer must not land on fragmented page experiences |

### Anti-principles (forbidden)

| Forbidden | Why |
|-----------|-----|
| Page invents its own structure | Breaks journey continuity |
| Technical vocabulary on merchant surfaces | Violates Commerce Language |
| Same question on two top-level pages | Forces merchant to hunt |
| Dashboard-of-dashboards | CartFlow is an operating companion, not a control panel collage |
| Visual novelty per page | Reads as different products |

---

## 3. Experience language — one question per page

Every merchant page must answer **exactly one** question.

| Page (canonical) | Merchant question | If it cannot answer uniquely… |
|------------------|-------------------|--------------------------------|
| **Home** | What happened while I was away? | Merge or remove |
| **Carts** | Which situations deserve my attention? | Merge or remove |
| **Messages** | What conversations has CartFlow started? | Merge or remove |
| **WhatsApp** | Is customer communication healthy? | Merge or remove |
| **Settings** | Is my store correctly configured? | Merge or remove |

### Supporting pages (must not compete with the five)

Supporting destinations may exist only as **sections, tabs, or sub-routes** under a canonical page — never as a second answer to the same question.

| Supporting surface | Must serve | Must not become |
|--------------------|------------|-----------------|
| Home → Store setup | Settings / readiness under Home journey | Second Home |
| Home → Monthly summary | Learning / period rollup under Home | Second analytics product |
| Home → Test tools | Demo/sandbox only | Production Work |
| Carts → Waiting / Intervention / Completed / VIP | Filters of **attention** | Separate products |
| WhatsApp → Connect | Step inside communication health | Parallel WhatsApp app |
| Plans | Account configuration depth under Settings | Competing Settings |
| Widget | Storefront configuration under Settings | Competing Settings |
| Reasons / Trigger templates | Conversation content under Messages (or Settings if purely config) | Competing Carts/Home |

---

## 4. Unified page rhythm

Every major page follows the **same rhythm**. No page invents its own structure.

```text
Hero
  ↓
One sentence explaining today's purpose
  ↓
Primary content
  ↓
Supporting details
  ↓
Optional actions
```

| Beat | Job | Rules |
|------|-----|-------|
| **Hero** | Name the page in product language | One title; no competing H1s; no KPI strip in the hero |
| **Purpose sentence** | Answer the page’s one question in one line | Commerce Language only; no technical terms |
| **Primary content** | The work of the page | One primary region; answers the question without scrolling past noise |
| **Supporting details** | Proof, history, secondary lists | Collapsed or secondary by default |
| **Optional actions** | At most one primary CTA when Decision requires it | CTA placement shared; no action clusters in the hero |

### Rhythm violations (reject)

- Multiple heroes or purpose lines fighting for attention  
- Primary content that is a raw operational table without a story frame  
- Actions before the merchant understands the page question  
- Empty states that invent a different layout than success states  

---

## 5. Shared visual language

**Reference surfaces:** Messages and WhatsApp (current production visual quality).  
**Convergence target:** Home and Carts evolve toward that reference.

Standardize (rules only — no CSS in this document):

| Element | Shared rule |
|---------|-------------|
| **Hero** | Same hero family; title + purpose; calm; no decorative inventiveness |
| **Card spacing** | One spacing rhythm between cards/sections |
| **Typography** | One certified type system product-wide (PDS / Typography Lock) |
| **Card hierarchy** | Primary card = answer; secondary = support; never equal weight for unequal meaning |
| **Empty states** | Same empty pattern: what is missing → what it means → optional next step |
| **Success states** | Calm confirmation; no celebration chrome that other pages lack |
| **Warning states** | Earned by Decision/health only; same warning grammar everywhere |
| **CTA placement** | Primary CTA in a consistent region (end of primary content or decision slot) |

### Visual unity test

> Remove the nav label. If the merchant cannot tell it is still CartFlow — or if two pages feel like different products — the visual language failed.

Messages / WhatsApp pass more often today. Home / Carts must converge — **without** a redesign project that invents a third language.

---

## 6. Shared Commerce Language usage

**Commerce Language is the sole owner of merchant wording** on every page.

| Rule | Meaning |
|------|---------|
| **CL-1** | No page introduces technical language (Signal, Truth, Evidence, Confidence, Lifecycle, pipeline, …) |
| **CL-2** | No page invents alternate terms for the same meaning |
| **CL-3** | Core vocabulary is stable across Home, Carts, Messages, WhatsApp, Settings |

### Stable vocabulary (same meaning everywhere)

| Term | Means (everywhere) | Must not mean |
|------|--------------------|---------------|
| **Recovery** | Follow-up that aims to bring a cart back to purchase | Internal schedule/engine status |
| **Purchase** | Confirmed buy backed by Purchase Truth | Soft “maybe converted” |
| **Attention** | Something that may need the merchant now | Every cart row |
| **Decision** | A stance the merchant may take (or Leave) | Debug choice / ops toggle |
| **Opportunity** | Upside available if the store continues or the merchant acts | Vanity metric |

Pages may **project** Commerce Language; they may not **author** competing glossaries.

Related: recovered-purchase outcome wording is owned by Commerce Language V1 runtime — surfaces only display it.

---

## 7. Page ownership map

Inventory of current merchant dashboard destinations (`merchant_app.html` / `PAGE_PURPOSE`), reviewed against Experience V1.

### 7.1 Canonical five

| Page | Route / id | One question | Ownership | Notes |
|------|------------|--------------|-----------|-------|
| **Home** | `#home` / `page-home` | What happened while I was away? | Awareness / Pulse / while-away | Pulse (when enabled) is Home’s primary rhythm, not a second product |
| **Carts** | `#carts` / `page-carts` (+ tabs) | Which situations deserve my attention? | Work / attention queue | Tabs are filters of attention — not separate apps |
| **Messages** | `#messages` / `page-messages` | What conversations has CartFlow started? | Conversation log / send history | Visual reference |
| **WhatsApp** | `#whatsapp` (+ `#whatsapp-connect`) | Is customer communication healthy? | Channel health / readiness | Visual reference; Connect is a step, not a sibling product |
| **Settings** | `#settings` / `page-settings` | Is my store correctly configured? | Account + store configuration | Plans / Widget should deepen Settings, not compete |

### 7.2 Full page review

For each existing page: question, overlap, disappear?, section elsewhere?

| Page | 1. Merchant question today | 2. Already answered elsewhere? | 3. Can it disappear without reducing value? | 4. Become a section elsewhere? |
|------|----------------------------|--------------------------------|---------------------------------------------|-------------------------------|
| **Home (overview)** | What happened / what needs me? | Partially overlaps Carts attention | **No** — canonical awareness | — |
| **Home → Store setup** | Is the store ready to run? | Overlaps **Settings** | Partially — value is onboarding, not daily Home | **Yes → Settings** (or Home only during activation) |
| **Home → Monthly summary** | How did the month go? | Overlaps Home learning / future Monthly Experience | Not daily-critical | **Yes → Home supporting** (period rollup) or future Monthly cadence |
| **Home → Test tools** | Can I test without real send? | Demo/sandbox only | **Yes** for production merchants | **Yes → demo/sandbox only** (hide in production) |
| **Carts (waiting)** | What is waiting to send / progress? | Part of Carts attention | **No** as filter | Keep as **Carts tab/section** |
| **Carts → Intervention / followup** | What needs merchant follow-up? | Same as Carts question | **No** as filter | Keep as **Carts tab** |
| **Carts → Completed** | What finished (purchase/recovery)? | Touches Home “what happened” | Keep as archive filter | **Carts tab**; do not promote to top-level |
| **Carts → VIP** | Which high-value carts need me? | Subset of Carts attention | Keep as filter if VIP lane remains | **Carts tab/section** — not a separate product |
| **Messages** | What conversations started? | Distinct | **No** | Canonical |
| **Reasons (hesitation)** | Why do customers hesitate? | Learning; overlaps Knowledge / Home learning | Not top-level essential daily | **Candidate → Messages supporting** or Home learning |
| **Trigger templates** | What recovery copy is used per reason? | Config + Messages content | Config-heavy | **Candidate → Messages** (content) or **Settings** (config) |
| **Widget** | How does the storefront widget look/behave? | Settings / storefront config | No as capability | **Candidate → Settings** |
| **WhatsApp** | Is communication healthy? | Distinct | **No** | Canonical |
| **WhatsApp Connect** | How do I connect my number? | Step of WhatsApp | No as capability | **Section under WhatsApp** |
| **Plans** | What does my plan include? | Account | No as capability | **Candidate → Settings** |
| **Settings** | Is the store configured? | Distinct | **No** | Canonical |
| **Standalone recovery/VIP/exit-intent/widget HTML routes** (legacy) | Various config | Duplicates in-app Settings/WhatsApp/Widget | Prefer in-shell | **Merge into Settings / WhatsApp / Widget sections** over time |

---

## 8. Candidate page merges

| Candidate | Direction | Rationale | Risk if ignored |
|-----------|-----------|-----------|-----------------|
| **M1** | Home Setup → Settings (or activation-only Home) | Same “configured correctly?” family | Two setup homes |
| **M2** | Plans → Settings section | Account configuration, not a fifth journey | Settings feels incomplete; Plans feels orphaned |
| **M3** | Widget → Settings section | Storefront configuration | Settings vs Widget split-brain |
| **M4** | Trigger templates → Messages (content) or Settings (config) | One conversation system | Merchants hunt for “where copy lives” |
| **M5** | Reasons → Messages supporting or Home learning | Learning, not daily Work | Extra top-level under التواصل |
| **M6** | VIP / Completed / Followup stay **tabs under Carts** | One attention question | Top-level VIP app feeling |
| **M7** | Test tools → non-production only | Not part of merchant journey | Noise on Home |
| **M8** | Legacy standalone dashboard HTML → in-shell sections | One shell journey | Parallel apps |

**Merge rule:** Prefer **section under a canonical page** over a new top-level nav item.

---

## 9. Experience rules before Observation

Observation Layer must not begin until these gates hold as **product law** (implementation may follow later):

| Gate | Rule |
|------|------|
| **G1** | The five canonical pages each have one written merchant question |
| **G2** | No new top-level page without proving it does not duplicate G1 |
| **G3** | Every major page declares the shared rhythm (even if code still drifts) |
| **G4** | Visual reference is Messages / WhatsApp; Home / Carts have an explicit converge plan (docs/implementation later) |
| **G5** | Commerce Language owns merchant wording; pages do not mint synonyms |
| **G6** | Candidate merges (M1–M8) are decided or explicitly deferred with owner — not silently grown |
| **G7** | Observation may **observe** the unified journey; it may not invent a sixth competing surface |

### Before Observation — do / do not

| Do | Do not |
|----|--------|
| Align page purpose copy to the one-question map | Redesign CSS “to feel unified” without this foundation |
| Treat Messages/WhatsApp as visual north star | Let Home/Carts invent a third visual dialect |
| Route new features into canonical pages | Add Observation as a new top-level product |
| Keep technical terms off merchant UI | Use Observation to paper over fragmented pages |

---

## 10. Relationship to existing foundations

| Document | Relationship |
|----------|--------------|
| Merchant Experience Foundation | Experience V1 **applies** ME principles to the **unified page journey** |
| CartFlow Experience Foundation (CXF) | Experience V1 **narrows** to one-product journey + pre-Observation gates |
| Product Design System / Typography Lock | Experience V1 **requires** shared visual language; PDS owns enduring visual law |
| Commerce Language Foundation | Experience V1 **requires** CL as sole wording owner |
| Merchant Pulse / Home / Cart Page V2 | Implementations must **inherit** this foundation; they do not redefine it |

---

## 11. Success criterion

> A merchant moves Home → Carts → Messages → WhatsApp → Settings and feels **one product, one journey, one language**.  
> If any hop feels like a different application, Experience V1 is not yet satisfied — Observation must wait.

---

## 12. Explicit non-goals (this document)

- No UI redesign  
- No CSS cleanup  
- No HTML/JS changes  
- No Observation Layer build  
- No new Signal families  
- No copy implementation beyond defining ownership  

**Next (not this task):** decide merge candidates M1–M8; converge remaining pages toward Home Sprint 1 reference under PDS — still without inventing a third language.

---

## Appendix — Home Experience Sprint 1 (reference implementation)

**Status:** Implemented (presentation) — 2026-07-10  

Home is the first page fully composed on Commerce Brain → Commerce Language → Merchant Pulse → Experience V1:

| Beat | Owner | Rule |
|------|-------|------|
| **Hero** | `executive_brief` | Answers «ماذا حدث أثناء غيابك؟» — owns the narrative |
| **Cards (max 3)** | `decision_summary` / optional learning via `cartflow_progress` / `merchant_decision` | Labels: هل تحتاجني؟ · ماذا تعلمنا؟ · قرارك التالي — only if new information |
| **CTA** | `fork=enter_work` | Short «افتح السلال» — does not repeat card copy |

Never duplicate Hero in cards. Hide empty, placeholder, technical, and repeated messages. Assets: `static/merchant_pulse_v1.js` / `.css`.
