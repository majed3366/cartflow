# 03 — Responsive Ownership Map

| Breakpoint | GlobalNavigation presentation | Owner |
|------------|-------------------------------|-------|
| ≥1024px | `#cf2-nav` inline Upbar items | `NAV.global` via `paintGlobalNavigation` |
| ≤1023px | `#cf2-global-btn` + `#cf2-global-panel` | **same** `NAV.global` |
| ≤1023px (optional) | `#cf2-drawer-global` inside utility drawer | **same** `NAV.global` |

| Breakpoint | ContextualNavigation presentation | Owner |
|------------|-----------------------------------|-------|
| ≥1024px | `#cf2-ctx` sidebar column | `NAV.contextual` |
| ≤1023px | `#cf2-ctx` overlay + `#cf2-ctx-btn` | **same** `#cf2-ctx` |

## Rule replaced

**Removed architectural effect:** mobile Global destinations exist only because `#cf2-drawer` lists them after `.cf2-nav` is hidden.

**Replaced with:** mobile hides the *desktop list presentation* of `#cf2-nav`, and surfaces Global through `#cf2-global-btn` / `#cf2-global-panel` painted from the same registry. Utility drawer is no longer the exclusive Global owner.

## Separation

| Surface | body class | Contents |
|---------|------------|----------|
| Global panel | `is-global-nav-open` | Platform sections only |
| Contextual overlay | `is-ctx-open` | Section-local items only |
| Utility drawer | `is-drawer-open` | Account + optional Global shortcuts |
