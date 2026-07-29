# Claim and Evidence Matrix V1

**Status:** Binding claim inventory for future Arabic landing copy.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Copy Architecture V1  
**Authorities:** Constitution V1 · Information Architecture V1 · Tone Governance V1  

**Rule:** No claim may appear in final copy unless **Allowed Now = Yes** *or* blockers are cleared and this matrix is updated.

### Claim types

`Problem claim` · `Product capability claim` · `Operational claim` · `Integration claim` · `Knowledge claim` · `Trust claim` · `Commercial claim` · `Outcome claim`

### Readiness values

`Ready` · `Partial` · `Needs capture` · `Needs validation` · `Needs ops verify` · `Needs legal` · `Blocked` · `Deferred`

---

## 1. Claim inventory

| Claim ID | Section | Proposed Claim Meaning | Claim Type | Required Evidence | Current Readiness | Disclosure Needed | Allowed Now | Final Owner |
|----------|---------|------------------------|------------|-------------------|-------------------|-------------------|-------------|-------------|
| CL-01 | LP-02 / LP-03 | CartFlow addresses lost purchase opportunities / abandoned carts as a real merchant problem | Problem claim | Merchant-recognisable problem frame (no fake %) | Ready | No | **Yes** | Product |
| CL-02 | LP-02 | Helps recover abandoned purchase **opportunities** (not guaranteed recovered revenue) | Product capability claim | Recovery engine exists in production | Partial | Yes — opportunity ≠ confirmed revenue | **Yes** with wording discipline | Product |
| CL-03 | LP-02 | Begins to reveal what prevents customers from completing purchases | Product capability claim | Widget + reasons + merchant visibility exist | Partial | Must not equal full Knowledge identity | **Yes** (foreshadow only) | Product |
| CL-04 | LP-04 | Reminders/discounts alone are incomplete without understanding before/after | Problem claim | Conceptual reframe | Ready | No competitor attack | **Yes** | Product |
| CL-05 | LP-05 | CartFlow connects customer journey to what the merchant later sees | Product capability claim | End-to-end product path exists | Partial | Outline only; depth elsewhere | **Yes** | Product |
| CL-06 | LP-06 | Captures / surfaces hesitation through in-store tool (widget) | Product capability claim | Real storefront widget UI + reason capture | Needs capture | Beside real widget; not settings-as-UX | **No** until capture | Product / Design |
| CL-07 | LP-06 | Creates early opportunity to assist before customer disappears | Operational claim | Widget intervention behaviour | Needs capture | No mind-reading / all-visitors | **No** until capture | Product |
| CL-08 | LP-07 | Can continue the journey through WhatsApp | Operational claim | WA recovery journey + states | Needs capture + ops verify | Provider/gate honesty | **No** until verify+capture | Product / Ops |
| CL-09 | LP-07 | Tracks / reflects customer response and follow-up state | Operational claim | Merchant communication/reply states | Needs capture | No guaranteed reply | **No** until capture | Product |
| CL-10 | LP-07 / LP-08 | Tracks customer return to store | Operational claim | Return / movement signals in product | Partial | Wording must match actual signal | **Conditional** — verify signal language | Product |
| CL-11 | LP-07 / LP-12 | Recognises purchase closure | Operational claim | Purchase Truth / conversion stop | Ready (engine) | Show as behaviour not magic | **Yes** with evidence coupling preferred | Product |
| CL-12 | LP-07 / LP-12 | Stops unnecessary recovery after purchase | Operational claim | Purchase suppression / schedule cancel | Ready (engine) | Prefer beside evidence | **Yes** | Product |
| CL-13 | LP-08 | Shows what needs merchant attention | Observed / Operational | Current Home / Workspace attention surfaces | Needs capture (current faces) | No fake KPIs | **No** until capture | Product / Design |
| CL-14 | LP-08 | Brings together recovery state and customer movement for the merchant | Operational claim | Dashboard surfaces | Needs capture | Avoid undefined “all-in-one” | **No** until capture | Product |
| CL-15 | LP-09 | May form knowledge / recurring-pattern understanding when evidence is sufficient | Knowledge claim | Governed knowledge/findings with evidence state | Needs validation | Conditional modality; no fabrication | **No** until validation | Product |
| CL-16 | LP-09 / LP-12 | States when evidence is insufficient | Trust / Knowledge claim | Insufficient-evidence UX/states | Partial | Frame as honesty not failure | **Yes** as principle; UI proof preferred | Product |
| CL-17 | LP-09 / LP-12 | Distinguishes observation from conclusion | Trust claim | Product behaviour + copy discipline | Partial | Required in Knowledge/Trust sections | **Yes** | Product |
| CL-18 | LP-10 | Helps distinguish traffic weakness from conversion weakness | Outcome / Knowledge claim | Product must actually support this distinction | Needs validation | Only if product surfaces it | **No** until validation | Product |
| CL-19 | LP-10 | Helps merchant know what to review / stop assuming | Decision support / Outcome | Anchored to LP-08/09 behaviours | Partial | No “runs your store” | **Conditional** after evidence chain | Product |
| CL-20 | LP-11 | Value can accumulate as evidence accumulates over time | Outcome claim | Continuity of evidence→knowledge path | Partial | Conditional language only | **Yes** with modality lock | Product |
| CL-21 | LP-12 | No recommendation without sufficient evidence | Trust claim | Guidance/decision gating behaviour | Needs validation | Merchant language | **Conditional** | Product |
| CL-22 | LP-12 | Merchant data remains isolated per store | Trust claim | Store isolation model | Partial | Absolute privacy → legal | **Yes** bounded; absolutes **No** | Eng / Legal |
| CL-23 | LP-13 | Supports Zid | Integration claim | Production Zid path | Ready (ops-gated) | **Yes — ops-gated activation** | **Yes** with disclosure | Product / Ops |
| CL-24 | LP-13 | Zid activation may require operational intervention | Integration / Commercial | Onboarding reality | Ready | Required if claiming Zid | **Yes** (must disclose) | Ops |
| CL-25 | LP-13 | Salla is planned | Integration claim | Scaffold/plan status | Ready as plan | Not “under validation” unless true | **Yes** as Planned | Product |
| CL-26 | LP-13 | Shopify is planned | Integration claim | Scaffold/plan status | Ready as plan | Same | **Yes** as Planned | Product |
| CL-27 | LP-13 | Works on all platforms / instant install | Integration claim | — | Blocked | — | **No** | — |
| CL-28 | LP-15 / LP-01 | Signup is available | Commercial claim | `/signup` path | Ready | No result guarantees | **Yes** | Product |
| CL-29 | LP-15 | Login is available | Commercial claim | `/login` path | Ready | — | **Yes** | Product |
| CL-30 | LP-15 | Book a Demo is available | Commercial claim | Distinct booking path | Deferred | — | **No** | — |
| CL-31 | LP-14 / FAQ | Widget does not materially harm storefront speed | Operational claim | Measured performance evidence | Needs validation | Cannot claim without proof | **No** | Engineering |
| CL-32 | LP-02 | Commerce Intelligence Platform / category creation | Product / Brand | — | Blocked (Disclosure Law) | Internal only | **No** | — |
| CL-33 | Any | Guaranteed growth / ROI percentages / fake social proof | Outcome / Commercial | — | Blocked (Truth Policy) | — | **No** | — |
| CL-34 | LP-07 | Guaranteed WhatsApp delivery or reply | Operational claim | — | Blocked | — | **No** | — |
| CL-35 | LP-09 | Fabricated findings / always knows why | Knowledge claim | — | Blocked | — | **No** | — |

---

## 2. Mandatory claims — decision summary

| Mandatory theme | Claim IDs | Allowed now? |
|-----------------|-----------|--------------|
| Helps recover abandoned purchase opportunities | CL-02 | Yes (opportunity wording) |
| Captures hesitation through widget | CL-06, CL-07 | **No** until capture |
| Continues journey through WhatsApp | CL-08 | **No** until ops+capture |
| Tracks customer return | CL-10 | Conditional — verify language |
| Recognises purchase closure | CL-11 | Yes |
| Stops unnecessary recovery after purchase | CL-12 | Yes |
| Shows what needs merchant attention | CL-13 | **No** until capture |
| Distinguishes observation from conclusion | CL-17 | Yes |
| May form knowledge when evidence sufficient | CL-15 | **No** until validation |
| States insufficient evidence | CL-16 | Yes (principle) |
| Helps traffic vs conversion distinction | CL-18 | **No** until validation |
| Supports Zid | CL-23 + CL-24 | Yes with ops-gate disclosure |
| Salla planned | CL-25 | Yes as Planned |
| Shopify planned | CL-26 | Yes as Planned |
| Signup available | CL-28 | Yes |
| Demo booking not available | CL-30 | Correct — do not offer |
| Widget does not harm storefront speed | CL-31 | **No** without perf evidence |

---

## 3. Copy readiness matrix

| Section | Architecture Ready | Final Copy Ready | Evidence Blocker | Operational Blocker | Validation Blocker | Legal Blocker | Decision |
|---------|-------------------:|-----------------:|------------------|---------------------|--------------------|---------------|----------|
| LP-01 | Yes | No | — | Path truth only | — | — | Ready for final copy (labels) after language approval |
| LP-02 | Yes | No | Optional preview | — | — | — | Ready for final copy (headline structure) — no CIP/ROI |
| LP-03 | Yes | No | — | — | — | — | Ready for final copy |
| LP-04 | Yes | No | — | — | — | — | Ready for final copy |
| LP-05 | Yes | No | — | — | — | — | Ready for final copy (outline labels) |
| LP-06 | Yes | No | Storefront widget shots | Install self-serve overclaim | — | — | **Requires evidence capture** |
| LP-07 | Yes | No | Journey/state shots | Provider/Meta readiness | — | — | **Requires evidence capture** + **operational verification** |
| LP-08 | Yes | No | Current Home/Workspace/carts | — | Face freshness | — | **Requires evidence capture** |
| LP-09 | Yes | No | Knowledge cards / findings | Empty-state risk | Reality Validation | — | **Requires Reality Validation** (+ capture or labeled illustrative) |
| LP-10 | Yes | No | Depends on LP-08/09 | — | CL-18 traffic/conversion | — | Ready with disclosure / after evidence chain |
| LP-11 | Yes | No | — | — | Modality lock | — | Ready for final copy (conditional language) |
| LP-12 | Yes | No | Optional purchase-stop proof | — | Recommendation gating | Absolute privacy | Ready with disclosure; legal if absolute claims |
| LP-13 | Yes | No | — | Zid ops-gate wording | **Revalidate platforms** | Logo permissions | **Requires integration readiness verification** |
| LP-14 | Yes (categories) | No | Per answer | Per answer | Per answer | Privacy FAQ | Deferred final answers — then per-claim gates |
| LP-15 | Yes | No | — | Demo path absent | — | — | Ready for final copy (signup/login only); Demo deferred |
| LP-16 | Yes | No | — | — | — | Privacy/Terms pages | Requires legal review for legal links |

**Decision vocabulary used:** Ready for final copy · Ready with disclosure · Requires evidence capture · Requires Reality Validation · Requires operational verification · Requires legal review · Deferred

No section is “final copy ready” in the sense of authorised publication — architecture readiness ≠ publication approval.

---

## 4. Cross-check against Truth / Visual Evidence / Disclosure

| Law | Matrix enforcement |
|-----|-------------------|
| Truth Policy | CL-33, CL-35 blocked; no fake metrics |
| Visual Evidence Law | CL-06…CL-14 require capture beside primary evidence |
| Landing Disclosure Law | CL-32 blocked; CL-03 foreshadow only; CL-15 at LP-09 |
| Calm CTA | CL-30 Demo blocked; CL-28/29 only |
| Screenshot Policy | Capture rows require recognisable real UI |

---

## 5. Update rule

Before final copy approval:

1. Re-run integration readiness (CL-23…CL-26).  
2. Confirm WA operational gates (CL-08).  
3. Confirm Knowledge Reality Validation (CL-15, CL-18, CL-21).  
4. Confirm perf evidence before any speed claim (CL-31).  
5. Flip **Allowed Now** only via documented matrix update — not silent copy improvisation.
