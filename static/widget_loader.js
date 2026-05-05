/**
 * يحمّل ‎cartflow_widget.js‎ بعد اكتمال الصفحة. صفحات ‎/demo/*‎ (مثل ‎/demo/store‎) تُعرَف عبر ‎isCartPage()‎.
 */
(function () {
  "use strict";

  window.__cartflow_loader_build = "vip-runtime-loader-v1";
  try {
    console.log("[CARTFLOW LOADER BUILD]", window.__cartflow_loader_build);
  } catch (eLb) {}

  function cartflowBlockWidgetAfterConversion() {
    try {
      if (
        typeof window.cartflowIsSessionConverted === "function" &&
        window.cartflowIsSessionConverted()
      ) {
        return true;
      }
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (e) {
      return false;
    }
  }

  function loadWidget() {
    if (cartflowBlockWidgetAfterConversion()) {
      return;
    }
    var s = document.createElement("script");
    s.src = "/static/cartflow_widget.js?v=vip-runtime-state-v1";
    s.async = true;
    (document.body || document.documentElement).appendChild(s);
  }

  if (document.readyState === "complete") {
    loadWidget();
  } else {
    window.addEventListener("load", loadWidget);
  }
})();
