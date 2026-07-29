# Landing Page Evidence Readiness V1

**Status:** Governed evidence-readiness and product-proof report.  
**Date (UTC):** 2026-07-29  
**Governing authorities:**  
- Landing Page Constitution V1  
- Landing Page Information Architecture V1  
- Landing Page Copy Architecture V1  

**Non-goals:** No redesign. No final Arabic copy. No wireframes. No Figma. No 3D. No screenshot capture/selection. No frontend/UI change.

### Separation law (binding)

```text
Capability existence
        ≠
Operational readiness
        ≠
Merchant-visible proof
        ≠
Landing-page publication readiness
```

A claim is landing-eligible only when evidence is: **Real · Current · Merchant-visible · Understandable · Truthful · Reproducible · Publication-safe.**

Code, local tests, docs, demos, and Figma are **not** sufficient alone.

---

## 0. Evidence level model (binding)

| Level | Name | Landing use |
|-------|------|-------------|
| **E0** | No Evidence | Forbidden |
| **E1** | Documentation Evidence | Not sufficient for product claims |
| **E2** | Engineering Evidence | Not sufficient alone |
| **E3** | Operational Evidence | May support operational claims after verification |
| **E4** | Merchant-Visible Product Evidence | Eligible for visual evidence after freshness/truth review |
| **E5** | Validated Reality Evidence | Strongest product-proof level |
| **E6** | Commercially Publishable Evidence | Approved for publication |

**Finding:** As of this report, **no landing claim family has reached E6**. Highest clusters are **E4–E5** for dashboard/decision/knowledge **merchant surfaces** (with capture/freshness gates) and **E3** for widget/WA ops.

---

## 1. Contradiction log

| ID | Finding |
|----|---------|
| CX-ER-01 | None vs Constitution / IA / Copy Architecture. Copy Architecture Claim Matrix Allowed Now flags are **confirmed or tightened** by this audit (not contradicted). |

---

## 2. Section readiness LP-01 … LP-16

### LP-01 — Navigation

| Field | Value |
|-------|-------|
| **Section Responsibility** | Orientation + one calm begin path |
| **Required Proof** | Brand present; `/signup` and `/login` work |
| **Current Evidence** | Routes implemented; landing links exist |
| **Evidence Location** | `routes/merchant_auth.py`; `templates/cartflow_landing.html` |
| **Evidence Type** | Commercial Path Evidence |
| **Evidence Freshness** | Current |
| **Merchant Visibility** | Yes (public pages) |
| **Validation Status** | Path existence verified in code |
| **Publication Status** | Labels publishable after language approval |
| **Required Disclosure** | None for nav itself |
| **Primary Blocker** | None for paths |
| **Decision** | **Publication-ready** (utility) — final wording still unauthorised by Copy Architecture STOP |

---

### LP-02 — Hero

| Field | Value |
|-------|-------|
| **Section Responsibility** | Problem-first attention |
| **Required Proof** | Problem recognition (copy); optional restrained product preview |
| **Current Evidence** | Problem claim needs no product shot; preview candidates exist only as stale landing ops crops or newer dashboard packs not yet landing-approved |
| **Evidence Location** | Copy Architecture CL-01…03; optional later CAP-01 |
| **Evidence Type** | Problem / Commercial Path; optional Product UI |
| **Evidence Freshness** | N/A for text; preview not E6 |
| **Merchant Visibility** | N/A for problem frame |
| **Validation Status** | Problem framing OK; preview not publication-ready |
| **Publication Status** | Bounded problem + recovery-opportunity claims only |
| **Required Disclosure** | Opportunity ≠ confirmed revenue; no CIP/AI/ROI |
| **Primary Blocker** | Product preview not capture-approved |
| **Decision** | **Ready with disclosure** (message); preview = **Ready after fresh capture** |

---

### LP-03 — Problem Recognition

| Field | Value |
|-------|-------|
| **Section Responsibility** | Expand problem beyond abandoned cart |
| **Required Proof** | Merchant-recognisable situations (illustrative OK if labeled) |
| **Current Evidence** | Conceptual + Living Store reason mixes (shipping etc.) — not required as product UI |
| **Evidence Location** | Copy Architecture; Living Store reports (supporting only) |
| **Evidence Type** | Illustrative Evidence (default) |
| **Evidence Freshness** | N/A |
| **Merchant Visibility** | Situations are narrative |
| **Validation Status** | No fake stats |
| **Publication Status** | Illustrative situations allowed; stats blocked |
| **Required Disclosure** | Label illustrative if not single-store proof |
| **Primary Blocker** | None if no metrics |
| **Decision** | **Illustrative only** (situations) / **Ready with disclosure** |

---

### LP-04 — Recovery Limitation Reframe

| Field | Value |
|-------|-------|
| **Section Responsibility** | Action ≠ understanding |
| **Required Proof** | Conceptual contrast only |
| **Current Evidence** | Constitution + IA + product philosophy |
| **Evidence Location** | Governance packs |
| **Evidence Type** | Trust/Governance (conceptual) |
| **Evidence Freshness** | Current |
| **Merchant Visibility** | N/A |
| **Validation Status** | N/A |
| **Publication Status** | Conceptual OK; no superiority metrics |
| **Required Disclosure** | Do not attack competitors |
| **Primary Blocker** | None |
| **Decision** | **Publication-ready** (conceptual reframe) — wording still gated by language approval |

---

### LP-05 — How CartFlow Works

| Field | Value |
|-------|-------|
| **Section Responsibility** | Connected journey outline |
| **Required Proof** | Outline aligns with real product layers (not deep proof) |
| **Current Evidence** | Widget → recovery → WA → movement/purchase → knowledge path exists in product |
| **Evidence Location** | SYSTEM_SUMMARY; widget runtime; recovery; Purchase Truth; KL/ORV |
| **Evidence Type** | Engineering + Operational (outline) |
| **Evidence Freshness** | Current as architecture |
| **Merchant Visibility** | Outline is conceptual |
| **Validation Status** | Outline truthful at E2–E3 |
| **Publication Status** | Outline OK; depth deferred to LP-06…09 |
| **Required Disclosure** | Not a technical diagram; insufficient-evidence step allowed |
| **Primary Blocker** | None for outline |
| **Decision** | **Ready with disclosure** |

---

### LP-06 — Widget Evidence

| Field | Value |
|-------|-------|
| **Section Responsibility** | Early in-store hesitation understanding |
| **Required Proof** | Storefront tool UI + real reason choices + calm intervention — **not settings** |
| **Current Evidence** | V2 runtime production path; reason API; visual-gate demo/storefront flow PNGs (2026-06 audit); landing shows **settings** only |
| **Evidence Location** | `static/cartflow_widget_runtime/*`; `scripts/_production_visual_gate_out/`; `static/img/landing/widget_settings.png` (**ineligible**) |
| **Evidence Type** | Customer Journey / Product UI |
| **Evidence Freshness** | Landing settings **stale / wrong surface**; visual-gate not landing-approved E6 |
| **Merchant Visibility** | Yes in product; **No** truthful landing asset |
| **Validation Status** | Engine E3; landing publish blocked |
| **Publication Status** | **Not claimable on landing until fresh storefront capture** |
| **Required Disclosure** | Not all visitors interact; not mind-reading |
| **Primary Blocker** | Missing publication-safe storefront capture (incl. mobile) |
| **Decision** | **Ready after fresh capture** |

---

### LP-07 — WhatsApp Journey Evidence

| Field | Value |
|-------|-------|
| **Section Responsibility** | Continuation layer with states — not WA-sender identity |
| **Required Proof** | Journey states; reply/follow-up; return/purchase; suppression after purchase; not bulk blast |
| **Current Evidence** | Engine + Purchase Truth tests/ops; merchant `#communication` / messages; Meta often production-blocked; Twilio ops-gated; landing = **settings** |
| **Evidence Location** | Purchase Truth docs/tests; `merchant_app.html` communication; `integration_health_v1.py`; landing `whatsapp_settings.png` (**ineligible for journey**) |
| **Evidence Type** | Operational + Customer Journey + Product UI |
| **Evidence Freshness** | Settings landing stale; merchant UI current |
| **Merchant Visibility** | Partial (merchant states yes; customer-thread journey weak for landing) |
| **Validation Status** | Ops verification required for provider wording |
| **Publication Status** | Bounded continuation + purchase-stop only after capture + ops verify |
| **Required Disclosure** | Provider/activation gates; no delivery/reply guarantees; Meta not fully self-serve |
| **Primary Blocker** | Journey-grade capture + provider readiness wording |
| **Decision** | **Requires operational verification** (+ **Ready after fresh capture**) |

---

### LP-08 — Dashboard Evidence

| Field | Value |
|-------|-------|
| **Section Responsibility** | Merchant sees attention, recovery, movement, clarity |
| **Required Proof** | Current Home and/or Workspace / carts — coherent, no fake KPIs |
| **Current Evidence** | Strong prod packs 2026-07-25…29 (Home V2, Workspace Simplification, carts, communication); landing crops **2026-05-31** stale |
| **Evidence Location** | `docs/product/decision_workspace_simplification_v1/`; `home_constitution_v2/`; `executive_control_v1/`; landing `static/img/landing/*` (**stale**) |
| **Evidence Type** | Product UI Evidence |
| **Evidence Freshness** | Product packs **current**; landing assets **not** |
| **Merchant Visibility** | Yes |
| **Validation Status** | Surfaces CEO-review evolving; use approved current faces only |
| **Publication Status** | Eligible surfaces identified; capture not executed |
| **Required Disclosure** | Demo/Living Store data only; no real PII |
| **Primary Blocker** | Fresh landing-grade capture from eligible surfaces |
| **Decision** | **Ready after fresh capture** |

**Eligible surfaces (not final selection):** Home (`#home`) · Decision Workspace Simplification face (`#workspace`) · Carts operational clarity (`#carts`) · Communication status (`#communication`).  

**Blocked for LP-08:** Settings pages · WhatsApp settings · developer/test routes · empty Home presented as intelligence · stale May 2026 landing crops.

---

### LP-09 — Knowledge Layer Discovery

| Field | Value |
|-------|-------|
| **Section Responsibility** | Earn broader identity via evidence-backed understanding |
| **Required Proof** | Governed patterns + evidence state + insufficient honesty; no fabrication |
| **Current Evidence** | ORV V1 Completed & Released; Home findings/empty states; synthesis/findings engines; landing has **no** knowledge imagery |
| **Evidence Location** | `docs/product/observation_reality_validation_v1/`; admission bridge empty/after shots; Claim Matrix CL-15/18 |
| **Evidence Type** | Reality Validation + Product UI |
| **Evidence Freshness** | ORV 2026-07-24; materialisation empty-state risk remains |
| **Merchant Visibility** | Yes when materialised; often empty without bridge/EXECUTE |
| **Validation Status** | Theme-level RV still required for specific landing themes |
| **Publication Status** | Principle of insufficient evidence: bounded; pattern themes: gated |
| **Required Disclosure** | Illustrative label if not natural store state; no always-on intelligence |
| **Primary Blocker** | Theme Reality Validation + knowledge capture with evidence state visible |
| **Decision** | **Requires Reality Validation** (themes); insufficient-evidence principle = **Ready with disclosure** |

---

### LP-10 — Decision Value

| Field | Value |
|-------|-------|
| **Section Responsibility** | Understanding → practical decisions |
| **Required Proof** | Attention; observation≠conclusion; suppress weak recommendations; traffic vs conversion only if validated |
| **Current Evidence** | Workspace Simplification + Home Top Decision show attention + wait/no-action when evidence weak |
| **Evidence Location** | `decision_workspace_simplification_v1/prod_shots_meta.json`; Home diagnosis language |
| **Evidence Type** | Product UI + Trust/Governance |
| **Evidence Freshness** | 2026-07-29 packs |
| **Merchant Visibility** | Yes |
| **Validation Status** | Attention/suppress: strong; traffic vs conversion: **not** LP-validated |
| **Publication Status** | Selective outcomes only |
| **Required Disclosure** | Does not run the store; no ROI |
| **Primary Blocker** | CL-18 traffic/conversion; capture for CAP-14 |
| **Decision** | **Ready with disclosure** (bounded outcomes); traffic/conversion = **Requires Reality Validation** |

---

### LP-11 — Continuous Value Journey

| Field | Value |
|-------|-------|
| **Section Responsibility** | Value accumulates with evidence over time |
| **Required Proof** | Continuity without fake charts / auto-ML |
| **Current Evidence** | Living Store / SRS historical simulation → real tables → Home (lab), not organic multi-merchant longitudinal pack |
| **Evidence Location** | `living_store_reality_v1/`; ORV SRS; Claim CL-20 |
| **Evidence Type** | Reality Validation Evidence (lab) / Illustrative |
| **Evidence Freshness** | Lab current; not commercial longitudinal |
| **Merchant Visibility** | Indirect |
| **Validation Status** | Simulation ≠ E6 continuity |
| **Publication Status** | Conceptual + conditional language; no fake time-series |
| **Required Disclosure** | Conditional modality; not “gets smarter automatically” |
| **Primary Blocker** | No E6 continuity visual |
| **Decision** | **Illustrative only** / conceptual **Ready with disclosure** |

---

### LP-12 — Trust and Governance

| Field | Value |
|-------|-------|
| **Section Responsibility** | Restraint in merchant language |
| **Required Proof** | Insufficient stated; purchase stop; observation≠conclusion; isolation bounded |
| **Current Evidence** | UI insufficient/wait language; Purchase Truth; store isolation tests; absolute privacy unproven legally |
| **Evidence Location** | Workspace/Home copy; purchase truth tests; `test_recovery_isolation.py` |
| **Evidence Type** | Trust/Governance + Operational |
| **Evidence Freshness** | Current behaviours |
| **Merchant Visibility** | Partial (principles visible in product; landing visuals weak) |
| **Validation Status** | Behavioural yes; legal absolutes no |
| **Publication Status** | Bounded trust principles OK; absolute privacy blocked |
| **Required Disclosure** | No enterprise/military seals; no absolute privacy |
| **Primary Blocker** | Legal for absolute claims; optional CAP-06 for stop proof |
| **Decision** | **Ready with disclosure**; absolute isolation slogans = **Requires legal review** |

---

### LP-13 — Integration Readiness

| Field | Value |
|-------|-------|
| **Section Responsibility** | Truthful platform states |
| **Required Proof** | Revalidated Zid / Salla / Shopify status |
| **Current Evidence** | Zid production path ops-gated (snippet/OAuth); Salla/Shopify `adapter_scaffold_only` in `integration_health_v1.py`; no platform logo assets |
| **Evidence Location** | `services/integration_health_v1.py`; `zid_partner_widget_snippet_v1.md`; Claim CL-23…26 |
| **Evidence Type** | Integration Evidence |
| **Evidence Freshness** | Revalidated this audit (2026-07-29) |
| **Merchant Visibility** | Settings connection UI (Zid) |
| **Validation Status** | Confirmed |
| **Publication Status** | Text readiness only |
| **Required Disclosure** | Zid may need operational activation |
| **Primary Blocker** | None for text states; logos not claimable |
| **Decision** | **Ready with disclosure** (text); logos = **Not claimable** |

| Platform | Decision |
|----------|----------|
| Zid | **Currently supported** (ops-gated) |
| Salla | **Planned** |
| Shopify | **Planned** |

---

### LP-14 — FAQ

| Field | Value |
|-------|-------|
| **Section Responsibility** | High-value objections |
| **Required Proof** | Per-answer evidence (see Claim Gate) |
| **Current Evidence** | Categories defined in Copy Architecture; answers not written |
| **Evidence Location** | Copy Architecture FAQ contracts |
| **Evidence Type** | Mixed |
| **Evidence Freshness** | N/A |
| **Merchant Visibility** | N/A |
| **Validation Status** | Per claim |
| **Publication Status** | Answers blocked until claim gates pass |
| **Required Disclosure** | Per answer |
| **Primary Blocker** | Speed FAQ; WA activation; self-serve; privacy |
| **Decision** | **Deferred** (final answers); architecture ready |

---

### LP-15 — Final CTA

| Field | Value |
|-------|-------|
| **Section Responsibility** | Calm next step |
| **Required Proof** | `/signup` `/login`; no Demo path; free/beta honesty |
| **Current Evidence** | Auth routes work; Demo booking **absent**; landing already says free/beta |
| **Evidence Location** | `routes/merchant_auth.py`; Claim CL-28…30 |
| **Evidence Type** | Commercial Path Evidence |
| **Evidence Freshness** | Current |
| **Merchant Visibility** | Yes |
| **Validation Status** | Verified |
| **Publication Status** | Start Free + Login only |
| **Required Disclosure** | Not instant production activation; beta/pilot honesty if “free” |
| **Primary Blocker** | Demo deferred; overpromising activation |
| **Decision** | **Ready with disclosure** (signup/login); Demo = **Not claimable** |

---

### LP-16 — Footer

| Field | Value |
|-------|-------|
| **Section Responsibility** | Contact / legal / verify |
| **Required Proof** | Real contact; privacy/terms pages; no fake location |
| **Current Evidence** | `mailto:support@smartreplyai.net` exists; **no** Privacy/Terms routes found; no fake office on landing |
| **Evidence Location** | `templates/cartflow_landing.html`; route grep empty for privacy/terms |
| **Evidence Type** | Legal Evidence / Commercial Path |
| **Evidence Freshness** | Contact current; legal pages missing |
| **Merchant Visibility** | Contact yes |
| **Validation Status** | Legal pages fail |
| **Publication Status** | Contact only until legal pages exist |
| **Required Disclosure** | Do not claim Privacy/Terms links until real |
| **Primary Blocker** | Missing Privacy/Terms |
| **Decision** | Contact = **Publication-ready**; Privacy/Terms = **Requires legal review** |

---

## 3. Executive table

| Section | Required Evidence | Highest Current Level | Publication Ready | Capture Ready | Validation Needed | Main Blocker | Decision |
|---------|-------------------|----------------------:|------------------:|--------------:|------------------:|--------------|----------|
| LP-01 | Commercial paths | E4 | Yes (utility) | N/A | No | — | Publication-ready |
| LP-02 | Problem + optional preview | E4 paths / E1 preview | Bounded text | CAP-01 later | No | Preview not E6 | Ready with disclosure |
| LP-03 | Situations | E1–E3 lab | Illustrative | Optional | No fake stats | — | Illustrative only |
| LP-04 | Conceptual reframe | E1 | Conceptual | N/A | No | — | Publication-ready (conceptual) |
| LP-05 | Journey outline | E3 | Outline | N/A | No | Depth elsewhere | Ready with disclosure |
| LP-06 | Storefront widget | E3 | No | Plan ready | Soft | Settings-only landing | Ready after fresh capture |
| LP-07 | WA journey + ops | E3 | No | Plan ready | Ops | Settings + provider gates | Requires operational verification |
| LP-08 | Current dashboard | E5 packs / E1 landing | No | **Yes** (sources exist) | Face freshness | Stale landing assets | Ready after fresh capture |
| LP-09 | Knowledge + states | E5 ORV / E1 landing | Bounded principle | Plan ready | **Yes** themes | Theme RV + empty risk | Requires Reality Validation |
| LP-10 | Decision outcomes | E5 face | Bounded | CAP-14 | Traffic/conversion | CL-18 | Ready with disclosure |
| LP-11 | Continuity | E3 lab | Conceptual | Optional | Longitudinal | No E6 continuity | Illustrative / disclosure |
| LP-12 | Trust behaviours | E4 UI | Bounded | CAP-06 optional | Legal absolutes | Absolute privacy | Ready with disclosure |
| LP-13 | Platform states | E3 Zid / E1 others | Text yes | CAP-16 text | Revalidate at copy time | Logos | Ready with disclosure |
| LP-14 | FAQ answers | Mixed | No | Per answer | Per answer | Multiple | Deferred |
| LP-15 | Signup/Login | E4 | Bounded | N/A | No | Demo absent | Ready with disclosure |
| LP-16 | Legal/contact | E1–E4 | Contact only | N/A | Legal pages | Privacy/Terms missing | Requires legal review (pages) |

---

## 4. Copy readiness consequence

| Section | Future copywriting authorisation |
|---------|----------------------------------|
| LP-01 | **Final copy may begin** (labels) |
| LP-02 | **Final copy may begin with bounded claims** (no CIP/ROI; preview placeholder OK) |
| LP-03 | **Final copy may begin with bounded claims** (no stats) |
| LP-04 | **Final copy may begin** |
| LP-05 | **Final copy may begin with bounded claims** (outline only) |
| LP-06 | **Final copy blocked pending evidence** (capture) |
| LP-07 | **Final copy blocked pending operational verification** (+ capture) |
| LP-08 | **Final copy may begin with placeholders** (captions after capture) |
| LP-09 | **Final copy blocked pending Reality Validation** for themes; principle lines may begin bounded |
| LP-10 | **Final copy may begin with bounded claims** (exclude traffic/conversion until RV) |
| LP-11 | **Final copy may begin with bounded claims** (conditional only) |
| LP-12 | **Final copy may begin with bounded claims**; absolute privacy **blocked pending legal review** |
| LP-13 | **Final copy may begin with bounded claims** after revalidation at copy time |
| LP-14 | **Final copy blocked** (answers) until per-claim gates |
| LP-15 | **Final copy may begin with bounded claims** (signup/login; no Demo) |
| LP-16 | **Final copy may begin** for contact; legal links **blocked pending legal review** |

**Release note:** “Final copy may begin” means **authorised to draft under Copy Architecture** — **not** authorised to publish on production landing.

---

## 5. Cross-system review

| Lens | Assessment |
|------|------------|
| Evidence vs documentation | LP-04/05 partly E1 — allowed only as conceptual, not as capability proof |
| Evidence vs implementation | Widget/WA/Knowledge code ≠ landing publishability |
| Evidence vs operations | WA Meta often blocked; Twilio/Zid ops-gated — must disclose |
| Evidence vs UI | Strongest gap: landing still shows **settings**; product has current Home/Workspace |
| Evidence vs Reality Validation | ORV released helps LP-09/10; theme claims still gated |
| Evidence vs marketing | Current production landing exceeds Visual Evidence Law (settings as product) — future page must not |
| Evidence freshness | Landing PNGs 2026-05-31 vs Simplification 2026-07-29 — **stale** |
| Mobile evidence | Merchant mobile packs exist; **storefront widget mobile pack missing** |
| Privacy | Capture must use demo/synthetic only — rules in Capture Plan |
| Commercial honesty | Signup yes; instant activation no; Demo no |
| Visual hierarchy | Product screenshots = proof; 3D never proof |

---

## 6. Approval

See pack README STOP gate. Completing this report does **not** authorise redesign, copy publication, screenshot capture, or implementation.
