# Platform Identity Authority (INV-002 WP-1)

Permanent foundation for merchant identity resolution.

## Rules

- **Import from** `services.identity_authority` (public façade).
- **Do not** invent `store_slug` in Dashboard / Knowledge / Brief / Timeline.
- **Do not** put ResolveMQIC / membership / attach logic in `main.py`.
- **WP-1** has **no DB I/O** — callers supply membership + canonical stores.
- **HTTP middleware / consumer migration** = later WPs.

## Core flow

```text
ResolveIdentityInput (explicit, preloaded)
        ↓
resolve_mqic / resolve_and_bind
        ↓
MerchantQueryIdentityContext (MQIC, sealed, immutable)
        ↓
request scope (contextvars) — exactly once
```

## Constitutional guarantees

| ID | Rule |
|----|------|
| IA-1 | Provider ids are aliases only; surfaces see Canonical Identity |
| IA-2 | Exactly one resolve per request scope |
| IA-3 | MQIC immutable after bind |
| IA-4 | Only Authority seals / owns MQIC |

## Observability

`identity_diagnostics()` — resolution provenance, authority source, context metadata, violation counters. Not merchant chrome.
