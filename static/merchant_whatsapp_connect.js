(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function escHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function renderPlaceholder(block) {
    var root = byId("ma-wa-connect-root");
    if (!root) return;
    var b = block || {};
    var statusAr = b.status_ar || "—";
    var nextAr = b.next_action_ar || "";
    var applicable = !!b.applicable;
    var foundation = b.foundation_only !== false;

    root.innerHTML =
      '<section class="ma-wa-connect-card setting-card ma-fw-card" dir="rtl">' +
      '<div class="setting-title">ربط واتساب المتجر</div>' +
      '<div class="setting-desc">Embedded Signup — تأسيس V1 (بدون إرسال بعد)</div>' +
      '<div class="setting-row"><span class="setting-label">الحالة</span>' +
      '<span class="setting-value">' +
      escHtml(statusAr) +
      "</span></div>" +
      (nextAr
        ? '<p class="ma-wa-connect-next">' + escHtml(nextAr) + "</p>"
        : "") +
      '<p class="ma-fw-field-hint ma-wa-connect-foundation">' +
      (foundation
        ? "هذه الصفحة placeholder — زر «Login with Facebook» واستبدال الرمز سيُفعّل في مرحلة لاحقة."
        : "") +
      "</p>" +
      '<button type="button" class="ma-fw-save ma-sc-btn-secondary" id="ma-wa-connect-launch" disabled' +
      ' title="قريباً — Embedded Signup V2">' +
      "ربط واتساب (قريباً)" +
      "</button>" +
      (!applicable
        ? '<p class="ma-fw-field-hint">مسار CartFlow Shared لا يستخدم Embedded Signup. ' +
          '<button type="button" class="ma-link-btn" onclick="if(window.goTo){goTo(\'whatsapp\');}">العودة إلى واتساب</button></p>'
        : '<p class="ma-fw-field-hint"><button type="button" class="ma-link-btn" onclick="if(window.goTo){goTo(\'whatsapp\');}">العودة إلى إعدادات واتساب</button></p>') +
      "</section>";
  }

  function loadConnectState() {
    var root = byId("ma-wa-connect-root");
    if (!root) return;
    root.setAttribute("aria-busy", "true");
    fetch("/api/recovery-settings?_=" + Date.now(), { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var block =
          (data && data.whatsapp_embedded_signup) ||
          (data && data.whatsapp_connection_readiness &&
            data.whatsapp_connection_readiness.whatsapp_embedded_signup) ||
          {};
        renderPlaceholder(block);
      })
      .catch(function () {
        renderPlaceholder({
          status_ar: "تعذّر تحميل الحالة",
          next_action_ar: "حدّث الصفحة أو عد لاحقاً.",
          applicable: true,
          foundation_only: true,
        });
      })
      .finally(function () {
        if (root) root.setAttribute("aria-busy", "false");
      });
  }

  window.maInitWhatsappConnectPage = function () {
    loadConnectState();
  };
})();
