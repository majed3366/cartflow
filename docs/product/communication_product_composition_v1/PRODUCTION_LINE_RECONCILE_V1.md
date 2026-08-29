# Production Line Reconciliation for Communication V2 V1

Local source-control reconciliation only. **No deploy. No `railway up`. No autodeploy change.**

## Parent

`34c831b4885588ea3962ff6576d42c99589bf905` — current Living Store (Railway `1af494e6`).

## Sources (content only, not history)

| SHA | Used for |
|-----|----------|
| `f7228c0628ed80e494d52c0710436de427720095` | Reviewed Communication V2 composition |
| `cf9451aa1056360d1bdf4b4ec71ce2b8cb3300c6` | Reviewed `.railwayignore` hardening |

Divergent branch history is **not** inherited. Merge-base of live vs Communication remains `c6a912f`.

## Conflict log

| File | Conflict? | Resolution |
|------|-----------|------------|
| `static/merchant_ui_v2_app.js` | No — 34c831b blob == c6a912f | Applied f7228c0 Communication hunks |
| `templates/merchant_app_v2.html` | No — 34c831b blob == c6a912f | Applied f7228c0 Communication wiring |
| `tests/test_merchant_ui_v2.py` | No — 34c831b blob == c6a912f | Applied f7228c0 V2 assertions |
| `docs/SYSTEM_SUMMARY.md` | Yes — both lines edited | Kept 34c831b Admin/canonical text; appended Communication route row + isolated changelog rows |
| `railway.api.toml`, `cartflow_api.py`, Home/Workspace/Carts, Admin paint | None | Untouched |

## Protected (unchanged vs 34c831b)

- `railway.api.toml` PORT-aware `cartflow_api:app`
- `cartflow_api.py`
- `static/merchant_ui_v2_home.js`, `merchant_ui_v2_workspace.js`, `merchant_ui_v2_carts.js`
- Admin Operations V1.1 (`presentation_v11`, `#ops-v11`)
- Needs-You unification marker on Carts

## Added

- `static/merchant_ui_v2_comms.js` / `.css`
- Communication composition tests + pack docs
- `.railwayignore` + snapshot-ignore test/report
