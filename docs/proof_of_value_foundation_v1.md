# CartFlow Proof of Value Foundation V1

**Status:** Ratified baseline — the official commercial proof standard for CartFlow  
**Date (UTC):** 2026-07-04  
**Scope:** Defines **what CartFlow may claim**, **how value is measured**, and **how value is presented** — not how features are built or designed  
**Authority:** This document is the **commercial counterpart** to [`engineering_constitution_v1.md`](engineering_constitution_v1.md). Where merchant-facing claims and this document disagree, this document wins (until formally amended per §10).  
**Audience:** Product, commercial, engineering, and operations — anyone who surfaces value to merchants or buyers  

**Explicitly out of scope:** Implementation, dashboard UI design, marketing copy, migrations, refactors.

**Canonical inputs (do not extend beyond demonstrated evidence):**

| Document | Role |
|----------|------|
| [`cartflow_value_validation_foundation_v1.md`](cartflow_value_validation_foundation_v1.md) | Why merchants pay; value domains; proof categories; daily brief contract |
| [`merchant_value_audit_v1.md`](merchant_value_audit_v1.md) | Current merchant value maturity (**Level 1 Working**); gaps; audit baseline |
| [`SYSTEM_SUMMARY.md`](SYSTEM_SUMMARY.md) | Shipped surfaces, truth layers, engineering foundation status |

> **Note on intent:** This document **formalizes proof discipline CartFlow already practices internally** (Purchase Truth, KL-C2 attribution honesty, LT-C1, Provider Truth separation, VIP lane isolation) and **extends it to merchant-visible claims**. It does not invent new merchant value — it governs how existing and future value may be **proven**.

---

## Executive summary

CartFlow's engineering constitution defines **how truth is built**. This foundation defines **how truth becomes merchant-trustable proof**.

Merchants pay for outcomes — recovered revenue, understanding, confident decisions, operational trust. Proof of Value is the permanent framework that ensures every claim, metric, insight, and recommendation is **evidence-backed**, **confidence-labelled**, and **commercially honest**.

**Current baseline (Merchant Value Audit V1):** CartFlow delivers **Working** outcomes in pilot (automation, lifecycle, reasons, VIP) but **cannot yet prove** attributed ROI, delivery-backed recovery, or daily decision closure at **Level 2 Proven**. This foundation governs the path from Level 1 → Level 2+ without repeating the engineering-first pattern.

---

## Section 1 — Proof Philosophy

Permanent principles. Ordered — earlier principles constrain later ones.

### 1.1 Truth Before Claims

No merchant-visible statement may precede its governing truth layer. Purchase, lifecycle, provider, and recovery questions must be answered by owned evidence before any KPI, headline, or success story is shown.

*Precedent:* KL-C2 removed misleading recovery purchase counts; Purchase Truth closed before recovery stop; LT-C1 CI gate before lifecycle-dependent UX.

**It is failing when:** Dashboard copy, marketing, or insights assert outcomes the truth layer does not support.

### 1.2 Evidence Before Marketing

Commercial language, tier packaging, and sales narratives must trace to proof contracts (§4) and evidence hierarchy (§3). Feature lists are not proof.

*Precedent:* Landing page policy «no fake ROI» (`SYSTEM_SUMMARY.md` §1); Merchant Value Audit forbids «guaranteed recovered revenue» demonstrations.

**It is failing when:** Starter/Growth/Pro tier bullets promise proof categories the audit marks **Future** or **Not Ready**.

### 1.3 Proof Before Intelligence

Intelligence (Knowledge Layer, future Decision Engine, Product Intelligence) may **compose and explain** evidence — never **substitute** for it. Patterns without primary truth are hypotheses, not merchant proof.

*Precedent:* KL v1 closed as read-only composition from operational tables; KL-C3 product bridge reads foundation health only — no parallel truth writes.

**It is failing when:** An insight card, ranking, or recommendation appears without identifiable primary evidence and confidence level.

### 1.4 Measured Before Estimated

Merchant-visible metrics use **defined denominators**, **owned computation paths**, and **honest insufficient-data states**. Estimates, projections, and industry benchmarks are not merchant KPIs unless explicitly labelled non-proof.

*Precedent:* Provider Reliability metrics require denominators; Operational Metrics V1 rejects bare counts as KPIs; attribution module uses conservative confidence levels (`purchase_attribution_v1.py`).

**It is failing when:** «Recovered revenue» is shown without attribution evidence, or rates appear without stated numerator/denominator.

### 1.5 Merchant Trust Before Growth

Growth motions (upsell, referral, expansion pricing) must not outrun provable value. A withheld claim preserves more trust than an inflated one.

*Precedent:* Merchant Value Audit — **Not Ready** for referral-grade ROI; Value Validation Foundation anti-patterns (fake counters, guaranteed ROI).

**It is failing when:** Renewal or upsell depends on claims the merchant cannot verify in-product.

### 1.6 Prime directive

> **Every merchant-visible proof must strengthen trust through evidence — and must not silently weaken it for growth convenience.**

Deliberate trade-offs (e.g. showing partial proof with **Medium** confidence while foundation matures) require explicit confidence labelling per §7 — not omission.

---

## Section 2 — Proof Domains

Five permanent proof domains. Every merchant-visible claim belongs to **one primary domain**. Secondary domains allowed when evidence supports both.

### 2.1 Recovery Proof

| Field | Definition |
|-------|------------|
| **Purpose** | Prove that CartFlow recovery actions contributed to measurable commerce outcomes |
| **Merchant benefit** | Answer «Did CartFlow bring money back?» and «Did recovery efforts work?» with honest attribution |
| **Required evidence** | Recovery Truth (schedule, send, reply chain) + Purchase Truth for outcomes; Provider Truth when claiming message **reached** customer; attribution path for **attributed** revenue (KL-C2 / `purchase_attribution_v1`); VIP lane isolated (KL-C4) |

**Audit baseline:** Automation **Working**; attributed SAR and delivery-backed recovery **Future** for merchant surfaces.

### 2.2 Understanding Proof

| Field | Definition |
|-------|------------|
| **Purpose** | Prove the merchant understands customers, patterns, and cart state — not merely counts |
| **Merchant benefit** | Answer «Why are customers leaving?», «Who is stuck?», «What changed?» with explanatory evidence |
| **Required evidence** | Lifecycle Truth (LT-C1) for per-cart state; captured reasons (`CartRecoveryReason`); Behavior Truth signals where governed (return tracker — partial today); Knowledge Layer composition when coverage sufficient (KL health); Product Truth when product claims are made (foundation exists — merchant surfacing **Future**) |

**Audit baseline:** Lifecycle block **Confirmed**; weekly reasons + KL **Partial**; product-level **Future**.

### 2.3 Decision Proof

| Field | Definition |
|-------|------------|
| **Purpose** | Prove the merchant knows what to do next — with eligible action or explicit acceptable inaction |
| **Merchant benefit** | Answer «What should I do first?», «Does this need me?», «What if I do nothing?» |
| **Required evidence** | Lifecycle `merchant_needed` + next-action copy; eligible action matrix (archive/reopen/VIP alert documented — normal-carts executable actions **gap**); Daily Brief contract (3–5 items, what/why/action); inaction consequence when automation continues or stops |

**Audit baseline:** Decision Proof **weakest** (~Level 0–1); composite decision confidence **C−**.

### 2.4 Operational Proof

| Field | Definition |
|-------|------------|
| **Purpose** | Prove the platform, integrations, and dashboard data are working and trustworthy |
| **Merchant benefit** | Answer «Is my store set up?», «Is WhatsApp/widget working?», «Can I trust this number?» |
| **Required evidence** | Integration Truth (onboarding reality, store connection, widget configuration trust, storefront runtime truth gate); Read Model Truth (snapshot freshness, stale visibility when implemented); Provider Truth for send disposition; Operational Metrics for internal ownership — merchant surfacing **Partial** |

**Audit baseline:** Setup journey **Partial**; freshness contract **not merchant-visible**; ops metrics **admin/dev only** today.

### 2.5 Commercial Proof

| Field | Definition |
|-------|------------|
| **Purpose** | Prove that CartFlow's **priced promise** matches **demonstrable merchant outcomes** for a tier and motion |
| **Merchant benefit** | Answer «Is this plan worth it?» without marketing inflation |
| **Required evidence** | Composite of Recovery + Understanding + Decision + Operational proof **scoped to tier** (Value Validation §7.2); explicit **Not Ready** classification where proof absent; no billing claim without payment truth (billing **Future** — SaaS Phases 1–4 visual only) |

**Audit baseline:** Pilot demonstration **Ready**; ROI/referral/Pro intelligence **Not Ready**; tier claims partially ahead of proof.

---

## Section 3 — Evidence Hierarchy

Acceptable evidence sources, **strictly ordered**. Lower layers may **compose** upper layers — never **override** them.

```
Tier 0 — Primary truth (single owners, engineering-governed)
├── Purchase Truth      — PurchaseTruthRecord; platform webhook > reply > return
├── Lifecycle Truth     — LT-C1; customer_lifecycle_states_v1 (mint once)
├── Provider Truth      — Provider Reliability reconciliation; acceptance ≠ delivery
├── Recovery Truth      — RecoverySchedule, CartRecoveryLog, durable send chain
└── Widget Truth        — public-config parity, widget-seen beacon, configuration trust RC1–RC7

Tier 1 — Derived truth (read-only composition; no parallel writes)
├── Behavior Truth      — return tracker, reason capture, cart events (partial; future governed)
├── Product Truth       — cart line snapshots, catalog, hesitation/purchase mappings (foundation closed; merchant **Future**)
├── Integration Truth   — integration_health_v1, onboarding reality (admin-merchant partial)
└── Read Model Truth    — dashboard snapshots, read observability, freshness contracts

Tier 2 — Intelligence (patterns over evidence)
└── Knowledge Layer     — knowledge_layer_v1; KL-C1..C4; /api/knowledge/report + /health

Tier 3 — Explanation (narration only)
└── AI Explanation      — copy generation, summarization; must cite Tier 0–2 sources

Tier 4 — Presentation (display only)
└── Presentation        — dashboard copy, cards, charts, briefs, reports
```

### 3.1 Hierarchy rules

| Rule | Meaning |
|------|---------|
| **R-1** | Presentation **never creates** evidence. UI labels, charts, and marketing strings are not sources of truth. |
| **R-2** | AI Explanation **never creates** evidence. Generated text must map to Tier 0–2 identifiers. |
| **R-3** | Knowledge Layer **never mints** primary truth. Insufficient coverage → insufficient-data state (KL health). |
| **R-4** | Intelligence **cannot raise** confidence above its weakest input evidence. |
| **R-5** | Conflicts resolve **upward** — Purchase Truth wins over lifecycle presentation; Provider delivery wins over «sent» copy. |
| **R-6** | VIP lane evidence **must not** pollute normal-lane Recovery Proof (KL-C4). |
| **R-7** | Behavior Truth and Product Truth at **future** maturity must complete governance before merchant **Confirmed** claims. |

### 3.2 Evidence → claim eligibility (summary)

| Claim type | Minimum evidence tier |
|------------|---------------------|
| «Customer purchased» | Purchase Truth + Lifecycle propagation |
| «Recovery attributed purchase» | Purchase Truth + attribution record + defined window |
| «Message delivered» | Provider Truth delivery altitude — not acceptance alone |
| «Cart state X» | Lifecycle Truth (LT-C1) only |
| «Top objection this week» | Knowledge Layer + reason capture coverage |
| «Product X loses sales» | Product Truth + governed aggregation — **not yet merchant-eligible** |
| «Do X now» | Decision Proof contract + eligible action — **partial today** |

---

## Section 4 — Proof Contracts

Permanent contracts **PV-1…PV-18**. Violations are proof defects — classified P0–P3 aligned with engineering risk practice.

### 4.1 Universal contracts

| ID | Contract | Rationale |
|----|----------|-----------|
| **PV-1** | Every merchant-visible claim must be evidence-backed by identifiable Tier 0–2 source(s). | Prevents vanity UI and marketing drift |
| **PV-2** | Recovery **outcome** value requires Purchase Truth for purchase claims; Recovery Truth for action claims. | Outcomes ≠ sends |
| **PV-3** | No attributed revenue without attribution evidence (`purchase_attribution_v1` / KL-C2 path) and stated confidence. | KL-C2 precedent; audit #1 gap |
| **PV-4** | Every recommendation must declare confidence (§7) and proof domain (§2). | Decision Proof integrity |
| **PV-5** | Unknown must remain unknown — never interpolated, never defaulted to success. | Provider «unknown is a state»; KL insufficient-data |
| **PV-6** | Merchant-visible metrics require operational ownership — defined owner module, denominator, refresh contract, and stale behavior. | Mirrors engineering «one source of truth» |
| **PV-7** | Every proof must identify its source — merchant-facing `proof_source` or equivalent trace (recovery_key, purchase_id, correlation_key, insight_id). | Explainability prerequisite |
| **PV-8** | Presentation must not contradict primary truth. | LT-C1 chip must match classifier output |
| **PV-9** | Tier packaging claims must map to proof domains provable at that tier. | Commercial Proof; Pro intelligence **Not Ready** |
| **PV-10** | Rates require denominators; bare counts may appear as context, not as KPI. | Provider Reliability + Operational Metrics precedent |

### 4.2 Recovery Proof contracts

| ID | Contract | Rationale |
|----|----------|-----------|
| **PV-11** | «Sent» or equivalent must not imply **delivered** without Provider Truth delivery evidence. | Acceptance ≠ delivery (Provider Reliability audit) |
| **PV-12** | Recovered revenue (SAR) sums only **attributed** purchases per PV-3; VIP and normal lanes reported separately when both present. | KL-C4 isolation |
| **PV-13** | Recovery effectiveness comparisons (template, reason, timing) require defined cohort, window, and minimum sample — or **Low/Unknown** confidence. | Prevents false «what worked» |

### 4.3 Understanding Proof contracts

| ID | Contract | Rationale |
|----|----------|-----------|
| **PV-14** | Lifecycle explanations must originate from LT-C1 fields — no duplicate classifiers in presentation layer. | LT-C1 enforcement |
| **PV-15** | Pattern insights (KL) must expose coverage inputs from `/api/knowledge/health` when confidence below **High**. | KL health diagnosis codes |
| **PV-16** | Product-linked claims require Product Truth identity tier meeting foundation governance threshold — else **Unknown**. | Product foundation; audit gap |

### 4.4 Decision Proof contracts

| ID | Contract | Rationale |
|----|----------|-----------|
| **PV-17** | Recommended actions must be **eligible** — merchant can execute in-product or via documented path; else downgrade to informational only. | Decision audit **D** on «what should I do» |
| **PV-18** | Daily Brief items (when implemented) must satisfy Value Validation §5.2: what / why / action; max 3–5; one decision per item. | Daily brief contract |

### 4.5 Contract traceability (audit gaps → contracts)

| Merchant Value Audit gap | Governing contracts |
|--------------------------|---------------------|
| No attributed SAR | PV-3, PV-12 |
| «Sent» ≠ delivered | PV-11 |
| Intervention without action | PV-17 |
| No daily brief | PV-18, PV-4 |
| Tier ahead of proof | PV-9 |
| `#completed` semantic overload | PV-8, PV-14 (lifecycle truth in presentation) |

---

## Section 5 — Merchant Proof Surfaces

**Purpose only** — where proof may appear. No UI design. Surfaces must obey §4 contracts and §7 confidence.

| Surface | Primary proof domains | Purpose | Audit status |
|---------|----------------------|---------|--------------|
| **Dashboard — Carts (`#carts`)** | Understanding, Decision (partial) | Per-cart proof: lifecycle block, reason, intervention flag | **Shipped** — strongest Understanding surface |
| **Dashboard — Home Overview (`#home`)** | Understanding, Decision (partial) | Curated insight entry; KL cards; weekly reasons | **Shipped** — partial Daily Brief |
| **Daily Brief** | Decision, Understanding, Recovery, Operational | Max 3–5 ranked items: what / why / action | **Future** — contract defined, not enforced |
| **Recovery Timeline** | Recovery, Understanding | Chronological evidence chain per cart (send, reply, return, purchase) | **Future** — Recovery Truth exists; not merchant timeline |
| **Dashboard — VIP (`#vip`, carts banner)** | Recovery, Decision | High-value proof + merchant alert eligibility | **Shipped** — partial delivery proof |
| **Dashboard — Monthly Summary (`#home-month`)** | Recovery, Understanding | Period proof: wins, patterns, attributed summary when PV-3 satisfied | **Shipped** — partial; attribution **Future** |
| **Dashboard — Store Setup (`#home-setup`)** | Operational, Commercial | Setup completeness proof; go-live readiness | **Shipped** — partial (overstate risk documented) |
| **Dashboard — WhatsApp (`#whatsapp`)** | Operational | Connection/readiness proof; not recovery ROI | **Shipped** — partial |
| **Reports (export / scheduled)** | Recovery, Understanding, Commercial | Durable proof artifacts for merchant records | **Future** |
| **Plans / subscription (`#plans`, `#settings`)** | Commercial | Tier vs provable outcomes alignment | **Shipped** — visual; enforcement off |
| **Future Mobile** | All domains | Same proof contracts; condensed Daily Brief + alerts | **Future** |

### 5.1 Surface rules

1. **One surface, one primary job** — e.g. Setup proves Operational; Monthly Summary proves period Recovery when metrics exist.  
2. **No proof duplication without parity** — same metric on two surfaces must share one owner (mirrors Dashboard Read Model DR-DUP governance).  
3. **Charts are not proof** — trends (`recovery-trend`) require PV-10 denominators and domain classification or they remain contextual only.  
4. **Admin/ops surfaces are not merchant proof** — `/dev/operational-metrics`, admin operations JSON inform **internal** ownership (PV-6), not merchant claims.

---

## Section 6 — Value Metrics

Merchant-visible metrics CartFlow **may** surface when proof contracts are satisfied. Each requires PV-6 ownership definition before merchant display.

### 6.1 Metric registry

| Metric | Proof domain | Definition (merchant meaning) | Required evidence | Justification | Merchant-visible today |
|--------|--------------|--------------------------------|-------------------|---------------|------------------------|
| **Recovered Revenue (SAR)** | Recovery | Sum of purchase value **attributed** to CartFlow recovery within governed window | Purchase Truth + attribution + PV-3/PV-12 | Primary ROI metric; audit #1 gap | **No** — engineering exists |
| **Recovery Conversion Rate** | Recovery | Attributed purchases ÷ recovery-eligible abandons (denominator explicit) | Purchase Truth + Recovery Truth + KL honest counts | Answers «did recovery work?» without inflating | **Partial** — KL internal only |
| **Purchases After Recovery** | Recovery | Count of purchases with any recovery touch (confidence-labelled) | Purchase Truth + attribution confidence levels | Conservative sibling to attributed SAR | **Partial** — lifecycle «تم الشراء» without attribution label |
| **Known Reasons Rate** | Understanding | Share of abandons with captured hesitation reason | CartRecoveryReason + abandon denominator | Proves «why leaving» capture value | **Partial** — weekly distribution, no rate KPI |
| **Lifecycle Coverage** | Understanding | Share of active carts with complete lifecycle block | LT-C1 output on normal-carts rows | Proves decision frame reliability | **De facto high** on `#carts` |
| **VIP Saves Surfaced** | Recovery + Decision | High-value carts flagged + merchant alert attempted | VIP lane + alert logs | Growth tier proof | **Partial** — no delivery proof to merchant |
| **Decision Confidence** | Decision | Composite: share of brief/row items with eligible action + stated inaction | Decision Proof contracts PV-17, PV-18 | Meta-metric for product quality | **Not measured** — audit C− baseline |
| **Operational Confidence** | Operational | Composite: setup truth + integration health + dashboard freshness | Integration Truth + Read Model Truth | Trust to act on dashboard | **Not measured** merchant-facing |
| **Merchant Time Saved** | Decision | Estimated minutes not spent manually scanning carts (proxy or survey) | Instrumentation **Future**; proxy via brief adoption **Future** | Commercial narrative support — never primary ROI | **No** |
| **Message Delivery Rate** | Recovery + Operational | Delivered ÷ accepted sends (provider-scoped) | Provider Truth | PV-11 compliance | **No** — ops only |
| **Setup Readiness Score** | Operational | Weighted checklist from onboarding reality | onboarding_reality_v1 | Store Health proof | **Partial** — setup cards |

### 6.2 Metric rules

1. **No metric without owner** — module + refresh path documented before merchant display.  
2. **No metric without denominator** when expressed as rate (PV-10).  
3. **Insufficient data is a valid metric state** — show «غير كافٍ» not zero.  
4. **Internal and merchant definitions must match** — no marketing number without engineering equivalent.  
5. **Pilot validation before fleet claims** — Value Validation §6.2.

---

## Section 7 — Confidence Model

Every merchant-visible proof carries exactly one confidence level. Confidence **follows evidence** — never AI tone, never UX optimism.

### 7.1 Levels

| Level | Meaning | When to use | Merchant copy pattern (illustrative) |
|-------|---------|-------------|--------------------------------------|
| **Confirmed** | Primary truth directly observed; single owner; no material gap | Purchase Truth terminal; LT-C1 state; captured reason on row | «مؤكد — …» |
| **High** | Primary + derived evidence align; coverage thresholds met (KL health green) | KL insight with strong coverage; attributed purchase at `confirmed_recovery` confidence | «مرتفع — …» |
| **Medium** | Evidence partial; known gaps documented | Pattern with moderate coverage; purchase with weaker attribution tier | «متوسط — …» + gap note |
| **Low** | Directional only; small sample or stale inputs | Early-store KL; few carts in window | «منخفض — …» + «样本 صغير» |
| **Unknown** | Evidence absent, conflicting, or below minimum threshold | No reason captured; delivery undispositioned; product identity tier E | «غير معروف — …» ; **never guess** |

### 7.2 Confidence rules

| Rule | Statement |
|------|-----------|
| **C-1** | Confidence is computed from **weakest link** in evidence chain. |
| **C-2** | AI Explanation **cannot raise** confidence — only restate it (Tier 3). |
| **C-3** | Presentation **cannot raise** confidence — styling must not imply certainty (C-2 extends to color/severity). |
| **C-4** | **Unknown** is mandatory when Provider Truth disposition is unknown — not «pending» framed as success. |
| **C-5** | Downgrade is always allowed; upgrade requires new evidence, not new copy. |
| **C-6** | Recommendations at **Low** or **Unknown** must not use imperative «do now» framing (PV-17). |

### 7.3 Mapping to existing engineering signals

| Engineering signal | Proof confidence |
|--------------------|------------------|
| `PurchaseTruthRecord` + platform webhook | **Confirmed** for purchase |
| `purchase_attribution_v1` → `confirmed_recovery` | **High** for attributed recovery |
| `purchase_attribution_v1` → lower tiers | **Medium** or **Low** per module rules |
| LT-C1 lifecycle fields on row | **Confirmed** for state label |
| KL `/api/knowledge/health` → sufficient coverage | **High** for store-level insight |
| KL stale / missing inputs | **Medium**, **Low**, or **Unknown** per diagnosis |
| `CartRecoveryLog` acceptance without delivery | **Unknown** for «reached customer» — not **Confirmed** |
| Onboarding `self_serve_to_production_ready: False` | Operational claims **Medium** at best for «ready» |

---

## Section 8 — Commercial Integrity

Claims CartFlow **may never make** — regardless of channel (product, sales, marketplace listing, support).

### 8.1 Forbidden claims

| # | Never claim… | Why |
|---|--------------|-----|
| **CI-1** | Recovered revenue totals without PV-3 attribution evidence | Destroys trust permanently; audit Not Ready |
| **CI-2** | Guaranteed ROI or «pays for itself» as promise | Violates Measured Before Estimated |
| **CI-3** | Message «delivered» because status shows sent | PV-11; Provider audit |
| **CI-4** | Product-level loss rankings without Product Truth PV-16 | Foundation not merchant-served |
| **CI-5** | AI-generated explanations as facts | R-2; AI never creates evidence |
| **CI-6** | Hidden uncertainty — omit confidence when below **High** | PV-4, PV-5 |
| **CI-7** | Inflated success — all purchases as recovery wins | KL-C2 fix precedent |
| **CI-8** | Self-serve production-ready when onboarding reality false | Platform readiness evidence |
| **CI-9** | Pro / intelligence tier outcomes not yet at **Partial** proof maturity | PV-9; tier alignment |
| **CI-10** | Referral-worthy ROI stories without merchant-verifiable metric | Merchant Trust Before Growth |

### 8.2 Allowed claim posture (honest pilot)

CartFlow **may** truthfully state in pilot:

- CartFlow captures **why** customers leave when the widget fires  
- Each cart shows **governed lifecycle state** in Arabic  
- Recovery automation **runs** on durable schedules when environment configured  
- VIP carts can **alert the merchant** on high-value abandons  
- Knowledge insights appear when **data coverage is sufficient** — with confidence  
- Purchase outcomes **stop recovery** and appear as «تم الشراء»  

### 8.3 Tier integrity matrix (current baseline)

| Tier | May claim (proof-backed) | Must not claim yet |
|------|--------------------------|-------------------|
| **Starter (99 SAR)** | Reason capture; automated recovery; cart visibility; lifecycle understanding | Attributed ROI; product intelligence |
| **Growth (199 SAR)** | + VIP prioritization; weekly patterns (KL when coverage OK) | Advanced analytics as proven ROI; delivery proof |
| **Pro (399 SAR)** | + early access framing only with explicit **preview / partial** label | Operational insights; decision engine; product intelligence as **Confirmed** |

---

## Section 9 — Roadmap Alignment

How **future domains** strengthen proof — without replacing Tier 0 evidence. None may skip to merchant **Confirmed** claims without governance.

| Future domain | Strengthens proof domain | How (purpose only) | Prerequisite |
|---------------|-------------------------|--------------------|--------------|
| **Proof of Value implementation** | All | Surfaces metrics §6 on merchant proof surfaces §5 under PV contracts | This foundation ratified |
| **Behavior Truth** | Understanding, Decision | Governed timeline (return, hesitate, engage) → Recovery Timeline surface; return-as-decision | Movement foundation governance |
| **Merchant Understanding** | Decision, Commercial | Priority rank calibrated to merchant behavior — not generic | Behavior Truth + proof metrics |
| **Knowledge Layer V2+** | Understanding | Deeper patterns with product linkage; still KL-C1..C4 discipline | Product Truth coverage |
| **Product Intelligence** | Understanding, Recovery | Product-level objection/loss proof (PV-16) | Product Foundation merchant thresholds |
| **Decision Engine** | Decision | Eligible ranked actions with PV-17 compliance | Decision Layer + action matrix implemented |
| **Explainability** | All | Merchant-visible `proof_source` chains (PV-7) | All domains instrumented |
| **Revenue Intelligence** | Recovery, Commercial | Leakage quantification with conservative models — labelled **Medium/Low** unless PV-3 satisfied | Attributed SAR live |

### 9.1 Implementation sequence (proof era — not code)

Aligned with Merchant Value Audit §8 priority and engineering readiness:

1. **Attributed Recovered Revenue** (PV-3, PV-12) — highest commercial leverage  
2. **Delivery-backed recovery status** (PV-11) — trust on WhatsApp product  
3. **Daily Brief** (PV-18) — Decision Proof closure  
4. **Executable interventions** (PV-17) — C− → B path  
5. **Product proof surfacing** (PV-16) — Pro tier integrity  

Each step: audit current state → governance contracts → implementation → merchant validation → update this foundation's baseline table.

---

## Section 10 — Future Evolution

### 10.1 Amendment authority

| Change type | Process |
|-------------|---------|
| **New proof domain** | Formal V2+ amendment; evidence that existing five domains cannot classify; recorded in institutional memory decision registry |
| **New PV contract** | Additive by default; numbered PV-N+1; traceability to audit or incident |
| **Principle change** | Versioned supersession — same discipline as Engineering Constitution §11 |
| **Metric added to §6** | Requires PV-6 owner + pilot validation note |
| **Confidence level change** | Requires evidence — not UX preference |

### 10.2 Relationship to Engineering Constitution

| Engineering Constitution | Proof of Value Foundation |
|--------------------------|---------------------------|
| **How** truth is built | **How** truth is **claimed** |
| Audit → Governance → Implementation | Audit (Merchant Value) → **This foundation** → Proof Governance → Surfacing |
| LT-C1, Purchase Truth, SG-* | PV-*, confidence, commercial integrity |
| Level 0–6 engineering maturity | Merchant value Level 0–5 (audit §9) |

Neither document duplicates the other. Engineering closes truth; Proof of Value closes **merchant trust**.

### 10.3 Maturity path (merchant value)

| Level | Proof requirement |
|-------|-------------------|
| **1 Working** (today) | Outcomes exist; proof partial — **current** |
| **2 Proven** | PV-3 SAR + PV-11 delivery visible; pilot merchants verify |
| **3 Valuable** | Daily Brief + Decision Confidence measured; C− → B+ |
| **4 Differentiated** | Product + behavior proof competitor lacks |
| **5 Indispensable** | Commercial Proof sustains renewal without operator narration |

### 10.4 Document maintenance

| Event | Action |
|-------|--------|
| New truth layer closed | Update §3 hierarchy + §6 metric eligibility |
| Merchant surface ships | Verify §5 + PV contracts + confidence |
| Merchant Value Audit refreshed | Update baseline tables + §8 tier matrix |
| Proof defect incident | Add PV contract or CI rule; failure registry |

**Versioning:** V1 ratified 2026-07-04. Supersession requires `proof_of_value_foundation_v2.md` with changelog and decision registry entry.

---

## Appendix A — Constitution ↔ Proof index

| Engineering principle | Proof principle |
|----------------------|-----------------|
| Truth Before Intelligence | Proof Before Intelligence |
| Evidence Before Assumptions | Evidence Before Marketing |
| Measure Before Optimize | Measured Before Estimated |
| Fail Safe / Fail Loud | Unknown must remain unknown (PV-5) |
| One source of truth | PV-6, PV-7 |
| Governance before optimization | Proof contracts before surfacing |

---

## Appendix B — Success criteria (this document)

| Question | Answer location |
|----------|-----------------|
| What value may CartFlow claim? | §2 domains + §8 allowed posture |
| How is value proven? | §3 hierarchy + §4 PV contracts + §7 confidence |
| How do merchants build trust? | §5 surfaces + §6 metrics + §7 confidence + §8 integrity |
| How does intelligence strengthen evidence? | §1.3, §3, §9 — compose never substitute |
| What comes after this foundation? | §9.1 — Proof Governance + controlled surfacing (implementation separate) |

This document is the **official framework** for the Merchant Value Era — the commercial counterpart to the Engineering Constitution. Documentation only. No implementation.
