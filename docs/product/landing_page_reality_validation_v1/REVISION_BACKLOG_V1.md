# Landing Page Revision Backlog V1

**Status:** Evidence-backed backlog only  
**Date (UTC):** 2026-07-29  
**Rule:** No opinion-based revisions. Every item needs Observation → Evidence → Hypothesis → Recommended change → Expected outcome → Priority.

During the Reality Validation window: **do not execute** UX/visual/copy redesign items — only Critical production defects.

---

## Priority legend

| Priority | Meaning |
|----------|---------|
| **Critical** | Production broken / blocked / unsafe |
| **High** | Blocks truthful value communication vs approved IA |
| **Medium** | Measurable engagement friction once sample exists |
| **Low** | Polish after Major/Minor decision |
| **Future** | Post-V2 or deferred paths (Demo, etc.) |

---

## RB-001 — Implement approved LP-01…16 / Hi-Fi on production

| Field | Content |
|-------|---------|
| **Observation** | Live `GET /` is pre-IA product-story landing; Knowledge absent; Widget not first evidence |
| **Evidence** | DOM audit; CX-RV-01; Hi-Fi Figma V1 + IA V1; `knowledge_section_viewed` cannot fire |
| **Hypothesis** | Merchants cannot experience the approved value story until production matches governance structure |
| **Recommended change** | After formal design approval + sample decision: ship Major Revision V2 implementing Hi-Fi / LP-01…16 (placeholders per Design Readiness) |
| **Expected outcome** | Widget-first proof, Dashboard climax, earned Knowledge; telemetry events map 1:1 to LP sections |
| **Priority** | **High** (Major Revision V2 candidate) |
| **Insight refs** | I-01, I-02 |

---

## RB-002 — Replace ineligible settings screenshots (replace-only)

| Field | Content |
|-------|---------|
| **Observation** | Live Widget/WhatsApp evidence uses settings UI crops |
| **Evidence** | Evidence Production reject list; CX-RV-02; Visual Evidence Law |
| **Hypothesis** | Merchants may misread settings chrome as product journey evidence |
| **Recommended change** | Swap fills with Acceptance-passed EV candidates / Production Ready assets only — preserve layout dimensions |
| **Expected outcome** | Widget/WA sections communicate operational truth |
| **Priority** | **High** |
| **Insight refs** | I-03 |
| **Window rule** | Asset swap only if treated as evidence defect; no layout redesign |

---

## RB-003 — Privacy / Terms footer destinations

| Field | Content |
|-------|---------|
| **Observation** | Live footer has contact + login only; no Privacy/Terms |
| **Evidence** | Evidence Readiness / Design Readiness publication blockers |
| **Hypothesis** | Trust verification incomplete for some merchants |
| **Recommended change** | Add real legal pages then footer links (utility only) |
| **Expected outcome** | Verifiable legitimacy without new marketing story |
| **Priority** | **Medium** |
| **Insight refs** | Constitution trust / LP-16 |

---

## RB-004 — Hero comprehension (merchant) — awaiting sample

| Field | Content |
|-------|---------|
| **Observation** | Pending early-exit vs hero_cta patterns |
| **Evidence** | _empty until ≥30 sessions_ |
| **Hypothesis** | TBD |
| **Recommended change** | TBD — copy only if rates show incomprehension; must cite message architecture |
| **Expected outcome** | TBD |
| **Priority** | **Medium** (placeholder) |
| **Insight refs** | I-04 |

---

## RB-005 — Scroll drop-off remediation — awaiting sample

| Field | Content |
|-------|---------|
| **Observation** | Pending scroll ladder cliffs |
| **Evidence** | _empty_ |
| **Hypothesis** | TBD |
| **Recommended change** | TBD — spacing/order only after measured cliff; no speculative section removal |
| **Expected outcome** | Higher reach to Widget/Dashboard/FAQ |
| **Priority** | **Medium** (placeholder) |
| **Insight refs** | I-05 |

---

## RB-006 — CTA hierarchy tuning — awaiting sample

| Field | Content |
|-------|---------|
| **Observation** | Pending hero vs final vs login rates |
| **Evidence** | _empty_ |
| **Hypothesis** | TBD |
| **Recommended change** | TBD — keep `/signup` primary, `/login` secondary; no Demo |
| **Expected outcome** | Calmer completion aligned with Constitution CTA law |
| **Priority** | **Low** until data |
| **Insight refs** | I-07 |

---

## RB-007 — Mobile-specific defects — awaiting sample

| Field | Content |
|-------|---------|
| **Observation** | Lab GET shows viewport meta; no merchant mobile defect filed |
| **Evidence** | Device distribution pending |
| **Hypothesis** | TBD |
| **Recommended change** | Fix only Critical mobile bugs if found |
| **Expected outcome** | Usable mobile path |
| **Priority** | **Critical** if broken; else **Low** |
| **Insight refs** | I-08 |

---

## RB-008 — Demo booking path

| Field | Content |
|-------|---------|
| **Observation** | Demo deferred by Constitution / Copy Architecture |
| **Evidence** | No booking path exists |
| **Hypothesis** | Adding Demo without path would violate truth law |
| **Recommended change** | Only after real booking exists |
| **Expected outcome** | Optional secondary path without urgency theatre |
| **Priority** | **Future** |

---

## Execution gate

| Item | May execute during RV window? |
|------|-------------------------------|
| Critical production defects | **Yes** |
| RB-001 Major implementation | **No** — requires decision + formal design approval |
| RB-002 asset replace-only | Prefer after Acceptance; no redesign |
| RB-004…006 | **No** until behavioural evidence filled |
| Opinion redesign | **Never** |

---

## Backlog update log

| Date (UTC) | Change |
|------------|--------|
| 2026-07-29 | Initial backlog from structural audit + telemetry readiness |
