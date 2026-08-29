# 08 — Operational Regression

| Gate | Result |
|------|--------|
| `#communication` canonical | PASS — V2 `go("comms")` writes `#communication` |
| `#messages` alias-only | PASS — `currentHash` maps messages → comms |
| Data loads | PASS — one `Promise.all` of messages + followups + summary |
| Send/delivery facts | PASS — message rows only |
| Latest inbound | PASS — follow-up inbound / `customer_reply_ar` |
| Human-response trigger | PASS — follow-up rows only |
| Automated wait not human | PASS |
| No-phone not human | PASS |
| Carts execution separate | PASS — `#carts` handoff only; no WA CTA |
| Settings separate | PASS — `#settings` when blocked |
| Purchase terminal | PASS — no recovery CTA |
| No duplicate fetch loop | PASS — `fetchGen` guard |
| Shell / Home / Workspace / Carts | PASS — files untouched except Communication wiring in app/template |
| No horizontal overflow | PASS — desktop 1280 and mobile 390 |

Tests: `tests/test_communication_product_composition_v1.py` (10) + Gate 4 + V2 template + Carts composition = 34 passed.
