# Commercial Interpretation Layer V1

**Status:** Implemented — first production interpretation  
**Interpretation ID:** `missing_contact_blocks_recovery_v1`  
**Module:** `services/commercial_interpretation_v1.py`

## Purpose

Transform existing canonical CartFlow operational truth into governed merchant-value language:

1. Commercial conclusion  
2. Supporting evidence  
3. Business impact  
4. Current CartFlow action  
5. Merchant action (when required)  
6. Confidence level  

Deterministic. Evidence-based. Not AI.

## Canonical evidence source

| Field | Owner |
|-------|--------|
| `no_phone_total` | `services/dashboard_counter_totals_v1.py` |
| Classification rule | `services/dashboard_no_phone_facet_v1.py` (`is_no_phone_pre_send_dashboard_row`) |
| Cart drilldown | `#carts?tab=nophone` |

Evidence count in the interpretation **must equal** Cart-page `no_phone_total`. No second independent query/classification.

## Threshold rule (V1)

| Condition | Result |
|-----------|--------|
| `count == 0` | Suppress (`suppression_reason=count_zero`) |
| `count > 0` | Generate observation |
| Generated in V1 | Mark `is_primary_commercial_blocker=true` (sole V1 blocker interpretation) |
| Confidence | High when count is direct canonical counter evidence |

**Threshold ownership:** Commercial Interpretation Layer (`commercial_interpretation_v1.py`).

## Consumers

- **Home** — `compose_merchant_home_experience_v1` → `apply_commercial_interpretation_to_home_v1` (Understanding primary; Attention CTA drilldown aligned)
- **Knowledge** — `enrich_knowledge_report_commercial_interpretation_v1` after KL projection

Home and Knowledge **consume** the package. They must not rebuild conclusions.

## Failure behavior

- Home continues loading on failure  
- Last valid package retained per `store_slug` when safe  
- Observability records `failure_reason`  
- No invented conclusions  

## Non-goals

No PIB-4. No AI. No Widget/WhatsApp changes. No additional interpretations until this one is visually approved.
