# Sprint 2.3 — Production Acceptance (commit `d692502`)

**Date (UTC):** 2026-07-11  
**Commit:** `d692502` — `fix: make widget reason transition fail fast` (pushed to `main`)  
**Artifacts:** `scripts/_sprint2_3_prod_acceptance_v1_out/`

---

## Deploy

| Probe | Result |
|-------|--------|
| HTTP `POST /api/cartflow/reason` (demo, no cart) | **534 ms** after warm (first poll 1237 ms) |
| Storefront timed reason after real cart persist | still **~2600 ms** wall (same order as pre-fix ~2343 ms) |

Deploy of `main` is on GitHub. Warm demo path is fast. Full cart reason path remains multi-second — likely remaining sync work on the request (`_ensure_cartflow_api_db_warmed` / persist), or API process not yet on `d692502`. **No further code change in this step** (acceptance-only mandate).

---

## Journey checks (automated)

| Check | Result |
|-------|--------|
| Auth (signup) | PASS |
| Add to cart (test-widget) | PASS |
| Reason clicked once | PASS |
| Reason → phone UI composite | **FAIL** (9829 ms includes UI waits; HTTP ~2.8 s) |
| Phone saved once | PASS |
| Desktop cart in seconds | **PASS** (~1.2 s, `hit=true`, all=3) |
| Mobile cart visible | **PASS** (`hit=true`, all=3) |
| «رسالة أُرسلت» without provider | **PASS** (sent=0) |
| 30 s stability | **PASS** (all=3, rows=3 stable) |
| Hero needs_you | Present («لديك 2 سلة تحتاج انتباهك») — matches intervention semantics |

**Automated verdict:** FAIL (reason transition budget)  
**Sprint status:** **OPEN** — merchant visual approval required.

---

## Captures

| Shot | File |
|------|------|
| Widget → phone step | `shots/05_after_reason.png` |
| Phone entered | `shots/06_phone_entered.png` |
| After phone save | `shots/07_after_phone.png` |
| Desktop carts | `shots/08_desktop_carts.png` |
| Mobile carts | `shots/09_mobile_carts.png` |
| Desktop after 30 s | `shots/10_desktop_after_30s.png` |

Cart: `cf_cart_61eb9ac9-f615-42c7-8ac5-ef55c7e92863`  
Merchant signup: `cf.s23accept.2b22c8d052@smartreplyai.net`

---

## What still needs human approval

1. Confirm reason click *feels* fast on a warm production session (not cold signup).  
2. Confirm desktop + mobile carts + counters match screenshots.  
3. Confirm «رسالة أُرسلت» stays truthful.  

If reason HTTP remains ~2.5 s after confirmed API roll of `d692502`, next repair target is **sync work still on the reason response path** (warm/persist) — not polling.
