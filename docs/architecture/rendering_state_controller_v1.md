# Rendering State Controller V1 — Design

**Status:** Implemented (Cart Page V2 Phase 2.6) — runtime owner of merchant-visible Cart composition  
**Date (UTC):** 2026-07-09  
**Surface:** Cart Page V2 (`#page-carts` / `/dashboard#carts`)  
**Evidence:** [`docs/product/cart_page_rendering_lifecycle_audit.md`](../product/cart_page_rendering_lifecycle_audit.md)  
**Module:** `static/cart_page_rendering_state_controller_v1.js` (wired from `merchant_dashboard_lazy.js`; loaded before lazy in `merchant_app.html`)  
**Related:** Lifecycle Governance Engine V1 (`docs/lifecycle_governance_engine_v1.md`) — LGE governs interactive component lifecycles; **this controller governs merchant-visible page composition** for Carts. They are complementary, not duplicates.

> **Law:** There is exactly **ONE owner** of merchant-visible rendering on the Cart page. Attention Verdict, MI Workspace, Pending UI, Empty UI, and Story Cards **consume** the controller. They must **never** independently decide what the merchant sees.

---

## 0. Mission

Cart Page V2 currently allows **distributed rendering ownership**:

- Attention Verdict decides from `cartsAttentionVerdictPending` + row counts
- MI Workspace decides from `hasRenderablePayload(d)`
- Pending UI replaces story cards when MI is missing
- Empty UI / queue whisper can appear independently
- Cache / memory keep paths paint rows without MI and overwrite last-good intelligence

That produces merchant-visible drift (e.g. desktop pending while another client reaches final cards) without a viewport-specific code path.

**Rendering State Controller (RSC) V1** establishes a single authority that:

1. Holds the only merchant-visible rendering plan for Carts
2. Accepts inputs from fetch/cache/guards (data plane)
3. Emits one coordinated plan to pure presenters (view plane)
4. Preserves last-good visible content under refresh/failure policies

RSC does **not** own operational truth (lifecycle, archive, recovery, snapshot builders). It owns **how truth is shown** while data is loading, refreshing, degraded, or final.

---

## 1. Rendering owner

### Sole owner

| Role | Name | Responsibility |
|------|------|----------------|
| **Rendering Owner** | `CartPageRenderingStateController` (RSC) | Sole authority for merchant-visible Cart page composition |

### Authority split (non-negotiable)

| Plane | May decide merchant-visible UI? | Examples |
|-------|--------------------------------|----------|
| **RSC** | **Yes — only** | Verdict mode, body mode, empty/pending/stories, freshness badge |
| **Data ingress** | No — may only **propose** events to RSC | `applyNormalCarts`, cache hydrate, thin/partial guards |
| **Presenters** | No — **paint only** from RSC plan | Verdict HTML, MI groups, pending whisper, empty whisper |
| **CSS / viewport** | No — layout only | Desktop panel vs mobile CTA visibility |
| **Filter bar** | No for verdict/body composition | May filter *which* story rows are visible **after** RSC says body = stories; must not invent pending/final |

### Consumers (must not decide)

These modules become **pure presenters** of an RSC plan:

| Consumer | Host | Forbidden today → required tomorrow |
|----------|------|-------------------------------------|
| Attention Verdict | `#ma-carts-attention-verdict-v1` | Must not call `buildCartsAttentionVerdictV1` from local pending flags alone |
| MI Workspace | `#ma-carts-groups-v2` | Must not branch on `hasRenderablePayload(d)` to choose pending vs stories |
| Pending UI | same groups host | Must render only when plan.bodyMode = `pending` |
| Empty UI | `#ma-carts-queue-empty` | Must render only when plan.bodyMode = `empty` |
| Story Cards | groups host (stories/groups) | Must render only when plan.bodyMode = `stories` |

Conversation panel (`#ma-carts-panel-v2` / mobile CTA) remains a **detail selection** consumer: it shows the selected cart story, but **queue composition** (verdict + body) is still RSC-owned.

---

## 2. Rendering states

RSC holds one **Rendering Snapshot** (immutable plan per tick). Conceptual fields:

```text
RenderingSnapshot {
  phase:            boot | cached | refreshing | final | failed
  freshness:        pending | final
  bodyMode:         loading | pending | stories | empty
  verdictMode:      refreshing | needs_you | automatic | calm | empty | loading
  rowsSource:       none | cache | memory | live | degraded
  miSource:         none | last_good | live
  rows:             CartRow[]          // active (non-archived) for display counts
  miPayload:        object | null      // intelligence / value stories for body
  lastGood:         { rows, miPayload, verdictMode, bodyMode } | null
  reason:           string             // e.g. boot_priority, partial_keep, thin_keep
  fetchGen:         number
  appliedGen:       number
}
```

### Merchant-visible phases (coarse)

| Phase | Merchant meaning | Typical freshness | Typical bodyMode |
|-------|------------------|-------------------|------------------|
| `boot` | Page opening, no usable paint yet | pending | loading |
| `cached` | Temporary paint from sessionStorage | pending | pending **or** stories-from-last_good* |
| `refreshing` | Live fetch in flight or keep/retry | pending | last_good body preferred |
| `final` | Successful live/snapshot apply accepted | final | stories or empty |
| `failed` | Fetch error after retries policy | pending | last_good body preferred |

\*Under **Last-good state policy** (§7), cached/refreshing should prefer showing last-good stories with a pending verdict, not wipe the body into MI-pending whisper.

### Verdict modes (presentation labels)

| verdictMode | When RSC may emit |
|-------------|-------------------|
| `refreshing` | freshness = pending (calm «جارٍ تحديث الصورة...») |
| `needs_you` / `automatic` / `calm` / `empty` | freshness = final, derived from rows’ primary actions |
| `loading` | boot with no rows and no last-good |

### Body modes

| bodyMode | Visible content |
|----------|-----------------|
| `loading` | Minimal loading whisper (no fake counts) |
| `pending` | Explicit body pending only when **no** last-good stories exist |
| `stories` | Story cards / MI groups |
| `empty` | Confirmed empty whisper |

---

## 3. Allowed transitions

```text
                    ┌──────────┐
                    │   boot   │
                    └────┬─────┘
           cache hit     │     no cache
                ┌────────┴────────┐
                ▼                 ▼
           ┌─────────┐       ┌────────────┐
           │ cached  │       │ refreshing │◄── fetch started
           └────┬────┘       └─────┬──────┘
                │                  │
                └────────┬─────────┘
                         │ apply success
                         ▼
                    ┌─────────┐
         ┌─────────│  final  │◄──────────── retry success
         │         └────┬────┘
         │              │ fetch / visibility refresh
         │              ▼
         │         ┌────────────┐
         │         │ refreshing │── keep/degraded ──┐
         │         └─────┬──────┘                   │
         │               │ apply success            │
         │               └──────────► final         │
         │                                          │
         │         fetch exhausted / hard error     │
         └────────►┌─────────┐◄─────────────────────┘
                   │ failed  │── retry success ──► refreshing → final
                   └─────────┘
```

### Transition table (normative)

| From | Event | To | Notes |
|------|-------|----|-------|
| `boot` | `CACHE_HYDRATED` | `cached` | freshness=pending; body uses last_good if any |
| `boot` | `FETCH_STARTED` | `refreshing` | No cache |
| `cached` | `FETCH_STARTED` | `refreshing` | Keep body per last-good policy |
| `refreshing` | `APPLY_SUCCESS` | `final` | Only path that sets freshness=final |
| `refreshing` | `APPLY_KEEP` (partial/thin/unconfirmed) | `refreshing` | **Must not** clear last_good MI; schedule retry |
| `refreshing` | `APPLY_CONFIRMED_EMPTY` | `final` | bodyMode=empty |
| `final` | `FETCH_STARTED` | `refreshing` | Soft refresh; keep last_good visible |
| `final` / `refreshing` | `FETCH_FAILED` | `failed` | Keep last_good; calm pending verdict |
| `failed` | `FETCH_STARTED` | `refreshing` | Retry |
| `failed` | `APPLY_SUCCESS` | `final` | Recovered |

### Forbidden transitions

| Forbidden | Why |
|-----------|-----|
| Any → `final` without `APPLY_SUCCESS` / confirmed empty | Prevents stale-final counts |
| `final` → body `pending` solely because memory payload lacks MI | Root cause of lifecycle audit |
| Presenter-local jump to `stories` while RSC phase ≠ `final` and miSource ≠ `last_good`/`live` | Independent MI decisions banned |
| Verdict `needs_you`/`automatic` while freshness=pending | Stale counts as final — banned by freshness hotfix intent |

---

## 4. Rendering truth

### What RSC treats as truth (presentation)

| Question | RSC answer source |
|----------|-------------------|
| What should the merchant see **right now**? | Current `RenderingSnapshot` only |
| Are counts final? | `freshness === final` |
| Should story cards show? | `bodyMode === stories` |
| Should pending whisper show? | `bodyMode === pending` |
| Should empty whisper show? | `bodyMode === empty` |

### What RSC does **not** own (operational truth)

| Domain | Owner | RSC relationship |
|--------|-------|------------------|
| Lifecycle / archive / reopen | Lifecycle APIs + row fields | RSC displays rows after data plane updates |
| Primary action projection | `cart_page_primary_action_v1` | RSC counts from rows when freshness=final |
| Snapshot / hot-slice | Backend snapshot read | Data plane proposes `APPLY_*` events |
| Filter bucket totals | `merchant_cart_filter_counts` | Separate from verdict; must not drive bodyMode |

**Rendering truth ≠ operational truth.** RSC may show last-good stories while freshness=pending; that is honest UI, not a claim that counts are final.

---

## 5. Who can update the screen

### Allowed writers (data plane → RSC events only)

| Actor | Allowed action |
|-------|----------------|
| `hydrateNormalCartsCache` | Emit `CACHE_HYDRATED` with rows (+ optional cached MI if later persisted) |
| `fetchNormalCarts` | Emit `FETCH_STARTED` / `FETCH_FAILED` |
| `applyNormalCarts` | Emit `APPLY_SUCCESS`, `APPLY_KEEP`, `APPLY_CONFIRMED_EMPTY` |
| Lifecycle optimistic patches | Emit `ROWS_PATCHED` (rows only); RSC recomputes plan; must not bypass RSC |
| Hash / ensure / visibility | Emit `REVALIDATE_REQUESTED` → fetch; must not call presenters directly |

### Allowed painters (view plane)

| Actor | Allowed action |
|-------|----------------|
| `paintAttentionVerdict(plan)` | Write verdict host from plan |
| `paintCartBody(plan)` | Write groups/empty hosts from plan.bodyMode |
| `paintFilters(counts)` | Update chip numbers (not composition) |
| `paintConversationPanel(selection)` | Detail only |

**Single paint entry:** RSC `commit(snapshot)` → calls painters once per accepted transition.

---

## 6. Who cannot update the screen

| Actor | Forbidden |
|-------|-----------|
| `renderCartsAttentionVerdictV1` (as decision maker) | Choosing refreshing vs needs_you from private flags |
| `renderMiCartsV1Workspace` | Calling `hasRenderablePayload` to choose pending vs stories |
| `renderMiCartsV1Pending` | Self-invoking based on payload shape |
| `rerenderCartsFromMemory` | Direct `renderNormalCartsTables` that invents merchant-visible state |
| `showNormalCartsLoadingState` | Touching groups/verdict hosts |
| CSS / media queries | Hiding “final” content or inventing pending |
| Filter apply | Switching bodyMode to pending/empty |
| Test hooks / ad-hoc DOM writes | Except via RSC in tests |

Any of the above that still exist as functions must become **thin adapters** that only forward events or paint plans.

---

## 7. Last-good state policy

### Definition

**Last-good** = the most recent snapshot where:

- `phase === final` **or**
- body successfully showed `stories` with a coherent MI payload

Stored as `lastGood: { rows, miPayload, verdictMode, bodyMode, appliedGen }`.

### Rules

1. **Never discard last-good MI** on `APPLY_KEEP`, cache hydrate, or memory rerender.
2. On `CACHE_HYDRATED` / `APPLY_KEEP` / soft `FETCH_STARTED`:
   - `freshness = pending`
   - `verdictMode = refreshing`
   - `bodyMode = stories` if `lastGood.miPayload` exists; else `pending` or `loading`
3. On `APPLY_SUCCESS`, replace last-good with the new live snapshot.
4. On `APPLY_CONFIRMED_EMPTY`, last-good may clear body to empty (terminal honesty).
5. Optimistic archive/reopen updates **rows** inside last-good / current snapshot via `ROWS_PATCHED`, then RSC recomputes; do not drop MI.

This directly addresses the lifecycle audit root cause: MI-less memory paint overwriting `lastMerchantIntelligencePayload`.

---

## 8. Pending policy

| Concern | Policy |
|---------|--------|
| **Verdict pending** | Always when `freshness === pending`. Copy: calm «جارٍ تحديث الصورة...». Never show final count headlines. |
| **Body pending whisper** | Only when `bodyMode === pending` **and** no last-good stories. |
| **Body with last-good** | Prefer stories + pending verdict (refresh badge), not «يجهّز فهم هذه السلال…». |
| **Boot with nothing** | `bodyMode = loading`; verdict `loading`/`refreshing`. |
| **Semantics** | Pending means “not final,” not “blank the page.” |

---

## 9. Refresh policy

| Event | Behavior |
|-------|----------|
| Soft refresh (poll, visibility, token) | `FETCH_STARTED` → phase `refreshing`; keep last-good body; pending verdict |
| Hard boot | Cache hydrate (if any) then fetch; same last-good rules |
| Keep/degraded responses | `APPLY_KEEP` → stay `refreshing`; schedule retry; **do not** MI-wipe |
| Successful apply | `APPLY_SUCCESS` → `final`; update last-good; clear pending |
| Concurrent fetches | Only higher/equal `fetchGen` may commit; stale gens ignored (existing gen guard) |

Refresh must never look like a full page teardown unless last-good is absent.

---

## 10. Failure policy

| Failure | RSC behavior |
|---------|--------------|
| Network / parse error | `failed`; pending verdict; keep last-good body; retry per existing scheduler |
| Exhausted retries | Stay `failed` with calm copy; do not invent empty or final counts |
| Confirmed full empty | `final` + `empty` (not failure) |
| Partial empty with no last-good | `refreshing`/`failed` + `loading`/`pending` — never fake “no carts” |

Failure must not present stale counts as final (freshness stays pending until `APPLY_SUCCESS`).

---

## 11. Current architecture → Target architecture

### Current (distributed owners)

```text
┌──────────────┐   ┌─────────────────┐   ┌──────────────────────┐
│ sessionStorage│──►│ hydrate / memory │──►│ renderNormalCartsTables│
└──────────────┘   │ (rows, no MI)    │   │ lastMI = d (wipe)     │
                   └────────┬────────┘   └──────────┬───────────┘
┌──────────────┐            │                       │
│ fetch/apply  │────────────┼───────────────────────┤
│ guards/keep  │            │                       ▼
└──────────────┘            │         ┌─────────────────────────────┐
                            │         │ renderMiCartsV1Workspace     │
                            │         │  if !hasRenderablePayload    │
                            │         │    → Pending UI (decides)    │
                            │         │  else → Story Cards (decides)│
                            │         └──────────────┬──────────────┘
                            ▼                        │
                   ┌────────────────────┐            │
                   │ Attention Verdict  │◄───────────┘  (also called alone)
                   │ pending flags      │
                   │ (decides counts)   │
                   └────────────────────┘

Empty UI / filters / panel also paint without a shared plan.
```

**Problem:** Multiple decision makers → verdict/body drift, MI wipe on keep, cross-device pending vs final.

### Target (single Rendering Owner)

```text
┌─────────────────────────────────────────────────────────────┐
│                 DATA PLANE (propose only)                   │
│  cache hydrate │ fetch │ apply guards │ lifecycle patches   │
│         emit: CACHE_HYDRATED / FETCH_* / APPLY_* / ROWS_*   │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          CartPageRenderingStateController (SOLE OWNER)      │
│  state machine + lastGood + freshness + bodyMode + verdict  │
│  commit(RenderingSnapshot) — one plan per accepted event    │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              VIEW PLANE (paint only — no decisions)         │
│  Attention Verdict │ Pending UI │ Empty UI │ Story Cards    │
│  (MI Workspace is a painter for bodyMode=stories)           │
│  Filters / Conversation panel: secondary, plan-constrained  │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Implementation boundaries

| In scope (Phase 2.6 shipped) | Out of scope |
|------------------------------|--------------|
| Cart page composition only | Snapshot builder, lifecycle APIs, recovery |
| Client presentation state machine | Backend “verdict” field |
| Last-good MI preservation | Redesign of story card visuals |
| Align with freshness hotfix intent | Phase 3 automatic band product work |
| Tests: transitions + last-good keep | Desktop-only CSS hacks |

Shipped module shape:

- `static/cart_page_rendering_state_controller_v1.js` — state machine + commit
- Presenters in `merchant_dashboard_lazy.js` / MI module paint from RSC plan (legacy fallback if controller missing)
- Build id: `ui-setup-v8f-rsc-v1`
---

## 13. Acceptance criteria for this design

Implementation matches this design when:

1. Exactly one module may set merchant-visible Cart composition. ✅ `CartPageRenderingStateController`
2. Verdict, Pending, Empty, and Story Cards never choose mode from private predicates. ✅ paint-from-plan
3. `APPLY_KEEP` / cache hydrate cannot clear last-good stories. ✅ covered by transition tests
4. Final count headlines appear only when `freshness === final`. ✅
5. Desktop and mobile, given the same RSC snapshot, show the same verdict + body (layout may differ). ✅ same plan, shared painters

---

## 14. Relationship to LGE

| Concern | LGE V1 | RSC V1 |
|---------|--------|--------|
| Story card open/close / locks | Yes | No |
| Page-level pending vs final composition | No | Yes |
| DOM as authority | Forbidden | Forbidden |
| Governor / Controller split | Lifecycle transitions | Rendering transitions |

RSC may later register Cart page composition as an LGE-governed surface; until then, RSC is the **presentation composition constitution** for Cart Page V2.
