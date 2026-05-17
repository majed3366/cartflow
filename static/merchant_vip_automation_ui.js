/* VIP dashboard actions — driven by merchant_automation_mode (UI only). */
(function () {
  "use strict";

  var mode = "manual";
  var lastVipPayload = null;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function normalizeMode(raw) {
    var v = String(raw || "manual").trim().toLowerCase();
    if (v === "assistant" || v === "assist" || v === "مساعد") return "assistant";
    if (v === "auto" || v === "automatic" || v === "تلقائي") return "auto";
    return "manual";
  }

  function statusLineForAuto(vr) {
    if (!vr || !vr.has_phone) return "بانتظار الوقت المناسب";
    var n = parseInt(vr.amount_display, 10) || 0;
    if (n % 3 === 0) return "أرسل تنبيه VIP";
    if (n % 3 === 1) return "بانتظار الوقت المناسب";
    return "توقف: العميل عاد";
  }

  function stateFromSubtitle(sub) {
    var s = String(sub || "").trim();
    if (!s) return "لم يعد العميل";
    var parts = s.split("•");
    if (parts.length > 1) return parts[parts.length - 1].trim() || s;
    return s;
  }

  function renderTableAction(vr) {
    var href = vr.contact_href || "";
    var m = normalizeMode(mode);
    if (m === "manual") {
      var btn = href
        ? '<a class="va-btn" href="' +
          esc(href) +
          '" rel="noopener noreferrer">تواصل يدوي (VIP) ←</a>'
        : '<span class="va-btn is-disabled">تواصل يدوي (VIP) ←</span>';
      return (
        '<div class="ma-vip-action-wrap">' +
        btn +
        '<div class="ma-vip-action-desc">أنت تراجع وتتواصل بنفسك</div></div>'
      );
    }
    if (m === "assistant") {
      var disabled = !href
        ? ' disabled aria-disabled="true"'
        : "";
      var btn2 =
        '<button type="button" class="va-btn ma-vip-suggest-btn"' +
        disabled +
        ' data-contact-href="' +
        esc(href) +
        '" data-amount="' +
        esc(vr.amount_display) +
        '" data-subtitle="' +
        esc(vr.subtitle_ar) +
        '">اقتراح متابعة (VIP)</button>';
      return (
        '<div class="ma-vip-action-wrap">' +
        btn2 +
        '<div class="ma-vip-action-desc">يعرض النظام اقتراحاً قبل المتابعة</div></div>'
      );
    }
    return (
      '<div class="ma-vip-auto-wrap">' +
      '<div class="ma-vip-auto-head">يتابع النظام حسب إعداداتك</div>' +
      '<div class="ma-vip-auto-status">' +
      esc(statusLineForAuto(vr)) +
      "</div></div>"
    );
  }

  function renderCompactBtn(vr, className, arrow) {
    var href = vr.contact_href || "";
    var m = normalizeMode(mode);
    var cls = className || "va-btn";
    var suffix = arrow ? " ←" : "";
    if (m === "manual") {
      return href
        ? '<a class="' + cls + '" href="' + esc(href) + '">تواصل يدوي (VIP)' + suffix + "</a>"
        : '<span class="' + cls + ' is-disabled">تواصل يدوي (VIP)' + suffix + "</span>";
    }
    if (m === "assistant") {
      return (
        '<button type="button" class="' +
        cls +
        ' ma-vip-suggest-btn" data-contact-href="' +
        esc(href) +
        '" data-amount="' +
        esc(vr.amount_display) +
        '" data-subtitle="' +
        esc(vr.subtitle_ar) +
        '"' +
        (href ? "" : ' disabled aria-disabled="true"') +
        ">اقتراح متابعة (VIP)" +
        suffix +
        "</button>"
      );
    }
    return (
      '<span class="ma-vip-auto-inline"><span class="ma-vip-auto-head">يتابع النظام حسب إعداداتك</span> — ' +
      esc(statusLineForAuto(vr)) +
      "</span>"
    );
  }

  function updatePageHints() {
    var helper = byId("ma-vip-automation-helper");
    if (helper) helper.style.display = "";
    var detail = byId("ma-vip-alert-dynamic");
    if (!detail) return;
    var m = normalizeMode(mode);
    if (m === "manual") {
      detail.textContent =
        "النظام لا يُرسل سلسلة واتساب آلية لهذه السلال — استخدم «تواصل يدوي (VIP)» للوصول للعميل مباشرة.";
    } else if (m === "assistant") {
      detail.textContent =
        "وضع مساعد: اضغط «اقتراح متابعة» لمراجعة الاقتراح قبل فتح واتساب.";
    } else {
      detail.textContent =
        "وضع تلقائي (عرض فقط): يُظهر الحالة دون تنفيذ تلقائي بعد.";
    }
  }

  function closeSuggestPanel() {
    var panel = byId("ma-vip-suggest-panel");
    if (panel) panel.style.display = "none";
  }

  function openSuggestPanel(vr) {
    var panel = byId("ma-vip-suggest-panel");
    if (!panel) return;
    var href = (vr && vr.contact_href) || "";
    panel.setAttribute("data-contact-href", href);
    var amt = (vr && vr.amount_display) || "";
    setText("ma-vip-suggest-amount", amt ? amt + " ريال" : "—");
    setText("ma-vip-suggest-state", stateFromSubtitle(vr && vr.subtitle_ar));
    setText("ma-vip-suggest-action", "تواصل خلال 15 دقيقة");
    panel.style.display = "";
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) el.textContent = t == null ? "" : String(t);
  }

  function bindSuggestPanelOnce() {
    var panel = byId("ma-vip-suggest-panel");
    if (!panel || panel.getAttribute("data-bound") === "1") return;
    panel.setAttribute("data-bound", "1");
    var dismiss = panel.querySelector(".ma-vip-suggest-dismiss");
    if (dismiss) {
      dismiss.addEventListener("click", function () {
        closeSuggestPanel();
      });
    }
    var ignore = byId("ma-vip-suggest-ignore");
    if (ignore) {
      ignore.addEventListener("click", function () {
        closeSuggestPanel();
      });
    }
    var approve = byId("ma-vip-suggest-approve");
    if (approve) {
      approve.addEventListener("click", function () {
        var href = panel.getAttribute("data-contact-href") || "";
        closeSuggestPanel();
        if (href) window.open(href, "_blank", "noopener,noreferrer");
      });
    }
    panel.addEventListener("click", function (e) {
      if (e.target === panel) closeSuggestPanel();
    });
  }

  function bindDelegatedClicks() {
    if (document.body.getAttribute("data-ma-vip-automation-clicks") === "1") return;
    document.body.setAttribute("data-ma-vip-automation-clicks", "1");
    document.body.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var btn = t.closest(".ma-vip-suggest-btn");
      if (!btn || btn.disabled) return;
      e.preventDefault();
      openSuggestPanel({
        contact_href: btn.getAttribute("data-contact-href") || "",
        amount_display: btn.getAttribute("data-amount") || "",
        subtitle_ar: btn.getAttribute("data-subtitle") || "",
      });
    });
  }

  function rerenderFromCache() {
    if (lastVipPayload && typeof window.maApplyVipCartsPayload === "function") {
      window.maApplyVipCartsPayload(lastVipPayload);
    }
  }

  function syncFromCachedVipCarts() {
    if (lastVipPayload && lastVipPayload.merchant_automation_mode) {
      mode = normalizeMode(lastVipPayload.merchant_automation_mode);
    }
    updatePageHints();
    rerenderFromCache();
  }

  window.maVipAutomation = {
    getMode: function () {
      return normalizeMode(mode);
    },
    setMode: function (m) {
      mode = normalizeMode(m);
      updatePageHints();
    },
    syncFromCachedVipCarts: syncFromCachedVipCarts,
    renderTableAction: renderTableAction,
    renderHomeItemBtn: function (vr) {
      return renderCompactBtn(vr, "vbtn", false);
    },
    renderBannerBtn: function (ban) {
      if (!ban) return "";
      return renderCompactBtn(
        { contact_href: ban.contact_href, amount_display: "", subtitle_ar: ban.amount_line, has_phone: !!ban.contact_href },
        "va-btn",
        true
      );
    },
    storePayload: function (d) {
      lastVipPayload = d;
    },
    rerenderFromCache: rerenderFromCache,
    bind: function () {
      bindSuggestPanelOnce();
      bindDelegatedClicks();
      updatePageHints();
    },
  };

  bindSuggestPanelOnce();
  bindDelegatedClicks();
})();
