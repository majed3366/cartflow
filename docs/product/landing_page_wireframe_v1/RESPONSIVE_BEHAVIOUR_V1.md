# Responsive Behaviour V1

**Status:** Binding responsive structural rules.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Wireframe V1  
**Canonical:** Mobile Wireframe Spec V1  

---

## 1. Core principles

1. **Mobile sequence is law** — LP-01…16 order never changes.  
2. **Desktop expands** — more width/whitespace, not new story beats.  
3. **Whitespace compresses before content** — remove Atmosphere/frames before cutting Hero Objects or core copy roles.  
4. **One dominant focus survives** at every breakpoint.  
5. **Evidence readability beats frame beauty** — bezels collapse first.  

---

## 2. Global behaviours

| Rule | Behaviour |
|------|-----------|
| Hero message order | Headline → support → CTA scales without reordering |
| Dashboard dominance | Remains dominant object in LP-08 at all widths |
| Knowledge cards | Stack vertically; one card focus on mobile |
| Widget evidence | Screenshot/placeholder precedes deep explanation on mobile; desktop may place beside with evidence ≥67% |
| CTA duplication | Nav may keep begin path; Final CTA section must not spawn a second sticky promo bar |
| Screenshot count | Never introduce a second competing screenshot when narrowing |
| 3D placeholders | Collapse/remove before evidence shrinks |
| RTL | Structure mirrors; dominance ratios preserved |

---

## 3. Breakpoint behaviour (conceptual)

Exact px deferred to Visual Direction. Behavioural tiers:

| Tier | Intent |
|------|--------|
| **Mobile** | Canonical single column; full-width evidence |
| **Tablet** | Mostly mobile stack; optional mild widen of evidence; still no equal heroes |
| **Desktop** | Allowed 2-column evidence patterns per Desktop Spec |

---

## 4. Per-section responsive notes

| Section | Narrowing behaviour |
|---------|---------------------|
| LP-01 | Anchors collapse; CTA remains |
| LP-02 | Preview drops below; never beside on mobile |
| LP-03 | Beats always stack |
| LP-04 | Side-by-side contrast → stack A/B |
| LP-05 | Horizontal step ideas → vertical only |
| LP-06 | 2-col → stack; evidence full-width |
| LP-07 | Same as LP-06 |
| LP-08 | Side copy → outcome above shot; shot widens |
| LP-09 | Card full-width; honesty below |
| LP-10 | Outcomes always stack |
| LP-11 | Progression always stack |
| LP-12 | Always stack + silence |
| LP-13 | Always stack rows |
| LP-14 | Accordion always |
| LP-15 | Full-width primary |
| LP-16 | Utility groups stack |

---

## 5. Touch vs pointer

| Concern | Mobile | Desktop |
|---------|--------|---------|
| Primary action | Large primary CTA | Same hierarchy, may be less wide |
| Accordion | Large headers | Same |
| Evidence inspect | Prefer stillness; readable Arabic UI | Same; no hover-only meaning |
| Hover-only reveals | **Forbidden** for meaning | Prefer not required |

---

## 6. Failure modes

| Failure | Fix |
|---------|-----|
| Desktop invents a new section | Remove |
| Mobile hides Knowledge honesty | Restore `PH-INSUFFICIENT` |
| Tablet shows collage of 3 shots | Reduce to one Hero |
| Sticky CTA covers evidence | Demote sticky; protect inspect sections |
| Evidence shrunk to fit 3D frame | Remove frame |
