/**
 * Global compatibility + single entry after module chain load.
 */
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
  };

  /** Rollback helpers (same names as legacy where safe). */
  window.cartflowDevMountProductViewAuto = window.cartflowDevMountProductViewAuto || function () {
    try {
      console.warn("[V2 stub] cartflowDevMountProductViewAuto — use layered flows or VIP legacy bridge");
    } catch (e) {}
  };
})();
