# Mobile Context Navigation Architecture Correction V3

**Status:** Evidence captured — **NO PASS / NO FREEZE**  
**Deploy SHA:** `aa4c5c0818c4a828a0cde2e7017b879310756d14`  
**Marker:** `data-cf2-appbar="nav-ctx-chrome-v3"`

## Correction

Removed the content-flow floating/page-level `في هذا القسم` button entirely.

| Layer | Behavior |
|-------|----------|
| App Bar (mobile closed) | Account · CartFlow · Global menu only — no section pills |
| Page chrome (mobile) | Frame affordance under App Bar: kicker `تنقل القسم` + active contextual item → Contextual Sheet |
| Content stage | Starts with page title/question — no nav control row above title |
| Contextual Sheet | Area-only items (Home: نظرة عامة; Workspace: ما يحتاج قرارك) |
| Global Drawer | Platform sections + account only — no page-local items |
| Desktop | Upbar + contextual sidebar + stage unchanged |

## Probe highlights (Living Store)

| Check | Result |
|-------|--------|
| Marker live | `nav-ctx-chrome-v3` |
| `#cf2-section-chrome` present | **false** |
| Trigger inside page content / stage | **false** |
| Trigger in `#cf2-page-chrome` frame | **true** |
| Mobile App Bar has `الرئيسية` / `مساحة القرار` pill | **false** |
| Stage floating `في هذا القسم` button | **false** |
| Context sheet Home items | `نظرة عامة` |
| Context sheet Workspace items | `ما يحتاج قرارك` |
| Global drawer has ctx items | **false** |
| Desktop sidebar visible Home/Workspace | **true** |

## Screenshots

1. `01_desktop_home.png`
2. `02_desktop_workspace.png`
3. `03_mobile_home_closed.png`
4. `04_mobile_home_context_open.png`
5. `05_mobile_workspace_closed.png`
6. `06_mobile_workspace_context_open.png`
7. `07_mobile_global_drawer.png`

Home / Workspace visual compositions and APIs untouched.
