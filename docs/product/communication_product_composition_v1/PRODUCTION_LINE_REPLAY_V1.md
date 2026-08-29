# Communication — Production-Line Replay V1

**Date (UTC):** 2026-08-28  
**Base:** `c6a912f` (Living Store production line)  
**Source of Communication hunks:** `d08859a`  
**Deploy:** none

## Why replay

`d08859a` is Communication-complete but diverges from Living Store. It lacks `railway.api.toml` / `cartflow_api.py` and starts `main:app`. It must not be deployed.

## Conflict resolution

Mechanical `git checkout d08859a --` was used only for new Communication files (JS/CSS/tests/pack). Shared files were patched by hunk.

| File | d08859a also wanted | Kept from `c6a912f` | Why |
|------|---------------------|---------------------|-----|
| `templates/merchant_app_v2.html` | Carts CSS/JS cache-bust `cartscomp2` / `cartsempty1`→`cartscomp2` | `cartsempty1` + `cartscomp1` | Carts production cache line; not Communication |
| `tests/test_merchant_ui_v2.py` | Drop `merchant_ui_v2_carts.js` assert; add carts question/root asserts | Keep carts.js assert; add **comms** asserts only | Carts tests already valid on this base |
| `docs/SYSTEM_SUMMARY.md` | Full §2.2 / §10 drift from the other branch | Isolated Communication row + replay/composition changelog | Preserve Needs-You / API contract history |
| `railway.api.toml`, `cartflow_api.py`, `Dockerfile`, `Procfile`, `railway.toml` | Older `main:app` / missing API split | Unchanged | Production API contract |

No Carts Needs-You, Scheduler, or Railway variable files were replayed.

## Result

Communication V2 (`#cf2-comms-root`) sits on the current production API line. `#communication` canonical; `#messages` alias-only.
