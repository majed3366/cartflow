# Merchant UI V2 — Mobile App Bar Geometry Correction V2

**Status:** Implemented on Living Store — **awaiting visual approval**  
**Do NOT declare PASS. Do NOT freeze App Bar.**  
**Deploy SHA:** `971b1a7`  
**Marker:** `data-cf2-appbar="mobile-geometry-v2"`  

---

## Why the prior bar failed

`mobile-visual-final-v1` used a **3-column grid** with the identity cluster `justify-self: center`. That made `[ mark + CartFlow | section ]` a **viewport-centered island** between Account and Menu — technically tidy, optically wrong. Dead gaps on both sides; no RTL navigation sentence.

---

## Closed-state composition (this pass)

Markup order + natural RTL flex (no forced LTR, no equal-width columns, no space-between as the design):

| Edge / role | Treatment |
|-------------|-----------|
| **Menu** (inline-start / right) | Quiet utility |
| **CartFlow mark + wordmark** | Primary anchor, packed next to Menu |
| **Active section** | Secondary, quieter type, teal rule |
| **Breathing space** | `margin-inline-start: auto` on Account — intentional, not centering |
| **Account** (inline-end / left) | Opposite utility |

Physical LTR reading of the row:

`[ Account ] ——breathing—— [ section | CartFlow + mark ] [ Menu ]`

Desktop unchanged: `.cf2-appbar__core { display: contents }`; Home / Workspace page modules untouched.

---

## Open-state composition (authored handoff)

| Closed | Open |
|--------|------|
| Menu / core / Account visible | App Bar utilities yield (hidden) |
| Navy product bar | **Full-width drawer chrome** (same navy gradient + height) carries CartFlow + close |
| — | White drawer body continues below as the navigation surface |
| — | Account actions live in drawer **الحساب** section |

Intent: open state is **drawer chrome as the App Bar**, not a clipped leftover strip beside a side panel.

---

## Living Store evidence

Viewport **390×844** · SHA `971b1a7`

| File | Scene |
|------|--------|
| `01_mobile_home_closed.png` | Home closed |
| `02_mobile_workspace_closed.png` | Workspace closed |
| `03_mobile_home_bar_closeup.png` | Home bar crop |
| `04_mobile_workspace_bar_closeup.png` | Workspace bar crop |
| `05_mobile_home_drawer_open.png` | Home drawer open |
| `06_mobile_workspace_drawer_open.png` | Workspace drawer open |
| `07_closed_vs_open_relationship.png` | Closed vs open composite |

Supporting probe: `production_probe.json`  
(geometry flags for closed: `coreNotViewportCentered`, `menuNearRightEdge`, `accountNearLeftEdge`, `noWrap`, `noOverflow` — **supporting only**)

---

## Visual questions (for reviewer — not agent PASS)

| # | Question | Notes for review |
|---|----------|------------------|
| A | One intentional CartFlow product bar? | Closed: right-weighted RTL sentence |
| B | CartFlow visually the anchor? | Bold wordmark + mark next to Menu |
| C | Active section clearly secondary? | Smaller / softer; teal rule |
| D | Menu & Account edge utilities? | Not equal siblings to brand |
| E | No artificial centered island? | Cluster packed to Menu; breathing to Account |
| F | Dead spaces controlled? | One intentional flex gap — not two equal voids |
| G | Drawer preserves continuity? | Full-width navy chrome replaces bar |
| H | Stable Home ↔ Workspace? | Same architecture; section text only |
| I | No wrap / overflow / clip? | Probe + screenshots at Living Store mobile |

---

## Out of scope (honored)

- No App Bar freeze  
- No Products / Carts / Communication / Settings work  
- No Home or Decision Workspace composition edits  
- No Desktop App Bar redesign  

---

## STOP

Implementation + Living Store screenshots + this report.  
**Await visual approval.** Do not declare PASS. Do not freeze.
