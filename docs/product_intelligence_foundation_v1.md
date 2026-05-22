# Product Intelligence Foundation v1

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add product intelligence foundation v1`

Prepares **product-aware recovery decisions** using facts only. This is **not** the continuation cheaper-matching layer (`cartflow_product_intelligence.py`), which remains unchanged.

## What PI foundation is

```text
ProductContext (cart / platform / widget)
        +
reason_tag + CustomerContext
        ↓
ProductIntelligenceContext (safe booleans + price_confidence)
        ↓
[future] recommendation / offer / bundle decisions
```

| Component | Role |
|-----------|------|
| `ProductContext` | Normalized product fields (name, id, category, price, …) |
| `ProductContextResolver` | Extract context from cart, platform payload, widget state, abandoned cart JSON |
| `ProductIntelligenceInputs` | `reason_tag` + product + customer (+ optional catalog for factual checks) |
| `ProductIntelligenceContext` | Facts only: `has_same_category`, `has_cheaper_option`, … |

## What PI foundation is NOT

- Not recommendations, offers, bundles, or discount copy  
- Not fake products, invented prices, or hallucinated alternatives  
- Not wired into recovery send, continuation, WhatsApp, lifecycle, Purchase Truth, attribution, queue, or widget flow in v1  
- Not merchant dashboard ROI claims  

Existing **`services/cartflow_product_intelligence.py`** still powers continuation cheaper paths; do not conflate the two layers.

## Safe output (`ProductIntelligenceContext`)

| Field | Meaning |
|-------|---------|
| `has_same_category` | Category string present on product (v1) |
| `has_cheaper_option` | **Only** if optional `catalog_entries` contain a cheaper, same-category, available SKU |
| `has_shipping_reassurance` | Non-empty `shipping_info` on product |
| `has_warranty_signal` | Non-empty `warranty` on product |
| `price_confidence` | `high` / `medium` / `low` / `none` from price + identity |
| `evidence` | Machine tags (`category_missing`, `catalog_not_provided`, …) |

## Logs

```
[PRODUCT CONTEXT]
store_slug=demo
product_id=...
product_name=...
...

[PRODUCT INTELLIGENCE]
has_cheaper_option=false
price_confidence=high
...
```

Use `observe_product_intelligence(inputs)` for build + log (observation only).

## Future use

1. **Alternatives** — only when catalog + category + lower price verified (same rules as `has_cheaper_option`)  
2. **Offers** — merchant-configured, never generated without catalog/settings  
3. **Bundles** — multi-line cart context + inventory facts  
4. **Integrations** — `ProductContextResolver.resolve_from_platform_payload` + normalized events  

## Risks

| Risk | Mitigation |
|------|------------|
| Confusing PI foundation with continuation PI | Separate module + docs; no imports from foundation into `cartflow_reply_intent_engine` in v1 |
| Hallucinated cheaper SKU | `has_cheaper_option=false` unless catalog rows prove it |
| Incomplete cart JSON | `price_confidence=none`, explicit `evidence` |
| Duplicate logic with `recovery_product_context` | Foundation is canonical for *future* decisions; recovery context unchanged |

## Code map

- `services/product_intelligence_foundation_v1.py`
- `tests/test_product_intelligence_foundation_v1.py`

## Verification

```bash
python -m pytest tests/test_product_intelligence_foundation_v1.py -q
python -m pytest tests/test_cartflow_product_intelligence.py -q
```

**Deploy PASS:** recovery messages and continuation behavior unchanged (foundation not called from production paths until explicitly wired).
