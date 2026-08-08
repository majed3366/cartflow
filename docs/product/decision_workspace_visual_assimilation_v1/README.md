# CartFlow Decision Workspace Visual Assimilation V1

Desktop-first visual assimilation of the **real** Decision Workspace into the frozen CartFlow identity.

## Scope

**ONLY** Decision Workspace (`/dashboard#workspace`).

Not in scope: Home · Carts · Communication · Settings · Landing · Widget.

## What changed (presentation only)

| File | Role |
|---|---|
| `static/decision_workspace_visual_assimilation_v1.css` | Workspace-scoped assimilation (tokens, chrome, cards, hierarchy, actions) |
| `templates/merchant_app.html` | Canonical CF mark in topbar + stylesheet link (workspace-gated) |

No JS / API / decision / projection / routing / permission changes.

## Preview

1. `CARTFLOW_CART_WORKSPACE_V1=true`
2. `ENV=development`
3. Open `/dev/living-store-home-review` then `/dashboard#workspace`
4. Optional seed: `POST /api/cart-workspace/v1/demo-seed`

Capture helper: `scripts/_capture_decision_workspace_visual_assimilation_v1.py`

## Visual proof

| # | File | Purpose |
|---|---|---|
| 1 | `after_desktop_full.png` | Full desktop Decision Workspace |
| 2 | `after_desktop_viewport.png` | Above-the-fold |
| 3 | `after_decision_closeup.png` | Decision area close-up |
| 4 | `after_evidence_closeup.png` | Evidence / knowledge close-up |
| 5 | `after_header_sidebar_closeup.png` | Header + sidebar close-up |
| 6 | `before_after_comparison.png` | Before / After (current real page) |
| — | `before_desktop_viewport.png` | Before baseline (same live surface) |
| — | `before_reference_prod_green_chrome.png` | Historical green-chrome dialect reference |

## Confirmations

1. **No product logic or behavior changed** — CSS + brand mark markup only; projection, commands, statuses, CTAs, and IA unchanged.
2. **Canonical CartFlow brand used** — `static/img/brand/cartflow_cf_mark.png` in Decision Workspace topbar (no legacy monogram).
3. **Arabic RTL preserved** as first-class layout (sidebar start, reading order, decision emphasis).

## Legacy visual treatments removed / replaced (workspace-scoped)

- Forest-green / unrelated green chrome dialect overrides (`merchant_app.css` `--green` topbar/sidebar) when on workspace
- Text-only wordmark without canonical mark (workspace)
- Flat black primary commitment button → navy→teal directional action treatment
- Soft / equal card mass → primary decision densified; next decisions quieter
- Unstructured evidence lines → restrained evidence surface supporting decision densification
- Soft-circle / glow hero leftovers purged on workspace
- Inconsistent radii / shadows aligned to `--cfvi-*` / assimilation tokens
- Generic status-band presentation restyled to calm DS language (function retained)

## Signature DNA (structural only)

- Controlled gap between primary and next decisions
- Navy→teal directional edge on primary decision (micro-atom, not decorative open-C)
- Evidence → decision → action densification
- Intentional silence around the decision shell
- No large logo shapes behind the page

## Design System gaps (not expanded)

- No dedicated “workspace decision band” primitive existed; closest approved tokens used (`--cfvi-*` color/radius/shadow/type).
- Shell green fallback in `merchant_shell_identity_v1.css` left untouched globally; workspace overrides only.

## STOP

Await visual approval before propagating to Home / Carts / Communication / Settings or updating Landing product screenshot.
