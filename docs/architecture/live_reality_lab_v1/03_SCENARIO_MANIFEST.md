# Live Reality Dataset V1 — Scenarios

**dataset_version:** `live_reality_dataset_v1`  
**store_slug:** `cf_live_reality_lab`

| ID | Intent |
|----|--------|
| R1 | Communication obligation (no_phone carts) |
| R2 | Shipping hesitation → commercial mission |
| R3 | Price hesitation → commercial mission |
| R4 | Product confidence |
| R5 | Product opportunity focus |
| R6 | Insufficient evidence |
| R7 | Ops contact + merchandising commercial (Priority Surface) |
| R8 | CDC ACTION_CHOSEN |
| R9 | CDC UNDER_MEASUREMENT |
| R10 | CDC RECHECK_DUE |
| R11 | Portfolio conflict (active shipping; price deferred) |
| R12 | Capacity released after close |

Machine-readable manifests: `services/live_reality_lab_v1/dataset_v1.py`

Truth writers: `CartRecoveryReason` (source `live_reality_lab_v1`) · lab-prefixed `AbandonedCart` · CDC via normal accept/confirm/close APIs.

No frontend JSON injection. No threshold bypass. No lab-specific ranker.
