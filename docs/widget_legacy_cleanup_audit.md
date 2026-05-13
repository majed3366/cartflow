# Widget Legacy Cleanup Audit

**Purpose:** Inventory **layered V2** (`static/cartflow_widget_runtime/**`) vs **legacy monolith** (`static/cartflow_widget.js`) vs **shared storefront scripts**, and track **incremental cleanup** after V2 isolation.

**Audit revision:** Refresh after **V2 isolation** — the layered runtime **no longer** injects legacy, sets **`__CF_LOAD_LEGACY_CARTFLOW_WIDGET`**, or references **`injectLegacyCartflowWidget`**. VIP mirrors still run via **`mirrorCartTotals()`** only; recovery + exit-intent UI for bundled V2 storefronts stays inside **`cartflow_widget_runtime`**.

---

## Classification key

| Tag | Meaning |
|-----|---------|
| **A)** | V2 active runtime (layered bundle + shim) |
| **B)** | Legacy widget runtime (monolith `cartflow_widget.js` and anything only meaningful when that file executes) |
| **C)** | Shared tracking / return / abandon scripts (paired with storefront load, not the monolith) |
| **D)** | Demo-only helpers |
| **E)** | Cleanup candidate later (post-migration QA) |
| **F)** | Must keep for now |

---

## 1. Current architecture (post-isolation)

### 1.1 Active V2 runtime (**A**

| Artifact | Role |
|----------|------|
| `static/widget_loader.js` | After `window.load`: schedules **`cartflow_return_tracker.js`**, then **`cartflow_widget_runtime/cartflow_widget_loader.js`** when **`CARTFLOW_WIDGET_RUNTIME_V2 === true`**, or legacy URL when false. Also forces V2 on **`/demo/store*`** via **`cartflowIsDemoStorePrimaryV2Path()`**. |
| `static/cartflow_widget_runtime/cartflow_widget_loader.js` | Serial module loader → bootstrap |
| `static/cartflow_widget_runtime/cartflow_widget_*.js` | Config, API, State, **Triggers**, Phone, Shell, **Ui**, **Flows**, LegacyBridge |
| `window.__cartflowV2Bootstrap` / `Flows.start()` | Starts V2 flows + trigger orchestrator (hesitation, exit intent, gates) |

**Not in V2:** dynamic append of **`/static/cartflow_widget.js`**. **`cartflow_widget_flows.js`** documents that **`mirrorCartTotals()`** refreshes **`cartflowState.isVip`** only; **`[CF V2 FULLY ISOLATED]`** is emitted after **`Triggers.init`**.

### 1.2 Shared storefront scripts (**C**

| Artifact | Typical load |
|----------|----------------|
| `static/cartflow_return_tracker.js` | Injected by **`widget_loader.js`** |
| `static/cart_abandon_tracking.js` | Via **`templates/partials/cart_abandon_tracking.html`** (**`demo_store.html`** and dashboards) |

### 1.3 Demo helpers (**D**

| Artifact | Typical load |
|----------|----------------|
| `static/cartflow_demo_panel.js` | `templates/demo_store.html` |
| `static/cartflow_demo_guide.js` | `templates/demo_store.html` |

### 1.4 Legacy-only runtime (**B** — **F** until sunset)

| Artifact | When it loads |
|-----------|----------------|
| `static/cartflow_widget.js` | **`widget_loader`** when **`CARTFLOW_WIDGET_RUNTIME_V2 !== true`**; **or** **`GET /dev/widget-test*`** (`_DEV_LEGACY_WIDGET_HARNESS_HTML` — **development ENV only**, see §**6.5**) |

---

## 2. `/demo/store` — files loaded (Network-level)

_Order may vary slightly; shim uses non-blocking patterns._

1. **`/static/widget_loader.js`**
2. **`/static/cartflow_return_tracker.js`**
3. **`/static/cart_abandon_tracking.js`** (from partial)
4. **`/static/cartflow_demo_panel.js`**, **`/static/cartflow_demo_guide.js`**
5. **`/static/cartflow_widget_runtime/cartflow_widget_loader.js`**
6. Chained **`cartflow_widget_runtime/*.js`** modules (config → … → legacy_bridge)

**Not loaded** on primary demo store path: **`/static/cartflow_widget.js`** (see **`tests/test_demo_behavioral_navigation.py`** guard).

---

## 3. Direct answers (updated)

### Is `static/cartflow_widget.js` still loaded anywhere?

**Yes**, but **not** as part of the **V2 chained runtime**:

| Loader / page | Mechanism |
|---------------|-----------|
| **`static/widget_loader.js`** | **`s.src = "/static/cartflow_widget.js`** when **`CARTFLOW_WIDGET_RUNTIME_V2` is not `true`** |
| **`main.py`** | **`_DEV_LEGACY_WIDGET_HARNESS_HTML`** — **`GET /dev/widget-test`**, **`GET /dev/widget-test/cart`** embed legacy **`cartflow_widget.js`** directly (**no shim / no V2**). **`404`** unless **`ENV=development`** (explicitly **excluded** from **`_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`** — see **`no_dev_in_production`**). See §**6.5**. |

### Is `static/cartflow_widget.js` still referenced in code/tests/docs?

**Yes** — **shim**, **dev HTML**, **`tests/**`** (static reads), **`docs/SYSTEM_SUMMARY.md`** (**refreshed 2026-05-13** for shim V2 vs legacy), **`cartflow_widget.js` internally** (**`__CF_LOAD_LEGACY_CARTFLOW_WIDGET`** early-exit guard for edge double-load scenarios).

**V2 layered `cartflow_widget_flows.js`:** **does not** reference **`injectLegacyCartflowWidget`**, **`__CF_LOAD_LEGACY_CARTFLOW_WIDGET`**, **`data-cf-legacy-widget-v2-fallback`**, or legacy URL construction (validated by **`tests/test_cartflow_widget_layered_runtime.py`**).

### Does any V2 path still inject legacy fallback?

**No.** Rollback path for storefronts today is **`widget_loader`** choosing the **legacy** script tag when **`CARTFLOW_WIDGET_RUNTIME_V2`** is omitted/false — not runtime injection from V2.

### Exit intent: legacy vs V2?

| Surface | Behavior |
|---------|----------|
| **V2** | **`cartflow_widget_triggers.js`** + **`flows.js`** hooks **`fireExitNoCart` / `fireExitWithCart`**; duplicate cart recovery while shell open is blocked with **`[CF TRIGGER BLOCKED] reason=already_open`**. |
| **Legacy** | Still contains its own exit-intent implementation if **`cartflow_widget.js`** is the only widget script loaded. |
| **Config** | **`exit_intent_*`** from store / API — shared contract (**F**). |

---

## 4. Reclassified inventory

### 4.1 Active V2 runtime (**A** / **F**)

- `static/widget_loader.js` (V2 branch)
- All of `static/cartflow_widget_runtime/**`

### 4.2 Shared scripts (**C** / **F**)

- `static/cartflow_return_tracker.js`
- `static/cart_abandon_tracking.js` + `templates/partials/cart_abandon_tracking.html`

### 4.3 Legacy-only scripts (**B** / **F**)

- `static/cartflow_widget.js` monolith

### 4.4 Demo-only (**D** / **F**)

- `static/cartflow_demo_panel.js`, `static/cartflow_demo_guide.js` (as wired in **`demo_store.html`**)

### 4.5 Cleanup candidates (**E**) — later

- **Done (Tier 1):** ~~`SYSTEM_SUMMARY.md` shim narrative~~ refreshed; ~~`cartflow_operational_risk_test_report.md` ambiguity~~ clarified (still scans loader + legacy only by design).
- Merchant-facing embed snippets in templates / playbooks — periodically scan for copy that ignores **`CARTFLOW_WIDGET_RUNTIME_V2`** or implies V2 loads **`cartflow_widget.js`** automatically.
- After **100% V2** embeds: optional removal of **`widget_loader.js`** legacy branch (then delete monolith last)

### 4.6 Must keep for now (**F**)

- **`widget_loader.js`** + **`CARTFLOW_WIDGET_RUNTIME_V2`** fork
- **`cartflow_widget.js`** for non-V2 embeds, dev widget test, tests, operational scans
- Return tracker + abandon tracking + V2 module tree

---

## 5. Safe first deletion candidates

**Executed (Tier 1, chore `remove safe legacy widget cleanup candidates`):** refreshed **`docs/SYSTEM_SUMMARY.md`** (shim **`CARTFLOW_WIDGET_RUNTIME_V2`** vs legacy branching, **`/demo/store*`** coercion, **`cartflow_widget_runtime/**`**, VIP via **`mirrorCartTotals()`**, no layered legacy injection narrative) and **`docs/cartflow_operational_risk_test_report.md`** (clarifies static scans intentionally cover **`widget_loader`** + **`cartflow_widget.js`**, while V2 **does not** inject the monolith). **No standalone orphaned doc/static files** met the Tier‑1 bar for **`git rm`** beyond removing those stale narratives.

Remaining ordered work:

| Priority | Candidate | Why “first” | Risk if done too early |
|----------|-----------|-------------|-------------------------|
| ~~**1**~~ | ~~Stale **documentation**~~ | ~~No runtime~~ | ~~Confusion~~ — **completed** above |
| **2** | **`/dev/widget-test`** switch to **`widget_loader` + V2** | Aligns dev with primary storefront path | Loses dedicated “legacy only” harness unless a **second** route is kept (**F** rollback/dev today) |
| **3** | **`widget_loader.js`** legacy `else` branch | After **all** embeds **`CARTFLOW_WIDGET_RUNTIME_V2=true`** | Legacy-only merchants break |
| **4** | **`static/cartflow_widget.js`** file (**do not touch yet**) | Sunset monolith last | Loader legacy branch, dev test, **`tests/**`** reading file, **`test_operational_static_observability.py`** |

**There is no “safe first” deletion inside `static/cartflow_widget_runtime/` for isolation purposes** — the bundle is entirely **A / F**.

---

## 6. Explicit lists

### 6.1 Not loaded on **primary V2** storefront runtime

When **`CARTFLOW_WIDGET_RUNTIME_V2 === true`** at **`widget_loader`** run (including **`/demo/store*`** coercion):

- **`/static/cartflow_widget.js`**

_All other URLs are V2 modules, return tracker, abandon tracking (if template includes partial), demo assets on demo._

### 6.2 Dev / test-only (legacy script **usage**)

- **`main.py`** — **`_DEV_LEGACY_WIDGET_HARNESS_HTML`** → **`GET /dev/widget-test`**, **`GET /dev/widget-test/cart`** (**`ENV=development`** only via **`no_dev_in_production`** — **not** in **`_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`**).
- **`tests/**`** — multiple files **`read_text`** **`static/cartflow_widget.js`** or assert HTML **omits** legacy on **`/demo/store`**

### 6.3 Still required today for rollback / QA

- **`static/cartflow_widget.js`** — **non-V2** **`widget_loader`** path
- **`widget_loader.js`** legacy branch + duplicate-guard strings for **`cartflow_widget.js`**
- **Static tests** coupled to monolith file contents (**F** until rewritten to V2 sources)
- **Operational** checks over **`cartflow_widget.js`** (**F**)

### 6.4 VIP

- **VIP flag** still maintained in **`window.cartflowState`** via **`mirrorCartTotals()`** inside V2 **`flows.js`**.
- **VIP no longer pulls in** legacy **`cartflow_widget.js`** automatically from layered code. Merchants relying **only** on legacy behavior must keep **`CARTFLOW_WIDGET_RUNTIME_V2`** unset/false in embed until they accept full V2 UX.

### 6.5 Dev legacy widget harness (**isolated** — **not production cleanup path**)

Complete inventory (HTML harness only — **no** **`widget_loader`** / **no** **`cartflow_widget_runtime`**):

| URL | Behaviour |
|-----|-----------|
| **`GET /dev/widget-test`** | Serves **`_DEV_LEGACY_WIDGET_HARNESS_HTML`**. Visible banner + **`data-cf-dev-legacy-widget-harness`** mark page as **[CartFlow DEV ONLY]**. Script tag **`/static/cartflow_widget.js`**. |
| **`GET /dev/widget-test/cart`** | Same HTML body (**URL variant**); client **`history.replaceState`** may normalize path to **`/dev/widget-test/cart`**. |

**Production / shipped non-dev:**

- Middleware **`no_dev_in_production`** returns **`404`** for these paths whenever **`ENV` ≠ `development`**.
- Paths are **explicitly excluded** from **`_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`** (see comment in **`main.py`** next to the frozenset).
- **`/demo/store*`** (**unchanged**) remains the canonical **layered V2** storefront demo; do **not** use **`/dev/widget-test`** as a substitute.

**Safely delete harness later:** only after audit priority **4** (**`cartflow_widget.js`**) roadmap; **not deleted** in this milestone (**Audit §5**).

---

## 7. Risks before deleting `cartflow_widget.js`

1. **Embeds without V2 flag** still load legacy via **`widget_loader.js`**.
2. **Regression tests** and **operational observability** scrape monolith markers.
3. ~~**`/dev/widget-test`**~~ — **Controlled:** served only when **`ENV=development`** (**not** production-allowlisted). Still loads legacy inline for QA; **`/demo/store`** remains **primary V2** storefront preview.
4. **Rollback** strategy for misconfigured storefronts disappears if loader legacy branch removed first.

---

## 8. Recommended future order (cleanup execution)

Same spirit as rev 1 — updated for isolation:

1. ~~Refresh **documentation** (`SYSTEM_SUMMARY`, risk reports).~~ — **Tier 1 done**
2. ~~Expose dev tooling~~ — **`/dev/widget-test*`** **isolated** from production allowlist + labelled HTML (**`chore isolate legacy widget dev harness`**); optional future: second route with **`widget_loader` + V2** for parity.
3. **Merchant embed defaults**:** document **`CARTFLOW_WIDGET_RUNTIME_V2 = true`** in **`general_settings.html`** snippets.
4. **Migrate tests** toward **`cartflow_widget_runtime`** where behavior moved.
5. Remove **`widget_loader`** legacy branch when **no** production consumer needs it.
6. Archive or delete **`cartflow_widget.js`** last.

---

## 9. Verification commands

```bash
pytest tests/test_cartflow_widget_layered_runtime.py tests/test_cartflow_widget_shell_lifecycle.py -q
pytest tests/test_demo_behavioral_navigation.py -q
```

**Manual:** **`/demo/store`** — Network shows **`cartflow_widget_runtime/cartflow_widget_loader.js`** + module chain; **no** **`cartflow_widget.js`**.

---

## 10. Disclaimer — this commit boundary

**Isolation chore:** **`main.py`** (`_DEV_LEGACY_WIDGET_HARNESS_HTML`, **`dev_widget_test`** docstring, comment beside **`_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`**), **`tests/test_cartflow_production_readiness.py`**, **`services/cartflow_production_readiness.py`** (parity comment), **`SYSTEM_SUMMARY`**, **`docs/cartflow_production_readiness.md`**, **`widget_legacy_cleanup_audit.md`**. Unchanged: **`templates/demo_store.html`**, **`cartflow_widget_runtime/**`**, **`cart_abandon_tracking.js`**, **`cartflow_return_tracker.js`**, recovery / lifecycle / WhatsApp. **`widget_loader`** legacy branch + **`cartflow_widget.js`** unchanged.
