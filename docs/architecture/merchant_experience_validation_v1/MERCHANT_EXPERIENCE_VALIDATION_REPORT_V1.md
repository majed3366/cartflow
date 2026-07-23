# Merchant Experience Validation Report V1

**Status:** COMPLETE — STOP for Product / Architecture review  
**Date (UTC):** 2026-07-22  
**Validation type:** Product (merchant experience) — **not** an engineering implementation task  
**Question answered:** Can a merchant safely understand and operate their store using the current CartFlow platform?  
**Answer:** **No — not yet.**

**Evidence root:** `docs/architecture/merchant_experience_validation_v1/`  
**Collector:** `scripts/merchant_experience_validation_v1.py`  
**Simulation run:** `srs_32921fb36ed24fccadf4b453d29cb5aa`  
**Seed / window:** `20260722` · historical `2026-05-01` → `2026-05-03` (sim probe `as_of=2026-05-04T12:00:00`)  
**Store:** `demo` only · Reality Simulator · no fake dashboard fill · no manual injection  

> Validation only. No redesign. No feature work. No architecture changes in this task.

---

## 1. Executive Summary

A governed Small Reality historical run produced durable platform truth on `demo` (**27 abandoned carts, 20 purchase-truth rows, 18 hesitation reasons, 13 mock WhatsApp sends, Reality Score 72.2**). Production Product Performance probes for Knowledge / Guidance / Routing / Presentation / Surface Composition all return `ok: true`.

**Merchant-facing experience still fails the trust test.**

Within 30 seconds of opening Home, a newly signed-up merchant (lab-bound to `demo`) sees a **skeleton** (“تجهز ملخص عملك اليومي…”) and cannot answer:

| 30-second question | Merchant-visible answer |
|--------------------|-------------------------|
| What is happening? | Unclear (loading / empty) |
| What requires attention? | Unclear (attention empty / suppressed) |
| What is healthy? | Unclear |
| What is uncertain? | Partially implied by “insufficient” understanding — but contradicted by silent 27 carts |

**Core product failure:** Platform truth exists; **merchant pages do not consume Surface Composition** (or time-aligned Knowledge/Guidance). Pages still decide locally (or show zeros / skeletons) while foundations compose in parallel.

**Final readiness score: 28 / 100 — Not Ready for merchant operation.**

---

## 2. Merchant Journey

Walked (lab session + screenshots):

```text
Signup/Login → Home → Decision (attempted) → Carts → Communication → Settings/WhatsApp → Back toward Home
```

| Step | Merchant question | Observed | One-question pass? |
|------|-------------------|----------|--------------------|
| Login / Signup | Can I enter my store? | Signup 303; lab bind `ok=true` to `demo` | Pass (lab) |
| Home | What should I know now? | Skeleton + “preparing daily summary”; attention empty | **Fail** |
| Decision Workspace | What decision needs review? | **No dedicated nav surface**; `#workspace` landed blank/Home | **Fail** |
| Carts | What cart attention is needed? | Hero asks attention; body “يرجى الانتظار قليلاً”; API rows `[]` | **Fail** |
| Communication | What needs follow-up? | Top nav “التواصل” routed into **Settings → WhatsApp loading** | **Fail** |
| Settings | How do I control the platform? | WhatsApp settings loading; purpose text clear | Partial |
| Back to Home | Is the store coherent? | Still skeleton / empty understanding vs 27 carts | **Fail** |

Screenshots: `desktop_*.png`, `mobile_*.png` in evidence folder.

---

## 3. Home Evaluation

### Evidence

- Screenshot: `desktop_home.png` / `mobile_home.png` — skeleton, “تجهز ملخص عملك اليومي…”, wall date **22 Jul 2026**.
- Composed Home API (`build_merchant_home_experience_api_payload` for `demo`):
  - `while_away.items = []` (suppressed: `empty_or_duplicate_timeline`)
  - `attention_today.count = 0` (suppressed: `empty_priority`)
  - `store_understanding` admits **insufficient** hesitation (`hesitation_total=0`) despite DB **reasons=18**
  - `brief_date = 2026-07-22` (wall), not sim end
- Dashboard summary KPIs: abandoned/recovered/WA/revenue all **0**
- Durable counts on same store slug: carts **27**, purchases **20**

### Verdict

**Executive Understanding: FAIL.** Merchant cannot safely understand the store in 30 seconds.

| Issue ID | Evidence | Impact | Page | Severity | Proposed architectural owner |
|----------|----------|--------|------|----------|------------------------------|
| MEV1-H01 | Home skeleton while 27 carts exist | Merchant believes store is empty/preparing | Home | **Critical** | Merchant Presentation + Surface Composition consumer wiring (pages) |
| MEV1-H02 | Attention empty / KPIs 0 vs 27 carts | Contradicts operational reality | Home | **Critical** | Time Authority + Home composition admission (page-owned today) |
| MEV1-H03 | Understanding claims hesitation_total=0 with 18 reasons in DB | Misleading “insufficient” theatre | Home | **High** | Knowledge Routing / Home semantic composition (temporal window) |
| MEV1-H04 | Setup still prominent (“قريب من التشغيل”, remaining_setup_count=4) | Onboarding fights lived history | Home | **High** | Merchant setup lifecycle vs Reality history |

---

## 4. Decision Workspace Evaluation

### Evidence

- Top nav has **no** Decision Workspace item (Home / Carts / Communication / Settings only).
- Screenshot attempt `desktop_decision.png` — blank/empty Home chrome.
- Surface Composition (sim-aligned) includes `decision_workspace` compositions, but UI does not expose a consumer.
- Visible SCF for decision in this sim run collapsed to **empty_state** `nothing_requiring_action` while guidance exists as `monitor_new_pattern` (see Guidance).

### Verdict

**FAIL** as a merchant decision surface — not findable; not answering “what decision requires review?”

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-D01 | No merchant nav to Decision Workspace | Merchant cannot reach the surface | Decision Workspace | **Critical** | Information Architecture / Surface Contract |
| MEV1-D02 | SCF decision visible item = empty_state despite guidance | Even if opened, composition understates review need | Decision Workspace | **High** | Surface Composition input boundary (Presentation-only; weak decision pressure) |

---

## 5. Carts Evaluation

### Evidence

- Screenshot: `desktop_carts.png` — “ما الذي يحتاج انتباهك الآن؟” + “يرجى الانتظار قليلاً.”
- API `GET /api/dashboard/normal-carts`: `merchant_carts_page_rows: []`, groups empty.
- Durable `AbandonedCart` count for demo store: **27**.
- SCF sim-aligned **carts** visible composition: `empty_state` / `nothing_requiring_action` (does not see cart operational truth).

### Verdict

**FAIL.** Asks for attention while showing wait/empty; durable carts invisible.

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-C01 | UI wait + API rows empty; DB carts=27 | Operational blindness | Carts | **Critical** | Cart projection + identity/time window for list queries |
| MEV1-C02 | SCF carts empty_state vs 27 carts | Composition cannot represent cart ops yet | Carts / SCF | **High** | Surface Composition inputs (Operational Truth missing in V1) |
| MEV1-C03 | Attention hero with no queue | Trust damage (question without answer) | Carts | **High** | Cart Workspace projection ownership |

---

## 6. Communication Evaluation

### Evidence

- Nav label “التواصل” → screenshot shows **Settings → WhatsApp** with “جاري تحميل إعدادات واتساب…”.
- Mock WA logs on demo: **13**; SCF communication visible: empty_state `no_operational_issues`.
- No communication follow-up queue surfaced to merchant.

### Verdict

**FAIL** as a communication operations surface — collapses into configuration loading.

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-M01 | Communication nav opens Settings WhatsApp | Wrong merchant question answered | Communication | **Critical** | Routing / IA (surface vs settings) |
| MEV1-M02 | 13 mock sends invisible as follow-ups | Merchant cannot operate recovery follow-up | Communication | **High** | Communication projection + Guidance Routing follow_up scope |
| MEV1-M03 | Persistent loading state in capture | Blocks trust in communication health | Communication/Settings | **Medium** | Page load / readiness presentation |

---

## 7. Knowledge Evaluation

Reviewed Knowledge Foundation statements (sim-aligned sample, n=30; production probe `ok=true`).

| Statement class (sample) | Understandable? | Actionable? | Too technical? | Duplicated? | Misleading? | Missing context? |
|--------------------------|-----------------|-------------|----------------|-------------|-------------|------------------|
| “Evidence does not include cart_abandoned_count.” | Weak | No | **Yes** | **Yes** (repeated across subjects) | Can imply no carts despite 27 abandons | **Yes** — engineering gap language |
| “Evidence quality is very_high.” | Partial | No | Yes | Yes | Overconfident vs merchant emptiness | Yes — not merchant outcome |
| “Purchases have newly appeared during the last 7 days.” | Better | Low | Medium | Yes | Timing depends on window alignment | Needs counts / products |
| Home KL understanding: hesitation_total=0 | Clear Arabic | Misleading action | No | — | **Yes** vs 18 reasons | Temporal |

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-K01 | KF statements are evidence-engineering language | Merchant cannot use Knowledge | Knowledge / Home | **Critical** | Knowledge Foundation merchant language vs ECF internals |
| MEV1-K02 | Duplicate evidence_gap statements across subjects | Cognitive noise | Home / SCF | **High** | Knowledge + Surface Composition duplicate governance |
| MEV1-K03 | Wall vs sim Knowledge counts differ (56 wall / 30 sim) without merchant cue | Temporal confusion | Cross-surface | **High** | Time Authority consumer binding |

---

## 8. Guidance Evaluation

Sim-aligned Commercial Guidance: **6** items, all `monitor_new_pattern` / `active`.

| Criterion | Assessment |
|-----------|------------|
| Relevance | Weak — monitoring only; no shipping/price operational guidance despite S03 shipping scenarios |
| Clarity | Key is internal (`monitor_new_pattern`); not merchant Arabic action |
| Timing | Active at sim end; merchant UI does not show it |
| Confidence | Not merchant-visible as confidence |
| Merchant usefulness | **Technically present, operationally unhelpful** for daily operation |

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-G01 | Only `monitor_new_pattern` after rich hesitation/recovery reality | Guidance abstains from useful ops advice | Guidance | **High** | Commercial Guidance registry / eligibility thresholds |
| MEV1-G02 | Guidance not bound into merchant pages | Zero merchant usefulness at UI | Home/DW | **Critical** | Page consumption of Presentation/SCF |
| MEV1-G03 | Reject as ops guidance: correct-but-unhelpful monitoring | False calm | Decision/Home | **High** | Guidance product policy |

---

## 9. Surface Composition Evaluation

### Production (live demo probe)

- `ok: true`, compositions **33**, visible **16**, collapsed **17**, `duplicate_current=0`, deterministic
- Classes: executive_summary×4, critical_attention×4, operational_health×3, knowledge×20, empty_state×2
- Cognitive-load collapse working (knowledge overflow collapsed)

### Sim-aligned (post Reality run)

- `ok: true`, compositions **51**, accounting composed **13** / collapsed **27** / rejected **11**
- **Carts / Decision / Communication visible = empty_state** while durable carts & mock WA exist
- Home visible dominated by knowledge/observation cards — not executive “what happened in my store”

| Criterion | Result |
|-----------|--------|
| Ordering / priority | Deterministic scores present — Pass (engine) |
| Collapse | Enforced — Pass (engine) |
| Freshness | `fresh` — Pass (engine) |
| Duplicate suppression | Groups class-scoped — Pass (engine) |
| Cognitive load | Collapse counts prove limits — Pass (engine) |
| Merchant usefulness of composed empty states | **Fail** when ops truth excluded from inputs |
| Pages consume composition | **Fail** — pages do not read `surface_compositions` |

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-S01 | Pages ignore SCF; own local composition | Dual truth systems | All pages | **Critical** | Surface Composition adoption (pages as consumers only) |
| MEV1-S02 | Empty-state “nothing requiring action” with 27 carts | False calm | Carts/DW | **Critical** | SCF input boundary — Operational Truth / Merchant Operational State not yet governed inputs |
| MEV1-S03 | Stack order conflict (task diagram places Composition before Presentation; closed stack is reverse) | Product confusion on ownership | Architecture | **Medium** | Architecture ratification |

---

## 10. Trust Evaluation

Can the merchant distinguish fact / observation / guidance / uncertainty?

| Signal | Merchant-visible? |
|--------|-------------------|
| Fact (27 carts, 20 purchases) | **No** on Home/Carts UI |
| Observation (KF / understanding) | Partial — often technical or “insufficient” |
| Guidance (CGF/MPF) | **No** on pages |
| Uncertainty | Over-shown as empty/insufficient while facts exist |

**Trust verdict: FAIL.**

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-T01 | Fact invisible; uncertainty overstated | Merchant distrust / wrong decisions | Home/Carts | **Critical** | Truth → Surface Composition → Page contract |
| MEV1-T02 | Foundations ok while UI empty | “Platform works” ≠ “merchant safe” | Cross-surface | **Critical** | Product readiness gate (this report) |

---

## 11. Cognitive Load

| Measure | Observation |
|---------|-------------|
| Decisions required | Unclear — no actionable decision surfaced |
| Unnecessary reading | Setup + preparing copy compete with emptiness |
| Hidden important information | **27 carts / 18 reasons / 13 WA** hidden | 
| Excessive scrolling | Low (pages mostly empty/skeleton) — load is *absence*, not density |
| SCF engine load | Collapse works; merchant never sees governed density |

**Cognitive-load failure mode:** not overload — **under-informing with false calm / perpetual preparing**.

| Issue ID | Evidence | Impact | Page | Severity | Proposed owner |
|----------|----------|--------|------|----------|----------------|
| MEV1-L01 | Empty/skeleton hides critical ops | Merchant cannot act | Home/Carts | **Critical** | Page composition from SCF + ops projections |

---

## 12. Missing Information

Merchant expected but could not find:

1. Live cart queue / abandoned list (27 exist)  
2. Hesitation reason mix (18 reasons exist)  
3. WhatsApp recovery follow-ups (13 mock sends)  
4. Decision Workspace entry point  
5. Explicit fact vs guidance labels on Home  
6. Time context that history is May-sim vs July wall chrome  
7. Surface Composition outputs bound into any page  

---

## 13. Redundant Information

1. KF `evidence_gap` / `evidence_quality` statements repeated across subjects (sim sample).  
2. Home understanding repeats insufficient hesitation messaging via multiple Arabic fields (observation/title/answer).  
3. WhatsApp title repeated (nav + header + loading) on communication/settings path.  
4. Dual composition systems: Home semantic composition **and** SCF (not yet unified) — conceptual redundancy.

---

## 14. Explainability

| Important statement | “Why is CartFlow saying this?” |
|---------------------|--------------------------------|
| Home preparing summary | UI loading path — **not** explained via evidence lineage |
| hesitation_total=0 | Wall-window Knowledge — lineage exists in API fields, not merchant-visible “why” |
| Carts “please wait” | No evidence explanation |
| SCF empty_state nothing_requiring_action | Engine-true given Presentation/Knowledge-only inputs — **misleading at product level** |
| Production SCF executive_summary (live demo) | Explainable via Presentation←Routing←Guidance — **not shown on merchant pages** |

**Explainability verdict: FAIL** for merchant-critical claims; Pass only inside foundation probes.

---

## 15. Suggested Structural Changes

*(Recommendations only — not implemented.)*

1. **Make every merchant page a consumer of Surface Composition only** — remove page-owned ranking/empty invention.  
2. **Govern Operational Truth + Merchant Operational State** as SCF inputs (carts / recovery / communication health) so empty-states cannot deny durable ops.  
3. **Bind Time Authority into all merchant reads** when Reality/history is the working context (wall vs sim mismatch).  
4. **Expose Decision Workspace** as a first-class surface in IA.  
5. **Separate Communication ops from Settings WhatsApp configuration.**  
6. **Translate Knowledge/Guidance into merchant language** before presentation (technical ECF strings must not ship as merchant Knowledge).  
7. **Ratify stack order** (Composition vs Presentation) so ownership stops drifting.  
8. **Product gate:** foundations `ok:true` is necessary but **not sufficient** for merchant readiness.

---

## 16. Evidence Screenshots

| File | Surface |
|------|---------|
| `desktop_home.png` / `mobile_home.png` | Home skeleton |
| `desktop_carts.png` / `mobile_carts.png` | Carts wait/empty |
| `desktop_decision.png` / `mobile_decision.png` | Missing DW |
| `desktop_communication.png` / `mobile_communication.png` | Settings WhatsApp loading |
| `desktop_settings.png` / `mobile_settings.png` | Settings |

Also: `mev1_evidence.json`, `stack_sim_full.json`, `production_probes.json`, simulation manifest under `srs_32921fb36ed24fccadf4b453d29cb5aa/`.

---

## 17. Final Readiness Score

| Dimension | Score (0–10) | Notes |
|-----------|-------------:|-------|
| Executive understanding (30s) | 1 | Skeleton / empty |
| Knowledge quality (merchant) | 2 | Technical / duplicated |
| Guidance usefulness | 2 | Monitor-only; not shown |
| Surface Composition (engine) | 7 | Deterministic; collapse works |
| Surface Composition (merchant) | 1 | Not consumed; false empty-states |
| Merchant journey coherence | 2 | DW missing; Comm misrouted |
| Trust (fact vs uncertainty) | 1 | Facts hidden |
| Cognitive load (useful density) | 2 | Under-informing |
| Explainability | 2 | Probe-only |
| Ops visibility (carts/WA) | 1 | Invisible |

**Weighted readiness: 28 / 100 — NOT READY.**

**Primary question answer:** A merchant **cannot** safely understand and operate their store using the current CartFlow merchant experience, even when governed foundations and Reality Simulator truth are healthy underneath.

---

## 18. STOP

**Merchant Experience Validation V1 is complete.**

Do **not** begin redesign, page binding, or architectural changes until this report is reviewed and approved.

Collecting evidence only — no fixes were applied.
