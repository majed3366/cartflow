# Sprint 2.3 — Live Timing Confirmation + Smallest Repair

**Status:** LIVE CONFIRMED + REPAIR APPLIED (reason arm)  
**Date (UTC):** 2026-07-11  
**Evidence:** `scripts/_sprint2_3_op_fast_path_live_timing_v1_out/live_timing_report_v1b.json`  
**Cart:** `cf_cart_fc348d23-987c-401b-afaa-87604c19877b` / AbandonedCart `4287` / store `cartflow-42b491`

---

## Live timing table (one real production cart)

| Stage | Measured |
|-------|----------|
| Add → cart_persisted | 5910 ms (empty-cart bridge retries during add — **before** reason) |
| Widget reason click → bridge ensure | **0.3 ms** (`already: true`, cart_persisted) |
| Reason POST start → end | **2343.2 ms** ← **first over-budget after reason click** |
| AbandonedCart truth visible | **~2.7 s** (not minutes) |
| Refresh token / hot-slice UI | requires merchant session (not captured this run) |

Empty-retry ladder fired during **add** (2 scheduled / 2 fired), not during the reason-click wait.

---

## A) Widget latency — confirmed

**Is the cart-bridge retry ladder the first over-budget stage after reason click?**  
**No.** When cart identity was already persisted, bridge ensure was 0.3 ms.

**First over-budget stage after reason click:**  
`POST /api/cartflow/reason` while **awaiting** `_schedule_normal_recovery_after_cart_recovery_reason_saved` (~2.3 s).

---

## B) Dashboard latency — confirmed (partial)

- AbandonedCart row existed within **seconds** after persist (`abandoned_cart_id=4287`).
- That id is the live `:c{max_id}` source for refresh-state.
- Therefore the **cart-truth → revision source** path fires in seconds; minute-scale UI lag is **not** explained by late AbandonedCart insert.
- Merchant-cookie capture of `refresh-state` token change + `hot-slice` merge was **not** available this run (`CARTFLOW_PROD_*` unset). No refresh-token / hot-slice code change applied (not proven failed).

---

## Repair applied (smallest confirmed)

**Only:** detach recovery arm from the reason HTTP response.

- `routes/cartflow.py`: after reason commit, `background_tasks.add_task(_arm_recovery_after_reason_saved_bg, …)`
- Fresh DB scope via `scoped_db_session_begin` / `release_scoped_db_session`
- Profile phases: `committed_reason_response` (response path) + `recovery_arm_background`
- **Not changed:** polling, retries, timeouts, UI, «رسالة أُرسلت» / `sent_real` semantics
- **Not applied:** bridge fail-fast (not first over-budget on reason click)  
- **Not applied:** refresh-token / hot-slice edits (B not proven failed)

Tests: `tests/test_sprint2_3_reason_arm_fast_path_v1.py`

---

## «رسالة أُرسلت»

Unchanged: **C) Provider accepted** — `sent_real` only via `merchant_filter_bucket_for_lifecycle`.

---

## Acceptance remaining

Sprint stays **OPEN** until merchant production journey visually confirms:

1. Reason click advances within ~1 s (reason HTTP fast; arm in background)  
2. New cart counters/rows update in seconds on an open dashboard tab  
3. «رسالة أُرسلت» only for real sends  
