# Rendering State Controller — Stability Investigation

**Date (UTC):** 2026-07-09  
**Scope:** Investigation only — no code changes  
**Build:** `ui-setup-v8f-rsc-v1`  
**Surface:** Cart Page V2 (`#page-carts`)  
**Related:** `docs/architecture/rendering_state_controller_v1.md`, Phase 2.6 ship `bbf1163`

---

## Verdict

**FINAL is not a merchant-visible terminal state under current wiring.**

After a successful `APPLY_SUCCESS`, any subsequent `fetchNormalCarts(...)` immediately dispatches `FETCH_STARTED`, which forces:

- `phase = refreshing`
- `freshness = pending`
- verdict copy «جارٍ تحديث الصورة...»

That fetch is driven primarily by the **2.5s refresh-token watcher** (and secondarily by pending-cart / keep-retry loops). Phase 2.6 made this worse than the freshness hotfix: soft refreshes after a final verdict used to **skip** re-pending the verdict; RSC now **always** re-enters Refreshing on every fetch.

`ROWS_PATCHED` is **not** the cause of re-entering Refreshing when already final.

---

## 1. Which event(s) trigger repeated FINAL → Refreshing?

| Event | Forces Refreshing? | Merchant-visible effect |
|-------|--------------------|-------------------------|
| **`FETCH_STARTED`** | **Yes — always** | Verdict → refreshing / pending |
| `APPLY_KEEP` | Yes (stays refreshing) | Pending verdict; last-good body preferred |
| `FETCH_FAILED` | Yes → `failed` | Pending verdict; last-good body |
| `CACHE_HYDRATED` | → `cached` (pending) | Boot/cache only |
| `APPLY_SUCCESS` / `APPLY_CONFIRMED_EMPTY` | → `final` | Final verdict |
| **`ROWS_PATCHED`** | **No** (if already `final`) | Recomputes final verdict from rows |

**Normative code** (`static/cart_page_rendering_state_controller_v1.js`):

```317:350:static/cart_page_rendering_state_controller_v1.js
      if (eventType === EVENTS.FETCH_STARTED) {
        // ... any prior phase including FINAL ...
        next.phase = PHASE.REFRESHING;
        next.freshness = "pending";
        // ...
        next.verdict = buildRefreshingVerdict(next.counts);
```

**Emitter that matters after settle** (`static/merchant_dashboard_lazy.js`):

```5564:5575:static/merchant_dashboard_lazy.js
  function fetchNormalCarts(label) {
    var gen = ++normalCartsFetchGen;
    showNormalCartsLoadingState();
    // Soft refresh: RSC enters refreshing; keep last-good body when present.
    rscDispatch("FETCH_STARTED", {
      rows: activeNormalCartRows(lastNormalCartsPageRows || []),
      miPayload: lastMerchantIntelligencePayload,
      reason: label || "fetch",
      fetchGen: gen,
    });
    cartsAttentionVerdictFresh = false;
    cartsAttentionVerdictPending = true;
```

Also: `markAttentionVerdictRefreshing(reason)` independently dispatches `FETCH_STARTED` (used by keep/empty/retry paths). That is expected for degraded paths; it is **not** required for soft token refresh, but `fetchNormalCarts` already covers that.

---

## 2. Is polling causing it?

**Yes — primary cause of “every few seconds.”**

| Poller | Interval | Condition | Effect on RSC |
|--------|----------|-----------|---------------|
| `startRefreshWatcher` → `checkRefreshState` | **2500ms** (skips when `document.hidden`) | Token change → `scheduleNormalCartsTokenRefetch` → `fetchNormalCarts("token_refresh_state")` | **`FETCH_STARTED` → Refreshing** |
| `startPendingNewCartWatcher` | **1200ms**, up to 25 tries | `sessionStorage.cartflow_cart_event_id` present and not yet in rows | `fetchNormalCarts("pending_cart_poll")` → Refreshing each tick |
| `scheduleNormalCartsRetry` | **1200ms** once | After thin/partial/unconfirmed keep | Another fetch → Refreshing |
| `visibilitychange` | on tab focus | Only fetches if **no** rows | Occasional |

Watcher wiring:

```6430:6445:static/merchant_dashboard_lazy.js
  function startRefreshWatcher() {
    if (merchantRefreshTimer) return;
    checkRefreshState();
    merchantRefreshTimer = window.setInterval(function () {
      if (document.hidden) return;
      checkRefreshState();
    }, 2500);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) {
        checkRefreshState();
        if (!lastNormalCartsPageRows.length) {
          fetchNormalCarts("visibility_resume");
        }
```

Token change path:

```6418:6423:static/merchant_dashboard_lazy.js
        if (next !== merchantDashboardRefreshToken) {
          // ...
          scheduleNormalCartsTokenRefetch("token_refresh_state");
        }
```

`scheduleNormalCartsTokenRefetch` always calls `fetchNormalCarts(label)` once boot is complete (no debounce, no “silent” mode).

**Note:** Polling `refresh-state` alone does **not** touch RSC. Only a **token delta** (or other fetch triggers) does. If the live token is stable, the 2.5s poll is quiet. Instability appears when:

1. Token **actually changes** (new recovery log / sent / archive rev), or  
2. Token **oscillates** across sources (see § Trigger source), or  
3. **Pending-cart** / **retry** loops keep calling `fetchNormalCarts`.

---

## 3. Is `ROWS_PATCHED` treated as a fresh load?

**No.**

When `phase === final` and `freshness === final`, `ROWS_PATCHED`:

- Updates rows/counts
- Re-derives **final** verdict
- Does **not** set `phase = refreshing`
- Does **not** set `freshness = pending`

Emitters: lifecycle optimistic patch (`rerenderAllCartsTable`), non-keep `rerenderCartsFromMemory` (e.g. `ensure_*` / hash).

So archive/reopen row patches are **not** the refresh loop. (They may still call `fetchNormalCarts("lifecycle_*")` afterward, which **does** re-enter Refreshing via `FETCH_STARTED`.)

---

## 4. Is `FETCH_STARTED` emitted too often?

**Yes — both frequency and semantics.**

### Frequency sources after first FINAL

1. **Token refetch** — every time `merchant_dashboard_refresh_token` differs (watcher 2.5s, or `ingestRefreshToken` from `normal-carts` / `summary` / `messages`).
2. **Pending cart poll** — every 1.2s while seeded `cartflow_cart_event_id` is unresolved (up to ~30s).
3. **Keep retries** — 1.2s after thin/partial/unconfirmed.
4. **Lifecycle follow-up fetch** — after archive/reopen.
5. **`refreshCoreSections`** — also calls `fetchNormalCarts("refresh_core")` (token path uses `scheduleNormalCartsTokenRefetch`, not always `refreshCoreSections`).

### Semantic regression vs pre-RSC freshness hotfix

Before Phase 2.6, `fetchNormalCarts` only forced pending when the verdict was **not already fresh**:

```text
if (!cartsAttentionVerdictFresh) {
  markAttentionVerdictRefreshing(label || "fetch");
}
```

After Phase 2.6, **every** `fetchNormalCarts` unconditionally:

1. `rscDispatch("FETCH_STARTED")` → merchant Refreshing  
2. Clears `cartsAttentionVerdictFresh`

So a settled FINAL page cannot survive a soft background refetch without flashing Refreshing. That is the direct answer to “why does it repeatedly re-enter Refreshing after reaching a stable state?”

---

## 5. Does successful APPLY ever become a terminal stable state?

**Operationally: no (merchant-visible).**

| Layer | After `APPLY_SUCCESS` |
|-------|------------------------|
| RSC phase | `final` (briefly) |
| RSC freshness | `final` (briefly) |
| Merchant verdict | Final counts / calm / automatic |
| Next soft fetch | Immediate `FETCH_STARTED` → **not terminal** |

Design doc already allowed `final → FETCH_STARTED → refreshing` for soft refresh, with last-good body. That is fine for **data**. It is **not** fine for **merchant-visible verdict** if every poll-driven fetch paints «جارٍ تحديث الصورة...».

`APPLY_SUCCESS` is therefore a **transient** state whenever any of the fetch drivers above remain active — which they do for the whole dashboard session (`startRefreshWatcher` never stops).

---

## 6. State transition log (one page session)

Canonical sequence for a carts tab left open after boot (labels = `fetchNormalCarts` / RSC reasons):

```text
BOOT
  → CACHE_HYDRATED          (sessionStorage hit; phase=cached, freshness=pending)
  → FETCH_STARTED           reason=boot_priority
  → APPLY_SUCCESS           phase=final, freshness=final   ← first settle
  → (optional) FETCH_STARTED reason=token_* / boot_done ensure
  → APPLY_SUCCESS           final again

  ── stable window (often < 2.5s–few seconds) ──

  → FETCH_STARTED           reason=token_refresh_state     ← unexpected for UX
  → APPLY_SUCCESS | APPLY_KEEP
  → FETCH_STARTED           reason=token_refresh_state | pending_cart_poll | normal_carts_retry_*
  → APPLY_SUCCESS | APPLY_KEEP
  → … loop while tab visible …

UNEXPECTED (merchant-visible):
  FINAL ──FETCH_STARTED──► REFRESHING   (soft poll / token / pending poll)
```

Console breadcrumbs to confirm on a live session:

- `[CLIENT REFRESH] rsc_commit` — `phase`, `freshness`, `reason`
- `[CLIENT REFRESH] token_changed` / `token_update`
- `[CLIENT REFRESH] normal_carts_applied` / `attention_verdict_refreshing`

---

## Trigger source (ranked)

1. **Primary (architecture):** Unconditional `FETCH_STARTED` inside `fetchNormalCarts` after Phase 2.6 — turns every soft refetch into merchant Refreshing.  
2. **Primary (driver):** `refresh-state` watcher @ 2.5s → token delta → `fetchNormalCarts("token_refresh_state")`.  
3. **Amplifier:** `ingestRefreshToken` on apply of `normal-carts` / `summary` / `messages` can schedule **another** refetch if embedded token ≠ client token (snapshot vs live refresh-state skew / partial tokens).  
4. **Session amplifier:** `pending_cart_poll` @ 1.2s when `cartflow_cart_event_id` is set (common after widget seed / prod verify).  
5. **Degraded amplifier:** thin/partial/unconfirmed → `APPLY_KEEP` + retry fetch.  
6. **Not a cause:** `ROWS_PATCHED` while already final.

Token shape (live): `{slug}:{max_log_id}:{max_sent_id}:{sent_total}:{max_archive_rev}` — any recovery/archive activity changes it and legitimately refetches. Oscillation between empty/partial snapshot tokens and live tokens can refetch even without merchant action.

---

## Why mobile refreshes every few seconds

Same SPA as desktop. Visible cadence matches:

- **~2.5s** when refresh token keeps changing or oscillating, or  
- **~1.2s** when pending-cart watcher is active.

Mobile feels “constant refresh” because the Attention Verdict headline flips to «جارٍ تحديث الصورة...» on each `FETCH_STARTED`, even when story cards (last-good) remain. Background tab is quieter (`document.hidden` skips the interval).

---

## Why desktop never settles

Same mechanism. Desktop often:

- Stays on `#carts` longer with the watcher running  
- May keep `cartflow_cart_event_id` from earlier journeys  
- May have multiple overlapping fetches (boot + token + retry) so FINAL is overwritten before it is perceived as stable  

There is **no desktop-only RSC branch**. “Never settles” = FINAL repeatedly interrupted by `FETCH_STARTED` from soft fetches.

---

## Recommended transition-policy change (do not implement here)

### Policy intent

- **Data plane** may soft-refetch freely.  
- **Merchant-visible Refreshing** must not re-enter from FINAL on silent/background refetch.  
- Refreshing is for: boot, cache hydrate, first paint, hard failure recovery, explicit user refresh, or confirmed stale-empty/degraded keep — not for every token poll.

### Concrete policy (recommended)

1. **Split events** (preferred):
   - `FETCH_STARTED` — merchant-visible refreshing (boot / explicit / no last-good).  
   - `SOFT_REVALIDATE` (or `FETCH_SILENT`) — bump `fetchGen` only; **keep** `phase=final`, `freshness=final`, verdict unchanged until `APPLY_*`.  
2. **Or gate `FETCH_STARTED`:** if `phase===final && lastGood` and reason ∈ `{token_*, refresh_core, pending_cart_poll, visibility_resume}`, do **not** commit refreshing; only track in-flight gen.  
3. **Restore pre-RSC freshness rule:** do not clear final verdict on soft fetch; only `APPLY_SUCCESS` may update final counts; `APPLY_KEEP` may show refreshing **without** wiping last-good (already true for body).  
4. **Debounce token refetch** (secondary): coalesce token changes within e.g. 2–5s; ignore no-op applies.  
5. **Stop pending-cart poll** once cart appears **or** after N tries without flipping verdict each tick (silent fetch).  
6. **Keep `ROWS_PATCHED` as-is** — it correctly stays final.

### Acceptance after a future fix

- One page session: `… → APPLY_SUCCESS → FINAL` remains FINAL across ≥N quiet `refresh-state` polls with unchanged token.  
- Token change updates rows/stories without mandatory «جارٍ تحديث الصورة...» flash when last-good exists.  
- Boot / empty / failed paths still show honest pending.  
- Desktop and mobile still converge on the same plan.

---

## Answers checklist

| Question | Answer |
|----------|--------|
| 1. Events back to Refreshing? | Almost exclusively **`FETCH_STARTED`** (plus `APPLY_KEEP` / `FETCH_FAILED` on degraded paths). |
| 2. Polling? | **Yes** — 2.5s token watcher is the main driver; 1.2s pending-cart/retry amplify. |
| 3. `ROWS_PATCHED` as fresh load? | **No** when already final. |
| 4. `FETCH_STARTED` too often? | **Yes** — every `fetchNormalCarts`, including soft token polls (Phase 2.6 regression vs freshness hotfix). |
| 5. APPLY final terminal? | **Not merchant-visible** while soft fetches continue. |
| 6. Transition log | See §6 — `FINAL → FETCH_STARTED → REFRESHING` is the unexpected UX loop. |

---

## Out of scope / not done

- No code fixes  
- No Phase 3  
- No production redeploy
