# Release-before-wait

Law: read truth → release → external/non-DB work → reacquire only if persist is required.

## Violations found (before)

- `services/whatsapp_provider.py` send path (Meta/Twilio HTTP)
- `integrations/zid_client.py` all `requests.get/post`
- `services/merchant_password_reset_email.py` Resend HTTP after commit, session still scoped
- Admin Meta helper modules (lower frequency; same pattern)

## Correct exemplar (already present)

`recovery_delay_dispatcher.py` calls `release_db_before_async_wait()` before sleep.

## Remediation

Reusable `release_before_external_wait()` at the choke points:

- WhatsApp send entry
- Zid HTTP wrappers `_zid_get` / `_zid_post`
- Password-reset email send

Admin Meta modules remain deferred (not First-100 merchant hot path).
