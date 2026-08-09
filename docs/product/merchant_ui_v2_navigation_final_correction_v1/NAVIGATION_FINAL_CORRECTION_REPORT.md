# Merchant Navigation Architecture — Final Correction V1

**Status:** Implemented on Living Store — awaiting manual visual acceptance  
**Do NOT declare PASS. Do NOT freeze navigation.**  
**Deploy SHA:** `cad4518`  
**Marker:** `data-cf2-appbar="nav-final-v1"`  

---

## Rejection fixed

Removed the wrong **horizontal contextual bar** (`#cf2-ctx-mobile` / pill row under the App Bar).

Deleted its DOM, CSS, and paint path — not hidden, not overridden.

---

## Required architecture (now)

| Region | Implementation |
|--------|----------------|
| **1. Global Upbar** | `.cf2-appbar` — primary destinations + identity/account/menu |
| **2. Contextual Sidebar** | Desktop: real `#cf2-ctx` column. Mobile: dedicated `#cf2-ctx-sheet` opened from quiet `#cf2-ctx-trigger` |
| **3. Page content** | `.cf2-stage` — Home / Workspace compositions untouched |

### Mobile closed
Global App Bar only (no under-bar contextual row). Quiet trigger opens the **contextual sheet**.

### Mobile contextual sheet
Contains **only** current-area items (e.g. Home → نظرة عامة). Separate from global drawer.

### Global drawer
Platform sections + account only. **No** نظرة عامة / ملخص / page subsections.

---

## Contextual items (real V2 only)

| Area | Items |
|------|--------|
| الرئيسية | نظرة عامة |
| مساحة القرار | ما يحتاج قرارك |

`الملخص` not added — not a live V2 composition.

---

## Living Store screenshots

| # | File |
|---|------|
| 1 | `01_desktop_home.png` |
| 2 | `02_desktop_workspace.png` |
| 3 | `03_mobile_home_closed.png` |
| 4 | `04_mobile_home_context_open.png` |
| 5 | `05_mobile_global_drawer.png` |
| 6 | `06_mobile_workspace_closed.png` |
| 7 | `07_mobile_workspace_context_open.png` |
| 8 | `08_mobile_page_scroll.png` |

Probe gate `gate_no_horizontal_ctx`: **true** (`horizontalCtxStripExists` false; drawer has no overview items). Supporting only — not visual PASS.

---

## STOP

Home / Workspace composition unchanged. Products / Carts / Communication / Settings not started.  
**Await manual visual acceptance.**
