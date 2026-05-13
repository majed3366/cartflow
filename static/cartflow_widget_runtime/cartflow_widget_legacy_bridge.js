/**
 * Global compatibility + single entry after module chain load.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  window.__cartflowV2Bootstrap = function () {
    try {
      if (window.CartFlowRuntime) {
        window.CartFlowRuntime.widget = {
          runtime: "v2_layered",
          build: window.__cartflow_runtime_v2_build || null,
          loading: false,
        };
      }
    } catch (eRf) {}

    /** Chain into tracking cart sync hook after tracking script defined stub. */
    try {
      if (window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.Flows) {
        window.CartflowWidgetRuntime.Flows.start();
      }
    } catch (eSt) {}

    try {
      console.log(
        "[CARTFLOW WIDGET LEGACY_BRIDGE V2]",
        window.__cartflow_runtime_v2_build || ""
      );
    } catch (eLg) {}

    try {
      console.log("[CF V2 GLOBAL READY]", {
        runtime_exists: !!window.CartflowWidgetRuntime,
        modules: Object.keys(window.CartflowWidgetRuntime || {}),
      });
    } catch (eGr) {}
  };

  window.__cfV2ShowNow = function () {
    return window.CartflowWidgetRuntime?.Ui?.showBubble?.();
  };

  window.__cfV2Runtime = window.CartflowWidgetRuntime;

  var LegacyBridge = {
    version: "1",
    bootstrap: window.__cartflowV2Bootstrap,
  };
  window.CartflowWidgetRuntime.LegacyBridge = LegacyBridge;

  /** Rollback helpers (same names as legacy where safe). */
  window.cartflowDevMountProductViewAuto = window.cartflowDevMountProductViewAuto || function () {
    try {
      console.warn("[V2 stub] cartflowDevMountProductViewAuto — use layered flows or VIP legacy bridge");
    } catch (e) {}
  };
})();
