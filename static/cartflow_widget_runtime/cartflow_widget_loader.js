/**
 * Layered storefront widget bootstrap (additive).
 * Set window.CARTFLOW_WIDGET_RUNTIME_V2 = true before widget_loader loads this chain.
 *
 * Scripts load strictly one-after-one; bootstrap runs only after every module succeeds.
 */
(function () {
  "use strict";

  function resolveRuntimeModuleBase() {
    try {
      var root = window.__CARTFLOW_STATIC_ROOT__;
      if (root && String(root).trim()) {
        return String(root).replace(/\/+$/, "") + "/cartflow_widget_runtime/";
      }
    } catch (eRoot) {
      /* ignore */
    }
    try {
      var cur = document.currentScript;
      if (cur && cur.src) {
        var u = new URL(cur.src, window.location.href);
        return u.origin + u.pathname.replace(/[^/]+$/, "");
      }
    } catch (eCur) {
      /* ignore */
    }
    return "/static/cartflow_widget_runtime/";
  }

  var BASE = resolveRuntimeModuleBase();
    var RUNTIME_TAG = window.CARTFLOW_RUNTIME_VERSION || "layered-runtime-v20";
  try {
    if (/^\/demo\/store(?:\/|$)/i.test(String(window.location.pathname || ""))) {
      console.log("[CF V2 PRIMARY RUNTIME]", {
        layered: RUNTIME_TAG,
      });
    }
  } catch (ePri) {}

  /** Must match filesystem; order preserves dependencies between modules. */
  var MODULES = [
    "cartflow_widget_config.js",
    "cartflow_product_identity_capture.js",
    "cartflow_widget_fetch.js",
    "cartflow_widget_state.js",
    "cartflow_widget_theme.js",
    "cartflow_widget_triggers.js",
    "cartflow_storefront_cart_bridge_contract.js",
    "cartflow_storefront_cart_adapters.js",
    "cartflow_storefront_cart_bridge_core.js",
    "cartflow_cart_sources.js",
    "cartflow_cart_event_bridge.js",
    "cartflow_widget_phone.js",
    "cartflow_widget_shell.js",
    "cartflow_widget_ui.js",
    "cartflow_widget_flows.js",
    "cartflow_widget_legacy_bridge.js",
  ];

  window.__cartflow_runtime_v2_build = RUNTIME_TAG;

  // Additive, read-only widget health snapshot (Observability only).
  // Consumed by the runtime-truth beacon so Admin Operations → Widget Health
  // can detect module/bootstrap failures even when bootstrap is blocked.
  function widgetHealth() {
    try {
      if (!window.__cartflowWidgetHealth) {
        window.__cartflowWidgetHealth = {
          runtime_version: RUNTIME_TAG,
          module_load_status: "loading",
          loaded_modules: [],
          failed_modules: [],
          bootstrap_ready: false,
          bootstrap_blocked: false,
          missing_runtime_objects: [],
          updated_at: new Date().toISOString(),
        };
      }
      return window.__cartflowWidgetHealth;
    } catch (eWh) {
      return {};
    }
  }

  function setHealth(patch) {
    try {
      var h = widgetHealth();
      for (var k in patch) {
        if (Object.prototype.hasOwnProperty.call(patch, k)) {
          h[k] = patch[k];
        }
      }
      h.updated_at = new Date().toISOString();
      try {
        if (window.CartflowWidgetRuntime) {
          window.CartflowWidgetRuntime.__health = h;
        }
      } catch (eMir) {}
    } catch (eSh) {}
  }

  widgetHealth();

  function v2Log(tag, meta) {
    try {
      if (meta !== undefined && meta !== null) {
        console.log(tag, meta);
      } else {
        console.log(tag);
      }
    } catch (eL) {}
  }

  function getMissingNamespaces() {
    var R = window.CartflowWidgetRuntime;
    var need = [
      "Config",
      "Api",
      "State",
      "Theme",
      "Triggers",
      "Phone",
      "Shell",
      "Ui",
      "Flows",
      "LegacyBridge",
    ];
    if (!R || typeof R !== "object") {
      return [
        "CartflowWidgetRuntime (root)",
      ].concat(
        need.map(function (k) {
          return "CartflowWidgetRuntime." + k;
        })
      );
    }
    var missing = [];
    var i;
    for (i = 0; i < need.length; i++) {
      var k = need[i];
      if (!R[k] || typeof R[k] !== "object") {
        missing.push("CartflowWidgetRuntime." + k);
      }
    }
    if (!R.Flows || typeof R.Flows.start !== "function") {
      missing.push("CartflowWidgetRuntime.Flows.start (function)");
    }
    if (!R.Triggers || typeof R.Triggers.init !== "function") {
      missing.push("CartflowWidgetRuntime.Triggers.init (function)");
    }
    if (!R.Shell || typeof R.Shell.open !== "function") {
      missing.push("CartflowWidgetRuntime.Shell.open (function)");
    }
    if (!R.Shell || typeof R.Shell.setContent !== "function") {
      missing.push("CartflowWidgetRuntime.Shell.setContent (function)");
    }
    return missing;
  }

  function namespacesOk() {
    return getMissingNamespaces().length === 0;
  }

  function runBootstrap() {
    if (!namespacesOk()) {
      var missingNs = getMissingNamespaces();
      setHealth({ bootstrap_blocked: true, bootstrap_ready: false, missing_runtime_objects: missingNs });
      v2Log("[CF V2 BOOTSTRAP BLOCKED]", { missing: missingNs });
      return false;
    }
    v2Log("[CF V2 BOOTSTRAP START]", {});
    try {
      if (typeof window.__cartflowV2Bootstrap === "function") {
        window.__cartflowV2Bootstrap();
      } else {
        setHealth({ bootstrap_blocked: true, bootstrap_ready: false, missing_runtime_objects: ["__cartflowV2Bootstrap"] });
        v2Log("[CF V2 BOOTSTRAP BLOCKED]", {
          missing: ["__cartflowV2Bootstrap"],
        });
        return false;
      }
    } catch (eBo) {
      setHealth({ bootstrap_blocked: true, bootstrap_ready: false, last_runtime_error: String((eBo && eBo.message) || eBo || "bootstrap_error") });
      try {
        console.warn("[CF V2 BOOTSTRAP ERROR]", eBo);
      } catch (eW) {}
      return false;
    }
    setHealth({ bootstrap_ready: true, bootstrap_blocked: false });
    v2Log("[CF V2 BOOTSTRAP READY]", {});
    return true;
  }

  function loadIndex(i, chainOk) {
    chainOk = chainOk !== false;
    if (i >= MODULES.length) {
      var hEnd = widgetHealth();
      var anyFailed = (hEnd.failed_modules || []).length > 0;
      setHealth({
        module_load_status: anyFailed ? "failed" : "ok",
        missing_runtime_objects: getMissingNamespaces(),
      });
      v2Log("[CF V2 ALL MODULES LOADED]", { count: MODULES.length, chain_ok: chainOk });
      if (!namespacesOk()) {
        setHealth({ bootstrap_blocked: true, bootstrap_ready: false, missing_runtime_objects: getMissingNamespaces() });
        v2Log("[CF V2 BOOTSTRAP BLOCKED]", { missing: getMissingNamespaces() });
        return;
      }
      runBootstrap();
      return;
    }

    var name = MODULES[i];
    var s = document.createElement("script");
    s.async = false;
    s.src = BASE + name + "?v=" + encodeURIComponent(RUNTIME_TAG);
    s.onload = function () {
      try {
        widgetHealth().loaded_modules.push(name);
      } catch (eLm) {}
      v2Log("[CF V2 MODULE LOADED]", name);
      loadIndex(i + 1, chainOk);
    };
    s.onerror = function () {
      try {
        widgetHealth().failed_modules.push(name);
        setHealth({ module_load_status: "failed" });
      } catch (eFm) {}
      try {
        console.warn("[CF V2 MODULE FAILED]", name, "(continuing chain)");
      } catch (eWf) {}
      loadIndex(i + 1, chainOk);
    };

    try {
      (document.head || document.body || document.documentElement).appendChild(
        s
      );
    } catch (eApp) {
      try {
        widgetHealth().failed_modules.push(name);
        setHealth({ module_load_status: "failed" });
      } catch (eFm2) {}
      try {
        console.warn("[CF V2 MODULE FAILED]", name + " (append)", eApp);
      } catch (eWa) {}
      loadIndex(i + 1, chainOk);
    }
  }

  v2Log("[CF V2 LOAD START]", {
    runtime: RUNTIME_TAG,
    modules: MODULES.slice(),
  });
  loadIndex(0, true);
})();
