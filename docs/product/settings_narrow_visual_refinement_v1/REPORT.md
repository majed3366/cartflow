# Settings Narrow Visual Refinement V1

STATUS: LOCAL CANDIDATE ONLY. NOT DEPLOYED.

## Verdict fields

BASE SHA:
`a2cf3df88d74224775482c69d84116e9edb845a8`

NEW SHA:
(this commit on `candidate/settings-narrow-visual-refinement-v1`; recorded in the commit that contains this file)

DIRECT PARENT:
`a2cf3df88d74224775482c69d84116e9edb845a8`

OVERVIEW STATUS COMPLETENESS:
FIXED

STORE ACTION TRUTH:
FIXED

COMMUNICATION CTA HIERARCHY:
FIXED

MOBILE QUESTION REPETITION:
FIXED

DUAL TEAL STATE:
FIXED

SETTINGS TAB DISCOVERABILITY:
FIXED

EMPTY DETAIL:
IMPROVED

QUEUEPOOL REMEDIATION PRESERVED:
YES

FIRST-LOAD REQUEST PATTERN:
`GET /api/merchant/subscription` (existing `merchant_subscription.js` DOMContentLoaded bind) → sequential `GET /api/merchant/store-connection` → `GET /api/recovery-settings`. No `Promise.all`. No startup `maInit*` fan-out. No duplicate recovery-settings read on first overview. Detail remains lazy / same-page cache. Settings JS cache token remains `qpool1`.

DESKTOP:
PASS

MOBILE:
PASS

OPERATIONAL REGRESSION:
NO

UNRELATED CHANGES:
NO

SAFE FOR PRODUCTION RECONCILIATION:
YES

SAFE FOR SETTINGS PROVISIONAL ACCEPTANCE AFTER LIVE REVIEW:
YES

STOP.

## Scope

Authorized narrow visual refinement only. Composition, ownership, operational semantics, QueuePool remediation, and Settings IA were not reopened.

Parent / production base: `a2cf3df`. One child commit on `candidate/settings-narrow-visual-refinement-v1`.

## Finding 1 — Overview status completeness

Overview already classified READY / NEEDS_SETUP / PARTIAL. Store now also surfaces the truthful companion chips that already existed in `STATE_AR`:

- `READ_ONLY · الباقة` (subscription remains read-only)
- `UNAVAILABLE · سلة` (Salla remains unavailable)

Primary area state is still one chip. READ_ONLY / UNAVAILABLE use the existing muted pill treatment (not actionable, not broken). PARTIAL keeps its distinct quiet chip (not failure). `is-needs` no longer paints a second teal border.

Evidence: `screenshots/desktop_overview.png`, `screenshots/mobile_overview.png`, `capture_meta.json`.

## Finding 2 — Disconnected store action truth

`.ma-sc-actions { display: flex }` was overriding `[hidden]`, so reconnect/disconnect stayed visually present when disconnected.

Fix is presentation-only: `[hidden] { display: none !important }` inside Settings. Existing `applyStatus` gating is unchanged.

Disconnected store now shows only the truthful Zid connect control. Connected-only reconnect/disconnect stay hidden. No Salla/Shopify connect path invented.

Evidence: `screenshots/desktop_store.png`, `screenshots/mobile_store.png`. Measured: `storeConnectedHidden=true`, `storeConnectedDisplay=none`, `storeConnectDisplay=flex`.

## Finding 3 — Communication CTA hierarchy

WhatsApp path buttons were both `ma-fw-save` (equal navy).

Current path remains the single dominant navy control (`ma-fw-save is-current`, disabled). The other path is `is-secondary` (outline). Destinations and save/handoff semantics unchanged. Templates remain the existing underlined handoff.

Evidence: `screenshots/desktop_communication.png`, `screenshots/mobile_communication.png`.

## Finding 4 — Mobile question repetition

Overview keeps the canonical question.

On mobile `.is-detail-open`, the question, hint, and needs line are hidden. Back label is compact area context: `رجوع · {area title}`. No new mobile header. Merchant Shell untouched.

Evidence: mobile store/communication `questionDisplay=none`, `backText` = `رجوع · المتجر` / `رجوع · التواصل`.

## Finding 5 — Dual teal after Back

Cause was `is-needs` sharing the selection teal, plus leftover focus after Back.

- `is-needs` no longer uses teal.
- `:focus` outline removed; `:focus-visible` keeps a navy accessibility ring.
- Back / close-detail blurs the active Settings control so selection and keyboard focus cannot both stay painted.

After Back: `tealSelected=0`, needs rows have `box-shadow: none`. One selected teal inset only while an area is open.

Evidence: `screenshots/mobile_after_back.png`.

## Finding 6 — Settings GlobalUpbar discoverability

No shell redesign. No extra Settings icon.

`paintGlobalNavigation` / `setActiveNav` now shift `#cf2-nav.scrollLeft` so the active destination is fully inside the existing horizontal scroller. No new nav pattern.

Evidence: `merchant_ui_v2_app.js` `revealActiveNavItem`; mobile 390px recapture.

## Empty detail

Dashed decorative empty shell removed. Desktop overview keeps the existing truthful line: `اختر منطقة لعرض حالتها وضبطها.` No invented filler.

## QueuePool safety

Unchanged:

- `LOAD_MODE = settings-queuepool-pressure-remediation-v1`
- sequential store-connection then one recovery-settings
- no `Promise.all` / `initExisting` / startup `maInit*`
- `__cfSettingsReadCache`
- schema-ensure memoization (untouched)
- dashboard script token `qpool1`

Local first-load watch: subscription bind + store-connection + recovery-settings.

## Tests

PASS (ENV=development):

- `tests/test_settings_narrow_visual_refinement_v1.py`
- `tests/test_settings_product_composition_v1.py`
- `tests/test_settings_queuepool_pressure_remediation_v1.py`
- `tests/test_merchant_ui_v2.py`

41 passed.

V1 HTML-on-V2 dashboard assertions in older merchant settings tests remain the known baseline (same class as on clean `a2cf3df` / `50cc5f9`). Not treated as this candidate.

## Stop

Do not deploy.
Do not begin Merchant Platform Visual Assimilation Review.
Do not expand beyond these findings.

Await live review of this child SHA before Settings Product Composition V1 provisional acceptance.
