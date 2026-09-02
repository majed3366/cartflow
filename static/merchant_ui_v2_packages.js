/**
 * Merchant UI V2 — Packages experience (authoritative catalog only).
 * GET /api/merchant/plans-catalog — read-only; no fake purchase CTA.
 */
(function () {
  "use strict";

  var loaded = false;
  var loading = false;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function subscriptionFrom(payload) {
    if (!payload || typeof payload !== "object") return null;
    return (
      (payload.subscription && typeof payload.subscription === "object"
        ? payload.subscription
        : null) ||
      (payload.ok && payload.current_plan ? payload : null)
    );
  }

  function catalogFrom(payload) {
    if (!payload || typeof payload !== "object") return null;
    var c = payload.catalog;
    if (c && typeof c === "object" && Array.isArray(c.plans)) return c;
    if (Array.isArray(payload.plans)) {
      return {
        plans: payload.plans,
        read_only: payload.read_only !== false,
        billing_available: !!payload.billing_available,
        upgrade_available: !!payload.upgrade_available,
        footnote_ar: payload.footnote_ar || "",
      };
    }
    return null;
  }

  function render(root, payload) {
    var sub = subscriptionFrom(payload);
    var cat = catalogFrom(payload);
    var planId =
      (sub && (sub.current_plan || sub.plan_id || sub.plan)) || "";
    var planLabel =
      (sub &&
        (sub.current_plan_label_ar ||
          sub.plan_label_ar ||
          sub.plan_name_ar ||
          planId)) ||
      "—";
    var status =
      (sub &&
        (sub.plan_status_label_ar ||
          sub.status_badge_label_ar ||
          sub.plan_status)) ||
      "";
    var billingOk = !!(cat && cat.billing_available);
    var upgradeOk = !!(cat && cat.upgrade_available);
    var footnote =
      (cat && cat.footnote_ar) ||
      "عرض للمقارنة فقط — الترقية والدفع غير متاحين من لوحة التحكم حالياً.";

    var cards = "";
    var plans = (cat && cat.plans) || [];
    var i;
    for (i = 0; i < plans.length; i++) {
      var p = plans[i] || {};
      var id = String(p.plan_id || "");
      var isCurrent = id && id === String(planId);
      var feats = Array.isArray(p.features_ar) ? p.features_ar : [];
      var featLis = feats
        .slice(0, 8)
        .map(function (f) {
          return "<li>" + esc(f) + "</li>";
        })
        .join("");
      var priceBits = [];
      if (p.monthly_label_ar) priceBits.push(String(p.monthly_label_ar));
      if (p.annual_label_ar) priceBits.push(String(p.annual_label_ar));
      var priceHtml = priceBits.length
        ? '<p class="cf2-plan-card__price">' +
          esc(priceBits.join(" · ")) +
          '<br><span style="font-size:0.75rem">مصدر السعر: كتالوج CartFlow للقراءة فقط</span></p>'
        : '<p class="cf2-plan-card__price">السعر غير معروض كفاتورة شراء</p>';
      var actionHtml = isCurrent
        ? '<p class="cf2-plan-card__action">باقتك الحالية</p>'
        : upgradeOk && billingOk
          ? '<p class="cf2-plan-card__action">الترقية متاحة عبر مسار الفوترة</p>'
          : '<p class="cf2-plan-card__action cf2-packages__blocked-cta">الترقية غير متاحة من هذه الشاشة</p>';
      cards +=
        '<article class="cf2-plan-card' +
        (isCurrent ? " is-current" : "") +
        '" data-cf2-plan="' +
        esc(id) +
        '">' +
        (isCurrent
          ? '<span class="cf2-plan-card__badge">الحالية</span>'
          : p.most_popular
            ? '<span class="cf2-plan-card__badge">الأكثر اختياراً</span>'
            : "") +
        '<h3 class="cf2-plan-card__name">' +
        esc(p.label_ar || id) +
        "</h3>" +
        priceHtml +
        (featLis
          ? '<ul class="cf2-plan-card__features">' + featLis + "</ul>"
          : "") +
        actionHtml +
        "</article>";
    }

    root.innerHTML =
      '<div class="cf2-packages" dir="rtl">' +
      '<h1 class="cf2-packages__title">الباقات</h1>' +
      '<p class="cf2-packages__lede">باقتك الحالية ومقارنة الباقات من المصدر المعتمد — بدون دفع من هنا.</p>' +
      '<div class="cf2-packages__current">' +
      '<div class="cf2-packages__current-label">الباقة الحالية</div>' +
      '<div class="cf2-packages__current-name">' +
      esc(planLabel) +
      (status ? " · " + esc(status) : "") +
      "</div></div>" +
      '<p class="cf2-packages__ready" role="status">' +
      esc(footnote) +
      (!billingOk || !upgradeOk
        ? " · الترقية والدفع غير متاحين من لوحة التحكم حالياً."
        : "") +
      "</p>" +
      (cards
        ? '<div class="cf2-packages__grid">' + cards + "</div>"
        : '<p class="cf2-packages__ready">لا تتوفر بطاقات باقات معتمدة للعرض الآن.</p>') +
      "</div>";
  }

  function load(force) {
    var root = $("#cf2-packages-root");
    if (!root) return Promise.resolve();
    if (loading) return Promise.resolve();
    if (loaded && !force) return Promise.resolve();
    loading = true;
    root.innerHTML = '<p class="cf2-loading">جاري تحميل الباقات…</p>';
    return fetch("/api/merchant/plans-catalog", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (!x.data || x.data.ok === false) {
          root.innerHTML =
            '<p class="cf2-packages__ready">تعذّر تحميل الباقات من المصدر المعتمد.</p>';
          return;
        }
        render(root, x.data);
        loaded = true;
      })
      .catch(function () {
        root.innerHTML =
          '<p class="cf2-packages__ready">خطأ في الشبكة أثناء تحميل الباقات.</p>';
      })
      .finally(function () {
        loading = false;
      });
  }

  window.CartFlowUiV2Packages = {
    load: load,
    show: function () {
      return load(false);
    },
  };
})();
