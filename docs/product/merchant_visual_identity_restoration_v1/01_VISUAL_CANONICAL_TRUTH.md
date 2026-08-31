# 01 — Visual canonical truth

## Figma / visual references

| Source | Role |
|--------|------|
| Merchant Visual System V1 (P1–P16) | Binding merchant visual law |
| `static/merchant_ui_v2_language.css` + `merchant_ui_v2_language.js` | Runtime primitive layer |
| Figma `1NnI69Jd7BhfnNdehmBq0Q` Foundations | Token / DS supporting reference |
| Figma `0YWwVn1cKxH45M6mLZfGJE` Visual Asset System | Marketing asset library — **not** Merchant page SoT |
| Historical V1 “Figma 25–34” notes | Apply to rollback `merchant_app.html` only |

## Production primitives (required selectors)

P1 `.cf2-home__board` / `.cf2-dobj--primary` · P2 start-edge · P3 `.cf2-home__mark` / `.cf2-ws__mark` · P4/P9 detail surfaces · P5 attention rail · P6 selected row · P7 canvas · P8 Settings inner card · P10 empty truth block · P11 state marker · P12 `.cf2-co-row` · P13 `.cf2-evfield` · P14 `.cf2-mtrace` / `.cf2-route` · P15 `.cf2-dmass` · P16 `.cf2-home__kicker` + `.cf2-home__lane`

## Page responsibilities

| Surface | Responsibility | Required grammar | Forbidden |
|---------|----------------|------------------|-----------|
| Home | Executive truth now | Scene kicker, CO family, gravity, density, momentum if ≥2 real lanes | Card gallery, HES equal cards, two-column LKG |
| Workspace | Decision now + why | Decision Object, CO row, living route, Decision Mass | Home teaser, inbox |
| Carts | Operational queue | Filters, rows, inspect, solid empty | Dashed shell, executive board |
| Communication | Status / history | Filters, unboxed rows, related detail | Inbox / chat / twin panes |
| Settings | Config overview → detail | Question, rows, one detail edge | Card wall, form dump |

## Canonical shell

UtilityRow → GlobalUpbar → ContextualSidebar → PageStage. Historical App Bar / `cf-rail` is rollback-only.
