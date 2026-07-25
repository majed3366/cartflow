# Root Cause Report — Observation Admission Gap

**Date (UTC):** 2026-07-25  
**Living Store proof:** foundation ready = 4 · ORV admitted = 0 (before fix)

---

## Symptom

```
Observation Foundation → statement_capabilities_ready: 4
                ↓
ORV present_capabilities: []
                ↓
Home Product Observations: empty / insufficient evidence
```

No silent “empty store” — the store had 1,452 signals, 946 observations, 90 correlations.

---

## Root cause (proven)

**Primary:** Product display-name binding failed for Product Identity tier-B keys.

Living Store correlations use keys like:

`b|demo_watch_band|demo-watch-band`

`project_merchant_observation_findings_v1` required `resolve_real_product_display_name_v1` to return a real name. The resolver only exact-matched catalog/snapshot `sku` / `product_id` / `name`, so composite keys never joined to snapshot names such as «Raven — حزام جلد للساعة».

**Secondary:** First-correlation-wins with silent `continue` — no suppression reason recorded when resolve failed.

**Tertiary (Home slim path):** Gate 1 slim transport skipped ORV attach entirely, so even admitted findings could not reach `extract_home_teaser_inputs_v1` in production Home.

**Not the cause:** Freshness windows, confidence thresholds, or capability readiness logic at Foundation (those already passed).

---

## Rejection without explicit reason (before)

| Stage | Behaviour |
|-------|-----------|
| Canonical product identity | `continue` with no registry row |
| Home slim | ORV never attached → teaser count 0 |

---

## Fix boundary

Close only:

`Observation Foundation → Admission Bridge → ORV → Knowledge Routing → Home / Workspace`

No Product Intelligence. No new observation inventing. No page redesign.
