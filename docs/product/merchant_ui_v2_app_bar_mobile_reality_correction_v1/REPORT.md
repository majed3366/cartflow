# Merchant UI V2 — App Bar Mobile Reality Correction V1

**Status:** PASS (visual bbox + closed-bar screenshots)  
**Deploy:** `4e03720` (+ polish push for spacing/cache)  
**Prior gate:** App Bar Final Closure V1 is **NOT closed** for mobile visual acceptance.

## Verdict

The closed mobile App Bar now visibly renders all four required elements on an iPhone-sized Living Store viewport:

`[account] · [CartFlow mark + word] · [active section] · [menu]`

## Root cause

Mobile CSS intentionally hid the brand wordmark:

```css
.cf2-brand__word {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
```

Result on real iPhone:
- only a mark fragment remained next to account
- CartFlow identity read as missing
- section/`flex: 1` created a large empty gap that made the bar feel broken
- DOM/probe gates could still PASS while the visual product failed

## Exact fix

In `static/merchant_ui_v2_frame.css` (mobile ≤1023px):

1. Restore `.cf2-brand__word` to visible static layout (`position: static`, no clip)
2. Keep brand `flex: 0 0 auto` so mark+word never disappear under compression
3. Keep account + menu `flex-shrink: 0`
4. Keep section readable with ellipsis only when needed (`min-width: 4.5rem`)
5. Marker: `data-cf2-appbar="mobile-reality-v1"`

No page composition / truth / API changes.

## Before / after

| Before (Final Closure mobile) | After (Reality Correction) |
|-------------------------------|----------------------------|
| account + mark fragment + gap + section + menu | account + **CartFlow mark+word** + section + menu |
| wordmark clipped / invisible | wordmark visible (`CartFlow`) |
| DOM probe could PASS falsely | bbox probe requires all four rects in viewport |

## Visual acceptance (mandatory)

Probe measures real bounding rectangles and requires each of account / brand word / section / menu to intersect the visible viewport with non-trivial size. DOM-only presence is insufficient.

| Gate | Result |
|------|--------|
| visualFourElementsHome | **PASS** |
| visualFourElementsWorkspace | **PASS** |
| wordmarkNotClipped | **PASS** |
| sectionHome (`الرئيسية`) | **PASS** |
| sectionWorkspace (`مساحة القرار`) | **PASS** |
| afterDrawerCloseStillComplete | **PASS** |
| afterHashNavigationStillComplete | **PASS** |
| drawerBodyLockReleased | **PASS** |
| pageVerticalScroll | **PASS** |
| desktopIdentityIntact | **PASS** |
| workspaceCompositionUnchanged | **PASS** |

## Evidence

| File | Role |
|------|------|
| [01_mobile_home_bar_closed.png](01_mobile_home_bar_closed.png) | Home closed bar — all four visible |
| [02_mobile_workspace_bar_closed.png](02_mobile_workspace_bar_closed.png) | Workspace closed bar — all four visible |
| [03_mobile_home_drawer_open.png](03_mobile_home_drawer_open.png) | Drawer open |
| [04_mobile_home_after_drawer_close.png](04_mobile_home_after_drawer_close.png) | Bar intact after drawer close |
| [05_mobile_workspace_after_hash_navigation.png](05_mobile_workspace_after_hash_navigation.png) | After `#workspace` navigation |
| [06_desktop_workspace_regression.png](06_desktop_workspace_regression.png) | Desktop regression |
| [production_probe.json](production_probe.json) | Bbox probe + gates |

## STOP

Mobile App Bar reality correction is complete.  
Do **not** freeze Decision Workspace in this step.  
Do **not** start Products / Carts / Communication / Settings.
