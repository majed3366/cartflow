# Decision Playbook Catalog V1

**Status:** Constitutional catalog — families only.  
**Date (UTC):** 2026-07-28  
**Authority:** Canonical playbook families under [`DECISION_PLAYBOOKS_CONSTITUTION_V1.md`](./DECISION_PLAYBOOKS_CONSTITUTION_V1.md).  
**Non-goals:** No UI. No production copy. No store-specific instances. No implementation.

Every published Decision Playbook **must** instantiate exactly one family from this catalog (or a future approved amendment).  
Ad-hoc “recommendation text” outside a family is unconstitutional.

**Instance rule:** The catalog defines the **family shape**. Store-specific objects (which product, which threshold, which message) are filled at generation time — never left generic.

**Publication rule:** If family minimum evidence is not met → **playbook is not generated** (diagnosis / insufficiency only) — **DP-004**.  
**Confidence rule:** A valid diagnosis does not auto-produce a playbook — **PBL-001** validation must pass.  
**Metadata rule:** Every family must define complete **PBL-002** publication metadata (internal engine only) before it may emit — see [`PLAYBOOK_PUBLICATION_METADATA_V1.md`](./PLAYBOOK_PUBLICATION_METADATA_V1.md).

---

## Family schema (mandatory fields)

Every family declares:

| Field | Meaning |
|-------|---------|
| **Family ID** | Stable identifier |
| **Inputs** | Signals / objects the generator may consume |
| **Evidence required** | Minimum evidence bar before a playbook instance may exist |
| **Execution location** | CartFlow · Commerce Platform · Business Operation (primary) |
| **Business task (shape)** | What kind of concrete task instances must name — not merchant-facing copy |
| **Expected outcome** | Business result the task aims at |
| **Reality validation** | How CartFlow observes whether it worked (**EM-002** class) |
| **Publication metadata (PBL-002)** | Internal engine fields — Family, Business Domain, Execution Type, Minimum Evidence, Minimum Confidence, Minimum Readiness State, Execution Location, Reality Validation Metric, Success Threshold, Failure Behaviour, Review Cadence, Supported Platforms |

Illustrative task shapes below are **directional patterns**, not production copy.  
Publication metadata must **never** be merchant-facing.

---

## Catalog

### PF-SHIPPING — Shipping

| Field | Definition |
|-------|------------|
| **Inputs** | Shipping-related observations; order / cart value bands; abandon-after-shipping signals; platform shipping config locus |
| **Evidence required** | Sufficient abandon / leave signal after shipping exposure **and** attributable shipping cost or rule context for a named cohort or threshold |
| **Execution location** | **Commerce Platform** (primary); Business Operation when carrier/contract change is required |
| **Business task (shape)** | Open the platform shipping settings for the named rule / threshold / zone and change or verify the specific cost or condition tied to the diagnosis |
| **Expected outcome** | Fewer leaves after shipping is shown; improved completion for the affected cohort |
| **Reality validation** | Lower abandonment after shipping · Higher purchase completion for the named value band |

**Publication metadata (PBL-002 — internal only; illustrative):**

| Field | Value |
|-------|--------|
| Playbook Family | Shipping (`PF-SHIPPING`) |
| Business Domain | Shipping / fulfillment cost & rules |
| Execution Type | B (C when carrier/contract) |
| Minimum Evidence | Leave-after-shipping + named threshold/cohort + shipping rule context |
| Minimum Confidence | 85% |
| Minimum Readiness State | READY |
| Execution Location | Commerce Platform |
| Reality Validation Metric | Shipping abandonment decreases |
| Success Threshold | Observed decrease in shipping-linked abandonment for named cohort/band after action window |
| Failure Behaviour | Return to Diagnosis · Continue collecting evidence |
| Review Cadence | Periodic family review (engine/ops — not merchant UI) |
| Supported Platforms | Zid · Salla · Shopify · future |

---

### PF-PAYMENT — Payment

| Field | Definition |
|-------|------------|
| **Inputs** | Payment-method / payment-step failures or drops; method availability; gateway errors; checkout payment stage |
| **Evidence required** | Drop or failure concentrated at payment stage **and** identifiable method / error / availability condition |
| **Execution location** | **Commerce Platform** (primary); Business Operation for bank / provider contracts |
| **Business task (shape)** | Open platform payment settings for the named method or failure condition and enable, fix, or replace that method |
| **Expected outcome** | Higher payment-step completion |
| **Reality validation** | Lower payment-stage abandonment · Higher purchase completion |

---

### PF-PRODUCT — Product

| Field | Definition |
|-------|------------|
| **Inputs** | Product-bound views, interest, leave-before-checkout; product identity; PDP engagement |
| **Evidence required** | Named product (or tight product set) with repeated interest **and** leave before purchase without a stronger competing cause |
| **Execution location** | **Commerce Platform** (PDP / catalog); Business Operation for creative / merchandising |
| **Business task (shape)** | Open the named product’s page / listing and change the specific deficient element the diagnosis isolates (content, options, clarity — not “optimize product”) |
| **Expected outcome** | Higher progression from product interest to checkout / purchase |
| **Reality validation** | Higher purchase completion for the named product · Lower PDP leave rate |

---

### PF-PRICING — Pricing

| Field | Definition |
|-------|------------|
| **Inputs** | Price-sensitivity signals; compare / hesitate-at-price; discount response; product or cart value |
| **Evidence required** | Named product or cart band with price-linked hesitation **and** current price / offer context |
| **Execution location** | **Commerce Platform** (price / offer); Business Operation for margin / positioning decisions |
| **Business task (shape)** | Review and decide the price or offer for the named product / band under the diagnosed hesitation — merchant owns the commercial trade-off |
| **Expected outcome** | Higher conversion at acceptable margin for that object |
| **Reality validation** | Higher conversion for the named object · Lower price-stage abandonment |

---

### PF-RECOVERY-MSG — Recovery Messages

| Field | Definition |
|-------|------------|
| **Inputs** | Recovery send / open / click / return / purchase outcomes; message sequence position; template identity |
| **Evidence required** | Named message (or sequence step) with open/engage **without** proportionate return-to-checkout or purchase |
| **Execution location** | **CartFlow** (primary) when recovery lives in CartFlow; Commerce Platform if recovery is platform-owned |
| **Business task (shape)** | Open the named recovery message / step and revise the specific weak element (offer, clarity, CTA, timing) tied to the diagnosis |
| **Expected outcome** | Higher return-to-checkout and recovery completion from that message |
| **Reality validation** | Higher recovery rate · Higher return-to-checkout after open |

---

### PF-WHATSAPP — WhatsApp

| Field | Definition |
|-------|------------|
| **Inputs** | WhatsApp delivery / read / reply / recovery linkage; template / WABA readiness; conversation outcomes |
| **Evidence required** | Channel-attributable gap (delivery, template, timing, or reply path) with enough volume to justify action |
| **Execution location** | **CartFlow** and/or **Commerce Platform** / Meta dependency as readiness states (**EXTERNAL_DEPENDENCY** when provider-blocked) |
| **Business task (shape)** | Fix the named WhatsApp configuration, template, or conversation step that the diagnosis isolates |
| **Expected outcome** | Reliable delivery and higher recovery / reply effectiveness on WhatsApp |
| **Reality validation** | Higher delivery/read success · Higher recovery via WhatsApp path |

---

### PF-CHECKOUT — Checkout

| Field | Definition |
|-------|------------|
| **Inputs** | Checkout-stage drops; field / step friction; shipping+payment handoff; guest vs account |
| **Evidence required** | Concentrated drop at a **named checkout stage** with causal evidence beyond generic “low conversion” |
| **Execution location** | **Commerce Platform** (primary) |
| **Business task (shape)** | Open the named checkout stage / setting and change the specific friction the diagnosis isolates |
| **Expected outcome** | Higher checkout completion through that stage |
| **Reality validation** | Lower abandonment at the named stage · Higher purchase completion |

---

### PF-TRUST — Trust

| Field | Definition |
|-------|------------|
| **Inputs** | Trust / policy / returns / contact visibility signals; hesitation without product or price dominance |
| **Evidence required** | Trust-linked leave pattern **and** missing or weak trust object (policy, contact, guarantee) on a named surface |
| **Execution location** | **Commerce Platform** (storefront content); Business Operation for policy truth |
| **Business task (shape)** | Add or clarify the named trust object on the named surface (returns, contact, guarantee — not “build trust”) |
| **Expected outcome** | Lower trust-linked hesitation; higher progression to purchase |
| **Reality validation** | Lower abandonment on trust-sensitive paths · Higher purchase completion |

---

### PF-PRODUCT-IMAGES — Product Images

| Field | Definition |
|-------|------------|
| **Inputs** | Image-quality / missing-image / gallery engagement; product identity; leave after image interaction |
| **Evidence required** | Named product with image deficiency signal strong enough vs competing causes |
| **Execution location** | **Commerce Platform** (media); Business Operation for creative production |
| **Business task (shape)** | Replace or complete images for the named product (count, angle, or quality gap the diagnosis names) |
| **Expected outcome** | Higher confidence progression from browse to checkout for that product |
| **Reality validation** | Higher purchase completion for the named product · Lower early leave after image view |

---

### PF-DELIVERY — Delivery

| Field | Definition |
|-------|------------|
| **Inputs** | Delivery promise, SLA, COD/delivery option friction; post-purchase delivery issues feeding repurchase hesitation |
| **Evidence required** | Delivery-linked abandon or complaint pattern with named option / zone / promise |
| **Execution location** | **Commerce Platform** and/or **Business Operation** (carrier, SLA, ops) |
| **Business task (shape)** | Change the named delivery promise, option, or ops rule tied to the diagnosis |
| **Expected outcome** | Fewer delivery-linked leaves / failures; higher completion or repurchase confidence |
| **Reality validation** | Lower delivery-linked abandonment · Higher purchase / repurchase completion |

---

### PF-RETURNING — Returning Visitors

| Field | Definition |
|-------|------------|
| **Inputs** | Return-visit cohorts; prior cart / view without purchase; re-engagement outcomes |
| **Evidence required** | Identifiable returning cohort with repeated interest **and** incomplete purchase path |
| **Execution location** | **CartFlow** (recovery / communication) and/or **Commerce Platform** (offer / merchandising) |
| **Business task (shape)** | Act on the named returning cohort via the specific channel or offer the diagnosis supports — not “investigate customers” |
| **Expected outcome** | Higher conversion among returning visitors |
| **Reality validation** | Higher purchase completion for returning cohort · Higher recovery among returners |

---

### PF-LOW-CONV — Low Conversion

| Field | Definition |
|-------|------------|
| **Inputs** | Conversion rate vs store baseline / peer band; funnel stage contributions; competing diagnoses |
| **Evidence required** | **Must not** publish as a playbook from “conversion is low” alone. Requires a **winning subordinate diagnosis** (shipping, checkout, product, etc.) with that family’s evidence bar |
| **Execution location** | Inherited from the winning subordinate family |
| **Business task (shape)** | **Meta-family:** instances must collapse into a concrete subordinate family task. A standalone “improve conversion” playbook is forbidden |
| **Expected outcome** | Outcome of the subordinate family |
| **Reality validation** | Validation of the subordinate family; overall conversion may be a secondary rollup |

---

### PF-HIGH-INTEREST — High Interest / Low Purchase

| Field | Definition |
|-------|------------|
| **Inputs** | High view / engagement with low purchase; product or category bound; stage of leave |
| **Evidence required** | Named product/category with high interest **and** leave stage identified; competing causes resolved enough to pick one task family |
| **Execution location** | Usually **Commerce Platform**; may route to Product / Pricing / Trust / Images subordinate tasks |
| **Business task (shape)** | Prefer binding to a subordinate family (Product, Pricing, Trust, Images, Checkout). If published under this ID, task must still name object + leave stage + concrete change |
| **Expected outcome** | Convert interest into purchase for the named object |
| **Reality validation** | Higher purchase completion for high-interest object · Lower leave at the named stage |

---

### PF-VIP — VIP Customers

| Field | Definition |
|-------|------------|
| **Inputs** | VIP / high-value identity; abandon or silence among VIPs; recovery outcomes for VIP cohort |
| **Evidence required** | Named VIP cohort or customers with actionable gap (abandon, unanswered, failed recovery) at sufficient confidence |
| **Execution location** | **CartFlow** (primary for contact / recovery); Business Operation for offline relationship work |
| **Business task (shape)** | Contact or recover the named VIP cohort / customers through the CartFlow path the diagnosis supports — not “investigate VIP” |
| **Expected outcome** | Recovered VIP purchases or closed VIP silence with known outcome |
| **Reality validation** | Higher VIP recovery / purchase completion · Lower VIP abandon without contact |

---

### PF-COMMUNICATION — Communication

| Field | Definition |
|-------|------------|
| **Inputs** | Message performance across channels; timing; template set; reply handling (non-WhatsApp-specific or multi-channel) |
| **Evidence required** | Named message / channel / timing gap with outcome evidence |
| **Execution location** | **CartFlow** (primary) |
| **Business task (shape)** | Change the named message, timing, or reply handling rule — not “improve communication” |
| **Expected outcome** | Higher response, return, or recovery from that communication object |
| **Reality validation** | Higher recovery / reply / return rates for the named object |

---

### PF-PLATFORM-CONFIG — Platform Configuration

| Field | Definition |
|-------|------------|
| **Inputs** | Misconfiguration / missing capability signals; feature flags; integration health; checkout/shipping/payment config completeness |
| **Evidence required** | Specific configuration defect linked to observed commerce harm (or hard block) |
| **Execution location** | **Commerce Platform** (primary); readiness often **BLOCKED** / **EXTERNAL_DEPENDENCY** until fixed |
| **Business task (shape)** | Open the named platform setting and complete the named configuration change |
| **Expected outcome** | Unblock or restore the broken commerce path |
| **Reality validation** | Path completion resumes · Related abandonment / error rate falls |

---

### PF-BUSINESS-OPS — Business Operations

| Field | Definition |
|-------|------------|
| **Inputs** | Ops-only causes: staffing, fulfillment capacity, supplier, policy exceptions, offline process |
| **Evidence required** | Diagnosis that CartFlow cannot resolve in software **and** enough evidence that ops action is the correct locus |
| **Execution location** | **Business Operation** |
| **Business task (shape)** | Name the ops action and owner locus (who/what process) — never pretend CartFlow will perform it |
| **Expected outcome** | Ops constraint removed or mitigated; commerce metric improves as a consequence |
| **Reality validation** | Downstream commerce metric named by diagnosis (abandonment / completion / recovery) after ops change is observed |

---

## Family selection rules

1. **One primary family per playbook instance.**  
2. **Prefer the most specific causal family** over umbrella families (`PF-LOW-CONV`, `PF-HIGH-INTEREST`).  
3. **Umbrella families may not publish abstract tasks** — they must bind to a concrete subordinate task or remain diagnosis-only.  
4. **Execution location** on the instance must match the family’s primary location unless an approved override is recorded (e.g. Shipping → Business Operation for carrier contracts).  
5. **New families** require catalog amendment — surfaces must not invent families in copy.  
6. **PBL-002:** A family may not emit until its publication metadata block is complete (Shipping example above is the shape; other families must be calibrated before engine eligibility).  
7. **PBL-001:** Passing diagnosis + evidence still requires Playbook Validation before publication.

---

## STOP

Catalog defines families only.

**No implementation. No production copy. No UI.**

Await constitutional approval with the rest of this pack.
