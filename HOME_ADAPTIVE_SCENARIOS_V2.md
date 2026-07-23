# Home Adaptive Scenarios V2

**Document type:** Adaptive cognition scenario coverage  
**Status:** **Proposed** — companion to [`HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md`](HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md)  
**Date (UTC):** 2026-07-18  

Each scenario shows Router path, active/skipped/deferred nodes, emotion, exit, and which Cognitive Stress finding is resolved.

---

## Scenario matrix

| # | Situation | Path | Interim leave | Final closure |
|---|-----------|------|---------------|---------------|
| S01 | Healthy store, no action | A | — | A |
| S02 | VIP with phone | C | Communication | A/B/C after return |
| S03 | VIP without phone | C | Communication | A/B/C |
| S04 | High traffic / low conversion (urgent) | B | Decision Workspace | A/B/C |
| S05 | Multiple problems, one winner | B or C | Winner owner | Recompute after return |
| S06 | Store integration issue | D | Settings | Then Understanding if any |
| S07 | Communication unavailable + VIP | D or C+inline trust | Settings or Comm with caveat | Per restore |
| S08 | New store / no data | E | — | C |
| S09 | Understanding pending, no action | F | — | C |
| S10 | Reasoning not accepted, otherwise healthy | A | — | A (BU skipped) |
| S11 | Insufficient evidence, no urgency | E or F | — | C |
| S12 | Conflicting evidence, no urgency | F or A with incomplete BU | Optional DW | C or B |
| S13 | Ops failure only | D | Settings | A/C |
| S14 | Partial degradation (BU down, VIP up) | C | Communication | Deferred BU skipped if still down |
| S15 | Return after VIP resolved | RETURN | — | A |
| S16 | Return after VIP unresolved | RETURN | May re-route Comm | B |
| S17 | Stale BU, healthy otherwise | A | — | A/C (stale skipped or caveat, no hollow tour) |
| S18 | Purchase completed, recovery suppressed | A | — | A |
| S19 | Merchant reply follow-up | B | Communication | A/B |
| S20 | Dead-end: pending repeats | F → escape | — | C + calm still-forming |

---

## S01 — Healthy store

| Field | Value |
|-------|-------|
| **Path** | A |
| **Active** | Arrival A → Orientation → Understanding* → Confidence silent → Direction* → Closure A |
| **Skipped** | Focus; hollow BU/DIR |
| **Emotion** | Calm → Curious → Reassured → Confident |
| **Stress resolved** | N/A (was already good); confirms Focus omission |

---

## S02 — VIP with phone

| Field | Value |
|-------|-------|
| **Path** | C |
| **Active (entry)** | Arrival B → VIP Focus → Closure B → Communication |
| **Skipped** | Understanding, Orientation chapter, Direction |
| **Deferred** | Confidence, Direction; Understanding never forced |
| **Return** | Restore → VIP gone if resolved → Confidence* → Direction* → Closure |
| **Emotion** | Concerned → Purposeful → Reassured |
| **Stress resolved** | Mental jump; delayed routing; hollow Understanding; Direction after VIP |

---

## S03 — VIP without phone

| Field | Value |
|-------|-------|
| **Path** | C |
| **Same as S02** | Plus contact-limitation calm note inside VIP Focus — still routes Communication |
| **Stress resolved** | Same as S02; no invented channel |

---

## S04 — High traffic / low conversion (urgent)

| Field | Value |
|-------|-------|
| **Path** | B |
| **Active** | Arrival B → Focus (conversion) → Route Decision Workspace |
| **Deferred** | Understanding, Confidence, Direction after return |
| **Emotion** | Concerned → Determined → (return) Curious |
| **Stress resolved** | Understanding-before-Focus jump; delayed routing |

---

## S05 — Multiple simultaneous problems

| Field | Value |
|-------|-------|
| **Path** | C if VIP wins; else B |
| **Active** | Single primary Focus only; “+N more” acknowledgment without competing CTA |
| **After return** | Next winner or Closure A |
| **Stress resolved** | Competing priorities / attention stability |

---

## S06 — Store integration issue

| Field | Value |
|-------|-------|
| **Path** | D |
| **Active** | Arrival E → Confidence (integration) → Settings |
| **Skipped** | Pre-route Understanding (no business conclusions on broken pipe) |
| **Return** | Understanding* → Closure |
| **Emotion** | Concerned (platform) — not business decline |
| **Stress resolved** | Confidence oscillation (ops first when ops is the story); premature business interpretation |

---

## S07 — Communication unavailable + VIP

| Field | Value |
|-------|-------|
| **Path** | D first, or C with `R-INLINE-TRUST` |
| **Active** | Confidence (channel down) before any Communication promise; then VIP Focus when act possible or Settings if config-owned |
| **Hard rule** | Never imply auto-contact or executable outreach while channel down |
| **Stress resolved** | Trust check in wrong order; delayed truth about platform |

---

## S08 — New store / no data

| Field | Value |
|-------|-------|
| **Path** | E |
| **Active** | Arrival F → Orientation (day-zero) → Closure C |
| **Skipped** | Understanding, Focus, Direction, Confidence (unless D) |
| **Stress resolved** | Hollow stages; empty reasoning tour |

---

## S09 — Understanding pending

| Field | Value |
|-------|-------|
| **Path** | F |
| **Active** | Arrival C → Orientation → Pending Understanding (honest) → Closure C |
| **Skipped** | Full BU claims |
| **Stress resolved** | Hollow Understanding chapter |

---

## S10 — Reasoning not product-accepted

| Field | Value |
|-------|-------|
| **Path** | A (if otherwise healthy) with `R-SKIP-HOLLOW-BU` |
| **Active** | No Understanding chapter at all |
| **Stress resolved** | State H hollow stage |

---

## S11 — Insufficient evidence

| Field | Value |
|-------|-------|
| **Path** | E or F |
| **Closure** | C |
| **Skipped** | Recommendations, fake causes |
| **Stress resolved** | Hollow / forced Understanding |

---

## S12 — Conflicting evidence

| Field | Value |
|-------|-------|
| **Path** | F or A with incomplete BU only if accepted and merchant-worthy as “incomplete” |
| **Never** | Home-resolved narrative |
| **Stress resolved** | Confidence oscillation from fake certainty |

---

## S13 — Ops failure only

| Field | Value |
|-------|-------|
| **Path** | D |
| **Distinct meaning** | Platform failure ≠ business decline |
| **Stress resolved** | Wrong emotional attribution |

---

## S14 — Partial degradation (BU failed, VIP active)

| Field | Value |
|-------|-------|
| **Path** | C |
| **BU** | Skipped / deferred; VIP path uninterrupted |
| **Stress resolved** | One failed layer must not force linear tour or blank Home |

---

## S15 — Return after VIP resolved

| Field | Value |
|-------|-------|
| **Segment** | RETURN |
| **Feel** | “I came back” / “I already solved this” |
| **Active** | No VIP; deferred Confidence*/Direction*; Closure A |
| **Stress resolved** | Return psychology; no restart |

---

## S16 — Return after VIP unresolved

| Field | Value |
|-------|-------|
| **Segment** | RETURN |
| **Feel** | “Still needs me” — not first discovery drama |
| **May** | Re-route Communication with same identity |
| **Stress resolved** | Lost context; repeated discovery |

---

## S17 — Stale Business Understanding

| Field | Value |
|-------|-------|
| **Path** | A |
| **BU** | Skip or single not-current caveat — never stale recommendation tour |
| **Stress resolved** | Stale-as-live; oscillation |

---

## S18 — Purchase completed; recovery suppressed

| Field | Value |
|-------|-------|
| **Path** | A |
| **Skipped** | Recovery Focus / VIP for purchased cart |
| **Closure** | A |
| **Stress resolved** | Ghost attention |

---

## S19 — Merchant reply follow-up

| Field | Value |
|-------|-------|
| **Path** | B |
| **Route** | Communication |
| **Deferred** | Understanding after return |
| **Stress resolved** | Delayed routing |

---

## S20 — Pending repeats (dead end escape)

| Field | Value |
|-------|-------|
| **Path** | F then escape |
| **Escape** | After repeated pending visits → Closure C + calm “still forming — no action” |
| **Never** | Infinite Pending Understanding education loop |
| **Stress resolved** | Cognitive dead end |

---

## Stress-finding coverage checklist

| Finding | Covered by |
|---------|------------|
| Mental jump (Understanding before Focus) | S02–S05, S19 |
| Delayed routing | S02–S05, S19 |
| Hollow stages | S08–S11, S10, S17 |
| Confidence oscillation | S06, S07, S02 (deferred Confidence) |
| Return “started over” | S15, S16 |
| Competing priorities | S05 |
| Ops ≠ business decline | S06, S13 |
