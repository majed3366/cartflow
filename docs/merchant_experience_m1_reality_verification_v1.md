# Merchant Experience M1 — Reality Verification V1

**Status:** Root-cause verification complete — no fixes applied  
**Date (UTC):** 2026-07-06  
**Scope:** Confirm whether M1 is visible to merchants; classify three observed issues  
**Authority:** Pre–Product Excellence gate after [`merchant_experience_era_milestone_m1.md`](merchant_experience_era_milestone_m1.md)  
**Method:** Code-path trace, API probes (local TestClient), snapshot-path simulation, boot/render chain analysis  

**Explicitly out of scope:** Redesign, copy changes, CSS, component moves, Product Excellence implementation.

---

## Executive summary

| Issue | Merchant-visible symptom | Primary root cause | Classification |
|-------|-------------------------|-------------------|----------------|
| **1 — Home appears empty** | Greeting + loading shell; no five-section story | Production summary often served from **snapshot read path** that returns payloads **without** `merchant_home_experience_v1`; broken Daily Brief fallback (DOM removed) | **Missing wiring** (+ secondary **Bug** on fallback) |
| **2 — Carts unchanged** | Carts tab still looks like classic ops dashboard | M1 migrated **knowledge ownership** for cart detail only; **list layout intentionally unchanged** | **Intentional current design** |
| **3 — Loading delay** | Noticeable wait before Home content appears | Home paint is **gated on** `GET /api/dashboard/summary`; live path ~300–380 ms warm (composition ~150 ms inside); cold DB warm ~1.1–1.5 s dominates first request | **Intentional current design** (lazy boot) + measurable API latency |

M1 **is implemented** on the live builder path. The gap between “code exists” and “merchant sees it” is primarily a **production read-model / snapshot freshness** problem, not missing composition logic or a Home renderer bug.

---

## Verification method

### Code paths traced

| Layer | Artifact | Role |
|-------|----------|------|
| API (live) | `main.py` → `_api_json_dashboard_summary()` | Calls `build_merchant_home_experience_api_payload()`; attaches `merchant_home_experience_v1` when store slug resolves |
| API (production) | `main.py` → `api_dashboard_summary()` | When `CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1`, returns **snapshot only** via `serve_enforced_snapshot_response()` — **never** runs live home builder |
| Snapshot builder | `dashboard_snapshot_builder_v1.py` → `_build_summary_payload()` | Calls live `_api_json_dashboard_summary()` — **will** include home field **after** post-M1 rebuild |
| Snapshot read | `dashboard_snapshot_read_v1.py` → `build_summary_from_snapshot()` | Returns stored JSON as-is; pre-M1 or degraded snapshots omit home field |
| JS consumer | `merchant_dashboard_lazy.js` → `applySummary()` | Calls `maApplyHomeExperience(d.merchant_home_experience_v1)` only when field present |
| Renderer | `merchant_home_experience.js` → `applyHomeExperience()` | Replaces `#ma-home-experience-root` innerHTML with all five sections when `payload.ok` |
| Template shell | `templates/merchant_app.html` | Static greeting + «CartFlow يجهّز ملخص يومك…» until JS applies payload |

### Local API probes (development, warm DB)

| Probe | Result |
|-------|--------|
| `GET /api/dashboard/summary` (live path) | `merchant_home_experience_v1` **present**, `ok: true`, 12 while-away items, 5 quick-nav items |
| Warm summary latency | ~312–379 ms (3 samples) |
| Isolated composition | ~150 ms |
| Snapshot mode simulation (`CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1`, no DB snapshot) | Response in ~16 ms; **`merchant_home_experience_v1` absent** (degraded snapshot payload) |
| `GET /api/dashboard/normal-carts` (warm) | ~156–182 ms |
| `GET /api/dashboard/vip-carts` (warm) | ~71–80 ms |

---

## Issue 1 — Merchant Home appears almost empty

### Expected behavior

Merchant Home Experience V1 renders five sections from `merchant_home_experience_v1`:

1. Greeting  
2. While you were away (`بينما كنت بعيداً`)  
3. Today needs your attention (`يحتاج انتباهك اليوم`)  
4. Store understanding (`فهم المتجر`)  
5. Quick navigation (`انتقال سريع`)  

Source: [`merchant_home_experience_v1.md`](merchant_home_experience_v1.md).

### Actual behavior

Merchants report:

- Greeting only (from static HTML shell)  
- Large empty space below  
- Loading line «CartFlow يجهّز ملخص يومk…» may persist or feel like empty space (muted 13px copy)

This matches the **pre-apply shell** in `#ma-home-experience-root`, not a partially rendered composition.

### Root-cause analysis

#### Ruled out: Missing composition

- `services/merchant_home_composition_v1.py` implements full five-section contract.  
- Live summary path attaches `merchant_home_experience_v1` (verified locally).  
- **Not** “not implemented.”

#### Ruled out: Rendering bug / hidden sections

`applyHomeExperience()` always renders **all section titles** when `payload.ok === true`, even with zero items (empty-state copy + quick nav with 5 items).  

Observed “greeting only **without** section headers” implies **`applyHomeExperience()` did not run with a valid payload** — not a CSS hide or conditional section skip.

#### Ruled out (as sole cause): Missing data

Sparse data (setup merchants, empty brief) still produces section structure. Review Board notes setup-phase Home feels empty **emotionally**, but composition would still paint section headers. Pure missing data does **not** explain greeting-only shell.

#### Confirmed: Missing wiring — snapshot → client payload gap

Production dashboard uses enforced snapshot mode for hot paths:

```17868:17882:main.py
        if dashboard_snapshot_mode_enabled():
            payload = serve_enforced_snapshot_response(
                path="/api/dashboard/summary",
                build_from_snapshot=build_summary_from_snapshot,
                degraded_builder=_degraded_summary_payload,
                store_slug=resolve_merchant_store_slug_for_snapshot(),
            )
            ...
            return j(payload)
```

Implications:

1. **Pre-M1 summary snapshots** stored in DB do not contain `merchant_home_experience_v1` until the snapshot builder rebuilds them post-deploy.  
2. **`_degraded_summary_payload`** (miss / read error) also omits the field — confirmed in local snapshot simulation.  
3. Snapshot builder **does** call live `_api_json_dashboard_summary()` (which includes home) — wiring is correct **after rebuild**, not at first merchant request post-M1.

#### Confirmed: Missing wiring — broken fallback when field absent

When `merchant_home_experience_v1` is missing, `applySummary()` falls back to Daily Brief:

```2095:2102:static/merchant_dashboard_lazy.js
    if (window.maApplyHomeExperience && d.merchant_home_experience_v1) {
      window.maApplyHomeExperience(d.merchant_home_experience_v1);
    } else if (window.maApplyDailyBriefPayload) {
      if (d.merchant_daily_brief_v1 && d.merchant_daily_brief_v1.ok) {
        window.maApplyDailyBriefPayload(d.merchant_daily_brief_v1);
```

But M1 **removed** `#ma-daily-brief-root` from `templates/merchant_app.html`. `merchant_daily_brief.js` no-ops when root is absent:

```293:293:static/merchant_daily_brief.js
    if (!byId("ma-daily-brief-root")) return;
```

Result: **silent no-op** — shell never replaced.

#### Secondary: Exception path omits field

Live builder wraps home composition in `try/except`; failures log and omit `merchant_home_experience_v1` without failing summary (`main.py` ~19592–19616). Same broken fallback applies.

#### Secondary: Fetch failure leaves shell

`fetchSection()` catches errors and leaves shell unchanged (`merchant_dashboard_lazy.js` ~4539–4541).

### Classification

| Factor | Classification |
|--------|----------------|
| Snapshot serving stale/degraded summary without home field | **Missing wiring** |
| Fallback to removed Daily Brief DOM | **Bug** |
| Home composition / renderer when payload present | Works as designed |
| Setup merchant sparse story | **Intentional current design** (content density), but would still show section chrome if wired |

### Decision tree (Issue 1)

```
Merchant opens Home
  → Static shell: greeting + pending text
  → bootLazyDashboard → fetchSection("/api/dashboard/summary")
       → Production: snapshot read (fast)
            → Snapshot pre-M1 OR degraded? → NO merchant_home_experience_v1
       → applySummary: field missing
            → maApplyDailyBriefPayload → #ma-daily-brief-root gone → NO-OP
  → Merchant sees greeting-only empty Home
```

---

## Issue 2 — Carts workspace feels visually unchanged

### Expected behavior (merchant intuition)

After “Merchant Experience Era M1,” merchants may expect the **Carts tab** to feel like the new calm Home — less ops-dashboard density.

### Actual behavior

Carts workspace remains:

- Filter bar, status tabs (all / intervention / waiting / completed / VIP)  
- Table columns, badges, expandable rows  
- Classic operational dashboard density  

Review Board: **“Home whispers; Carts shouts.”**

### Root-cause analysis

#### What M1 intentionally changed (Carts)

| Change | Layer | Merchant-visible? |
|--------|-------|-------------------|
| `cart_detail_projection_v1` on normal-carts rows | API + routing | **Expand row only** — explanation / suggested action sourced from projection |
| Retired `merchantDecisionExecutable`, local decision labels | JS | **Copy/eligibility in detail panel**, not list chrome |
| `route_cart_detail_knowledge_v1` certification | Backend | **No list layout change** |

Certification doc explicitly states:

> **Layout / expand / HTML structure** — `merchant_dashboard_lazy.js` — **Surface-owned**

Source: [`cart_detail_migration_v1.md`](cart_detail_migration_v1.md) ownership audit.

#### What M1 intentionally did NOT change (Carts)

- List/table layout, filters, tabs, column structure  
- Carts page HTML in `templates/merchant_app.html`  
- Visual density or “whisper” tone on list surface  

#### What remains for Product Excellence

[`merchant_experience_cohesion_program_v1.md`](merchant_experience_cohesion_program_v1.md) Phase 1: **Carts workspace whisper** — explicit future cohesion work, not M1 migration scope.

[`merchant_experience_review_board_v1.md`](merchant_experience_review_board_v1.md): Carts tab **Fail** on cohesion; **Pass** on architectural migration.

### Classification

**Intentional current design** — M1 completed **ownership migration**, not Carts list visual migration. Visual parity with Home is **Cohesion Program** scope, not M1.

### M1 visual change map

| Surface | M1 visual change |
|---------|------------------|
| **Home overview** (`#page-home`) | **Yes** — KPI wall, standalone KL, reasons, VIP removed; `#ma-home-experience-root` added *(when payload wired)* |
| **Home month sub-page** (`#page-home-month`) | KPIs relocated here — unchanged chrome |
| **Carts list** (`#page-carts`) | **No** intentional layout change |
| **Cart expand detail** | **Partial** — content authority moved to projection; layout same |
| **KL / Brief standalone on home** | **Removed** from overview (merged into composition) |

---

## Issue 3 — Noticeable page loading delay

### Expected behavior

Home should feel like a morning operating center quickly available on open.

### Actual behavior

Merchants notice delay before Home content replaces the loading shell.

### Root-cause analysis — measured breakdown

| Phase | Local measurement | Notes |
|-------|-------------------|-------|
| **Cold DB warm** (first dashboard request) | ~1.1–1.5 s | `widget_schema` cache miss dominates — production may differ |
| **Warm summary API (live path)** | ~312–379 ms | Includes full summary + home composition |
| **Home composition only** | ~150 ms | Brief + KL fetch inside composition |
| **Warm normal-carts API** | ~156–182 ms | Booted in parallel with summary |
| **Warm vip-carts API** | ~71–80 ms | Booted in parallel |
| **Snapshot summary read** (when snapshot exists) | ~16 ms (degraded miss) | Fast but may lack home field |
| **Frontend render** | Sub-ms (sync `innerHTML`) | Not a meaningful delay source |

#### Boot sequence (frontend)

```4618:4631:static/merchant_dashboard_lazy.js
  function bootLazyDashboard() {
    ...
    fetchSection("/api/dashboard/summary", applySummary, "summary");
    ...
    fetchVipCarts(...);
    fetchNormalCarts("boot_priority")...
```

- Home sections paint **only after** summary fetch completes and `applyHomeExperience` runs.  
- Normal-carts / VIP do not block Home paint but compete for network/CPU on boot.  
- Initial HTML shows loading shell immediately — **perceived delay = time until summary returns**.

#### Production path nuance

- Snapshot mode: summary is **fast** (~tens of ms) but may **not** paint Home sections (Issue 1).  
- Merchant may experience **fast empty Home** rather than **slow full Home** in production today.

### Classification

| Factor | Classification |
|--------|----------------|
| Lazy boot gating Home on summary fetch | **Intentional current design** |
| ~300 ms+ warm live summary (composition nested) | Real latency — architecture tradeoff, not network assumption |
| Cold-start DB warm on first hit | Environmental — can dominate first load |
| No progressive Home section streaming | **Intentional current design** (single payload apply) |

### Where delay originates (ranked)

1. **API / server:** Summary endpoint (live path) — largest controllable block before Home paint  
2. **Composition generation:** ~40% of warm summary (~150 ms of ~370 ms) — Brief re-fetch + KL report inside home builder  
3. **Frontend rendering:** Negligible  
4. **Lazy loading timing:** Home intentionally waits for summary — not a render bug  

---

## Cross-issue synthesis

| Question | Answer |
|----------|--------|
| Why does Home appear empty? | **`merchant_home_experience_v1` not reaching JS** on production snapshot path (stale/degraded snapshot) + **broken Daily Brief fallback** after DOM removal |
| Why does Carts appear unchanged? | **M1 only migrated cart-detail knowledge ownership**; list visual redesign is **explicitly deferred** to Cohesion Program |
| Is loading delay real? | **Yes** on live path (~300 ms+ warm); Home paint is **blocked on summary**. Production snapshot path may be fast but **empty** (Issue 1) |

---

## Recommended verification before Product Excellence (ops, not code)

1. **Production API inspect:** `GET /api/dashboard/summary` — confirm presence of `merchant_home_experience_v1` for an activated store.  
2. **Snapshot age:** Compare snapshot `generated_at` / builder tick vs M1 deploy time (`c7bb1c8`).  
3. **Force snapshot rebuild** for pilot stores if field absent.  
4. **Browser network tab:** Time from navigation → summary response → DOM update in `#ma-home-experience-root`.  

---

## Files referenced

| File | Relevance |
|------|-----------|
| `main.py` | Summary live vs snapshot routing; home payload attach |
| `services/merchant_home_composition_v1.py` | Composition builder |
| `services/dashboard_snapshot_read_v1.py` | Snapshot read + degraded summary |
| `services/dashboard_snapshot_builder_v1.py` | Post-M1 snapshot rebuild path |
| `static/merchant_home_experience.js` | Home renderer |
| `static/merchant_dashboard_lazy.js` | Boot, applySummary, fallback |
| `templates/merchant_app.html` | Home shell; removed brief root |
| `docs/merchant_home_experience_v1.md` | M1 Home spec |
| `docs/cart_detail_migration_v1.md` | Carts ownership vs layout |
| `docs/merchant_experience_cohesion_program_v1.md` | Future Carts visual work |

---

*End of Merchant Experience M1 Reality Verification V1 — no fixes applied.*
