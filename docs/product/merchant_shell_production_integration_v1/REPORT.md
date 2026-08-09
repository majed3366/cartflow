# Merchant Shell Production Integration V1

**Status:** Implemented · deploy/evidence pending · **STOP for visual approval**  
**Marker:** `shell-integration-v1`  
**Brief:** `docs/product/merchant_shell_prototype_v1/PRODUCTION_INTEGRATION_TASK_BRIEF.md`

## Acceptance answers (post-capture)

1. Global Navigation visible on mobile without opening any menu? → see `production_probe.json` / gates  
2. Desktop and Mobile same GlobalNavigation model? → yes by construction (`NAV.global` → `#cf2-nav` only)  
3. Contextual same semantic owner across breakpoints? → yes (`#cf2-ctx` + `NAV.contextual`)  
4. Account / Utility separate? → yes (`#cf2-drawer` utility-only)  
5. Rejected global panel / grid removed? → yes (see `03_REMOVED_SUPERSEDED_BEHAVIOR.md`)  
6. Home composition unchanged? → Home JS/CSS untouched  
7. Workspace composition unchanged? → Workspace JS/CSS untouched  
8. Horizontal overflow limited to GlobalUpbar? → see `responsive_overflow_probe.json`  
9. Remaining nav layer outside Utility / Global / Contextual / PageStage? → **must be NO** or FAIL

**PASS:** not declared  
**Freeze:** not declared
