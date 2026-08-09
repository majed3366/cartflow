# Merchant Shell Prototype V1

**Mode:** Isolated visual + architectural prototype only  
**Status:** **VISUALLY APPROVED** (architectural direction) — not final UI polish  
**Production:** untouched pending dedicated integration task  
**Integration brief:** [`PRODUCTION_INTEGRATION_TASK_BRIEF.md`](./PRODUCTION_INTEGRATION_TASK_BRIEF.md)

## Canonical structure

```
MerchantShell
├── UtilityRow      ← identity + account/utility only
├── GlobalUpbar     ← visible platform destinations
├── ContextualSidebar
└── PageStage       ← placeholder content only
```

## Prototype entry

Open locally:

`docs/product/merchant_shell_prototype_v1/prototype/index.html`

Capture script (no deploy):

`python scripts/_capture_merchant_shell_prototype_v1.py`

## Screenshots

| File | Viewport |
|------|----------|
| `screenshots/01_desktop_1440_home.png` | 1440 Home |
| `screenshots/02_desktop_1440_workspace.png` | 1440 Workspace |
| `screenshots/03_tablet_1024.png` | 1024 |
| `screenshots/04_mobile_430_home_closed.png` | 430 Home closed |
| `screenshots/05_mobile_430_home_sidebar_open.png` | 430 Home sidebar open |
| `screenshots/06_mobile_430_workspace.png` | 430 Workspace |
| `screenshots/07_mobile_390_home_closed.png` | 390 Home closed |
| `screenshots/08_mobile_390_global_upbar_scrolled.png` | 390 Global scroll |

## Mobile contract shown

1. **Utility row** — CartFlow + account/menu only (no Global icon, no Contextual icon, no section pill)
2. **Global Upbar** — six destinations visible without opening anything; horizontal overflow; active state
3. **Contextual** — collapsed handle on Page Stage edge; opens as off-canvas sidebar (not a new nav product)
4. **Account drawer** — الحساب / الملف والباقة / تسجيل الخروج only (no platform destinations)

## Explicit non-goals completed

- No production CSS/JS/HTML changes
- No Living Store deploy
- No real Home/Workspace composition
- No grid Global button / Global panel / page chrome / تنقل القسم

## Approval

Architectural shell model **approved**. Final density/polish later.  
**STOP** — wait for the production integration task. Do not redesign; do not polish; do not touch page compositions.
