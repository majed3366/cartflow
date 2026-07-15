# Store Reality Simulator V1 — Scenario Registry (Phase 1)

**Status:** Phase 1 design — **STOP for review**  
**Date (UTC):** 2026-07-15  
**Companion:** `store_reality_simulator_v1_architecture.md`, `store_reality_simulator_v1_event_compatibility_matrix.md`

Each scenario defines **source behavior** and **expected platform interpretation**.  
Scenarios must **not** inject Knowledge, recommendations, confidence, or dashboard totals.

**Platform readiness legend (per scenario):**  
`Ready` = can exercise with existing ingress + derived layers  
`Partial` = can exercise core path; some expected outcomes lack platform support  
`Blocked` = requires missing integration (usually Time Machine or unsupported events) before honest validation  
`Observe-only` = generate what exists; report gaps without fabricating outputs

---

## Shared contracts

### Hesitation reason mapping (spec → platform)

| Spec reason | Platform `reason_tag` | Notes |
|-------------|----------------------|-------|
| Shipping cost | `shipping` | Supported |
| Price concern | `price` (+ sub e.g. `price_discount_request`) | Supported |
| Need more time | `thinking` | Closest governed tag |
| Comparing options | `thinking` or `other` | **No dedicated tag** — document as mapped |
| Trust concern | `quality` or `other` | **No dedicated tag** |
| Payment concern | `other` | **No dedicated tag** |
| Product uncertainty | `quality` | Closest |
| Human support request | assist-handoff path | `POST /api/cartflow/assist-handoff` — not a reason_tag |

### Attribution levels (platform — use these in expectations)

| Spec phrase | Platform level |
|-------------|----------------|
| Confirmed recovery | `confirmed_recovery` |
| Possible / uncertain influence | `assisted_recovery` (or `likely_recovery` when medium) |
| Organic / no CartFlow influence | `organic_or_unknown` / `not_attributed` |

### Defect signal (all scenarios)

A defect is indicated when reconciliation mismatches, false recovery claims, invented reasons, infinite schedules, non-demo contamination, real outbound send, or Knowledge overgeneralization appear.

---

## S01 — Normal Store Baseline

| Field | Content |
|-------|---------|
| **Name** | `S01_normal_store_baseline` |
| **Business purpose** | Believable everyday store activity |
| **Readiness** | Partial (needs Time Machine for multi-day honesty) |
| **Expected customer behavior** | Browse → some ATC → mix of abandon / purchase / return; mobile+desktop; mild weekly variation |
| **Expected source events** | cart sync/abandon, mixed reasons (sparse), some conversions, some returns |
| **Expected CartFlow interpretation** | Calm dashboard; no exaggerated warnings; KL cautious; confidence rises only with sample |
| **Expected merchant-facing outcome** | Usable Home / Carts / Monthly after snapshot rebuild |
| **Defect if** | Constant urgent attention with thin evidence; traffic advice without visitor data; broken empty states |

---

## S02 — High Traffic, Low Conversion

| Field | Content |
|-------|---------|
| **Name** | `S02_high_traffic_low_conversion` |
| **Business purpose** | Distinguish volume from conversion |
| **Readiness** | Partial — **visitor traffic metrics often unavailable** in KL (`visitor_data_available=false`) |
| **Expected customer behavior** | Many sessions/carts, many views/ATC (as supported), few purchases |
| **Expected source events** | High abandon volume; low conversion |
| **Expected interpretation** | Problem ≠ lack of traffic; weak conversion / hesitation |
| **Required validation** | Must **not** recommend “increase traffic”; KL must stay evidence-based |
| **Defect if** | Marketing-style traffic advice; forbidden phrases from `FORBIDDEN_ADVICE_PHRASES` |
| **Honest gap** | Without real visitor ingest, KL may emit `traffic_visitor_unavailable` — that is **correct**, not a simulator failure |

---

## S03 — Shipping Cost Hesitation

| Field | Content |
|-------|---------|
| **Name** | `S03_shipping_cost_hesitation` |
| **Business purpose** | Concentrated shipping hesitation evidence |
| **Readiness** | Ready (core) / Partial (product-scoped generalization rules) |
| **Expected behavior** | ATC → reason `shipping` → exit; some returns; minority purchase after reassurance |
| **Expected events** | `hesitation_reason_selected`→`shipping`, abandon, return, some purchase |
| **Expected interpretation** | Shipping cost pattern in product/category context when sample ≥ `MIN_HESITATION_SAMPLE` (3) |
| **Required validation** | Evidence IDs; no premature high confidence; no store-wide claim from one product without evidence |
| **Defect if** | Recommendation before sample threshold; invented non-shipping dominant reason |

---

## S04 — Product Added Often, Purchased Rarely

| Field | Content |
|-------|---------|
| **Name** | `S04_product_high_atc_low_purchase` |
| **Business purpose** | Product-level conversion friction |
| **Readiness** | Partial — product metrics depend on Product Foundation capture path |
| **Expected behavior** | One product: high view/ATC proxies, low purchase, mixed reasons, multi-customer |
| **Expected interpretation** | Product creates carts but converts poorly |
| **Required validation** | Stable product identity (`demo_{key}`); product insight ≠ store-wide truth; purchases close correctly |
| **Defect if** | Product id drift; store-wide overclaim; purchase not mapped |

---

## S05 — WhatsApp Return Without Purchase

| Field | Content |
|-------|---------|
| **Name** | `S05_wa_return_without_purchase` |
| **Business purpose** | Engagement ≠ purchase |
| **Readiness** | Ready (with sim-safe send) |
| **Expected behavior** | Abandon → WA scheduled/sent(mock) → return → browse/checkout → no purchase |
| **Expected interpretation** | Return/movement visible; **not** purchase; no ROI |
| **Required validation** | Purchase Truth empty; attribution not confirmed; movement may show return |
| **Defect if** | Classified as recovered; ROI inflated |

---

## S06 — WhatsApp Success

| Field | Content |
|-------|---------|
| **Name** | `S06_wa_success` |
| **Business purpose** | Governed recovery success path |
| **Readiness** | Ready (with sim-safe send + purchase ingest) |
| **Expected behavior** | Abandon → WA → return → purchase within attribution window; vary confidence situations |
| **Expected interpretation** | Purchase Truth closes cart; schedules cancelled; movement purchase; coherent timeline; attribution per evidence |
| **Required validation** | No duplicate recovery count; schedules cancelled; wording matches level |
| **Defect if** | Post-purchase WA; double count; confirmed claim without evidence |

---

## S07 — Discount Message Failure

| Field | Content |
|-------|---------|
| **Name** | `S07_discount_message_failure` |
| **Business purpose** | Discount-oriented recovery underperforms |
| **Readiness** | Partial — message content is template-driven; “discount-oriented” = price templates + reason `price` |
| **Expected behavior** | Price/discount templates; ignore / return without purchase / abandon; minority purchase; reasons often **not** price on later visits |
| **Expected interpretation** | Do not recommend more discounts merely because abandonment exists |
| **Defect if** | Auto “add more discounts” advice; ignore non-price reasons |

---

## S08 — Repeated Product Interest

| Field | Content |
|-------|---------|
| **Name** | `S08_repeated_product_interest` |
| **Business purpose** | Sustained interest with friction |
| **Readiness** | Partial — dwell/scroll events unsupported; use multi-session ATC/remove/return as proxy |
| **Expected behavior** | Multi-session returns; add/remove cycles; delayed purchase vs permanent abandon |
| **Expected interpretation** | Interest + friction; uncertainty where evidence thin |
| **Required validation** | Identity continuity; movement updates; no invented dwell metrics |
| **Defect if** | Identity loss; duplicate timeline noise; fake scroll/dwell rows |

---

## S09 — Widget Opened and Ignored

| Field | Content |
|-------|---------|
| **Name** | `S09_widget_opened_ignored` |
| **Business purpose** | Widget non-participation still leaves storefront truth |
| **Readiness** | Partial — `widget_opened` / `widget_ignored` **not durable ingest**; model as no reason POST + abandon + some organic purchase |
| **Expected interpretation** | No invented hesitation reason; purchase can close without widget |
| **Defect if** | Fabricated reason_tag; broken purchase without widget |

---

## S10 — Widget Reason Capture

| Field | Content |
|-------|---------|
| **Name** | `S10_widget_reason_capture` |
| **Business purpose** | Realistic reason distributions |
| **Readiness** | Ready for platform tags; Partial for spec-only reasons (mapped) |
| **Expected behavior** | Uneven mix of governed tags + assist-handoff minority |
| **Required validation** | `reason_tag` persistence; human support path; reason→message templates; KL aggregates only with sufficient evidence |
| **Defect if** | Tag loss; support path skipped; KL overclaims on tiny samples |

---

## S11 — Customer Ignores All Recovery

| Field | Content |
|-------|---------|
| **Name** | `S11_ignore_all_recovery` |
| **Business purpose** | Terminal / resting lifecycle without false engagement |
| **Readiness** | Ready |
| **Expected behavior** | No reason / ignore WA / no return / no purchase; suppression where applicable |
| **Required validation** | No infinite schedule; no false engagement/recovery; governed resting/terminal state |
| **Defect if** | Endless due rows; fake replies; false recovery |

---

## S12 — Customer Returns Multiple Times

| Field | Content |
|-------|---------|
| **Name** | `S12_multi_return_customer` |
| **Business purpose** | Identity + movement correctness across days/sessions |
| **Readiness** | Partial (Time Machine + movement field naming) |
| **Expected behavior** | Same-day, next-day, multi-day returns; with/without original cart; purchase and non-purchase branches |
| **Required validation** | `recovery_key` rules; `passive_return_visit_count` / `returned_at` (platform names); `movement_active`; ordered non-duplicated timeline |
| **Note** | Spec names `passive_revisit_count` / `returned_to_site_at` → platform: `passive_return_visit_count` / `returned_at` |
| **Defect if** | Count inflation; identity splits; unordered timeline |

---

## S13 — Purchase Without CartFlow Influence

| Field | Content |
|-------|---------|
| **Name** | `S13_organic_purchase` |
| **Business purpose** | Organic purchase integrity |
| **Readiness** | Ready |
| **Expected behavior** | Visit/cart → purchase; no widget reason; no WA |
| **Required validation** | Purchase Truth recorded; **not** recovered-by-CartFlow; ROI not inflated |
| **Expected attribution** | `organic_or_unknown` / `not_attributed` |
| **Defect if** | Confirmed/likely recovery label |

---

## S14 — Purchase After Possible Influence

| Field | Content |
|-------|---------|
| **Name** | `S14_ambiguous_influence` |
| **Business purpose** | Conservative attribution under ambiguity |
| **Readiness** | Ready (attribution engine) / Partial (Time Machine for long delay) |
| **Expected behavior** | Message sent → long delay → unrelated visits → purchase |
| **Expected classification** | `assisted_recovery` or weaker — **never** overstated confirmed |
| **Required validation** | Conservative wording; evidence visible |
| **Defect if** | `confirmed_recovery` without strong window/evidence |

---

## S15 — VIP Customer

| Field | Content |
|-------|---------|
| **Name** | `S15_vip_customer` |
| **Business purpose** | VIP lane + phone semantics |
| **Readiness** | Ready / Partial (merchant alert must be suppressed in sim) |
| **Expected behavior** | High-value carts; with/without phone; WA avail/unavail; reply/no-reply; purchase/no-purchase |
| **Required validation** | VIP lane correct; hydration not false no-phone; manual contact only when phone valid; no conflicting primary actions |
| **Defect if** | VIP no-phone false state; real merchant alert send; action conflicts |

---

## S16 — Insufficient Data

| Field | Content |
|-------|---------|
| **Name** | `S16_insufficient_data` |
| **Business purpose** | Honest insufficiency |
| **Readiness** | Ready |
| **Expected behavior** | Tiny sample |
| **Expected merchant message** | Data insufficient for recommendation (KL `insufficient` confidence / insufficient insights) |
| **Required validation** | No forced recommendation; dashboard not “broken empty” |
| **Defect if** | High confidence on n≪threshold |

---

## S17 — Conflicting Evidence

| Field | Content |
|-------|---------|
| **Name** | `S17_conflicting_evidence` |
| **Business purpose** | No dominant pattern |
| **Readiness** | Ready |
| **Expected behavior** | Mixed price/shipping; fast buyers + repeat abandoners |
| **Expected outcome** | No single definitive explanation; limited confidence; careful competing evidence |
| **Defect if** | Single overconfident root cause; contradictory recommendations |

---

## S18 — Purchase Closure and Suppression

| Field | Content |
|-------|---------|
| **Name** | `S18_purchase_closure_suppression` |
| **Business purpose** | Stop recovery at every purchase timing |
| **Readiness** | Ready |
| **Expected behavior** | Purchase before/after widget; before/after WA; during active schedule; after returns |
| **Required validation** | Future recovery stops; schedules cancelled; no post-purchase message; movement+cart close; completed state in dashboard after rebuild |
| **Defect if** | Post-purchase send; open schedules remain due |

---

## S19 — Channel Failure

| Field | Content |
|-------|---------|
| **Name** | `S19_channel_failure` |
| **Business purpose** | Provider/config failure ≠ customer hesitation |
| **Readiness** | Partial — failure paths exist (`whatsapp_failed`, provider failure logs); full retry ledger varies |
| **Expected behavior** | WA unavailable / provider error / fail / retry allowed / exhausted / incomplete merchant config |
| **Required validation** | Isolated failure; availability wording correct; not labeled as hesitation; no silent loss |
| **Defect if** | Failure counted as reason_tag; events vanish |

---

## S20 — Data Growth

| Field | Content |
|-------|---------|
| **Name** | `S20_data_growth` |
| **Business purpose** | Bounded historical scale |
| **Readiness** | Blocked on Time Machine + batch infra (Phase 2–4) |
| **Minimum useful target** | 60 days; hundreds–thousands sessions; multi product/customer/cart states; schedules; purchases; movement; KL evidence |
| **Required validation** | Hot paths use snapshots; bounded jobs; no pool exhaustion; responsive ops UI |
| **Defect if** | Unbounded recompute; request-path simulation; pool exhaustion |

---

## Suggested Phase 3 validation set

For the mandated **3-day small run**:

1. `S01_normal_store_baseline` (scaled down)  
2. `S03_shipping_cost_hesitation`  

Reconciliation must pass before Phase 4 unlocks all scenarios.

---

## Scenario × layer exercise matrix (summary)

| Scenario | Cart/WA/Purchase | Movement | KL/Decision | Dashboard | Notes |
|----------|------------------|----------|-------------|-----------|-------|
| S01 | Yes | Yes | Cautious | Yes | Baseline |
| S02 | Yes | Limited | Partial (no visitors) | Yes | Traffic gap honest |
| S03 | Yes | Yes | Yes | Yes | Core hesitation |
| S04 | Yes | Yes | Partial product | Yes | Identity critical |
| S05 | Yes | Yes | Attribution neg | Yes | No ROI |
| S06 | Yes | Yes | Attribution pos | Yes | Closure |
| S07 | Yes | Yes | Yes | Yes | Anti-discount pressure |
| S08 | Partial proxies | Yes | Cautious | Yes | No fake dwell |
| S09 | Partial | Yes | N/A invent | Yes | No fake widget open |
| S10 | Yes | — | Yes | Yes | Tag distribution |
| S11 | Yes | Neg | — | Yes | Terminal |
| S12 | Yes | Critical | — | Yes | Identity |
| S13 | Purchase only | — | Attribution neg | Yes | Organic |
| S14 | Yes | Yes | Attribution mid | Yes | Ambiguity |
| S15 | Yes | — | — | VIP UI | Suppress alerts |
| S16 | Tiny | — | Insufficient | Yes | Calm UI |
| S17 | Mixed | — | Conflict | Yes | No overclaim |
| S18 | Closure | Yes | — | Completed | Suppression |
| S19 | Failure | — | Ops attention | Partial | ≠ hesitation |
| S20 | Scale | Scale | Scale | Snapshots | Phase 4 |

---

**STOP for review.** No scenario execution in Phase 1.
