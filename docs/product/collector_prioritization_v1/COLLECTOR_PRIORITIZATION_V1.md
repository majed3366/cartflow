# CartFlow Collector Prioritization V1

**Status:** Official research & architecture roadmap  
**Scope:** Docs only — no collector implementation, no Home/Diagnostic/Evidence Expansion code changes  
**Date (UTC):** 2026-07-28  

## Governing question

> Which missing evidence would most improve CartFlow's ability to explain **why** customers do not purchase?

Not: what data can we collect.

## Inputs used

| Source | Role |
|--------|------|
| Evidence Expansion catalog (`observable_registry_v1`) | Governed missing observables per family |
| Cause registry (`cause_registry_v1`) | Competing causes + evidence gates |
| Living Store / CEO packs | Dominant published status = `insufficient_evidence` on shipping-stage leave |
| Widget + recovery + WhatsApp paths | Already-collected signals (reason tags, phone, delivery truth) |
| Provider docs (Zid abandoned-cart phases; Salla/Shopify typical gaps) | Platform support realism |

## Diagnostic families in scope

| Family | Dominant Living Store state | Competing causes |
|--------|----------------------------|------------------|
| `checkout_abandonment_after_shipping` | **insufficient_evidence** (stage known, subtype unknown) | shipping_cost, delivery_time, shipping_option_availability, late_shipping_disclosure, payment_friction, unknown |
| `interest_without_purchase` | Often insufficient causal | price, product_images/quality, shipping_cost, unknown |
| `payment_friction_at_checkout` | Needs payment signals | payment_friction vs shipping/price |
| `contact_followup_blocked` | Often **supported** via `no_phone` | missing_contact (already strong) |

---

# 1) Master Collector Catalog

IDs are stable keys for the roadmap (not implemented).

### Shipping / checkout stage

| ID | Collector | Observable intent |
|----|-----------|-------------------|
| C-S01 | Shipping step entered | Confirm shipping UI appeared |
| C-S02 | Shipping cost first shown | First numeric shipping cost visible |
| C-S03 | Shipping option selected | Chosen method/option before leave |
| C-S04 | Delivery estimate shown | ETA / delivery window visible |
| C-S05 | Shipping method changed | Option toggled before abandon |
| C-S06 | Shipping step dwell | Time on shipping step |
| C-S07 | Return after shipping | Revisit after shipping seen |
| C-S08 | Address editing at checkout | Address fields edited |

### Payment / checkout completion

| ID | Collector | Observable intent |
|----|-----------|-------------------|
| C-P01 | Payment step reached | Entered payment after shipping |
| C-P02 | Payment method chosen | Selected method |
| C-P03 | Payment attempt | Submit / authorize started |
| C-P04 | Payment failure | Decline / error code class |
| C-P05 | Coupon attempt | Discount code try |
| C-P06 | Checkout dwell (payment) | Time on payment step |

### Product interest

| ID | Collector | Observable intent |
|----|-----------|-------------------|
| C-R01 | Image gallery interaction | Gallery open / swipe |
| C-R02 | Spec expansion | Specs accordion open |
| C-R03 | Reviews opened | Reviews section engagement |
| C-R04 | Variant change | Option/SKU change |
| C-R05 | Repeat product visits | Same product multi-session |
| C-R06 | Add-to-cart without checkout | ATC then leave pre-shipping |

### Storefront navigation

| ID | Collector | Observable intent |
|----|-----------|-------------------|
| C-F01 | Search usage | Search queries / results click |
| C-F02 | Category path | Category → product path |
| C-F03 | Product comparison | Compare / multi-PDP pattern |
| C-F04 | Exit destination | Next URL / leave type (tab close unknown) |
| C-F05 | Session return timing | Gap until return |

### Communication / recovery

| ID | Collector | Observable intent |
|----|-----------|-------------------|
| C-M01 | Usable phone captured | Valid phone before leave |
| C-M02 | Message accepted / sent | Provider accept (partially exists) |
| C-M03 | Message delivered | Provider delivery truth (partial) |
| C-M04 | Message opened | Open/read if provider exposes |
| C-M05 | Reply timing | Customer reply latency |
| C-M06 | Link click in message | CTA click |
| C-M07 | Revisit after message | Store return post-outreach |
| C-M08 | Purchase after communication | Attributed purchase post-message |

### Already partially available (not new collectors — inventory)

| Signal | Status |
|--------|--------|
| Hesitation / reason tag (shipping, price, payment, …) | Widget — **exists** (too coarse alone) |
| `shipping_stage_observed` (weak) | Derived — **exists**, insufficient alone |
| `no_phone` / contact blocked | Lifecycle — **exists**, often supported |
| WhatsApp accept/deliver | Provider truth — **partial** |
| Cart value / VIP | Cart row — **exists**, not causal |

---

# 2) Diagnostic Impact Matrix

| ID | Diagnoses improved | Evidence Gap closed | Causes distinguished | Recommendations unlocked |
|----|--------------------|---------------------|----------------------|--------------------------|
| C-S02 | checkout_after_shipping | Shipping leave w/o subtype | cost vs late_disclosure; cost vs vague “shipping” | Show/fix shipping cost earlier |
| C-S03 | checkout_after_shipping | Options ambiguity | options vs cost | Fix missing methods / option UX |
| C-S04 | checkout_after_shipping | Time vs cost | delivery_time vs cost | Clarify ETA before pay |
| C-S05 | checkout_after_shipping | Options friction | options vs cost | Reduce method thrash / gaps |
| C-P01–P03 | checkout_after_shipping + payment_friction | Post-shipping abandon | payment vs shipping_* | Payment UX / methods |
| C-P04 | payment_friction | Failure vs abandon | payment_friction supported | Fix failing method |
| C-R01–R03 | interest_without_purchase | Browse w/o cause | images/quality vs price | Content / trust fixes |
| C-R05 | interest_without_purchase | Hesitation pattern | interest recurrence | Follow-up timing |
| C-M01 | contact_followup_blocked | Already strong | contact vs other | Capture phone earlier |
| C-M04–M08 | contact + recovery value | Ops follow-up quality | contact effectiveness | Message/template tuning |
| C-F01–F04 | weak / indirect | Rarely closes shipping gap | rarely separates shipping causes | Postpone |

---

# 3) Provider Capability Matrix

Legend: **Native** = provider API/webhook; **Widget** = CartFlow storefront JS; **Partial** = incomplete; **Unsupported** = not reliable.

| ID | Zid | Salla | Shopify | Generic (widget) |
|----|-----|-------|---------|------------------|
| C-S01 | Partial (phase `shipping_*`) | Partial | Partial (checkout ext.) | **Widget** |
| C-S02 | Unsupported native | Unsupported native | Unsupported native | **Widget** |
| C-S03 | Partial (phase `shipping_method`) — **not cost** | Partial | Partial | **Widget** (preferred) |
| C-S04 | Unsupported native | Unsupported native | Unsupported native | **Widget** |
| C-S05–S08 | Unsupported / weak | Unsupported / weak | Unsupported / weak | **Widget** |
| C-P01 | Partial (`payment_method` phase) | Partial | Partial | Widget |
| C-P02–P03 | Partial | Partial | Partial | Widget |
| C-P04 | Partial webhooks | Partial | Partial (orders/payments) | Hybrid |
| C-P05 | Unsupported | Unsupported | Partial (discounts) | Widget |
| C-R01–R05 | Unsupported | Unsupported | Unsupported | **Widget** |
| C-F01–F05 | Unsupported | Unsupported | Partial (pixels) | Widget / analytics |
| C-M01 | Widget + cart | Widget + cart | Widget + cart | **Exists path** |
| C-M02–M03 | WhatsApp provider | WhatsApp provider | WhatsApp provider | **Partial exists** |
| C-M04 | Often Unsupported (WA) | Often Unsupported | Often Unsupported | Provider-dependent |
| C-M05–M08 | Partial | Partial | Partial | Hybrid |

**Rule:** Never assume Zid phase ≡ shipping cost. Zid `shipping_method` phase ≠ `shipping_cost_first_shown`.

---

# 4) Cost Matrix

| ID | Eng. | Runtime | Storage | Maintenance | Overall |
|----|------|---------|---------|-------------|---------|
| C-S02 | Medium | Low | Low | Medium | **Medium** |
| C-S03 | Medium | Low | Low | Medium | **Medium** |
| C-S04 | Medium | Low | Low | Medium | **Medium** |
| C-S01 | Low | Low | Low | Low | **Low** |
| C-S06 | Low | Low | Low | Low | **Low** |
| C-P01–P03 | Medium–High | Low | Low | Medium | **Medium–High** |
| C-P04 | High | Low | Medium | High | **High** |
| C-R01–R03 | Medium | Medium | Medium | Medium | **Medium** |
| C-F01–F04 | High | High | High | High | **High** |
| C-M04 | High | Low | Low | High | **High** |
| C-M06–M08 | Medium | Low | Medium | Medium | **Medium** |

---

# 5) Business / Diagnostic Value

| ID | Diagnostic value | Why |
|----|------------------|-----|
| C-S02 | **Very High** | Unlocks the Living Store gap; turns insufficiency into supported shipping_cost or late_disclosure |
| C-S03 | **Very High** | Separates options from cost — second half of shipping ambiguity |
| C-S04 | **High** | Separates delivery_time from cost |
| C-P01–P03 | **High** | Separates payment from shipping after stage |
| C-P04 | **High** (narrow) | Strong when failures exist; less frequent than shipping leave |
| C-R01–R03 | **Medium** | Improves interest family; not Living Store primary |
| C-M01 | **Medium** (already mostly covered) | Contact family already diagnoses |
| C-M04–M08 | **Medium** | Improves recovery ops more than purchase-cause diagnosis |
| C-F* | **Low** | Weak causal link to purchase-cause families |

---

# 6) Prioritization Score

Score = DiagnosticValue(VH=5…L=2) + FamiliesHelped×1 + ProviderFit(Widget-generic=2, Partial=1, Hard=0) − EngCost(L=0,M=1,H=2) − Runtime(L=0,M=1,H=2)

| Rank | ID | Score | Notes |
|------|----|-------|-------|
| 1 | **C-S02** shipping_cost_first_shown | **9** | VH + shipping family + widget + med cost |
| 2 | **C-S03** shipping_option_selected | **8** | VH; Zid phase partial assist |
| 3 | **C-S04** delivery_estimate_shown | **7** | High; widget |
| 4 | **C-P01** payment_step_reached | **7** | Separates payment vs shipping |
| 5 | **C-S05** shipping_method_changed | **6** | Helps options |
| 6 | **C-P03** payment_attempt | **6** | Cross-family |
| 7 | **C-S07** return_after_shipping | **5** | Useful secondary |
| 8 | **C-R05** repeat_product_visits | **5** | Interest family |
| 9 | **C-R01** image_gallery | **5** | Interest |
| 10 | **C-P04** payment_failure | **4** | High eng; narrow |
| … | C-F*, C-M04 | ≤3 | Defer |

---

# 7) Dependencies

```text
C-S01 Shipping step entered
  └─► C-S02 Cost first shown
  └─► C-S03 Option selected
  └─► C-S04 Delivery estimate shown
  └─► C-S05 Method changed
  └─► C-S06 Dwell
        └─► C-S07 Return after shipping

C-S02/C-S03
  └─► C-P01 Payment step reached  (proves visitor continued past shipping)
        └─► C-P02 Method / C-P03 Attempt / C-P04 Failure

C-R05 can stand alone for interest family.

C-M02/M03 (partial exists) ◄─ before C-M04 open (provider-limited)
```

**Note:** Living Store already has weak stage (`shipping`). Wave 1 may treat C-S01 as **satisfied-by-existing** and start at C-S02 — still document C-S01 as explicit hardening if stage provenance is noisy.

---

# 8) Recommended Waves

### Wave 1 — Highest ROI (shipping insufficiency)

Independently valuable: converts Living Store shipping leave from insufficiency toward supported causes.

1. **C-S02 Shipping cost first shown** ← **build first**  
2. C-S03 Shipping option selected  
3. C-S04 Delivery estimate shown (if capacity)

### Wave 2 — Separate payment from shipping

1. C-P01 Payment step reached  
2. C-P03 Payment attempt after shipping  
3. C-P02 Payment method chosen  

### Wave 3 — Interest / product trust

1. C-R05 Repeat product visits  
2. C-R01 Image gallery  
3. C-R03 Reviews opened  
4. C-P05 Coupon attempt  

### Wave 4 — Recovery communication quality

1. C-M06 Link click  
2. C-M07 Revisit after message  
3. C-M08 Purchase after communication  
4. C-M04 Message opened **only if** provider supports  

Each wave improves a different published diagnosis family without requiring the next wave.

---

# 9) What NOT to build (now)

| Attractive idea | Why postpone / reject |
|-----------------|------------------------|
| Full session replay / heatmaps | High cost; does not yield governed cause keys |
| Exit destination / tab-close | Unreliable; weak causal mapping |
| Storefront search & category graphs | Improves merchandising analytics, not shipping-cause diagnosis |
| Message open (WA) | Often unsupported; do not fake opens |
| Pixel-only Shopify stacks | Duplicate noise; prefer CartFlow widget contract |
| Collecting “all checkout fields” | Violates no-random-collection; no per-diagnosis ownership |
| Deep payment PSP integration (Wave 1) | High cost; Living Store gap is **pre-payment shipping** |

---

# Deliverable index

| # | Artifact |
|---|----------|
| 1 | Catalog — §1 above |
| 2 | Collector / impact — §2 |
| 3 | Provider capability — §3 |
| 4 | Diagnostic coverage — §2 + families table |
| 5 | Cost — §4 |
| 6 | Priority — §6 |
| 7 | Waves — §8 |
| 8 | Deferred — §9 |
| 9 | Final recommendation — `FINAL_RECOMMENDATION_V1.md` |

---

**STOP.** Research published. No collector implementation until Wave 1 is explicitly approved.
