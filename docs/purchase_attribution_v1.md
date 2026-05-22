# Purchase Attribution v1

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add purchase attribution decision layer v1`

Estimates whether a purchase was **likely influenced** by CartFlow after Purchase Truth closes the lifecycle. This is **confidence-based**, not proof of causality.

## Flow

```text
Purchase Truth verified
        ↓
[PURCHASE LIFECYCLE CLOSED]
        ↓
gather evidence → compute AttributionDecision
        ↓
[ATTRIBUTION DECISION] log (+ optional recovery_events row)
```

Attribution **never blocks** lifecycle closure. Failures log a warning only.

## Levels

| Level | Meaning |
|-------|---------|
| `confirmed_recovery` | Recovery WA sent + strong engagement (reply / return / click) + purchase after send (within window) |
| `likely_recovery` | Recovery sent + purchase within attribution window, weak engagement proof |
| `assisted_recovery` | Widget/reason or return/uncertain engagement; influence unclear |
| `organic_or_unknown` | Purchase truth with little or no CartFlow evidence |
| `not_attributed` | Purchase before recovery, outside window, or recovery blocked without send |

## AttributionDecision fields

- `attribution_level`, `confidence` (`high` / `medium` / `low` / `none`)
- `reason` — machine-readable (e.g. `purchase_within_72h_after_recovery`)
- `evidence` — tags collected (`recovery_message_sent`, `customer_replied`, …)
- `window_hours` — default **72**
- `purchase_after_recovery`
- `recommended_label` — short English label for future admin/ROI UI

## Evidence inputs

| Input | Source (best-effort) |
|-------|----------------------|
| `recovery_sent_at` | **Latest** `CartRecoveryLog` for same `store_slug` + `session_id` (+ `cart_id` when set), ordered **desc** — not oldest row; stale sends outside window ignored |
| `purchase_completed_at` | Now UTC, or payload `purchase_completed_at` / `converted_at` |
| `customer_replied` | `cf_behavioral`, session helpers |
| `returned_to_site` | `cf_behavioral` |
| `recovery_click` | `recovery_link_clicked` in behavioral |
| `reason_tag` / `reason_captured` | `CartRecoveryReason`, behavioral |
| `recovery_blocked` | behavioral `future_recovery_allowed=false` without send |

Incomplete platform data is **not guessed**; missing fields reduce confidence toward `organic_or_unknown`.

## Logs

```
[ATTRIBUTION DECISION]
store_slug=demo
session_id=...
cart_id=...
recovery_key=...
attribution_level=likely_recovery
confidence=medium
reason=purchase_within_72h_after_recovery
```

## Storage (v1)

- Primary: stdout + application log
- Optional: `recovery_events.event_type = purchase_attribution_v1` JSON payload (existing table; failures ignored)

No new analytics schema. **Not exposed** on merchant dashboard in v1.

## Intentionally NOT in v1

- Merchant ROI dashboard or revenue claims
- Changing Purchase Truth, lifecycle, WhatsApp, schedules, widget, integrations gateway
- Absolute “caused by CartFlow” language in product UI

## Limitations

- In-process / DB evidence may be incomplete on cold restarts
- Multi-worker: sent/reply markers may differ per process until durable attribution store exists
- 72h window is configurable via `attribution_window_hours` on inputs only (env hook later)

## Future merchant ROI usage

1. Aggregate `purchase_attribution_v1` events per store  
2. Show distributions (confirmed / likely / assisted / organic) with disclaimers  
3. Never surface as guaranteed incremental revenue  

## Verification (staging)

1. Trigger recovery → WA sent (or mock `sent_real` log)  
2. Simulate purchase truth (`POST /api/conversion` or dev test)  
3. Confirm log order: `[PURCHASE TRUTH]` → `[PURCHASE LIFECYCLE CLOSED]` → `[ATTRIBUTION DECISION]`  
4. Expect `likely_recovery` or `confirmed_recovery` depending on reply/return evidence  

```bash
python -m pytest tests/test_purchase_attribution_v1.py -q
```
