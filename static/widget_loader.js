/**
 * يحمّل ‎cartflow_widget.js‎ بعد اكتمال الصفحة. صفحات ‎/demo/*‎ (مثل ‎/demo/store‎) تُعرَف عبر ‎isCartPage()‎.
 */
(function () {
  "use strict";

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
    s.src = "/static/cartflow_widget.js";
    s.async = true;
    (document.body || document.documentElement).appendChild(s);
  }

  if (document.readyState === "complete") {
    loadWidget();
  } else {
    window.addEventListener("load", loadWidget);
  }
})();
