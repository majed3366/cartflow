# Operational Truth Registry V1

**Version:** `otreg_v1`  
**Code owner:** `services/product_data/operational_truth_registry_v1.py`  
**Rule:** Inventory only facts CartFlow already produces. No invented concepts. No page-specific logic.

| id | source | metric | surfaces | information_class | evidence_threshold |
|----|--------|--------|----------|-------------------|-------------------:|
| `ot_waiting_carts` | AbandonedCart count | `abandoned_carts` | home, carts, decision_workspace | critical_attention | 1 |
| `ot_recovery_backlog` | RecoverySchedule count | `recovery_schedules` | home, carts | recovery_health | 1 |
| `ot_communication_health` | CartRecoveryLog mock_sent | `mock_whatsapp_sent` | communication, home | operational_health | 1 |
| `ot_hesitation_coverage` | CartRecoveryReason count | `hesitation_reasons` | home, decision_workspace | operational_health | 1 |
| `ot_purchase_truth_coverage` | PurchaseTruthRecord count | `purchase_truth` | home | operational_health | 1 |
| `ot_recovery_execution_health` | schedules + mock_sent | composite | carts, home | recovery_health | 1 |

Each truth defines: id, owner, source, severity policy, freshness, lifecycle, visibility, stability, confidence, merchant relevance, expiration policy.

## Severity bands (summary)

| Policy | warning enter | critical enter |
|--------|--------------:|---------------:|
| waiting carts | 3 | 10 |
| recovery backlog | 5 | 20 |
| communication activity | 10 | n/a |
| coverage (informational) | n/a | n/a |
| recovery execution composite | 8 | 25 |
