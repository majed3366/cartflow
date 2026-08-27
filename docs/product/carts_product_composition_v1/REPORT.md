# Carts Product Composition V1 — Report

Status: composed inside Merchant UI V2 PageStage. Not a visual copy of V1.

## What shipped

- `#cf2-carts-root` operations workspace: compact orientation → filter chips → queue → detail.
- Desktop master-detail. Mobile queue → detail → back (`is-detail-open`).
- Same contracts: `GET /api/dashboard/normal-carts`, `cart_page_primary_action_v1`, attention labels, archive/reopen POSTs, proof-surface timeline.
- Gate 3 paint still off: no MI stories, MPL, publication banners, VIP threshold fields.
- Shell / Home / Workspace / Settings / Communication unchanged. `contextual.carts` remains `null`.

## Evidence

Local demo (`127.0.0.1:8765`), one waiting cart. Screenshots in `screenshots/`.

| Required | File | Truth |
|----------|------|--------|
| Desktop queue | `01_desktop_queue_actionable.png` | Waiting-dominant (needs_you=0). Not fabricated urgency. |
| Desktop detail | `02_desktop_selected_detail.png` | State + wait primary + demoted archive |
| Desktop waiting/quiet | `03_desktop_waiting_quiet.png` | Filter / quiet waiting |
| Desktop purchased | — | **Omitted** — no purchased truth locally |
| Mobile 5–11 | `05`–`11` | Queue, row, detail, primary, timeline, back, calm attention filter |

Probes: `production_probe.json`, `mobile_overflow_probe.json`.

## Regression (local)

Queue loads. Filters change the list (all shows 1; يحتاجني is calm empty). Select works. Primary key `wait` on the live row. Timeline from proof surface. Archive secondary only. Purchase suppression not exercisable (no purchased row). Attention labels unchanged (`بانتظار الإرسال`). No Workspace narratives. No VIP config. Shell/Home/Workspace intact. One fetch per `loadAndPaint`. No horizontal overflow.

## Living Store deploy

Attempted after local gates. If origin/Railway is unauthorized, evidence remains local and labeled. Do not declare PASS.

---

CANONICAL QUESTION:
ما السلال التي تحتاج انتباهي الآن، وما الإجراء التشغيلي المطلوب لكل سلة؟

QUEUE STATUS:
COMPOSED — local waiting row visible; actionable count 0 (truthful)

DETAIL STATUS:
COMPOSED — state → one primary → context → timeline

PRIMARY ACTION CONTRACT:
UNCHANGED (wait / contact_customer / follow_up_manually / review_cart / no_action_required / reopen; archive demoted)

ATTENTION SEMANTICS:
UNCHANGED (canonical labels only)

PURCHASE TERMINAL:
PRESERVED IN CODE — no local purchased row to show

WORKSPACE OVERLAP:
ABSENT

VIP CONFIG IN CARTS:
ABSENT

MOBILE OPERABILITY:
QUEUE → DETAIL → BACK; primary reachable; timeline in details; no overflowX

OPERATIONAL REGRESSION:
YES

COMPOSITION VERDICT:
READY_FOR_VISUAL_REVIEW
