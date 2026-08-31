# Merchant Platform Visual Identity Residual Closure V1 — Review

**Date (UTC):** 2026-08-31  
**Base candidate:** `011f7d8b1c12942f863527366fcae7847a6313aa`  
**Production SHA:** `2bf18ebcdff069a1b16a7a896b6f6ecb494b92e8`  
**Review URL:** `http://127.0.0.1:8772/dashboard?cf_ui=v2`  
**Not reviewed:** port 8765 (`9d078cc0`, historical) · port 8771 (`011f7d8b`, prior candidate)

## Review environment

| Field | Value |
|-------|-------|
| REVIEW PROCESS | `python -m uvicorn cartflow_api:app --host 127.0.0.1 --port 8772` |
| REVIEW PORT / URL | `127.0.0.1:8772` |
| HTML tokens | `resid1` · `assim1` · `qpool1` · `nvis1-fanout1` |
| Served CSS | Carts/Comms have **no** teal inset; Settings rows `background: transparent` |
| IDENTITY PROVEN | **YES** after candidate commit (header SHA = HEAD). Pre-commit header was still `011f7d8b` because git SHA is HEAD; residual CSS and `resid1` were already served. |

## Rendered evidence

`docs/product/merchant_platform_visual_identity_residual_closure_v1/review/`

Desktop: `desktop_home_ref.png`, `desktop_workspace_ref.png`, `desktop_carts.png`, `desktop_carts_selected.png`, `desktop_comms.png`, `desktop_settings.png`, `desktop_settings_selected.png`  
Mobile: `mobile_home_ref.png`, `mobile_workspace_ref.png`, `mobile_carts.png`, `mobile_carts_selected.png`, `mobile_comms.png`, `mobile_settings.png`, `mobile_settings_selected.png`  
Metrics: `review_metrics.json`

### Computed (Chromium)

| Residual | Selector | Result |
|----------|----------|--------|
| R1 | `.cf2-carts__row.is-selected` | start `3px rgb(8,32,72)`; `box-shadow: none`; radius `0 12 12 0`; top border quiet navy 10% — not teal |
| R2 | `.cf2-comms__detail` | `background: transparent`; start `3px rgba(8,32,72,0.2)`; no pane box |
| R2 mobile | `.cf2-comms__detail` | start `0` (list→detail ownership unchanged) |
| M1 | `.cf2-comms__empty` | solid + start `3px rgba(8,32,72,0.22)` |
| R3 | `.cf2-settings__row` | `background: transparent`; radius `0` |
| R3 needs | `.cf2-settings__row.is-needs` | start amber `rgba(122,78,12,0.42)` |
| R3 selected | `.cf2-settings__row.is-selected` | start navy `rgb(8,32,72)` |
| M3 | `.cf2-settings__detail` | start `3px rgba(8,32,72,0.2)` unchanged |
| Mobile overflow | Carts / Comms / Settings | **false** |

Communication had no list rows on Living Store (truthful empty). Empty M1 demonstrates the list object; detail is the open related pane.

Two Carts queue rows with filter count 1 is **pre-existing** (same on `011f7d8b` review shots). CSS-only pass. Not scored as a new defect.

## Identity

| Surface | Class |
|---------|-------|
| Home | STRONG CARTFLOW IDENTITY (reference; loading copy) |
| Decision Workspace | STRONG CARTFLOW IDENTITY (reference) |
| Carts | STRONG CARTFLOW IDENTITY — queue objects + navy open-start selection |
| Communication | STRONG CARTFLOW IDENTITY — status/history + related open detail |
| Settings | STRONG CARTFLOW IDENTITY — row objects + one detail edge |

**GENERIC SaaS GAP: CLOSED.**  
The prior gap was selection chrome, twin white panes, and filled Settings cards. Those three are gone. Carts remains an operational queue of objects (not an executive stage). That is a different responsibility, not a generic-SaaS leftover.

**LOGO-HIDDEN COHERENCE: PASS.**  
Same grammar: canvas, start-edge, navy selected / amber needs, no teal outline, no extra cards. Different jobs.

## Defects

**BLOCKERS: 0**  
**MUST FIX: 0**  
**DEFERRED POLISH: 0**

## Operational smoke

Desktop and mobile each requested the same eight API paths while visiting Home → Workspace → Carts → Communication → Settings: workspace projection, followups, messages, normal-carts, summary, store-connection, subscription, recovery-settings. No Settings `Promise.all`. No inactive-surface storm. QueuePool tokens unchanged.

**OPERATIONAL REGRESSION: PASS**
