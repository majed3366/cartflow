# Merchant UI V2 — Figma Visual Language Production Parity V1

**Surface:** Living Store only — `/dashboard?cf_ui=v2#home` · `/dashboard?cf_ui=v2#workspace`  
**Scope:** Home + Decision Workspace · Desktop + Mobile  
**Status:** Implemented for Gate B/C visual review (architecture Gate A already accepted).

## What changed

V2 presentation now uses a dedicated language layer — not navy/teal SaaS polish:

| Asset | Role |
|-------|------|
| `static/merchant_ui_v2_language.css` | Commerce Objects, Evidence Field, Living Route, Decision Mass, Momentum Trace, Capsules, Silence/Taper |
| `static/merchant_ui_v2_language.js` | Presentation helpers (no business logic) |
| `static/merchant_ui_v2_home.js` + `.css` | Executive commerce scene (Attention Gravity + Evidence Density) |
| `static/merchant_ui_v2_workspace.js` + `.css` | Decision Object + living route geometry |
| Gate captures | `docs/product/merchant_ui_v2_figma_parity_v1/` |

Truth bindings unchanged:

- Home → `GET /api/dashboard/summary` → `home_executive_summary_v1.sections[]`
- Workspace → `GET /api/cart-workspace/v1/projection` → `zone_b[]`

## Mapping table

| Figma primitive | Real CartFlow truth | Live component | Where visible |
|-----------------|---------------------|----------------|---------------|
| Commerce Objects | HES section id + diagnosis/recommendation text (attention, evidence, hesitation, recovery, insufficient…) | `.cf2-co` / `CartFlowUiV2Lang.commerceObject` | Home gravity + capsules; Workspace Decision Object header |
| Evidence Density | Evidence line count / supporting HES evidence sections; sparse when “أدلة غير كافية” | `.cf2-evfield` | Home density aside; Workspace evidence node |
| Attention Gravity | `executive_rank` / `dominant` / `decisions` section as primary | `.cf2-scene__gravity` | Home primary scene |
| Commerce Momentum | Only when ≥2 real lanes exist among hesitation/evidence/decision/carts/recovery | `.cf2-mtrace` | Home gravity (conditional) |
| Living Routes | Decision card evidence → understanding → decision → action/wait | `.cf2-route` | Workspace Decision Object |
| Decision Densification | `decision_sentence_ar` / readiness → `.cf2-dmass` size & tension | `.cf2-dmass` | Workspace decision node |
| Decision Tension | `execution_readiness`, confidence, `execution_available` | `[data-cf2-tension]` | Workspace route + decision mass |
| Recovery Continuation | Wait lines when not READY; recovery commerce object when action path open | `.cf2-reason__wait` / `.cf2-co--recovery` | Workspace action terminus |
| Knowledge Capsules | Non-primary HES sections | `.cf2-capsule` | Home orbit (secondary) |
| Visual Breathing / Silence | Structural spacer between gravity and orbit | `.cf2-silence` / `.cf2-taper` | Home + Workspace |
| Signature Geometry | Open-C, controlled gap, taper spine, recovery scoop (structural CSS, not logo paste) | CO glyphs + route/dmass clip-paths | All language surfaces |
| Core Silence | Open/sparse tension when evidence weak | open route opacity + sparse field | Home/Workspace when truth is thin |

## Gate shots (required)

| # | File | View |
|---|------|------|
| 1 | `01_desktop_home.png` | Home full viewport |
| 2 | `02_desktop_home_language_closeup.png` | Home visual-language close-up |
| 3 | `03_desktop_workspace.png` | Workspace full viewport |
| 4 | `04_desktop_decision_object_closeup.png` | Primary Decision Object |
| 5 | `05_mobile_home.png` | Mobile Home |
| 6 | `06_mobile_workspace.png` | Mobile Workspace |
| 7 | `07_mobile_decision_object_closeup.png` | Mobile Decision Object |
| 8 | `08_home_grayscale_logo_hidden.png` | Gate C Home |
| 9 | `09_workspace_grayscale_logo_hidden.png` | Gate C Workspace |

Probe: `gate_bc_probe.json` · Capture: `scripts/_capture_merchant_ui_v2_figma_parity_v1.py`

## Explicit non-goals

- No V1 global replacement
- No Products / Carts / Communication / Settings V2
- No fake metrics, charts, or invented journeys
- No runtime animation pass (static structural motion only)

Also note: Living Store `zone_b` may be empty at capture time. In that case Workspace renders a **Core Silence Decision Object** (open Living Route + sparse Evidence Field + open Decision Mass + wait terminus) — uncertainty as visual state, not invented decisions.
