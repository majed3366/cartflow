# Landing Page Wireframe V1

**Status:** First design execution phase — structural layout only.  
**Date (UTC):** 2026-07-29  
**Governing authorities:** Constitution · IA · Copy Architecture · Evidence Readiness · Storyboard · Visual Narrative  

**Non-goals:** No colours, fonts, components, illustrations, screenshot selection/capture, 3D assets, animations, hi-fi Figma, or frontend.

This document defines **structure**, not appearance. Placeholders only.

---

## 0. Global wireframe rules (binding)

1. One dominant focus per section.  
2. One primary scroll direction (top → bottom).  
3. No competing hero objects.  
4. Product evidence precedes deep explanation in evidence sections.  
5. Copy never overwhelms screenshots when Evidence Weight is Primary.  
6. Screenshots never become decoration or wallpaper.  
7. 3D placeholders never replace evidence.  
8. Mobile retains the same narrative sequence (LP-01…16).  
9. Each section remains understandable in isolation.  
10. Screenshot placeholders only where Evidence Readiness allows eventual eligibility (see §0.1).  

### 0.1 Evidence placeholder eligibility

| Section | Screenshot placeholder | Status per Evidence Readiness |
|---------|------------------------|-------------------------------|
| LP-02 | Optional restrained preview | After capture eligibility (CAP-01 optional) |
| LP-03–05 | None (concept/illustrative only) | No primary product proof |
| LP-06 | **Required** storefront widget | Blocked until CAP-02/03 — placeholder allowed in wireframe |
| LP-07 | **Required** WA journey | Blocked until CAP-04+ — placeholder allowed |
| LP-08 | **Required** dashboard | Ready after fresh capture — placeholder allowed |
| LP-09 | **Required** knowledge + state | RV-gated themes — placeholder allowed with honesty state |
| LP-10 | Optional decision fragment | Bounded |
| LP-11–16 | None as product proof | — |

Wireframe placeholders **do not** authorise capture or claim publication.

---

## 1. Height & time vocabulary

| Token | Approx. desktop viewport fractions | Approx. mobile |
|-------|-------------------------------------|----------------|
| XS | ~0.25–0.4 vh | ~0.3–0.5 vh |
| S | ~0.5–0.75 vh | ~0.6–0.9 vh |
| M | ~0.85–1.1 vh | ~1.0–1.4 vh |
| L | ~1.1–1.6 vh | ~1.3–1.8 vh |
| XL | ~1.6–2.2 vh | ~1.8–2.5 vh |

Scroll times align with Storyboard Expected Viewing Time.

---

## 2. Section wireframes LP-01 … LP-16

### WF-01 — LP-01 Navigation

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-01` |
| **Desktop Position** | Fixed/sticky top band |
| **Mobile Position** | Fixed/sticky top band |
| **Approximate Height** | XS (bar only) |
| **Viewport Behaviour** | Always available; never steals Hero |
| **Visual Anchor Position** | Brand start-edge |
| **Copy Area** | Labels only (anchors + actions) |
| **Evidence Placeholder** | None |
| **CTA Position** | End-edge primary; Login secondary |
| **Whitespace Allocation** | Minimal inside bar |
| **Allowed Layout Pattern** | Single horizontal bar |
| **Transition Into Next** | Hero begins immediately below |
| **Expected Scroll Time** | &lt;2s |
| **Reading Priority** | Brand → primary CTA |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | Sticky only |

---

### WF-02 — LP-02 Hero

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-02` |
| **Desktop Position** | First full content block (above the fold) |
| **Mobile Position** | First full content block (above the fold) |
| **Approximate Height** | M–L (~1 vh preferred) |
| **Viewport Behaviour** | Primary above-the-fold composition |
| **Visual Anchor Position** | Headline block (dominant) |
| **Copy Area** | Headline + one support + CTA group |
| **Evidence Placeholder** | Optional restrained preview below or end-side (subordinate) |
| **CTA Position** | Under support line |
| **Whitespace Allocation** | Generous below Hero before Problem |
| **Allowed Layout Pattern** | Copy-primary; optional single preview |
| **Transition Into Next** | Soft silence → Problem |
| **Expected Scroll Time** | 8–15s |
| **Reading Priority** | Headline → support → CTA → preview |
| **Screenshot Placeholder** | `PH-PREVIEW` optional |
| **3D Placeholder** | None as dependency; Atmosphere none preferred |
| **Motion Placeholder** | Soft entrance |

**Above the fold (canonical):** Brand bar + Hero headline + support + primary CTA. Preview may fall below fold on short mobile viewports.

---

### WF-03 — LP-03 Problem Recognition

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-03` |
| **Desktop Position** | After Hero |
| **Mobile Position** | After Hero |
| **Approximate Height** | L |
| **Viewport Behaviour** | Multi-beat scroll |
| **Visual Anchor Position** | Core problem statement |
| **Copy Area** | Statement + situation beats (stacked) |
| **Evidence Placeholder** | None (context beats only) |
| **CTA Position** | None |
| **Whitespace Allocation** | Between beats |
| **Allowed Layout Pattern** | Vertical beat list (desktop may use 2-col beats **only if** one beat remains dominant — prefer stack) |
| **Transition Into Next** | Tension → Reframe |
| **Expected Scroll Time** | 15–25s |
| **Reading Priority** | Idea → beats |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | Beat reveal |

---

### WF-04 — LP-04 Recovery Limitation Reframe

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-04` |
| **Desktop Position** | After Problem |
| **Mobile Position** | After Problem |
| **Approximate Height** | S–M |
| **Viewport Behaviour** | Single contrast unit |
| **Visual Anchor Position** | Contrast pair |
| **Copy Area** | Contrast + fairness clause |
| **Evidence Placeholder** | None |
| **CTA Position** | None |
| **Whitespace Allocation** | After section (silence) |
| **Allowed Layout Pattern** | Two-part contrast (desktop side-by-side **or** stacked; mobile stacked) |
| **Transition Into Next** | Hope → Journey outline |
| **Expected Scroll Time** | 10–15s |
| **Reading Priority** | A → B → fairness |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | Contrast settle |

---

### WF-05 — LP-05 How CartFlow Works

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-05` |
| **Desktop Position** | After Reframe |
| **Mobile Position** | After Reframe |
| **Approximate Height** | M–L |
| **Viewport Behaviour** | Scan steps |
| **Visual Anchor Position** | Step sequence |
| **Copy Area** | Short intro + step labels |
| **Evidence Placeholder** | None (no product screenshot collage) |
| **CTA Position** | None |
| **Whitespace Allocation** | Before Widget (prepare evidence climb) |
| **Allowed Layout Pattern** | Vertical steps (desktop may number horizontally only if scan remains single-path — prefer vertical) |
| **Transition Into Next** | Silence → first product evidence |
| **Expected Scroll Time** | 10–20s |
| **Reading Priority** | Steps in order |
| **Screenshot Placeholder** | **Forbidden** |
| **3D Placeholder** | Optional minimal journey marks only |
| **Motion Placeholder** | Step reveal |

---

### WF-06 — LP-06 Widget Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-06` |
| **Desktop Position** | First primary evidence section |
| **Mobile Position** | Same |
| **Approximate Height** | L |
| **Viewport Behaviour** | Inspect pause |
| **Visual Anchor Position** | Storefront widget placeholder (dominant) |
| **Copy Area** | Short block ≤1/3 desktop width or above/below on mobile |
| **Evidence Placeholder** | `PH-WIDGET` (storefront — not settings) |
| **CTA Position** | None |
| **Whitespace Allocation** | Before section entry |
| **Allowed Layout Pattern** | Evidence-primary: copy + single evidence |
| **Transition Into Next** | After-store question → WA |
| **Expected Scroll Time** | 15–25s |
| **Reading Priority** | Evidence → short copy (or copy then evidence on mobile — see Mobile Spec) |
| **Screenshot Placeholder** | `PH-WIDGET` required |
| **3D Placeholder** | Frame only, never replace |
| **Motion Placeholder** | Reveal/settle |

---

### WF-07 — LP-07 WhatsApp Journey Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-07` |
| **Desktop Position** | After Widget |
| **Mobile Position** | After Widget |
| **Approximate Height** | L |
| **Viewport Behaviour** | Inspect pause |
| **Visual Anchor Position** | Journey/state placeholder |
| **Copy Area** | Short ≤1/3 desktop |
| **Evidence Placeholder** | `PH-WA-JOURNEY` (+ optional stop state) |
| **CTA Position** | None |
| **Whitespace Allocation** | Between WA and Dashboard (air before climax) |
| **Allowed Layout Pattern** | Evidence-primary single journey |
| **Transition Into Next** | Merchant view question → Dashboard |
| **Expected Scroll Time** | 15–25s |
| **Reading Priority** | Journey → meaning |
| **Screenshot Placeholder** | `PH-WA-JOURNEY` required |
| **3D Placeholder** | Phone frame optional subordinate |
| **Motion Placeholder** | State progression |

---

### WF-08 — LP-08 Dashboard Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-08` |
| **Desktop Position** | Ops evidence climax |
| **Mobile Position** | Same |
| **Approximate Height** | L–XL |
| **Viewport Behaviour** | **Strongest inspect pause** |
| **Visual Anchor Position** | Dashboard UI placeholder (full dominant) |
| **Copy Area** | One outcome sentence; ≤1/3 desktop if beside |
| **Evidence Placeholder** | `PH-DASHBOARD` (+ optional `PH-ATTENTION`) |
| **CTA Position** | None |
| **Whitespace Allocation** | **Required before** section |
| **Allowed Layout Pattern** | Screenshot owns; single shot |
| **Transition Into Next** | Silence → Knowledge discovery |
| **Expected Scroll Time** | 20–35s |
| **Reading Priority** | Screenshot → outcome line |
| **Screenshot Placeholder** | `PH-DASHBOARD` required |
| **3D Placeholder** | **Forbidden** |
| **Motion Placeholder** | Minimal settle |

---

### WF-09 — LP-09 Knowledge Layer Discovery

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-09` |
| **Desktop Position** | After Dashboard |
| **Mobile Position** | After Dashboard |
| **Approximate Height** | L |
| **Viewport Behaviour** | Discovery pause |
| **Visual Anchor Position** | Knowledge card placeholder |
| **Copy Area** | Medium; must not bury card |
| **Evidence Placeholder** | `PH-KNOWLEDGE` + `PH-INSUFFICIENT` |
| **CTA Position** | None |
| **Whitespace Allocation** | **Required before**; soft after |
| **Allowed Layout Pattern** | Single knowledge object + honesty state |
| **Transition Into Next** | Decision value |
| **Expected Scroll Time** | 20–30s |
| **Reading Priority** | Card → evidence state → meaning |
| **Screenshot Placeholder** | `PH-KNOWLEDGE` required |
| **3D Placeholder** | **Forbidden** |
| **Motion Placeholder** | Calm card/state reveal |

---

### WF-10 — LP-10 Decision Value

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-10` |
| **Desktop Position** | After Knowledge |
| **Mobile Position** | After Knowledge |
| **Approximate Height** | M–L |
| **Viewport Behaviour** | Outcome list |
| **Visual Anchor Position** | Outcome list |
| **Copy Area** | Outcomes (primary) |
| **Evidence Placeholder** | Optional `PH-DECISION` fragment |
| **CTA Position** | None |
| **Whitespace Allocation** | Soft |
| **Allowed Layout Pattern** | Vertical outcomes; optional small UI |
| **Transition Into Next** | Continuity |
| **Expected Scroll Time** | 15–20s |
| **Reading Priority** | Outcomes |
| **Screenshot Placeholder** | Optional only |
| **3D Placeholder** | None |
| **Motion Placeholder** | List settle |

---

### WF-11 — LP-11 Continuous Value Journey

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-11` |
| **Desktop Position** | After Decision Value |
| **Mobile Position** | Same |
| **Approximate Height** | S–M |
| **Viewport Behaviour** | Faster reinforce |
| **Visual Anchor Position** | Progression strip |
| **Copy Area** | Short conditional lines |
| **Evidence Placeholder** | None |
| **CTA Position** | None |
| **Whitespace Allocation** | YES (breathe) |
| **Allowed Layout Pattern** | Vertical progression |
| **Transition Into Next** | Trust |
| **Expected Scroll Time** | 10–15s |
| **Reading Priority** | Progression |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | Soft progression |

---

### WF-12 — LP-12 Trust and Governance

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-12` |
| **Desktop Position** | After Continuity |
| **Mobile Position** | Same |
| **Approximate Height** | M |
| **Viewport Behaviour** | Quiet principles |
| **Visual Anchor Position** | Core restraint line |
| **Copy Area** | Principle list |
| **Evidence Placeholder** | Optional reuse stop-state (small) |
| **CTA Position** | None |
| **Whitespace Allocation** | **YES** |
| **Allowed Layout Pattern** | Text-primary silence |
| **Transition Into Next** | Integrations |
| **Expected Scroll Time** | 12–18s |
| **Reading Priority** | Restraint → principles |
| **Screenshot Placeholder** | Optional small |
| **3D Placeholder** | None |
| **Motion Placeholder** | Near zero |

---

### WF-13 — LP-13 Integration Readiness

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-13` |
| **Desktop Position** | After Trust |
| **Mobile Position** | Same |
| **Approximate Height** | S |
| **Viewport Behaviour** | Fast status scan |
| **Visual Anchor Position** | Status rows |
| **Copy Area** | Platform + state |
| **Evidence Placeholder** | Text status only (`PH-INTEGRATION-TEXT`) |
| **CTA Position** | None |
| **Whitespace Allocation** | YES |
| **Allowed Layout Pattern** | Single-column status list |
| **Transition Into Next** | FAQ |
| **Expected Scroll Time** | 8–12s |
| **Reading Priority** | Rows |
| **Screenshot Placeholder** | No logo wall |
| **3D Placeholder** | None |
| **Motion Placeholder** | None |

---

### WF-14 — LP-14 FAQ

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-14` |
| **Desktop Position** | After Integrations |
| **Mobile Position** | Same |
| **Approximate Height** | Variable (M–XL) |
| **Viewport Behaviour** | Optional dive |
| **Visual Anchor Position** | Accordion list |
| **Copy Area** | Q/A |
| **Evidence Placeholder** | None |
| **CTA Position** | None inside body |
| **Whitespace Allocation** | YES |
| **Allowed Layout Pattern** | Single-column accordion |
| **Transition Into Next** | Final CTA |
| **Expected Scroll Time** | 0–60s |
| **Reading Priority** | Question → answer |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | Accordion only |

---

### WF-15 — LP-15 Final CTA

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-15` |
| **Desktop Position** | After FAQ |
| **Mobile Position** | Same |
| **Approximate Height** | S–M |
| **Viewport Behaviour** | Decision pause |
| **Visual Anchor Position** | Primary button |
| **Copy Area** | Short invitation |
| **Evidence Placeholder** | **None** |
| **CTA Position** | Dominant center/start of content column |
| **Whitespace Allocation** | **Required before** |
| **Allowed Layout Pattern** | Invitation + primary (+ secondary below) |
| **Transition Into Next** | Footer |
| **Expected Scroll Time** | 5–10s |
| **Reading Priority** | Invitation → primary CTA |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | Affordance only |

---

### WF-16 — LP-16 Footer

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-16` |
| **Desktop Position** | Page end |
| **Mobile Position** | Page end |
| **Approximate Height** | XS–S |
| **Viewport Behaviour** | Utility close |
| **Visual Anchor Position** | Contact / legal cluster |
| **Copy Area** | Links |
| **Evidence Placeholder** | None |
| **CTA Position** | Utility login only |
| **Whitespace Allocation** | Compact |
| **Allowed Layout Pattern** | Compact link groups (not second nav mega) |
| **Transition Into Next** | None |
| **Expected Scroll Time** | &lt;5s |
| **Reading Priority** | Contact → legal |
| **Screenshot Placeholder** | None |
| **3D Placeholder** | None |
| **Motion Placeholder** | None |

---

## 3. Contradiction log

| ID | Finding |
|----|---------|
| CX-WF-01 | None. Structure follows Storyboard evidence intro map and Visual Narrative hierarchy. |

---

## 4. Review checklist

| Lens | Result |
|------|--------|
| Every section one layout owner? | Yes — see Layout Contracts |
| Reading path obvious? | Yes — defined Primary Reading Order |
| Evidence where approved? | Yes — LP-06 first, then 07, 08 climax, 09 discovery |
| Screenshot placeholders only for eligible families? | Yes — gated; settings forbidden |
| Scroll continuous / peaks match Storyboard? | Yes — inspect at 06–09; peak 08 |
| Mobile coherent? | Yes — Mobile Spec canonical |
| Governance / unsupported capability? | Placeholders must not imply E6 publishability; Demo CTA absent; no logo wall |
