# CartFlow Merchant Daily Brief UX Redesign V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — consumer UX redesign (presentation only)  
**Foundation:** [`merchant_daily_brief_foundation_v1.md`](merchant_daily_brief_foundation_v1.md)  
**Implementation:** [`merchant_daily_brief_implementation_v1.md`](merchant_daily_brief_implementation_v1.md)

---

## Problem

V1 implementation correctly consumed `merchant_decisions_v1`, but the experience felt like **another dashboard card list** — stacked OIA blocks, repeated labels, high reading effort. That violated the foundation principle: the brief must protect attention, not consume it.

---

## Product principle

> The Daily Brief is the first screen a merchant opens every morning — not a report, not Knowledge Layer, not another card grid.

**Goal:** Merchant understands today's priorities in **20–30 seconds** with minimal scrolling.

---

## UX decisions

| Decision | Rationale | Foundation alignment |
|----------|-----------|---------------------|
| **Greeting + today header** replaces section title | Opens like a morning briefing, not a dashboard widget | DBP-6 presentation; answers "what day is this?" instantly |
| **Hero priority panel** for item #1 only | Eye lands on highest-priority decision before reading body copy | Visual hierarchy: Top priority → remaining; MD-A-2 attention budget |
| **Colored priority rail + tag** before text | Priority visible without reading paragraphs | DG-6 attention protection; critical/suggested/attention scannable |
| **Action as headline** when decision declares execute | Merchant sees *what to do* first, not labels | PV-18 what/why/action — action-forward for suggested/critical |
| **Truncated copy** (72/56/48 chars) | High information density, low reading effort | DBP-8 — brief must not overwhelm |
| **Compact queue rows** for items 2–5 | Single-line scan list, not stacked cards | Not KL card layout; minimal scroll on mobile |
| **Calm empty state** (green, short) | Silence is acceptable — no manufactured urgency | DBP-7 |
| **No bordered dashboard box** on section | Brief feels lighter than KL/reasons cards below | "Not another dashboard section" |

---

## Visual hierarchy

```
Greeting (صباح الخير)
  ↓
Today + count (٣ أمور تستحق انتباهك)
  ↓
Hero — الأولوية الآن [priority rail]
  ↓
Queue — numbered compact rows
  ↓
(Knowledge Layer and rest of home below)
```

---

## What did NOT change

- `merchant_decisions_v1` input contract
- Decision Layer, Truth, Proof, Evidence, Governance
- Backend composer (`services/merchant_daily_brief_v1.py`)
- API payload shape

---

## Screenshots

Captured via fixture (`scripts/_daily_brief_ux_redesign_v1_fixture.html`):

| File | State |
|------|-------|
| `scripts/_daily_brief_ux_redesign_v1_out/01_brief_with_items_mobile.png` | Hero + 2 queue rows |
| `scripts/_daily_brief_ux_redesign_v1_out/02_brief_empty_calm_mobile.png` | Calm empty day |
| `scripts/_daily_brief_ux_redesign_v1_out/03_brief_full_fixture_mobile.png` | Full fixture (390×844) |

Regenerate:

```bash
python scripts/_daily_brief_ux_redesign_v1_screenshots.py
```

---

## Files changed

| File | Change |
|------|--------|
| `static/merchant_daily_brief.js` | Briefing renderer (hero + queue + greeting) |
| `static/merchant_app.css` | Briefing layout styles (replaces card stack) |
| `templates/merchant_app.html` | Shell simplified — greeting rendered in JS |

---

*End of Merchant Daily Brief UX Redesign V1.*
