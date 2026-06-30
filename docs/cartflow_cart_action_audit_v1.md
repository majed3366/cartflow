# CartFlow — Cart Action Audit V1

**Date (UTC):** 2026-06-30  
**Status:** Read-only audit + **Cart Archive Identity Fix V1** (2026-06-30)  
**Scope:** Every merchant-initiated cart action: DB writes, lifecycle effects, expected vs actual behavior. Includes root-cause analysis and fix for **«archiving one cart archives multiple carts»**.

---

## Fix status — Cart Archive Identity V1 (2026-06-30)

| Item | Status |
|------|--------|
| Bug: session-only key mutates sibling carts | **Fixed** |
| Module | `services/cart_action_identity_v1.py` |
| Archive/reopen | `filter_mutation_recovery_keys()` — session-only aliases excluded from writes |
| Read path | `any_merchant_archived_for_mutation_keys()` — lifecycle attach ignores session-only archive rows |
| Frontend | `rowMatchesLifecycleKey()` — no longer matches all rows by `session_id` |
| Tests | `tests/test_cart_action_identity_v1.py` |

### Identity rule (mutation actions)

| Key type | Example | Read/diagnostic | Archive/reopen write |
|----------|---------|-----------------|----------------------|
| Session-only | `store_slug:session_id` | Allowed | **Forbidden** |
| Cart-specific | `store_slug:session_id:cart_id` | Allowed | Allowed |
| Log recovery key | `store_slug:log-…` | Allowed | Allowed (when tied to target cart) |

Session-only keys remain in `canonical_recovery_keys_for_cart()` for log matching and diagnostics but **must not** be passed to `archive_recovery_keys` / `reopen_recovery_keys` or used to infer `merchant_archived` on sibling carts.

---

## 1. Action inventory

| Action | UI location | API | Identity sent |
|--------|-------------|-----|---------------|
| Archive | Per-row `نقل للأرشيف` | `POST /api/dashboard/cart-lifecycle/archive` | `recovery_key`, `store_slug`, `abandoned_cart_id`, `session_id`, `cart_id` |
| Reopen | Per-row `إعادة فتح` | `POST /api/dashboard/cart-lifecycle/reopen` | Same payload shape |
| VIP manual contact | VIP row `تواصل يدوي` | `GET /api/dashboard/vip-cart/{id}/manual-contact` | `AbandonedCart.id` |
| Follow-up list | Tab **تحتاج تدخل** | `GET /api/dashboard/followups` | List only |
| Mark follow-up complete | Legacy `vip_cart_settings.html` only | `POST /api/merchant-followup-actions/{id}/complete` | `action_id` |

**Not implemented:** Bulk archive/reopen, bulk mark-complete on `merchant_app.html`.

---

## 2. Archive

### 2.1 Expected behavior

- Merchant archives **one cart case**.
- Case leaves active operational list; appears under **مكتملة** / archived slice.
- Lifecycle shows `archived` / `reopen` action.
- Recovery workers **continue** unless separately gated — archive is merchant display flag (route docstring in `main.py`).

### 2.2 Frontend flow

`static/merchant_dashboard_lazy.js`:

- `cartLifecycleActionBtnHtml()` — one `data-recovery-key` per row.
- `lifecycleActionPayload(mc, rk)` — single `abandoned_cart_id`, single `recovery_key`.
- On success: `patchCartRowArchivedVisual` → `fetchNormalCarts` → `goToCartTab("completed")`.

### 2.3 Backend flow

`POST /api/dashboard/cart-lifecycle/archive` (`main.py`):

1. Require `recovery_key`.
2. Resolve `AbandonedCart` by `abandoned_cart_id` → `session_id` → session from RK → `zid_cart_id`.
3. Expand **`alias_keys`** via `canonical_recovery_keys_for_abandoned_cart()`.
4. Call `archive_recovery_keys(alias_keys, ...)`.

### 2.4 Alias expansion (critical)

`services/merchant_dashboard_recovery_resolve_v1.py` — `canonical_recovery_keys_for_cart()` always adds:

```python
# When session_id present:
recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id="")  # session-only key
recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=cid)   # session+cart key
# Plus log recovery_key and store:cart_id variants
```

**Session-only key** (`store:session_id`) is **shared across all carts in the same browser session**.

### 2.5 Database writes (per archive click)

| Table | Rows affected | Write |
|-------|---------------|-------|
| `merchant_cart_lifecycle_archives` | **One row per alias key** (typically 2–4+) | UPSERT: `is_archived=True`, `archived_at`, `archive_source='manual'` |
| `lifecycle_closure_records` | **One row per alias key** | `closure_status=cancelled`, `closure_reason=merchant_archived:manual` |

Service: `services/merchant_cart_lifecycle_archive_v1.py` — `archive_recovery_keys()` loops all deduped alias keys with **commit per key**.

### 2.6 Lifecycle / list effects

- Lifecycle attach uses **full alias list**: `any_merchant_archived_for_alias_keys(...)`.
- Active vs archived **bucket filter** uses narrower `_merchant_batch_manual_archived()` — only primary log key + parts key, **not** full alias list.

**Split behavior:** Sibling cart in same session may show archived lifecycle styling while still appearing on active list until refresh — looks like partial multi-archive.

### 2.7 Expected vs actual

| Aspect | Expected | Actual |
|--------|----------|--------|
| Carts archived per click | 1 | 1 intended; **N keys persisted** |
| Visible rows affected | 1 | 1–N depending on shared session key |
| DB archive rows | 1 | **N** (= len(alias_keys)) |
| Recovery engine | Unchanged | Unchanged (display flag) |
| Closure records | 0–1 | **N** closure rows |

---

## 3. Reopen

### 3.1 Expected behavior

Clears merchant archive for one case; restores active visibility; reclassifies lifecycle from evidence.

### 3.2 Database writes

| Table | Rows | Write |
|-------|------|-------|
| `merchant_cart_lifecycle_archives` | One per alias key | `is_archived=False`, `reopened_at=now` |
| `lifecycle_closure_records` | **None** | Reopen does not reverse closure rows |

### 3.3 Response

`lifecycle_payload_for_reopen(rk)` — reclassifies for **clicked** recovery key only; frontend applies via `patchCartRowArchivedVisual(rk, false, d.lifecycle)`.

**Same alias expansion as archive** — reopen clears all alias keys for the cart case.

---

## 4. VIP manual contact

| Aspect | Detail |
|--------|--------|
| UI | `<a href="contact_href">تواصل يدوي (VIP)</a>` — opens `wa.me` in browser |
| API | Read-only `GET /api/dashboard/vip-cart/{cart_row_id}/manual-contact` |
| DB writes | **None** |
| Lifecycle | No change |
| Expected | Merchant contacts customer outside CartFlow send path |
| Actual | Matches — no server send, no lifecycle write |

---

## 5. Follow-up tab (تحتاج تدخل)

| Aspect | Detail |
|--------|--------|
| UI | `#page-followup` — separate table schema from main carts |
| API | `GET /api/dashboard/followups` — `MerchantFollowupAction` where `status=needs_merchant_followup` |
| Creation | **System** — `whatsapp_positive_reply.py` on positive inbound (phone-keyed UPSERT) |
| DB writes (merchant click) | **None** on follow-up tab itself |
| Gap | Server provides `contact_wa_href` but lazy JS **does not render** contact link on follow-up rows |
| Mark complete | **Not wired** in `merchant_app` — only legacy VIP settings page |

---

## 6. Mark follow-up complete

| Aspect | Detail |
|--------|--------|
| UI | `templates/vip_cart_settings.html` only |
| API | `POST /api/merchant-followup-actions/{id}/complete` |
| DB writes | `merchant_followup_actions.status` → completed |
| Lifecycle | No cart lifecycle change |
| Gap | Action exists but **not exposed** on primary merchant dashboard |

---

## 7. BUG: Archiving one cart appears to archive multiple carts

### 7.1 Verdict

**Confirmed — real architectural issue**, not bulk UI. Multiple mechanisms compound:

| # | Layer | Severity | Mechanism |
|---|-------|----------|-----------|
| A | Backend alias keys | **Primary** | Session-only `store:session_id` key shared across carts in same session |
| B | Frontend optimistic patch | **Secondary** | `rowMatchesLifecycleKey` matches all rows with same `session_id` |
| C | Lifecycle vs filter split | **Presentation** | Full alias archived for lifecycle; narrow key for active-list exclusion |
| D | Cart resolution | **Edge case** | Archive POST resolves cart without `store_id` filter |

### 7.2 Hypothesis A — Session-level alias key (primary)

**Code:** `canonical_recovery_keys_for_cart()` line 83:

```python
_add(recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=""))
```

Archive persists **every** alias in `archive_recovery_keys()`.

**Effect:** Cart A and Cart B sharing `recovery_session_id` both inherit archived status when `store:session` key is archived. If both carts use `store:session` as primary `recovery_key`, **both leave active list**.

Tests expect multi-key archive for one cart (`tests/test_merchant_dashboard_runtime_truth_v1.py`) — intentional for alias consistency, but session key crosses cart boundaries.

### 7.3 Hypothesis B — Optimistic UI over-match

**Code:** `merchant_dashboard_lazy.js` `rowMatchesLifecycleKey()`:

```javascript
var tail = key.split(":").slice(1).join(":");
if (tail && String(mc.session_id || "").trim() === tail) return true;
```

When `recovery_key` is `store:session`, **all rows with that session_id** get archived visual before server refresh.

### 7.4 Hypothesis C — Lifecycle vs bucket mismatch

- Lifecycle attach: full `_alias_keys_lc`.
- Active bucket: `_merchant_batch_manual_archived()` — narrower key set.

Sibling cart shows **مؤرشفة** chip while still counted active — merchant perceives «extra cart archived».

### 7.5 Hypothesis D — Unscoped cart lookup

Archive route resolves `AbandonedCart` by session/cart id **without `store_id` filter** — wrong cart → wrong alias set in edge cases.

### 7.6 What is NOT the cause

- Bulk archive UI — not implemented.
- Multiple `abandoned_cart_id` in payload — frontend sends one id.
- Store filter on archive table — writes include `store_slug` but lookup is by global `recovery_key`.

### 7.7 Recommended fix directions (future — not in this audit)

1. Stop persisting session-only alias keys when cart-specific stable key exists.
2. Align `_merchant_batch_manual_archived` with full alias list **or** namespace keys per `abandoned_cart_id`.
3. Restrict `rowMatchesLifecycleKey` to `recovery_key` + `abandoned_cart_id` only.
4. Add `store_id` filter to all archive/reopen cart resolution queries.

---

## 8. Store scoping summary

| Path | Store-scoped? |
|------|---------------|
| Normal-carts API | Yes — dashboard store row |
| Archive/reopen POST | Partial — slug on write; resolution often unscoped |
| Archive table lookup | By `recovery_key` globally |
| Follow-up list/complete | `store_id` null or dashboard store |
| VIP manual contact | Per cart id + VIP lane check |

---

## 9. State refresh after archive

1. Optimistic `patchCartRowArchivedVisual` + table rerender
2. `fetchNormalCarts("lifecycle_archive")` — splits `merchant_archived_carts_page_rows`
3. Navigate to `completed` tab
4. Session cache via `persistNormalCartsCache`

If alias collision affects siblings, refresh still shows them archived in lifecycle fields.

---

## 10. Source file index

| Concern | Path |
|---------|------|
| Archive service | `services/merchant_cart_lifecycle_archive_v1.py` |
| Archive routes | `main.py` (~17994–18173) |
| Alias keys | `services/merchant_dashboard_recovery_resolve_v1.py` |
| Closure side-effect | `services/lifecycle_closure_records_v1.py` |
| Dashboard JS | `static/merchant_dashboard_lazy.js` |
| Model | `models.py` — `MerchantCartLifecycleArchive` |
| Tests | `tests/test_merchant_dashboard_runtime_truth_v1.py` |

---

**End of document.**
