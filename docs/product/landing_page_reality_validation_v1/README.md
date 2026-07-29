# Landing Page Reality Validation V1

**Status:** Observation window OPEN  
**Date (UTC):** 2026-07-29  
**Production URL:** https://smartreplyai.net/  
**Principle:** Observation → Evidence → Decision → Improvement

## Purpose

Answer one question only:

> Does the current Landing Page communicate CartFlow's value to real merchants?

This pack does **not** redesign the page. It observes the publicly deployed implementation and records evidence-backed revision candidates.

## Files

| File | Role |
|------|------|
| `LANDING_PAGE_REALITY_VALIDATION_V1.md` | Charter, scope, production rules, telemetry contract, decision gate |
| `LANDING_PAGE_OBSERVATION_REPORT_V1.md` | Measured observations (technical + behavioural) |
| `LANDING_PAGE_BEHAVIOUR_INSIGHTS_V1.md` | Interpretation of observation questions |
| `REVISION_BACKLOG_V1.md` | Evidence-traced backlog (Critical→Future) |
| `README.md` | This index |

## Governing authorities (read-only)

Constitution · IA · Copy Architecture · Storyboard · Wireframe · Visual Direction · Hi-Fi Figma V1

Validation **must not reopen** approved governance. It validates **implementation**.

## Implementation under validation

| Layer | Reality |
|-------|---------|
| Public host | `https://smartreplyai.net/` (`GET /`) |
| Template | `templates/cartflow_landing.html` |
| Structure | Pre–LP-01…16 product-story landing (live) |
| Hi-Fi Figma | Design authority — **not yet implemented** on `GET /` |
| Telemetry | `POST /api/landing/event` + `static/cartflow_landing_telemetry.js` |

**Contradiction logged (not silently fixed):** Live page ≠ approved LP-01…16 Hi-Fi. Behavioural questions about Knowledge (LP-09) cannot be answered until that section exists on production.

## Production rules during window

Fix only: broken layouts, routing errors, loading failures, accessibility blockers, critical bugs.

Do **not**: UX polish, visual redesign, copy rewrites, new/removed sections.

## How to refresh aggregates

```bash
curl -sH "X-CartFlow-Admin: $CARTFLOW_ADMIN_PASSWORD" \
  "https://smartreplyai.net/api/landing/summary?hours=168"
```

## Decision (exactly one, when sample is sufficient)

- Approve V1  
- Minor Revision V2  
- Major Revision V2  

Until the behavioural sample threshold is met, decision status remains **PENDING — observation window open**. Structural findings may already justify backlog items without closing the window early on opinion.
