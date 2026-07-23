# Time Authority Binding Foundation V1 (TABF)

**Status:** Implementation (platform infrastructure)  
**Position:** Governing capability between Evidence and Commerce Intelligence Synthesis in the Product Performance stack — binds *all* PP consumers to one temporal authority.  
**Closes:** CG-MEH-01 (Time Authority binding gap)

## Mission

Guarantee every platform layer interprets time identically. No independent time semantics on merchant Product Performance paths.

## Stack position

```
Canonical Truth
        ↓
Evidence
        ↓
Time Authority  ← governing infrastructure (not producer/consumer of business intel)
        ↓
Commerce Intelligence Synthesis
        ↓
Knowledge
        ↓
Commercial Guidance
        ↓
Operational Truth
        ↓
Surface Composition
        ↓
Merchant Experience
```

## Phases delivered

1. **Inventory** — `TIME_INVENTORY_V1` in `time_authority_binding_registry_v1.py`
2. **Canonical model** — clocks in `time_authority_model.md` / types
3. **Binding audit** — `SUBSYSTEM_BINDINGS_V1` + runtime audit in foundation
4. **Replay consistency** — deterministic SCF/OT fingerprints under fixed `as_of`
5. **Merchant chronology** — MEIF `chronology_cue` on Home (bound display as_of)
6. **SCF binding** — generate uses `resolve_bound_as_of_v1`; freshness from as_of only
7. **Runtime probe** — `GET /dev/time-authority?store=demo`

## Code map

| Module | Role |
|--------|------|
| `time_authority_binding_flag_v1.py` | `CARTFLOW_TIME_AUTHORITY_BINDING_V1` (default on) |
| `time_authority_binding_types_v1.py` | Clock + binding constants |
| `time_authority_binding_registry_v1.py` | Inventory + subsystem bindings |
| `time_authority_binding_resolve_v1.py` | Thin `resolve_bound_as_of_v1` (no PP imports) |
| `time_authority_binding_foundation_v1.py` | Audit + replay verify + report |
| `time_authority_binding_prod_probe_v1.py` | Production probe builder |
| `services/time_authority/*` | Existing INV-001 authority / QTC / scopes |

## Probe contract

`GET /dev/time-authority?store=demo` exposes:

- binding status / canonical clocks
- replay consistency / ordering conflicts
- chronology warnings / drift detection / stale interpretations
- subsystem bindings / SCF·OT·MEIF bind checks
- `ok: true` when registries valid, SCF bound, replay consistent, required subsystems bound

## Explicitly forbidden

- Timeline redesign, analytics, recommendations
- Knowledge / Guidance *logic* changes (as_of default binding only)
- Page-owned freshness or chronology
- New merchant product features

## Tests

`tests/test_time_authority_binding_v1.py` — registry, deterministic replay, historical ordering, SCF/OT/KF/MEIF binding, flag, probe, main wiring-only, FixedAsOf scheduler consistency.

## Exit gate

After deploy: Reality Validation V4 + production closure evidence confirming probe `ok: true` and stable chronology across replay / production / historical simulation.
