# 07 — Root Cause

---

## PRIMARY ROOT CAUSE

Merchant UI V2 encodes a **breakpoint-conditioned ownership split for Global navigation**: below 1024px, the Global Upbar destination list (`.cf2-nav`) is forcibly hidden and Global platform navigation is presented **only** through the hamburger Global Drawer (`#cf2-drawer`). Responsive behavior therefore changes **ownership/surface of Global**, not merely its visual density — violating the intended invariant that Global always means platform sections hosted by GlobalNavigation (Upbar on desktop, adapted but still Global-owned on mobile).

This rule was introduced in the original V2 shell (`4fb6604`) and reaffirmed by Navigation Architecture Reset V1 (`8828635` / `nav-reset-v1`). Later iterations patched Contextual presentation and App Bar chrome while leaving this Global demotion intact.

---

## CODE EVIDENCE

**1. Hide Global from mobile Upbar**

File: `static/merchant_ui_v2_frame.css` L467–490

```css
@media (max-width: 1023px) {
  /*
   * Mobile closed App Bar = GLOBAL shell only:
   * Menu · Contextual sidebar control · CartFlow · Account.
   * No section name pills. No second bar under App Bar.
   */
  body[data-cf-ui="v2"] .cf2-nav,
  body[data-cf-ui="v2"] .cf2-appbar__actions,
  body[data-cf-ui="v2"] .cf2-appbar__date,
  body[data-cf-ui="v2"] .cf2-appbar__desktop-only {
    display: none !important;
  }
}
```

**Effect:** Platform links الرئيسية / مساحة القرار / المنتجات / السلال / التواصل / الإعدادات leave the visible App Bar.

**2. Reveal hamburger as Global entry**

Same file L492–505: `.cf2-menu-btn { display: inline-flex; }`

**3. Duplicate Global destinations live only in drawer for mobile users**

File: `templates/merchant_app_v2.html` L114–119 (`.cf2-drawer__item[data-cf2-nav]`)  
Opened by: `toggleDrawer` / `openDrawer` in `static/merchant_ui_v2_app.js`

**4. Historical origin**

Commit `4fb6604` first added the `.cf2-nav` hide under `max-width: 1023px`.  
Commit `8828635` kept it while documenting mobile Global as “App Bar + Global Drawer”.

---

## WHY PREVIOUS FIXES FAILED

Previous tasks repeatedly changed **Contextual presentation** (section pills, under-bar strips, page-chrome `تنقل القسم`, dedicated ctx sheets, geometry of App Bar chrome) and **App Bar visual composition** (wordmark, three-zone layout, drawer-as-open-App-Bar).

None of those inverted the rule that **`.cf2-nav` must not appear on mobile**. So:

- Moving Contextual into icons/pills/sheets could never restore Global platform sections to the Upbar.
- Polishing hamburger/drawer chrome only reinforced drawer-as-Global.
- “Architecture reset” removed third layers and unified Contextual on `#cf2-ctx`, but **explicitly retained** drawer-only Global on mobile.

Symptom motion without ownership correction.

---

## SECONDARY CONTRIBUTING CAUSES (proven)

1. **Dual static Global markup** — `.cf2-nav` and `#cf2-drawer` are independent HTML copies; `NAV.global` does not render them. Presentation containers can diverge and breakpoint CSS can kill one host without the model “noticing.”

2. **Inherited ≤1023 drawer law from V1** — `merchant_frame_v1.css` already used hamburger + off-canvas rail for navigation below 1024px. V2 reused the breakpoint philosophy for `.cf2-nav`.

3. **App Bar role confusion in comments/product language** — mobile App Bar is labeled “GLOBAL shell” but contains chrome controls, not Global destinations — which invited patches that treated chrome as navigation architecture.

---

## NOT the root cause

- Not a Home/Workspace content bug.
- Not missing Arabic labels in the model.
- Not absence of a Contextual sidebar (Contextual `#cf2-ctx` exists and is correctly separated).
- Not “needs more visual polish.”
- Not requiring a new V4/V5 navigation product.
