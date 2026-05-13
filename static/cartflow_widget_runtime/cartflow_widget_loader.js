/**
 * Layered storefront widget bootstrap (additive).
 * Set window.CARTFLOW_WIDGET_RUNTIME_V2 = true before widget_loader loads this chain.
 *
 * Sequential load order — no bundler dependency.
 */
(function () {
  "use strict";

  var BASE = "/static/cartflow_widget_runtime/";
  var RUNTIME_TAG = window.CARTFLOW_RUNTIME_VERSION || "layered-runtime-v1";
  window.__cartflow_runtime_v2_build = RUNTIME_TAG;

  var CHAIN = [
    "cartflow_widget_config.js",
    "cartflow_widget_api.js",
    "cartflow_widget_state.js",
    "cartflow_widget_triggers.js",
    "cartflow_widget_ui.js",
    "cartflow_widget_phone.js",
    "cartflow_widget_flows.js",
    "cartflow_widget_legacy_bridge.js",
  ];

  function appendScript(idx) {
    if (idx >= CHAIN.length) {
      try {
        if (typeof window.__cartflowV2Bootstrap === "function") {
          window.__cartflowV2Bootstrap();
        }
      } catch (eBo) {
        try {
          console.warn("[CartflowWidgetRuntimeV2]", eBo);
        } catch (eL) {}
      }
      return;
    }
    var name = CHAIN[idx];
    var prev = window.__cartflow_runtime_v2_last_script;
    if (prev === name) {
      appendScript(idx + 1);
      return;
    }
    window.__cartflow_runtime_v2_last_script = name;
    var s = document.createElement("script");
    s.async = false;
    s.src = BASE + name + "?v=" + encodeURIComponent(RUNTIME_TAG);
    s.onload = function () {
      appendScript(idx + 1);
    };
    s.onerror = function () {
      try {
        console.warn("[CartflowWidgetRuntimeV2] script_load_failed", name);
      } catch (eW) {}
      appendScript(idx + 1);
    };
    (document.head || document.body || document.documentElement).appendChild(s);
  }

  appendScript(0);
})();
