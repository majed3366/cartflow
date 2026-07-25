# Business Theme Contract V1

**Layer:** Business Theme Engine (between Business Facts and Executive Editorial)  
**Constitution:** One Business Theme. One Owner. Many Consumers.  
**No Product Intelligence. Gates 3–7 LOCKED.**

---

## What a Theme is

A Business Theme is one business issue, opportunity, or trend.

| A Theme is | A Theme is not |
|------------|----------------|
| Canonical commercial truth | A counter |
| One story from many facts | A recommendation |
| Owned by one primary surface | A UI card |
| Consumed identically everywhere | A page-local reinterpretation |

---

## Required fields

| Field | Purpose |
|-------|---------|
| `theme_id` | Stable id |
| `theme_type` | Bucket (see types) |
| `title_ar` / `title_en` | Theme name |
| `executive_summary_ar` | One commercial sentence |
| `supporting_fact_ids` | Facts collapsed into this theme |
| `evidence` | Fact count + capability ids |
| `confidence` | Level + score |
| `business_impact` | Why it matters commercially |
| `freshness` | As-of |
| `priority` | Rank for Home / Workspace |
| `primary_owner` | Sole meaning owner |
| `destination_surfaces` | home_teaser / decision_workspace / communication |

`recommendation` is always `null`.

---

## Theme types (V1)

- `recovery_opportunity`
- `shipping_friction`
- `product_demand`
- `product_conversion`
- `customer_return_behaviour`
- `communication_coverage`
- `store_health`
- `pricing_opportunity` (stub)
- `inventory_risk` (stub)

---

## Ownership

| Theme | Primary owner | Other surfaces |
|-------|---------------|----------------|
| Recovery / Shipping / Conversion / Demand / Return | Decision Workspace | Home = executive teaser only |
| Communication coverage | Communication | Home teaser only |
| Store health | Home | — |

Carts never explain recovery themes.

---

## Admission

Publish only when:

1. Evidence threshold passed (supporting facts)
2. Confidence threshold passed
3. Business impact exists
4. Merchant action exists (Workspace-owned) — or soft Home/Communication teaser

Otherwise the theme stays `internal_only`.

---

## Pipeline

```text
Operational Truth
        ↓
Observation Foundation
        ↓
Business Facts
        ↓
Business Theme Engine   ← this contract
        ↓
Executive Editorial
        ↓
Merchant Understanding (Gate 2X)
        ↓
Decision Workspace / Home / Communication
```

Executive Editorial and Decision Workspace **never** read Business Facts directly when Themes are enabled.
