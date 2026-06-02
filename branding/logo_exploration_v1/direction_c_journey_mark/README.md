# Direction C — Journey Mark

**Phase:** Logo exploration v1 (concept only — not final logo)  
**Design school:** Geometric abstraction  
**Metaphor:** Three nodes on a path — **Understand → Decide → Act → Recover** as spatial sequence

---

## Visual description

**Three nodes** of decreasing visual weight (or equal weight with middle node accented) connect via straight **path segments** with a **junction at the center node** (Decide). The third segment leads to a **filled resolution square** (Outcome / Recover) — slightly larger than signal nodes.

Layout options:
- **Horizontal (LTR):** signal → junction → outcome (mirrors for RTL)
- **Compact:** diagonal path for app icon square

Stroke 1.5–2px; nodes as 4px circles or 4×4px squares for grid consistency.

**Master construction:** 32×32 viewBox; nodes `#1E293B`; center node ring `#6366F1`; path `#3B82F6`; outcome fill `#2563EB`.

---

## Visual rationale

CartFlow’s brand meaning is a **journey**, not a single action. Three nodes make the **Understand → Decide → Act → Recover** story visible without icons or text labels. The center accent node is the **merchant decision moment** — the product’s differentiated control point.

This direction best expresses **lifecycle** and **recovery as a process**, aligning with dashboard customer lifecycle states and operational documentation.

---

## Strengths

| Area | Detail |
|------|--------|
| **Narrative** | Strongest semantic match to brand meaning table |
| **Dashboard** | Lifecycle timelines can echo the same three-node grammar |
| **Documentation** | Diagrams and docs inherit mark language easily |
| **Differentiation** | Unlikely confused with cart, chat, or AI icons |
| **Bilingual storytelling** | Works in diagrams for Arabic and English docs |

---

## Weaknesses

| Area | Detail |
|------|--------|
| **Complexity** | Three nodes crowded at 16px favicon |
| **Width** | Horizontal lockup needs space; poor for ultra-narrow slots |
| **Marketing minimalism** | Busier than A or B at small scale |
| **App icon** | Requires vertical or triangular compact rearrangement |

---

## Suitability matrix

| Context | Rating | Notes |
|---------|--------|-------|
| **Zid Marketplace** | ★★★★☆ | Good with explanatory subtitle; icon needs compact variant |
| **Merchant dashboard** | ★★★★★ | Pairs with lifecycle UI; co-brand in header |
| **Admin dashboard** | ★★★★☆ | Use compact 2-node variant in sidebar |
| **App icon (512)** | ★★★☆☆ | Use triangular compact layout in `app_icon_concept.svg` |
| **Favicon** | ★★☆☆☆ | Recommend extracting center+outcome only for 16px |
| **Widget** | ★★☆☆☆ | Too narrative; avoid on storefront |
| **Landing hero** | ★★★★☆ | Strong for “how it works” diagram beside hero copy |

---

## Color variants

| Variant | Mark | Background |
|---------|------|------------|
| Full story | 3 nodes + path (horizontal) | Marketing, docs |
| Compact | 2 nodes + outcome (diagonal) | App icon |
| Monochrome | Single ink | Legal, stamps |

---

## Files

| File | Purpose |
|------|---------|
| `mark_concept.svg` | 32×32 horizontal three-node journey |
| `app_icon_concept.svg` | 512×512 compact diagonal arrangement |

---

## Selection guidance

**Choose Direction C if** the priority is **merchant dashboard, lifecycle storytelling, and documentation** where the mark must teach the operational model at a glance.

**Requires** a derived **simple icon sub-mark** (2 elements max) for favicon and widget — do not shrink full three-node mark below 24px.

---

## Comparison snapshot

| vs A | vs B |
|------|------|
| C tells story; A tells structure | C is multi-step; B is single motion |
| C busier at small size | B more marketplace-flashy; C more product-honest |

---

## Next steps (post-selection)

1. Finalize compact app icon geometry (diagonal 3-node)  
2. Define favicon sub-mark: outcome square + single path  
3. Document RTL mirroring rules for marketplace screenshots  
4. Align lifecycle diagram components in dashboard redesign spec
