# Before / After Reconciliation — Observation Admission Bridge V1

## Before (Living Store — pre-bridge)

| Layer | Count |
|-------|------:|
| Foundation-ready | 4 |
| ORV-admitted | **0** |
| Routed | 0 |
| Home-visible | **0** |
| Workspace-visible | 0 |
| Explicit suppressions | 0 (silent `continue`) |
| Silent drops | **4** |

## After (Living Store rerun + admission bridge)

| Layer | Count |
|-------|------:|
| Foundation-ready | **4** |
| ORV-admitted | **4** |
| Routed | **4** |
| Home-visible | **4** |
| Workspace-visible | **3** |
| Explicit suppressions | **39** |
| Silent drops | **0** |

### Suppressed by reason (after)

| Reason | Count |
|--------|------:|
| capability_already_admitted_for_stronger_product | 32 |
| banned_placeholder_product_key | 6 |
| observation_valid_for_home_not_workspace | 1 |

## Law

```
foundation_ready ≥ orv_admitted = routed = home_visible
workspace_visible ⊆ orv_admitted
silent_drops == 0
```

Evidence: `after_verification.json` · `docs/product/living_store_reality_v1/observation_capture.json`
