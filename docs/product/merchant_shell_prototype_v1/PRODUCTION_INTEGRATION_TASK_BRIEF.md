# Merchant Shell — Production Integration Task Brief V1

**Status:** READY TO ISSUE — not started  
**Prerequisite:** Merchant Shell Prototype V1 — **VISUALLY APPROVED** (architectural direction)  
**Prototype pack:** `docs/product/merchant_shell_prototype_v1/`

---

## Approved architecture (do not redesign)

```
MerchantShell
├── UtilityRow
├── GlobalUpbar
├── ContextualSidebar
└── PageStage
```

| Layer | Responsibility |
|-------|----------------|
| UtilityRow | CartFlow identity + account/utility only |
| GlobalUpbar | Platform destinations — visible at every breakpoint |
| ContextualSidebar | Items inside active platform section |
| PageStage | Page content only |

### Desktop (approved)

Global Upbar + Contextual Sidebar + Page Stage

### Mobile closed (approved)

Utility/header + **visible** Global platform destinations (horizontal overflow OK) + Page Stage  
Contextual = restrained edge handle on Page Stage (not in Utility/Global rows)

### Mobile contextual open (approved)

Same Contextual Sidebar off-canvas — separate from Global; not a new nav product

### Account / utility (approved)

Account/hamburger = utility only (الحساب / الملف والباقة / تسجيل الخروج).  
**Must not** be the primary owner of platform navigation.

---

## Explicitly approved vs not approved

| Approved | Not approved yet |
|----------|------------------|
| Core shell ownership model | Final mobile density / polish |
| Global always visible on mobile (no grid/panel as primary) | Visual micro-tuning of chrome |
| Contextual separate from Global | Home / Workspace composition changes |
| Architectural direction from prototype | Production pixel parity with prototype styling |

---

## Integration scope (when task is issued)

**In scope**

- Wire production Merchant UI V2 shell (`merchant_app_v2.html` + `merchant_ui_v2_frame.css` + `merchant_ui_v2_app.js`) to this ownership model
- One canonical `NAV.global` / `NAV.contextual` → Utility / Global / Contextual mounts
- Replace drawer-only / grid-panel Global presentation with visible Global Upbar on mobile
- Keep Contextual as `#cf2-ctx` (desktop column / mobile off-canvas from Page Stage edge)
- Strip platform destinations from being account-drawer-primary
- Regression evidence: desktop + mobile closed + contextual open + account utility

**Out of scope**

- Redesigning the approved shell structure
- Broad visual polishing / density pass
- Home composition changes
- Decision Workspace composition changes
- Products / Carts / Communication / Settings implementation
- New navigation V4/V5/V6 experiments

---

## Hard constraints for the integrator

1. Do **not** redesign the shell.
2. Do **not** start broad visual polishing.
3. Do **not** touch page compositions (Home / Workspace).
4. Do **not** reintroduce: grid Global button, Global panel as primary, page chrome, تنقل القسم, section pills in utility row, Global+Contextual controls sharing the utility row.
5. Responsive may change presentation density; must **not** change ownership or semantics.

---

## Suggested acceptance (for future task)

- Desktop: Upbar Global + Sidebar Contextual unchanged in ownership
- Mobile closed: platform destinations visible without opening any menu; active section indicated
- Mobile: Contextual opens from Page Stage edge handle only
- Account drawer: utility-only primary purpose
- Home/Workspace file hashes / visual freeze preserved
- Living Store evidence only after automated shell gates pass
- **STOP for visual approval** — no PASS/freeze until product reviews production shell

---

## STOP

This brief prepares the integration task.  
**Do not begin production integration until the dedicated integration task is issued.**
