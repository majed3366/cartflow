# CartFlow Brand Guidelines v1

**Status:** Official — frozen  
**Source:** Visual Identity board (approved)  
**Path:** `branding/cartflow_brand_foundation_v1/`

This document is the single source of truth for CartFlow visual decisions. All future UI — landing, merchant dashboard, admin, widget, Zid marketplace, documentation, marketing — must follow it.

---

## 1. Brand meaning

CartFlow is a **smart operational system** that moves customers from hesitation to outcome:

```
Customer enters a path
        ↓
Customer hesitates
        ↓
System understands
        ↓
System decides
        ↓
System acts (communicates at the right moment)
        ↓
Outcome / recovery
```

**Philosophy:** Understand → Decide → Act → Recover  
**Arabic tagline (approved):** افهم · قرر · استرجع

### CartFlow is NOT

- A WhatsApp tool
- A cart reminder
- A chatbot
- A message blaster

### CartFlow IS

- Calm, intelligent, trustworthy, operational SaaS
- Behavior understanding → decision → action → recovery

---

## 2. Brand philosophy

1. **Simple and calm** — intelligence without noise  
2. **Geometric abstraction** — flow through shape, not literal commerce icons  
3. **Green as trust** — growth through clarity, not hype gradients  
4. **Bilingual parity** — Arabic and English receive equal typographic care  
5. **One identity** — no parallel color or icon experiments in product work  

**Visual style:** Simple · Clean · Calm · Modern · Trustworthy

**Avoid:** Shopping carts, WhatsApp logos, robots, AI clichés, 3D marketing gloss, random palette experiments

---

## 3. Logo

### 3.1 Symbol (CF monogram)

Approved geometry from Visual Identity board — **do not alter**. Reference: `applications/cartflow_visual_identity_board_v1.png`.

Four elements with consistent white-space gutters (no connecting strokes):

| Element | Shape | Color |
|---------|-------|-------|
| **C** | Thick letterform — rounded outer curve, flat vertical inner edge on the right | `#1E6B4A` |
| **Node** | Solid circle centered in the C opening | `#A7E3C4` |
| **F top** | Small horizontal pill (rounded rectangle) | `#A7E3C4` |
| **F bottom** | Larger tall rounded flag / leaf shape | `#2DA36A` |

**Not approved:** open stroke arcs, uniform accent bars, gap-pause Flow Decision marks, or dot-only reinterpretations.

Master viewBox: `0 0 48 48` — scale uniformly only.

### 3.2 Wordmark

- **Cart** — `#1E6B4A` · Tajawal Bold (700)  
- **Flow** — `#2DA36A` · Tajawal Medium (500)  

### 3.3 Approved files (`logo/`)

| File | Use |
|------|-----|
| `primary_logo.svg` / `.png` | Headers, marketing, documents (symbol + wordmark) |
| `icon_only.svg` / `.png` | Compact chrome, sidebars |
| `app_icon.svg` / `.png` | App store, Zid marketplace (512×512, primary green field) |
| `favicon.svg` / `.png` | Browser tab (32×32, white field, full-color symbol) |

---

## 4. Logo spacing (clear space)

Minimum clear space on all sides = **height of the node circle** in the symbol (1× node diameter).

No text, UI chrome, or other marks may enter this zone.

**Lockup:** Symbol left, wordmark right, gap = 1× node diameter minimum.

---

## 5. Minimum sizes

| Context | Min size | Asset |
|---------|----------|-------|
| Favicon | 16×16 px | `favicon` — symbol only |
| Sidebar / mobile | 24×24 px | `icon_only` |
| Dashboard header | 28–32 px symbol | `primary_logo` or icon + text |
| App icon / Zid | 512×512 px | `app_icon` |
| Print | 12 mm symbol height | vector `primary_logo.svg` |

Below 16px — use `favicon` asset; do not use full wordmark.

---

## 6. Logo usage rules

**Do**

- Use approved SVG first; PNG when raster required
- Use `app_icon` on app stores and Zid
- Use `primary_logo` on landing and dashboard headers
- Maintain proportions — scale uniformly

**Do not**

- Redraw or tweak C thickness, node size, leaf shapes, or gutter spacing
- Rotate, skew, stretch, or add shadows to the symbol
- Place symbol on busy photography without a `cf-surface` plate
- Use archived exploration marks (`branding/_archive/logo_explorations/`)
- Change wordmark colors outside approved palette

---

## 7. Approved colors

See `colors/palette.md` and `colors/tokens.css`.

| Token | Hex | Role |
|-------|-----|------|
| `cf-primary` | `#1E6B4A` | Primary brand, headings, main actions |
| `cf-secondary` | `#2DA36A` | Flow wordmark, secondary accents |
| `cf-accent` | `#A7E3C4` | Symbol F, highlights |
| `cf-background` | `#E9F7EF` | Page backgrounds |
| `cf-surface` | `#F6FBF8` | Cards, panels |
| `cf-text` | `#344054` | Body text |

**No new brand colors** without governance approval.

---

## 8. Typography

| Role | Family | Weight |
|------|--------|--------|
| Headings | Tajawal | Bold (700) |
| Body | Tajawal | Regular (400) |
| UI labels | Tajawal | Medium (500) |

**Load:** Google Fonts `Tajawal` (already used on landing).

**English product copy** may use Tajawal for parity or IBM Plex Sans only where Tajawal Latin is unavailable — prefer Tajawal for unified brand.

**Numbers in tables:** `font-variant-numeric: tabular-nums`

---

## 9. Icon system

See `icons/README.md`.

- **Stroke:** 1.5px, round caps, `#1E6B4A`
- **Process set:** Understand, Decide, Communicate, Recover
- **Dashboard set:** Dashboard, Customers, Settings

Do not introduce alternate icon families (Feather, Lucide wholesale swap, emoji nav, etc.) without approval.

### Shape language (supporting grammar)

| Shape | Meaning |
|-------|---------|
| Circle | Node |
| Curved line | Path |
| Diamond | Decision |
| Rounded square | Outcome |

Use in illustrations only — not as logo substitutes.

---

## 10. Motion principles

- **Flow left-to-right** (RTL layouts: mirror direction, preserve order of meaning)
- **Duration:** 150–250ms for UI; 400ms max for marketing path draws
- **Easing:** ease-out / cubic-bezier(0.2, 0, 0, 1)
- **Allowed:** path draw between process icons, soft fade, 8px panel slide
- **Forbidden:** bounce, confetti, pulsing logos, parallax overload
- **Respect** `prefers-reduced-motion`

Process icon sequence in motion diagrams: **Understand → Decide → Communicate → Recover**

---

## 11. UI principles

1. **White + green** — `cf-surface` cards on `cf-background`; primary green for chrome accents  
2. **One primary action** per panel — `cf-primary` button  
3. **Sidebar** — primary green background, light text (see application board mock)  
4. **Density** — operational clarity over decoration; real data, no fake ROI  
5. **Widget** — calm header band in primary green; subordinate to merchant storefront  
6. **Status colors** — semantic only (success/warning/error); not brand substitutes  
7. **Border radius** — 8px inputs/buttons, 12px cards (consistent with board mockups)  

---

## 12. Exploration status

**Frozen.** Prior explorations archived at `branding/_archive/logo_explorations/`. Do not use their marks in new work.

---

## 13. File index

```
cartflow_brand_foundation_v1/
├── brand_guidelines.md      ← this document
├── governance.md
├── logo/
├── colors/
├── icons/
└── applications/
```

---

*CartFlow Brand Foundation v1 — established from approved Visual Identity board. Product UI adoption is a separate implementation phase.*
