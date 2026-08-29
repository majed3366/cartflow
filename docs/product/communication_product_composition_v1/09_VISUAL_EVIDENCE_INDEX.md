# 09 — Visual Evidence Index

Source: local `verify_paint.html` on `127.0.0.1:8767`. Demo store has **0** send-log rows and **0** follow-up rows. Missing states were **not fabricated**.

| Required | File | Truth |
|----------|------|--------|
| 1 Desktop list | `screenshots/01_desktop_list.png` | Calm empty list + orientation |
| 2 Selected item | `screenshots/02_desktop_selected.png` | Same empty truth; detail empty prompt |
| 3 Merchant-response | — | **Omitted** — no `needs_merchant_followup` rows |
| 4 Automated/waiting | `screenshots/04_desktop_needs_empty.png` | Needs filter empty (valid calm) |
| 5 Detail/history | `screenshots/05_desktop_detail_history.png` | History pane empty-select copy |
| 6 Mobile list | `screenshots/06_mobile_list.png` | List + orientation |
| 7 Mobile needs item | — | **Omitted** |
| 8 Mobile automated | — | **Omitted** |
| 9 Mobile detail | — | **Omitted** — no selectable row |
| 10 Back to list | — | **Omitted** — no detail open |
| 11 Calm/no-action | `screenshots/11_mobile_calm_state.png` | No-action empty |

Probes: `production_probe.json`, `mobile_overflow_probe.json`.
