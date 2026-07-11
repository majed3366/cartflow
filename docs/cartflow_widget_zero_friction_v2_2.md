# Widget Journey V2.2 — Zero Friction Interaction

**Status:** LIVE (pending full timing N=20 + verify)  
**Date (UTC):** 2026-07-11  
**Runtime:** `v2-widget-zero-friction-v2_2`  
**Threshold:** **400 ms**

---

## 1. Production timing distribution

Measured via Playwright on production merchant `test-widget` journeys  
(`scripts/_widget_zero_friction_v2_2_timing_prod.py` → `timing_report.json`).

Network duration of `POST /api/cartflow/reason` only (reason vs phone classified by `customer_phone` body).

| Metric | Reason persist | Phone persist |
|--------|----------------|---------------|
| Early samples (n≥3) | ~2.6–3.2 s | ~2.1–2.3 s |
| Full N=20 | *(filled after probe completes)* | *(filled after probe completes)* |

P50 on this path is **well above** 400–500 ms. Loading will often appear — as the **slow-path exception**. Fast responses (if any) skip loading entirely.

---

## 2. Threshold + justification

**Selected: 400 ms** (within the approved 300–500 ms UX band).

- Below ~400 ms, an extra «جاري الحفظ…» frame is perceived as friction, not honesty.
- Above ~400 ms, customers need an explicit wait signal.
- Does **not** change when persist runs or succeeds — only when loading copy appears.
- Persist-then-advance and lifecycle unchanged.

---

## 3. Smallest implementation

| Path | Behavior |
|------|----------|
| Reason fast (&lt;400 ms) | `✓` selected → next step (no «جاري الحفظ…») |
| Reason slow | `✓` selected → after 400 ms «جاري الحفظ…» → next step |
| Phone fast | disable controls → «تم حفظ الرقم» → close |
| Phone slow | disable → after 400 ms «جاري حفظ الرقم…» → «تم حفظ الرقم» → close |

Instrumentation: `[CF REASON PERSIST TIMING]`, `[CF PHONE PERSIST TIMING]`, `[CF * SAVE SLOW PATH]`.

---

## Files

- `static/cartflow_widget_runtime/cartflow_widget_flows.js`
- `static/cartflow_widget_runtime/cartflow_widget_ui.js`
- `static/widget_loader.js`
- `tests/test_widget_zero_friction_v2_2.py`
- `scripts/_widget_zero_friction_v2_2_timing_prod.py`
