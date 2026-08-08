# Merchant UI V2 — Decision Workspace Final Product Composition V1

**Status:** Living Store evidence captured — STOP for Workspace visual review  
**Deploy:** `8cc5ad1`  
**URL:** https://smartreplyai.net/dashboard#workspace  
**Home:** FROZEN — not modified

## Objective

Turn Decision Workspace into a living operational decision surface using the approved CartFlow visual language — not a static infographic board.

## Report answers

### 1. What changed in the App Bar?

- Mobile App Bar is now a complete product chrome row: **menu** · **CartFlow mark** · **current section title** (`#cf2-appbar-section`, synced from router) · **account** (SVG, no emoji).
- Desktop keeps the same system: brand + horizontal nav + account actions; active section remains in nav.
- Workspace contextual sidebar rail is **off** (same as Home) so the stage owns the decision field — no legacy ctx remnants.
- Brand mark is inverted to white on navy so identity reads on mobile.

### 2. What previously made Workspace feel static?

- CO **gallery / rail** treated as decoration beside a text stack.
- Design-vocabulary beat labels (“كثافة الدليل”, etc.) instead of merchant questions.
- Projection paint often missed real `zone_b` because the API envelope was not unwrapped (`projection.zone_b`).
- Vertical route + objects read as one frozen poster without state-driven emphasis.
- Mobile spent first-viewport budget on oversized visual vocabulary.

### 3. Which elements now react to real product state?

| Element | Truth driver |
|--------|----------------|
| Silent CO kind | tension + readiness → waiting / insufficient / forming / ready / blocked |
| Evidence field density | evidence line count → sparse→gathering→aligned→converging |
| Confidence copy | density + tension (merchant Arabic) |
| Living Route node `is-active` / `is-complete` | progress: evidence → understanding → decision → action |
| Decision Mass `is-forming` / `is-ready` | execution readiness |
| Terminus `is-armed` | action available |
| Motion classes `is-arriving` | one-shot on evidence paint (`prefers-reduced-motion` gated) |

No fake counters, invented metrics, or looping decoration.

### 4. What was removed because it was visual vocabulary without merchant value?

- Multi-object CO rails / galleries on primary and secondary decisions
- Design-system beat labels as merchant-facing copy
- Workspace contextual sidebar content for `#workspace`
- Emoji account control on mobile App Bar
- Poster-like equal weight of four large state objects as a gallery

### 5. How was mobile vertical density reduced?

- One compact silent mark (≤28px) instead of a CO vocabulary block
- Merchant title + eyebrow first; route nodes tighter padding
- Desktop board chrome removed on mobile (transparent primary, no heavy card frame)
- Secondary “بعده” compressed to title + link/note rows (no object rail)
- First viewport targets: attention · evidence state · CartFlow conclusion · act/wait

### 6. Which Commerce Objects remain and what merchant meaning does each one carry?

Only **one** CO on the primary decision (silent, label clipped):

| Kind | Merchant meaning |
|------|------------------|
| `insufficient` | Needs more evidence |
| `waiting` | Waiting for a signal / Core Silence |
| `decision-forming` | Decision is forming |
| `decision-ready` | Ready to decide / act |
| `blocked` | High-attention / blocked path |

Secondary decisions: **no** CO — title + next step only.

### 7. How does the Living Route now represent real decision progression?

Route is the structural backbone under merchant language:

**observation (`ما يظهر الآن`) → meaning (`ماذا يعني`) → decision (`ما يقرره CartFlow`) → next step (`خطوتك الآن`)**

Node emphasis (`is-active` / `is-complete`) follows real tension/readiness. Merchant never needs to decode visual grammar to understand the decision — Arabic labels carry meaning; route only supports progression.

## Evidence

| File | Role |
|------|------|
| [01_desktop_workspace_full.png](01_desktop_workspace_full.png) | Desktop full Workspace |
| [02_desktop_primary_decision.png](02_desktop_primary_decision.png) | Primary decision dominance |
| [03_desktop_route_progression.png](03_desktop_route_progression.png) | Living Route progression |
| [04_mobile_first_viewport.png](04_mobile_first_viewport.png) | Mobile first viewport |
| [05_mobile_decision_progression.png](05_mobile_decision_progression.png) | Mobile full decision path |
| [06_mobile_appbar.png](06_mobile_appbar.png) | Mobile App Bar chrome |
| [07_motion_state_a.png](07_motion_state_a.png) | Motion — arrival paint |
| [08_motion_state_b.png](08_motion_state_b.png) | Motion — settled paint |
| [09_grayscale_logo_hidden.png](09_grayscale_logo_hidden.png) | Grayscale / logo hidden |
| [10_before_after.png](10_before_after.png) | Before (maturity) vs after |
| [production_probe.json](production_probe.json) | Living Store probe |

## Truth / architecture lock

Unchanged: APIs, decision logic, projections, readiness/admission rules, merchant actions, business truth, **Home**.

## STOP

Decision Workspace Final Product Composition V1 is ready for visual review.  
Do **not** start Products, Carts, Communication, or Settings.
