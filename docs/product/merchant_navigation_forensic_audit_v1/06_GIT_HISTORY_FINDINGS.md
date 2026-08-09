# 06 — Git History Findings

**Question:** When did mobile become effectively hamburger/drawer-only for Global platform navigation, and did that inherit a prior responsive contract?

---

## A. Historical architectures found

### A1. Merchant UI V1 — Topbar + Rail (merged nav)

**Files:** `templates/merchant_app.html`, `static/merchant_frame_v1.css`, `static/merchant_app.js`  
**Frame intro commits:** `88715f9` (recompose merchant app frame), later presentation rebuilds `425afab`.

**Ownership model:**

```
TOPBAR (.cf-topbar)
  menu + brand + section/page labels + account utils
RAIL (#ma-context-sidebar.cf-rail)
  GLOBAL platform buttons (.cf-rail__primary)
  + CONTEXTUAL panels (.ma-ctx-panel)
CONTENT (.cf-stage / main)
```

**Mobile contract (still in `merchant_frame_v1.css`):**

```css
@media (max-width: 1023px) {
  .cf-topbar__sections, .ma-gtb-sections, … { display: none !important; }
  .cf-rail { /* off-canvas drawer */ transform: translateX(100%); }
  #ma-sidebar-toggle:checked ~ .cf-rail { transform: translateX(0); }
}
```

**Meaning:** ≤1023px → hamburger opens **one** drawer containing **both** Global and Contextual. Topbar does not carry platform section pills.

This is **not** exactly “GLOBAL TOPBAR + CONTEXTUAL SIDEBAR”; Global lived in the rail. But it **is** the ancestor of the breakpoint law:

> mobile &lt; 1024px ⇒ hide persistent platform chrome ⇒ use hamburger drawer

### A2. Merchant UI V2 clean-slate — Global Upbar + Contextual Sidebar (desktop); drawer Global (mobile)

**Commit:** `4fb6604c7a74d8e801c932eaf9ad35fdc0feca88`  
**Date:** Sat Aug 8 2026  
**Message:** `feat: add Merchant UI V2 clean-slate vertical slice (frame, Home, Workspace)`

Introduced:

- `templates/merchant_app_v2.html` with `.cf2-nav` **and** `#cf2-drawer` both listing the six platform sections
- `static/merchant_ui_v2_frame.css` with:

```css
@media (max-width: 1023px) {
  body[data-cf-ui="v2"] .cf2-nav,
  body[data-cf-ui="v2"] .cf2-appbar__date,
  body[data-cf-ui="v2"] .cf2-appbar__desktop-only {
    display: none !important;
  }
  body[data-cf-ui="v2"] .cf2-menu-btn { display: inline-flex; }
  /* drawer becomes the mobile Global nav surface */
}
```

**Proof:** `git log -S ".cf2-nav" -- static/merchant_ui_v2_frame.css` first introduces the hide rule in **`4fb6604`**. It was not a later regression.

**Ownership at birth:**

```
Desktop: Global → Upbar (.cf2-nav); Contextual → #cf2-ctx; Content → stage
Mobile:  Global → Drawer only; Upbar = chrome; Contextual → (evolved later)
```

### A3. Iteration chain (Aug 9 2026) — symptom patches

| Commit | Message | Effect on Global hide rule |
|--------|---------|----------------------------|
| `ed5a902` … `971b1a7` | App Bar / drawer geometry / wordmark / three-zone chrome | Changed App Bar **chrome** and drawer **look**; did not restore `.cf2-nav` on mobile |
| `34d83c3` | restore Global Upbar + Contextual Sidebar | Restored desktop two-level split; mobile context strip separate — **Global still drawer on mobile** |
| `cad4518` | ctx sheet instead of horizontal strip | Contextual presentation change |
| `8d3c5f1` | remove section pill from mobile App Bar | Explicitly **kept** Global out of closed App Bar |
| `aa4c5c0` | move mobile contextual into page chrome V3 | Contextual presentation change |
| `8828635` | reset merchant nav to two levels from one registry | Removed third layers; **reaffirmed** mobile = App Bar + Global Drawer; CSS comment “No section name pills” |

**Current HEAD shell:** `8828635` + docs evidence `8d28dbf`.

---

## B. Comparison: old vs current ownership

| | V1 | V2 original (`4fb6604`) | V2 current (`8828635` / `nav-reset-v1`) |
|--|----|-------------------------|----------------------------------------|
| Global host desktop | Rail | Upbar `.cf2-nav` | Upbar `.cf2-nav` |
| Global host mobile | Rail-as-drawer | Drawer `#cf2-drawer` | Drawer `#cf2-drawer` |
| Contextual host | Same rail panels | `#cf2-ctx` | `#cf2-ctx` (overlay on mobile) |
| ≤1023 hide persistent Global list | Yes (sections not in topbar; rail off-canvas) | Yes (`.cf2-nav { display:none !important }`) | Yes (same rule retained) |
| Global+Contextual merged on mobile? | Yes (one drawer) | Partial (Global drawer; ctx evolved) | No (two overlays) — **but Global still absent from Upbar** |

---

## C. Direct answer to Audit 6

**Does the current failure originate from an inherited responsive contract:**

```
mobile < 1024px
  => hide top/global navigation
  => use hamburger drawer
```

**Yes.**

**Exact proof:**

1. V1: `merchant_frame_v1.css` `@media (max-width: 1023px)` hides topbar section chrome and makes `.cf-rail` a hamburger drawer.
2. V2 birth commit `4fb6604` copies the **same breakpoint** and applies `display: none !important` to `.cf2-nav`, revealing `.cf2-menu-btn` and routing Global destinations through `#cf2-drawer`.
3. Navigation Architecture Reset `8828635` documents and keeps that mobile Global presentation: “App Bar + Global Drawer” / “No section name pills.”

The failure is therefore **not** an accidental CSS bug introduced by a late patch. It is the **foundational V2 mobile presentation binding** for Global navigation, inherited from the V1 ≤1023 drawer pattern, never inverted by subsequent “architecture” fixes (which mostly reworked Contextual presentation and App Bar chrome).

---

## D. What “historical GLOBAL TOPBAR + CONTEXTUAL SIDEBAR” refers to

In V2 terms, that contract is the **desktop** ownership model introduced in `4fb6604` and explicitly restored in `34d83c3` / reset in `8828635`.

It was **never** fully true for mobile V2: mobile Global was drawer-only from the first V2 commit.
