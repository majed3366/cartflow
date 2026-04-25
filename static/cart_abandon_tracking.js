/**
 * تتبع السلة المتروكة على مستوى التطبيق — أي صفحة فيها ‎window.cart‎.
 */
(function () {
  "use strict";
  if (typeof window.cart === "undefined" || window.cart === null) {
    window.cart = [];
  }
  if (typeof window.replyaiTrack !== "function") {
    window.replyaiTrack = function () {};
  }
  console.log("abandon tracking active");
  window.addEventListener("beforeunload", function () {
    if (window.cart && window.cart.length > 0) {
      console.log("cart_abandoned triggered (beforeunload)");
      window.replyaiTrack({ event: "cart_abandoned" });
    }
  });
  document.addEventListener("visibilitychange", function () {
    if (document.hidden && window.cart && window.cart.length > 0) {
      console.log("cart_abandoned triggered (visibility)");
      window.replyaiTrack({ event: "cart_abandoned" });
    }
  });
})();
