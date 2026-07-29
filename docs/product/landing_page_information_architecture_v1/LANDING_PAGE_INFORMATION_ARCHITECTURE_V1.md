# CartFlow Landing Page Information Architecture V1

**Status:** Architectural product definition — governance only.  
**Date (UTC):** 2026-07-29  
**Governing authority:** Landing Page Constitution V1 (`docs/product/landing_page_constitution_v1/`)  
**Surface (future):** `GET /` · `templates/cartflow_landing.html`  
**Non-goals:** No redesign. No Arabic copy. No Figma. No 3D. No production UI change. No screenshot selection.

This document defines the **approved section sequence** and each section’s unique responsibility. Implementation is forbidden until constitutional and product approval.

---

## 0. Cognitive Journey (binding)

The page must lead the merchant through:

```text
Recognise the problem
        ↓
Realise recovery alone is insufficient
        ↓
Understand how CartFlow responds
        ↓
See credible product evidence
        ↓
Discover the broader knowledge value
        ↓
Build trust
        ↓
Take the next action
```

The broader CartFlow identity must be **earned through evidence**.  
It must **not** be claimed in the Hero (Landing Disclosure Law).

---

## 1. Constitution → Architecture Map

| Constitution role | Architecture section(s) |
|-------------------|-------------------------|
| *(chrome)* | LP-01 Navigation · LP-16 Footer |
| Hero — capture attention | LP-02 Hero |
| Problem — create urgency | LP-03 Problem Recognition |
| Difference — reframe thinking | LP-04 Recovery Limitation Reframe |
| Solution — explain approach | LP-05 How CartFlow Works |
| *(primary evidence chain)* | LP-06 Widget · LP-07 WhatsApp · LP-08 Dashboard |
| Knowledge Layer — demonstrate intelligence | LP-09 Knowledge Layer Discovery |
| Benefits — reinforce outcome | LP-10 Decision Value |
| Merchant Journey — continuous value | LP-11 Continuous Value Journey |
| *(trust translation)* | LP-12 Trust and Governance |
| *(truthful readiness)* | LP-13 Integration Readiness |
| FAQ — remove objections | LP-14 FAQ |
| Final CTA — convert | LP-15 Final CTA |

**Note:** LP-06 / LP-07 expand Visual Evidence Law into dedicated evidence sections. They do not replace LP-05; LP-05 stays conceptual; evidence sections prove each layer.

---

## 2. Approved Page Structure (top → bottom)

### LP-01 — Navigation

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-01` |
| **Working Name** | Navigation |
| **Merchant Question** | Where am I, and how do I begin? |
| **Section Responsibility** | Provide orientation and one calm path to action. |
| **Required Merchant Belief** | I can start when I’m ready; the page won’t pressure me. |
| **Primary Evidence** | Brand mark + calm primary CTA target (no product screenshot required). |
| **Permitted Secondary Visuals** | None competing with Hero. Optional subtle brand mark only. |
| **Entry Condition** | Page load (always present). |
| **Exit Condition** | Merchant knows brand, can jump to key anchors if needed, and sees one primary begin path. |
| **Prohibited Content** | Feature lists; category claims; urgency badges; competing CTAs; mega-menus; social proof bars. |
| **Mobile Behaviour** | Compact bar; optional collapse of secondary links; primary CTA remains visible; never a second hero. |
| **Relationship to Previous** | None (page start). |
| **Relationship to Next** | Hands attention to Hero without competing. |

---

### LP-02 — Hero

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-02` |
| **Working Name** | Hero |
| **Merchant Question** | Does CartFlow address a problem I recognise? |
| **Section Responsibility** | Lead with the merchant problem and immediate value. Capture attention. |
| **Required Merchant Belief** | This is about lost revenue *and* unknown customer behaviour—not another reminder tool. |
| **Primary Evidence** | Optional restrained real-product preview (dashboard or widget crop) that supports recognition—never required decorative composition. |
| **Permitted Secondary Visuals** | Minimal atmospheric support only if it does not dominate or obscure product preview. No Hero 3D composition dependency. |
| **Entry Condition** | Merchant arrives with recovery-tool expectations or vague curiosity. |
| **Exit Condition** | Merchant recognises the problem frame and wants to scroll for proof—not a category lecture. |
| **Prohibited Content** | “Commerce Intelligence Platform” or any early category label; fake metrics; fake logos; desperate CTAs; feature grids; AI jargon. |
| **Mobile Behaviour** | Single column: problem → short supporting line → one primary CTA (+ optional secondary) → optional product preview below. |
| **Relationship to Previous** | Continues from Navigation orientation. |
| **Relationship to Next** | Creates need to examine whether abandoned carts are the full problem (LP-03). |

---

### LP-03 — Problem Recognition

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-03` |
| **Working Name** | Problem Recognition |
| **Merchant Question** | Is the abandoned cart itself the full problem? |
| **Section Responsibility** | Create urgency by showing hesitation, return behaviour, failed recovery, product friction, and insufficient evidence beyond the abandon event. |
| **Required Merchant Belief** | My real problem is missing understanding—not only missing checkouts. |
| **Primary Evidence** | Merchant-recognisable situations (may use clearly illustrative scene framing). Prefer real product surfaces only if they depict the *problem*, not the solution. |
| **Permitted Secondary Visuals** | Simple situation diagrams; no fake charts or invented percentages. |
| **Entry Condition** | Merchant recognised a familiar pain in Hero. |
| **Exit Condition** | Merchant feels the problem is deeper than “send a reminder.” |
| **Prohibited Content** | Final recommendations; product feature tour; competitor attacks; ROI claims; knowledge conclusions. |
| **Mobile Behaviour** | Stacked situation beats; one idea per beat; no side-by-side required. |
| **Relationship to Previous** | Deepens Hero recognition into concrete store situations. |
| **Relationship to Next** | Creates need to question why current recovery tactics fail (LP-04). |

---

### LP-04 — Recovery Limitation Reframe

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-04` |
| **Working Name** | Recovery Limitation Reframe |
| **Merchant Question** | Why are reminders and discounts not enough? |
| **Section Responsibility** | Reframe the category without attacking competitors: sending recovery actions ≠ learning from what happens before and after those actions. |
| **Required Merchant Belief** | Discounts and reminders are incomplete if they don’t explain behaviour. |
| **Primary Evidence** | Contrast of two modes (action-sending vs understanding)—conceptual; no competitor logos. |
| **Permitted Secondary Visuals** | Minimal comparative diagram; decorative support only if it clarifies the reframe. |
| **Entry Condition** | Merchant accepts the problem is broader than abandon events. |
| **Exit Condition** | Merchant wants to know what CartFlow does differently (without yet hearing a category claim). |
| **Prohibited Content** | Unsupported superiority claims; “#1” / “best AI”; competitor naming; fake before/after metrics. |
| **Mobile Behaviour** | Sequential contrast (A then B); not a two-column comparison dependency. |
| **Relationship to Previous** | Answers the pressure created by LP-03. |
| **Relationship to Next** | Opens the door for the connected CartFlow journey (LP-05). |

---

### LP-05 — How CartFlow Works

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-05` |
| **Working Name** | How CartFlow Works |
| **Merchant Question** | What does CartFlow actually do? |
| **Section Responsibility** | Explain the connected CartFlow journey as a conceptual merchant story—not a technical architecture diagram. |
| **Required Merchant Belief** | CartFlow connects behaviour → recovery → evidence → understanding in one continuous path. |
| **Primary Evidence** | Governed conceptual flow (see §3). Optional small real-product anchors; depth deferred to LP-06…LP-09. |
| **Permitted Secondary Visuals** | Simple journey connectors; no 3D pipeline art as the main idea. |
| **Entry Condition** | Merchant accepts that recovery-without-learning is insufficient. |
| **Exit Condition** | Merchant understands the outline and wants proof of each layer. |
| **Prohibited Content** | Deep widget/WhatsApp/dashboard tours; API diagrams; internal registry names; category labels; ML claims. |
| **Mobile Behaviour** | Vertical step list; one step visible as dominant at a time. |
| **Relationship to Previous** | Converts reframe into a concrete approach. |
| **Relationship to Next** | Creates need for early-hesitation proof (LP-06). |

**Governed conceptual flow (binding outline):**

```text
Customer behaviour
        ↓
Widget interaction
        ↓
Recovery journey
        ↓
WhatsApp continuation
        ↓
Movement and purchase evidence
        ↓
Merchant understanding
```

---

### LP-06 — Widget Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-06` |
| **Working Name** | Widget Evidence |
| **Merchant Question** | How does CartFlow understand hesitation early? |
| **Section Responsibility** | Demonstrate the widget as an early understanding and recovery surface (Visual Evidence Law — primary). |
| **Required Merchant Belief** | CartFlow can observe hesitation on the storefront before (and beyond) a generic reminder. |
| **Primary Evidence** | Real widget interface; real hesitation choices; real customer-journey representation (storefront UX—not settings-only). |
| **Permitted Secondary Visuals** | Light framing around the widget; must not replace the widget. |
| **Entry Condition** | Merchant knows the conceptual journey includes early behaviour. |
| **Exit Condition** | Merchant believes early understanding is real and wants to see post-store continuation. |
| **Prohibited Content** | Settings screenshots presented as customer UX; fake reason rates; claiming universal install self-serve if not true. |
| **Mobile Behaviour** | Full-width product evidence; copy above or below—not beside as a dependency. |
| **Relationship to Previous** | Proves the first operational layer of LP-05. |
| **Relationship to Next** | Creates need to see recovery beyond the storefront (LP-07). |

---

### LP-07 — WhatsApp Journey Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-07` |
| **Working Name** | WhatsApp Journey Evidence |
| **Merchant Question** | What happens when recovery continues beyond the store? |
| **Section Responsibility** | Demonstrate the governed WhatsApp journey as a later recovery and continuation layer—not as “CartFlow = WhatsApp sender.” |
| **Required Merchant Belief** | Recovery continues with state, response, and closure—including stopping when purchase happens. |
| **Primary Evidence** | Real WhatsApp journey representation; customer response state; merchant follow-up state; purchase suppression/closure where relevant. Prefer journey/thread evidence over settings-only. |
| **Permitted Secondary Visuals** | Channel framing only; never decorative phone mockups that invent UI. |
| **Entry Condition** | Merchant saw early storefront understanding. |
| **Exit Condition** | Merchant wants to see what *they* operate day-to-day (dashboard). |
| **Prohibited Content** | Positioning CartFlow as merely a WhatsApp blaster; delivery guarantees; fake reply rates; Meta/Twilio brand theatre. |
| **Mobile Behaviour** | Single evidence stack; states listed vertically. |
| **Relationship to Previous** | Continues the recovery layer after widget. |
| **Relationship to Next** | Hands trust-building to merchant-facing dashboard (LP-08). |

---

### LP-08 — Dashboard Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-08` |
| **Working Name** | Dashboard Evidence |
| **Merchant Question** | What will I actually see as a merchant? |
| **Section Responsibility** | Build product credibility through the real merchant experience. One of the strongest visual sections. |
| **Primary Evidence** | Real dashboard (prefer current Home and/or Decision Workspace / carts operational clarity): attention state, recovery state, customer movement, merchant-facing clarity. |
| **Permitted Secondary Visuals** | Minimal or absent. No 3D chrome around screenshots. |
| **Entry Condition** | Merchant accepts storefront + WhatsApp layers exist. |
| **Exit Condition** | Merchant trusts CartFlow is a real operating surface—not a pitch deck. |
| **Prohibited Content** | Fake KPIs; decorated screenshots that hide UI; outdated screenshots that misrepresent current faces without disclosure; category claims. |
| **Mobile Behaviour** | Full-bleed or full-width screenshot; caption/outcome sentence; no dual-column dependency. |
| **Relationship to Previous** | Shows the merchant side of the journey proven in LP-06/07. |
| **Relationship to Next** | Opens discovery of what CartFlow *learns* beyond operations (LP-09). |

**Disclosure timing:** By end of LP-08, merchant may begin to sense CartFlow is more than recovery tooling—but the broader identity is **named through evidence in LP-09**, not claimed here as a category.

---

### LP-09 — Knowledge Layer Discovery

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-09` |
| **Working Name** | Knowledge Layer Discovery |
| **Merchant Question** | What does CartFlow learn that I could not see before? |
| **Section Responsibility** | Reveal the broader identity of CartFlow **through evidence** rather than category claims. First section where the merchant may naturally realise CartFlow is broader than a recovery tool. |
| **Required Merchant Belief** | CartFlow forms governed understanding (and can say when evidence is insufficient)—not just message logs. |
| **Primary Evidence** | Knowledge cards; evidence status; confidence; insufficient-data states; product/category insights; behavioural patterns—**no fabricated findings**. |
| **Permitted Secondary Visuals** | Light framing; never replace knowledge cards with abstract “AI brain” art. |
| **Entry Condition** | Merchant trusts the operational surfaces (LP-08). |
| **Exit Condition** | Merchant sees CartFlow as recovery **plus** store understanding—earned, not labeled. |
| **Prohibited Content** | “Commerce Intelligence Platform” as a launch claim; invented insights; guaranteed autonomous advice; empty-state theatre presented as always-on intelligence. |
| **Mobile Behaviour** | Card stack; one knowledge object dominant at a time. |
| **Relationship to Previous** | Extends dashboard trust into learning. |
| **Relationship to Next** | Creates need to connect knowledge to decisions (LP-10). |

**Illustrative rule:** Any example not derived from real governed product evidence must be **clearly marked illustrative**.

---

### LP-10 — Decision Value

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-10` |
| **Working Name** | Decision Value |
| **Merchant Question** | How does this understanding help me run the store better? |
| **Section Responsibility** | Connect knowledge to merchant decisions without overpromising (constitution Benefits). |
| **Required Merchant Belief** | Understanding changes what I attend to and what I avoid doing. |
| **Primary Evidence** | Merchant-outcome statements anchored to product behaviours already shown (attention, hesitation patterns, insufficient evidence, operational decisions). Prefer real decision/workspace language over abstract benefit icons. |
| **Permitted Secondary Visuals** | Minimal icons only if they do not become a feature grid. |
| **Entry Condition** | Merchant discovered knowledge value. |
| **Exit Condition** | Merchant can name practical decision outcomes. |
| **Prohibited Content** | Autonomous advice as guaranteed truth; ROI percentages; “grow 3x”; feature laundry lists. |
| **Mobile Behaviour** | Short outcome list; one outcome per row. |
| **Relationship to Previous** | Converts LP-09 discovery into practical value. |
| **Relationship to Next** | Raises the question of value over time (LP-11). |

**Permitted outcome themes (not final copy):**

- Know what needs attention  
- Separate traffic problems from conversion problems  
- Understand recurring hesitation  
- Avoid ineffective actions  
- Recognise when evidence is insufficient  
- Make better operational decisions  

---

### LP-11 — Continuous Value Journey

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-11` |
| **Working Name** | Continuous Value Journey |
| **Merchant Question** | Does CartFlow become more useful over time? |
| **Section Responsibility** | Show progression from daily recovery activity to accumulated merchant understanding (constitution Merchant Journey). |
| **Required Merchant Belief** | Use compounds into clearer store understanding—without magic ML promises. |
| **Primary Evidence** | Continuity journey (Observe → Recover → Track movement → Collect evidence → Form knowledge → Improve decisions). May reuse small real-product anchors already established. |
| **Permitted Secondary Visuals** | Simple progression graphic; no neural-net decoration. |
| **Entry Condition** | Merchant accepts decision value. |
| **Exit Condition** | Merchant sees CartFlow as ongoing, not a one-shot campaign tool. |
| **Prohibited Content** | Unsupported machine-learning claims; “gets smarter automatically” without evidence framing; fake time-series charts. |
| **Mobile Behaviour** | Vertical progression; no timeline side panel required. |
| **Relationship to Previous** | Extends LP-10 from discrete decisions to continuity. |
| **Relationship to Next** | Raises trust/restraint questions (LP-12). |

---

### LP-12 — Trust and Governance

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-12` |
| **Working Name** | Trust and Governance |
| **Merchant Question** | Can I trust what CartFlow tells me? |
| **Section Responsibility** | Explain CartFlow’s truth, evidence, and restraint principles in **merchant language**. |
| **Required Merchant Belief** | CartFlow prefers restraint and evidence over hype. |
| **Primary Evidence** | Product behaviours already real: no recommendation without evidence; insufficient evidence stated; purchases stop unnecessary recovery; store isolation; observation ≠ conclusion. |
| **Permitted Secondary Visuals** | None required; avoid seal/badge theatre. |
| **Entry Condition** | Merchant understands ongoing value. |
| **Exit Condition** | Merchant’s remaining blockers are practical (integration, FAQ), not existential trust. |
| **Prohibited Content** | Deep internal governance jargon; registry IDs; architecture diagrams; fake certifications. |
| **Mobile Behaviour** | Short principle list; full narrative preserved. |
| **Relationship to Previous** | Grounds continuity claims in restraint. |
| **Relationship to Next** | Clears the way for platform readiness (LP-13). |

**Permitted trust themes (not final copy):**

- No recommendation without evidence  
- Insufficient evidence is stated clearly  
- Purchases stop unnecessary recovery  
- Merchant data remains isolated  
- CartFlow distinguishes observation from conclusion  

---

### LP-13 — Integration Readiness

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-13` |
| **Working Name** | Integration Readiness |
| **Merchant Question** | Will this work with my commerce platform? |
| **Section Responsibility** | Clarify supported and planned integrations **truthfully**. |
| **Required Merchant Belief** | CartFlow is honest about what works today vs what is planned. |
| **Primary Evidence** | Truthful readiness states only. |
| **Permitted Secondary Visuals** | Platform names as text; **no unsupported logos**. |
| **Entry Condition** | Merchant is considering fit. |
| **Exit Condition** | Merchant knows current support vs planned without false universality. |
| **Prohibited Content** | “Works everywhere”; fabricated logos; claiming Salla/Shopify as live if scaffold-only; hiding ops-gated install reality for Zid. |
| **Mobile Behaviour** | Status list (Supported / Under validation / Planned). |
| **Relationship to Previous** | Practical trust after principle trust. |
| **Relationship to Next** | Remaining objections → FAQ (LP-14). |

**Required readiness vocabulary (binding):**

| State | Meaning |
|-------|---------|
| Currently supported | Production path exists for merchants (may still be ops-gated). |
| Under validation | Being proven; not claimable as ready. |
| Planned | Intention only; no product proof. |

**Baseline truth (as of this architecture date — must be revalidated before copy):**

| Platform | State |
|----------|-------|
| Zid | Currently supported (ops/install gated—not full self-serve) |
| Salla | Planned / scaffold |
| Shopify | Planned / scaffold |

---

### LP-14 — FAQ

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-14` |
| **Working Name** | FAQ |
| **Merchant Question** | What concerns still prevent me from starting? |
| **Section Responsibility** | Resolve only high-value objections. **Define categories only in this phase—no final answers.** |
| **Required Merchant Belief** | My remaining questions have clear, honest answers. |
| **Primary Evidence** | None required beyond truthful answers (later phase). |
| **Permitted Secondary Visuals** | None. |
| **Entry Condition** | Merchant has seen story + evidence + trust. |
| **Exit Condition** | Objections reduced; ready for calm CTA. |
| **Prohibited Content** | FAQ as second feature dump; SEO keyword stuffing; inventing answers for unready capabilities. |
| **Mobile Behaviour** | Accordion; one question open at a time. |
| **Relationship to Previous** | Catches residual concerns after integrations. |
| **Relationship to Next** | Clears path to Final CTA. |

**Approved FAQ question categories (no final answers in this pack):**

1. What CartFlow does  
2. Whether it replaces existing tools  
3. Widget impact on storefront speed  
4. WhatsApp requirements  
5. Data sufficiency / when CartFlow says “insufficient evidence”  
6. Supported platforms  
7. Setup expectations  
8. What happens when a customer purchases  

---

### LP-15 — Final CTA

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-15` |
| **Working Name** | Final CTA |
| **Merchant Question** | What is the next safe step? |
| **Section Responsibility** | Offer one clear, calm action reflecting actual commercial readiness. |
| **Required Merchant Belief** | Starting is safe and proportionate—no pressure. |
| **Primary Evidence** | None; credibility already built. |
| **Permitted Secondary Visuals** | None competitive. |
| **Entry Condition** | Story complete; objections addressed. |
| **Exit Condition** | Merchant takes the next step or leaves without coercion. |
| **Prohibited Content** | Urgency manipulation; fake scarcity; exaggerated promises; “limited offer.” |
| **Mobile Behaviour** | One primary button dominant; secondary optional (e.g. login). |
| **Relationship to Previous** | Converts resolved objections into action. |
| **Relationship to Next** | Footer for verification/contact. |

**CTA readiness (architecture constraint):**

| Candidate CTA | Readiness |
|---------------|-----------|
| Start Free → `/signup` | Ready (current commercial path) |
| Login → `/login` | Ready (secondary) |
| Book a Demo | **Deferred** until a distinct demo-booking path exists |
| Explore CartFlow | Optional secondary if a truthful explore path exists; otherwise omit |

Primary CTA for V1 architecture: **Start Free** (or constitution-equivalent calm phrasing)—not “Book a Demo” until product supports it.

---

### LP-16 — Footer

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-16` |
| **Working Name** | Footer |
| **Merchant Question** | Where can I verify, contact, or learn more? |
| **Section Responsibility** | Provide necessary legal, contact, navigation, and platform information. |
| **Required Merchant Belief** | CartFlow is a real company/product I can contact. |
| **Primary Evidence** | Real contact / legal links only. |
| **Permitted Secondary Visuals** | None. |
| **Entry Condition** | End of page. |
| **Exit Condition** | Merchant can verify or contact without reopening a marketing story. |
| **Prohibited Content** | Second navigation system; new sales pitch; fake partner logo walls. |
| **Mobile Behaviour** | Compact stacked links. |
| **Relationship to Previous** | Closes after CTA. |
| **Relationship to Next** | None. |

---

## 3. Narrative Continuity Map

```text
LP-01 Nav
  → LP-02 Hero                 (recognise problem)
  → LP-03 Problem              (abandon ≠ full problem)
  → LP-04 Reframe              (recovery actions ≠ understanding)
  → LP-05 How it works         (connected journey outline)
  → LP-06 Widget               (early evidence)
  → LP-07 WhatsApp             (continuation evidence)
  → LP-08 Dashboard            (merchant operating evidence)
  → LP-09 Knowledge            (broader identity earned)
  → LP-10 Decision Value       (understanding → decisions)
  → LP-11 Continuous Value     (value accumulates)
  → LP-12 Trust                (restraint & truth)
  → LP-13 Integrations         (platform honesty)
  → LP-14 FAQ                  (residual objections)
  → LP-15 Final CTA            (calm next step)
  → LP-16 Footer
```

**Disclosure checkpoint:** Broader-than-recovery identity may be *felt* from LP-08 onward and should be *earned as understanding* by LP-09. Category labels remain internal.

---

## 4. Architectural Review

### 4.1 Section necessity

| Section | Necessary? | Rationale |
|---------|------------|-----------|
| LP-01 | Yes | Orientation chrome; constitution-compatible if lightweight. |
| LP-02 | Yes | Constitution Hero. |
| LP-03 | Yes | Constitution Problem / Stage 1. |
| LP-04 | Yes | Constitution Difference / Stage 2. |
| LP-05 | Yes | Constitution Solution / Stage 3 outline. |
| LP-06 | Yes | Visual Evidence Law — widget primary; dedicated proof after outline. |
| LP-07 | Yes | Visual Evidence Law — WhatsApp journey primary; not “WhatsApp seller.” |
| LP-08 | Yes | Constitution Dashboard — strongest trust visual. |
| LP-09 | Yes | Constitution Knowledge Layer — disclosure earning point. |
| LP-10 | Yes | Constitution Benefits — outcomes without overclaim. |
| LP-11 | Yes | Constitution Merchant Journey — continuity. |
| LP-12 | Yes | Translates Truth Policy into merchant trust (not technical docs). |
| LP-13 | Yes (short) | Blocking commercial question; Truth Policy requires honesty. |
| LP-14 | Yes | Constitution FAQ. |
| LP-15 | Yes | Constitution Final CTA. |
| LP-16 | Yes | Legal/contact closure. |

No section is kept “because SaaS landings usually have it.”

### 4.2 Section overlap (resolved)

| Pair | Risk | Resolution |
|------|------|------------|
| LP-05 vs LP-06/07/08 | Journey vs proof | LP-05 = outline only; evidence sections own depth. |
| LP-08 vs LP-09 | Trust vs intelligence | LP-08 = operate/see; LP-09 = learn/understand (broader identity). |
| LP-09 vs LP-10 | Knowledge vs decisions | LP-09 = what is learned; LP-10 = how that changes decisions. |
| LP-10 vs LP-11 | Outcomes vs time | LP-10 = decision outcomes; LP-11 = accumulation over time. |
| LP-12 vs LP-14 | Trust vs FAQ | LP-12 = trust narrative once; FAQ = residual Q&A categories. |
| LP-13 vs FAQ#platforms | Integration | LP-13 owns readiness states; FAQ may repeat briefly, not expand false claims. |

### 4.3 Evidence availability

| Section | Truthful evidence today? | Landing-ready capture? |
|---------|--------------------------|------------------------|
| LP-06 Widget | Yes (prod storefront widget) | Capture required (landing currently leans settings). |
| LP-07 WhatsApp | Yes (engine + merchant states); journey UX partial | Capture required (prefer journey/reply/suppression over settings). |
| LP-08 Dashboard | Yes (Home / Workspace / carts) | Capture required (use current faces, not stale crops). |
| LP-09 Knowledge | Partial (KL/findings when materialised) | Requires validation + careful illustrative labeling if empty. |
| LP-13 Integrations | Zid yes; Salla/Shopify no | Text readiness only—no fake logos. |

### 4.4 Product maturity risks

- Do **not** advertise Salla/Shopify as live.  
- Do **not** claim self-serve Zid if install remains ops-gated.  
- Do **not** present Knowledge as always-on if many stores show empty until materialisation.  
- Do **not** use “Book a Demo” as primary until a real path exists.  
- Do **not** claim Meta WhatsApp production readiness beyond actual gate status.  
- Decision Workspace / Home faces evolve under CEO review—landing shots must match current production faces at copy time.

### 4.5 Narrative continuity

Each section creates the need for the next (see §3). Stage mapping:

| Story stage | Sections |
|-------------|----------|
| Stage 1 — I have a problem | LP-02, LP-03 |
| Stage 2 — Current tools don’t explain | LP-04 |
| Stage 3 — CartFlow sees what I cannot | LP-05 → LP-09 |
| Stage 4 — I understand my store | LP-10 → LP-12 |

### 4.6 Mobile continuity

Entire narrative is single-column survivable: every section’s merchant question and exit condition remain without side-by-side layouts. Evidence sections stack product proof full-width.

### 4.7 Disclosure timing

Compliant: Hero problem-first; no early category label; broader identity earned at Knowledge Layer (LP-09) after Dashboard evidence (LP-08).

### 4.8 Visual evidence hierarchy

Compliant: Dashboard, widget, WhatsApp journey, merchant workflow, and knowledge cards are **primary** in LP-06…LP-09. Illustrations/3D/effects are secondary and never Hero-dependent.

### 4.9 CTA readiness

Primary calm CTA = Start Free (`/signup`). Login secondary. Book a Demo deferred. Reflects pilot/beta maturity—not ROI self-serve claims.

---

## 5. Decision Table

| Section | Keep | Merge | Defer | Remove | Reason | Evidence Readiness |
|---------|:----:|:-----:|:-----:|:------:|--------|--------------------|
| LP-01 Navigation | ✓ | | | | Required orientation; must stay lightweight | Ready |
| LP-02 Hero | ✓ | | | | Constitution Hero; problem-first | Partially ready (preview optional; no 3D dependency) |
| LP-03 Problem Recognition | ✓ | | | | Stage 1 urgency; unique question | Ready (illustrative situations OK if marked) |
| LP-04 Recovery Limitation Reframe | ✓ | | | | Constitution Difference; no competitor attack | Ready (conceptual) |
| LP-05 How CartFlow Works | ✓ | | | | Constitution Solution; outline only | Ready (conceptual) |
| LP-06 Widget Evidence | ✓ | | | | Primary visual evidence; unique question | Requires product evidence capture |
| LP-07 WhatsApp Journey Evidence | ✓ | | | | Primary visual evidence; not WA-seller positioning | Requires product evidence capture |
| LP-08 Dashboard Evidence | ✓ | | | | Strongest trust visual; constitution Dashboard | Requires product evidence capture (current faces) |
| LP-09 Knowledge Layer Discovery | ✓ | | | | Disclosure earning point; constitution Knowledge | Requires validation (+ illustrative rules) |
| LP-10 Decision Value | ✓ | | | | Constitution Benefits; distinct from knowledge display | Partially ready |
| LP-11 Continuous Value Journey | ✓ | | | | Constitution Merchant Journey; continuity ≠ ML | Partially ready |
| LP-12 Trust and Governance | ✓ | | | | Merchant-language Truth Policy; not FAQ dump | Partially ready |
| LP-13 Integration Readiness | ✓ | | | | Blocking fit question; honesty required | Partially ready (Zid); Planned others |
| LP-14 FAQ | ✓ | | | | Constitution FAQ; categories only this phase | Ready to define; answers later |
| LP-15 Final CTA | ✓ | | | | Calm convert; maturity-aligned | Ready (`/signup`); Demo deferred |
| LP-16 Footer | ✓ | | | | Legal/contact; not second nav | Ready |

**Merge/Remove/Defer outcomes:** No section removed. No merge required after overlap resolution. **Deferred capability inside Keep sections:** Book a Demo CTA; Salla/Shopify as supported; always-on Knowledge claims.

---

## 6. Approval Gate

This architecture does **not** authorise redesign, copy, wireframes, screenshot selection, 3D direction, Figma, or frontend implementation.

See pack `README.md` STOP gate.
