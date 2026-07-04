# CartFlow Merchant Daily Brief Implementation V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — first governed consumer of Merchant Decisions  
**Foundation:** [`merchant_daily_brief_foundation_v1.md`](merchant_daily_brief_foundation_v1.md)  
**Governance:** PV-18, MD-A-2, DG-1, DG-6

---

## Purpose

The **Merchant Daily Brief** is the first visible consumer of the Merchant Decision Layer. It answers:

> If I have only one minute this morning, what are the most important things I should know and act on?

It **consumes** `merchant_decisions_v1` only. It never mints decisions, evaluates truth, or generates recommendations.

---

## Architecture

```
Truth → Evidence → Proof → Merchant Decision Layer → Merchant Daily Brief → Home UI
```

| Layer | Role |
|-------|------|
| Decision Layer | Mints published `merchant_decisions_v1` |
| Daily Brief composer | Selects + projects published decisions (read-only) |
| Home UI | Renders brief payload — presentation only |

---

## Modules

| File | Role |
|------|------|
| `services/merchant_daily_brief_v1.py` | Composer + brief item projection + API builder |
| `routes/daily_brief.py` | `GET /api/dashboard/daily-brief` |
| `static/merchant_daily_brief.js` | Home `#ma-daily-brief-root` renderer |
| `templates/merchant_app.html` | Daily brief section on home overview |
| `static/merchant_app.css` | Mobile-first brief styles |
| `tests/test_merchant_daily_brief_v1.py` | PV-18 compliance tests |

---

## Input sources (decisions only)

The API aggregates existing `merchant_decisions_v1` bundles from:

1. **Knowledge Layer** — `/api/knowledge/report` enrichment path (KL observation decisions)
2. **Normal carts rows** — `build_normal_carts_dashboard_api_payload` row bundles

No direct Truth / Proof / KL insight reads in the composer.

---

## Selection rules

1. Filter: `lifecycle_state == published`, `verification_status == passed`, `suppression_state == none`
2. Sort: by governance `priority` (desc)
3. Dedupe: by `merge_key`
4. Cap: **≤5 items** (PV-18)
5. Empty: calm merchant-facing empty state — no manufactured content

---

## Brief item contract

Each item is a **projection** of one published decision:

| Field | Source |
|-------|--------|
| `what_ar` | `decision_explanation.rationale_ar` |
| `why_ar` | `decision_explanation.why_now_ar` |
| `action_ar` | `merchant_action` + `action_key` when class is suggested/critical |
| `confidence_label_ar` | Pass-through confidence |
| `evidence_source_ar` | First `evidence_ids` → Evidence Registry label |
| `commercial_goal_label_ar` | Pass-through commercial goal |
| `decision_class_label_ar` | Pass-through class |

Validated by `validate_merchant_daily_brief_v1()`.

---

## API

**`GET /api/dashboard/daily-brief`**

Authenticated merchant only. Returns:

```json
{
  "ok": true,
  "version": "v1",
  "brief_date": "2026-07-04",
  "item_count": 2,
  "max_items": 5,
  "empty": false,
  "empty_state_ar": { "title_ar": "...", "message_ar": "..." },
  "items": [ /* brief item projections */ ],
  "observability": { "decisions_collected": 3, "decisions_selected": 2 }
}
```

---

## UI

Home overview (`#home`) — **ملخص يومك** section above Knowledge Layer.

- Mobile-first card list
- What / why / action (when decision declares executable action)
- Confidence + evidence source per item
- No charts, KPI walls, or AI summaries

---

## Restrictions honored

- No changes to Purchase / Lifecycle / Provider Truth
- No changes to Evidence Registry, Proof Surface, or Decision Layer logic
- No recovery execution or scheduler changes
- No snapshot generation behavior changes

---

## Tests

```bash
python -m pytest tests/test_merchant_daily_brief_v1.py -q
```

Covers: eligibility filter, max-5 cap, priority sort, merge_key dedupe, empty state, brief item contract, no action for needs_attention execute.

---

*End of Merchant Daily Brief Implementation V1.*
