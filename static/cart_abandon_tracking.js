/**
 * تتبع السلة المتروكة على مستوى التطبيق — أي صفحة فيها ‎window.cart‎.
 */
(function () {
  "use strict";
  window.cart = window.cart || [];
  if (!Array.isArray(window.cart)) {
    window.cart = [];
  }
  if (typeof window.replyaiTrack !== "function") {
    window.replyaiTrack = function () {};
  }
  console.log("abandon tracking active");

  function apiCartEventUrl() {
    var base = (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
    return base ? base + "/api/cart-event" : "/api/cart-event";
  }

  function sendCartAbandonedToBackend(source) {
    var body = JSON.stringify({
      event: "cart_abandoned",
      source: source,
      cart: window.cart,
    });
    var url = apiCartEventUrl();
    var opts = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
    };
    if (source === "beforeunload") {
      opts.keepalive = true;
    }
    return fetch(url, opts)
      .then(function (r) {
        return r.json().then(function (j) {
          return { status: r.status, body: j };
        });
      })
      .then(function (response) {
        console.log("cart_abandoned backend response", response);
        return response;
      })
      .catch(function (err) {
        console.log("cart_abandoned backend response", err);
      });
  }

  function onCartAbandoned(source) {
    window.cart = window.cart || [];
    if (!Array.isArray(window.cart)) {
      window.cart = [];
    }
    if (window.cart.length === 0) {
      return;
    }
    console.log("cart_abandoned triggered");
    window.replyaiTrack({ event: "cart_abandoned" });
    console.log("sending cart_abandoned to backend");
    void sendCartAbandonedToBackend(source);
  }

  window.addEventListener("beforeunload", function () {
    onCartAbandoned("beforeunload");
  });
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      onCartAbandoned("visibility");
    }
  });
})();
