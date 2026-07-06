# Product Excellence Visual Rebuild V2 — Zero-Legacy Layout

**Status:** AWAITING VISUAL APPROVAL — mockups only, **no production implementation**  
**Date (UTC):** 2026-07-06  
**Supersedes:** V1 prototypes (rejected — still read as dashboard/table)  
**Authority:** MDL V1, MXP V1, Merchant Experience Foundation

---

## Final verdict (Product Owner)

| Surface | V1 result | V2 requirement |
|---------|-----------|----------------|
| **Home** | Text on page, four headings | **One story**, one visual focal point |
| **Carts** | Expanded table | **Today's work queue** — scan, don't read |
| **Cart Detail** | Operational record | **Guided conversation** — not diagnostics |

**Do not iterate V1 or production UI.** V2 starts from a blank canvas.

---

## Zero-legacy rule

Pretend the dashboard never existed. V2 does **not** inherit:

- Section stack layout (`ma-home-block` pattern)
- Table columns or expand-in-cell model
- Question-label explanation walls
- Filter bar ops chrome
- Equal-weight headings

---

## Design question

> *If CartFlow launched today as an intelligent operating companion, how would this screen look?*

Not: *How do we improve the current dashboard?*

---

## Visual hierarchy (every screen)

```
One Hero
    ↓
One Primary Story
    ↓
One Primary Action
    ↓
Supporting context (whisper)
    ↓
Hidden detail (MXP-5)
```

---

## Surface designs

### Home V2

**Feeling:** CartFlow has already been working. One morning story.

| Element | V2 treatment |
|---------|--------------|
| **Hero** | Full-bleed gradient card — single headline + integrated story line |
| **Achievements (MXP-1)** | Pills inside hero — no «بينما كنت بعيداً» section title |
| **Attention (MXP-2/9)** | One action card — eyebrow + headline + single CTA |
| **Insight (MXP-6)** | Whisper card — uppercase label, one line |

**Files:** `home_v2.html` (mobile-first), `home_v2_desktop.html` (split hero + action)

### Carts V2

**Feeling:** Today's work queue. Every cart understandable in one glance.

| Element | V2 treatment |
|---------|--------------|
| **Layout** | Accent-bar queue cards — amount + one scan line + time |
| **Filters** | Segmented pills — «الكل · يحتاجك · يتابع» |
| **Selection** | Border glow + desktop conversation panel |
| **Mobile** | Tap card → full conversation page |

**File:** `carts_v2.html` (responsive: mobile CTA / desktop split)

### Cart Detail V2

**Feeling:** Guided conversation with visual flow connectors.

| Beat | Visual |
|------|--------|
| What happened | Icon step 1 |
| CartFlow did | Green ✓ step |
| What's next | Indigo ⏳ step |
| Your action | Orange → step |
| Timeline | Hidden until tap |
| Action | Sticky full-width primary |

**File:** `cart_detail_v2.html`

---

## MXP pattern mapping

| Pattern | V1 failure | V2 expression |
|---------|------------|---------------|
| MXP-1 | Separate achievement section | Hero stat pills |
| MXP-2 | List under heading | Single «يحتاجك الآن» card |
| MXP-3 | Text band in table cell | Queue accent + flow icon |
| MXP-4 | Label lines in cell | Vertical icon flow |
| MXP-5 | `<details>` in row | Footer drawer / hidden panel |
| MXP-9 | Small primary link | Full-width sticky CTA |

---

## Mockup assets

| Asset | Path |
|-------|------|
| Design system V2 | `scripts/_product_excellence_visual_rebuild_v2/pe-v2-system.css` |
| Review hub | `scripts/_product_excellence_visual_rebuild_v2/index.html` |
| Home mobile | `home_v2.html` |
| Home desktop | `home_v2_desktop.html` |
| Carts | `carts_v2.html` |
| Cart detail | `cart_detail_v2.html` |
| Before fixtures | `before_home_legacy.html`, `before_carts_legacy.html` |
| Screenshots | `scripts/_product_excellence_visual_rebuild_v2_out/` |

### View locally

```bash
python -m http.server 8765
# Open: http://127.0.0.1:8765/scripts/_product_excellence_visual_rebuild_v2/index.html
```

```bash
python scripts/_product_excellence_visual_rebuild_v2_screenshots.py
```

---

## Before / After (screenshots)

| File | Content |
|------|---------|
| `01_home_v2_mobile.png` | V2 home mobile |
| `02_home_v2_desktop.png` | V2 home desktop split |
| `03_carts_v2_mobile.png` | V2 queue mobile |
| `04_carts_v2_desktop.png` | V2 queue + panel desktop |
| `05_cart_detail_v2_mobile.png` | V2 conversation |
| `06_before_home_legacy.png` | Legacy section stack |
| `07_before_carts_legacy.png` | Legacy table |
| `08_comparison_hub.png` | Full review hub |

---

## 5-second success test

| Screen | Merchant understands in 5s |
|--------|---------------------------|
| Home | CartFlow worked; one thing needs me |
| Carts | This is my queue; one cart needs me |
| Detail | Story arc: happened → CF → next → my move |

If paragraphs are required → **design fails**.

---

## Implementation gate

**Blocked until visual approval.**

After approval:

1. Wire V2 CSS namespace into production (new files — do not patch legacy incrementally)
2. Replace Home/Carts/Detail **renderers only** — same payloads
3. Add preview routes `/preview/product-excellence-v2/*` (optional)

**Not in scope until approved:** production code, push, API, routing, tests changes.

---

## Success reaction test

Show mockups to someone who has never seen CartFlow.

| Reaction | Action |
|----------|--------|
| «Modern SaaS operating system» | Proceed to implementation planning |
| «Looks like a dashboard» | Start over |

---

## Relation to V1 preview routes

V1 remains at `/preview/product-excellence/*` for reference.

### Deployed V2 preview URLs (visual review only)

Production base: `https://smartreplyai.net`

| Surface | Preview URL |
|---------|-------------|
| **Home V2** | https://smartreplyai.net/preview/product-excellence-v2/home |
| **Carts Workspace V2** | https://smartreplyai.net/preview/product-excellence-v2/carts |
| **Cart Detail V2** | https://smartreplyai.net/preview/product-excellence-v2/cart-detail |

No authentication required. Production merchant UI remains at `/dashboard`. Preview responses include header `X-CartFlow-Preview: product-excellence-v2`.
