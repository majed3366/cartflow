# Landing Page Production V1

**Status:** Official production implementation  
**Date (UTC):** 2026-07-29  
**Figma:** https://www.figma.com/design/fPur35ZnK96pDvKPLUGXTb  
**Public:** `GET /` → `templates/cartflow_landing.html`

## Authority order

Constitution → IA → Copy Architecture → Storyboard → Wireframe → Visual Direction → **Hi-Fi Figma V1**

Figma wins on spacing, hierarchy, type, colour, radius, layout.

## Implementation map

| Asset | Path |
|-------|------|
| Template | `templates/cartflow_landing.html` |
| Styles | `static/cartflow_landing_v1.css` |
| Evidence | `static/img/landing_v1/` (widget, dashboard, home, workspace) |
| Telemetry | `static/cartflow_landing_telemetry.js` + `POST /api/landing/event` |
| Tokens | Brand Foundation (`--cf-primary` #1E6B4A …) — Figma variables |

## Sections

LP-01…LP-16 implemented. Approved placeholders: WhatsApp journey, Knowledge RV, Privacy, Terms.

## Post-deploy review

See `PRODUCTION_VISUAL_REVIEW_V1.md`.
