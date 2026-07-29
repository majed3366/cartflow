# Landing Page Behaviour Insights V1

**Status:** Living — merchant behavioural cells update as aggregates fill  
**Date opened (UTC):** 2026-07-29  
**Parent:** Landing Page Reality Validation V1  
**Rule:** Insights require evidence. Structural gaps may be stated without merchant scroll proof.

---

## Insight method

```text
Observation (event / DOM / deploy probe)
        →
Evidence (counts, rates, absence)
        →
Hypothesis (testable)
        →
Implication for Revision Backlog
```

No “feels better” language.

---

## I-01 — Knowledge cannot be validated on live

| Field | Content |
|-------|---------|
| **Observation** | Live HTML has no Knowledge / LP-09 section |
| **Evidence** | DOM audit of `cartflow_landing.html`; `knowledge_section_viewed` has no `data-lp-view` target |
| **Hypothesis** | Merchants cannot “reach Knowledge” because it is not implemented — not because they bounce before it |
| **Implication** | Major structural gap vs IA + Hi-Fi; backlog RB-001 |
| **Confidence** | High (structural) |

---

## I-02 — Live story ≠ approved merchant journey

| Field | Content |
|-------|---------|
| **Observation** | Live order: Hero → think → objections → recovery → visibility → components (widget/WA/settings) → FAQ → CTA |
| **Evidence** | Template section IDs; IA LP-01…16 sequence |
| **Hypothesis** | Scroll stops and CTA behaviour on live will not transfer 1:1 to Hi-Fi; validating live teaches current value communication, not Hi-Fi efficacy |
| **Implication** | Report conclusions must label **implementation under test**; Major Revision V2 = implement approved sequence |
| **Confidence** | High (structural) |

---

## I-03 — Widget evidence quality on live is compromised

| Field | Content |
|-------|---------|
| **Observation** | `#components` Widget/WhatsApp use settings screenshots |
| **Evidence** | Evidence Production rejected settings crops as ineligible marketing evidence |
| **Hypothesis** | Even if `widget_section_viewed` is high, merchants may not see storefront Widget truth — engagement may misread as “understood Widget” |
| **Implication** | RB-002 asset replace-only after Acceptance; do not treat settings UI views as proof of Widget value communication |
| **Confidence** | High (governance + DOM) |

---

## I-04 — Hero value comprehension (merchant) — PENDING

| Field | Content |
|-------|---------|
| **Observation** | Hero exposes problem + recovery + understanding story; dual CTAs |
| **Evidence needed** | Early `page_exit` without `scroll_25`; `hero_cta_clicked` / `signup_clicked` rates; optional future moderated sessions |
| **Hypothesis** | TBD after ≥30 sessions |
| **Implication** | Do not rewrite Hero copy in-window |
| **Confidence** | None yet (behavioural) |

---

## I-05 — Scroll depth / stop points — PENDING

| Field | Content |
|-------|---------|
| **Observation** | Scroll ladder instrumented (`scroll_25…100`) + section views |
| **Evidence needed** | Drop-off between consecutive section_viewed rates |
| **Hypothesis** | TBD — candidate stop after `#recovery` or before `#components` once data exists |
| **Implication** | Backlog items only with measured cliff |
| **Confidence** | None yet |

---

## I-06 — Dashboard engagement — PENDING

| Field | Content |
|-------|---------|
| **Observation** | Live “dashboard” moment mapped to `#visibility` (cart next-step), not full Home/Workspace climax of Hi-Fi LP-08 |
| **Evidence needed** | `dashboard_section_viewed` vs later `faq` / `footer` / CTA |
| **Hypothesis** | TBD whether visibility section retains attention |
| **Implication** | Hi-Fi Dashboard dominance cannot be claimed validated until LP-08 ships |
| **Confidence** | Low until data; mapping caveat high |

---

## I-07 — CTA preference — PENDING

| Field | Content |
|-------|---------|
| **Observation** | Instrumented: hero signup, nav signup, final signup, login |
| **Evidence needed** | Counts by `section` on click events |
| **Hypothesis** | TBD |
| **Implication** | No CTA hierarchy change without rates |
| **Confidence** | None yet |

---

## I-08 — Mobile vs desktop — PENDING

| Field | Content |
|-------|---------|
| **Observation** | Device class recorded on events |
| **Evidence needed** | `device_distribution_opens` + scroll depth by device (future summary enhancement if needed) |
| **Hypothesis** | TBD |
| **Implication** | Mobile-canonical Hi-Fi remains design law; live mobile behaviour still to measure |
| **Confidence** | None yet |

---

## Cross-check with Storyboard expectations

| Storyboard expectation | Live validation status |
|------------------------|------------------------|
| Widget first primary product evidence | **Not met structurally** — Widget buried in `#components` with settings shot |
| Dashboard strongest inspect | **Partially analogous** via `#visibility` / `#think` — not Hi-Fi LP-08 |
| Knowledge earns identity | **Not met** — absent |
| Calm CTA / no Demo | **Met** on live |

---

## Insight update log

| Date (UTC) | Note |
|------------|------|
| 2026-07-29 | Structural insights I-01…I-03 recorded; behavioural I-04…I-08 opened pending sample |
