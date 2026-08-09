# 06 — Visual Review

**Status:** STOP — await real-device visual approval. Do not declare PASS. Do not freeze.

**Deploy SHA:** `ea236e5`

## Screenshots captured

| # | File | Observation (agent) |
|---|------|---------------------|
| 01 | `screenshots/01_mobile_home_closed.png` | Closed App Bar shows Menu · Contextual · CartFlow · Global (grid) · Account — Global control present without opening drawer |
| 02 | `screenshots/02_mobile_home_global_nav_open.png` | Panel titled **أقسام المنصة** with six destinations; distinct from account drawer |
| 03 | `screenshots/03_mobile_workspace_after_global_switch.png` | Workspace content after Global switch; App Bar intact |
| 04 | `screenshots/04_mobile_workspace_contextual_nav_open.png` | Contextual overlay: مساحة القرار → ما يحتاج قرارك |
| 05 | `screenshots/05_mobile_global_account_drawer.png` | Utility drawer titled **الحساب**; optional Global shortcuts + account actions |
| 06 | `screenshots/06_desktop_home_regression.png` | Desktop Upbar six sections + sidebar نظرة عامة |
| 07 | `screenshots/07_desktop_workspace_regression.png` | Desktop Workspace regression |

## Human review checklist

A reviewer must confirm three layers are visually distinct:

1. **GLOBAL** — grid control → أقسام المنصة panel / desktop Upbar
2. **CONTEXTUAL** — sidebar icon → `#cf2-ctx` section items
3. **ACCOUNT / UTILITY** — person / hamburger → حساب drawer

If those three are not visually distinct on a real phone → FAIL even though automated gates passed.
