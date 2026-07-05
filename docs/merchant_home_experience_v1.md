# CartFlow Merchant Home Experience V1

**Status:** Implemented — Graduation Sprint of Merchant Experience Migration Program  
**Date (UTC):** 2026-07-05  
**Scope:** Phase 3 — Merchant Home as operational composition center (not dashboard)  
**Authority:** [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) Phase 3  
**Audience:** Engineering, architecture review  

---

## Executive summary

Merchant Home is the merchant's **daily operating center**. It composes governed platform knowledge into one coherent morning story — never minting business logic, routing, or explanations.

```
Merchant Knowledge Infrastructure
        ↓
Knowledge Routing (Daily Brief + Home KL slice)
        ↓
Daily Brief · Knowledge Layer · KPI read-model (nav only)
        ↓
Merchant Home Composition (`merchant_home_composition_v1`)
        ↓
Merchant Home UI (`merchant_home_experience.js` — presentation only)
```

Merchant Home is the **fourth certified routing consumer surface** (composition layer certifying consumption of Brief + Home-routed KL).

---

## Home experience model (five sections)

| Section | Source | Home role |
|---------|--------|-----------|
| **1. Greeting** | Composition metadata | Merchant name + date + time greeting |
| **2. While you were away** | Daily Brief achievements (Composer V2) | Platform-completed work |
| **3. Today needs your attention** | Daily Brief attention (max 3 display) | Action-first, deduped |
| **4. Store understanding** | Home-routed KL projection | Governed understanding — not KPI wall |
| **5. Quick navigation** | Composition + read-model badges | Carts, completed, settings |

Removed from home overview (moved to **الملخص العام** sub-page): KPI grid, reasons week chart, VIP list, standalone Daily Brief block, standalone KL fetch.

---

## Removed surface ownership

| Removed from home overview | Former responsibility | New owner |
|---------------------------|----------------------|-----------|
| `#ma-daily-brief-root` + `merchant_daily_brief.js` on home | Separate brief rendering | Home composition Section 2–3 |
| `#ma-knowledge-root` + independent KL fetch | Separate KL selection | Home composition Section 4 via routing |
| Reasons week card | Dashboard widget | `#page-home-month` / reasons page |
| VIP home list | Dashboard widget | Carts VIP tab |
| KPI grid on overview | Metric wall | `#page-home-month` only |

### JS decisions audit

| Decision | Classification |
|----------|----------------|
| Read `merchant_home_experience_v1` from summary | **KEEP** — composition consumer |
| Render five sections from payload | **KEEP** — presentation |
| `esc()` HTML escaping | **KEEP** — presentation safety |
| Quick nav onclick handlers | **KEEP** — navigation interaction |
| Local insight selection | **REMOVE** — never on home JS |
| Independent `/api/knowledge/report` fetch on home | **REMOVE** — composition owns KL slice |

---

## Implementation

### Routing (`services/knowledge_routing_v1.py`)

- Added `route_merchant_home_knowledge_v1()` — KL insights for `surface=merchant_home`
- Uses existing `route_knowledge_for_surface_v1` (no algorithm changes)

### Composition (`services/merchant_home_composition_v1.py`)

- `compose_merchant_home_experience_v1()` — five-section display contract
- `build_merchant_home_experience_api_payload()` — Brief + KL + nav metadata
- Dedupes items across sections by aggregation_key / knowledge_id
- Attention display capped at 3 (platform max remains 5 via Brief)
- `experience_tier` + `tier_capabilities` — Starter active; Growth/Pro architecture placeholder only

### API (`main.py`)

`GET /api/dashboard/summary` adds:

- `merchant_home_experience_v1` — composed home payload
- `merchant_daily_brief_v1` — embedded from composition (backward compat)

### UI

- `templates/merchant_app.html` — `#ma-home-experience-root` replaces brief/KL/reasons/VIP on overview
- `static/merchant_home_experience.js` — presentation-only renderer
- `static/merchant_app.css` — calm home experience styles (no KPI wall)

---

## Home principles compliance

| Rule | Status |
|------|--------|
| HM-1 — understand today, not inspect data | **Pass** |
| HM-2 — achievements before problems | **Pass** |
| HM-3 — understanding before metrics | **Pass** |
| HM-4 — actions before reports | **Pass** |
| HM-5 — knowledge before charts | **Pass** |
| HM-6 — calm before complexity | **Pass** |
| HM-7 — one merchant story | **Pass** |

---

## Progressive experience tiers

Architecture supports Starter / Growth / Pro via `experience_tier` and `tier_capabilities`. **Only Starter is active** — no plan-based UI differences implemented.

---

## Regression safety

| Layer | Changed? |
|-------|----------|
| Purchase / Lifecycle Truth | **No** |
| Recovery execution | **No** |
| Merchant Explanation | **No** |
| Decision Layer | **No** |
| Daily Brief Composer / routing | **No** — consumed as-is |
| Knowledge Layer producer | **No** |
| KPI calculation | **No** — KPIs remain on month sub-page |
| `/api/knowledge/report` | **No** — still available for future dedicated KL view |

---

## Tests

| File | Coverage |
|------|----------|
| `tests/test_merchant_home_experience_v1.py` | Composition sections, dedupe, attention cap, routing, JS grep gate |
| `tests/test_knowledge_routing_v1.py` | `route_merchant_home_knowledge_v1` (when added) |
| `tests/test_merchant_standalone_app_dashboard.py` | Home experience script + root in dashboard |
| `tests/test_merchant_knowledge_dashboard_v1.py` | Home composition replaces standalone KL section |

---

## Merchant Home Experience Review V1

### Experience consistency

Home sections consume the same governed language as Daily Brief, Knowledge Layer, and Cart Detail. Achievements and attention originate from Composer V2 routed feed. Store understanding uses KL projection path with Home surface routing.

### Merchant attention flow

Achievements → attention (max 3) → understanding → navigation. Calm empty states when sections have no items. No KPI wall on overview.

### Composition ownership

| Responsibility | Owner |
|----------------|-------|
| Achievements / attention copy | Daily Brief Composer V2 + routing |
| Store understanding copy | KL projection + Home routing |
| Section ordering / layout | Home composition + JS |
| Nav badge counts | Read-model summary fields |
| Greeting / date | Composition metadata |

Composition creates no knowledge, decisions, explanations, or routing.

### Routing consumption

`knowledge_routing_v1` embedded with `surface=merchant_home` for store understanding slice.

### Visual simplicity

Single column, max-width 720px, whitespace-friendly. No card overload on overview. KPIs relegated to month sub-page.

### Architecture verdict

## **PASS**

Merchant Home is certified as a **governed composition consumer** — Graduation Sprint complete.

**Merchant Experience Migration Program V1 — all three phases certified:**

| Surface | Status |
|---------|--------|
| Daily Brief | ✅ Reference consumer |
| Knowledge Layer | ✅ Phase 1 |
| Cart Detail | ✅ Phase 2 |
| **Merchant Home** | **✅ Phase 3** |

Ready for **Merchant Experience Review V1**.

---

## Related documents

| Document | Role |
|----------|------|
| [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) | Program Phase 3 definition |
| [`knowledge_layer_migration_v1.md`](knowledge_layer_migration_v1.md) | KL consumer pattern |
| [`cart_detail_migration_v1.md`](cart_detail_migration_v1.md) | Cart Detail consumer pattern |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Brief achievements/attention source |
