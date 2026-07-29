# Landing Page Section Contracts V1

**Status:** Binding architectural contracts — governance only.  
**Date (UTC):** 2026-07-29  
**Parent:** [`LANDING_PAGE_INFORMATION_ARCHITECTURE_V1.md`](./LANDING_PAGE_INFORMATION_ARCHITECTURE_V1.md)  
**Governing authority:** Landing Page Constitution V1  

Each approved section answers **one** merchant question. No section may inherit another section’s responsibility without explicit architectural justification recorded here.

---

## Contract schema (every section)

| Clause | Meaning |
|--------|---------|
| **A. Single Owner** | One merchant question; exclusive responsibility |
| **B. Claim Boundary** | Allowed claims / forbidden claims |
| **C. Evidence Requirement** | Every visual classified |
| **D. Content Readiness** | Ready / Partially ready / Requires capture / Requires validation / Deferred |
| **E. Mobile Contract** | Remains / stacks / simplifies / disappears |
| **F. Removal Test** | Understanding lost if removed |

### Evidence classification vocabulary

| Class | Definition |
|-------|------------|
| **Product Evidence** | Real product UI or governed product output |
| **Merchant Journey Evidence** | Real end-to-end customer/merchant path representation |
| **Operational Evidence** | Real merchant operating states (attention, recovery, closure) |
| **Illustrative Evidence** | Clearly marked non-production example used only to teach |
| **Decorative Support** | Secondary visual that must never compete with or obscure primary evidence |

---

## LP-01 — Navigation

### A. Single Owner

- **Question:** Where am I, and how do I begin?
- **Owns:** Brand presence, light orientation, one calm begin path.
- **Does not own:** Storytelling, product proof, category positioning.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| CartFlow brand; links to page anchors; calm Start / Login | Feature claims; ROI; category labels; urgency badges; multi-CTA competition with Hero |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Logo / wordmark | Decorative Support (brand) |
| CTA control | Operational Evidence (path exists: `/signup`, `/login`) |

### D. Content Readiness

**Ready from existing product** (paths exist).

### E. Mobile Contract

- Remains: brand + primary CTA  
- Simplifies: secondary nav into compact/collapse  
- Disappears: any desktop-only link sprawl that competes with Hero  

### F. Removal Test

Without Navigation, merchants lose a calm begin path and brand orientation—especially on long mobile scrolls. **Keep.**

---

## LP-02 — Hero

### A. Single Owner

- **Question:** Does CartFlow address a problem I recognise?
- **Owns:** Problem-first attention capture and immediate value framing.
- **Does not own:** Reframe (LP-04), journey depth (LP-05), product tours (LP-06+), category naming.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Merchant-recognisable problem (lost revenue, abandon, unknown behaviour); calm CTA | “Commerce Intelligence Platform”; fake metrics; AI revolution claims; feature grids; desperate CTAs |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Optional restrained real preview | Product Evidence |
| Atmospheric gradient/pattern | Decorative Support (only if non-competing) |
| 3D Hero composition | **Forbidden as dependency**; if ever used, Decorative Support only and never primary |

### D. Content Readiness

**Partially ready** — copy/architecture ready; optional product preview requires capture later.

### E. Mobile Contract

- Remains: problem, one support line, primary CTA  
- Stacks: preview below copy  
- Simplifies: secondary CTA optional  
- Disappears: any dual-hero or decorative competition  

### F. Removal Test

Without Hero, merchants never lock onto the problem frame. **Keep.**

---

## LP-03 — Problem Recognition

### A. Single Owner

- **Question:** Is the abandoned cart itself the full problem?
- **Owns:** Urgency via situations beyond the abandon event.
- **Does not own:** Solution journey; recommendations; competitor critique.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Hesitation, return behaviour, failed recovery, product friction, insufficient evidence as real merchant situations | Final recommendations; invented statistics; “your store loses X%” without truth |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Situation beats | Illustrative Evidence (must be recognisable, not fake metrics) |
| Optional problem-state product crop | Product Evidence / Operational Evidence |

### D. Content Readiness

**Ready from existing product** conceptually; situation framing may be illustrative.

### E. Mobile Contract

- Remains: full situation sequence  
- Stacks: one beat per block  
- Disappears: multi-column comparison layouts  

### F. Removal Test

Without this section, merchants may think CartFlow is only cart-reminders. **Keep.**

---

## LP-04 — Recovery Limitation Reframe

### A. Single Owner

- **Question:** Why are reminders and discounts not enough?
- **Owns:** Category reframe without competitor attack.
- **Does not own:** CartFlow feature proof; knowledge claims.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Difference between sending recovery actions and learning before/after those actions | Unsupported superiority; competitor naming; fake uplift charts |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Contrast diagram (action vs understanding) | Illustrative Evidence |
| Decorative connectors | Decorative Support |

### D. Content Readiness

**Ready from existing product** (conceptual).

### E. Mobile Contract

- Remains: both sides of contrast  
- Stacks: A then B  
- Simplifies: remove decorative connectors if they clutter  

### F. Removal Test

Without reframe, Stage 2 (“current tools don’t explain”) collapses; Hero problem alone is insufficient. **Keep.**

---

## LP-05 — How CartFlow Works

### A. Single Owner

- **Question:** What does CartFlow actually do?
- **Owns:** Connected conceptual journey outline only.
- **Does not own:** Deep widget/WhatsApp/dashboard/knowledge proof (explicitly deferred to LP-06…LP-09).

**Architectural justification for split:** One Purpose Per Section — outline vs evidence are different merchant questions (“what does it do?” vs “show me”).

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Behaviour → widget → recovery → WhatsApp → movement/purchase evidence → merchant understanding as a story | Technical architecture; registry names; ML; category platform claims; deep tours |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Journey steps | Illustrative Evidence / Merchant Journey Evidence (conceptual) |
| Optional tiny product anchors | Product Evidence (must not become a tour) |

### D. Content Readiness

**Ready from existing product** (conceptual).

### E. Mobile Contract

- Remains: full step sequence  
- Stacks: vertical steps  
- Disappears: horizontal pipelines that require desktop width  

### F. Removal Test

Without outline, evidence sections feel like disconnected feature demos. **Keep.**

---

## LP-06 — Widget Evidence

### A. Single Owner

- **Question:** How does CartFlow understand hesitation early?
- **Owns:** Widget as early understanding/recovery surface.
- **Does not own:** WhatsApp continuation; dashboard operations; knowledge synthesis.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Real hesitation capture / early storefront understanding | Settings UI as if it were customer UX; fake reason rates; universal self-serve install if untrue |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Live storefront widget UI | Product Evidence (**required primary**) |
| Hesitation choices | Product Evidence / Merchant Journey Evidence |
| Framing chrome | Decorative Support only |

### D. Content Readiness

**Requires product evidence capture** (production widget exists; landing-ready storefront shots needed).

### E. Mobile Contract

- Remains: widget evidence + question outcome  
- Stacks: copy then full-width evidence  
- Simplifies: secondary framing removed first  

### F. Removal Test

Without widget evidence, early-understanding claims fail Visual Evidence Law. **Keep.**

---

## LP-07 — WhatsApp Journey Evidence

### A. Single Owner

- **Question:** What happens when recovery continues beyond the store?
- **Owns:** Governed WhatsApp continuation layer.
- **Does not own:** Positioning CartFlow as a WhatsApp product; Meta marketplace claims.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Continuation, response states, merchant follow-up, purchase stop/suppression where real | “Just send WhatsApp”; delivery SLAs; fake reply/conversion rates; settings-as-journey misrepresentation |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Journey / thread / state representation | Merchant Journey Evidence / Operational Evidence (**primary**) |
| Merchant follow-up state | Operational Evidence |
| Purchase suppression/closure | Operational Evidence |
| Invented phone UI | Forbidden |

### D. Content Readiness

**Requires product evidence capture** (engine real; journey-grade shots needed; Meta path gated—do not overclaim).

### E. Mobile Contract

- Remains: journey + closure/suppression truth  
- Stacks: states vertically  
- Simplifies: decorative device frames removed if they obscure evidence  

### F. Removal Test

Without this section, merchants may assume CartFlow ends at the widget or is “WhatsApp spam.” **Keep.**

---

## LP-08 — Dashboard Evidence

### A. Single Owner

- **Question:** What will I actually see as a merchant?
- **Owns:** Merchant operating credibility via real dashboard experience.
- **Does not own:** Knowledge-layer discovery narrative (LP-09); category labeling.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Real attention/recovery/movement clarity merchants see | Fake KPIs; outdated faces presented as current without truth; 3D screenshot cages; early category claims |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Home / Workspace / carts (current production faces) | Product Evidence / Operational Evidence (**primary**) |
| 3D / glass decoration | Decorative Support — **prefer absent** |

### D. Content Readiness

**Requires product evidence capture** (surfaces exist; must use current faces).

### E. Mobile Contract

- Remains: one dominant real screenshot + outcome sentence  
- Stacks: full-width  
- Disappears: multi-screenshot collages that dilute recognition  

### F. Removal Test

Without dashboard evidence, trust collapses into marketing assertion. **Keep.**

---

## LP-09 — Knowledge Layer Discovery

### A. Single Owner

- **Question:** What does CartFlow learn that I could not see before?
- **Owns:** Earned broader identity via knowledge evidence.
- **Does not own:** Decision outcome lists (LP-10); technical governance exposition (LP-12).

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Governed knowledge/insight presentation; confidence; insufficient-data honesty | Fabricated findings; “Commerce Intelligence Platform” as a claimed category banner; always-on intelligence if empty-state common; guaranteed advice |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Knowledge cards / findings UI | Product Evidence (**primary when available**) |
| Evidence status / confidence / insufficient | Operational Evidence |
| Non-real example | Illustrative Evidence (**must be labeled**) |
| AI-brain art | Decorative Support — forbidden as primary |

### D. Content Readiness

**Requires validation** (capability partial; empty/materialisation risk). Capture only when truthful store evidence exists; otherwise labeled illustrative or section scope reduced at copy time.

### E. Mobile Contract

- Remains: at least one knowledge object + insufficient-evidence honesty  
- Stacks: cards  
- Simplifies: secondary pattern examples  

### F. Removal Test

Without this section, Disclosure Law fails—broader identity never earns itself. **Keep.**

---

## LP-10 — Decision Value

### A. Single Owner

- **Question:** How does this understanding help me run the store better?
- **Owns:** Practical decision outcomes from understanding.
- **Does not own:** Showing knowledge objects (LP-09); time-accumulation story (LP-11).

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Attention, problem separation, hesitation patterns, avoiding ineffective actions, acting under insufficient evidence | Guaranteed autonomous advice; ROI %; growth multipliers; feature laundry list |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Outcome list anchored to previously shown product | Illustrative Evidence or Operational Evidence |
| Decision Workspace language crop (optional) | Product Evidence |
| Icon rows as decoration | Decorative Support — avoid feature grids |

### D. Content Readiness

**Partially ready** — outcomes must stay inside proven product behaviours.

### E. Mobile Contract

- Remains: outcome list  
- Stacks: one outcome per row  
- Disappears: icon clusters that become feature marketing  

### F. Removal Test

Without Decision Value, knowledge feels academic—Stage 4 confidence weakens. **Keep.**

---

## LP-11 — Continuous Value Journey

### A. Single Owner

- **Question:** Does CartFlow become more useful over time?
- **Owns:** Continuity from daily recovery to accumulated understanding.
- **Does not own:** One-shot decision outcomes (LP-10); ML mythology.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Observe → recover → track → evidence → knowledge → better decisions as continuity | “AI that learns by itself”; fake trend charts; unsupported ML claims |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Progression journey | Merchant Journey Evidence (conceptual) / Illustrative Evidence |
| Small real anchors reused | Product Evidence |

### D. Content Readiness

**Partially ready** — continuity is real as product story; must not invent learning curves.

### E. Mobile Contract

- Remains: full progression  
- Stacks: vertical  
- Simplifies: decorative timeline art  

### F. Removal Test

Without continuity, CartFlow looks like a campaign tool, not a store companion. **Keep.**

---

## LP-12 — Trust and Governance

### A. Single Owner

- **Question:** Can I trust what CartFlow tells me?
- **Owns:** Merchant-language truth/restraint principles.
- **Does not own:** FAQ Q&A (LP-14); deep architecture education.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Evidence before recommendation; insufficient stated; purchase stops recovery; data isolation; observation ≠ conclusion | Registry IDs; internal constitution jargon; fake compliance seals |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Principle statements tied to real behaviours | Operational Evidence (behavioural, not screenshot-required) |
| Optional purchase-stop proof crop | Product Evidence / Operational Evidence |

### D. Content Readiness

**Partially ready** — behaviours exist; merchant translation required later (not in this pack).

### E. Mobile Contract

- Remains: all trust themes in short form  
- Stacks: principle list  
- Disappears: technical appendices  

### F. Removal Test

Without Trust, evidence-heavy pages still feel risky for cautious merchants. **Keep.**

---

## LP-13 — Integration Readiness

### A. Single Owner

- **Question:** Will this work with my commerce platform?
- **Owns:** Truthful supported / under validation / planned states.
- **Does not own:** Full setup FAQ detail (may echo in LP-14).

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Zid as currently supported with honest install/ops caveats; Salla/Shopify as planned | “Works everywhere”; unsupported logos; claiming scaffold platforms as live |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Readiness status table/list | Operational Evidence (truth state) |
| Platform logos | **Forbidden** unless officially allowed and accurately representing support |

### D. Content Readiness

**Partially ready** — Zid supported (ops-gated); others planned. Revalidate before copy.

### E. Mobile Contract

- Remains: three-state readiness list  
- Stacks: platform rows  
- Disappears: logo walls  

### F. Removal Test

Without this section, platform-fit blockers force merchants to invent answers—Truth Policy risk. **Keep (short).**

---

## LP-14 — FAQ

### A. Single Owner

- **Question:** What concerns still prevent me from starting?
- **Owns:** High-value objection categories only.
- **Does not own:** Primary storytelling; primary evidence; trust narrative (already in LP-12).

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Honest answers to approved categories (later phase) | Inventing readiness; SEO feature dumps; contradicting LP-13 |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Accordion UI | Decorative Support / none |
| Answers | Must cite Product / Operational truth—no Illustrative presented as Product |

### D. Content Readiness

**Ready** to hold categories; **Deferred** final answers to copy phase after approval.

### E. Mobile Contract

- Remains: all approved categories  
- Stacks: accordion  
- Simplifies: long answers later  

### F. Removal Test

Without FAQ, residual blockers convert curiosity into drop-off. **Keep.**

---

## LP-15 — Final CTA

### A. Single Owner

- **Question:** What is the next safe step?
- **Owns:** One calm conversion action aligned to readiness.
- **Does not own:** New claims; new evidence; urgency theatre.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Start Free / Understand Your Store style calm CTA to real path (`/signup`); optional Login | Buy now; limited offer; don’t miss out; Book a Demo as primary before path exists; exaggerated promises |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| CTA control | Operational Evidence (path readiness) |
| Background flourish | Decorative Support — optional, non-competing |

### D. Content Readiness

**Ready from existing product** for `/signup` + `/login`. **Deferred:** Book a Demo.

### E. Mobile Contract

- Remains: one primary CTA  
- Simplifies: secondary under primary  
- Disappears: multi-offer button groups  

### F. Removal Test

Without Final CTA, narrative ends without a safe action. **Keep.**

---

## LP-16 — Footer

### A. Single Owner

- **Question:** Where can I verify, contact, or learn more?
- **Owns:** Legal, contact, minimal verification links.
- **Does not own:** Marketing story; second sitemap of features.

### B. Claim Boundary

| Allowed | Forbidden |
|---------|-----------|
| Real contact, legal, login | Fake partners; logo walls; renewed pitch |

### C. Evidence Requirement

| Visual | Class |
|--------|-------|
| Links / contact | Operational Evidence |
| Partner logos | Forbidden unless true |

### D. Content Readiness

**Ready from existing product** (contact patterns exist; expand only with real legal pages).

### E. Mobile Contract

- Remains: contact + essential legal  
- Stacks: compact  
- Disappears: redundant nav clones  

### F. Removal Test

Without Footer, verification/contact trust fails at the last mile. **Keep.**

---

## Cross-section inheritance rules

1. **No silent inheritance.** If a later section restates an earlier claim, it must advance a new belief (proof → implication → trust), not repeat the same job.
2. **Evidence chain exclusivity.** LP-06, LP-07, LP-08, LP-09 each own one primary evidence family; they must not become a combined “components” collage (current landing anti-pattern vs Constitution).
3. **Disclosure lock.** Only LP-09 may complete the earned broader-identity realisation. Earlier sections may foreshadow via evidence, not via category labels.
4. **CTA maturity lock.** LP-01 and LP-15 must share the same readiness-aligned primary action model.

---

## Contract compliance checklist (pre-copy / pre-design)

- [ ] Every section still answers exactly one merchant question  
- [ ] No visual lacks an evidence class  
- [ ] No section marked Ready claims a Deferred capability  
- [ ] Mobile preserves question + exit condition for all Keep sections  
- [ ] Removal Test still fails (understanding would be lost) for every Keep section  
- [ ] Landing Page Constitution V1 laws intact (especially Disclosure, Visual Evidence, Truth, Mobile First, Calm CTA)  
