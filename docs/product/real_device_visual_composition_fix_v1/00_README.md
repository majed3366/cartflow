# Controlled Real-Device Visual Composition Fix V1

**Base (failed candidate):** `67ed1432fb9e7cb9cd7366b2f9f08ab79d4dd7ee`  
**Branch:** `candidate/real-device-visual-composition-fix-v1`  
**Source RCA:** `docs/product/real_device_visual_failure_rca_v1/`  
**Cache bust:** `rdfix1`  
**semantic-visual-model-v1:** unchanged  
**Deploy:** NOT performed

## What changed

Geometry amplification only — page organisms made merchant-readable.

| Surface | Fix |
|---------|-----|
| Home | Primary mass 10px / min-height 11.5rem; orbit axis; asymmetric satellite max-widths; mobile preserves gravity edge |
| Workspace | Void ≥40px (large 56px); mass dominates; void also when insufficient; review requires `CARTFLOW_CART_WORKSPACE_V1=true` |
| Carts | Detail no longer white card; 6px actionable edge; selected→detail spine |
| Communication | Ticks ≥12px + connector; truthful step slice; dormant scaffold when empty |
| Settings | Joints 18×18 (16 mobile) + ledger rail |

## Contract blind spots

Closed via `tests/test_real_device_visual_composition_fix_v1.py` (FRC-01…08 measurable thresholds).
