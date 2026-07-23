# Surface Composition Foundation V1 — Deploy Verification

**Flag:** `CARTFLOW_SURFACE_COMPOSITION_V1` (default on)  
**Probe:** `GET /dev/surface-composition?store=demo`  
**Migration:** Alembic `h7i8j9k0l1m2` → `surface_compositions`

## Local

```bash
pytest tests/test_surface_composition_v1.py -q
```

## Production

```bash
python scripts/_verify_surface_composition_v1.py --base https://smartreplyai.net --store demo
```

Expect `ok: true` with:

- `table_exists: true`
- `deterministic: true`
- `accounting_ok: true`
- `registries_valid: true`
- `duplicate_current: 0`
- `consumes_governed_inputs_only: true`
- `composition_count > 0`

## Forbidden after deploy

No page redesign until Surface Composition V1 is reviewed and approved.
