# CartFlow Merchant UI V2 — Clean-Slate Vertical Slice

## Status

**Deployed to Living Store (feature-gated). Gate A evidence captured. Awaiting visual Gates A–C.**

## How to open V2 (does not replace V1)

| Method | URL / action |
|---|---|
| Query | https://smartreplyai.net/dashboard?cf_ui=v2#home |
| Review entry | https://smartreplyai.net/dev/merchant-ui-v2 |
| Back to V1 | https://smartreplyai.net/dashboard?cf_ui=v1#home or `/dev/merchant-ui-v1` |
| Env (force) | `CARTFLOW_MERCHANT_UI_V2=1` |

Default production remains **V1** until approval.

## Deployed commit

| Field | Value |
|---|---|
| SHA | `4fb6604c7a74d8e801c932eaf9ad35fdc0feca88` |
| Short | `4fb6604` |
| Message | `feat: add Merchant UI V2 clean-slate vertical slice (frame, Home, Workspace)` |

## Architecture

| Layer | Asset |
|---|---|
| Namespace | `body[data-cf-ui="v2"]` |
| Template | `templates/merchant_app_v2.html` |
| DS | `static/merchant_ui_v2_ds.css` |
| Frame | `static/merchant_ui_v2_frame.css` + `merchant_ui_v2_app.js` |
| Home | `merchant_ui_v2_home.css` + `merchant_ui_v2_home.js` |
| Workspace | `merchant_ui_v2_workspace.css` + `merchant_ui_v2_workspace.js` |
| Flag | `services/merchant_ui_v2/flag_v1.py` |

**No legacy CSS** linked in V2 (`merchant_frame_v1`, `merchant_pe_v2`, DWA, experience rebuild CSS absent).

## Product truth

| Surface | API |
|---|---|
| Home | `GET /api/dashboard/summary` → `home_executive_summary_v1` |
| Workspace | `GET /api/cart-workspace/v1/projection` → `zone_b` |

## Gate A probe

Source: `gate_a_probe.json`

| Check | Result |
|---|---|
| Deploy SHA `4fb6604` | PASS |
| `data-cf-ui="v2"` | PASS |
| App bar + stage present | PASS |
| V2 CSS linked / legacy frame+PE **not** linked | PASS |
| Home composition painted | PASS |
| Workspace composition painted | PASS |
| Mobile drawer opens | PASS |

## Captures

| File | Surface |
|---|---|
| `desktop_home.png` | Desktop Home V2 |
| `desktop_workspace.png` | Desktop Workspace V2 |
| `mobile_home.png` | Mobile Home V2 |
| `mobile_workspace.png` | Mobile Workspace V2 |
| `mobile_drawer_open.png` | Mobile navigation open |

## Frame model (intentional break from V1)

- **Desktop:** horizontal App Bar owns primary nav; contextual sidebar is separate and only when useful (Workspace); Home collapses ctx for max stage width.
- **Mobile:** compact app bar (menu + brand + one account affordance); content-sized drawer with sections vs account separated — not a permanent blue rail.

## STOP

Vertical slice only: Frame + Home + Workspace (desktop + mobile).

Do **not** implement Products / Carts / Communication / Settings.
Do **not** replace V1 globally until visual approval.
