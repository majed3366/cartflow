# CF-CDA Production Contract V1

**Primitive:** Commercial Decision Arc — `cf-cda`  
**Status:** FINAL PASS — frozen for production integration  
**Logic baseline:** `b1867d2c`  
**Exploration:** CLOSED

## Allowed states (production)

| State | When |
|-------|------|
| `action_chosen` | Primary opportunity with ready production truth (default Home/WS active) |
| `under_measurement` | Presentation when measure continuum should dominate (same opportunity; visual emphasis) |
| `recheck_due` | Workspace (or Home) when recheck hinge should dominate |
| `insufficient_evidence` | `col.empty` / no primary — intentional withhold |

Lab-only states (discovered/won/lost/learned) are **not** required on Merchant UI V1 integration.

## Allowed geometric variations

- Continuous spine open-C owning decision core
- Decision mass node
- Move taper (directional)
- Measure flow as **extension of the same stroke** (no progress bar / diamond stepper)
- Recheck hinge arm → hinge pocket
- Hollow dashed scoop for insufficient

## Forbidden

- Progress bars, gauges, donuts, traffic lights, AI sparkle
- Generic empty illustration
- Applying `cf-cda` to every secondary as full organism
- Merging into operational gravity well
- Hardcoded lab mission objects / simulation truth on `/dashboard`

## Layout / text relationship

- Spine owns core via proximity + shared baseline
- Headline beside mass — not forced inside SVG if readability suffers
- Evidence remains `<details>` supporting, collapsed by default
- Measurement + recheck copy live inside the organism, not as equal stacked cards

## Mobile behavior

- Min spine width ≈ 40–44px at 390px
- No stroke crossing readable copy
- No horizontal overflow
- Same structural relationship as desktop

## Minimum safe dimensions

- Organism min-height active ≈ 168–200px
- Recheck ≈ 240px+
- Insufficient ≈ 150px+
- Compact secondary: lighter chrome **without** full spine organism (or compact spine only if space allows)

## Grayscale

Geometry alone must still distinguish active / measure / recheck / insufficient.

## Adapter rule

Production maps COL package fields only:

`title_ar`, `why_ar`, `action_ar`, `measure_ar`, `recheck_ar`, `decision_contract_ar`, `evidence.lines_ar`, `truth_class`, `empty`

No new intelligence fields.
