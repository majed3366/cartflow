# Store Reality Simulator V1 — Event Compatibility Matrix (Phase 1)

**Status:** Phase 1 design — **STOP for review**  
**Date (UTC):** 2026-07-15  
**Companions:** `store_reality_simulator_v1_architecture.md`, `store_reality_simulator_v1_scenario_registry.md`

## How to read this matrix

| Column | Meaning |
|--------|---------|
| **Spec event** | Name from the Reality Simulator brief |
| **Platform status** | `Supported` · `Partial` · `Internal-only` · `Unsupported` · `Derived` |
| **Canonical platform name** | Existing vocabulary (do **not** invent parallel names) |
| **Ingress** | How a real store produces it today |
| **Simulator strategy** | How Phase 2+ should exercise it |
| **Bypass risk** | What direct DB insert would skip |

**Rules**

1. Use existing canonical names when they exist.  
2. Do not fabricate durable rows for Unsupported events.  
3. Unsupported events appear in DRY RUN / run reports as `unsupported` with reason.  
4. Derived outputs (Knowledge, Decisions, snapshots) are **never** ingested as source events.

---

## A. Storefront behavior

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `session_started` | Unsupported | — | None durable | Report unsupported; optional in-memory plan marker only | N/A |
| `page_viewed` | Unsupported | — | None | Report unsupported | N/A |
| `product_viewed` | Unsupported | Lab step name only | None durable | Do not persist; use cart line / product id on sync as proxy where needed | Fake analytics |
| `category_viewed` | Unsupported | — | None | Report unsupported | N/A |
| `scroll_depth_reached` | Unsupported | — | None | Report unsupported | N/A |
| `dwell_time_recorded` | Unsupported | Client hesitation timer only | None durable | Report unsupported | Fake engagement |
| `product_revisited` | Unsupported | — | None | Multi-session cart sync as proxy; mark proxy in report | Fake revisit metric |
| `checkout_started` | Partial | `NormalizedPlatformEvent.checkout_started` / cart progress | Platform webhook partial; not widget primary | Prefer cart_state_sync near checkout if available; else unsupported/partial | Skip abandon arming |
| `checkout_step_viewed` | Unsupported | — | None | Report unsupported | N/A |
| `session_ended` | Unsupported | — | None | Report unsupported | N/A |
| `customer_returned` | Partial | return / passive return payloads | `POST /api/cart-event` misc return paths | HTTP return / passive return | Skip movement hooks |

---

## B. Cart behavior

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `cart_created` | Partial | `AbandonedCart` create via sync/abandon | `/api/cart-event` | HTTP cart_state_sync / abandon | Skip schedules/identity |
| `item_added` | Partial | `cart_state_sync` + reason `add` | `/api/cart-event` | HTTP sync with line items | Skip line snapshots |
| `item_removed` | Partial | cart_state_sync quantity/lines | `/api/cart-event` | HTTP sync | Same |
| `item_quantity_changed` | Partial | cart_state_sync | `/api/cart-event` | HTTP sync | Same |
| `cart_value_changed` | Partial | cart total on AbandonedCart | sync/abandon | HTTP | VIP threshold mis-eval if skipped |
| `cart_abandoned` | Supported | `event=cart_abandoned` | `/api/cart-event` → `handle_cart_abandoned` | HTTP | Skip recovery arming |
| `cart_reopened` | Partial | merchant archive reopen API | `POST /api/dashboard/cart-lifecycle/reopen` | Only when testing merchant archive UX | Wrong merchant semantics |
| `cart_archived` | Partial | merchant archive | `POST /api/dashboard/cart-lifecycle/archive` | Optional merchant-action scenarios | Same |
| `cart_completed` | Derived / via purchase | lifecycle closure + purchase truth | conversion → closure | Purchase Truth path | Orphan completed flags |

---

## C. Widget behavior

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `widget_eligible` | Unsupported | client/session heuristics | None durable | Report unsupported | Fake eligibility |
| `widget_shown` | Partial | widget health / client | Not durable event API | Do not invent DB event; optional log-only plan marker | Fake widget truth |
| `widget_opened` | Unsupported | — | None | Model as “no reason yet”; report unsupported | Invented opens |
| `widget_ignored` | Unsupported | — | None | Absence of reason POST | Invented ignore rows |
| `widget_closed` | Unsupported | — | None | Report unsupported | N/A |
| `hesitation_reason_selected` | Supported | reason capture | `POST /api/cartflow/reason` (+ Layer D API) | HTTP with platform tags | Skip schedule arming / templates |
| `phone_submitted` | Supported | phone on reason / `vip_phone_capture` | `/api/cartflow/reason` | HTTP | VIP/no-phone facet wrong |
| `human_support_requested` | Supported | assist handoff | `POST /api/cartflow/assist-handoff` | HTTP | Skip support URL path |
| `widget_suppressed` | Partial | suppression gates in widget/runtime | Mostly client/server gates | Exercise via repeated exposure rules where code exists; else unsupported | Fake suppression |

---

## D. WhatsApp behavior

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `whatsapp_eligible` | Partial | store flags + rejection gates | Internal gates | Assert via eligibility checks; no fake eligible event | Skip gates |
| `whatsapp_scheduled` | Internal-only | `RecoverySchedule` + timeline `scheduled` | reason/abandon materialization | Real materialization under sim-safe policy | Skip due scanner |
| `whatsapp_sent` | Internal-only | `CartRecoveryLog` `mock_sent`/`sent_real` + timeline `provider_sent` | due scanner / send path | **mock_sent only**; never `sent_real` to providers | Fake delivery truth |
| `whatsapp_delivered` | Partial | `WhatsAppDeliveryTruth` / timeline `webhook_delivered` | Meta/Twilio webhooks | Optional simulated webhook **only** if isolated; else mark unsupported/partial | Fake delivery |
| `whatsapp_failed` | Internal-only | log/status `whatsapp_failed` | provider failure paths | Call failure logging paths / inject via sim-safe adapter | Mislabel as hesitation |
| `whatsapp_ignored` | Unsupported as named event | inferred by no reply + no return | — | Infer in report; do not invent event row | Fake ignore |
| `whatsapp_replied` | Internal-only | timeline `customer_reply` | inbound webhooks | Sim-safe reply injector (internal) for S15/S06 variants | Skip movement/attention |
| `merchant_followup_required` | Partial | VIP / attention composition | derived | Do not inject; observe surfaces | Fake attention |
| `whatsapp_suppressed` | Partial | skip statuses / ops pause / user_rejected | send gates | Exercise gates; record `provider_suppressed_simulation` | Silent skip |

---

## E. Movement

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `passive_return` | Supported/Partial | `EVENT_PASSIVE_RETURN` / passive return payload | `/api/cart-event` + `apply_movement_event` | HTTP + movement | Count drift |
| `continuation_started` | Internal-only | timeline / movement `continuation_started` | recovery continuation writers | Via real continuation path | Skip snapshot |
| `returned_to_site` | Supported/Partial | movement `returned_to_site` + return cart-event | return paths | HTTP return | Skip snapshot |
| `repeated_revisit` | Partial | `passive_return_visit_count` increments | passive return path | Multi return events | Inflated counts if direct SQL |
| `purchase_detected` | Internal-only | movement `purchase_detected` | purchase truth hooks | Via Purchase Truth | Orphan movement |

**Field name alignment (spec → platform):**

| Spec | Platform |
|------|----------|
| `passive_revisit_count` | `passive_return_visit_count` |
| `returned_to_site_at` | `returned_at` |

---

## F. Purchase

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `purchase_created` | Supported | conversion / purchase evidence names | `POST /api/conversion` | Prefer HTTP; use `ingest_purchase_truth(..., purchase_time=)` for history | Skip cancel/closure |
| `purchase_truth_persisted` | Derived | `PurchaseTruthRecord` | ingest | Assert after ingest | Direct insert skips lifecycle |
| `purchase_mapped_to_cart` | Partial | product purchase mapping + recovery_key map | post-truth services | Via truth path | Orphan mapping |
| `schedules_cancelled` | Derived | `cancel_durable_schedules_for_purchase` | purchase lifecycle | Via truth | Leftover dues |
| `recovery_classified` | Derived | `purchase_attribution_v1` levels | `run_purchase_attribution_after_truth_closure` | Via truth | Fake ROI |
| `purchase_unattributed` | Derived | `not_attributed` / `organic_or_unknown` | attribution | Via truth | Mislabel recovery |

---

## G. Operational / Knowledge

| Spec event | Status | Canonical / closest | Ingress | Simulator strategy | Bypass risk |
|------------|--------|---------------------|---------|--------------------|-------------|
| `provider_failure` | Internal-only | `log_provider_failure` / failed send | provider paths | Sim-safe failure adapter | Silent loss |
| `retry_scheduled` | Partial | retry / reschedule paths | internal | Only where implemented | Fake retries |
| `retry_exhausted` | Partial | exhausted statuses | internal | Only where implemented | Same |
| `data_insufficient` | Derived | KL `confidence=insufficient` / insufficient insights | `knowledge_insights_v1` | Generate tiny sample; **read** KL | Injected insight |
| `evidence_threshold_reached` | Derived | sample ≥ `MIN_HESITATION_SAMPLE` etc. | KL | Observe after volume | Fake threshold event |
| `knowledge_candidate_created` | Unsupported | — | None (KL computes insights) | Report unsupported as ingest event | Parallel knowledge pipeline |
| `knowledge_routed` | Derived | `knowledge_routing_v1` | Daily Brief composition | Observe routed brief items | Fake routing |
| `recommendation_suppressed` | Derived | decision suppression reasons | decision layer | Observe | Fake suppression rows |

---

## H. Recovery Truth Timeline (platform chain — use these names)

Do not invent a second timeline vocabulary. Platform statuses:

```text
scheduled → delay_started → before_send → provider_queued → provider_sent
→ webhook_delivered → customer_reply → continuation_started
```

Commerce Signals (derived, not stored):  
`recovery_started` | `recovery_progressed` | `recovery_completed` | `recovery_blocked` | `purchase_confirmed`

---

## I. Paths bypassed by direct inserts (summary)

Direct inserts into operational tables **skip** (non-exhaustive):

1. Schedule materialization / delay arming / due-scanner claim  
2. Timeline monotonic rules + movement snapshot hooks  
3. Purchase → schedule cancel + lifecycle closure + product purchase mapping  
4. Attribution after truth closure  
5. Commerce Signals / Pulse / Knowledge metric windows  
6. Dashboard snapshot freshness (stale until rebuild)  
7. In-process idempotency / session memory  
8. WhatsApp delivery truth / retry ledger  
9. Hesitation → product mapping hooks  
10. Operational control / rejection / anti-spam gates  

**Lab Scenario 1 is the reference anti-bypass pattern.**

---

## J. Unsupported-event list (authoritative Phase 1)

These spec events have **no durable platform ingest** today. Simulator must classify them `unsupported` and must **not** fabricate persistence to “satisfy” the catalog.

### Storefront / behavioral

1. `session_started`  
2. `page_viewed`  
3. `product_viewed` (as durable analytics event)  
4. `category_viewed`  
5. `scroll_depth_reached`  
6. `dwell_time_recorded`  
7. `product_revisited` (as named event)  
8. `checkout_step_viewed`  
9. `session_ended`  

### Widget UI chrome

10. `widget_eligible`  
11. `widget_opened`  
12. `widget_ignored` (as named event)  
13. `widget_closed`  

### Named operational knowledge ingest

14. `knowledge_candidate_created` (Knowledge is computed, not ingested)  
15. `whatsapp_ignored` (as named event — inference only)

### Spec reasons without platform tags (map or report)

Not “events”, but **unsupported reason vocabulary** if used literally:

- `comparing_options` (no tag)  
- `trust_concern` (no tag)  
- `payment_concern` (no tag)  
- `need_more_time` (map → `thinking`)  
- `product_uncertainty` (map → `quality`)

### Missing integration (not unsupported events, but blockers)

- Historical HTTP timestamps for cart-event / reason / timeline  
- Dedicated simulation provider adapter  
- Run-scoped cleanup model  
- Remote Lab/Reality control surface  

---

## K. Supported / Partial event quick index (simulator may exercise)

**HTTP-first:** `cart_abandoned`, cart sync proxies for item/value changes, `hesitation_reason_selected`, `phone_submitted`, `human_support_requested`, return/passive return, `purchase_created` (conversion).

**Internal with sim-safe policy:** schedule / send(mock) / fail / reply / movement purchase_detected / timeline statuses.

**Derived only (observe, never inject):** Purchase Truth persistence, schedule cancel, attribution, KL insights, routing, decision suppression, dashboard/monthly snapshots, attention items.

---

## L. Phase 1 implications for later phases

| If Phase 2 wants… | Then it must… |
|-------------------|---------------|
| Honest 60-day history | Ship Timestamp Authority (§7 architecture) |
| Widget-open scenarios | Accept Partial modeling **or** wait for durable widget interaction ingest (product work — separate) |
| Traffic volume claims | Accept KL visitor-unavailable **or** add real visitor ingest (product work — separate) |
| Knowledge validation | Call `/api/knowledge/report` after data exists; never write insights |
| Dashboard consistency | Call `build_store_dashboard_snapshots` for `demo` after execute |

---

**STOP for review.** No event generation in Phase 1.
