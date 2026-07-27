# Executive Home Research V1

**Status:** Research complete — awaiting approval before Home Constitution V2  
**Date (UTC):** 2026-07-27  
**Scope:** Evidence-based product research only. No redesign. No implementation.  
**Method:** Cross-product pattern analysis of executive / decision-support homes, grounded in cognitive science (cognitive load, progressive disclosure, recognition over recall) and industry practice for BI and operational SaaS.

---

## 1. Research question

What do the world’s best executive dashboards and decision-support products *do* on Home — and which of those patterns should CartFlow adopt or reject for an Executive Home that helps a merchant manage the store better?

This document answers that question. It does **not** specify a new Home layout.

---

## 2. Per-product findings

For each product: the ten required questions.

### 2.1 Microsoft Power BI (executive / app landing)

| # | Finding |
|---|--------|
| 1 | **Question Home answers:** “What is the status of the business areas I care about right now?” (scorecard / landing of pinned apps & KPIs) |
| 2 | **Intentionally hidden:** Raw query definitions, model relationships, DAX, full fact tables, every available report |
| 3 | **Shown first:** Pinned visuals / KPI cards and recently used / recommended content |
| 4 | **Executive actions:** Few — open a report, open an app, respond to an alert; not a dense action toolbar |
| 5 | **Priority order:** User-pinned and role-based scorecards → alerts → recent |
| 6 | **“View details” / drill:** Opens the owning report or a drill-through page with filters preserved |
| 7 | **Never on Home:** Full data model, ETL status (except when broken as an alert), ad-hoc query builders |
| 8 | **Cognitive principles:** Progressive disclosure; recognition (pinned tiles) over recall; exception highlighting |
| 9 | **Shared patterns:** Scorecard first; detail elsewhere; alerts as exceptions |
| 10 | **CartFlow applicability:** High — Home as scorecard + alerts; detail in Workspace / domain pages |

### 2.2 Tableau (pulse / viz landing)

| # | Finding |
|---|--------|
| 1 | **Question:** “Which metrics moved, and which deserve attention?” |
| 2 | **Hidden:** Full workbook authoring, joins, calculated-field editors |
| 3 | **First:** Metric cards / Pulse digests with change direction |
| 4 | **Actions:** Typically 1–3 per metric (explore, follow, share) |
| 5 | **Order:** Magnitude of change / followed metrics → browse |
| 6 | **Details:** Opens workbook / viz with context filters |
| 7 | **Never on Home:** Authoring chrome, data-source plumbing |
| 8 | **Principles:** Pre-attentive encoding (up/down); sparklines for trajectory |
| 9 | **Patterns:** Change-aware cards; exploration deferred |
| 10 | **CartFlow:** High for “what changed” cards; low for free-form viz exploration on Home |

### 2.3 Looker (Looker Home / boards)

| # | Finding |
|---|--------|
| 1 | **Question:** “What do I need to review from my boards and schedules?” |
| 2 | **Hidden:** LookML, explores, SQL |
| 3 | **First:** Boards / favorites and delivered content |
| 4 | **Actions:** Open board, open Look, acknowledge schedule |
| 5 | **Order:** Favorites and schedules → catalog |
| 6 | **Details:** Opens Look or Explore with governed metrics |
| 7 | **Never on Home:** Model development, permission admin (except links) |
| 8 | **Principles:** Governed semantics; role-based content |
| 9 | **Patterns:** Curated boards ≠ catalog |
| 10 | **CartFlow:** Medium — “curated executive surface” yes; self-serve Explore on Home no |

### 2.4 Google Analytics (GA4 Home / Reports snapshot)

| # | Finding |
|---|--------|
| 1 | **Question:** “How is traffic and engagement trending, and what’s notable?” |
| 2 | **Hidden:** Full event schemas, BigQuery exports, DebugView (unless troubleshooting) |
| 3 | **First:** Snapshot KPIs (users, sessions, engagement) + insights cards |
| 4 | **Actions:** Few — open report, follow insight recommendation |
| 5 | **Order:** Snapshot → Insights → collections |
| 6 | **Details:** Named report (Acquisition, Engagement, etc.) |
| 7 | **Never on Home:** Raw hit streams, tag manager config |
| 8 | **Principles:** Snapshot + insight narrative; drill to report taxonomy |
| 9 | **Patterns:** Insights as prioritized exceptions |
| 10 | **CartFlow:** Medium — insights pattern yes; vanity traffic KPIs as Home heroes no (CartFlow is recovery/decision ops) |

### 2.5 Shopify Analytics (Overview)

| # | Finding |
|---|--------|
| 1 | **Question:** “How is the store performing over the selected period?” (sales, orders, sessions) |
| 2 | **Hidden:** Checkout code, theme code, full order line tables (on Overview) |
| 3 | **First:** Period KPIs and primary sales chart |
| 4 | **Actions:** Period control, open report, Live View — not many competing CTAs |
| 5 | **Order:** Totals → trends → report links |
| 6 | **Details:** Named Analytics reports (sales, customers, behavior) |
| 7 | **Never on Overview:** Inventory SKUs, staff permissions, theme editor |
| 8 | **Principles:** One overview surface; reports own depth |
| 9 | **Patterns:** Commerce KPI overview ≠ operational queue |
| 10 | **CartFlow:** Partial — Shopify Overview is **performance**; CartFlow Home should be **attention / decision**. Do not copy KPI wall as primary Home job |

### 2.6 Stripe Dashboard (Home)

| # | Finding |
|---|--------|
| 1 | **Question:** “How is the business performing, and what needs attention now?” |
| 2 | **Hidden:** API keys, webhook payloads, full dispute case files, Radar rules detail |
| 3 | **First:** Overview widgets (volume, success) + **notifications** (disputes, identity, etc.) |
| 4 | **Actions:** Sparse — resolve notification, open payments/customers; customizable widgets |
| 5 | **Order:** Notifications / exceptions → overview metrics → resources |
| 6 | **Details:** Owning product area (Payments, Disputes, Customers, Settings) |
| 7 | **Never on Home:** Secret keys, raw event logs, full API explorer |
| 8 | **Principles:** Exception-first for ops risk; overview for health |
| 9 | **Patterns:** Home = health + unresolved work; depth in domain nav |
| 10 | **CartFlow:** **Very high** — closest analog: money ops + exceptions + calm overview |

### 2.7 HubSpot (Home / Command Center style)

| # | Finding |
|---|--------|
| 1 | **Question:** “What should my team work on today across pipeline and engagement?” |
| 2 | **Hidden:** Full CRM schemas, workflow builders (unless entered), marketing asset libraries |
| 3 | **First:** Tasks, needs attention, pipeline summary |
| 4 | **Actions:** Several task CTAs but grouped as “work queue,” not equal KPI buttons |
| 5 | **Order:** Attention / tasks → pipeline → reports |
| 6 | **Details:** Contact/deal record or report |
| 7 | **Never on Home:** Full workflow canvas, design tools |
| 8 | **Principles:** Work queue as primary; CRM record as system of record |
| 9 | **Patterns:** “Needs attention” before vanity charts |
| 10 | **CartFlow:** High for attention queue; Carts/Communication own the queue detail |

### 2.8 Linear (Home / Inbox)

| # | Finding |
|---|--------|
| 1 | **Question:** “What needs my attention in the work system?” |
| 2 | **Hidden:** Full roadmap databases, cycle analytics dumps, admin billing |
| 3 | **First:** Inbox / my issues / active work |
| 4 | **Actions:** One primary action per item (open, triage, assign) |
| 5 | **Order:** Inbox priority / urgency → projects |
| 6 | **Details:** Issue detail (the decision object) |
| 7 | **Never on Home:** Org charts, full settings, raw git |
| 8 | **Principles:** Extreme focus; keyboard speed; one object type |
| 9 | **Patterns:** Home ≈ inbox of decisions; detail = issue |
| 10 | **CartFlow:** High for “Home as inbox of decisions”; Workspace = issue detail |

### 2.9 Notion Home

| # | Finding |
|---|--------|
| 1 | **Question:** “Where do I resume, and what’s relevant to me?” |
| 2 | **Hidden:** Workspace schema, permission graphs, API |
| 3 | **First:** Recents, favorites, assigned tasks / my work |
| 4 | **Actions:** Open page; create — not metric CTAs |
| 5 | **Order:** Personal relevance → workspace browse |
| 6 | **Details:** The page itself |
| 7 | **Never on Home:** Database schema editors as default |
| 8 | **Principles:** Continuity and personalization over global KPIs |
| 9 | **Patterns:** Resume > report |
| 10 | **CartFlow:** Low for KPI design; medium for “resume primary decision” |

### 2.10 Superhuman (triage home)

| # | Finding |
|---|--------|
| 1 | **Question:** “What is the next email I should act on?” |
| 2 | **Hidden:** Full archive browsing as default, settings, analytics of send volume |
| 3 | **First:** Single focused inbox item / split inbox |
| 4 | **Actions:** Extremely few — reply, archive, remind, open |
| 5 | **Order:** Strict triage order (importance / split) |
| 6 | **Details:** Thread (still the same object, expanded) |
| 7 | **Never on Home:** Marketing charts, admin |
| 8 | **Principles:** One decision at a time; speed; hide the rest |
| 9 | **Patterns:** Single primary focus; everything else deferred |
| 10 | **CartFlow:** **Very high** for “one top decision”; do not mirror email chrome |

### 2.11 Vercel Dashboard

| # | Finding |
|---|--------|
| 1 | **Question:** “Is my deployment healthy, and what failed?” |
| 2 | **Hidden:** Build logs (until failure), env secret values, full project graph |
| 3 | **First:** Project status, latest deployments, failures |
| 4 | **Actions:** Redeploy / open deployment / fix — few per incident |
| 5 | **Order:** Failures and latest → projects list |
| 6 | **Details:** Deployment or project page |
| 7 | **Never on Home:** Secret plaintext, full CDN config |
| 8 | **Principles:** Status + exception; logs on demand |
| 9 | **Patterns:** Health strip + incident drill-down |
| 10 | **CartFlow:** High for store health strip; logs/diagnostics never on Home |

### 2.12 Datadog (executive / service views)

| # | Finding |
|---|--------|
| 1 | **Question:** “Is the system healthy, and which services are burning?” |
| 2 | **Hidden:** Raw span dumps, query language (until explore), billing |
| 3 | **First:** SLO / status, monitors firing, top services |
| 4 | **Actions:** Acknowledge monitor, open service, runbook link — limited |
| 5 | **Order:** Firing / breached → watchlist → explore |
| 6 | **Details:** Service page, monitor, or notebook |
| 7 | **Never on Home:** Full APM flame graphs as default landing |
| 8 | **Principles:** Alert fatigue control; severity ordering |
| 9 | **Patterns:** Severity-ranked exceptions; deep telemetry elsewhere |
| 10 | **CartFlow:** High for severity ranking of situations; reject metric soup |

### 2.13 Grafana (executive / overview dashboards)

| # | Finding |
|---|--------|
| 1 | **Question:** “Are the critical golden signals in band?” |
| 2 | **Hidden:** Panel JSON, datasource config, alert rule editors |
| 3 | **First:** Row of golden signals / SLA panels |
| 4 | **Actions:** Usually zero primary CTAs — navigation via panel click |
| 5 | **Order:** Left-to-right / top-to-bottom by designer-defined importance |
| 6 | **Details:** Drilldown dashboard or Explore |
| 7 | **Never on overview:** Datasource credentials, provisioning YAML |
| 8 | **Principles:** Golden signals; one screen; variables for scope |
| 9 | **Patterns:** Overview dashboard ≠ Explore |
| 10 | **CartFlow:** Medium — golden signals as health; Explore-like freedom on Home no |

### 2.14 Composite: “executives making operational decisions”

Across payments, commerce, support, and eng ops products that force same-day decisions:

| Pattern | Evidence |
|---------|----------|
| Home answers **state + next move**, not **full analysis** | Stripe, HubSpot, Linear, Vercel, Datadog |
| Exceptions outrank charts | Stripe notifications, Datadog monitors, HubSpot tasks |
| One primary decision object | Superhuman thread, Linear issue, Stripe dispute |
| Details open the **owner surface** | Always a named destination, not a modal dump of everything |
| Settings / diagnostics stay out | Universal |

---

## 3. Cross-product findings

### 3.1 The Home question converges

Successful executive Homes answer a variant of:

> **What is the state of my operation, and what (if anything) needs my decision or action now?**

They do **not** primarily answer:

- “Show me every metric we can compute.”
- “Explain the full causal model.”
- “Let me build a report.”

### 3.2 Information deliberately withheld on Home

Repeated exclusions across products:

| Hidden class | Examples |
|--------------|----------|
| Construction / authoring | Power BI model, LookML, Grafana JSON |
| Full operational tables | Order lines, cart rows, email archives |
| Secrets & diagnostics | API keys, raw logs, query plans |
| Secondary time ranges | Month walls when “today / now” is the job |
| Equal-weight metrics | 20 KPIs with no priority |

### 3.3 What is shown first

Almost always, in this order:

1. **Exceptions / needs attention** (if any)  
2. **Health / status summary** (calm or alert)  
3. **One primary decision or focus**  
4. **Secondary context cards** (few)  
5. **Navigation into owning domains**

### 3.4 How many executive actions

| Band | Typical count | Products |
|------|---------------|----------|
| Ultra-focused | **1** primary action | Superhuman, Linear (per item) |
| Executive ops | **1–3** primary CTAs visible without scroll | Stripe, Vercel, HubSpot attention |
| BI scorecard | **0–2** global actions; cards are entry points | Power BI, Tableau Pulse, Grafana |

**Research conclusion:** More than ~3 competing primary actions on Home correlates with “report browsing,” not “executive control.”

### 3.5 How priorities are ordered

Repeated ranking rules:

1. **Severity / irreversibility** (dispute, outage, blocked recovery)  
2. **Time sensitivity** (today / SLA)  
3. **Business value at stake** (revenue, VIP, conversion)  
4. **User pin / role** (BI tools)  
5. **Recency** only after the above  

Vanity popularity (sessions, pageviews) rarely outranks exceptions on ops Homes.

### 3.6 What “View Details” opens

Cross-product rule:

> Details open the **constitutional owner** of that information — not a second Home.

| Home signal | Destination |
|-------------|-------------|
| KPI / chart | Owning report or Explore |
| Alert / monitor | Incident / service / case |
| Task / issue | Record detail |
| Insight | Underlying report with filters |

### 3.7 What never appears on Home

Universal “never” list:

- Developer diagnostics and internal IDs as UI content  
- Full queues / tables meant for operators’ working pages  
- Settings and unfinished roadmap placeholders  
- Evidence packs, confidence math, long explanations  
- Duplicate second heroes that restate the same decision  

### 3.8 Cognitive principles repeatedly used

| Principle | Source tradition | Home implication |
|-----------|------------------|------------------|
| **Cognitive Load Theory** (Sweller) | Instructional design | Minimize extraneous load; show only decision-relevant chunks |
| **Miller’s working memory (~7±2)** | Psychology | Cap simultaneous top-level cards (practice target often **4–7**, prefer **≤5** for ops) |
| **5-second / glance comprehension** | Executive dashboard practice | State + next action readable immediately |
| **Progressive disclosure** | HCI (Nielsen et al.) | Summary → owner page → evidence |
| **Recognition over recall** | HCI heuristics | Named CTAs (“View details”) to known places |
| **Pre-attentive attributes** (Ware / Tufte) | Viz science | Position, length, one accent for status — not decoration |
| **Exception-based management** | Ops / SRE | Silence when healthy; amplify when not |
| **One primary job per screen** | Product design | Home ≠ Workspace ≠ Queues |

### 3.9 Executive UX patterns that recur

1. **Inverted pyramid** — headlines first, depth later  
2. **Health + exception dual** — calm baseline with interruptible alerts  
3. **Single top decision** — Superhuman/Linear influence on ops products  
4. **Owner-linked drill-down** — never orphan details  
5. **Sparse primary CTAs** — 1–3, same verb family  
6. **Role-curated Home** — not a dump of all modules  
7. **Mobile meaning parity** — same decisions, different layout density  
8. **Customization within rails** — Stripe widgets; not free chaos  

---

## 4. Decision hierarchy (research synthesis)

A durable hierarchy observed across successful products:

```text
L0  Identity / context   →  “Whose operation am I seeing?” (session/store)
L1  Store / system health →  “Is the operation OK, at risk, or urgent?”
L2  Top decision          →  “What is the single most important move?”
L3  Supporting domains    →  Product / carts / communication teasers (links only)
L4  Owner surfaces        →  Workspace, Products, Carts, Communication, Settings
L5  Evidence & diagnostics→  Never on Home; only on owner or Admin/Dev
```

**Home owns L1–L3.**  
**Workspace owns L2 depth (why / evidence / impact).**  
**Domain pages own L3–L4 operational truth.**  
**Admin/Dev owns L5.**

---

## 5. Scientific justification (compact)

1. **Working memory limits** make multi-equal KPI walls fail under time pressure; executives satisfice on the first coherent signal (Simon’s bounded rationality).  
2. **Extraneous cognitive load** rises with decorative charts, duplicate narratives, and technical labels — measured in dashboard redesign studies as slower time-to-insight.  
3. **Progressive disclosure** preserves germane load (learning the decision) while cutting extraneous load (parsing unused data).  
4. **Exception-based attention** matches signal detection theory: constant high-signal noise trains users to ignore the dashboard.  
5. **Action coupling** (insight → owned action path) outperforms diagnosis-only surfaces for operational outcomes — consistent with decision-support system literature (DSS: intelligence → design → choice).

---

## 6. What CartFlow should adopt

Aligned with CartFlow’s merchant job (recover carts, decide, communicate) and with Dashboard Constitution V1 ownership:

| Adopt | Why (research) | CartFlow mapping |
|-------|----------------|------------------|
| Home question = state + next attention | Cross-product convergence | Keep: «ماذا يجب أن أعرف الآن عن متجري؟» |
| Health first, then one top decision | Stripe / Datadog / Superhuman | Store Health → Today’s Top Decision |
| ≤ few supporting domain teasers | Miller + ops Homes | Product / Cart / Communication summaries only |
| Every card ends with owner link (“عرض التفاصيل”) | Universal drill rule | Already constitutional; keep strict |
| Details open owner pages only | Power BI / Stripe / Linear | Workspace / Products / Carts / Communication |
| Hide evidence, confidence, tables, history on Home | Progressive disclosure | Already required; reinforce in Constitution V2 |
| Severity-ordered priorities | Datadog / HubSpot | Situation priority → primary decision |
| Exception when constrained (e.g. no phone) | Stripe notifications | Communication teaser → Carts action |
| Desktop/Mobile same meaning | Executive mobile practice | Already acceptance criterion |
| Session identity available but not Home content | Stripe account vs Home widgets | Account Identity panel (done) — not Home cards |

---

## 7. What CartFlow should reject

| Reject | Why | Seen as anti-pattern in |
|--------|-----|-------------------------|
| KPI month walls / equal metric grids on Home | Turns Home into reporting, not control | Shopify Overview copy without ops exceptions; weak BI Homes |
| Multiple competing “primary” decisions | Breaks Superhuman/Linear focus | Overloaded HubSpot-like task soup without ranking |
| Evidence / confidence / situation IDs on Home | Extraneous load; developer leakage | GA Debug-style surfaces |
| Long explanations and duplicate heroes | Duplicate understanding | Failed executive dashboards (report-simple critiques) |
| Operational cart tables on Home | Domain ownership violation | Putting Linear’s full backlog on Home |
| Settings, setup, roadmap placeholders on Home | Stripe/Vercel never do this | Feature-marketing Homes |
| Free-form Explore / report builder on Home | Looker Explore ≠ Home | Power BI authoring |
| Calm Home that hides active urgency | Violates exception-based management | “Green” dashboards while monitors fire |
| Different decisions on mobile vs desktop | Meaning split = product bug | Inconsistent responsive BI apps |

---

## 8. CartFlow-specific applicability matrix

| Pattern | Applicable? | Notes |
|---------|-------------|-------|
| Stripe-style Home (health + notifications) | **Yes — primary reference** | Closest to merchant money ops |
| Superhuman single focus | **Yes — for Top Decision** | One P1; secondaries as links only |
| Linear inbox | **Yes — metaphor** | Workspace = issue detail |
| Shopify Analytics Overview | **Selective** | Good for domain Analytics later; **not** CartFlow Executive Home job |
| Power BI / Tableau scorecards | **Selective** | Pinning/customization later; not V2 must-have |
| Datadog severity | **Yes** | Order situations by urgency/value |
| Grafana Explore | **No on Home** | Belongs Admin/Dev or future analysis |
| Notion recents | **Low** | Continuity secondary to store state |
| GA vanity traffic | **No as Home hero** | Not CartFlow’s executive question |

---

## 9. Implications for Home Constitution V2 (research only — not a draft constitution)

When Constitution V2 is authorized, research recommends it encode at least:

1. **One Home question** (state + now).  
2. **Fixed information budget** (health, one top decision, ≤3 domain teasers).  
3. **Hard exclusions** (evidence, confidence, tables, IDs, settings, month KPI walls).  
4. **Mandatory owner links** for every teaser.  
5. **Severity ordering law** for choosing the top decision.  
6. **Silence when healthy** — do not invent urgency.  
7. **Parity law** — Desktop/Mobile identical meaning.

No layout, visual redesign, or implementation is implied here.

---

## 10. Sources & grounding (non-exhaustive)

**Product surfaces (observed patterns):** Power BI apps/scorecards; Tableau Pulse; Looker Home/boards; GA4 Home/Insights; Shopify Analytics Overview; Stripe Dashboard Home docs; HubSpot Home/attention; Linear Home/Inbox; Notion Home; Superhuman triage; Vercel Dashboard; Datadog monitors/service views; Grafana overview vs Explore.

**Practice & science:** Cognitive Load Theory (Sweller); Miller’s working-memory bounds; progressive disclosure / Nielsen heuristics; Tufte / pre-attentive perception; executive “5-second rule” dashboard practice; exception-based ops management (SRE-style); DSS intelligence→design→choice framing.

---

## 11. STOP

- Home implementation work remains **stopped**.  
- This file is the **only** deliverable for Executive Home Research V1.  
- **Do not** draft Home Constitution V2 until explicit approval.  
- **Do not** redesign or implement Home from this research alone.

---

*End of Executive Home Research V1*
