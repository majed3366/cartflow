# Home Information Budget V1

**Status:** Awaiting approval before Home Constitution V2  
**Date (UTC):** 2026-07-27  
**Basis:** [`Executive Home Research V1`](../executive_home_research_v1/EXECUTIVE_HOME_RESEARCH_V1.md)  
**Constraint:** Information budget only. No redesign. No UI. No implementation. No Constitution V2 in this deliverable.

**Home question (locked for budgeting):**  
ماذا يجب أن أعرف الآن عن متجري؟  
*(What should I know right now about my store?)*

**Home nature (locked):** Home is an **executive briefing** — not an analytics dashboard, not a reporting page, not an operational page. Every sentence on Home must have executive value.

---

## Executive Information Value Law

**Constitutional.** Overrides any desire to show “correct but inert” data on Home.

A piece of information is allowed to occupy space on Home **only if it changes executive behaviour**.

| The question is NOT | The question IS |
|---------------------|-----------------|
| “Is this information correct?” | “Will this information change what the merchant does next?” |

If the answer is **NO**, the information does **not** belong on Home.  
It belongs to its **constitutional owner page** instead.

### Allowed (executive value)

| Example | Why it changes what the merchant does next |
|---------|--------------------------------------------|
| ✓ Review checkout experience. | Directs the next move |
| ✓ Product Raven needs attention. | Names the subject of attention |
| ✓ Customer communication is blocked. | Forces a path to unblock recovery |
| ✓ Recovery is operating normally. | Authorizes calm — *not* acting is the behaviour change |

### Not allowed (no executive value on Home)

| Example | Why it fails the law | Owner |
|---------|----------------------|-------|
| ✗ 172 carts. | Count without a next move | Carts |
| ✗ 8 customers. | Headcount without a decision | Carts / Communication |
| ✗ Confidence 87%. | Technical certainty; does not choose an action | Workspace |
| ✗ Timeline. | History / reporting | Owner domain or Workspace |
| ✗ Technical status. | Diagnostics | Admin / Dev |
| ✗ Operational history. | Reporting | Owner domain |
| ✗ Raw observations. | Evidence layer | Workspace / Admin |

**Test before paint:** For every candidate sentence, number, or card on Home — if removing it would not change the merchant’s next action (including the deliberate action of *not intervening*), it is over budget.

---

## Budget law

Home may spend attention only on information that:

0. **Satisfies the Executive Information Value Law** (changes what the merchant does next), and  
1. Answers the Home question in under the reading-time budget, and  
2. Has no deeper owner that must hold the truth, and  
3. Links to exactly one owner when the merchant needs more.

Anything that fails (0)–(3) is **out of budget**.

---

## 1. What information deserves a place on Home?

| # | Information | Why it belongs on Home | Why it does not belong elsewhere as the *first* surface | Scientific / research justification |
|---|-------------|------------------------|----------------------------------------------------------|-------------------------------------|
| A | **Store Health** (one status: calm / opportunity / needs attention / urgent / insufficient evidence) | Answers “state of my operation now” | Workspace explains *why*; domains operate *queues* — neither replaces the glanceable state | Stripe / Vercel / Datadog health-first; 5-second rule; golden-signal pattern |
| B | **Today’s Top Decision** (one primary decision statement + one recommended move, no evidence pack) | Answers “what needs my decision now” | Workspace owns why/evidence/impact; Home only names the decision | Superhuman / Linear single focus; DSS “choice” before “design” |
| C | **Product Highlights** (≤1 short teaser of product-level attention, not product analytics) | Merchants need product signal without opening Products every time | Products owns performance/interest/conversion depth | Progressive disclosure; supporting domain teaser (research §3.3) |
| D | **Cart Summary** (one executive line about cart *state that changes behaviour* — e.g. follow-up needed / stable — **not** bare counts like “172 carts”, not rows) | Carts are the core recovery object; Home must surface stake as a next-move signal | Carts owns per-cart truth and raw counts | Executive Information Value Law; Stripe exception + ops stake |
| E | **Communication Summary** (one constraint/status line that changes behaviour — e.g. blocked by missing phone — not “8 customers”, not message logs) | Communication failures block recovery; must interrupt calmly | Communication owns facts, counts, and history | Executive Information Value Law; exception-based management |

**Budget total for (A)–(E):** these five slots are the **maximum content classes** on Home. Not every class must paint when empty/healthy (silence is allowed).

---

## 2. What information must NEVER appear on Home?

| Forbidden class | Why never on Home | Where it belongs | Scientific / research justification |
|-----------------|-------------------|------------------|-------------------------------------|
| Bare counts / headcounts without a next move (e.g. “172 carts”, “8 customers”) | Correct but inert — fails Executive Information Value Law | Carts / Communication | Value Law; research: Home ≠ reporting |
| Evidence packs, proof lists, “why this decision” essays | Extraneous load; duplicates Workspace | Workspace | Progressive disclosure; Cognitive Load Theory (extraneous) |
| Confidence scores, model certainty, scoring math | Technical; not merchant executive language | Workspace (if needed) / Admin | Research §3.7 never-list; language constitution |
| Situation IDs, registry names, `cs:…`, `simulation_run_id`, merchant diagnostics | Developer leakage | Admin / Dev only | Cross-product: secrets & diagnostics off Home |
| Tables (carts, messages, products, SKUs) | Operational working surfaces | Carts / Communication / Products | Linear/HubSpot: queues ≠ Home |
| Month / period KPI walls, equal-weight metric grids | Turns Home into reporting | Future Analytics (not Home); Settings never | Reject Shopify-Overview-as-Home; Miller overload |
| Long explanations, duplicate heroes, second “primary decision” | Competing L2 signals | One Top Decision only; rest are teasers | Superhuman focus; >3 primaries → browsing |
| Settings, setup wizards, roadmap / “قريباً”, locked placeholders | Configuration ≠ now-state | Settings | Stripe/Vercel never put settings on Home |
| Full Workspace decision cards (impact, alternatives, evidence) | Home would become Workspace | Workspace | Owner-linked drill-down law |
| Message content, delivery logs, template editors | Communication depth | Communication | Domain ownership |
| Per-product conversion funnels, hesitation analysis UI | Products depth | Products | Progressive disclosure |
| Account secrets, API keys, env dumps | Security / noise | Settings / Admin | Universal never-list |

---

## 3. Maximum number of cards

| Limit | Value | Rule |
|-------|-------|------|
| **Hard maximum** | **5** cards | Store Health · Top Decision · Product Highlights · Cart Summary · Communication Summary |
| **Soft target when healthy** | **2–3** visible cards | Health + Top Decision (or calm health alone) + only domain teasers that carry a non-zero signal |
| **Minimum when urgent** | **2** | Health (urgent) + Top Decision — domain teasers may collapse to links inside those cards but must not exceed 5 total cards |

**Why:** Research practice targets ≤5 ops cards (Miller; executive ops band). Five content classes match Dashboard Constitution ownership teasers without KPI walls.

**Why not elsewhere:** Card count is a Home budget, not a Workspace/Products constraint.

**Science:** Working-memory bounds; inverted pyramid; cognitive load from equal cards.

---

## 4. Maximum number of executive actions

| Limit | Value | Definition |
|-------|-------|------------|
| **Primary executive actions on Home** | **1** | The single recommended move attached to Today’s Top Decision (or the health interrupt if it *is* the decision) |
| **Secondary navigational actions** | **≤4** | At most one “عرض التفاصيل” per non-primary card (see §5) — these are *navigation*, not competing executive choices |
| **Competing P1 CTAs** | **0** | Never two buttons that both claim “do this now” for different decisions |

**Why:** Superhuman/Linear and research §3.4: >3 competing primary actions → report browsing.

**Why not elsewhere:** Workspace may expose multiple decision actions; Home must not.

**Science:** Decision-support “choice” stage; signal detection — multiple P1s train ignore.

---

## 5. Maximum number of “View Details”

| Limit | Value | Rule |
|-------|-------|------|
| **Hard maximum** | **5** | At most one “عرض التفاصيل” (or equivalent owner link) per card |
| **Required** | Every painted card that is not purely calm-empty must expose exactly **one** owner link | No orphan diagnosis |
| **Destination** | Constitutional owner only | Top Decision → Workspace; Product → Products or Workspace per ownership law; Cart → Carts; Communication → Communication; Health → Workspace if decision-bearing, else no fake details |

**Why:** Cross-product drill law — details open the owner, not a second Home.

**Why not elsewhere:** Other pages may have many links; Home budget caps them.

**Science:** Recognition over recall; progressive disclosure; action coupling.

---

## 6. Maximum reading time

| Limit | Value |
|-------|-------|
| **Glance comprehension (mandatory)** | **≤ 5 seconds** to know: health state + whether a decision is waiting |
| **Full Home read (mandatory)** | **≤ 30 seconds** to read all painted cards and know where to click next |
| **Failure condition** | If a trained merchant needs >30s to find the next move, Home is over budget |

**Why:** Executive 5-second rule (research); CartFlow prior CEO 30s review standard aligns with full-read budget.

**Why not elsewhere:** Workspace/Products may require minutes; Home must not.

**Science:** Time-pressure decision making; glance comprehension studies in executive BI practice.

---

## 7. Maximum cognitive load

| Dimension | Budget |
|-----------|--------|
| **Simultaneous top-level chunks** | **≤ 5** (one per card class) |
| **Independent decisions presented as primary** | **≤ 1** |
| **Status colors / severity accents in view** | **≤ 1 dominant** (health or top decision) — others muted |
| **Narrative sentences per card** | **≤ 2** short sentences (or 1 status + 1 action line) |
| **Numbers per card** | **≤ 2** salient numbers (e.g. count + money) — not a metric grid |
| **Extraneous load** | **Zero** decorative charts, duplicate headlines, tech IDs, evidence |

**Why:** Cognitive Load Theory — cut extraneous; preserve germane (understanding the next move).

**Why not elsewhere:** Domain pages may carry higher germane load for their job.

**Science:** Sweller CLT; Miller; pre-attentive encoding limits; research §3.8.

---

## 8. Which information must always stay in Workspace?

| Must stay in Workspace | Why not on Home | Research link |
|------------------------|-----------------|---------------|
| Decision **Why** | Explanation is choice-support depth | Progressive disclosure |
| **Evidence** / proof / supporting observations | Evidence packs are L5/L4 depth | Never-list §3.7 |
| **Confidence** / certainty language | Technical; slows glance | Language + load |
| **Expected impact** | Decision design stage | DSS design≠intelligence on Home |
| **Recommended action detail** (steps, alternatives, tradeoffs) | Home states the move; Workspace elaborates | Owner drill-down |
| Category landscape / decision inventory beyond the single P1 | Multiple decisions = Workspace inbox | Linear issue list ≠ Home |
| Any second “primary” decision body | Would break single-focus budget | Superhuman |

**Home may only carry:** the **title/statement** of the Top Decision + link to Workspace.

---

## 9. Which information must always stay in Products?

| Must stay in Products | Why not on Home | Research link |
|-----------------------|-----------------|---------------|
| Product performance tables / rankings | Working surface | Domain queues ≠ Home |
| Interest / conversion / purchase behaviour detail | Analytic depth | Shopify reports pattern off Overview-as-exec |
| Hesitation analysis UI | Diagnostic | Progressive disclosure |
| Multi-product comparison grids | Load | Miller |
| Product-level decisions framed as decisions | Decisions → Workspace | Ownership law |

**Home may only carry:** ≤1 **Product Highlights** teaser (signal + link).

---

## 10. Which information must always stay in Carts?

| Must stay in Carts | Why not on Home | Research link |
|--------------------|-----------------|---------------|
| Per-cart rows (customer, product, value, status, last event) | Operational table | Research forbidden tables |
| Filters, tabs, VIP queue chrome | Working UI | HubSpot queue ≠ Home |
| Next operational action **per cart** | Carts question | Domain ownership |
| Executive business recommendations about carts | Those are Workspace | Constitution: Carts ops-only |

**Home may only carry:** one **Cart Summary** line (aggregate stake / need) + link to Carts.

---

## 11. Which information must always stay in Communication?

| Must stay in Communication | Why not on Home | Research link |
|----------------------------|-----------------|---------------|
| Fact grid: sent / delivered / replied / returned / no phone / needs follow-up (full) | Communication question | Facts owner |
| Message history / threads | Logs | Stripe: cases off Home |
| Templates, WhatsApp setup entry points (as page job) | Settings/Comms depth | Settings off Home |
| Per-customer communication problems list | Working queue | Exception detail on owner |

**Home may only carry:** one **Communication Summary** (especially constraints that block recovery) + link to Communication (or Carts for affected customers when that is the owner action).

---

## 12. Information priority from top to bottom

Strict paint / reading order on Home:

| Priority | Slot | Rule |
|----------|------|------|
| **P0** | Session/context identity | Not a Home card — available from account control; never consumes Home budget |
| **P1** | **Store Health** | Always first among Home content |
| **P2** | **Today’s Top Decision** | Immediately after health; omitted only if health is calm **and** no decision exists |
| **P3** | **Product Highlights** | Only if non-empty signal |
| **P4** | **Cart Summary** | Only if non-empty signal |
| **P5** | **Communication Summary** | Only if non-empty signal; may rise visually when it **is** the blocking exception, but must not create a second P2 decision card |

**Ordering law for choosing P2 content:** severity / irreversibility → time sensitivity → business value (research §3.5). Recency alone never beats severity.

**Why this order:** Matches research §3.3 (exceptions/health → primary decision → domain teasers).

**Why not elsewhere:** Domain pages use their own question order; Home order is executive glance order.

---

## 13. Information that is always hidden unless requested

“Requested” = merchant opens the owner page, expands Workspace, or opens Account Identity / Settings / Admin.

| Hidden unless requested | Request path | Why hidden on Home |
|-------------------------|--------------|--------------------|
| Evidence, why, confidence, impact | Workspace | Progressive disclosure |
| Product analytics depth | Products | Load budget |
| Cart rows & filters | Carts | Tables forbidden |
| Communication fact grid & logs | Communication | Domain depth |
| Month KPIs / historical walls | Not on Home (future Analytics or Settings reports — never Home default) | Reject KPI wall |
| Setup / connection wizards | Settings | Config ≠ now |
| Account email, merchant ID, session fingerprint | Account Identity panel | Identity ≠ Home content |
| Developer diagnostics, run IDs, ORV chips | Admin / Dev | Never merchant Home |
| Secondary decisions (P2, P3…) | Workspace inventory | Single primary on Home |
| Charts beyond a minimal health affordance | Owner / future Analytics | Pre-attentive budget; no chartjunk |

---

## Budget summary (normative)

| Parameter | Budget |
|-----------|--------|
| Executive Information Value Law | **Mandatory gate** — no Home space without behaviour change |
| Content classes | **5 max** (Health, Top Decision, Product, Carts, Communication) |
| Cards painted | **≤ 5**; prefer **2–3** when calm |
| Primary executive actions | **1** |
| View Details links | **≤ 5** (≤1 per card) |
| Glance time | **≤ 5 s** |
| Full read | **≤ 30 s** |
| Primary decisions | **1** |
| Sentences / card | **≤ 2** |
| Salient numbers / card | **≤ 2** |

---

## STOP

- This is the **only** deliverable for Home Information Budget V1.  
- **Do not** write Home Constitution V2 until this budget is **explicitly approved**.  
- **Do not** redesign or implement Home from this document alone.

---

*End of Home Information Budget V1*
