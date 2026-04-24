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
    w.setAttribute("data-cartflow-bubble", "1");
    w.style.cssText =
      "position:fixed;right:12px;bottom:12px;z-index:2147483640;max-width:260px;" +
      "padding:10px 12px;border-radius:12px;background:#1e1b4b;color:#f5f3ff;" +
      "font:14px/1.4 system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.2);" +
      "pointer-events:auto;touch-action:manipulation;isolation:isolate;";

    var btnStyle =
      "cursor:pointer;border:0;border-radius:8px;padding:6px 14px;font:inherit;" +
      "font-weight:600;background:#7c3aed;color:#fff;";

    // يمنع السرقة من مستمعي النقر على ‎body/document‎ بعد أن يتصاعد من الزر
    w.addEventListener("click", function (ev) {
      ev.stopPropagation();
    }, false);

    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 8px 0;";
    p.textContent = "تبغى أساعدك تكمل طلبك؟ 👋";

    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "نعم";
    btn.setAttribute("aria-label", "نعم");
    btn.style.cssText = btnStyle;
    // مستمع واضح — ‎click‎ على الزر (مع إيقاف الانتشار)
    btn.addEventListener(
      "click",
      function onYes(ev) {
        if (w.getAttribute("data-cf-yes") === "1") return;
        w.setAttribute("data-cf-yes", "1");
        ev.stopPropagation();
        ev.preventDefault();
        console.log("user_interested");
        while (w.lastChild) {
          w.removeChild(w.lastChild);
        }
        var p2 = document.createElement("p");
        p2.style.cssText = "margin:0 0 8px 0;";
        p2.textContent = "تمام 👌 وش أكثر شيء متردد فيه؟";
        w.appendChild(p2);
        var row = document.createElement("div");
        row.style.cssText =
          "display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;";
        var bPrice = document.createElement("button");
        bPrice.type = "button";
        bPrice.textContent = "السعر";
        bPrice.style.cssText = btnStyle;
        bPrice.addEventListener("click", function (e) {
          e.stopPropagation();
          e.preventDefault();
          console.log("objection_price");
        });
        var bQ = document.createElement("button");
        bQ.type = "button";
        bQ.textContent = "الجودة";
        bQ.style.cssText = btnStyle;
        bQ.addEventListener("click", function (e) {
          e.stopPropagation();
          e.preventDefault();
          console.log("objection_quality");
        });
        row.appendChild(bPrice);
        row.appendChild(bQ);
        w.appendChild(row);
      },
      false
    );

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
