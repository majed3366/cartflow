# Claim Publication Gate V1

**Status:** Binding publication gate for future landing claims.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Evidence Readiness V1  
**Related:** Copy Architecture `CLAIM_AND_EVIDENCE_MATRIX_V1.md`  

No silent override. Any **No** → Block · Bounded rewrite · Disclosure · Illustrative-only · Deferral.

---

## 1. Twelve-question gate

A claim may be published only when all applicable answers are **Yes**:

1. Does the capability exist?  
2. Has it executed successfully?  
3. Is it merchant-visible or customer-visible?  
4. Is the evidence current?  
5. Has the relevant validation been completed?  
6. Does the wording stay within the evidence?  
7. Does commercial readiness support the claim?  
8. Is the claim legally safe?  
9. Is the claim understandable without internal context?  
10. Is the supporting visual truthful?  
11. Can the claim survive mobile compression?  
12. Has an owner approved publication?  

---

## 2. Mandatory claim decisions

| Claim | Decision | Evidence level | Evidence source | Evidence gap | Allowed wording ceiling | Required disclosure | Owner |
|-------|----------|----------------|-----------------|--------------|-------------------------|---------------------|-------|
| CartFlow helps recover abandoned purchase opportunities | **Bounded** | E3 | Recovery engine + schedules | Landing journey visuals | فرص الشراء / الاستعادة — not guaranteed revenue | Opportunity ≠ confirmed sale | Product |
| The in-store tool captures customer-selected hesitation | **Block** (until capture) | E3 engine / E1 landing | V2 widget + reason API; settings PNG ineligible | Storefront capture CAP-02/03 | After capture: records selected reasons | Not all visitors interact | Product |
| CartFlow understands hesitation early | **Block** (until capture) | E3 | Widget triggers + reasons | Mind-reading risk; no E6 visual | After capture: early in-store understanding opportunity | No intention mind-reading | Product |
| CartFlow continues recovery through WhatsApp | **Block** → **Bounded** after ops+capture | E3 | Twilio path; Meta often blocked | Journey capture; provider honesty | Continuation when activated | Ops/provider gates; no delivery SLA | Product/Ops |
| CartFlow tracks customer return | **Bounded** | E3–E4 | Return signals / carts | Language must match signal | Only if UI shows return clearly | Verify signal semantics before copy | Product |
| CartFlow detects confirmed purchase | **Bounded** | E3–E4 | Purchase Truth + carts UI | Landing visual optional | Confirmed purchase recognised | Prefer CAP-06/10 | Product |
| CartFlow stops unnecessary recovery after purchase | **Bounded** | E3–E4 | Purchase suppression / tests + UI | Landing visual recommended | Stops further recovery after purchase | CAP-06 recommended | Product |
| The dashboard shows what needs attention | **Block** (stale landing) → **Bounded** after capture | E5 packs / E1 landing | Home/Workspace 2026-07 packs | Landing-grade capture | Attention / priority now | Demo data; current face only | Product |
| CartFlow forms store understanding over time | **Bounded** | E3 lab / E5 ORV partial | Living Store + ORV | No organic longitudinal E6 | Conditional: when evidence accumulates | No auto-ML / gets smarter | Product |
| CartFlow identifies shipping hesitation | **Illustrative** or **Block** | E2–E3 engine / E5 ORV themes partial | CISYN / Living Store mixes | Theme-specific RV for landing | Labeled illustrative until theme RV pass | Not universal | Product |
| CartFlow detects product add-to-cart / purchase weakness | **Illustrative** or **Block** | E2–E5 | Findings/ORV when present | Materialisation + theme RV | Labeled illustrative until validated capture | Insufficient possible | Product |
| CartFlow distinguishes traffic weakness from conversion weakness | **Block** | E2 | Language audit cautions | Dedicated RV | — | — | Product |
| CartFlow says when evidence is insufficient | **Bounded** | E4 | Home/Workspace insufficient/wait | Landing CAP-12 | لا توجد أدلة كافية بعد | Honesty ≠ broken product | Product |
| CartFlow separates observation from conclusion | **Bounded** | E4 | Decision/Guidance behaviour + UI | — | Observation ≠ conclusion | Merchant language only | Product |
| CartFlow does not materially affect storefront speed | **Block** | E0–E2 | Loader async only | Measured Web Vitals study | — | — | Engineering |
| CartFlow supports Zid | **Bounded** | E3 | OAuth + snippet + adapters | Self-serve incomplete | مدعوم حاليًا | قد يتطلب التفعيل تدخلًا تشغيليًا | Product/Ops |
| Salla support is planned | **Publish** (as Planned) | E1 | `adapter_scaffold_only` | — | مخطط له only | Not available now | Product |
| Shopify support is planned | **Publish** (as Planned) | E1 | scaffold | — | مخطط له only | Not available now | Product |
| Start Free is available | **Bounded** | E4 | `/signup` | Instant activation false | ابدأ / Start Free → signup | Not instant full production; beta honesty if free | Product |
| CartFlow offers demo booking | **Block** | E0 | No path | Booking product | — | — | — |
| Merchant data remains isolated | **Bounded** / **legal review** for absolutes | E2–E3 | Isolation tests + store identity | Absolute privacy wording | Store-separated / لا تُخلط بيانات المتاجر | No absolute privacy/security seals without legal | Eng/Legal |

---

## 3. Reality Validation dependencies

| Scenario | Required Input | Expected Platform Truth | Expected Merchant Surface | Failure Condition | Landing Claim Affected | Publication Consequence |
|----------|----------------|-------------------------|---------------------------|-------------------|------------------------|-------------------------|
| RV-LP-01 Knowledge patterns painted | Living Store / SRS with materialised findings | Findings tied to evidence | Home/knowledge cards | Empty or unlinked cards | Pattern claims LP-09 | **Block** themes |
| RV-LP-02 Insufficient evidence | Store with weak evidence | Insufficient/wait state | Workspace/Home Arabic honesty | Hidden uncertainty or fake certainty | Insufficient claim | **Block** if UI lies |
| RV-LP-03 Conflicting evidence | Conflicting signals | Conflict surfaced or abstention | Merchant UI | Conflict silently resolved to fake certainty | Conflict theme | **Illustrative/Block** |
| RV-LP-04 Confidence progression | Multi-stage evidence | Confidence changes with evidence | Merchant-visible status | Fake % | Knowledge confidence | **Block** fake % |
| RV-LP-05 Traffic vs conversion | Traffic + conversion evidence pair | Distinction supported in product language | Home/Workspace | Visit language unsafe (audit) | CL-18 / LP-10 | **Block** until pass |
| RV-LP-06 Repeated shipping hesitation | Shipping hesitation signals | Pattern eligible | Knowledge/finding | No merchant-visible pattern | Shipping theme | Illustrative or Block |
| RV-LP-07 Add frequent / purchase rare | Product signals | Pattern eligible | Knowledge/finding | No paint | Product weakness theme | Illustrative or Block |
| RV-LP-08 WA return without purchase | Return after WA, no purchase | States consistent | Carts/comms/Home | Identity mismatch | WA continuation themes | **Block** misleading mashup |
| RV-LP-09 Discount ineffectiveness | Discount context + outcome | Pattern or abstention | Knowledge | Invented ineffectiveness | Discount theme | **Block** without evidence |
| RV-LP-10 Movement continuity | Multi-step journey | Timeline/states coherent | Merchant UI | Broken chronology | Continuity LP-11 | Conceptual only |
| RV-LP-11 Purchase closure consistency | Purchase after recovery | Stop further recovery | Carts/proof | Messages continue | Purchase stop | **Block** if fails |
| RV-LP-12 Dashboard vs canonical truth | Same as_of | Home/Workspace match truth | Home/Workspace | Surface contradicts ops | LP-08 | **Block** capture |
| RV-LP-13 Merchant knowledge visibility | Materialisation path | Cards visible when eligible | Home | Always empty | LP-09 always-on | **Block** always-on |
| RV-LP-14 14-day / 60-day accumulation | Longer window sim | Clearer understanding possible | Knowledge progression | Fake charts | LP-11 | Conceptual / illustrative |

---

## 4. Gate outcomes for copy release

| Outcome | Meaning |
|---------|---------|
| Publish | Allowed Now for final draft **and** future publish after language approval |
| Bounded | Draft allowed only inside wording ceiling + disclosure |
| Illustrative | Must be labeled; not product proof |
| Block | No landing claim until gap closed |

Publication of any claim still requires question **12** (owner approval) after capture/validation where applicable.
