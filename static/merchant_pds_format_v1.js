/**
 * Product Design System Compliance V1 — shared merchant presentation helpers.
 * Presentation only: currency format + governed language sanitization.
 */
(function () {
  "use strict";

  var SAR_PREFIX = "SR\u00a0";

  function formatMerchantSar(amount) {
    var n = Math.round(parseFloat(String(amount == null ? "" : amount).replace(/,/g, "")) || 0);
    if (isNaN(n)) return "";
    return SAR_PREFIX + n.toLocaleString("en-US");
  }

  function formatMerchantSarHtml(amount) {
    var text = formatMerchantSar(amount);
    if (!text) return "";
    return (
      '<span class="cf-currency-atom cftyp-currency" data-cf-currency="1" dir="ltr">' +
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
