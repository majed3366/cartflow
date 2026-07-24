# CartFlow Architecture & Surface Alignment Audit V1

**Document type:** Architectural alignment audit (read-only)  
**Date (UTC):** 2026-07-24  
**Status:** Complete — awaiting Product / CEO review before Product Intelligence V1  
**Scope:** Merchant surfaces only (Home, Decision Workspace, Carts, Communication, Settings)  
**Out of scope:** Product Intelligence implementation · UI redesign · new merchant features  

**Law (draft):** Binding page ownership is defined in [`docs/product/PRODUCT_CONSTITUTION_V1.md`](../product/PRODUCT_CONSTITUTION_V1.md), including Principle 0 — *Every Surface Must Lead to a Decision*. This audit is the evidence pack against that constitution.

---

## 0. Verdict

| Dimension | Verdict |
|-----------|---------|
| Painted Home UI (post Stabilization) | **Aligned** — five executive teasers; single paint path when `home_surface_mode=executive_summary_v1` |
| Summary / data transport for Home | **Misaligned** — Home still pays for full MEIF, ORV, legacy Home, Pulse, KPIs, reason panels |
| Decision Workspace ownership | **Split** — Cart Workspace (live) vs MEIF/BFL Finding Decision Engine (built, often unpainted) |
| Carts | **Misaligned** — ops + Merchant Intelligence recommendations |
| Communication | **Split / partial** — `#communication` stub vs `#messages` history with PII |
| Settings | **Mostly aligned** — mild scope creep only |
| Ready for Product Intelligence V1? | **No** — foundations need ownership + Home transport alignment first |

**Constitution used for this audit** (user brief):

| Surface | Merchant question |
|---------|-------------------|
| Home | What should I know about my store right now? |
| Decision Workspace | What decision should I make, and why? |
| Carts | What is happening to each cart? |
| Communication | What happened during customer communication? |
| Settings | Configuration only |

---

## 1. Current page responsibilities

### 1.1 Home (`#home`)

| Field | Current state |
|-------|---------------|
| **Intended question** | What should I know about my store right now? |
| **Painted responsibility** | Executive Summary teasers only (`home_executive_summary_v1`) |
| **Sections painted** | صحة العمل · قرارات اليوم · ملاحظات المنتجات · السلال · التواصل |
| **Owner module** | `services/home_executive_summary_v1/` + `static/home_executive_summary_v1.js` |
| **Transport reality** | `/api/dashboard/summary` finalize still builds full MEIF (all five page packages), ORV, adaptive cognition, commerce/Pulse, legacy `merchant_home_experience_v1`, KPI/month/reason projections |
| **Alignment** | UI ✓ · Transport ✗ |

### 1.2 Decision Workspace (`#workspace`)

| Field | Current state |
|-------|---------------|
| **Declared MEIF question** | Why is this happening, and what should I review? |
| **Live merchant surface** | Cart Workspace V1 (Zones A–E, command cards) via `/api/cart-workspace/v1/projection` |
| **Parallel package** | MEIF `pages.decision_workspace` (BFL findings + Finding Decision Engine) — built on every summary; **not painted while HES claims Home** (MEIF apply gated behind failed HES) |
| **Alignment** | Dual owner · question wording differs from constitution · products/history incomplete on CW path |

### 1.3 Carts (`#carts`)

| Field | Current state |
|-------|---------------|
| **Declared MEIF question** | What is happening in carts, and what needs attention? |
| **Ops responsibility** | Cart list, filters, status, proof/timeline, archive/reopen |
| **Extra responsibility (violation)** | Merchant Intelligence / value stories / decision-style cards / optional MEIF findings («لماذا تهمّ هذه السلال؟») |
| **Primary API** | `/api/dashboard/normal-carts` (plus MI/value-story attach) |
| **Alignment** | Ops present · recommendations violate constitution |

### 1.4 Communication (`#communication` / `#messages`)

| Field | Current state |
|-------|---------------|
| **Declared MEIF question** | What happened in communication, and what needs follow-up? |
| **Nav target** | `#communication` when MEIF on |
| **MEIF package** | Ops counts (sent/schedules) + findings — often **unpainted** under HES |
| **Real history surface** | `#messages` — delivery/reply status **and** masked phone + full message body |
| **Alignment** | Status tracking partial · PII/content on messages · surface split |

### 1.5 Settings (`#settings` + siblings)

| Field | Current state |
|-------|---------------|
| **Declared question** | How do I control platform behavior and configuration? |
| **Owns** | Store connection, subscription, notification toggles, widget display prefs, operating mode; siblings WhatsApp / Widget / Plans; Diagnostics relocated here |
| **Unused** | MEIF `pages.settings` package has no dedicated painter |
| **Alignment** | Mostly ✓ · minor ops bleed (e.g. month cart line from summary) |

---

## 2. Recommended final page responsibilities

| Surface | Owns (single question) | May show | Must never show |
|---------|------------------------|----------|-----------------|
| **Home** | What should I know about my store right now? | Short summary · status · count · View Details for: Store Health, Today's Decisions, Product Observations, Cart Summary, Communication Summary | Reporting walls · raw tables · full decision cards · full ORV analysis · MI · KPI grids · setup theatre as primary content |
| **Decision Workspace** | What decision should I make, and why? | Decision · reason · evidence · confidence · suggested action · related products · historical context when available | Raw operational cart tables · Home executive bands · communication logs |
| **Carts** | What is happening to each cart? | Product · customer · value · status · timeline · stage · next **operational** action | Business recommendations · product intelligence · decision engine cards |
| **Communication** | What happened during customer communication? | Sent · Delivered · Failed · Replied · Returned · No phone · Waiting | Product intelligence · decision recommendations · full message bodies as default (PII policy TBD) |
| **Settings** | Configuration only | Connections, templates, toggles, plans, diagnostics | Merchant decisions · cart ops · intelligence |

**Product Intelligence V1** (future, not in this audit): owns product findings. Home may **tease** count/summary only; never own analysis.

---

## 3. Responsibilities to remove

| Remove from | Responsibility | Why |
|-------------|----------------|-----|
| Home transport | Full MEIF five-page package on every summary | Home needs teaser inputs only |
| Home transport | Full ORV (evidence/diagnostics) before paint | Slim observation package / deferred detail API |
| Home transport | Legacy `merchant_home_experience_v1` + Daily Brief attach when HES on | Superseded by HES |
| Home transport | Commerce Signals + Pulse when Pulse UI off | Dead cost on critical path |
| Home transport | Double MEIF attach (live builder + finalize) | Duplicated calculation |
| Home boot | Eager `/normal-carts` + `/messages` regardless of hash | Loads page-owned data on Home entry |
| Carts | MI value stories / recommendation cards as primary content | Violates ops-only constitution |
| Carts | MEIF business-finding recommendations on carts focus | Belongs to Decision / Product Intelligence |
| Communication (`#messages`) | Product-adjacent interpretation; default full message body + phone as intelligence surface | Constitution = status tracking |
| Decision | Parallel “decision of the day” ownership on Home beyond teaser | Home routes; Decision owns |

---

## 4. Responsibilities to move

| Responsibility | From | To |
|----------------|------|-----|
| Full finding / decision cards (why, evidence, confidence, action, products, history) | Home / MEIF Home sections / Carts MI | **Decision Workspace** (single owner) |
| Durable cart list + timeline + stage + ops next action | Summary bloat / Home month | **Carts** (on-demand API) |
| Communication status timeline (sent/delivered/failed/replied/…) | Split `#communication` stub + `#messages` | **One Communication surface** (prefer `#communication` as primary; `#messages` merge or redirect) |
| Observation detail / product-bound analysis | Home in-place expand + full ORV on summary | **Product Intelligence** (future) or deferred Observation detail endpoint — Home keeps teaser only |
| Setup / activation theatre | Competing with Home executive story | **Settings → Store Setup** (already partly relocated; keep off Home primary) |
| Reason analytics panels (7d/30d) | Live summary builder | **Own analytics/reasons surface** or Settings diagnostics — not Home critical path |

---

## 5. Responsibilities to merge

| Merge | Into | Rationale |
|-------|------|-----------|
| Cart Workspace + MEIF Decision / Finding Decision Engine | **One Decision Workspace** | Two stacks answer overlapping “what should I decide?” |
| `#communication` MEIF package + `#messages` history | **One Communication page** | Nav promises `#communication`; history lives elsewhere |
| Legacy Home painters (ECC / Pulse / PeV2 / ORV sibling) | **Delete or lab-only** once HES is permanent | Cascade already hard-gated; scripts still ship |
| MEIF Home sections (executive_summary / critical_attention / …) | **HES teasers only** while HES is the Home owner | Avoid dual Home compositions |

**Do not merge:** Carts into Decision, or Communication into Settings (MEIF already fixed Settings≠Communication).

---

## 6. Data ownership map

| Data class | Canonical owner | Home may | Other surfaces |
|------------|-----------------|----------|----------------|
| Executive teaser summaries (health / decision count / obs count / cart count / comms count) | **Home composer** (`home_executive_summary_v1`) | Own | — |
| Business Findings (BFL) | **BFL store** | Count / top title only | Decision paints full contract |
| Finding → Decision projection | **Finding Decision Engine** | Teaser only | Decision owns render |
| Observation findings (entity-bound) | **Observation Foundation / ORV** | Slim teaser + honest empty | Product Intelligence (future) owns analysis |
| Cart rows / timeline / stage | **Cart / recovery truth + normal-carts API** | Count only | Carts owns list/detail |
| Communication events | **WhatsApp / recovery communication truth** | Count only | Communication owns timeline |
| Merchant Intelligence / value stories | **MI service** | None | Must not live on Carts as recommendations under this constitution (Decision or retire) |
| Store connection / widget / WA config | **Settings APIs** | None as primary | Settings |
| Setup / activation | **Merchant setup experience** | Suppress on executive Home | Settings / Store Setup |

---

## 7. Query ownership map

| Query / attach (today) | Runs on | Should run on | Notes |
|------------------------|---------|---------------|-------|
| `home_stage_meif_attach` (full MEIF gen) | Every summary | Decision/Carts/Comms **page APIs**, or slim “Home teaser inputs” query | Highest Home cost |
| `home_stage_orv_attach` (full ORV) | Every summary | Home: slim count/empty only; detail deferred | Slim after full assemble today |
| `home_stage_hes_attach` | Every summary | Home summary (keep) | Cheap |
| `home_stage_adaptive_cognition` | Every summary | Off Home critical path unless Home-owned | |
| `home_stage_commerce_pulse` | Every summary | Only if Pulse UI on | Usually wasted |
| `build_merchant_home_experience_api_payload` | Live summary | Off when HES on | Legacy |
| `_merchant_kpi_today_projection` / month | Live summary | Month page / Settings, not Home overview | |
| `_merchant_reason_counts_store_window_*` | Live summary | Reasons surface / diagnostics | |
| `_normal_carts_dashboard_stats` | Live summary | Carts API | |
| `build_merchant_whatsapp_readiness_card` | Live summary | Communication or Settings | |
| Double MEIF (live + finalize) | Live summary | **Once**, or skip finalize if present | Determinism + cost |
| `/api/dashboard/normal-carts` | Eager boot | Carts navigation / lazy | |
| `/api/dashboard/messages` | Eager boot | Communication navigation / lazy | |
| `/api/cart-workspace/v1/projection` | Workspace | Decision Workspace only | Keep |

---

## 8. Surface ownership map

```
Home (#home) — executive teasers only; slim summary package
        | View Details
        +---> Decision Workspace (#workspace) — decisions only
        +---> Carts (#carts) — operational cart management only
        +---> Communication (#communication) — communication status only
        +---> Settings (#settings) — configuration only

Product Intelligence V1 (future): product findings — not Home, not Carts
```

| Surface | Single owner (recommended) | Forbidden second owner |
|---------|---------------------------|------------------------|
| Home | `home_executive_summary_v1` | MEIF Home painter, ECC, Pulse, ORV sibling, PeV2 |
| Decision | **Unify** Cart Workspace + MEIF Decision under one product owner | Home decision cards, Carts MI decisions |
| Carts | Normal-carts ops renderer | Decision engine, Product Intelligence |
| Communication | One primary hash + one painter | Settings WhatsApp as communication home |
| Settings | Settings / WA / Widget / Plans modules | Intelligence or ops queues |

---

## 9. Performance impact of proposed alignment

### 9.1 Root causes of Home latency (ordered)

1. **Unnecessary queries on summary** — KPI/month/reason/normal-carts-stats/WA readiness while overview only paints HES  
2. **Duplicated calculations** — MEIF attach on live builder **and** finalize  
3. **Loading page-owned data** — full MEIF Decision/Carts/Comms/Settings packages; eager normal-carts + messages on boot  
4. **Rendering unnecessary sections** — mitigated in UI by HES gate; transport still serializes them  
5. **Expensive joins / aggregation** — ORV durable assemble + per-finding product resolve; BFL bind + decision engine inside MEIF  
6. **Avoidable aggregation** — Pulse/commerce when UI off; adaptive cognition on Home path  

### 9.2 Expected impact of alignment (architectural, not micro-opt)

| Change | Expected effect on Home |
|--------|-------------------------|
| Slim Home summary contract (teaser inputs only; no full MEIF pages) | Large latency + payload reduction |
| Single MEIF attach / skip when HES-only | Removes duplicate wall-clock |
| Defer ORV detail; Home empty/count path | Cuts observation query fan-out on empty stores |
| Lazy normal-carts + messages | Faster first paint on `#home` |
| Drop legacy home + Pulse from HES path | Removes dead work |
| Unify Decision to one API | No direct Home win; clears ownership for PI |

Temporary micro-optimizations without ownership change will **re-bloat** as Product Intelligence lands.

---

## 10. Required architectural changes before Product Intelligence V1

**Gate: do not start Product Intelligence V1 until these are accepted.**

### P0 — blocking

1. **Home slim transport contract**  
   Define `home_executive_summary_v1` inputs that do **not** require full MEIF page packages or full ORV diagnostics on `/api/dashboard/summary`.

2. **Single Decision Workspace owner**  
   Choose Cart Workspace **or** MEIF/BFL Decision as the sole Decision product; migrate the other to consume it or retire.

3. **Carts ops-only boundary**  
   Move/remove MI recommendation primary UI from Carts before PI adds a third recommendation surface.

4. **Communication single surface**  
   Make `#communication` the real status page; stop leaving MEIF Comms unpainted while `#messages` is the de-facto home of communication.

5. **No duplicate Home painters in production boot**  
   Keep HES hard-gate; plan removal of dead script loads (ECC/Pulse/ORV sibling/PeV2) from production dashboard.

### P1 — before PI scale

6. **Lazy page APIs** — normal-carts / messages / decision projection only when their hash is active (or explicit prefetch).  
7. **Observation detail endpoint** — Home never expands full product analysis; PI owns that page.  
8. **Query ownership tests** — assert summary path does not call Carts/Comms list builders.  
9. **MEIF role clarification** — MEIF becomes page-package factory for Decision/Carts/Comms/Settings, **not** Home composition when HES is on.

### Explicit non-goals (this audit)

- Do not implement Product Intelligence V1  
- Do not redesign UI  
- Do not add merchant features  

---

## 11. Gap scorecard vs constitution

| Surface | Single responsibility? | Owns one question? | Duplication? | Home overreach? |
|---------|------------------------|--------------------|--------------|-----------------|
| Home (paint) | Yes | Yes | Legacy paths dormant | Transport overreach |
| Home (transport) | No | — | MEIF/ORV/legacy/Pulse | Yes |
| Decision | No (dual stack) | Partial | vs Home teasers / Carts MI | — |
| Carts | No | Partial (“needs attention” invites recommendations) | vs Decision | — |
| Communication | No (split) | Partial | vs `#messages` / Settings siblings | — |
| Settings | Mostly | Yes | Low | — |

---

## 12. STOP

**Architectural alignment is incomplete.**  
Home Stabilization fixed the **painted** Home; it did not fix **summary ownership** or **cross-surface recommendation sprawl**.

**Do not begin Product Intelligence V1** until Product / CEO accept this audit and authorize P0 changes (or an explicit waiver with recorded risk).

---

## Appendix A — Primary evidence files

| Area | Path |
|------|------|
| Home finalize | `services/merchant_home_experience_activation_v1.py` |
| HES compose | `services/home_executive_summary_v1/compose_v1.py` |
| HES paint | `static/home_executive_summary_v1.js` |
| Summary cascade | `static/merchant_dashboard_lazy.js` |
| MEIF packages | `services/product_data/merchant_experience_integration_foundation_v1.py` |
| MEIF questions | `services/product_data/merchant_experience_integration_types_v1.py` |
| MEIF paint | `static/merchant_experience_integration_v1.js` |
| Decision engine | `services/finding_decision_engine_v1.py` |
| BFL bind | `services/merchant_experience_business_findings_binding_v1.py` |
| Cart Workspace | `static/cart_workspace_merchant_v1.js` |
| Live summary builder | `main.py` (`/api/dashboard/summary`) |
| Stabilization sprint | `docs/product/HOME_STABILIZATION_SPRINT_V1.md` |
| Home constitution | `HOME_EXECUTIVE_CONSTITUTION_V1.md` |
