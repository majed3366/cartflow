# 01 — Current Navigation Map

**Scope:** Production Merchant UI V2 (`data-cf-ui="v2"`, marker `data-cf2-appbar="nav-reset-v1"`).  
**Entry:** `GET /dashboard` → `templates/merchant_app_v2.html` when `merchant_ui_v2_requested()` is true.  
**Status:** READ-ONLY forensic map. No implementation.

---

## Intended vs observed

| Layer | Intended | Observed desktop (≥1024) | Observed mobile (≤1023) |
|-------|----------|---------------------------|-------------------------|
| GLOBAL | Platform sections in Upbar | `.cf2-nav` visible in `.cf2-appbar` | `.cf2-nav` **hidden**; platform sections only in `#cf2-drawer` |
| CONTEXTUAL | Items inside active section in Sidebar | `#cf2-ctx` column | Same `#cf2-ctx`, restyled as overlay; opened via `#cf2-ctx-btn` |
| CONTENT | Page stage only | `#cf2-stage` | `#cf2-stage` |

---

## Shell tree (live DOM)

```
body[data-cf-ui="v2"]
└── .cf2-root
    ├── header.cf2-appbar[data-cf2-appbar="nav-reset-v1"]     ← GLOBAL chrome surface
    │   ├── button.cf2-menu-btn                               ← opens GLOBAL drawer (mobile)
    │   ├── button#cf2-ctx-btn.cf2-ctx-btn                    ← opens CONTEXTUAL overlay (mobile)
    │   ├── a.cf2-brand[data-cf2-nav-brand]                   ← brand → #home
    │   ├── nav.cf2-nav                                       ← GLOBAL platform links (desktop)
    │   ├── .cf2-appbar__actions                              ← date + identity (desktop)
    │   └── button#cf2-mobile-account                         ← account → GLOBAL drawer (mobile)
    └── .cf2-shell[data-cf2-ctx="on|off"]
        ├── aside#cf2-ctx.cf2-ctx                             ← CONTEXTUAL host
        └── main#cf2-stage.cf2-stage                          ← CONTENT
            └── .cf2-stage__inner
                └── section.cf2-page[data-cf2-page=…]

(siblings of .cf2-root)
├── .cf2-drawer-backdrop
├── aside#cf2-drawer.cf2-drawer                               ← GLOBAL drawer (duplicate platform list)
└── #cf2-ctx-backdrop.cf2-ctx-backdrop                        ← CONTEXTUAL mobile dimmer
```

---

## Platform sections (labels)

| id | Label | Desktop host | Mobile host |
|----|-------|--------------|-------------|
| `home` | الرئيسية | `.cf2-nav__item` | `.cf2-drawer__item` |
| `workspace` | مساحة القرار | `.cf2-nav__item` | `.cf2-drawer__item` |
| `products` | المنتجات | `.cf2-nav__item` | `.cf2-drawer__item` |
| `carts` | السلال | `.cf2-nav__item` | `.cf2-drawer__item` |
| `comms` | التواصل | `.cf2-nav__item` | `.cf2-drawer__item` |
| `settings` | الإعدادات | `.cf2-nav__item` | `.cf2-drawer__item` |

Both hosts carry `data-cf2-nav="{id}"`. Active class `is-active` is set by JS on **all** `[data-cf2-nav]` nodes.

---

## Contextual sections (when present)

| Global section | Context title | Items |
|----------------|---------------|-------|
| `home` | الرئيسية | نظرة عامة (`overview`) |
| `workspace` | مساحة القرار | ما يحتاج قرارك (`attention`) |
| `products` / `carts` / `comms` / `settings` | — | `null` → `#cf2-ctx` hidden, `#cf2-ctx-btn` hidden |

Painted into `#cf2-ctx` by `paintCtxMarkup()` / `setContext()` in `static/merchant_ui_v2_app.js`.

---

## Authoritative files

| Role | Path |
|------|------|
| Markup shell | `templates/merchant_app_v2.html` |
| Nav registry + router | `static/merchant_ui_v2_app.js` |
| Frame / breakpoint CSS | `static/merchant_ui_v2_frame.css` |
| Tokens (`--cf2-appbar-h`, `--cf2-ctx-w`) | `static/merchant_ui_v2_ds.css` |
| Gate | `services/merchant_ui_v2/flag_v1.py`, `routes/merchant_pages.py` |

Home / Workspace page modules (`merchant_ui_v2_home.*`, `merchant_ui_v2_workspace.*`) paint **content only** inside `#cf2-home-root` / `#cf2-workspace-root`. They do not own shell navigation.

---

## One-line verdict

Desktop preserves Global Upbar + Contextual Sidebar. Mobile preserves Contextual as a restyled sidebar overlay, but **demotes Global from the Upbar into a hamburger drawer only** via the `max-width: 1023px` contract.
