# Widget Journey V2.1 — Interaction Rhythm Polish

**Status:** REPAIR APPLIED — production verify required  
**Date (UTC):** 2026-07-11  
**Runtime:** `v2-widget-interaction-rhythm-v2_1`

---

## Goal

Click → immediate acknowledgement → background work → confirmation.  
No silence between click and feedback.

No business / persistence / lifecycle changes — perceived responsiveness only.

---

## Reason selection

| Before V2.1 | After |
|-------------|--------|
| Outline / border was the main selected signal | Button label becomes `✓ {reason}` |
| Footer «جاري الحفظ…» only | Status line + footer: «تم الاختيار — جاري الحفظ…» |
| | `data-cf-reason-transition=saving` |

Ack still runs synchronously before bridge / `POST /reason`.

---

## Phone save

| Issue | Fix |
|-------|-----|
| Button said «جاري الحفظ…» | Button + footer: «جاري حفظ الرقم…» on click |
| `onSave` called `hideFooterMessage()` → **silence during persist** | Keep ack visible until success |
| Success copy was long | «تم حفظ الرقم» then close (~900 ms) |

Persistence path (`postReasonMerged`) unchanged.

---

## Files

- `static/cartflow_widget_runtime/cartflow_widget_flows.js`
- `static/cartflow_widget_runtime/cartflow_widget_ui.js`
- `static/widget_loader.js`
- `tests/test_widget_interaction_rhythm_v2_1.py`
