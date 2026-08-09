# Merchant Shell Production Integration V1

**Status:** Living Store deployed · automated gates true · **STOP for visual approval**  
**Marker:** `data-cf2-appbar="shell-integration-v1"`  
**Deploy SHA:** `111456bbcb8f5dd2ab45afc4d5403be71a41f31c`  
**Brief:** `docs/product/merchant_shell_prototype_v1/PRODUCTION_INTEGRATION_TASK_BRIEF.md`

**PASS:** not declared  
**Freeze:** not declared

---

## Acceptance answers

1. **Is Global Navigation visible on mobile without opening any menu?**  
   **Yes.** `#cf2-nav` remains visible in GlobalUpbar on ≤1023; six destinations rendered without drawer/panel.

2. **Does Desktop and Mobile consume the same GlobalNavigation model?**  
   **Yes.** Single `NAV.global` → single mount `#cf2-nav`.

3. **Is Contextual Navigation still the same semantic owner across breakpoints?**  
   **Yes.** `NAV.contextual` → `#cf2-ctx` (desktop column / mobile off-canvas). Handle `#cf2-ctx-handle` on PageStage edge only.

4. **Is Account / Utility separate from Global and Contextual navigation?**  
   **Yes.** `#cf2-drawer` contains الحساب / الملف والباقة / تسجيل الخروج only — no أقسام المنصة section.

5. **Were rejected global panel / grid experiments removed from active runtime?**  
   **Yes.** No `#cf2-global-btn`, `#cf2-global-panel`, `is-global-nav-open`, or App Bar `#cf2-ctx-btn`.

6. **Did Home composition remain unchanged?**  
   **Yes.** `merchant_ui_v2_home.js|.css` untouched; stage question/content probe matches frozen Home.

7. **Did Workspace composition remain unchanged?**  
   **Yes.** `merchant_ui_v2_workspace.js|.css` untouched; Workspace question probe matches.

8. **Is horizontal overflow limited to the GlobalUpbar itself?**  
   **Yes.** `responsive_overflow_probe.json` — page/stage/root overflow false across 1440/1024/430/390.

9. **Is there any remaining navigation layer outside UtilityRow / GlobalUpbar / ContextualSidebar / PageStage?**  
   **No.**

---

## Evidence

- Screenshots `01`–`10` under `screenshots/`
- `production_probe.json`
- `responsive_overflow_probe.json`
