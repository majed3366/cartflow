# Merchant UI Production Config Parity Regression Gate V1

**Mode:** AUTHORIZED MINIMAL IMPLEMENTATION — configuration governance only  
**Base:** `5606530c736416c0141b2f4a7f2cfef0e92290bc`  
**Invariant:** `MERCHANT-UI-INV-CONFIG-01`

## Deliverables

| Artifact | Path |
|----------|------|
| Material flag registry + effective compare | `services/merchant_ui_config_parity_v1.py` |
| Visual deploy authorization compound gate | `services/merchant_visual_deploy_authorization_v1.py` |
| Runtime identity attachment | `services/merchant_runtime_identity_v1.py` |
| Cases A–E + deploy integration tests | `tests/test_merchant_ui_config_parity_v1.py` |
| Visual regression gate hook | `tests/test_merchant_visual_identity_regression_gate_v1.py` |

**Not modified:** painters, CSS, semantic model, shell, scheduler, QueuePool, production flags.

Full scoreboard: [`REPORT.md`](./REPORT.md)
