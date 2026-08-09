# Merchant Navigation — Forensic Root Cause Audit V1

**Status:** READ-ONLY diagnostic complete. **NO IMPLEMENTATION. NO DEPLOY. NO PATCH.**  
**Date:** 2026-08-09  
**Production shell marker:** `data-cf2-appbar="nav-reset-v1"`  
**Pack:** `docs/product/merchant_navigation_forensic_audit_v1/`

---

## Pack index

| File | Audit |
|------|-------|
| [01_CURRENT_NAVIGATION_MAP.md](./01_CURRENT_NAVIGATION_MAP.md) | Live shell map |
| [02_DOM_OWNERSHIP.md](./02_DOM_OWNERSHIP.md) | DOM ownership matrix |
| [03_RESPONSIVE_BREAKPOINT_MAP.md](./03_RESPONSIVE_BREAKPOINT_MAP.md) | Media-query forensics |
| [04_JAVASCRIPT_NAVIGATION_MAP.md](./04_JAVASCRIPT_NAVIGATION_MAP.md) | JS ownership + dependency map |
| [05_LEGACY_COLLISION_REPORT.md](./05_LEGACY_COLLISION_REPORT.md) | ACTIVE/DEAD/HIDDEN/… inventory |
| [06_GIT_HISTORY_FINDINGS.md](./06_GIT_HISTORY_FINDINGS.md) | V1 ancestry + V2 birth of drawer-only Global |
| [07_ROOT_CAUSE.md](./07_ROOT_CAUSE.md) | Primary root cause |
| [08_TARGET_ARCHITECTURE_CONTRACT.md](./08_TARGET_ARCHITECTURE_CONTRACT.md) | Target invariants (no implementation) |

---

## Executive finding

Desktop V2 already matches the intended split: **Global in Upbar** (`.cf2-nav`) + **Contextual in Sidebar** (`#cf2-ctx`) + **Content** (`#cf2-stage`).

Mobile V2 does **not**. Below 1024px, CSS hides `.cf2-nav` and leaves platform sections reachable only via `#cf2-drawer` (hamburger). Contextual remains a separate overlay of the same `#cf2-ctx` node — that part is architecturally sound. The break is **Global ownership demotion on mobile**.

This was present from the first Merchant UI V2 commit (`4fb6604`) and kept through Navigation Architecture Reset V1 (`8828635`). It inherits the V1 ≤1023 “hamburger drawer for navigation” law from `merchant_frame_v1.css`.

---

## Audit 2 answers (Global source of truth)

1. **One canonical navigation model?** Semantically yes — `NAV` in `merchant_ui_v2_app.js`.  
2. **Separate desktop/mobile copies?** Yes — static HTML in `.cf2-nav` and `#cf2-drawer`.  
3. **Same list rendered into multiple containers?** Duplicated markup, not one renderer.  
4. **Moved between containers by JS?** No.  
5. **Mobile deliberately drawer-only?** Yes — CSS contract + comments.  
6. **Exact code that removes platform links from mobile Upbar:**

```css
/* static/merchant_ui_v2_frame.css @media (max-width: 1023px) */
body[data-cf-ui="v2"] .cf2-nav { display: none !important; }
```

---

## Hard gate compliance

| Action | Done? |
|--------|-------|
| Implement fix | NO |
| Deploy | NO |
| Modify Home / Workspace / Products / Carts / Comms / Settings pages | NO |
| Create V4/V5/V6 navigation | NO |
| Patch App Bar | NO |
| Forensic report only | YES |

---

PRIMARY ROOT CAUSE:
Merchant UI V2’s `max-width: 1023px` contract forcibly hides Global Upbar destinations (`.cf2-nav`) and reassigns Global platform navigation exclusively to the hamburger Global Drawer (`#cf2-drawer`), changing ownership—not just presentation—of Global on mobile. Introduced in V2 birth commit `4fb6604` and retained by `nav-reset-v1` (`8828635`); inherited from V1’s ≤1023 hamburger-drawer navigation law.

EXACT CODE RESPONSIBLE:
`static/merchant_ui_v2_frame.css` — `@media (max-width: 1023px) { body[data-cf-ui="v2"] .cf2-nav { display: none !important; } }` (with companion rules revealing `.cf2-menu-btn` and documenting “No section name pills”); destinations then only in `templates/merchant_app_v2.html` `#cf2-drawer` / `.cf2-drawer__item[data-cf2-nav]`, opened by `toggleDrawer`/`openDrawer` in `static/merchant_ui_v2_app.js`.

WHY THE LAST ITERATIONS FAILED:
They altered Contextual presentation (pills, strips, page-chrome, ctx sheets) and App Bar chrome/geometry while never inverting the rule that `.cf2-nav` must stay hidden on mobile—so Global platform sections could not return to the Upbar surface.

MINIMUM ARCHITECTURAL CORRECTION REQUIRED:
Restore a single semantic ownership model (GlobalNavigation + ContextualNavigation + PageStage) where responsive CSS may adapt Global presentation but must not demote Global destinations to drawer-only; bind Global lists to one registry (`NAV.global`) so breakpoint CSS cannot orphan the Upbar host independently of the model. Do not invent a third nav layer. Do not redesign page content.

FILES THAT WOULD NEED CHANGE:
`static/merchant_ui_v2_frame.css` (remove/replace Global demotion contract); `templates/merchant_app_v2.html` and/or `static/merchant_ui_v2_app.js` (single Global render path from `NAV.global`; clarify drawer as auxiliary presentation, not sole owner); possibly `tests/test_merchant_ui_v2.py` (align stale marker expectations). Evidence/docs for the future correction task only.

FILES THAT MUST NOT CHANGE:
Home/Workspace content modules and freezes (`static/merchant_ui_v2_home.js|.css`, `static/merchant_ui_v2_workspace.js|.css`, Home visual freeze packs); V1 rollback shell unless explicitly tasked (`templates/merchant_app.html`, `static/merchant_frame_v1.css`); product page stubs’ business content; no new parallel navigation experiment packs as substitutes for ownership correction.
