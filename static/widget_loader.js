/**
 * يحمّل ‎cartflow_widget.js‎ بعد اكتمال الصفحة. يضبط المسار ليشمل ‎/cart‎
 * حتى يعمل ‎isCartPage()‎ في الويدجت دون تعديل ملف الويدجت.
 */
(function () {
  "use strict";

  function loadWidget() {
    try {
      var p = (location.pathname || "").replace(/\/$/, "") || "/";
      if (p === "/demo/store") {
        history.replaceState(null, "", "/demo/store/cart");
      }
    } catch (e) {
      /* ignore */
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
