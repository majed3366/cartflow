# Merchant Intelligence Service V1

**Status:** Implemented  
**Authority:** `merchant_intelligence_v1`  
**Constitutional basis:** [`merchant_intelligence_authority_foundation_v1.md`](merchant_intelligence_authority_foundation_v1.md)  
**Service module:** `services/merchant_intelligence_v1.py`

---

## Mission

Merchant Intelligence answers one question:

> **What should the merchant understand right now?**

—not—

> What records exist?

The service consumes governed platform truth and knowledge outputs. It produces merchant understanding as structured intelligence objects. It does **not** render UI, HTML, CSS, pages, or surface-specific copy outside governed recommendation objects.

---

## Architectural position

```
Truth (Purchase, Lifecycle, Phone, VIP)
        ↓
Evidence + Proof Surface
        ↓
Decision Layer + Merchant Explanation
        ↓
Knowledge Producers + Routing metadata
        ↓
┌─────────────────────────────────────┐
│  Merchant Intelligence Service V1   │  ← this service
│  groups · recommendations · memory  │
│  · priorities · surface eligibility   │
└─────────────────────────────────────┘
        ↓
Surfaces (Home, Carts, Weekly Brief, Notifications, AI, Executive)
        ↓ read-only projection
Presentation (CXF, MDL, MXP, Visual System)
```

**Permanent rule:** No surface may derive its own intelligence. Every surface consumes the same governed Merchant Intelligence objects.

---

## Inputs (consumed only)

| Input | Source | Usage |
|-------|--------|-------|
| `merchant_cart_primary_bucket` | Cart row classifier | Operational group assignment |
| `customer_lifecycle_state` | Lifecycle truth | Returned, purchase window, completed |
| `customer_lifecycle_merchant_needed_ar` | Lifecycle truth | `needs_merchant` precedence |
| `merchant_decisions_v1` (published) | Decision Layer | Recommendations, needs_merchant |
| `merchant_proof_surface_v1` | Proof Surface | Evidence references |
| `merchant_explanation_v1` | Explanation Layer | Recommendation copy fallback |
| `is_vip_lane` | VIP operational truth | VIP group |
| `has_phone` | Phone truth | waiting_phone / no_contact |
| `reason_tag` | Hesitation truth | Pattern groups + memory |
| `product_id` / `zid_product_id` | Product identity | Product hesitation patterns |
| `merchant_intervention_executable` | Intervention eligibility | Recommendation type projection |
| `comparison_context` (optional) | Caller-provided snapshots | Temporal memory beats |

**Forbidden inputs:** UI state, page context, CSS classes, template flags, frontend sort order, local JS heuristics.

---

## Outputs (four families)

### 1. Intelligence Groups

Operational groups (per cart, aggregated at store level):

| `group_id` | Title (AR) | Trigger |
|------------|------------|---------|
| `needs_merchant` | يحتاج تدخلك | Published intervention decision or merchant-needed lifecycle truth |
| `vip` | سلة مهمة — VIP | `is_vip_lane` |
| `no_contact` | لا يمكن التواصل | `PRIMARY_NO_PHONE` bucket |
| `waiting_phone` | بانتظار الجوال | Missing phone before send |
| `returned` | عاد للمتجر | Return-to-site lifecycle / bucket |
| `waiting_purchase` | نافذة الشراء | `waiting_purchase_window` |
| `waiting_reply` | بانتظار رد العميل | Sent / awaiting customer |
| `completed` | مكتملة | Purchase truth or recovered lifecycle |

Pattern groups (store-level, cross-cart):

| `group_id` | Threshold |
|------------|-----------|
| `repeated_hesitation` | ≥3 carts same `reason_tag` |
| `product_hesitation` | ≥2 carts same product |
| `risk_pattern` | ≥3 observation decisions in batch |

Each group exposes: `group_id`, `title_ar`, `meaning_ar`, `reason`, `priority`, `confidence`, `evidence_count`, `affected_carts`, `representative_item`, `merchant_summary_ar`, `eligible_surfaces`, `authority`, `creation_reason`.

**Precedence rule (MIA-G4):** When a cart qualifies for both `needs_merchant` and `waiting_reply`, **`needs_merchant` wins**.

### 2. Recommendations

Derived from published decisions — never free-text authored in pages.

| `recommendation_type` | Source |
|-----------------------|--------|
| `required_action` | `critical_action` decision class |
| `suggested_action` | `suggested_action` / eligible `needs_attention` / merchant-needed intervention |
| `watch_only` | Observation + pattern metadata |
| `informational` | Observation (default) |
| `no_action` | Completed / calm bucket |
| `blocked` | Missing phone policy block |
| `suppressed` | Decision suppression (not rendered) |

Each recommendation exposes: `recommendation_id`, `recommendation_type`, `decision_class`, `priority`, `confidence`, `merchant_message_ar`, `supporting_evidence`, `expiration`, `eligible_surfaces`, `authority`, `creation_reason`.

### 3. Merchant Memory

Temporal understanding beats (evidence-backed):

| `memory_type` | Requires |
|---------------|----------|
| `compared_to_yesterday` | `comparison_context.group_counts_yesterday` |
| `compared_to_last_week` | `comparison_context.group_counts_last_week` |
| `repeated_pattern` | In-batch reason distribution (≥2) |
| `resolved` | Completed group count > 0 |

Each beat exposes: `memory_type`, `comparison_window`, `finding_ar`, `evidence`, `confidence`, `direction`, `eligible_surfaces`.

### 4. Merchant Priorities

Ordered merchant attention bands:

| `priority_band` | Source |
|-----------------|--------|
| `highest` | Required action recommendations |
| `today` | Suggested action recommendations |
| `watching` | Watch / blocked recommendations |
| `completed` | Completed group summary |

Each priority exposes: `priority_rank`, `priority_band`, `reason`, `merchant_message_ar`, `recommended_action_type`, `confidence`, `eligible_surfaces`.

---

## Service ownership

| Owns | Does not own |
|------|--------------|
| Group assignment | Truth (purchase, lifecycle, phone) |
| Recommendation derivation | Decision execution |
| Merchant memory beats | Knowledge production |
| Priority ordering | Knowledge routing |
| Surface eligibility metadata | Rendering / visual hierarchy |
| Confidence metadata on outputs | Page composition |
| Evidence references on outputs | Merchant wording outside governed objects |

---

## Surface contract

Every intelligence object carries `eligible_surfaces` — surfaces must filter, never re-derive:

| Surface key | Description |
|-------------|-------------|
| `merchant_home` | Home operating center |
| `carts` | Normal carts workspace |
| `cart_detail` | Cart conversation panel |
| `daily_brief` | Daily Brief |
| `weekly_brief` | Weekly Brief (future) |
| `notifications` | Push/in-app notifications |
| `knowledge_layer` | Knowledge Layer |
| `executive_view` | Executive summary |
| `future_ai` | AI companion |

---

## API wiring

### Per-cart (normal-carts row builder)

After explanation, decisions, and cart detail projection:

```python
attach_merchant_intelligence_v1(out)
```

Adds to each row:

- `merchant_intelligence_v1` — cart bundle (`group_assignment`, `recommendation`, `observability`)
- `intelligence_group_key` — top-level group id for surface filters

### Store-level (normal-carts API response)

After page rows extracted:

```python
attach_store_merchant_intelligence_v1(body, merchant_carts_page_rows)
```

Adds to API body:

- `merchant_intelligence_store_v1` — store bundle (`groups`, `recommendations`, `memory`, `priorities`)

---

## Observability

Every output includes reviewability metadata:

| Field | Meaning |
|-------|---------|
| `authority` | Always `merchant_intelligence_v1` |
| `creation_reason` | Why this object exists |
| `evidence_ids` / `supporting_evidence` | Evidence source |
| `confidence` | Governed confidence level |
| `observability.reviewable` | Always `true` |

Counters: `get_merchant_intelligence_observability_v1()` — groups assigned, recommendations projected, memory beats, priorities built, carts processed.

---

## Examples

### Cart: needs merchant (intervention decision)

**Inputs:**

- `customer_lifecycle_merchant_needed_ar`: `"نعم"`
- `merchant_decision_key`: `contact_customer`
- `merchant_cart_primary_bucket`: `sent`

**Output:**

```json
{
  "intelligence_group_key": "needs_merchant",
  "merchant_intelligence_v1": {
    "group_assignment": {
      "group_id": "needs_merchant",
      "title_ar": "يحتاج تدخلك",
      "reason": "decision:decision_contact_customer",
      "confidence": "insufficient",
      "eligible_surfaces": ["merchant_home", "carts", "cart_detail", "daily_brief", "notifications"]
    },
    "recommendation": {
      "recommendation_type": "suggested_action",
      "merchant_message_ar": "تحتاج تدخل",
      "decision_id": "decision_contact_customer"
    }
  }
}
```

### Store: pattern + operational groups

Three carts with `reason_tag: price`, two with merchant-needed:

- Operational group: `needs_merchant` (2 carts)
- Pattern group: `repeated_hesitation` (3 carts, reason=price)
- Memory beat: `repeated_pattern` for shipping/price tags

---

## Certification

**Test module:** `tests/test_merchant_intelligence_v1.py`

| Test area | Coverage |
|-----------|----------|
| Group assignment | needs_merchant, vip, completed, returned, no_contact, waiting_reply |
| Recommendation derivation | suggested, blocked, no_action, class mapping |
| Store aggregation | Operational + pattern groups |
| Memory | Comparison context required; in-batch repeated pattern |
| Priority ordering | From recommendations + completed |
| Surface eligibility | Per-group default surfaces |
| Forbidden ownership | No flask/jinja/dashboard imports in service |
| Regression | Deterministic same-input output |
| Contract validation | `validate_merchant_intelligence_contract_v1` |

Run:

```bash
python -m unittest tests.test_merchant_intelligence_v1 -v
```

---

## Forbidden locations (MIA-8)

The following must **never** assign groups, derive recommendations, or invent merchant guidance:

- `static/merchant_dashboard_lazy.js` (presentation only)
- `static/merchant_home_experience.js`
- Jinja templates
- CSS files
- Page-specific Python routes (except attach calls)

Surfaces consume `intelligence_group_key`, `merchant_intelligence_v1`, and `merchant_intelligence_store_v1` — they do not think.

---

## Evolution

| Next step | Owner |
|-----------|-------|
| Home consumes `merchant_intelligence_store_v1` | Experience layer |
| Carts UI groups by `intelligence_group_key` | Experience layer |
| Weekly Brief memory beats | Future cadence surface |
| Snapshot allowlist for MI fields | Read model |
| Historical `comparison_context` from archive | Ops / snapshot |

This service satisfies the constitutional blocker: **`merchant_intelligence_v1` service design** — enabling Merchant Intelligence Grouping V1 in surfaces.
