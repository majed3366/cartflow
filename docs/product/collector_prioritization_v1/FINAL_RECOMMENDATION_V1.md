# Collector Prioritization V1 — Final Recommendation

**Status:** Research / architecture only — **no collectors implemented**.  
**Authority inputs:** Evidence Gap Registry, Diagnostic families, Living Store `insufficient_evidence` (shipping stage), existing widget/recovery signals, provider constraints.

---

## If CartFlow can build only ONE collector next

### Build: `shipping_cost_first_shown`

**Collector name:** Shipping Cost First Shown  
**Family:** `checkout_abandonment_after_shipping`  
**Closes Evidence Gap:** shipping-stage leave without subtype (Living Store primary gap)

### Why this one

1. **Living Store truth:** Primary published diagnosis is honest `insufficient_evidence` after customers leave at Shipping — not because CartFlow lacks “intelligence,” but because **cost / time / options / payment are indistinguishable**.
2. **Diagnostic leverage:** Knowing whether a **numeric shipping cost was shown** separates:
   - `shipping_cost` vs `late_shipping_disclosure`
   - and, with stage already known, sharply reduces the “Unknown” bucket that forces insufficiency.
3. **Recommendation unlock:** Only with this evidence may CartFlow safely recommend *show/fix shipping cost earlier* — today that recommendation is correctly suppressed.
4. **Coverage:** Implementable via **CartFlow widget / checkout instrumentation** across Zid, Salla, and Shopify storefronts (generic). Does **not** require waiting for provider-specific payment webhooks.
5. **Cost:** Medium engineering; low runtime (one event per session at shipping reveal); bounded storage.
6. **Dependency:** Builds on existing weak stage signal (`shipping` / `shipping_stage_observed`). No upstream collector required.

### What this is not

- Not “collect everything about shipping.”
- Not payment or product gallery first — those improve other families that are **not** the dominant Living Store insufficiency.

### Immediate next (Wave 1 pair, if two)

If two collectors are allowed in Wave 1:

1. `shipping_cost_first_shown`  
2. `shipping_option_selected`  

Together they separate **cost vs options** — the remaining ambiguity after cost visibility is known.

---

**STOP.** Do not implement collectors until this roadmap is explicitly approved for Wave 1 execution.
