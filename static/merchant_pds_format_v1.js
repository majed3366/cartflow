/**
 * Product Design System Compliance V1 — shared merchant presentation helpers.
 * Presentation only: currency format + governed language sanitization.
 */
(function () {
  "use strict";

  var SAR_SUFFIX = "\u00a0ر.س";

  function formatMerchantSar(amount) {
    var n = Math.round(parseFloat(amount) || 0);
    if (isNaN(n)) return "";
    return n.toLocaleString("en-US") + SAR_SUFFIX;
  }

  function formatMerchantSarHtml(amount) {
    var text = formatMerchantSar(amount);
    if (!text) return "";
    return (
      '<span class="cf-currency-atom cftyp-currency" data-cf-currency="1">' +
      text +
      "</span>"
    );
  }

  /** Client-side guard for rejected Merchant Language strings (display layer). */
  function sanitizeMerchantLanguage(text) {
    var s = String(text == null ? "" : text).trim();
    if (!s) return "";
    if (/اكتملت\s*مشتريات/.test(s)) return "عادوا وأكملوا الشراء";
    return s;
  }

  window.formatMerchantSar = formatMerchantSar;
  window.formatMerchantSarHtml = formatMerchantSarHtml;
  window.sanitizeMerchantLanguage = sanitizeMerchantLanguage;
})();
