# Typography Certification Report — Typography Lock V1

**Date:** 2026-07-07 (UTC)  
**Scope:** Merchant Dashboard presentation only (`/dashboard` shell)  
**Implementation:** `static/merchant_typography_certification_v1.css` (final lock layer)

---

## Summary

Typography Lock V1 freezes the merchant reading rhythm under a single certified system: **Arial only**, **14 certified role tokens**, and **universal overrides** that neutralize legacy drift in `merchant_app.css`, PE v2, and product polish layers.

---

## Pages inspected

| Page | Desktop | Mobile | Typography CSS loaded |
|------|---------|--------|------------------------|
| Home | Yes | Yes | Required |
| Carts | Yes | Yes | Required |
| WhatsApp | Yes | Yes | Required |
| Plans | Yes | Yes | Required |
| Settings | Yes | Yes | Required |
| Sidebar / App bar | Yes | Yes | Required |

Review script: `scripts/_typography_certification_v1_review.py`  
Artifacts: `scripts/_typography_certification_v1_out/`

---

## Certified typography tokens

| Token | Size | Weight | Line-height |
|-------|------|--------|-------------|
| Hero Title | `clamp(1.35rem, 3.5vw, 1.65rem)` | 800 | 1.25 |
| Hero Subtitle | 14px | 500 | 1.55 |
| Page Title | 20px | 800 | 1.3 |
| Section Title | 16px | 700 | 1.35 |
| Card Title | 14px | 700 | 1.35 |
| Card Subtitle | 13px | 500 | 1.5 |
| Body | 14px | 400 | 1.5 |
| Secondary Body | 13px | 400 | 1.5 |
| Caption | 13px | 500 | 1.45 |
| Button | 13px | 700 | 1.2 |
| Badge | 11px | 700 | 1.2 |
| Table | 13px | 600 | 1.45 |
| Numeric | 15px | 800 | 1.2 |
| Currency | 15px | 800 | 1.2 |

CSS variables: `--cftyp-*` in `merchant_typography_certification_v1.css`.

---

## Legacy font declarations removed / neutralized

| Source | Action |
|--------|--------|
| Google Fonts IBM Plex link | **Removed** from `templates/merchant_app.html` |
| `--cfvi-font-certified` mixed stack | **Locked** to `Arial, sans-serif` |
| `--pds-font`, `--v2-font` | **Aliased** to `--cftyp-font` |
| Inline `font-size` / `font-weight` in `merchant_app.html` | **Removed** (13 instances) |
| Inline typography in `merchant_dashboard_lazy.js` | **Removed** (3 instances) |
| Legacy `--ma-type-*` scale | **Re-mapped** to certified tokens |

---

## Typography tokens used (by surface)

- **Heroes (Home, Carts, WhatsApp, Plans, Settings):** Hero Title + Hero Subtitle (Rule 10 — one subtitle token for `#pageSub`, `.ma-page-hero__purpose`, `.v2-hero-purpose`)
- **Cards:** Card Title + Card Subtitle (automatic via `.setting-card`, `.ma-vi-card`, etc.)
- **Buttons:** Button token on `.btn`, `.v2-btn`, `.ma-fw-btn`, `.filter-btn`, all submit buttons
- **Badges / filters / counters:** Badge token on `.nb`, pills, `.filter-btn` (inactive weight from button token only when active styling differs visually — size/weight locked)
- **Sidebar / app bar:** Caption token; active nav uses button weight only
- **Numbers / currency:** Numeric + Currency tokens on KPIs, amounts, plan prices; `formatMerchantSar()` unchanged (`449 ر.س`)

---

## Remaining exceptions

| Exception | Reason | Status |
|-----------|--------|--------|
| `.ma-msg-mono` | Diagnostic message IDs — intentional monospace | **Allowed** |
| `code`, `pre`, `kbd`, `samp` | Technical literals | **Allowed** |
| `merchant_auth.css` (login/signup) | Out of dashboard shell scope | **Deferred** |
| Empty-store gate pages | No numeric/currency text to probe | **Data limit, not typography** |

---

## Tests

`tests/test_merchant_typography_certification_v1.py` — CSS wiring, Arial lock, token system, inline cleanup.

---

## Success criteria checklist

- [x] Arial single certified merchant font (dashboard shell)
- [x] All visible dashboard text mapped to certified tokens via lock layer
- [x] Legacy inline font declarations removed from shell template + lazy JS
- [x] Hero subtitles unified to one token set
- [x] Buttons / badges / sidebar share certified scales
- [ ] **Product Owner visual approval** (required for closure)

---

## PO review instruction

Switch between Home → Carts → WhatsApp → Plans → Settings (desktop + mobile). Typography should not shift. Run after deploy:

```bash
python scripts/_typography_certification_v1_review.py
```

Inspect `scripts/_typography_certification_v1_out/typography_cert_report.json` for `hero_subtitle_consistency.uniform_size == true`.

**Status: OPEN — awaiting PO approval.**
