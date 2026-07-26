# Technical-Copy Removal Report V1

**Date (UTC):** 2026-07-26  
**Scope:** Merchant surfaces only (Home, Workspace, Products, Carts, Communication)

## Removed / stopped painting

| Surface | Removed |
|---------|---------|
| Home | Identity audit banner (`CONSISTENT`, `CEO_REVIEW_SAFE`, run stamps, store_slug) |
| Workspace | Visible `<code>situation_id</code>` / `cs:…` on decision cards |
| Products | Title «المنتجات المشاركة في مواقف العمل» → «المنتجات التي تستحق انتباهك»; no `cs:` chips |
| Carts | Raw situation-id banners above operational list; publication banner is merchant Arabic only |
| Communication | Identity chips / `run=` / `situations=` / CONSISTENT stamps |

## Still allowed (non-merchant)

- `/dev/reality-validation-context`
- `/dev/reality-validation-console`
- Admin / Dev diagnostics
- Transport fields inside JSON (`situation_id`, `truth_version`, `simulation_run_id`) that are **not rendered**

## Verification

Automated: `tests/test_executive_control_parity_v1.py::TechnicalCopyBanTests`  
Manual: Production CEO pack screenshots must show zero technical tokens on merchant pages.
