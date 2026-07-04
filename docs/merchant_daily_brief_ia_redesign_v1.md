# CartFlow Merchant Daily Brief IA Redesign V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — information architecture + loading  
**Prior:** [`merchant_daily_brief_ux_redesign_v1.md`](merchant_daily_brief_ux_redesign_v1.md)

---

## Problems addressed

| # | Problem | Fix |
|---|---------|-----|
| 1 | «الأولوية الآن» + generic class tag (متابعة/ملاحظة) weakened urgency | **Action/problem headline first**; decision class moved to metadata line |
| 2 | Brief loaded after page via separate fetch | **Embedded in `/api/dashboard/summary`**; renders with dashboard bootstrap |
| 3 | Vertical report required scrolling/reading | **Hero + compact grid queue** (2-col desktop, 1-col mobile) |

---

## New information hierarchy

### Section 1 — Greeting / Today / Attention count
Rendered in HTML shell on first paint; updated when summary arrives.

### Section 2 — Primary hero (one item)
- Large headline = **required action or problem** (`action_ar` → `what_ar`)
- Short why (one line)
- Metadata: decision class · confidence · evidence (**class last**)

### Section 3 — Remaining queue
- Desktop: **2-column compact card grid**
- Mobile: **single column stack**
- Each card: action/problem headline + class/confidence meta

---

## Loading strategy

1. **Server HTML shell** — greeting + date visible on first paint (`merchant_app.html`)
2. **`merchant_daily_brief_v1` on summary payload** — `_api_json_dashboard_summary` attaches existing composer output
3. **`applySummary`** — calls `maApplyDailyBriefPayload` with summary brief (same bootstrap as KPIs)
4. **Fallback** — `/api/dashboard/daily-brief` if summary omits brief (snapshot/degraded paths)

No delayed «جاري التحميل» flash after page open.

---

## Why this is faster to scan (5–10 seconds)

| Scan target | Where merchant sees it |
|-------------|------------------------|
| How many things? | Attention count under greeting |
| Highest priority? | Hero headline (action/problem, large) |
| What remains? | Grid cards — one line each |
| Decision class? | Small meta line — not hero title |
| Confidence / evidence? | Hero meta — tertiary |

---

## Foundation alignment

| Principle | IA support |
|-----------|------------|
| DBP-6 Presentation only | Same `merchant_decisions_v1` payload — IA reorder only |
| DBP-8 Attention protected | Hero + grid; no OIA label repetition |
| PV-18 what/why/action | Action-first headline; why one line |
| Opening experience | Summary bootstrap + instant shell |

---

## Files changed

| File | Role |
|------|------|
| `static/merchant_daily_brief.js` | IA renderer + instant shell |
| `static/merchant_app.css` | Hero + grid layout |
| `templates/merchant_app.html` | First-paint greeting shell |
| `static/merchant_dashboard_lazy.js` | Apply brief from summary |
| `main.py` | Attach `merchant_daily_brief_v1` to summary |

**Unchanged:** `services/merchant_daily_brief_v1.py` composer, Decision Layer, Truth, Proof, Governance.

---

## Screenshots

Regenerate: `python scripts/_daily_brief_ia_redesign_v1_screenshots.py`

Output: `scripts/_daily_brief_ia_redesign_v1_out/`

---

*End of Merchant Daily Brief IA Redesign V1.*
