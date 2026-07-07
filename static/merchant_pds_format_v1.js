/**
 * Product Design System Compliance V1 — shared merchant presentation helpers.
 * Presentation only: currency format + governed language sanitization.
 */
(function () {
  "use strict";

  function formatMerchantSar(amount) {
    var n = Math.round(parseFloat(amount) || 0);
    if (isNaN(n)) return "";
    return n.toLocaleString("en-US") + " ر.س";
  }

  /** Client-side guard for rejected Merchant Language strings (display layer). */
  function sanitizeMerchantLanguage(text) {
    var s = String(text == null ? "" : text).trim();
    if (!s) return "";
    if (/اكتملت\s*مشتريات/.test(s)) return "عادوا وأكملوا الشراء";
    return s;
  }

  window.formatMerchantSar = formatMerchantSar;
  window.sanitizeMerchantLanguage = sanitizeMerchantLanguage;
})();
