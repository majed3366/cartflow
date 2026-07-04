# Merchant Daily Brief Composer V2

**Status:** Implemented  
**Date:** 2026-07-04  
**Layer:** Presentation only — between Merchant Decision Layer and Merchant Daily Brief UI

## Position in the stack

```
Truth → Evidence → Proof → Merchant Decision Layer → Merchant Daily Brief Composer (v2) → Merchant Daily Brief → Home UI
```

The Composer **never** creates decisions, changes truth, or changes confidence. It only **groups**, **summarizes**, and **presents** published decisions as merchant-readable briefing topics.

## Problem solved

V1 projected one brief item per decision. When many carts shared the same decision family (e.g. five `decision_obtain_contact`), the merchant saw repeated lines:

> Waiting for customer number  
> Waiting for customer number  
> …

The merchant reads **topics**. The platform stores **decisions**.

## Responsibilities

| Responsibility | Composer v2 |
|----------------|-------------|
| Group related decisions | Yes — deterministic aggregation keys |
| Achievements first | Yes — observation / monitor / KL topics |
| Attention second | Yes — max 5 topic items |
| Traceability | Every topic lists `source_decision_ids`, `decision_count`, `aggregation_reason` |
| Mint decisions | **No** |
| Change confidence | **No** |
| LLM / generated advice | **No** |

## Module

- **`services/merchant_daily_brief_composer_v2.py`**
  - `compose_merchant_daily_brief_v2()` — main entry
  - `group_decisions_into_topics()` — partition + aggregate
  - `aggregation_key_for_decision()` — governed grouping key
  - `is_achievement_decision()` — achievement vs attention partition
  - `validate_merchant_daily_brief_v2()` — contract checks

Wired from `build_merchant_daily_brief_api_payload()` in `services/merchant_daily_brief_v1.py` (v1 compose helpers remain for tests and projection).

## Payload shape (v2)

```json
{
  "version": "v2",
  "composer_version": "v2",
  "brief_date": "2026-07-04",
  "achievements": [ /* topic items, section=achievement */ ],
  "attention_items": [ /* topic items, section=attention, max 5 */ ],
  "items": [ /* same as attention_items — backward compat */ ],
  "achievement_count": 1,
  "attention_count": 2,
  "empty": false,
  "observability": {
    "decisions_collected": 7,
    "decisions_composed": 7,
    "achievement_topics": 1,
    "attention_topics": 2
  }
}
```

### Topic item fields (extends v1 projection)

| Field | Purpose |
|-------|---------|
| `headline_ar` | Aggregated merchant-readable topic title |
| `decision_count` | Number of source decisions in this topic |
| `source_decision_ids` | Trace keys (`merge_key` when present, else `decision_id`) |
| `aggregation_key` | Internal grouping key |
| `aggregation_reason` | `decision_id_family+action_key+commercial_goal+evidence_id` |
| `representative_decision_id` | Family id used for labels/confidence display |
| `section` | `achievement` or `attention` |

Confidence and class on a topic come from the **representative** decision (highest priority in the group). Source decisions are not modified.

## Aggregation rules

Partition first:

- **Achievements:** `decision_class == observation`, `merchant_action == monitor`, or KL observation family
- **Attention:** all other eligible published decisions

Group within each partition by:

```
decision_id_family : action_key : commercial_goal : evidence_id
```

KL observations additionally include `insight_key` from proof sources.

**Never** aggregate unrelated families/goals/actions.

## Aggregation Governance

Composer V2 aggregation is **governed**, not an informal algorithm. These contracts apply to every compose run and every aggregated topic.

| ID | Contract |
|----|----------|
| **AG-1** | Composer **never creates new merchant actions**. Actions on a topic are projected from an existing published decision (representative only; plural topics omit per-cart action lines). |
| **AG-2** | Aggregation **never increases confidence**. Topic confidence is taken from the representative decision as-is; no uplift, blending, or recomputation. |
| **AG-3** | Aggregation **never changes `commercial_goal`**. Topic goal matches the grouped decisions; grouping key requires goal equivalence. |
| **AG-4** | Aggregation **preserves traceability to all source decisions** in each topic via `source_decision_ids` (instance keys: `merge_key` when present, else `decision_id`). |
| **AG-5** | Aggregation **may reduce duplication only** — fewer briefing rows, same underlying decisions. |
| **AG-6** | Aggregation **groups only semantically equivalent decisions** — same `decision_id` family, `action_key`, `commercial_goal`, and primary `evidence_id` (plus KL `insight_key` when applicable). |
| **AG-7** | Composer **never reads Truth directly**. Input is published `merchant_decisions_v1` bundles only (via `collect_published_decisions_from_bundles_v1`). |
| **AG-8** | Composer is **presentation preparation**, not business logic — no decision minting, suppression, verification, or lifecycle changes. |
| **AG-9** | Every aggregated topic **must declare** `source_decision_ids`, `decision_count`, and `aggregation_reason`. Enforced by `validate_merchant_daily_brief_v2()`. |
| **AG-10** | If decisions are **not semantically equivalent**, they **must remain separate briefing items** (distinct `aggregation_key`). |

### Implementation compliance (AG-1…AG-10)

| Contract | Implementation evidence |
|----------|-------------------------|
| AG-1 | `_brief_action_ar(rep)` only; no new `action_key` values minted |
| AG-2 | `confidence` copied from representative; source decisions untouched |
| AG-3 | `commercial_goal` from representative; key includes goal |
| AG-4 | `_decision_trace_id()` → `source_decision_ids`; count validated |
| AG-5 | Grouping merges duplicate-family rows into one topic |
| AG-6 | `aggregation_key_for_decision()` governed key |
| AG-7 | No Truth/Evidence/Proof imports or reads in composer module |
| AG-8 | Compose/group/project only; Decision Layer unchanged |
| AG-9 | `_build_topic_item()` + `validate_merchant_daily_brief_v2()` |
| AG-10 | Different keys → separate topics; test `test_unrelated_decisions_do_not_aggregate` |

Daily Brief UI (`static/merchant_daily_brief.js`) consumes Composer output only (`achievements`, `attention_items` / `items`) — it does not aggregate or read decisions.

### Plural headline templates (deterministic Arabic)

| Family | Template (count > 1) |
|--------|----------------------|
| `decision_obtain_contact` | `{n} عملاء لا يمكن التواصل معهم — أرقام التواصل غير متوفرة` |
| `decision_contact_customer` | `{n} سلات تحتاج تواصلك مع العملاء` |
| `decision_fix_channel` | `{n} سلات — فشل إرسال رسالة الاسترجاع` |
| `decision_monitor_return` | `CartFlow يراقب {n} عودة للموقع` |
| `decision_kl_observation` | `CartFlow رصد {n} ملاحظات في نشاط متجرك` |
| Other | `{n} حالات — {singular headline}` |

## UI (Home)

`static/merchant_daily_brief.js` renders:

1. Greeting + attention count
2. **Achievements** — “بينما كنت بعيداً…” with ✓ rows
3. **Attention** — “اليوم يحتاج انتباهك” → hero + queue (unchanged IA)

Styles: `static/merchant_app.css` (`.ma-brief-achievements*`).

## What we did not change

- Merchant Decision Layer
- Decision Registry
- Truth / Evidence / Proof
- Governance contracts
- Decision minting or verification

## Tests

- `tests/test_merchant_daily_brief_composer_v2.py` — aggregation, achievements-first, traceability, cap, no duplicates
- `tests/test_merchant_daily_brief_v1.py` — still uses v1 compose directly (unchanged)

## Verification checklist

- [x] No duplicated attention topics (unique `aggregation_key`)
- [x] Achievements before attention in payload and UI
- [x] Every topic maps to source decision trace IDs
- [x] No decision loss (`decisions_composed == decisions_collected`)
- [x] No truth/confidence mutation on source decisions
- [x] Attention cap remains 5 topics

## Related docs

- `docs/merchant_daily_brief_foundation_v1.md`
- `docs/merchant_daily_brief_implementation_v1.md`
- `docs/merchant_daily_brief_ux_redesign_v1.md`
- `docs/merchant_daily_brief_ia_redesign_v1.md`
