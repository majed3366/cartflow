# Cross-Surface Projection Verification V1

## Contract

All merchant surfaces read executive truth from `merchant_publication_v1`.

| Surface | Question | Consumes |
|---------|----------|----------|
| Home | How is my store / what first? | HES sections from publication |
| Workspace | Why this decision? | Same primary via `apply_publication_priority_to_decisions_v1` |
| Products | Which products need attention? | Commerce situations consumers + merchant titles |
| Carts | What is each cart’s status? | Operational list + `cart_condition` banner |
| Communication | What happened in outreach? | Operational history + `communication_condition` |

## Consistency checks

1. Home `أهم قرار اليوم` == publication `primary_action`  
2. Workspace primary card action == same `primary_action`  
3. Home store condition == publication `store_condition.summary_ar`  
4. Communication never says “طبيعي” when `communication_condition.constrained`  
5. Carts distinguish individual “لا يحتاج إجراءً فردياً الآن.” from systemic Workspace action  
6. No second decision with the same/similar action as P1  

## Code ownership

- Compose: `services/decision_composition_engine_v1/merchant_publication_v1.py`
- Home: `services/home_executive_summary_v1/compose_v1.py` + `slim_transport_v1.py`
- Workspace: `services/cart_workspace/business_findings_enrichment_v1.py`
- UI: `static/home_executive_summary_v1.js`, `commerce_situations_surfaces_v1.js`, `cart_workspace_decision_card_v1.js`
