# Widget Journey V2 — Interaction Reliability & Trust

**Status:** REPAIR APPLIED — sprint OPEN until human production feel is approved  
**Date (UTC):** 2026-07-11  
**Runtime:** `v2-widget-interaction-trust-v1`

---

## Root cause

| Stage | Before |
|-------|--------|
| Click | Event received |
| Visual acknowledgement | **Missing** — first paint change waited on bridge + `POST /reason` (~2.5 s) |
| Persist | Awaited (correct) |
| Transition | After persist (correct) |

Customers saw mute/disabled-looking buttons with no selected state and no “saving” signal → second clicks and lost trust.

**First stage over operational target (<100 ms ack):** **UI acknowledgement** — not polling, not bridge retries, not message semantics.

Phone optional save had the same gap: `onSave` fired with no busy label / lock until the network returned.

---

## Smallest repair

1. **Reason:** sync `acknowledgeReasonPick()` + `reason_save_in_flight` **before** bridge/POST — selected outline, siblings dimmed, footer «جاري الحفظ…». Persist-then-advance unchanged. Fail clears selection and shows retry error.
2. **Phone:** immediate «جاري الحفظ…» + disable save/skip; await promise; success «تم حفظ الرقم — سنتابع طلبك» then close (~900 ms); fail restores controls + clear error.
3. Shell exports `showFooterMessage` / `hideFooterMessage` for status.

No polling. No timeout increase. No extra retries. No wording-only change.

---

## Production evidence (2026-07-11)

- Deployed runtime: `v2-widget-interaction-trust-v1` (follow-up `v1b` = 900 ms success dwell).
- Five recorded journeys: `scripts/_widget_interaction_trust_v1_out/videos/journey_01.webm` … `journey_05.webm`.
- Console ack on all five: **1.9–3.8 ms** (`[CF REASON ACK]`).
- Phone path: `[CF PHONE SAVE ACK]` → `[CF PHONE SAVE ACK SUCCESS]` on all five.
- One reason POST per reason click (phone merge POST is a separate intentional save, not a duplicate reason click).
- Sprint remains **OPEN** until 20 human production journeys feel naturally responsive.

---

## Files

- `static/cartflow_widget_runtime/cartflow_widget_flows.js`
- `static/cartflow_widget_runtime/cartflow_widget_ui.js`
- `static/cartflow_widget_runtime/cartflow_widget_shell.js`
- `static/widget_loader.js`
- `tests/test_widget_interaction_trust_v1.py`
