# Mobile Wireframe Spec V1

**Status:** Canonical structural experience (mobile-first).  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Wireframe V1  

Mobile is **primary**. Desktop expands it. Sequence LP-01…16 is immutable.

No colours. No typography sizes. Structure and behaviour only.

---

## Global mobile rules

1. Single column always.  
2. One dominant object visible as the focus of each section.  
3. Whitespace compresses before content is removed.  
4. Evidence sections: short copy then full-width evidence **or** evidence then one support line — never shrink evidence beside copy.  
5. Primary CTA in nav may persist; Final CTA is not duplicated as a second sticky marketing bar.  
6. Touch targets for CTA / accordion must be prioritised over decorative frames.  

---

## LP-01 Navigation

| Field | Spec |
|-------|------|
| **Stack order** | Brand · (menu) · primary CTA |
| **Collapsed elements** | Secondary anchors into menu |
| **Expanded elements** | Primary CTA remains |
| **Reading order** | Brand → CTA |
| **Maximum paragraph length** | N/A (labels) |
| **CTA behaviour** | One primary; Login in menu or secondary |
| **Screenshot behaviour** | None |
| **Evidence order** | None |
| **Expected scroll rhythm** | Instant |
| **Touch priority** | Primary CTA / menu |

---

## LP-02 Hero

| Field | Spec |
|-------|------|
| **Stack order** | Headline → support → primary CTA → secondary CTA → optional preview |
| **Collapsed elements** | Preview may sit below fold |
| **Expanded elements** | Headline + CTA always in first viewport if possible |
| **Reading order** | Same as stack |
| **Maximum paragraph length** | 1 support sentence |
| **CTA behaviour** | Full-width primary preferred |
| **Screenshot behaviour** | Full-width preview if used; never beside headline |
| **Evidence order** | After CTA |
| **Expected scroll rhythm** | First pause |
| **Touch priority** | Primary CTA |

---

## LP-03 Problem Recognition

| Field | Spec |
|-------|------|
| **Stack order** | Core idea → beat 1…n |
| **Collapsed elements** | Extra beats may continue below |
| **Expanded elements** | Core idea |
| **Reading order** | Idea → beats |
| **Maximum paragraph length** | 1–2 short lines per beat |
| **CTA behaviour** | None |
| **Screenshot behaviour** | None |
| **Evidence order** | N/A |
| **Expected scroll rhythm** | Medium |
| **Touch priority** | Scroll continuity |

---

## LP-04 Recovery Limitation Reframe

| Field | Spec |
|-------|------|
| **Stack order** | Contrast A → Contrast B → fairness |
| **Collapsed elements** | None critical |
| **Expanded elements** | Both contrast parts |
| **Reading order** | A → B → fairness |
| **Maximum paragraph length** | Short clauses |
| **CTA behaviour** | None |
| **Screenshot behaviour** | None |
| **Evidence order** | N/A |
| **Expected scroll rhythm** | Brief pause |
| **Touch priority** | Scroll |

---

## LP-05 How CartFlow Works

| Field | Spec |
|-------|------|
| **Stack order** | Intro → step 1…n |
| **Collapsed elements** | None |
| **Expanded elements** | Full step list |
| **Reading order** | Steps |
| **Maximum paragraph length** | Step labels only |
| **CTA behaviour** | None |
| **Screenshot behaviour** | **Forbidden** |
| **Evidence order** | Conceptual only |
| **Expected scroll rhythm** | Faster scan |
| **Touch priority** | Scroll |

---

## LP-06 Widget Evidence

| Field | Spec |
|-------|------|
| **Stack order** | Short claim/support → `PH-WIDGET` full-width → optional caption |
| **Collapsed elements** | Device chrome |
| **Expanded elements** | Widget UI |
| **Reading order** | Copy → evidence |
| **Maximum paragraph length** | 1–2 lines before shot |
| **CTA behaviour** | None |
| **Screenshot behaviour** | Full-width; settings forbidden |
| **Evidence order** | After short copy |
| **Expected scroll rhythm** | Inspect pause |
| **Touch priority** | Evidence visibility (no overlay controls) |

---

## LP-07 WhatsApp Journey Evidence

| Field | Spec |
|-------|------|
| **Stack order** | Short support → `PH-WA-JOURNEY` → optional stop-state cue |
| **Collapsed elements** | Decorative phone bezel |
| **Expanded elements** | Journey states |
| **Reading order** | Copy → journey → stop cue |
| **Maximum paragraph length** | 1–2 lines |
| **CTA behaviour** | None |
| **Screenshot behaviour** | Full-width journey |
| **Evidence order** | After short copy |
| **Expected scroll rhythm** | Inspect |
| **Touch priority** | Evidence |

---

## LP-08 Dashboard Evidence

| Field | Spec |
|-------|------|
| **Stack order** | One outcome sentence → `PH-DASHBOARD` full-width |
| **Collapsed elements** | Laptop bezel; secondary shots |
| **Expanded elements** | Dashboard UI |
| **Reading order** | Outcome → screenshot |
| **Maximum paragraph length** | 1 sentence |
| **CTA behaviour** | None |
| **Screenshot behaviour** | Full-width; single shot only |
| **Evidence order** | After outcome line |
| **Expected scroll rhythm** | **Strongest inspect pause** |
| **Touch priority** | Pinch/scroll readability of UI text |

---

## LP-09 Knowledge Layer Discovery

| Field | Spec |
|-------|------|
| **Stack order** | Short meaning → `PH-KNOWLEDGE` → `PH-INSUFFICIENT` honesty |
| **Collapsed elements** | Extra pattern examples |
| **Expanded elements** | One card + honesty |
| **Reading order** | Meaning → card → honesty |
| **Maximum paragraph length** | 2–3 short lines |
| **CTA behaviour** | None |
| **Screenshot behaviour** | Full-width card |
| **Evidence order** | Card then insufficient state |
| **Expected scroll rhythm** | Discovery pause |
| **Touch priority** | Card readability |

---

## LP-10 Decision Value

| Field | Spec |
|-------|------|
| **Stack order** | Outcomes 1…n → optional small `PH-DECISION` |
| **Collapsed elements** | Outcomes beyond top 4 may continue |
| **Expanded elements** | Top outcomes |
| **Reading order** | Outcomes |
| **Maximum paragraph length** | One line per outcome |
| **CTA behaviour** | None |
| **Screenshot behaviour** | Optional small |
| **Evidence order** | After list |
| **Expected scroll rhythm** | Medium |
| **Touch priority** | Scroll |

---

## LP-11 Continuous Value Journey

| Field | Spec |
|-------|------|
| **Stack order** | Progression steps |
| **Collapsed elements** | Decorative connectors |
| **Expanded elements** | Steps |
| **Reading order** | Steps |
| **Maximum paragraph length** | Short conditionals |
| **CTA behaviour** | None |
| **Screenshot behaviour** | None |
| **Evidence order** | N/A |
| **Expected scroll rhythm** | Faster |
| **Touch priority** | Scroll |

---

## LP-12 Trust and Governance

| Field | Spec |
|-------|------|
| **Stack order** | Restraint line → principles |
| **Collapsed elements** | Optional tiny evidence |
| **Expanded elements** | Principles |
| **Reading order** | Line → list |
| **Maximum paragraph length** | One line per principle |
| **CTA behaviour** | None |
| **Screenshot behaviour** | Prefer none |
| **Evidence order** | Optional last |
| **Expected scroll rhythm** | Quiet pause |
| **Touch priority** | Scroll |

---

## LP-13 Integration Readiness

| Field | Spec |
|-------|------|
| **Stack order** | Status rows |
| **Collapsed elements** | None |
| **Expanded elements** | All platform rows |
| **Reading order** | Rows |
| **Maximum paragraph length** | One line + disclosure |
| **CTA behaviour** | None |
| **Screenshot behaviour** | No logos |
| **Evidence order** | Text |
| **Expected scroll rhythm** | Fast |
| **Touch priority** | Scroll |

---

## LP-14 FAQ

| Field | Spec |
|-------|------|
| **Stack order** | Accordion items |
| **Collapsed elements** | Answers until open |
| **Expanded elements** | One open answer |
| **Reading order** | Q → A |
| **Maximum paragraph length** | Short answers (later copy) |
| **CTA behaviour** | None in body |
| **Screenshot behaviour** | None |
| **Evidence order** | N/A |
| **Expected scroll rhythm** | Optional dive |
| **Touch priority** | Accordion headers |

---

## LP-15 Final CTA

| Field | Spec |
|-------|------|
| **Stack order** | Invitation → primary CTA → secondary |
| **Collapsed elements** | None |
| **Expanded elements** | Primary CTA |
| **Reading order** | Same |
| **Maximum paragraph length** | 1 invitation line |
| **CTA behaviour** | Full-width primary; no Demo |
| **Screenshot behaviour** | None |
| **Evidence order** | None |
| **Expected scroll rhythm** | Decision pause |
| **Touch priority** | **Primary CTA** |

---

## LP-16 Footer

| Field | Spec |
|-------|------|
| **Stack order** | Contact → legal → login |
| **Collapsed elements** | Extra link groups |
| **Expanded elements** | Contact |
| **Reading order** | Same |
| **Maximum paragraph length** | Labels |
| **CTA behaviour** | Utility only |
| **Screenshot behaviour** | None |
| **Evidence order** | None |
| **Expected scroll rhythm** | End |
| **Touch priority** | Mailto / links |
