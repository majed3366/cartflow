# CartFlow — Merchant Value Audit V1

**Date (UTC):** 2026-07-04  
**Type:** Read-only merchant value audit — no implementation, no redesign, no marketing copy  
**Method:** Evidence only — grounded in shipped merchant surfaces (`docs/SYSTEM_SUMMARY.md`), completed engineering foundations, and prior decision audits  
**Framework:** [`docs/cartflow_value_validation_foundation_v1.md`](cartflow_value_validation_foundation_v1.md) (value domains, proof categories, evidence registry, daily brief contract)

**Purpose:** Determine what merchant value **already exists**, what is **partially available**, and what is **missing** — as the evidence base for the next Merchant Value Foundation.

---

## Executive verdict

CartFlow **delivers real merchant outcomes today** in a controlled pilot: it captures abandonment reasons, runs automated WhatsApp recovery, surfaces cart lifecycle truth, and offers VIP prioritization with merchant alerts. Engineering foundations (Purchase Truth, Lifecycle Truth LT-C1, Knowledge Layer v1, Product Data Foundation, Provider Reliability record layer) are **stronger than merchant-visible proof**.

| Dimension | Verdict |
|-----------|---------|
| **Value exists?** | **Yes** — automation + visibility for routine cart operations |
| **Value provable to merchant?** | **Partially** — wins and states visible; attributed ROI and delivery truth not |
| **Value trustworthy daily?** | **Partially** — lifecycle frame is good; decision loop incomplete (**C−** baseline) |
| **Commercial demonstration?** | **Partially Ready** — honest pilot demos possible; tier claims and ROI stories not yet defensible fleet-wide |

**Bottom line:** CartFlow is **Level 1 Working** merchant value with **islands of Understanding Proof** — not yet **Level 2 Proven** or **Level 3 Valuable** at scale.

---

## Section 1 — Merchant Value Inventory

Every capability below is **merchant-visible** (dashboard, widget, or merchant API). Admin-only and `/dev/*` surfaces are excluded.

### 1.1 Storefront widget & reason capture

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Exit-intent / hesitation UX on the storefront; customer selects why they are leaving; optional phone capture; cart events synced to backend |
| **Evidence** | Layered V2 widget (`cartflow_widget_runtime/*`); `POST /api/cartflow/reason`, `POST /api/cart-recovery/reason`; storefront cart bridge → `POST /api/cart-event`; return tracker (`cartflow_return_tracker.js`) |
| **Value domain** | Revenue Recovery, Customer Understanding, Behavior Truth (partial) |
| **Maturity** | **Working** — default production path is V2 via `widget_loader.js` |
| **Limitations** | Widget install often engineering-gated (Partner Custom Snippet — no per-store API); dual reason API paths remain; behavioral timeline not merchant-visible |

### 1.2 Automated WhatsApp recovery

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Delayed recovery messages after abandon; per-reason templates and timing; multi-message sequences; conversion stops recovery |
| **Evidence** | `RecoverySchedule`, `execute_recovery_schedule`, `whatsapp_send.send_whatsapp` (Twilio when `PRODUCTION_MODE` + env); `decide_recovery_action`; reason templates |
| **Value domain** | Revenue Recovery |
| **Maturity** | **Working** (environment-dependent) — core engine restart-safe and durable |
| **Limitations** | Twilio env not self-serve; failed sends terminal with no merchant-visible re-drive (P1-1); acceptance shown as «sent» without delivery truth on merchant UI; Meta not the recovery provider |

### 1.3 Cart list & lifecycle understanding

| Field | Assessment |
|-------|------------|
| **What merchant receives** | `#carts` tab with filters; per-row lifecycle label; expanded block: «ماذا حدث؟ / ماذا فعل النظام؟ / التالي / تدخل التاجر»; reason chip; phone indicator |
| **Evidence** | `GET /api/dashboard/normal-carts`; `customer_lifecycle_states_v1.py` (LT-C1 mint); `merchant_dashboard_lazy.js` lifecycle-only chip |
| **Value domain** | Customer Understanding |
| **Maturity** | **Working → strong partial proof** — best daily-value surface today |
| **Limitations** | Return/purchase lack decision detail; phone ✓/✗ ambiguous; intervention flag without in-row action (decision summary **D** on «what should I do»); `#completed` mixes wins, exhaustion, dismissals |

### 1.4 Archive & reopen

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Dismiss carts from active view; restore visibility via reopen; merchant-archived excluded from operational lists |
| **Evidence** | `POST /api/dashboard/cart-lifecycle/archive` + `/reopen`; `merchant_cart_lifecycle_archive_v1.py`; reopen semantics doc |
| **Value domain** | Decision Support (dismiss path only) |
| **Maturity** | **Working** for intentional dismiss/restore |
| **Limitations** | Archive offered on states that do not require merchant action; reopen forbidden for purchased truth — correct but `#completed` semantics still confuse |

### 1.5 VIP prioritization & merchant alert

| Field | Assessment |
|-------|------------|
| **What merchant receives** | `#vip` tab and carts banner for high-value abandons; threshold config; WhatsApp alert **to merchant** (`POST …/merchant-alert`); optional manual contact link |
| **Evidence** | `vip_dashboard_batch_v1.py`; `vip_merchant_alert.py`; `AbandonedCart` threshold lane; VIP isolated in KL metrics (KL-C4) |
| **Value domain** | Revenue Recovery, Decision Support |
| **Maturity** | **Working** — only surface with contact-shaped actions aligned to «needs you» |
| **Limitations** | Alert delivery depends on `store_whatsapp_number` / support URL; delivery truth not merchant-surfaced; VIP phone capture path separate from normal intervention |

### 1.6 Knowledge Layer home insights

| Field | Assessment |
|-------|------------|
| **What merchant receives** | `#home` Overview — «ماذا يحدث في متجري الآن؟»; up to ~3–5 OIA cards (Observation / Impact / Action); weekly reason distribution; insufficient-data empty state |
| **Evidence** | `GET /api/knowledge/report`; `merchant_knowledge_layer.js`; KL-C1..C4 (honest attribution, VIP separation, product bridge health only) |
| **Value domain** | Customer Understanding, partial Product Understanding |
| **Maturity** | **Partial** — insights when data sufficient; not a governed daily brief |
| **Limitations** | No hard 3–5 cap with mandatory why+action on every item; no attributed SAR; product insights gated on foundation health not product decisions; cards can appear when merchant cannot act |

### 1.7 Weekly reasons & monthly summary

| Field | Assessment |
|-------|------------|
| **What merchant receives** | «أسباب الأسبوع» on home overview; `#home-month` monthly summary + «أبرز الاسترداد — اليوم» (moved off overview per Home Dashboard Closure v3) |
| **Evidence** | Dashboard snapshot `summary` payload; `GET /api/dashboard/summary`; recovery highlights on month page |
| **Value domain** | Customer Understanding, partial Revenue Recovery |
| **Maturity** | **Partial** — aggregate visibility without proof chain |
| **Limitations** | Recovery KPIs deliberately removed from overview; no attributed wins; trend/chart on separate live path |

### 1.8 Recovery settings & templates

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Delay, attempts, quiet period; per-reason message templates; exit-intent copy; widget appearance |
| **Evidence** | `GET`/`POST /api/recovery-settings`; `recovery_settings.html`, `cart_recovery_messages.html`, `widget_customization.html`, `exit_intent_settings.html` |
| **Value domain** | Revenue Recovery, Store Health (configuration) |
| **Maturity** | **Working** — self-serve in dashboard |
| **Limitations** | Template approval manual (Meta); merchant cannot see which template performed best |

### 1.9 WhatsApp path & readiness UX

| Field | Assessment |
|-------|------------|
| **What merchant receives** | `#whatsapp` — Path A (CartFlow managed) vs Path B (merchant-owned); readiness cards; journey selector; action-first connection guidance |
| **Evidence** | `merchant_whatsapp_mode_v1.py`, connection readiness, onboarding journeys, template registry (11 keys) |
| **Value domain** | Store Health |
| **Maturity** | **Partial** — strong UX copy; production send still Twilio/env-gated |
| **Limitations** | Embedded Signup is readiness stub (no token exchange); merchant may read «connected» before production send ready; recovery remains Twilio-only |

### 1.10 Store setup & onboarding

| Field | Assessment |
|-------|------------|
| **What merchant receives** | `#home-setup` unified P0 card; 6-step activation checklist; progress bar; nav locks; store connection (Zid OAuth when configured); test-widget path |
| **Evidence** | `merchant_setup_unified_p0.py`, `merchant_onboarding_journey_v2.py`, `merchant_onboarding_reality_v1.py` (`self_serve_to_production_ready: False`) |
| **Value domain** | Store Health, Operational Confidence (setup) |
| **Maturity** | **Partial** — guided but go-live engineering-gated |
| **Limitations** | Readiness can overstate progress (synthetic `zid_store_id` without OAuth); widget install unsupported without partner snippet |

### 1.11 Purchased / completed visibility

| Field | Assessment |
|-------|------------|
| **What merchant receives** | «تم الشراء» lifecycle label; purchased rows in `#completed` / active filters; cart marked `recovered` |
| **Evidence** | Purchase Truth → `merchant_purchased_cart_dashboard_v1.py`; lifecycle `completed`; platform webhook reconcile |
| **Value domain** | Revenue Recovery, Customer Understanding |
| **Maturity** | **Partial proof** — terminal state clear; attribution not shown |
| **Limitations** | No «did recovery cause this?»; no SAR amount prominence; mixed with archived/exhausted in same tab |

### 1.12 Manual customer send & demo sandbox

| Field | Assessment |
|-------|------------|
| **What merchant receives** | `POST /api/carts/{id}/send` (Meta path, homepage); `/demo/store` sandbox; test-widget harness |
| **Evidence** | `main.send_whatsapp_message`; demo commerce sandbox §3.2.1 |
| **Value domain** | Revenue Recovery (manual), Store Health (activation) |
| **Maturity** | **Working** for activation/demo; **orphan** for production recovery (Twilio is recovery path) |
| **Limitations** | Manual send not integrated into normal-carts decision loop; demo ≠ production merchant value proof |

### 1.13 Plans & subscription visibility

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Read-only plan card on `#settings`; `#plans` comparison (Starter/Growth/Pro SAR); trial/expiry display |
| **Evidence** | SaaS Phases 1–4; `GET /api/merchant/subscription`, `GET /api/merchant/plans-catalog` |
| **Value domain** | Commercial packaging (not outcome proof) |
| **Maturity** | **Working** visually — **no billing, no enforcement** (`CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE` default off) |
| **Limitations** | Tier feature claims exceed provable merchant value today (Pro «operational insights» largely future) |

### 1.14 Recovery trend chart

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Chart data via live API (not snapshot-enforced) |
| **Evidence** | `GET /api/dashboard/recovery-trend` |
| **Value domain** | Revenue Recovery (analytics) |
| **Maturity** | **Partial** — trend without attribution or delivery proof |
| **Limitations** | Removed from lazy boot for perf; not aligned with daily brief anti-pattern (chart without decision) |

### 1.15 Follow-ups & messages surfaces

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Live JSON for scheduled follow-ups and message history context |
| **Evidence** | `GET /api/dashboard/followups`, `GET /api/dashboard/messages` (live-only per read model audit) |
| **Value domain** | Customer Understanding, Recovery Truth (partial) |
| **Maturity** | **Partial** — operational detail for engaged merchants |
| **Limitations** | Not ranked into daily priority; delivery disposition not merchant-visible |

### 1.16 Auth & account self-serve

| Field | Assessment |
|-------|------------|
| **What merchant receives** | Signup, login, password reset |
| **Evidence** | `routes/merchant_auth.py`; PBKDF2; cookie session |
| **Value domain** | Store Health (access) |
| **Maturity** | **Working** |
| **Limitations** | No 2FA; production go-live still not self-serve |

---

## Section 2 — Evidence Inventory

For each **merchant value claim** CartFlow implicitly or explicitly makes, this table maps evidence sources and classification.

**Legend:** **Confirmed** = merchant can trust claim from visible evidence · **Partial** = claim directionally true but incomplete or misleading if overstated · **Future** = engineering exists but not merchant-visible

| Merchant value claim | Purchase Truth | Lifecycle Truth | Provider Truth | Snapshot | Dashboard | Widget | WhatsApp | Ops Metrics | Classification |
|----------------------|:--------------:|:---------------:|:--------------:|:--------:|:---------:|:------:|:--------:|:-----------:|----------------|
| «Customer purchased» | ✓ primary | ✓ propagates | — | ✓ in normal_carts | ✓ «تم الشراء» | — | stops recovery | dev/admin only | **Confirmed** (terminal label) |
| «Recovery was attempted» | — | ✓ via logs/state | ✓ acceptance | ✓ | ✓ row copy | — | ✓ send path | admin | **Partial** — «sent» ≠ delivered |
| «Message reached customer» | — | — | ✓ delivery layer exists | — | ✗ not shown | — | webhook ingest | admin/dev | **Future** for merchant |
| «Recovery caused purchase» | ✓ + attribution module | — | — | — | ✗ not shown | — | — | KL health only | **Future** as merchant KPI |
| «Cart needs merchant now» | — | ✓ `merchant_needed` | — | ✓ | ✓ flag | — | — | — | **Partial** — flag without action |
| «Why customer left» | — | — | — | ✓ reasons | ✓ chip + weekly | ✓ capture | — | — | **Confirmed** (when captured) |
| «High-value cart alert» | — | ✓ VIP lane | ✓ alert send | ✓ | ✓ VIP tab/banner | ✓ threshold | ✓ merchant alert | VIP diagnostics | **Partial** — alert delivery not proven to merchant |
| «Store patterns / bottlenecks» | ✓ honest counts | — | — | ✓ summary inputs | ✓ KL cards | — | — | KL health | **Partial** — when coverage sufficient |
| «Dashboard is current» | — | — | — | ✓ read model | ✓ fast O(1) read | — | — | ✓ observability | **Partial** — stale possible at scale; not explained to merchant |
| «Setup complete / ready» | — | — | — | ✓ store_connection | ✓ setup cards | ✓ beacon | ✓ readiness UX | onboarding reality | **Partial** — can overstate vs production send |
| «Recovered revenue (SAR)» | ✓ records exist | — | — | — | ✗ no KPI | — | — | attribution internal | **Future** |
| «Product losing sales» | ✓ purchase mapping | — | — | — | ✗ | ✓ lines capture | — | product-data health | **Future** |
| «What to do first today» | — | ✓ next copy | — | ✓ KL | ✓ mixed surfaces | — | — | — | **Partial** — not ranked brief |

### 2.1 Evidence layer summary

| Evidence layer | Engineering status | Merchant-visible status |
|----------------|-------------------|-------------------------|
| **Purchase Truth** | Closed / governed | Partial — wins yes, attribution no |
| **Lifecycle Truth** | Enforced (LT-C1 CI) | **Confirmed** — strongest merchant evidence |
| **Provider Truth** | Measured, activation deferred | **Future** — ops/dev only |
| **Recovery Truth** | Durable logs + schedules | Partial — copy not disposition |
| **Behavior Truth** | Return tracker + reasons | Partial — reasons yes, timeline no |
| **Product Truth** | Foundation closed | **Future** — no merchant UI |
| **Knowledge Layer** | Closed v1 (KL-C1..C4) | Partial — home cards |
| **Snapshot / Read Model** | Governed + measured | Partial — speed yes, freshness contract no |
| **Operational Metrics** | Measured (`/dev/operational-metrics`) | **Future** — not merchant-facing |

---

## Section 3 — Merchant Questions Coverage

Using merchant questions from [`cartflow_value_validation_foundation_v1.md`](cartflow_value_validation_foundation_v1.md) §Step 1.

### 3.1 Revenue & recovery

| Question | Status | Why |
|----------|--------|-----|
| Why are customers leaving? | **Answered** (when widget fires) | Reason capture + weekly distribution + KL hesitation insights |
| Which abandoned carts are worth acting on first? | **Partially answered** | VIP threshold + banner; no unified priority rank for normal carts |
| Did recovery actually bring money back? | **Not answered** | Purchase visible; attributed SAR not merchant-facing |
| Which recovery efforts actually worked? | **Not answered** | No per-template / per-reason outcome proof |
| What revenue am I losing right now? | **Partially answered** | VIP value visible; no store-wide leakage quantification |

### 3.2 Customer understanding

| Question | Status | Why |
|----------|--------|-----|
| Who is stuck and why? | **Partially answered** | Lifecycle block strong; return/purchase detail weak |
| Which customers came back but didn't buy? | **Not answered** | Return signals in backend; not a merchant decision prompt |
| What changed this week? | **Partially answered** | KL trends + weekly reasons when data sufficient |
| Does this cart need me or the system? | **Partially answered** | «تدخل التاجر» flag exists; contradictions documented in decision audits |

### 3.3 Product understanding

| Question | Status | Why |
|----------|--------|-----|
| Which products lose the most sales? | **Not answered** | Product Foundation captures data; no merchant insight |
| What objections block which products? | **Not answered** | Hesitation mappings exist; not surfaced |
| Store-wide vs product-specific objections? | **Partially answered** | Store-level reason distribution only |

### 3.4 Store health & operations

| Question | Status | Why |
|----------|--------|-----|
| Is my store set up correctly for recovery? | **Partially answered** | Setup journey + readiness cards; go-live not self-serve |
| Is WhatsApp / widget / platform working? | **Partially answered** | Readiness UX + widget beacon; no unified merchant health brief |
| What broke since yesterday? | **Not answered** | Degradation visible to ops/admin, not merchant |
| Can I trust the dashboard? | **Partially answered** | Lifecycle truth strong; stale snapshots possible silently at scale |

### 3.5 Decision support

| Question | Status | Why |
|----------|--------|-----|
| What should I do first today? | **Not answered** | No ranked 3–5 brief; KL cards approximate |
| What changed this week? | **Partially answered** | KL + monthly page |
| What happens if I do nothing? | **Not answered** | Rarely stated (decision summary **D**) |
| Is this cart finished? | **Partially answered** | Purchase clear; `#completed` overload |

### 3.6 Coverage scorecard

| Status | Count | Share |
|--------|------:|------:|
| **Answered** | 1 | ~6% |
| **Partially answered** | 12 | ~71% |
| **Not answered** | 4 | ~24% |

**Pattern:** CartFlow **explains routine automation well** and **captures reasons** — but **does not close the merchant decision loop** on money, priority, product, or inaction.

---

## Section 4 — Proof Inventory

Audit of the four proof categories from Value Validation Foundation §Step 3.

### 4.1 Recovery Proof

**Definition:** Money and carts recovered because of CartFlow actions.

| Aspect | Maturity | Evidence |
|--------|----------|----------|
| Abandon → schedule → send chain | **Working (internal)** | Durable `RecoverySchedule`, restart-safe execution |
| Purchase after recovery | **Partial** | Purchase Truth + lifecycle «تم الشراء»; attribution module exists (`knowledge_purchase_attribution_v1.py`, `purchase_attribution_v1.py`) |
| Attributed SAR to merchant | **Not proven** | KL-C2 fixed internal honesty; no merchant KPI |
| Delivery as recovery proof | **Not proven** | Provider Truth record-only; merchant sees acceptance language |
| VIP recovery priority | **Partial** | Threshold + alert; not full outcome proof |

**Overall Recovery Proof maturity: Level 1 Working** — automation runs; **merchant-trustable ROI proof absent**.

### 4.2 Understanding Proof

**Definition:** Merchant understands customers, products, or patterns from evidence — not counts alone.

| Aspect | Maturity | Evidence |
|--------|----------|----------|
| Per-cart lifecycle narrative | **Level 2 approaching** | LT-C1 block on every row — best proof surface |
| Hesitation / reason patterns | **Partial** | Weekly reasons + KL when coverage OK |
| Return / engage narrative | **Weak** | Classified but not explanatory for decisions |
| Product-linked understanding | **Absent** | Foundation only |
| KL OIA cards | **Partial** | Observation/Impact/Action framework; insufficient-data handled |

**Overall Understanding Proof maturity: Level 1–2** — **strongest proof category today**; still below daily brief contract.

### 4.3 Decision Proof

**Definition:** Merchant knows what to do next and why — with eligible actions.

| Aspect | Maturity | Evidence |
|--------|----------|----------|
| «What should I do?» on normal carts | **Weak (D)** | Text only; archive-only actions |
| Intervention scenarios | **Unusable (D)** | Flag without executable path |
| VIP actions | **Partial** | Merchant alert + manual contact |
| Daily priority rank | **Absent** | No 3–5 curated brief |
| Inaction consequences | **Absent** | Decision summary grade **D** |

**Overall Decision Proof maturity: Level 0–1** — **weakest proof category**; undermines renewal narrative for «tells me what to do».

### 4.4 Operational Proof

**Definition:** Platform and integrations working; data trustworthy.

| Aspect | Maturity | Evidence |
|--------|----------|----------|
| Setup / onboarding truth | **Partial** | Guided journey; `self_serve_to_production_ready: False` |
| WhatsApp readiness UX | **Partial** | Action-first cards; production send env-gated |
| Dashboard read performance | **Working (implicit)** | O(1) snapshot read; observability measured |
| Freshness transparency | **Not proven to merchant** | Stale served possible; internal flags only |
| Send/delivery operational truth | **Internal only** | Provider Reliability Level 3 measured at ops layer |

**Overall Operational Proof maturity: Level 1 Working** — merchant **feels** system works in pilot; **cannot verify** delivery or freshness themselves.

### 4.5 Proof maturity summary

| Proof category | Level | Merchant trust today |
|----------------|-------|----------------------|
| Recovery Proof | 1 — Working | Low for ROI claims |
| Understanding Proof | 1–2 | Moderate for cart rows |
| Decision Proof | 0–1 | Low |
| Operational Proof | 1 | Moderate in pilot; fragile at scale |

---

## Section 5 — Commercial Readiness

**Question:** Can CartFlow **honestly demonstrate value** to a merchant or buyer today?

### 5.1 By value domain

| Value domain | Demonstration readiness | Evidence |
|--------------|-------------------------|----------|
| **Revenue Recovery** | **Partially Ready** | Live recovery + purchase wins in pilot; **cannot** show attributed SAR or delivery-backed proof |
| **Customer Understanding** | **Partially Ready** | Lifecycle demo is credible; return/purchase decisions weak |
| **Product Understanding** | **Not Ready** | No merchant-facing product insights |
| **Store Health** | **Partially Ready** | Setup journey demoable; go-live requires engineering |
| **Operational Confidence** | **Partially Ready** | Strong ops instrumentation; merchant cannot see it |
| **Decision Support** | **Not Ready** | C− decision confidence; no daily brief |

### 5.2 By commercial motion

| Motion | Readiness | Evidence |
|--------|-----------|----------|
| **Pilot sale (hand-onboarded)** | **Ready** | Platform Readiness: CONTROLLED PILOT READY (~5.0/10); recovery core durable |
| **Self-serve signup → live recovery** | **Not Ready** | `self_serve_to_production_ready: False`; Twilio/Zid/widget engineering steps |
| **ROI story / renewal** | **Not Ready** | No merchant attributed revenue KPI; acceptance≠delivery |
| **Tier upsell (Growth/Pro)** | **Partially Ready** | VIP + KL partially deliver; Pro intelligence claims exceed proof |
| **Referral («it paid for itself»)** | **Not Ready** | Would require unattributed or anecdotal claims — violates value contract |
| **Billing / paid conversion** | **Not Ready** | No payment processing; plans UI visual only |

### 5.3 Honest demonstration script (what works today)

A **truthful** pilot demonstration can show:

1. Customer selects leave reason on widget → reason appears on cart row  
2. Lifecycle block explains system state in Arabic  
3. Recovery message sends after configured delay (with ops prerequisites)  
4. Purchase moves cart to «تم الشراء» with recovery stopped  
5. VIP cart triggers merchant alert path  
6. Knowledge Layer cards surface patterns when store has enough data  

A **dishonest** demonstration would claim:

- Guaranteed recovered revenue totals  
- Messages always delivered because status says «sent»  
- Pro-tier product intelligence  
- Self-serve production in one session  

### 5.4 Overall commercial readiness verdict

| Classification | Scope |
|----------------|-------|
| **Ready** | Controlled pilot with operator support; lifecycle + reason + automation narrative |
| **Partially Ready** | Growth-tier VIP + KL patterns; setup-guided onboarding |
| **Not Ready** | ROI proof, self-serve go-live, Pro intelligence, referrals, billing |

**Composite: Partially Ready for pilot revenue; Not Ready for scalable commercial proof.**

---

## Section 6 — Competitive Value

Without feature comparison — **unique merchant outcomes** CartFlow already creates:

### 6.1 Outcomes only CartFlow combines today

1. **Hesitation-moment reason capture tied to recovery** — merchant learns *why* customers leave at the moment of intent, not only from cart abandonment data alone. Outcome: objection-aware recovery messages without merchant manual tagging.

2. **Per-cart Arabic lifecycle decision frame** — every cart answers «what happened / what the system did / what's next / do you need me» from a single governed truth (LT-C1). Outcome: merchant can scan carts without reading raw logs.

3. **VIP lane with merchant-side alert** — high-value abandon surfaces to merchant's own WhatsApp before or alongside customer recovery. Outcome: human attention on money at risk without watching all carts.

4. **Honest attribution discipline (internal)** — platform refuses to inflate recovery purchase counts (KL-C2). Outcome: when ROI proof ships, merchants can trust it won't be marketing-inflated — a trust asset competitors often burn.

5. **Reason-driven template and timing** — recovery varies by captured objection (price, shipping, etc.). Outcome: messages match stated customer concern, not generic blast.

6. **Integrated widget → cart event → schedule → dashboard loop** — one pipeline from storefront behavior to merchant visibility. Outcome: merchant sees the same cart the system is acting on.

### 6.2 Outcomes not yet unique (because not merchant-visible)

- Attributed revenue proof  
- Product-level loss intelligence  
- Delivery-verified recovery  
- Daily prioritized action brief  

These are **engineering-prepared** but **not market-differentiating until surfaced**.

---

## Section 7 — Missing Value

Largest **merchant-visible outcome gaps** — identification only, no implementation proposals.

### 7.1 Proof gaps (merchant cannot verify claims)

| Gap | Impact |
|-----|--------|
| **No attributed recovered revenue (SAR)** | Cannot answer «Is CartFlow paying for itself?» — primary renewal blocker |
| **No delivery truth on merchant surfaces** | «Sent» overstates reach; trust risk on WhatsApp-centric product |
| **No recovery effort effectiveness** | Cannot answer «what worked?» — blocks optimization decisions |

### 7.2 Decision gaps (merchant cannot act)

| Gap | Impact |
|-----|--------|
| **Intervention flag without executable action** | «تدخل التاجر: نعم» creates anxiety without closure |
| **No daily priority brief (3–5 items)** | Merchant must scan full cart table — defeats «minutes not hours» promise |
| **Inaction consequences unstated** | Merchant cannot calibrate urgency |
| **Return-to-site not a decision** | High-value signal wasted as status only |

### 7.3 Understanding gaps

| Gap | Impact |
|-----|--------|
| **No product-level loss or objection mapping visible** | Pro tier promise unsupported |
| **`#completed` semantic overload** | Cannot run daily «wins vs losses vs dismissed» reporting |
| **Phone column ambiguity** | Wrong contact decisions |

### 7.4 Operational gaps (merchant blind to system health)

| Gap | Impact |
|-----|--------|
| **No unified store health brief** | Setup scattered across pages; degradation invisible |
| **Dashboard freshness not explained** | Silent stale data at scale erodes trust |
| **Go-live not self-serve** | Value delayed by engineering bottleneck |

### 7.5 Commercial gaps

| Gap | Impact |
|-----|--------|
| **No billing / paid conversion** | Value exists without business capture |
| **Tier claims exceed proof** | Pro «intelligence» and Growth «advanced analytics» ahead of evidence |
| **No referral-grade ROI story** | Word-of-mouth blocked by honesty rules |

---

## Section 8 — Prioritized Opportunities

Missing value ranked by **merchant impact**, **commercial impact**, and **implementation readiness** (engineering foundation already exists).

Scoring: **H** / **M** / **L** for each dimension. **Readiness** = how much closed engineering can be surfaced vs net-new build.

| Rank | Missing outcome | Merchant impact | Commercial impact | Readiness | Rationale |
|:----:|-----------------|-----------------|-------------------|-----------|-----------|
| **1** | **Attributed recovered revenue visible to merchant** | H | H | **H** | Purchase Truth + KL-C2 attribution exist; no merchant KPI — unlocks renewal and ROI |
| **2** | **Executable intervention actions on normal carts** | H | H | M | Decision audits complete; lifecycle truth ready; action matrix documented |
| **3** | **Daily brief (3–5 ranked insights, what/why/action)** | H | H | M | KL OIA + lifecycle + VIP signals exist; needs curation contract not new truth |
| **4** | **Delivery truth on recovery status** | M | H | **H** | Provider Reliability foundation record-only; surfacing is read-path work |
| **5** | **Return / re-engage as decision (not status)** | H | M | M | Behavior signals captured; decision frame exists |
| **6** | **Unified store health brief for merchant** | M | M | M | Integration health + onboarding reality + widget trust composed admin-side |
| **7** | **Product-level objection/loss insights** | M | H (Pro) | M | Product Foundation + hesitation/purchase mappings ready; KL bridge partial |
| **8** | **Dashboard freshness transparency** | M | M | **H** | Read model observability measured; merchant copy missing |
| **9** | **Recovery template effectiveness** | M | M | L | Requires aggregated Recovery + Purchase proof pipeline |
| **10** | **Self-serve go-live** | M | H | **L** | Platform/partner/env blockers — not surfacing problem |

**Top three** (#1–#3) dominate merchant impact and commercial impact with the highest readiness among high-impact items.

---

## Section 9 — Overall Maturity

### 9.1 Merchant Value maturity model

| Level | Name | Meaning |
|------:|------|---------|
| 0 | Experimental | Value hypothesis only |
| 1 | **Working** | Merchants receive outcomes; proof weak |
| 2 | Proven | Value demonstrable with evidence |
| 3 | Valuable | Daily trust; decisions closed |
| 4 | Differentiated | Unique outcomes competitors lack |
| 5 | Indispensable | Merchants cannot operate without it |

### 9.2 Classification: **Level 1 — Working**

**Justification:**

| Factor | Assessment |
|--------|------------|
| **Outcomes delivered** | Automated recovery, reason capture, lifecycle visibility, VIP alerts — **real in pilot** |
| **Proof maturity** | Recovery Proof and Decision Proof **below Level 2**; Understanding Proof **approaching Level 2** on cart rows only |
| **Decision confidence** | **C−** composite per `cartflow_merchant_decision_summary_v1.md` |
| **Commercial proof** | Partially Ready for pilot; **Not Ready** for ROI/referral/self-serve |
| **Engineering vs merchant gap** | Multiple foundations **Closed** at engineering layer; merchant value **Partial** per value validation foundation §8.2 |

**Not Level 2 Proven because:** CartFlow cannot yet **demonstrate** attributed recovery revenue or delivery-backed recovery to a merchant without operator narration.

**Not Level 0 because:** Shipped product delivers recurring merchant outcomes — not a prototype.

### 9.3 Segment maturity (nuance)

| Segment | Level | Comment |
|---------|-------|---------|
| Routine automation (wait send/reply) | **1+** | Acceptable B-grade daily use |
| Cart row understanding | **2−** | Strongest proof island |
| Revenue ROI proof | **0–1** | Engineering ready; merchant absent |
| Decision loop | **0–1** | Weakest area |
| Pilot onboarding | **1** | Works with hand-holding |

---

## Section 10 — Recommended Next Foundation

### Recommendation: **Proof of Value**

**One foundation only** — the next Merchant Value Era foundation should be **Proof of Value** (documented as audit → governance → contracts — not implementation in this task).

### Why Proof of Value (and not the alternatives)

| Alternative | Why not now |
|-------------|-------------|
| **Merchant Understanding** | Requires behavior history and merchant-specific models — depends on Proof of Value metrics existing first |
| **Commercial Readiness** | Platform Readiness Review v1 already covers business readiness; billing/go-live are partner/env blockers, not value-proof blockers |
| **Knowledge Layer** | KL v1 **closed**; further KL work without merchant proof surfaces repeats engineering-first pattern |

### What Proof of Value foundation would govern

1. **Merchant-visible Recovery Proof** — attributed SAR, honest denominators, VIP isolation preserved (KL-C4)  
2. **Delivery-backed recovery status** — acceptance ≠ delivery on merchant surfaces (Provider Truth consumption)  
3. **Value measurement contract** — merchant KPI definitions matching internal metrics (Step 6 of value validation)  
4. **Daily brief as proof surface** — 3–5 items with mandatory what/why/action/confidence  
5. **Tier claim alignment** — no package promise without proof category support  

### Why this is the highest-leverage next step

- **Closes the engineering→merchant gap** documented in §8.2 of value validation foundation  
- **Unlocks commercial motions** blocked today (renewal, referral, honest upsell)  
- **Highest readiness** — Purchase Truth, attribution, Provider Truth, KL, lifecycle already exist  
- **Does not require new intelligence** — surfacing and governing proof, not inventing insights  

Proof of Value becomes the **Merchant Value Era equivalent** of what Provider Reliability Audit was for engineering: evidence first, then governance, then controlled surfacing.

---

## Appendix A — Engineering foundations reviewed

Completed or closed foundations cross-checked against merchant value (from SYSTEM_SUMMARY + institutional memory baseline):

| Foundation | Engineering | Merchant value unlocked |
|------------|-------------|-------------------------|
| Purchase Truth | Closed | Partial — wins only |
| Lifecycle Truth LT-C1 | Enforced | **Yes** — cart rows |
| Knowledge Layer v1 | Closed | Partial — home cards |
| Product Data Foundation | Conditionally closed | None merchant-facing |
| Integration Health v1 | Closed | Admin/ops only |
| Provider Reliability | Measured, deferred activation | None merchant-facing |
| Dashboard Read Model | Governed + measured | Implicit speed |
| Snapshot Generation Optimization | Implemented | None direct |
| Data Growth Governance | Closed | None direct |
| Operational Metrics v1 | Measured | None merchant-facing |
| SaaS Plans Phases 1–4 | Implemented (no billing) | Packaging only |

---

## Appendix B — Source documents

| Document | Used for |
|----------|----------|
| `cartflow_value_validation_foundation_v1.md` | Framework, questions, domains, proof categories |
| `SYSTEM_SUMMARY.md` | Merchant surfaces, routes, foundation status |
| `cartflow_merchant_decision_summary_v1.md` | Decision confidence C− baseline |
| `platform_readiness_review_v1.md` | Commercial / pilot readiness |
| `cartflow_architecture_status_review_v1.md` | Layer closure status |
| `dashboard_read_model_audit_v1.md` | Snapshot vs live read paths |
| `provider_reliability_foundation_v1_audit.md` | Acceptance≠delivery |

---

## Success criteria (this audit)

| Question | Answer |
|----------|--------|
| What value does CartFlow already deliver? | §1 inventory — automation, lifecycle, reasons, VIP, partial KL |
| What can merchants already trust? | §2–§4 — lifecycle labels, captured reasons; not ROI or delivery |
| What prevents indispensability? | §7 — proof, decision, product, operational, commercial gaps |
| What comes next? | §10 — **Proof of Value** foundation |

This audit is the **evidence base** for the next Merchant Value Foundation. No code. No implementation.
