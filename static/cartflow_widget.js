/**
 * CartFlow — minimal cart helper bubble (no framework, no backend).
 * Injects after 3s; on /cart/* only; shows after 20s inactivity.
 */
(function () {
  "use strict";

  var ARM_DELAY_MS = 3000;
  var IDLE_MS = 20000;
  var shown = false;
  var idleTimer = null;
  var events = ["mousemove", "keydown", "scroll", "click", "touchstart"];

  function isCartPage() {
    return /\/cart/i.test(window.location.pathname + window.location.search);
  }

  function showBubble() {
    if (shown) return;
    shown = true;
    clearTimeout(idleTimer);
    events.forEach(function (e) {
      document.removeEventListener(e, resetIdle, true);
    });

    var w = document.createElement("div");
    w.setAttribute("dir", "rtl");
    w.setAttribute("lang", "ar");
    w.style.cssText =
      "position:fixed;right:12px;bottom:12px;z-index:2147483640;max-width:240px;" +
      "padding:10px 12px;border-radius:12px;background:#1e1b4b;color:#f5f3ff;" +
      "font:14px/1.4 system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.2);";

    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 8px 0;";
    p.textContent = "تبغى أساعدك تكمل طلبك؟ 👋";

    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "نعم";
    btn.style.cssText =
      "cursor:pointer;border:0;border-radius:8px;padding:6px 14px;font:inherit;" +
      "font-weight:600;background:#7c3aed;color:#fff;";
    btn.addEventListener("click", function () {
      console.log("user_interested");
    });

    w.appendChild(p);
    w.appendChild(btn);
    document.body.appendChild(w);
  }

  function resetIdle() {
    if (shown) return;
    clearTimeout(idleTimer);
    idleTimer = setTimeout(showBubble, IDLE_MS);
  }

  function arm() {
    if (!isCartPage()) return;
    events.forEach(function (e) {
      document.addEventListener(e, resetIdle, true);
    });
    resetIdle();
  }

  setTimeout(arm, ARM_DELAY_MS);
})();
