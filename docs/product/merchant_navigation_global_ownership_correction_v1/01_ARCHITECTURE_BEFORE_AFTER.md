# 01 — Architecture Before / After

## Before (nav-reset-v1)

```
Desktop ≥1024
  Global → .cf2-nav (static HTML)
  Contextual → #cf2-ctx
  Content → #cf2-stage

Mobile ≤1023
  .cf2-nav { display: none !important }   ← Global Upbar host killed
  Global destinations ONLY in #cf2-drawer (hamburger / account)
  Contextual → #cf2-ctx overlay
```

**Violation:** Responsive CSS changed Global **ownership** (Upbar → drawer-only).

## After (global-ownership-v1)

```
MerchantShell
├── GlobalNavigation   ← NAV.global (single registry)
│     desktop mount:  #cf2-nav
│     mobile mount:   #cf2-global-btn + #cf2-global-panel
│     utility mount:  #cf2-drawer-global (optional convenience)
├── ContextualNavigation ← NAV.contextual → #cf2-ctx (unchanged)
└── PageStage            ← #cf2-stage (unchanged)
```

Mobile closed App Bar:

| Control | Layer |
|---------|--------|
| Menu | Account / utility drawer |
| Contextual (`#cf2-ctx-btn`) | ContextualNavigation |
| CartFlow brand | Identity |
| Global (`#cf2-global-btn`) | GlobalNavigation |
| Account | Account / utility drawer |

Platform section switching on mobile uses **Global Navigation control → Global panel**, without requiring the account drawer.
