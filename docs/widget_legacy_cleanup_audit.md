# Widget Legacy Cleanup Audit

**Purpose:** Inventory references to legacy (`cartflow_widget.js`) vs layered V2 (`static/cartflow_widget_runtime/**`) vs shared scripts **before any deletion**.

**Audit date:** Snapshot of repository state when this doc was added.

**Classification key**

| Tag | Meaning |
|-----|---------|
| **A)** | V2 active runtime |
| **B)** | Legacy widget runtime |
| **C)** | Shared tracking / lifecycle (not “widget UI” monolith but often required alongside widget) |
| **D)** | Demo-only helper |
| **E)** | Cleanup candidate later (after migration + QA) |
| **F)** | Must keep for now |

---

## 1. Current active runtime

- **Canonical storefront shim:** `static/widget_loader.js` — loads return tracker, then loads either layered V2 or legacy based on **`window.CARTFLOW_WIDGET_RUNTIME_V2`** (and **`cartflowIsDemoStorePrimaryV2Path()`** for `/demo/store*`). **Classification: A + orchestration.**

- **`/demo/store` (demo storefront):**

  | Layer | File / behavior | Class |
  |-------|-----------------|-------|
  | Unified bootstrap | `static/widget_loader.js` | **A** (entry) |
  | Return / recovery tracking | `static/cartflow_return_tracker.js` (via shim) | **C** |
  | Demo UI | `static/cartflow_demo_panel.js` | **D** |
  | Demo guide | `static/cartflow_demo_guide.js` | **D** |
  | Abandon / session tagging | `static/cart_abandon_tracking.js` (via partial) | **C** |
  | V2 chain entry | `static/cartflow_widget_runtime/cartflow_widget_loader.js` → modules in same directory | **A** |

- **`/demo/store` does _not_ use `static/cartflow_widget.js`** for the cart-recovery UX when primary V2 is active (validated by baseline + Network checks). Legacy remains in repo for non-demo paths and fallback.

---

## 2. Answers to targeted questions

### Is `static/cartflow_widget.js` still loaded anywhere?

**Yes — but not on `/demo/store` under the current primary-V2 wiring.**

Known **loader-based** loads:

| Mechanism | When `cartflow_widget.js` loads |
|-----------|----------------------------------|
| **`static/widget_loader.js`** | **`window.CARTFLOW_WIDGET_RUNTIME_V2` is not `true`** at `load()` time → `s.src = "/static/cartflow_widget.js?..."`. **B / F** |
| **`static/cartflow_widget_runtime/cartflow_widget_flows.js`** (`injectLegacyCartflowWidget`) | Dynamic `<script>` to `/static/cartflow_widget.js` with `data-cf-legacy-widget-v2-fallback="1"` when **VIP mirror** chooses legacy — **skipped on `/demo/store*`** paths via `isDemoStorePrimaryWidgetPath()`. Elsewhere → **B / F** |
| **`main.py` dev HTML** `_DEV_WIDGET_TEST_HTML` routes `/dev/widget-test`, `/dev/widget-test/cart` | Inline `<script src="/static/cartflow_widget.js">`. **B / F** for dev tooling |

### Is `static/cartflow_widget.js` still referenced anywhere?

**Yes — broadly.** Non-exhaustive but material references:

| Area | References | Class |
|------|------------|-------|
| **Loader** | `widget_loader.js` comments, duplicate-script guard checks `prevSrc.indexOf("/static/cartflow_widget.js")`, legacy `s.src` | **A+B / F** |
| **V2 flows** | `injectLegacyCartflowWidget()` builds URL `/static/cartflow_widget.js?...` | **A+B / F** |
| **`static/cartflow_widget.js`** (self) | Guard with **`window.CARTFLOW_WIDGET_RUNTIME_V2 === true`** vs **`window.__CF_LOAD_LEGACY_CARTFLOW_WIDGET !== true`** | **B** |
| **Tests** reading file for static regressions | e.g. `tests/test_cartflow_widget_runtime_state_machine.py`, `test_cartflow_widget_reason_persist_client_guard.py`, `test_abandonment_reason_*`, `test_nested_price_classification.py`, operational observability tests | **B / F** (until tests rewritten against V2) |
| **Docs** | `docs/SYSTEM_SUMMARY.md`, `docs/cartflow_operational_risk_test_report.md` describe legacy bundle | **E** (documentation refresh later) |

### Does any fallback still depend on it?

**Yes.**

- **`__CF_LOAD_LEGACY_CARTFLOW_WIDGET`:** Set in **`cartflow_widget_flows.js`** before injecting legacy script; respected inside **`cartflow_widget.js`** (early guard).

- **VIP delegation:** **`mirrorAndVipGate()` → `injectLegacyCartflowWidget()`** still targets **`cartflow_widget.js`** for stores where VIP path is enabled (excluding **`/demo/store*`**).

- **Rollback:** Repo policy has been to **keep legacy file available** until all storefront/embed paths default to V2 and VIP strategy is redesigned.

### Does exit intent depend on legacy widget or V2?

**Both stacks can surface exit-intent UX; configs are shared conceptually.**

| Runtime | Exit intent handling |
|---------|---------------------|
| **Legacy** (`cartflow_widget.js`) | Large in-file implementation (`exit_intent_*`, timers, showBubble with `TRIGGER_SOURCE_EXIT_INTENT`, etc.). **B** |
| **V2** (`cartflow_widget_runtime/cartflow_widget_triggers.js`, `flows.js`) | Separate orchestration (`scheduleExitIntentTimer`, gates, hooks `fireExitNoCart` / `fireExitWithCart`). **Config** from **`cartflow_widget_config.js`** (`exit_intent_enabled`, sensitivity, frequency, delays). **A** |

**Dashboard / APIs** (`exit_intent_*` columns, recovery settings): **persisted separately** — not “legacy-only”; **F** regardless of storefront runtime.

---

## 3. Search term → summary

| Pattern | Role | Typical class |
|---------|------|----------------|
| `static/cartflow_widget.js` / `cartflow_widget.js` | Legacy monolith URL and file | **B** (runtime), **F** (until sunset) |
| `__CF_LOAD_LEGACY_CARTFLOW_WIDGET` | V2→legacy injection handshake | **A+B bridge / F** |
| `CARTFLOW_WIDGET_RUNTIME_V2` | Choose V2 chain in shim; demo template sets `true` | **A / F** |
| `cartflow_widget_runtime/` | Layered modules + `cartflow_widget_loader.js` | **A / F** |
| `widget_loader.js` | Single entry after `window.load`; V2 vs legacy fork | **A / F** |
| `cartflow_demo_guide.js` | **`templates/demo_store.html` only** (observed) | **D / F** for demo UX |
| `cart_abandon_tracking.js` | Many templates via `partials/cart_abandon_tracking.html`; **`demo_store.html` includes partial** | **C / F** (not legacy widget blob) |
| `cartflow_return_tracker.js` | Loaded by **`widget_loader.js`** for return-to-site durability | **C / F** |
| “Exit intent” / `exit_intent_*` | Legacy bundle + V2 config/triggers + DB/dashboard | Mixed **B / A / F** |
| “Legacy widget”, “fallback” (code) | Primarily **`injectLegacyCartflowWidget`**, **`data-cf-legacy-widget-v2-fallback`**, **`LEGACY_BRIDGE`** log banner in V2 (**name only** — does not load `cartflow_widget.js`) | **A+B / F** |

---

## 4. Match log (samples by area)

_Per search (not line-by-line). Use repo grep on these paths for exhaustive lists._

### 4.1 Runtime / loaders

| Location | Finding | Class |
|----------|---------|-------|
| `static/widget_loader.js` | Loads V2 **`…/cartflow_widget_loader.js`** or legacy **`cartflow_widget.js`**; loads **`cartflow_return_tracker.js`** | **A + C**, legacy branch **B** |
| `static/cartflow_widget_runtime/*.js` | Entire layered runtime | **A** |
| `static/cartflow_widget.js` | Monolith | **B** |

### 4.2 Templates

| Location | Finding | Class |
|----------|---------|-------|
| `templates/demo_store.html` | **`CARTFLOW_WIDGET_RUNTIME_V2 = true`**, **`widget_loader.js`**, **`cartflow_demo_guide.js`**, **`cartflow_demo_panel.js`**, **`cart_abandon_tracking` partial** | **A**, **D**, **C** |
| `templates/general_settings.html` | Snippet constructing **`widget_loader.js`** URL for merchant embed (**does not bake V2 flag** unless embedder adds inline flag) | **A / F** |
| Dashboard / hubs | **`cart_abandon_tracking` partial** widely; **no** inline `cartflow_widget.js` in scanned templates except dev | **C / F** |

### 4.3 Backend / Python (references only — **no deletion in this audit**)

| Location | Finding | Class |
|----------|---------|-------|
| `main.py` | **`/dev/widget-test`** serves HTML with **`/static/cartflow_widget.js`** | **D dev / B blob / F** until dev uses V2 |
| Models / schema / services | **`exit_intent_*`**, **`cartflow_widget_*`** gates — configuration, not legacy file deps | **F** |

### 4.4 Tests & docs

| Location | Finding | Class |
|----------|---------|-------|
| `tests/test_cartflow_widget_layered_runtime.py` | Expects shim to reference **both** V2 URL and **`/static/cartflow_widget.js`** (fork) | **A / F** |
| Multiple tests | **`read_text`** on **`static/cartflow_widget.js`** for static regressions | **B / F** |
| `docs/SYSTEM_SUMMARY.md` etc. | Legacy-oriented descriptions | **E** |

---

## 5. Cleanup candidates (**E**) — safe only _after_ migration sign-off

**Do not delete until:**

- All production storefront/embed paths intentionally use V2 (`CARTFLOW_WIDGET_RUNTIME_V2` or equivalent permanent default).
- VIP strategy no longer **`injectLegacyCartflowWidget()`** **or** product accepts dropping VIP legacy parity.
- Dev routes (`/dev/widget-test`) either removed or switched to **`widget_loader` + V2**.
- Static tests rewired from **`cartflow_widget.js`** excerpts to **`cartflow_widget_runtime`** or extracted shared fixtures.

**Tentative E-list (later):**

| Item | Risk if removed early |
|------|------------------------|
| **`static/cartflow_widget.js`** | Breaks loader legacy branch, VIP injection, `/dev/widget-test`, many regression tests |
| **`docs/SYSTEM_SUMMARY.md` sections pointing only at legacy** | Confusion — low technical risk (**E**) |
| **Legacy-only dead code paths** inside monolith (_if any_) | Requires dedicated diff — not identified in this pass |

---

## 6. Must keep for now (**F**)

| Artifact | Reason |
|----------|--------|
| **`static/widget_loader.js`** | Central bootstrap; **C** tracker + widget fork |
| **`static/cartflow_return_tracker.js`** | Used by shim |
| **`static/cart_abandon_tracking.js` + partial** | Storefront/dashboard inclusion; **`demo_store`** uses it |
| **`static/cartflow_widget_runtime/**`** | Primary V2 |
| **`static/cartflow_widget.js`** | Legacy default path; VIP fallback; dev harness; tests |
| **`injectLegacyCartflowWidget` path in `cartflow_widget_flows.js`** | Rollback / VIP unless product removes |
| **`CARTFLOW_WIDGET_RUNTIME_V2` + shim logic** | Runtime selection |

---

## 7. Risks before deletion

1. **Merchant embed snippets** (`general_settings.html`) construct **`widget_loader.js`** URLs — embedders may omit V2 flag and **implicitly remain on legacy** until documented/migrated (**F**).
2. **`injectLegacyCartflowWidget`** silently adds legacy script tag — deleting **`cartflow_widget.js`** breaks **VIP** storefronts until V2 parity is enforced.
3. **Test suite coupling** — several tests **`read`** the monolithic file verbatim (**F** to update first).
4. **Operational scans** (`test_operational_static_observability.py`) grep **`cartflow_widget.js`** for markers — pipeline expectations **F**.
5. **Documentation drift** — `SYSTEM_SUMMARY.md` still describes legacy as “main widget” (**E** refresh).

---

## 8. Recommended deletion order (**future** — **not executing in this audit**)

1. **Documentation** — Align `SYSTEM_SUMMARY.md` / risk reports with “V2 primary, legacy fallback” (**E**, zero runtime risk).

2. **Dev routes** — Switch **`/dev/widget-test`** to **`widget_loader`** + **`CARTFLOW_WIDGET_RUNTIME_V2`** (no direct legacy tag).

3. **Embed documentation + defaults** — Encourage **`CARTFLOW_WIDGET_RUNTIME_V2 = true`** in copied snippets (`general_settings.html` UX copy only — product decision).

4. **Migrate static tests** off **`cartflow_widget.js`** file reads where behavior now lives under **`cartflow_widget_runtime`**.

5. **VIP / fallback** — Remove **`injectLegacyCartflowWidget`** and legacy branch from **`widget_loader.js`** **only after** KPI sign-off.

6. **`static/cartflow_widget.js`** — Last: archive or delete when no code path loads it (**verify** CI grep + staging Network).

---

## 9. Verification commands (after any future cleanup)

```bash
# Seven baseline checks (layered runtime + shell lifecycle)
pytest tests/test_cartflow_widget_layered_runtime.py tests/test_cartflow_widget_shell_lifecycle.py -q

# Broader widget/static regressions (as needed)
pytest tests/test_demo_behavioral_navigation.py -q
pytest tests/test_cart_recovery_sequence_behavior.py -q
```

**Manual:** **`/demo/store`** — confirm Network has **`cartflow_widget_runtime/cartflow_widget_loader.js`** and module chain; **no** **`/static/cartflow_widget.js`** (with current primary-V2 wiring).

---

## 10. Disclaimer

This document is **read-only audit evidence**. **No loader, runtime, backend, dashboard, WhatsApp, or lifecycle code was modified** when adding this file.
