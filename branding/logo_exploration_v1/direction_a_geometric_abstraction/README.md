# Direction A — Geometric Abstraction

**Phase:** Logo exploration v1 (concept only — not final logo)  
**Design school:** Geometric abstraction  
**Metaphor:** Node → Path → Decision → Outcome (grid-anchored)

---

## Visual description

A **square node** (8×8 grid unit) sits at the origin of an **orthogonal path** that travels right, turns 90° down, and terminates in a **smaller resolved node**. The form fits a 24×24 grid with 2px stroke weight at master size.

The mark reads as: **signal captured → routed → outcome fixed**. No curves except optional 1px corner chamfer at the junction (decision point).

**Master construction:** 32×32 viewBox, stroke `#1E293B` (`cf-node`), optional junction accent `#6366F1` (`cf-decision`) on the inner corner only.

---

## Visual rationale

Geometric abstraction aligns with CartFlow’s operational personality. The mark is built on the same vocabulary as dashboard timelines and lifecycle diagrams (nodes + paths), so product and brand feel **one system** rather than a marketing logo bolted onto software.

Orthogonal paths suggest **deliberate process** — not flashy growth curves or chat motion. The square node anchors **trust and stability** at small sizes.

---

## Strengths

| Area | Detail |
|------|--------|
| **Scalability** | Reads clearly at 16px favicon; no thin diagonals that disappear |
| **System fit** | Directly reusable in UI diagrams and empty states |
| **Distinctiveness** | Does not resemble cart, bubble, or send icon |
| **Production** | Simple SVG; easy single-color reproduction |
| **RTL** | Path can mirror horizontally without losing meaning |

---

## Weaknesses

| Area | Detail |
|------|--------|
| **Warmth** | Can feel austere on emotional marketing hero |
| **Uniqueness at large scale** | May read generic “tech grid” without wordmark |
| **Story** | Single path — less narrative than three-node journey |
| **Memorability** | Requires repeated exposure alongside “CartFlow” name |

---

## Suitability matrix

| Context | Rating | Notes |
|---------|--------|-------|
| **Zid Marketplace** | ★★★★☆ | Strong app icon; pair with wordmark on cover banner |
| **Merchant dashboard** | ★★★★★ | Best alignment with lifecycle node UI |
| **Admin dashboard** | ★★★★★ | Dense chrome; mark stays crisp in sidebar |
| **App icon (512)** | ★★★★★ | Centered mark on `cf-primary-muted` or white |
| **Favicon** | ★★★★★ | Highest clarity of the three directions |
| **Widget** | ★★★☆☆ | Acceptable as 16px glyph; prefer wordless minimal node |
| **Landing hero** | ★★★☆☆ | Needs wordmark + headline; mark alone is cold |

---

## Color variants

| Variant | Mark | Background |
|---------|------|------------|
| Primary | `cf-node` on white | Default |
| Reversed | white on `cf-primary` | App icon, dark hero |
| Monochrome | `#000000` | Print, fax, legal |

---

## Files

| File | Purpose |
|------|---------|
| `mark_concept.svg` | 32×32 construction reference |
| `app_icon_concept.svg` | 512×512 padded app icon layout |

---

## Selection guidance

**Choose Direction A if** the priority is **product-native identity** — favicon, dashboard sidebar, admin ops, and marketplace app icon — with maximum legibility at small sizes.

**Do not choose A alone if** the primary launch surface is a **large emotional marketing campaign** without consistent wordmark presence.

---

## Next steps (post-selection)

1. Refine junction chamfer radius across 16 / 24 / 32px masters  
2. Lock clear-space and minimum size (16px)  
3. Export PNG @512, @192, @32 for Zid  
4. Add to `static/brand/` when product redesign begins — **not in v1 foundation**
