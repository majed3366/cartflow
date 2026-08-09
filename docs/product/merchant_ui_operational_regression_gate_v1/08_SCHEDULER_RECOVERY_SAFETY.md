# Gate 8 — Scheduler / Recovery Safety

## Evidence

| Concern | Finding |
|---------|---------|
| Scheduler process | Not invoked by V2 UI |
| Pending/due schedules | No schedule APIs in V2 fetch set |
| Outbound recovery | **No WhatsApp / outbound calls** from Merchant UI V2 |
| Inbound reply state | Untouched by presentation layer |
| Recent UI commits vs `services/` | Presentation-only (`static/`, `templates/merchant_app_v2.html`) |

No real outbound messages sent during this gate.
