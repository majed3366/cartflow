# Decision Workspace Visual Assimilation V1.1 — Structural Hierarchy Correction

## Scope

Real desktop Decision Workspace only (`/dashboard#workspace`).

No Home / Products / Carts / Communication / Settings / Landing.

## What hierarchy changed

| Layer | Before (V1) | After (V1.1) |
|---|---|---|
| Evidence | Soft note box, often flat with decision | Labeled beat `الملاحظة` — lightest band |
| Understanding | Missing on face | New beat `ما يعنيه ذلك` — teal bridge band |
| Decision | Bold line, same card weight as note | Labeled beat `القرار الآن` — densest typography |
| Action | Isolated commit button under text | Beat `خطوتك` — consequence band tied to stack |
| Page density | Wide empty canvas + sparse card | Narrower shell, tighter question→card gap, denser stack |

Reading order is now structurally:

**الملاحظة → ما يعنيه ذلك → القرار الآن → خطوتك**

Secondary / next decisions remain quieter (reduced opacity and flatter beats).

## What remained unchanged

- Projection / admission / ownership / command APIs
- Merchant actions, hrefs, readiness rules, wait states
- Page IA (`#workspace`, primary slot, next slot, quiet empty state)
- Decision content semantics (same decision types; Arabic presentation only)
- Header / sidebar product structure (chrome styling inherited from V1)

## How English leakage was removed

1. **Merchant explanation boundary** (`shadow_pipeline_v1._merchant_why_here_ar`)  
   Maps engine reasons like `Business exception` to Arabic merchant copy before `why_here` is painted.
2. **Narrative sanitize** (`sanitize_merchant_story_text_v1`)  
   Drops Latin-majority strings from merchant-facing story text.
3. **Card face guard** (`cart_workspace_decision_card_v1.js`)  
   `merchantSafeAr` / `isMostlyLatinLeak` strip residual English; action-typed Arabic fallbacks only when evidence is empty after scrub.

Verified in capture probe: `hasBusinessException=false`, `hasLatinLeak=false`.

## Files touched

- `static/cart_workspace_decision_card_v1.js` — beat stack face (presentation)
- `static/decision_workspace_visual_assimilation_v1.css` — V1.1 hierarchy densification
- `services/cart_workspace/shadow_pipeline_v1.py` — Arabic merchant why_here mapping
- `services/decision_workspace_v2/narrative_v1.py` — Latin leak sanitize
- `templates/merchant_app.html` — cache-bust query for V1.1 assets

## Visual proof

| Deliverable | File |
|---|---|
| After desktop full | `after_desktop_full.png` |
| After desktop viewport | `after_desktop_viewport.png` |
| Decision focal close-up | `after_decision_focal_closeup.png` |
| Evidence / understanding close-up | `after_evidence_understanding_closeup.png` |
| Action hierarchy close-up | `after_action_hierarchy_closeup.png` |
| Before / After | `before_after_comparison.png` |

Before baseline = V1 assimilated viewport (`decision_workspace_visual_assimilation_v1/after_desktop_viewport.png`).

## STOP

Await visual approval before any other surface or Landing screenshot work.
