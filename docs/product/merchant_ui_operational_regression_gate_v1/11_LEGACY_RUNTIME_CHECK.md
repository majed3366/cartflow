# Gate 11 — Legacy / Dead Runtime Check

Artifact: `legacy_runtime_inventory.json`

| Experiment | Classification | Evidence |
|------------|----------------|----------|
| `cf2-global-btn` / global panel | **REMOVED** | Absent template/JS; tests forbid |
| `is-global-nav-open` | **REMOVED** | Absent app/frame; tests forbid |
| page-chrome navigation | **REMOVED** | Superseded by shell-integration-v1 |
| Old contextual sheet / section pills | **REMOVED** | Runtime DOM false |
| `nav-reset-v1` remnants | **UNREACHABLE** | Historical only; current shell marker |
| `global-ownership-v1` panel | **REMOVED** | Superseded by UtilityRow+GlobalUpbar |
| Duplicate shell initializers | **DEAD** | Single `DOMContentLoaded` bind |

**ACTIVE colliding remnants:** **none**

Gate 11: **PASS** (no cleanup performed — audit only).
