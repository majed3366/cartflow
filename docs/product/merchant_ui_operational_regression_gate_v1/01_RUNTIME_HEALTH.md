# Gate 1 — Runtime Health

**Deploy:** `d1662e1`  
**Mode:** Living Store browser sequence (read-only)

## Findings

| Check | Result |
|-------|--------|
| Uncaught JS `pageerror` | **0** |
| Merchant UI V2 exceptions | **None observed** |
| Repeated render loops | **Not observed** |
| Duplicate nav handlers | `data-cf2-nav-bound` guard; bound count **6 → 6** across sequence |
| Runaway timers | **No `setInterval` in V2 app/home/workspace** |
| Drawer/ctx listener amplification | Bind once on `DOMContentLoaded` |
| Navigation recursion | Hash change → single `loadSection`; no stack growth observed |
| Lazy-load init failure | Home + Workspace paint completed |
| Shell init collision | Single `shell-integration-v1` chrome |

## Console

One network console error (not a Merchant UI exception):

- `GET/POST https://smartreplyai.net/api/landing/event` → **400** during boot on `/`

No `pageerror`. Artifact: `runtime_console_capture.json`.

## Verdict for Gate 1

**PASS with minor unrelated finding** (landing event 400 outside Merchant UI V2).
