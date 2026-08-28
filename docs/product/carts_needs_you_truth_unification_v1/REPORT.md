# Carts — Needs-You Truth Unification V1

**Date (UTC):** 2026-08-28  
**Status:** Truth-contract correction only. No snapshot recovery. No Scheduler. No Carts redesign. No new lifecycle states.

## What changed

Carts presentation (`static/merchant_ui_v2_carts.js`) now uses **one** action-based needs-you classifier for orientation, يحتاجني count, and يحتاجني queue membership.

`needsMerchantActionNow` = primary ∈ {contact_customer, follow_up_manually, review_cart}.

بانتظار الجاهزية with primary `wait` is **WAITING_ON_CARTFLOW**, not يحتاجني.

Snapshot miss with no hot-merged rows paints degraded/loading, not false calm.

`merchant_cart_filter_counts` is no longer allowed to overwrite Carts chips (mixed generation).

Primary-action mappings in `cart_page_primary_action_v1` are untouched.

## Living Store (25 rows)

Canonical يحتاجني **0**, wait **21**, الكل **25**. Raven: wait / بانتظار الجاهزية / not in يحتاجني.

## Pack

`01_CURRENT_DUAL_CONTRACT.md` … `07_REGRESSION.md`

---

CANONICAL NEEDS_YOU DEFINITION:  
السلال التي تتطلب إجراءً بشريًا من التاجر الآن — primary `contact_customer` / `follow_up_manually` / `review_cart` (`needsMerchantActionNow`)

WAITING_READY OWNERSHIP:  
WAITING_ON_CARTFLOW — not يحتاجني (primary `wait`)

ORIENTATION SOURCE:  
`countPrimary` on the same page rows (canonical needs-you / wait)

FILTER SOURCE:  
يحتاجني = `countPrimary.needs_you`; other chips from the same `state.rows` (no snapshot counter overwrite)

QUEUE SOURCE:  
Hot-merged `merchant_carts_page_rows`; `attention` membership = `needsMerchantActionNow`

SNAPSHOT REQUIRED:  
NO

CURRENT 25-ROW CONSISTENCY:  
CONSISTENT

OPERATIONAL REGRESSION:  
NO

SAFE FOR REAL-DEVICE CARTS REVIEW:  
YES (after this JS is on the review host)

STOP.
