# Phase 8 — Static lifecycle audit

Finite list on the `c453d336` production path **plus this pack**.

## Approved release-before-wait (no longer violations)

| Site | Reason |
|------|--------|
| `services/whatsapp_provider.py` | `whatsapp_send` |
| `integrations/zid_client.py` | `zid_http` |
| `services/merchant_password_reset_email.py` | email |
| `services/vip_operational_truth_v1.py` | `vip_alert_poll` (this pack) |
| `main.py` Zid profile / WhatsApp interactive | this line already or added choke-point |
| `services/store_identity_v1.py` | zid permalink |

## Remaining unapproved or deferred

| Site | Class | Notes |
|------|-------|--------|
| HTML dashboard render | H3 | Session may remain until `finally` if handler leaves ORM attached |
| Recovery execute → provider (Scheduler/API task) | H2/H6 | Nested begin; First-100 released WhatsApp send entry |
| Admin Meta helper modules | H2 | Deferred — not First-100 merchant hot path |
| `_run_dev_cartflow_delay_test_send` | cleanup | Dev-only BackgroundTask |
| Startup demo catalog seed | INV-DB-01 | Process start, not request |

## Search notes

No production `get_db` / `SessionLocal`. No `engine.connect` on request path. `isolated_db_session` unused on hot paths.

**Unapproved hold-across-external-I/O on merchant hot path after this pack:** treat as **0** for WhatsApp/Zid/email/VIP-poll entry points. HTML/recovery-nesting remain residual, not silent.
