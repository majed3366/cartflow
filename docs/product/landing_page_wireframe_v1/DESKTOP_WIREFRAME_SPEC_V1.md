# Desktop Wireframe Spec V1

**Status:** Structural desktop expansion of the mobile-canonical wireframe.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Wireframe V1  

Desktop **expands** mobile. It does not redefine sequence or narrative.

No colours. No typography. Structure only.

**Content width token:** `MAX-CONTENT` = single readable content column (conceptually ~60–72ch for pure text; evidence sections may widen for screenshots within a page shell). Exact px deferred to Visual Direction.

---

## LP-01 Navigation

| Field | Spec |
|-------|------|
| **Columns** | 1 bar / 3 zones |
| **Column ratio** | Brand ~20% · Anchors flex · Actions ~25% |
| **Alignment** | Edge-aligned within page shell |
| **Screenshot position** | None |
| **Copy position** | Labels in zones |
| **Hero object position** | N/A |
| **Evidence object position** | None |
| **Maximum content width** | Full shell |
| **Minimum whitespace** | Tight inside bar |
| **Vertical spacing** | Bar height only |
| **Section break style** | None (overlay/sticky) |

---

## LP-02 Hero

| Field | Spec |
|-------|------|
| **Columns** | 1 (copy-primary) or 12-grid 7/5 if preview used |
| **Column ratio** | Copy ≥58% if split; preview ≤42% |
| **Alignment** | Start-aligned copy; preview end-side if present |
| **Screenshot position** | Optional end-side or below — never larger than headline block in attention |
| **Copy position** | Start column |
| **Hero object position** | Headline block |
| **Evidence object position** | Optional preview subordinate |
| **Maximum content width** | MAX-CONTENT for copy; shell for section |
| **Minimum whitespace** | Large below Hero |
| **Vertical spacing** | Comfortable CTA gap under support |
| **Section break style** | Soft silence band |

---

## LP-03 Problem Recognition

| Field | Spec |
|-------|------|
| **Columns** | 1 preferred |
| **Column ratio** | 100% stack |
| **Alignment** | Start |
| **Screenshot position** | None |
| **Copy position** | Full |
| **Hero object position** | Statement |
| **Evidence object position** | Context beats only |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | Between beats |
| **Vertical spacing** | Medium beat gaps |
| **Section break style** | Standard |

**Forbidden:** Equal multi-column “feature cards” competing as heroes.

---

## LP-04 Recovery Limitation Reframe

| Field | Spec |
|-------|------|
| **Columns** | 2 for contrast **or** 1 stacked |
| **Column ratio** | 50/50 if 2-col — equal contrast parts OK (not product heroes) |
| **Alignment** | Centered contrast unit within MAX-CONTENT |
| **Screenshot position** | None |
| **Copy position** | Inside contrast cells + fairness below full width |
| **Hero object position** | Contrast unit |
| **Evidence object position** | None |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | Large after section |
| **Vertical spacing** | Compact inside contrast |
| **Section break style** | Silence band |

---

## LP-05 How CartFlow Works

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Start |
| **Screenshot position** | **None** |
| **Copy position** | Intro + steps |
| **Hero object position** | Step list |
| **Evidence object position** | Conceptual marks only |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | **Large before LP-06** |
| **Vertical spacing** | Even step rhythm |
| **Section break style** | Silence before evidence climb |

---

## LP-06 Widget Evidence

| Field | Spec |
|-------|------|
| **Columns** | 2 |
| **Column ratio** | Copy ≤33% · Evidence ≥67% |
| **Alignment** | Evidence dominant (end or start by locale/RTL — **structure:** evidence larger) |
| **Screenshot position** | Dominant column `PH-WIDGET` |
| **Copy position** | Narrow column |
| **Hero object position** | Widget placeholder |
| **Evidence object position** | Same as hero |
| **Maximum content width** | Wide shell allowed for evidence |
| **Minimum whitespace** | Entry air |
| **Vertical spacing** | Copy vertically centered to evidence mid |
| **Section break style** | Standard |

---

## LP-07 WhatsApp Journey Evidence

| Field | Spec |
|-------|------|
| **Columns** | 2 |
| **Column ratio** | Copy ≤33% · Evidence ≥67% |
| **Alignment** | Evidence dominant |
| **Screenshot position** | `PH-WA-JOURNEY` |
| **Copy position** | Narrow |
| **Hero object position** | Journey placeholder |
| **Evidence object position** | Journey + optional stop cue |
| **Maximum content width** | Wide shell |
| **Minimum whitespace** | **Large after** (before Dashboard) |
| **Vertical spacing** | Same as LP-06 |
| **Section break style** | Silence band before climax |

---

## LP-08 Dashboard Evidence

| Field | Spec |
|-------|------|
| **Columns** | 1 preferred (outcome above shot) **or** 2 with copy ≤25% |
| **Column ratio** | If 2-col: Copy ≤25% · Shot ≥75% |
| **Alignment** | Screenshot centered/dominant |
| **Screenshot position** | `PH-DASHBOARD` full dominant |
| **Copy position** | Above or narrow side — one sentence |
| **Hero object position** | Dashboard UI |
| **Evidence object position** | Attention state within/near shot |
| **Maximum content width** | Widest evidence shell on page |
| **Minimum whitespace** | **Largest before-section silence** |
| **Vertical spacing** | Shot breathing room |
| **Section break style** | Silence before Knowledge |

**Rule:** No second competing screenshot.

---

## LP-09 Knowledge Layer Discovery

| Field | Spec |
|-------|------|
| **Columns** | 2 or 1 |
| **Column ratio** | If 2: Card ≥55% · Copy ≤45% |
| **Alignment** | Card dominant |
| **Screenshot position** | `PH-KNOWLEDGE` + honesty `PH-INSUFFICIENT` adjacent/below |
| **Copy position** | Beside or below |
| **Hero object position** | Knowledge card |
| **Evidence object position** | Evidence state |
| **Maximum content width** | MAX-CONTENT+ for card |
| **Minimum whitespace** | Large before |
| **Vertical spacing** | Card then honesty |
| **Section break style** | Soft after |

---

## LP-10 Decision Value

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Start |
| **Screenshot position** | Optional small `PH-DECISION` below list |
| **Copy position** | Outcome list |
| **Hero object position** | List |
| **Evidence object position** | Optional fragment |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | Soft |
| **Vertical spacing** | Even outcomes |
| **Section break style** | Standard |

---

## LP-11 Continuous Value Journey

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Start |
| **Screenshot position** | None |
| **Copy position** | Progression |
| **Hero object position** | Progression |
| **Evidence object position** | None |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | YES |
| **Vertical spacing** | Compact steps |
| **Section break style** | Soft |

---

## LP-12 Trust and Governance

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Start |
| **Screenshot position** | Optional tiny |
| **Copy position** | Principles |
| **Hero object position** | Restraint line |
| **Evidence object position** | Optional |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | **YES (large)** |
| **Vertical spacing** | Airy principles |
| **Section break style** | Soft |

---

## LP-13 Integration Readiness

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Start |
| **Screenshot position** | None / text rows |
| **Copy position** | Status list |
| **Hero object position** | List |
| **Evidence object position** | Text states |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | YES |
| **Vertical spacing** | Compact rows |
| **Section break style** | Standard |

---

## LP-14 FAQ

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Start |
| **Screenshot position** | None |
| **Copy position** | Accordion |
| **Hero object position** | Accordion |
| **Evidence object position** | None |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | YES |
| **Vertical spacing** | Dense list OK |
| **Section break style** | Silence before CTA |

---

## LP-15 Final CTA

| Field | Spec |
|-------|------|
| **Columns** | 1 |
| **Column ratio** | 100% |
| **Alignment** | Center or start within MAX-CONTENT |
| **Screenshot position** | None |
| **Copy position** | Invitation above button |
| **Hero object position** | Primary button |
| **Evidence object position** | None |
| **Maximum content width** | MAX-CONTENT |
| **Minimum whitespace** | **Large before** |
| **Vertical spacing** | Invitation → primary → secondary |
| **Section break style** | Soft into footer |

---

## LP-16 Footer

| Field | Spec |
|-------|------|
| **Columns** | Up to 3 utility groups |
| **Column ratio** | Equal utility groups — not marketing columns |
| **Alignment** | Edge within shell |
| **Screenshot position** | None |
| **Copy position** | Links |
| **Hero object position** | N/A |
| **Evidence object position** | None |
| **Maximum content width** | Full shell |
| **Minimum whitespace** | Compact |
| **Vertical spacing** | Tight |
| **Section break style** | Page end |
