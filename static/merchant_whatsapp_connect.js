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

  function goBackWhatsapp() {
    if (window.goTo) {
      window.goTo("whatsapp");
    } else {
      window.location.href = "/dashboard#whatsapp";
    }
  }

  function renderConnectPage(block) {
    var root = byId("ma-wa-connect-root");
    if (!root) return;
    var b = block || {};
    var steps = b.steps_ar || [];
    var stepsHtml = "";
    if (b.show_steps && steps.length) {
      stepsHtml =
        '<ol class="ma-wa-connect-steps">' +
        steps
          .map(function (step) {
            return "<li>" + escHtml(step) + "</li>";
          })
          .join("") +
        "</ol>";
    }
    var statusHtml = "";
    if (b.show_status && b.status_ar) {
      statusHtml =
        '<div class="ma-wa-connect-status">' +
        '<span class="ma-wa-connect-status-k">' +
        escHtml(b.status_label_ar || "حالة الربط") +
        "</span>" +
        '<span class="ma-wa-connect-status-v">' +
        escHtml(b.status_ar) +
        "</span></div>";
    }
    var guidance = b.guidance_ar || b.body_ar || "";
    var primaryHtml = "";
    if (b.cta_primary_ar) {
      primaryHtml =
        '<button type="button" class="ma-fw-save ma-sc-btn-secondary ma-wa-connect-primary"' +
        ' id="ma-wa-connect-launch"' +
        (b.cta_primary_disabled ? " disabled" : "") +
        ">" +
        escHtml(b.cta_primary_ar) +
        "</button>";
      if (b.cta_primary_hint_ar) {
        primaryHtml +=
          '<p class="ma-fw-field-hint ma-wa-connect-primary-hint">' +
          escHtml(b.cta_primary_hint_ar) +
          "</p>";
      }
    }

    root.innerHTML =
      '<section class="ma-wa-connect-card setting-card ma-fw-card ma-wa-connect-commercial" dir="rtl">' +
      '<div class="setting-title">' +
      escHtml(b.headline_ar || "ربط واتساب أعمالك") +
      "</div>" +
      (b.intro_ar
        ? '<div class="setting-desc ma-wa-connect-intro">' + escHtml(b.intro_ar) + "</div>"
        : "") +
      statusHtml +
      (guidance ? '<p class="ma-wa-connect-guidance">' + escHtml(guidance) + "</p>" : "") +
      stepsHtml +
      primaryHtml +
      '<p class="ma-wa-connect-back">' +
      '<button type="button" class="ma-link-btn" id="ma-wa-connect-back">' +
      escHtml(b.cta_back_ar || "العودة إلى إعدادات واتساب") +
      "</button></p>" +
      "</section>";

    var backBtn = byId("ma-wa-connect-back");
    if (backBtn) {
      backBtn.addEventListener("click", goBackWhatsapp);
    }
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
        renderConnectPage((data && data.whatsapp_connect_page) || {});
      })
      .catch(function () {
        renderConnectPage({
          headline_ar: "ربط واتساب أعمالك",
          intro_ar: "تعذّر تحميل الصفحة.",
          guidance_ar: "حدّث الصفحة أو عد لاحقاً.",
          cta_back_ar: "العودة إلى إعدادات واتساب",
          show_status: false,
          show_steps: false,
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
