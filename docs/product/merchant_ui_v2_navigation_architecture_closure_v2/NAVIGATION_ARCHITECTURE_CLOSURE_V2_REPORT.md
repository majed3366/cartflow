# Navigation Architecture Closure V2

**Status:** Evidence captured — **NO PASS / NO FREEZE**  
**Deploy SHA:** `8d3c5f1`  
**Marker:** `data-cf2-appbar="nav-closure-v2"`

## Correction

Removed section name pill (`الرئيسية` / `مساحة القرار`) from the closed mobile App Bar.

| Surface | Behavior |
|---------|----------|
| Closed App Bar | Account · CartFlow · Global menu only |
| Global drawer | Platform sections + account |
| Desktop sidebar | Independent section context |
| Mobile context | Quiet page-level `في هذا القسم` → Contextual Sheet |

## Probe highlights (Living Store)

| Check | Result |
|-------|--------|
| Mobile home closed — App Bar has `الرئيسية` pill | **false** |
| Mobile workspace closed — App Bar has `مساحة القرار` pill | **false** |
| Context trigger inside App Bar | **false** |
| Page chrome `في هذا القسم` visible on mobile | **true** |
| Context sheet Home items | `نظرة عامة` |
| Context sheet Workspace items | `ما يحتاج قرارك` |
| Global drawer has ctx items | **false** |

Home / Workspace compositions untouched.
