# CartFlow Brand Validation Board v1

**Direction:** 1 — Flow Decision (exploration v2)  
**Purpose:** Decide if Direction 1 works as the official CartFlow identity before finalization.

---

## Files

| File | Description |
|------|-------------|
| [`validation_board.html`](validation_board.html) | Interactive 6-panel mockup board (open in browser) |
| [`validation_board.png`](validation_board.png) | Static export of the full board (2400px wide) |

---

## Contexts shown

1. **Landing page header** — RTL sticky header with mark + wordmark (current landing layout shape)
2. **Merchant dashboard header** — Top bar with section nav (matches `merchant_app.html` chrome)
3. **Admin dashboard header** — Sidebar head replacing CF monogram (`admin_sidebar.html`)
4. **Zid marketplace** — Listing card with app icon + Arabic subtitle
5. **Browser favicon** — Tab chrome at 16px and 32px
6. **Mobile app icon** — Home screen grid with highlighted CartFlow icon

---

## Rules observed

- Logo geometry **unchanged** from `logo_exploration_v2/Direction_1_FlowDecision`
- **No** production template or static asset changes
- Mock contexts only — for visual evaluation

---

## How to review

1. Open `validation_board.html` in a browser (file:// or local server)
2. Or review `validation_board.png` for a single-glance comparison
3. Complete the checklist at the bottom of the board
4. If approved → proceed to logo finalization phase (vector lockup, favicon export, wordmark pairing)

---

## Source mark

Geometry locked in `validation_board.html` SVG symbol `#cf-mark`:

- Open pill: `rect 5,13 11×6 rx=3` stroke `#2563EB`
- Solid pill: `rect 18,12 9×8 rx=4` fill `#1E293B`
- Gap between forms = hesitation (unchanged from v2)

App icon and marketplace panels reference `../logo_exploration_v2/Direction_1_FlowDecision/app_icon_preview.png`.
