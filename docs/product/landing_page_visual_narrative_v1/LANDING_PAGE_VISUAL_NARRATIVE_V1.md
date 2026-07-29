# Landing Page Visual Narrative V1

**Status:** Governed visual storytelling system — narrative only.  
**Date (UTC):** 2026-07-29  
**Governing authorities:**  
- Landing Page Constitution V1  
- Landing Page Information Architecture V1  
- Landing Page Copy Architecture V1  
- Landing Page Evidence Readiness V1  
- Landing Page Storyboard V1  

**Non-goals:** No wireframes. No Figma. No colours, typography, spacing, grids, or components. No screenshot capture/selection. No 3D generation. No frontend.

This document defines **how the product tells its story visually** — a narrative system, not a design system.

---

## 1. Visual storytelling philosophy

The landing page sells **confidence** through **product truth**.

Visuals exist to make the merchant believe:

> CartFlow understands what happens in my store — not only that it can send a reminder.

Therefore:

1. **Product evidence is the visual hero** whenever it is present.  
2. Frames, devices, and atmosphere serve evidence — never replace it.  
3. Empty space communicates calm confidence — not a need to fill.  
4. Motion guides attention — never performs.  
5. Broader identity is **seen** through Knowledge evidence (LP-09), not through category graphics.

### Capability ≠ visual publishability

Visual Narrative inherits Evidence Readiness: a surface may exist in product and still be **ineligible** as a landing Hero Object until capture/validation gates pass.

---

## 2. Narrative object roles (exclusive)

Every visual element must belong to **exactly one** role:

| Role | Purpose |
|------|---------|
| **Hero Object** | Primary product truth in the section; owns attention |
| **Evidence Object** | Reinforces product truth (states, journeys, confirmations) |
| **Supporting Object** | Frames evidence (devices, browser chrome, storefront windows) |
| **Context Object** | Situates the merchant’s world without proving capability (situation scenes) |
| **Atmosphere Object** | Feeling only (depth, light, soft shapes) — never explains |
| **Navigation Object** | Guides movement (buttons, anchors, indicators) |

**Hard rule:** No object may hold two roles at once.  
If a phone frame starts competing with the screenshot inside it, the frame has illegally become a Hero Object.

---

## 3. Visual trust principles

| Principle | Meaning |
|-----------|---------|
| Real product before illustration | Prefer governed screenshots over drawn metaphors |
| Product before decoration | Remove decoration first when in doubt |
| Simplicity before density | One dominant message / one dominant visual |
| Evidence before animation | Proof settles before motion runs |
| Readability before novelty | Arabic UI text must remain readable |
| Consistency before variety | Same product faces; don’t invent new “marketing UIs” |
| Honesty before polish | Insufficient-evidence states strengthen trust |
| Silence before filler | Whitespace over random SaaS illustration |

---

## 4. Visual anti-patterns (forbidden)

- Screenshot collages  
- Multiple competing screenshots in one section  
- Oversized floating devices that outrank the UI  
- Decorative 3D dominating product  
- Fake charts / fake metrics  
- Abstract AI brains / glowing network graphics  
- Excessive glassmorphism as product substitute  
- Random SaaS illustrations as “features”  
- Visual clutter / inconsistent icon styles  
- Decorative motion without purpose  
- Settings screens presented as customer or journey evidence  
- Stale UI presented as current product  
- Wallpaper screenshots that don’t match nearby claims  
- Combining unrelated states into one false screen  

---

## 5. Whitespace as narrative

Whitespace is a **narrative tool**. It communicates confidence.

| Moment | Silence required? | Why |
|--------|-------------------|-----|
| After Hero | Soft YES | Let recognition settle before problem depth |
| Before Widget (first proof) | YES | Prepare for evidence climb |
| Before Dashboard | **YES** | Strongest inspect pause needs air |
| Before Knowledge | **YES** | Discovery needs calm entry |
| After Knowledge | Soft YES | Let earned identity settle |
| Before Final CTA | YES | Decision needs quiet |
| Trust section | YES | Principles need calm |
| FAQ / Footer | YES | Utility, not theatre |

Whitespace must not be filled by Atmosphere Objects “because it looks empty.”

---

## 6. Screenshot governance

### Screenshots must

- Explain a nearby claim  
- Build trust  
- Reduce uncertainty  
- Match Evidence Readiness eligibility  
- Remain recognisable as CartFlow product UI  

### Screenshots must never

- Decorate  
- Fill empty space  
- Act as wallpaper  
- Show developer tools / test harness chrome  
- Contain fake data or invented metrics  
- Require large explanatory paragraphs to be understood  
- Be unrecognisable after decoration  

**Subordinate to:** Constitution Visual Evidence Law + Screenshot Policy + Evidence Capture Plan.

---

## 7. Device governance (frames, not heroes)

| Device | Story Purpose | Allowed Sections | Forbidden Sections | Max Visual Importance | Relationship to Screenshots |
|--------|---------------|------------------|--------------------|------------------------|------------------------------|
| **Phone** | Frame customer journey / WA continuation | LP-06, LP-07 (supporting) | LP-08 as hero; LP-09 as hero | Supporting only | Must shrink relative to UI content |
| **Storefront browser / window** | Frame in-store tool | LP-06 | LP-08/09 as substitute for dashboard/knowledge | Supporting | Widget UI remains Hero Object |
| **Merchant dashboard surface** | Show operating truth | LP-08 (content is Hero) | — | Hero = UI content, not bezel | Bezel optional; content owns |
| **Laptop** | Optional desktop merchant frame | LP-08, CAP-15 companion | Hero/Problem as spectacle | Supporting | Never larger in memory than UI |
| **Tablet** | Optional mobile merchant frame | LP-08 mobile | Evidence climax as decoration | Supporting | Same as phone |

**Law:** Devices are frames. Not heroes.  
If the screenshot is removed and the device still feels like the memorable object, the section fails.

---

## 8. Contradiction log

| ID | Finding |
|----|---------|
| CX-VN-01 | None. Aligns with Storyboard evidence intro map and Visual Evidence Law. |

---

## 9. Review answers

| Question | Answer |
|----------|--------|
| Is the dashboard always the visual hero when present? | **Yes** in LP-08 — the dashboard **UI content** is Hero Object; any device frame is Supporting. |
| Can every 3D object justify its existence? | Only if it supports a nearby Hero Object and loses purpose when that Hero is removed. |
| Can screenshots stand without decoration? | **Required.** Decoration that screenshots need to “work” are forbidden. |
| Does motion guide rather than distract? | Motion budget = reveal / focus / state — never idle loops over evidence. |
| Is visual hierarchy immediately obvious? | One Hero Object per evidence section; silence before climaxes. |
| Can the merchant identify the product within three seconds? | In LP-06/07/08/09, product UI must be identifiable without reading a paragraph. |
| Does every visual strengthen trust? | If not, demote to Atmosphere or remove. |
| Does the narrative remain coherent on mobile? | Same role hierarchy; full-width Hero Objects; devices never dominate. |
