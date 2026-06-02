# CartFlow Logo Exploration v2

**Status:** Concept phase — SaaS brand marks (not system diagrams)  
**Supersedes:** `logo_exploration_v1` (removed)  
**Parent spec:** [`../cartflow_brand_system_v1.md`](../cartflow_brand_system_v1.md)

---

## Brand meaning (source of truth)

```
Customer enters a path
        ↓
Customer hesitates
        ↓
System understands → decides → acts
        ↓
Outcome
```

**Philosophy:** Understand → Decide → Act → Recover

**Not:** WhatsApp · Cart · Chat · Recovery messages · Network topology

---

## Directions

| # | Folder | Idea | Avg score |
|---|--------|------|-----------|
| 1 | [`Direction_1_FlowDecision/`](Direction_1_FlowDecision/) | Flow pauses; solid form resolves | **8.6** |
| 2 | [`Direction_2_PathOutcome/`](Direction_2_PathOutcome/) | Path stops; outcome block | **7.7** |
| 3 | [`Direction_3_AbstractJourney/`](Direction_3_AbstractJourney/) | Layered depth → resolution | **7.1** |

Each folder: `explanation.md`, `logo_preview.png`, `app_icon_preview.png` (1024×1024).

---

## Comparison matrix

| Criterion | D1 Flow Decision | D2 Path Outcome | D3 Abstract Journey |
|-----------|------------------|-----------------|---------------------|
| Memorability | 9 | 7 | 7 |
| SaaS professionalism | 9 | 9 | 8 |
| Marketplace icon | 9 | 8 | 7 |
| Dashboard fit | 8 | 9 | 7 |
| Landing page fit | 8 | 7 | 8 |
| Scalability | 9 | 8 | 6 |
| Brand uniqueness | 8 | 6 | 7 |
| **Average** | **8.6** | **7.7** | **7.1** |

---

## Recommendation — ONE winner

### **Direction 1 — Flow Decision**

**Why:**

1. **Only mark that encodes hesitation as form** — the gap between stroke and fill is the brand story without arrows, nodes, or timelines.  
2. **Highest memorability and scalability** — two rectangles and a pause; survives favicon through marketplace icon.  
3. **Reads as SaaS identity** — same restraint tier as Stripe / Linear; would not be mistaken for an internal architecture diagram (v1 failure mode).  
4. **No channel or commerce literalism** — works even if the viewer knows nothing about ecommerce.  
5. **Best balanced score** across all seven criteria.

**Do not advance D2 or D3 to finalization** unless user explicitly overrides:

- **D2** is professionally minimal but risks generic “line + square” at small sizes.  
- **D3** tells a rich story but overlaps with progress-loader and step-diagram patterns.

---

## Next phase (not in scope)

- Final vector logo + wordmark lockup  
- 16px favicon sub-test for Direction 1 gap width  
- Apply to landing / dashboard / widget / Zid — **after** logo finalization

---

## Out of scope (this commit)

- Product UI changes  
- Marketplace asset generation  
- Replacing v1 color/typography tokens in code
