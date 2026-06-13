# Normal Carts Architecture Recovery v1 — Production Verification

**Date (UTC):** 2026-06-13  
**Endpoint:** `GET /api/dashboard/normal-carts`  
**Verdict:** **PASS (local verification gate)** — **awaiting production deploy** for live laptop/mobile parity check

---

## Local verification gate (pre-deploy)

Executed: `python scripts/normal_carts_batch_verify_v1.py --rows 45`

| Requirement | Target | Result |
|-------------|--------|--------|
| No `partial` | `partial=false` | **PASS** |
| No deadline exceeded | `degraded=false`, `timeout_stage=null` | **PASS** |
| `visible_rows` matches scale | 45 visible / 45 seeded | **PASS** |
| Business query budget | ≤ 55 | **PASS** (37) |
| Wall time | < 12s (local SQLite) | **PASS** (355ms post-warm) |
| `_perf` block present | `query_count`, `duration_ms`, `candidate_rows`, `visible_rows`, `partial` | **PASS** |

Evidence: `scripts/_normal_carts_batch_verify_v1_out/verify_report.json`

**Unit tests:** `tests/test_normal_carts_dashboard_batch_v1.py` — **3 passed** (query budget 10/50 rows, `_perf` on API JSON).

---

## Production checklist (run after deploy)

| # | Check | Method |
|---|--------|--------|
| 1 | `GET /api/dashboard/normal-carts` → 200, `ok:true` | Laptop + mobile Playwright (fresh context) |
| 2 | `_perf.partial` = false, `_perf.degraded` absent/false | Parse JSON body |
| 3 | `_perf.visible_rows` > 0 for store with normal carts | Same |
| 4 | `_perf.duration_ms` stable on repeat fetch (no 14s spikes) | Two fresh fetches, compare `_perf.duration_ms` |
| 5 | Laptop vs mobile row count parity | Same `merchant_carts_page_rows.length` |
| 6 | No `timeout_stage=payload_row` in logs | Server `[DASHBOARD STAGE]` / `_perf.timeout_stage` |

---

## Regression scope

| Area | Expected |
|------|----------|
| VIP `GET /api/dashboard/vip-carts` | Unchanged (separate batch module) |
| `customer_lifecycle_state` on rows | Still authoritative (LT-C1) |
| Archived tab rows | Still from unified build (`merchant_archived_carts_page_rows`) |
| `refresh-state` | Still merged in API payload |

---

## Notes

- Pre-recovery production symptom (`partial=1`, `rows_built=6` of 45 candidates, ~14s) matches per-row projection N+1; local post-fix build projects 46 rows in ~31ms projection phase with zero partial/degraded flags.
- Production deploy not performed in this session; re-run this checklist on `https://smartreplyai.net` after push.

---

**STOP — local verification complete; production sign-off pending deploy.**
