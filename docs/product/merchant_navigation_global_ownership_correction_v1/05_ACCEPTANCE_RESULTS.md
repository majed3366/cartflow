# 05 — Acceptance Results

**Deploy SHA:** `ea236e5a079196d9a1b59d788dd23f2264c6f91b`  
**Marker:** `global-ownership-v1`  
**Capture:** `scripts/_capture_merchant_navigation_global_ownership_correction_v1.py`  
**Raw:** `production_probe.json`

| Gate | Result |
|------|--------|
| globalNavCanonicalModel | **true** |
| desktopGlobalNavConsumesCanonicalModel | **true** |
| mobileGlobalNavConsumesCanonicalModel | **true** |
| drawerIfUsedConsumesCanonicalModel | **true** |
| mobileGlobalNavNotDrawerOnly | **true** |
| globalAndContextualSeparate | **true** |
| globalAndAccountSeparate | **true** |
| desktopUpbarUnchanged | **true** |
| contextualArchitectureUnchanged | **true** |
| homeCompositionUnchanged | **true** |
| workspaceCompositionUnchanged | **true** |
| mobileNoHorizontalOverflow | **true** |
| mobileVerticalScroll | **true** |
| rejectedChromeAbsent | **true** |
| workspaceHashAfterGlobalSwitch | **true** |
| homeHashRestore | **true** |

**Automated status:** all listed gates **true**.

**Visual PASS/FAIL:** NOT DECLARED — await real-device human review (`06_VISUAL_REVIEW.md`).
