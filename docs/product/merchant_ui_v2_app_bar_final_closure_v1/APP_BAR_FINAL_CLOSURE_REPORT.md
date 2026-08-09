# Merchant UI V2 — App Bar Final Closure V1

**Status:** PASS — Living Store validated  
**Deploy:** `ed5a902`  
**URL:** https://smartreplyai.net/dashboard  

## Objective

Close remaining App Bar gaps before Decision Workspace freeze — without redesigning Home or Workspace page compositions.

## What changed

### Desktop account identity
- Concise identity control: SVG account icon + store display name (`merchant_store_display_name`)
- Removed App Bar clutter: الباقة / خروج (remain in drawer)
- Identity is subordinate to primary nav (`max-width` capped; ellipsis on long names)
- Click opens the existing account/drawer surface (no new account product)

### Mobile real App Bar
Single-row anatomy (LTR chrome row for icon order):

`[account] · [CartFlow mark] · [active section] · [menu]`

- Active section synced from router: الرئيسية / مساحة القرار (reusable for later sections)
- No full desktop nav in the bar
- No two-row wrap
- Drawer remains full navigation

### Cross-surface
- One shared App Bar (`data-cf2-appbar="final-closure-v1"`)
- Home and Workspace differ only by active section label/state

## Do-not-change confirmation

| Surface | Marker | Status |
|--------|--------|--------|
| Home | `home-stage-closure-v1` | unchanged |
| Workspace | `workspace-final-v1` | unchanged |

No API / truth / CO / Living Route / Decision Mass / page typography changes.

## Gate results (Living Store)

| Gate | Result |
|------|--------|
| desktopAccountIdentity | **PASS** |
| mobileActiveSectionVisible | **PASS** |
| sameArchitectureHomeWorkspace | **PASS** |
| mobileNoWrap | **PASS** |
| mobileNoOverflow | **PASS** |
| pageVerticalScroll | **PASS** |
| drawerOpenClose | **PASS** |
| drawerBodyLockReleased | **PASS** |
| frozenHomeUnchanged | **PASS** |
| workspaceCompositionUnchanged | **PASS** |

Source: [production_probe.json](production_probe.json)

## Evidence

| File | Role |
|------|------|
| [01_desktop_home_appbar.png](01_desktop_home_appbar.png) | Desktop Home App Bar |
| [02_desktop_workspace_appbar.png](02_desktop_workspace_appbar.png) | Desktop Workspace App Bar |
| [03_desktop_account_identity_closeup.png](03_desktop_account_identity_closeup.png) | Desktop identity close-up |
| [04_mobile_home_appbar.png](04_mobile_home_appbar.png) | Mobile Home App Bar |
| [05_mobile_workspace_appbar.png](05_mobile_workspace_appbar.png) | Mobile Workspace App Bar |
| [06_mobile_drawer_open.png](06_mobile_drawer_open.png) | Mobile drawer open |
| [07_mobile_home_scrolled.png](07_mobile_home_scrolled.png) | Mobile Home scrolled |
| [08_mobile_workspace_scrolled.png](08_mobile_workspace_scrolled.png) | Mobile Workspace scrolled |
| [09_desktop_full_workspace_regression.png](09_desktop_full_workspace_regression.png) | Workspace regression |
| [10_mobile_full_workspace_regression.png](10_mobile_full_workspace_regression.png) | Mobile Workspace regression |

## STOP

App Bar Final Closure V1 gate is complete.  
Do **not** start Products, Carts, Communication, or Settings.  
Decision Workspace freeze remains a separate visual approval after this App Bar gate.
