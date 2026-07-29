# Capture Acceptance Criteria V1

**Status:** Binding checks before any asset may become `approved.png` / Production Ready.  
**Date (UTC):** 2026-07-29  

Nothing may be silently promoted. All four groups must pass.

---

## A. Product Truth

| # | Check |
|---|--------|
| A1 | Behaviour matches current production (or labeled demo path with disclosure) |
| A2 | State is reproducible via Scenario Execution Plan |
| A3 | No known hidden bugs represented as happy path |
| A4 | No temporary developer shortcuts / harness unlabeled |
| A5 | Face matches current approved merchant UI for that surface |

---

## B. Merchant Truth

| # | Check |
|---|--------|
| B1 | Merchant immediately understands the screen |
| B2 | No misleading empty state used as “intelligence” |
| B3 | No fake metrics, ROI, or invented badges |
| B4 | No unfinished/dev controls visible |
| B5 | Claim beside asset does not exceed Claim Publication Gate |

---

## C. Publication Quality

| # | Check |
|---|--------|
| C1 | Clean Arabic (readable, not cut off) |
| C2 | Consistent spacing / no broken layout |
| C3 | High resolution suitable for desktop + mobile use cases |
| C4 | No browser clutter unless intentional (storefront chrome) |
| C5 | No developer overlays, console, or debug banners |
| C6 | Complies with Screenshot Presentation Rules V1 |
| C7 | One Hero focus — not a collage |

---

## D. Privacy

| # | Check |
|---|--------|
| D1 | No real customer names |
| D2 | No real phone numbers |
| D3 | No personal identifiers |
| D4 | Synthetic / Living Store / demo merchant data only |
| D5 | Scrubbed before `approved.png` |

---

## Promotion workflow

```text
candidate.png
    ↓ pass A–D + owner sign-off
approved.png
    ↓
meta.status = Production Ready
meta.acceptance_result = pass
```

Fail any check → remain candidate / blocked; do not invent UI in an editor to force a pass.

---

## Special cases

| Case | Rule |
|------|------|
| Illustrative knowledge | Must be labeled; cannot be Production Ready as “real finding” |
| Insufficient evidence | Pass B2 only if framed as honesty |
| WA provider-gated | Ops disclosure required even if UI looks complete |
| Settings screenshots | Automatic fail A1/B1 for Widget/WA journey IDs |
