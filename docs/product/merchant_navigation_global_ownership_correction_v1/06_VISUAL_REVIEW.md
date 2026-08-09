# 06 — Visual Review

**Status:** STOP — await real-device visual approval. Do not declare PASS. Do not freeze.

## Required screenshots

| # | File | Must prove |
|---|------|------------|
| 01 | `screenshots/01_mobile_home_closed.png` | Closed App Bar: CartFlow + Global control visible without drawer |
| 02 | `screenshots/02_mobile_home_global_nav_open.png` | Global panel with six platform sections; not account drawer |
| 03 | `screenshots/03_mobile_workspace_after_global_switch.png` | After Global switch to Workspace |
| 04 | `screenshots/04_mobile_workspace_contextual_nav_open.png` | Contextual overlay distinct from Global |
| 05 | `screenshots/05_mobile_global_account_drawer.png` | Account/utility drawer distinct from Global panel |
| 06 | `screenshots/06_desktop_home_regression.png` | Desktop Upbar Global unchanged |
| 07 | `screenshots/07_desktop_workspace_regression.png` | Desktop Workspace + sidebar unchanged |

## Human review checklist

A reviewer must be able to distinguish **three** layers without reading DOM:

1. **GLOBAL** — platform sections via Global control / Upbar
2. **CONTEXTUAL** — section-local items via `#cf2-ctx`
3. **ACCOUNT / UTILITY** — account drawer

If those three are not visually distinct → FAIL even if probes pass.
