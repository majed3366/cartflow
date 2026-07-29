# Visual Rhythm Governance V1

**Status:** Binding rhythm law for future landing design.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Storyboard V1  

No colours, typography, layout, or components. Rhythm only.

---

## 1. Classification vocabularies

### Visual Intensity

`LOW` · `MEDIUM` · `HIGH` · `VERY HIGH` (evidence climax only)

### Reading Load

`Light` · `Medium` · `Heavy`

### Evidence Weight

`Primary` · `Supporting` · `Decorative` · `None`

### Visual Silence

`YES` — intentional breathing space  
`NO` — active narrative/evidence beat

---

## 2. Per-section rhythm

| Section | Visual Intensity | Reading Load | Evidence Weight | Visual Silence |
|---------|------------------|--------------|-----------------|----------------|
| LP-01 Navigation | LOW | Light | None | YES |
| LP-02 Hero | HIGH | Light | Supporting (optional preview) / None | NO |
| LP-03 Problem | MEDIUM | Medium | None / Decorative situations | Soft YES between beats |
| LP-04 Reframe | LOW–MEDIUM | Light–Medium | None | YES (after contrast) |
| LP-05 Journey | MEDIUM | Light | Decorative / Supporting concept | NO |
| LP-06 Widget | HIGH | Light | **Primary** | NO |
| LP-07 WhatsApp | HIGH | Light | **Primary** | NO |
| LP-08 Dashboard | **VERY HIGH** | **Light** | **Primary** | NO — inspect pause |
| LP-09 Knowledge | HIGH | Medium–Heavy | **Primary** | Soft YES around honesty |
| LP-10 Decision | MEDIUM | Medium | Supporting | Soft YES |
| LP-11 Continuous | LOW–MEDIUM | Light–Medium | Supporting / None | YES |
| LP-12 Trust | LOW | Medium | Supporting (principles) | **YES** |
| LP-13 Integrations | LOW | Light | None / Supporting text | YES |
| LP-14 FAQ | LOW | Medium | None | YES |
| LP-15 Final CTA | MEDIUM | Light | None | Soft YES before button |
| LP-16 Footer | LOW | Light | None | YES |

---

## 3. Rhythm rules (binding)

### R1 — Intensity curve

```text
Orient (low)
  → Hero spike (high, light reading)
  → Problem/reframe (medium → calm)
  → Journey (medium, fast scan)
  → Evidence climb: Widget → WhatsApp → Dashboard peak
  → Knowledge (high meaning, more reading)
  → Value/trust descend (lighter visuals)
  → CTA focus (medium, button owns)
  → Footer silence
```

### R2 — Never two VERY HIGH evidence sections competing

Dashboard is the **ops evidence climax**. Knowledge is the **understanding climax**. They must not be visually equal collage panels fighting for the same beat.

### R3 — Reading vs evidence inverse at climax

When Evidence Weight = Primary and intensity is HIGH/VERY HIGH, Reading Load must stay **Light** (except Knowledge, which may rise to Medium–Heavy because meaning is the product).

### R4 — Visual silence is design

LP-04 after contrast, LP-11, LP-12, LP-13, FAQ, Footer intentionally breathe. Do not fill silence with decorative motion or secondary cards.

### R5 — Hero is not the evidence climax

Hero may be HIGH intensity for attention, but Evidence Weight must remain Supporting/None. Strongest product proof is later.

### R6 — Scroll speed follows rhythm

| Faster | Slower (inspect) |
|--------|------------------|
| LP-05, LP-11, LP-13, FAQ skim, Footer | LP-02, LP-06, LP-07, LP-08, LP-09, LP-15 decision |

### R7 — Mobile preserves curve

Mobile may compress visuals but must keep the same intensity sequence: early light proof → evidence climb → understanding → calm close.

---

## 4. Motion governance

### Allowed

- Small movement  
- Soft transitions  
- Attention guidance toward primary evidence  
- Depth / scroll reveal  
- State change (e.g. journey steps, accordion)  

### Forbidden

- Decorative loops  
- Floating elements everywhere  
- Background distractions  
- Motion replacing explanation  
- Animation competing with screenshots  
- Pulse/urgency CTA theatre  

### Motion by zone

| Zone | Motion budget |
|------|----------------|
| LP-01, LP-12…16 | Near zero |
| LP-02…05 | Soft, purposeful |
| LP-06…09 | Reveal/settle only — never decorate over UI |
| LP-15 | Affordance only |

---

## 5. 3D governance (eligibility only)

| Section | 3D Eligibility |
|---------|----------------|
| LP-01 | No 3D |
| LP-02 | No 3D as dependency; Minimal framing only if ever |
| LP-03 | No 3D |
| LP-04 | No 3D |
| LP-05 | Minimal / Supporting journey only |
| LP-06 | Visual framing only — never primary evidence |
| LP-07 | Visual framing only — never replace journey evidence |
| LP-08 | **No 3D** (prefer absent) |
| LP-09 | **No 3D** |
| LP-10…16 | No 3D |

**Never:** Primary evidence · Main story · Screenshot replacement.

---

## 6. Desktop vs mobile rhythm

| Aspect | Mobile (primary) | Desktop |
|--------|------------------|---------|
| Sequence | Same LP order | Same |
| Evidence | Full-width stack | May widen, not invent side stories |
| Silence | Keep breathing between evidence climbs | May add whitespace — not extra widgets |
| Reading | Shorter lines; same anchors | Slightly longer support OK |
| Inspect stops | Same (06–09, 08 peak) | Same |

Desktop **expands** the experience. It does **not** redefine the emotional or evidence sequence.
