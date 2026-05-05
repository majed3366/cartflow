/**
 * يحمّل ‎cartflow_widget.js‎ بعد اكتمال الصفحة. صفحات ‎/demo/*‎ (مثل ‎/demo/store‎) تُعرَف عبر ‎isCartPage()‎.
 */
(function () {
  "use strict";

  function cartflowLoaderPerfDemoDevLog(line) {
    try {
      var p = window.location.pathname || "";
      if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
        console.log(line);
      }
    } catch (eL) {}
  }

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
    try {
      if (window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ === true) {
        cartflowLoaderPerfDemoDevLog(
          "[CF PERF] widget loader skipped duplicate"
        );
        return;
      }
    } catch (eAct) {}

    try {
      var scripts = document.getElementsByTagName("script");
      var si;
      for (si = 0; si < scripts.length; si++) {
        var prevSrc = scripts[si].getAttribute("src") || "";
        if (prevSrc.indexOf("/static/cartflow_widget.js") >= 0) {
          cartflowLoaderPerfDemoDevLog(
            "[CF PERF] widget loader skipped duplicate"
          );
          window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
          return;
        }
      }
    } catch (eScr) {}

    window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
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
