# Product Excellence Visual Rebuild V1

**Status:** Prototype gate — **awaiting visual approval before implementation**  
**Date (UTC):** 2026-07-06  
**Scope:** Visual layer rebuild proposals for Merchant Home, Carts Workspace, Cart Detail  
**Authority:** [`merchant_experience_design_language_v1.md`](merchant_experience_design_language_v1.md), [`merchant_experience_patterns_v1.md`](merchant_experience_patterns_v1.md)

**Explicitly out of scope:** Backend, routing, APIs, knowledge production, production CSS/JS changes until approved.

---

## Executive summary

The Merchant Knowledge Infrastructure and Experience Migration are **complete**. The visual layer still reads as an **operational dashboard that evolved over time**.

Visual Rebuild V1 proposes a **from-scratch presentation layer** that expresses what the architecture already knows — without touching Truth, Evidence, Proof, Decision, Explanation, or Routing.

**This deliverable is prototypes + documentation only.** No production implementation until approval.

---

## The gap we are closing

| Layer | Today | Target |
|-------|-------|--------|
| Backend / routing | Mature SaaS | Unchanged |
| Merchant feeling | «Dashboard evolved» | «Designed from day one» |
| Reading path | Sections + tables + labels | One focal story → progressive depth |
| Success metric | Tests / lines changed | 5-second comprehension |

---

## Design objective

Each screen begins with **«What should the merchant feel?»** — not «What did the old HTML look like?»

### Visual principles (rebuild)

1. **Immediate focus** — one Level-1 focal region per viewport (MDL hierarchy).
2. **Large hierarchy** — headline scale 28–36px; body subordinate.
3. **Breathing space** — 48–64px section rhythm; no dense ops chrome.
4. **One focal point** — never two competing heroes.
5. **Whisper noise** — filters, nav, metadata visually quiet.
6. **One primary action** — MXP-9 single CTA per focal region.
7. **Progressive disclosure** — MXP-5 timeline never above fold.

---

## Surface rebuild proposals

### 1. Merchant Home (first target)

**Merchant should feel:** *«CartFlow already handled today — here's the one thing that needs me.»*

| Before | After (prototype) |
|--------|-------------------|
| Equal-weight stacked blocks | L1 hero: today's story in one sentence |
| Section titles compete | Achievements as soft success rail (MXP-1) |
| Attention as list item | One dominant attention card (MXP-2 + MXP-9) |
| Quick nav as footer block | Pill nav — chapters, not modules |
| Dashboard gray density | White hero + calm background |

**Prototype:** `scripts/_product_excellence_visual_rebuild_v1/home_prototype.html`

### 2. Carts Workspace (second target)

**Merchant should feel:** *«I'm in a workspace reviewing cases — not querying a database.»*

| Before | After (prototype) |
|--------|-------------------|
| 6-column HTML table | Card queue + selected conversation panel |
| Filters as ops toolbar | Whisper chips: الكل · يحتاجك · CartFlow يتابع |
| Story buried in cell | One-liner on card; full MXP-4 in panel |
| Expand = more text in row | Split layout: scan left, understand right |
| Amount = table cell | Amount = card headline |

**Prototype:** `scripts/_product_excellence_visual_rebuild_v1/carts_prototype.html`

### 3. Cart Detail (third target)

**Merchant should feel:** *«CartFlow is walking me through this cart's chapter.»*

| Before | After (prototype) |
|--------|-------------------|
| Explanation inside table cell | Full-screen / panel conversation |
| Label walls | Numbered story steps (MXP-4) |
| Proof inline | MXP-5 drawer on demand |
| Multiple button weights | Sticky single primary + ghost secondary |
| Status as chip | Status as L1 headline |

**Prototype:** `scripts/_product_excellence_visual_rebuild_v1/cart_detail_prototype.html`

---

## How MXP patterns appear visually

| Pattern | Visual expression in rebuild | Anti-pattern avoided |
|---------|---------------------------|----------------------|
| **MXP-1 Achievement** | Green-soft cards, ✓ icon, compact rail above attention | KPI grid labeled achievements |
| **MXP-2 Attention** | Warm card, L2 headline, why line, one CTA | Red badge storm |
| **MXP-3 Waiting** | Gray-soft step with ⏳, calm copy | Error styling for patience |
| **MXP-4 Recovery Story** | Vertical numbered flow; whisper kicker labels | «ماذا حدث؟» paragraph walls |
| **MXP-5 Timeline** | Collapsed drawer / «التفاصيل»; recent first | Full history above fold |
| **MXP-6 Insight** | Quiet insight cards below fold | Chart wall |
| **MXP-9 Suggested Action** | Full-width primary button; sticky on mobile | Inline «الإجراء المقترح:» text |
| **MXP-10 Navigation** | Pill nav, chapter names | Sidebar module list |

### Composition order (all three surfaces)

```
Level 1 — dominant message / hero
        ↓
MXP-1 achievements (if any)
        ↓
MXP-2 attention (if any) + MXP-9 primary action
        ↓
MXP-4 story beats (Carts / Detail)
        ↓
MXP-5 timeline (collapsed)
        ↓
Secondary / ghost actions only
```

---

## Prototype assets

| Asset | Path |
|-------|------|
| Design system (prototype CSS) | `scripts/_product_excellence_visual_rebuild_v1/pe-visual-system.css` |
| Comparison hub | `scripts/_product_excellence_visual_rebuild_v1/index.html` |
| Before fixtures | `before_home.html`, `before_carts.html` |
| After prototypes | `home_prototype.html`, `carts_prototype.html`, `cart_detail_prototype.html` |
| Screenshots | `scripts/_product_excellence_visual_rebuild_v1_out/` |
| Preview routes | `routes/product_excellence_preview_v1.py` |

### Deployed preview URLs (visual review only)

Production base: `https://smartreplyai.net`

| Surface | Preview URL |
|---------|-------------|
| **Comparison hub** | https://smartreplyai.net/preview/product-excellence |
| **Merchant Home** | https://smartreplyai.net/preview/product-excellence/home |
| **Carts Workspace** | https://smartreplyai.net/preview/product-excellence/carts |
| **Cart Detail** | https://smartreplyai.net/preview/product-excellence/cart-detail |

No authentication required. Production merchant UI remains at `/dashboard`. Preview responses include header `X-CartFlow-Preview: product-excellence-v1`.

### View locally

```bash
# From repo root — any static server, e.g.:
python -m http.server 8765
# Open: http://127.0.0.1:8765/scripts/_product_excellence_visual_rebuild_v1/index.html
```

Regenerate screenshots:

```bash
python scripts/_product_excellence_visual_rebuild_screenshots.py
```

---

## Before / After screenshots

| File | Content |
|------|---------|
| `01_home_before.png` | Current Home section stack |
| `02_home_after.png` | Rebuilt Home hero + patterns |
| `03_carts_before.png` | Current table layout |
| `04_carts_after.png` | Card workspace + conversation |
| `05_cart_detail_after.png` | Guided conversation detail |
| `06_comparison_index.png` | Full comparison hub |

---

## Implementation gate (after approval)

When approved, implementation will:

1. Introduce `pe-visual-system.css` tokens into production (or merge into `merchant_app.css` under PE namespace).
2. Replace Home renderer (`merchant_home_experience.js`) HTML structure — **same payload**, new composition.
3. Replace Carts row renderer — **same API rows**, card workspace layout.
4. Add Cart Detail route or panel — **same `cart_detail_projection_v1`**, conversation layout.

**Will not change:** services, routing, knowledge contracts, decision logic, tests of business behavior.

---

## Success criteria (5-second test)

Opening any prototype, the merchant should immediately know:

| Question | Where answered |
|----------|----------------|
| What happened? | Story step 1 / hero subline |
| What CartFlow did? | Achievement rail / step 2 |
| What requires attention? | Hero + attention card |
| What can be ignored? | Collapsed timeline; «CartFlow يتابع» chips |

Without reading paragraphs.

---

## Verdict

**Status: AWAITING VISUAL APPROVAL**

Prototypes express the approved architecture visually. Implementation blocked until product sign-off on Home → Carts → Detail rebuild direction.
