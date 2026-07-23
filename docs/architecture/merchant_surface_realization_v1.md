# Merchant Surface Realization V1 (MSR)

**Status:** UI realization of closed foundations  
**Scope:** Home · Decision Workspace · Carts · Communication  
**Non-scope:** No new platform capabilities; no changes to Truth / Evidence / CIS / Knowledge / Guidance / OT / SCF / Time Authority generators.

## Mission

Reveal existing MEIF packages so a first-time merchant understands platform value.

## Consumer

| File | Role |
|------|------|
| `static/merchant_experience_integration_v1.js` | Renders MEIF `pages.*` with question-led hierarchy |
| `templates/merchant_app.html` | Mount `#meif-carts-focus-root` + MSR hierarchy CSS |

## Surfaces

| Page | Merchant questions answered |
|------|----------------------------|
| Home | Health today · attention first · what appeared · ops health · watching · know before details |
| Decision | Why · evidence · confidence · suggested step (from OT explainability / package fields) |
| Carts | What matters · why · expected action (composition_items + truth banner) |
| Communication | What happened · waiting · intervention need (state, not event dump) |

## Explicitly unchanged

Product Performance foundations remain production-closed. MSR only changes presentation of packages already attached to `/api/dashboard/summary`.
