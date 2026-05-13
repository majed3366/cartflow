# V2 widget baseline lock

This document freezes the **stable V2 storefront baseline** for **`/demo/store*`** before further legacy cleanup or refactors.

## Current stable baseline (locked by tests)

The following are enforced by **`tests/test_v2_widget_baseline_lock.py`** (HTTP template contract + static reads of **`static/cartflow_widget_runtime/`**):

- **Demo uses V2 shim, not legacy monolith**: **`widget_loader.js`**, **`CARTFLOW_WIDGET_RUNTIME_V2`** in **`demo_store`** HTML; **`/static/cartflow_widget.js`** is **absent** from those responses.
- **`/demo/store*` path coercion**: **`static/widget_loader.js`** continues to force **`CARTFLOW_WIDGET_RUNTIME_V2 = true`** on primary demo storefront paths.
- **V2 module chain**: **`cartflow_widget_loader.js`** `MODULES` array lists all layered files present on disk (**config → api → state → triggers → phone → shell → ui → flows → legacy_bridge**).
- **Add-to-cart / hesitation plumbing**: **`cartflow_widget_triggers.js`** retains **`add_to_cart`** firing/scheduling markers and listens for **`cf-demo-cart-updated`** for demo cart signals.
- **Flow steps**: **`cartflow_widget_ui.js`** defines **yes/no**, **reasons**, **phone**, **continuation** steps (shell `setStep` + presenters + **`[CF V2 SHOW …]`** logs).
- **«أكمل الطلب»**: Primary continuation CTA label remains **`أكمل الطلب`** on the continuation presenter.
- **Minimize-on-no («لا»)**: Cart-recovery **`renderYesNo`** **`onNo`** path still calls **`minimizeLauncher()`** before dismissal flags (**not** only unconditional close).

Adjacent existing guards (keep green): **`tests/test_cartflow_widget_layered_runtime.py`**, **`tests/test_cartflow_widget_shell_lifecycle.py`**, **`tests/test_demo_behavioral_navigation.py`** (seven baseline combo when run together as in CI docs).

## What must not be changed casually

- **`templates/demo_store.html`** embed wiring (**V2 flag** + **`widget_loader`**, never legacy **`cartflow_widget.js`**).
- **`static/widget_loader.js`** demo coercion and **V2-primary / legacy-opt-in** policy (without product sign-off — see **`docs/widget_legacy_cleanup_audit.md`**).
- **`cartflow_widget_ui.js`** step taxonomy (**`yes_no` / `reason` / `phone` / `continuation`**) and the **continuation** primary CTA string **`أكمل الطلب`**.
- **`cartflow_widget_flows.js`** **`onNo` → minimize** behavior for cart recovery yes/no (**UX contract**).

Do **not** treat these as refactor-only churn: loosen or redesign only with explicit acceptance criteria and updating this file + **`test_v2_widget_baseline_lock.py`**.

## Legacy status (summary)

- **`static/cartflow_widget.js`** remains for **explicit rollback** and **dev-only harnesses**; it is **not** part of **`/demo/store`** network contract.
- Authoritative inventory and cleanup ordering: **`docs/widget_legacy_cleanup_audit.md`**.

## Cleanup order later (do not skip)

Follow the audit’s recommended sequence: documentation → dev harness policy → merchant embed defaults → migrate tests off monolith where possible → remove **`widget_loader`** legacy branch only when no production consumer needs it → archive/delete **`cartflow_widget.js`** last.

## Verification

```bash
pytest tests/test_v2_widget_baseline_lock.py tests/test_cartflow_widget_layered_runtime.py tests/test_cartflow_widget_shell_lifecycle.py tests/test_demo_behavioral_navigation.py -q
```

Manual: open **`/demo/store`**, confirm Network shows **`cartflow_widget_runtime/cartflow_widget_loader.js`** + module chain and **no** **`cartflow_widget.js`**.
