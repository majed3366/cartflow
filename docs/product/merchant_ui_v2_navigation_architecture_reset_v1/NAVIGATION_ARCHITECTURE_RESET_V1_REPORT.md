# Merchant Navigation Architecture Reset V1

**Status:** Evidence captured — **NO PASS / NO FREEZE**  
**Deploy SHA:** `88286359870065012eb4ad71766eda849492ee7e`  
**Marker:** `data-cf2-appbar="nav-reset-v1"`

## Architecture

Exactly **two** levels from **one** registry (`NAV.global` + `NAV.contextual` in `merchant_ui_v2_app.js`):

| Level | Desktop | Mobile |
|-------|---------|--------|
| 1 GLOBAL | Upbar | App Bar + Global Drawer |
| 2 CONTEXTUAL | `#cf2-ctx` sidebar column | Same `#cf2-ctx` as overlay sidebar drawer |

Removed completely: V3 page-chrome, `تنقل القسم`, separate `#cf2-ctx-sheet`, content-flow triggers, App Bar section pills.

Home contextual: `نظرة عامة` only (no invented `الملخص` — not a live V2 composition).  
Workspace contextual: `ما يحتاج قرارك` only.

## Screenshots + layer map

| # | File | GLOBAL | CONTEXTUAL | CONTENT |
|---|------|--------|------------|---------|
| 1 | `01_desktop_home.png` | Upbar sections | Sidebar `الرئيسية` → نظرة عامة | Frozen Home |
| 2 | `02_desktop_workspace.png` | Upbar sections | Sidebar `مساحة القرار` → ما يحتاج قرارك | Workspace |
| 3 | `03_mobile_home_closed.png` | App Bar only | Closed | Home under App Bar |
| 4 | `04_mobile_home_contextual_sidebar.png` | App Bar | Same `#cf2-ctx` drawer | Home dimmed |
| 5 | `05_mobile_workspace_closed.png` | App Bar only | Closed | Workspace under App Bar |
| 6 | `06_mobile_workspace_contextual_sidebar.png` | App Bar | Same `#cf2-ctx` drawer | Workspace dimmed |
| 7 | `07_mobile_home_global_drawer.png` | Global Drawer | Not open | Home dimmed |
| 8 | `08_mobile_workspace_global_drawer.png` | Global Drawer | Not open | Workspace dimmed |

## Probe highlights

- `pageChromePresent` / `ctxSheetPresent` / `hasTanqulQism` → **false**
- Mobile closed App Bar has no `الرئيسية` / `مساحة القرار` pills
- Global drawer has **no** contextual items
- Home / Workspace compositions unchanged (nav shell only)
