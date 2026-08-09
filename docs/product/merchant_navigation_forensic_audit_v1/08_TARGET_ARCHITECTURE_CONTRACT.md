# 08 — Target Architecture Contract

**Status:** Contract only. **DO NOT IMPLEMENT** in this task.

---

## Target shell

```
MerchantShell
├── GlobalNavigation      ← platform sections only
├── ContextualNavigation  ← items inside active platform section only
└── PageStage             ← page content only
```

This matches the semantic split already declared in `merchant_ui_v2_app.js` header comments and `NAV` registry. The defect is **presentation binding**, not missing semantics.

---

## Invariants (non-negotiable)

1. **GLOBAL NAVIGATION always means platform sections**  
   الرئيسية · مساحة القرار · المنتجات · السلال · التواصل · الإعدادات

2. **CONTEXTUAL NAVIGATION always means items inside the active platform section**  
   e.g. Home → نظرة عامة; Workspace → ما يحتاج قرارك

3. **Responsive behavior may change PRESENTATION, never OWNERSHIP or SEMANTICS**  
   - Allowed: density, orientation, overlay vs in-flow, typography, reveal interaction  
   - Forbidden: relocating Global destinations exclusively into a chrome hamburger so the Upbar no longer hosts Global  
   - Forbidden: merging Global and Contextual into one list/drawer as one undifferentiated nav product  
   - Forbidden: inventing a third layer (page-chrome, floating pills, section strip) as a substitute for either level

4. **One semantic navigation ownership model**  
   Prefer a single registry (`NAV.global` / `NAV.contextual`) as the only author of destination lists. Presentation hosts subscribe to it; they must not maintain independent hardcoded copies that can be killed by breakpoint CSS independently of the model.

---

## Presentation bindings (illustrative — not a visual design)

| Viewport | GlobalNavigation presents as | ContextualNavigation presents as |
|----------|------------------------------|----------------------------------|
| Desktop | Upbar | Sidebar column |
| Mobile | Still GlobalNavigation (presentation TBD by later task) | Still ContextualNavigation (may be overlay/sheet/column — TBD) |

This audit does **not** prescribe the final mobile visual for Global (horizontal scroll, compact labels, segmented control, etc.). It only requires that whatever appears is still **owned by GlobalNavigation**, not demoted to “App Bar chrome → drawer-only platform list” as the sole Global surface.

---

## Feasibility against current code

| Piece | Already exists? | Gap |
|-------|-----------------|-----|
| `NAV.global` / `NAV.contextual` | Yes | Global HTML not generated from registry |
| Desktop Upbar Global | Yes (`.cf2-nav`) | Hidden on mobile by CSS contract |
| Contextual `#cf2-ctx` | Yes | Mobile overlay OK as presentation |
| Global Drawer | Yes | Currently **required** as sole mobile Global — must become optional/auxiliary, not owner |
| PageStage | Yes (`#cf2-stage`) | Keep |

**Verdict:** Clean target **can** be MerchantShell → GlobalNavigation + ContextualNavigation + PageStage with one semantic model. Minimum correction is to **break the ≤1023 ownership demotion of Global** and bind both presentations to one registry — without redesigning Home/Workspace content.

---

## Explicit non-goals for the future correction task

- No new V4/V5/V6 navigation product name required
- No Home / Workspace content redesign
- No inventing final mobile visuals in the forensic phase (done)
- No merging Global into Contextual or vice versa
