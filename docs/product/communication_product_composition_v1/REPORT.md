# Communication — Product Composition V1

**Date (UTC):** 2026-08-28  
**Status:** Composed inside Merchant UI V2 PageStage. Not a V1 visual copy. Not a generic inbox.

## What shipped

- `#cf2-comms-root` answers: ماذا حدث في التواصل مع العملاء، وما الذي يحتاج متابعتي الآن؟
- Compact orientation → status list → history detail.
- Desktop master-detail. Mobile list → detail → back.
- Truth: `GET /api/dashboard/messages` + `/followups` + `/summary`.
- يحتاج متابعتي = follow-up rows only.
- Carts handoff `#carts`. Settings link only when constrained.
- No WhatsApp CTA, no thread/inbox, no composer.

## Evidence

Local `verify_paint.html` (`127.0.0.1:8767`). Demo store: 0 messages, 0 follow-ups. Screenshots in `screenshots/`. Missing states omitted.

Probes: `production_probe.json`, `mobile_overflow_probe.json`.

## Deploy

`railway up --service smart-reply-ai` from the linked composition worktree (`authentic-motivation` / `production`) timed out twice on upload. Autodeploy was not enabled. Scheduler was not touched. Composition files are in the main repo and copied to that worktree for a retry.

Do not declare PASS. Await real-device visual review.

---

CANONICAL QUESTION:
ماذا حدث في التواصل مع العملاء، وما الذي يحتاج متابعتي الآن؟

STATUS LIST:
COMPOSED — event/status feed (empty locally; no fabricated rows)

DETAIL/HISTORY:
COMPOSED — أحداث التواصل (not chat bubbles)

NEEDS_MERCHANT_RESPONSE:
CONTRACT IN CODE — no live follow-up rows locally (omitted from screenshots)

AUTOMATED WAIT:
CONTRACT IN CODE — not classified as يحتاج متابعتي

CARTS HANDOFF:
`#carts` only — «هذه الحالة تحتاج متابعتك» / «افتح المتابعة في السلال»

SETTINGS OVERLAP:
ABSENT

GENERIC INBOX:
NO

PURCHASE TERMINAL:
PRESERVED — no recovery CTA after completed/purchased

MOBILE OPERABILITY:
LIST COMPOSED — detail/back not exercisable without a row; overflowX false at 390

OPERATIONAL REGRESSION:
NO

COMPOSITION VERDICT:
READY_FOR_VISUAL_REVIEW
