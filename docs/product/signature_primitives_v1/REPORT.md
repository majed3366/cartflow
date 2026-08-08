# CartFlow Signature Primitives V1 — Visual Grammar Foundation

## Course correction

Platform shell color/chrome alone is **not** assimilation complete.

This layer implements the frozen Figma **product visual language** as reusable, truth-bound primitives.

## Binding sources

- Figma page 23 — Commerce in Motion (CIM)
- Figma page 29 — Signature System / Laws SL-01…SL-12
- Constitution / Design System / Assimilation pages 25–34

## Shared implementation (not page-hardcoded)

| Asset | Role |
|---|---|
| `static/cf_signature_primitives_v1.js` | Maps real projection/HES fields → `data-cf-*` |
| `static/cf_signature_primitives_v1.css` | Structural grammar (weight, gap, densify, scoop, silence) |

Wired into:

- Decision Workspace card/grid/render controller
- Home Executive Summary sections
- Merchant app shell (load order)

## Truth mapping (no fake data)

| Grammar | Real signal |
|---|---|
| Living Evidence / Evidence Density | `evidence_lines_ar.length`, missing evidence |
| Decision Tension | `execution_readiness` (NEEDS_MORE_EVIDENCE / BLOCKED / READY) |
| Attention Gravity | `is_primary_decision` / HES `dominant` + `executive_rank` |
| Commerce Momentum | readiness → forward / held / external / calm |
| Living Routes | workspace `route-count` (primary + next, capped) |
| Visual Breathing | quiet / open breathing when no decision |
| Decision Densification | density ordinal 1–5 from readiness + role |
| Recovery Scoop | structural scoop edge + action continuation mark when momentum forward |
| Tapered Direction | primary→next tapered divider |
| Open-C geometry | structural clip edge on primary mass (not decorative backdrop) |
| Core Silence | controlled gap between primary and next |

## What this is not

- Not a color theme
- Not page content redesign
- Not invented analytics/motion
- Not decorative flowcharts

## Success test (SL-03)

Capture mode `body[data-cf-sig-proof="grayscale"]`:

- Grayscale filter
- Logo mark + wordmark hidden

Question: does Evidence → Understanding → Decision → Action still read through structure?

## Visual proof files

| File | Purpose |
|---|---|
| `home_grammar_color.png` | Home gravity ladder |
| `home_grammar_grayscale_no_logo.png` | Home without color/logo |
| `workspace_grammar_color.png` | Workspace living route + densify |
| `workspace_grammar_grayscale_no_logo.png` | Workspace without color/logo |
| `decision_mass_closeup.png` | Primary decision densification |
| `decision_mass_grayscale_closeup.png` | Same under grayscale |
| `evidence_to_action_stack_closeup.png` | Beat stack grammar |

## STOP

Foundation only. Page-by-page composition of these primitives comes after visual approval.
