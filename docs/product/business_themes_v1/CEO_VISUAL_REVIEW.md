# Business Theme Engine V1 — CEO Visual Review

**Date (UTC):** 2026-07-25  
**Store:** Living Store / production `demo`  
**Review URL:** `/dev/living-store-home-review`  
**Probe:** `GET /dev/business-themes?store=demo`

---

## What to look for

1. Home «مواضيع المتجر» shows **one** executive theme sentence (not a laundry list of facts).
2. Decision Workspace shows **one card per theme type** — not one card per fact.
3. Shipping / conversion / return stories are not repeated in different words on Home + Workspace + Communication.
4. Merchant can answer in under 10 seconds:
   - biggest opportunity?
   - biggest risk?
   - most important product?
   - most important behaviour?
   - highest-priority decision?

---

## Kill / keep decision

| Outcome | Action |
|---------|--------|
| Themes reduce repetition and clarify the store story | **KEEP** — proceed only after CEO accept |
| Themes add abstraction without clearer Home/Workspace | **REMOVE or REDESIGN** — do not keep complexity |

---

## Evidence checklist

- [ ] `living_store_validation.json` `ok=true`
- [ ] Desktop Home screenshot
- [ ] Mobile Home screenshot
- [ ] Workspace shows theme cards (`gate_business_themes`)
- [ ] MX judgment recorded below

---

## MX judgment (fill after prod)

| Question | Answer |
|----------|--------|
| Does Home feel less repetitive? | _pending deploy_ |
| Does Workspace feel less duplicated? | _pending deploy_ |
| Keep / remove / redesign? | _pending deploy_ |
