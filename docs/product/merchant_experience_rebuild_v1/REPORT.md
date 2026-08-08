# CartFlow Merchant Experience Rebuild V1

## Status

**Deployed to Living Store. Acceptance Gate 1 — awaiting visual judgment.**

## Deployed commit

| Field | Value |
|---|---|
| SHA | `61c415f` (polish on `425afab`) |
| Short | `61c415f` |
| Message | `fix: polish Home experience field spacing after Living Store capture` |
| Production header | matches `61c415f…` |

## What changed (presentation only)

| Surface | Before | After |
|---|---|---|
| Home | Equal HES white cards | `cx-home` gravity composition: condition → dominant decision mass → evidence lane → quiet secondary |
| Decision Workspace | White card rows (DWA) | `cx-decision` reasoning objects: Evidence → Understanding → Decision → Action with densification from readiness |
| Frame | Primary rail nav could be hidden | Rail primary visible; narrower rail (176px); DWA override unlinked |

Product truth unchanged: HES `sections[]`, workspace `zone_b[]`, APIs, permissions, routes.

## Gate 1 probe (real production)

Source: `gate1_probe.json` (Living Store session via `/dev/living-store-home-review-session`).

| Check | Result |
|---|---|
| Deploy SHA `425afab` | PASS |
| `data-cf-frame="v1"` | PASS |
| Experience Home/Workspace CSS linked | PASS |
| DWA / PSVA **not** in `<link>` list | PASS |
| `.cx-home` + `.cx-insight--primary` on Home | PASS |
| `.cx-ws` + `.cx-decision` on Workspace | PASS |
| Rail primary sections visible | PASS |

## Production captures (Home + Workspace only)

| File | Surface |
|---|---|
| `desktop_home.png` | Desktop Home |
| `desktop_home_full.png` | Desktop Home full page |
| `desktop_workspace.png` | Desktop Decision Workspace |
| `desktop_workspace_full.png` | Desktop Workspace full page |
| `mobile_home.png` | Mobile Home |
| `mobile_workspace.png` | Mobile Decision Workspace |

Figma binding refs (SA-02 / SA-03): `figma_refs/`.

## Architecture (live)

| Layer | Asset |
|---|---|
| Frame | `static/merchant_frame_v1.css` |
| Design System | `static/merchant_ds_v1.css` |
| Grammar | `static/merchant_grammar_v1.css` |
| Home experience | `static/merchant_experience_home_v1.css` + `home_executive_summary_v1.js` |
| Workspace experience | `static/merchant_experience_workspace_v1.css` + decision card/grid painters |

## STOP

No Products / Carts / Communication / Settings rebuild in this gate.

Acceptance is visual on:

https://smartreplyai.net/dashboard
