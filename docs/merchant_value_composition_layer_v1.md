# Merchant Value Composition Layer V1

**Status:** Implemented  
**Authority:** `merchant_value_composition_v1`  
**Position:** After Merchant Intelligence Service, before Merchant Experience / UI

---

## Mission

Convert **Merchant Intelligence** into **Merchant Value** — governed value stories that answer:

1. ماذا حدث؟
2. لماذا يهم؟
3. ماذا فعل CartFlow؟
4. هل تحتاج أن تتدخل؟

This layer **composes** existing truth, intelligence, recommendations, memory, and merchant language. It does **not** mint groups, recommendations, trends, or ROI.

---

## Architectural position

```
Truth → Evidence → Decision → Explanation → Knowledge Routing
        → Merchant Intelligence Service
        → Merchant Value Composition Layer   ← this document
        → Merchant Experience / UI
```

**Forbidden changes:** Truth, Purchase Truth, Lifecycle Truth, Decision Layer, MI Service, Knowledge Routing, recovery/WhatsApp/widget logic.

---

## Inputs (read-only)

| Source | Fields used |
|--------|-------------|
| `merchant_intelligence_store_v1` | `groups`, `recommendations`, `memory`, `priorities` |
| Per-cart bundles | `merchant_intelligence_v1`, `merchant_explanation_v1`, `cart_detail_projection_v1` |
| Evidence | `merchant_proof_surface_v1`, `merchant_cart_fact_v1`, purchase/lifecycle fields |

Wording follows **`docs/cartflow_merchant_language_system_v1.md`**.

---

## Output: `merchant_value_stories_v1`

```json
{
  "version": "v1",
  "authority": "merchant_value_composition_v1",
  "stories": [ { "...story contract..." } ],
  "observability": { "stories_composed": 3, "groups_considered": 5, "reviewable": true }
}
```

### Story contract

| Field | Purpose |
|-------|---------|
| `story_id` | Stable composed id |
| `story_type` | Internal type key (not shown to merchant) |
| `title_ar` | Card title |
| `headline_ar` | What happened |
| `merchant_meaning_ar` | Why it matters |
| `cartflow_action_ar` | What CartFlow did |
| `observed_result_ar` | What changed (when evidenced) |
| `recommendation_ar` | What merchant may consider |
| `merchant_action_line_ar` | Intervention summary |
| `action_required` | Boolean |
| `confidence` | From source group |
| `evidence_ids` | Traceability |
| `source_group_ids` | MI group lineage |
| `source_recommendation_ids` | Recommendation lineage |
| `affected_cart_keys` | Representative carts for UI |
| `eligible_surfaces` | Routing eligibility |
| `display_priority` | Sort hint |
| `diagnostics_internal` | Internal only — never rendered |

---

## Story types (V1 minimum)

| Type | MI source |
|------|-----------|
| `price_hesitation_story` | `repeated_hesitation` + `pattern_key: reason:price` |
| `shipping_hesitation_story` | `repeated_hesitation` + `pattern_key: reason:shipping` |
| `returned_without_purchase_story` | `returned`, `waiting_purchase` |
| `recovered_purchase_story` | `completed` + purchase evidence |
| `needs_merchant_story` | `needs_merchant` |
| `waiting_reply_story` | `waiting_reply` |

---

## Composition rules

- Every story must trace to MI groups and/or cart evidence.
- No story without `evidence_ids` or `affected_cart_keys`.
- Missing evidence → neutral fallback copy, never fabrication.
- ROI/revenue claims blocked unless Purchase Truth supports them.
- All merchant-facing strings are Arabic.

---

## Transport

`ensure_normal_carts_merchant_value_stories_v1(payload)` runs after MI attach on:

- Snapshot read (`build_normal_carts_from_snapshot`)
- Snapshot write (`build_canonical_normal_carts_payload`)
- Live normal-carts API

Snapshot slim allowlist includes `merchant_value_stories_v1`.

---

## First consumer: Carts

`static/merchant_intelligence_carts_v1.js` prefers `merchant_value_stories_v1.stories` over raw group text. Groups remain internal structure; merchant sees value stories with representative carts.

---

## Implementation

| File | Role |
|------|------|
| `services/merchant_value_composition_v1.py` | Composition service |
| `static/merchant_intelligence_carts_v1.js` | Story rendering |
| `static/merchant_dashboard_lazy.js` | Workspace wiring |

Tests: `tests/test_merchant_value_composition_v1.py`
