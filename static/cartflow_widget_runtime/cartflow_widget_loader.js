/**
 * Layered storefront widget bootstrap (additive).
 * Set window.CARTFLOW_WIDGET_RUNTIME_V2 = true before widget_loader loads this chain.
 *
 * Scripts load strictly one-after-one; bootstrap runs only after every module succeeds.
 */
(function () {
  "use strict";

  var BASE = "/static/cartflow_widget_runtime/";
    var RUNTIME_TAG = window.CARTFLOW_RUNTIME_VERSION || "layered-runtime-v17";
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
    "cartflow_widget_api.js",
    "cartflow_widget_state.js",
    "cartflow_widget_triggers.js",
    "cartflow_widget_phone.js",
    "cartflow_widget_shell.js",
    "cartflow_widget_ui.js",
    "cartflow_widget_flows.js",
    "cartflow_widget_legacy_bridge.js",
  ];

  window.__cartflow_runtime_v2_build = RUNTIME_TAG;

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
      v2Log("[CF V2 BOOTSTRAP BLOCKED]", { missing: getMissingNamespaces() });
      return false;
    }
    v2Log("[CF V2 BOOTSTRAP START]", {});
    try {
      if (typeof window.__cartflowV2Bootstrap === "function") {
        window.__cartflowV2Bootstrap();
      } else {
        v2Log("[CF V2 BOOTSTRAP BLOCKED]", {
          missing: ["__cartflowV2Bootstrap"],
        });
        return false;
      }
    } catch (eBo) {
      try {
        console.warn("[CF V2 BOOTSTRAP ERROR]", eBo);
      } catch (eW) {}
      return false;
    }
    v2Log("[CF V2 BOOTSTRAP READY]", {});
    return true;
  }

  function loadIndex(i, chainOk) {
    chainOk = chainOk !== false;
    if (!chainOk) {
      return;
    }
    if (i >= MODULES.length) {
      v2Log("[CF V2 ALL MODULES LOADED]", { count: MODULES.length });
      if (!namespacesOk()) {
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
      v2Log("[CF V2 MODULE LOADED]", name);
      loadIndex(i + 1, true);
    };
    s.onerror = function () {
      v2Log("[CF V2 MODULE FAILED]", name);
      loadIndex(i + 1, false);
    };

    try {
      (document.head || document.body || document.documentElement).appendChild(
        s
      );
    } catch (eApp) {
      v2Log("[CF V2 MODULE FAILED]", name + " (append)");
      loadIndex(i + 1, false);
    }
  }

  v2Log("[CF V2 LOAD START]", {
    runtime: RUNTIME_TAG,
    modules: MODULES.slice(),
  });
  loadIndex(0, true);
})();
