/* Merchant Session Identity Panel V1 — account verification (desktop + mobile). */
(function () {
  "use strict";

  var PANEL_ID = "ma-account-identity-panel";
  var BTN_ID = "ma-gtb-account-btn";
  var lastPayload = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function dashboardStoreSlug() {
    try {
      var sum =
        window.__cfLastSummaryForSituations ||
        window.__cfLastDashboardSummary ||
        null;
      if (sum && sum.store_slug) return String(sum.store_slug).trim();
    } catch (e) {}
    try {
      if (window.CARTFLOW_STORE_SLUG)
        return String(window.CARTFLOW_STORE_SLUG).trim();
    } catch (e2) {}
    return "";
  }

  function ensurePanel() {
    var existing = byId(PANEL_ID);
    if (existing) return existing;
    var wrap = document.createElement("div");
    wrap.id = PANEL_ID;
    wrap.className = "ma-account-identity";
    wrap.hidden = true;
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-modal", "true");
    wrap.setAttribute("aria-label", "هوية الحساب");
    wrap.innerHTML =
      '<div class="ma-account-identity__backdrop" data-ma-identity-close="1"></div>' +
      '<div class="ma-account-identity__card">' +
      '<header class="ma-account-identity__hdr">' +
      "<h2>هوية الحساب</h2>" +
      '<button type="button" class="ma-account-identity__close" data-ma-identity-close="1" aria-label="إغلاق">×</button>' +
      "</header>" +
      '<p class="ma-account-identity__review" id="ma-identity-review-label"></p>' +
      '<div class="ma-account-identity__body" id="ma-identity-body"></div>' +
      '<div class="ma-account-identity__check" id="ma-identity-check" aria-live="polite"></div>' +
      "</div>";
    document.body.appendChild(wrap);
    wrap.addEventListener("click", function (ev) {
      var t = ev.target;
      if (t && t.getAttribute && t.getAttribute("data-ma-identity-close")) {
        closePanel();
      }
    });
    return wrap;
  }

  function row(label, value, opts) {
    opts = opts || {};
    var cls = "ma-account-identity__row";
    if (opts.mono) cls += " ma-account-identity__row--mono";
    return (
      '<div class="' +
      cls +
      '"><span class="ma-account-identity__k">' +
      esc(label) +
      '</span><span class="ma-account-identity__v">' +
      esc(value) +
      "</span></div>"
    );
  }

  function paint(payload) {
    lastPayload = payload || {};
    var body = byId("ma-identity-body");
    var check = byId("ma-identity-check");
    var review = byId("ma-identity-review-label");
    if (!body || !check) return;

    if (review) {
      review.textContent =
        (payload && payload.review_label_ar) ||
        "هذا هو الحساب قيد المراجعة حالياً";
      review.hidden = !(payload && payload.authenticated);
    }

    if (!payload || !payload.ok) {
      body.innerHTML =
        '<p class="ma-account-identity__empty">تعذر قراءة هوية الجلسة. سجّل الدخول ثم أعد المحاولة.</p>';
      check.innerHTML = "";
      return;
    }

    var html = "";
    html += row("اسم التاجر", payload.merchant_name || "—");
    html += row("البريد", payload.merchant_email || "—");
    html += row("اسم المتجر", payload.store_name || "—");
    html += row("معرّف المتجر", payload.store_slug || "—", { mono: true });
    if (payload.merchant_id != null) {
      html += row("معرّف التاجر", String(payload.merchant_id), { mono: true });
    }
    html += row("منصة التجارة", payload.commerce_provider || "—");
    html += row("حالة الربط", payload.connection_status || "—");
    html += row("البيئة", payload.environment || "—");
    html += row(
      "بصمة الجلسة",
      payload.session_fingerprint || "—",
      { mono: true }
    );
    html += row(
      payload.last_sign_in_label_ar || "وقت بدء الجلسة الحالية",
      payload.last_sign_in_at || "—"
    );
    body.innerHTML = html;

    var c = payload.consistency || {};
    var ok = !!c.ok;
    var msg = c.message_ar || "";
    var action = "";
    if (!ok && c.action_ar && c.action_href) {
      action =
        '<p class="ma-account-identity__action"><a class="ma-account-identity__cta" href="' +
        esc(c.action_href) +
        '">' +
        esc(c.action_ar) +
        " ←</a></p>";
    }
    check.className =
      "ma-account-identity__check " +
      (ok
        ? "ma-account-identity__check--ok"
        : "ma-account-identity__check--bad");
    check.innerHTML =
      '<p class="ma-account-identity__check-msg">' + esc(msg) + "</p>" + action;
  }

  function openPanel() {
    var panel = ensurePanel();
    panel.hidden = false;
    document.body.classList.add("ma-account-identity-open");
    var btn = byId(BTN_ID);
    if (btn) btn.setAttribute("aria-expanded", "true");
    paint({ ok: false });
    var slug = dashboardStoreSlug();
    var url =
      "/api/merchant/session-identity?dashboard_store_slug=" +
      encodeURIComponent(slug) +
      "&_=" +
      Date.now();
    fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json().catch(function () {
          return { ok: false };
        });
      })
      .then(function (j) {
        paint(j || { ok: false });
      })
      .catch(function () {
        paint({ ok: false });
      });
  }

  function closePanel() {
    var panel = byId(PANEL_ID);
    if (panel) panel.hidden = true;
    document.body.classList.remove("ma-account-identity-open");
    var btn = byId(BTN_ID);
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  function togglePanel() {
    var panel = byId(PANEL_ID);
    if (panel && !panel.hidden) closePanel();
    else openPanel();
  }

  function bind() {
    var btn = byId(BTN_ID);
    if (!btn || btn.getAttribute("data-ma-identity-bound") === "1") return;
    btn.setAttribute("data-ma-identity-bound", "1");
    btn.setAttribute("aria-haspopup", "dialog");
    btn.setAttribute("aria-expanded", "false");
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      togglePanel();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") closePanel();
    });
  }

  window.maOpenAccountIdentityPanel = openPanel;
  window.maCloseAccountIdentityPanel = closePanel;
  window.maGetAccountIdentityLastPayload = function () {
    return lastPayload;
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
