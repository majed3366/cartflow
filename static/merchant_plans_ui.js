/* Merchant dashboard — plans comparison (read-only) */
(function () {
  "use strict";

  var bound = false;
  var loading = false;
  var lastPayload = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) el.textContent = t == null || t === "" ? "—" : String(t);
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function applyCurrentPlan(sub) {
    if (!sub) return;
    var label = sub.current_plan_label_ar || sub.current_plan || "—";
    setText(
      "ma-plans-current-summary",
      "أنت على باقة " +
        label +
        " — المصدر: " +
        (sub.plan_source_label_ar || sub.plan_source || "—")
    );
    setText("ma-plans-current-source", "المصدر: " + (sub.plan_source_label_ar || "—"));
    setText("ma-plans-current-status", "الحالة: " + (sub.status_badge_label_ar || sub.plan_status_label_ar || "—"));
    setText(
      "ma-plans-current-interval",
      "الفترة: " + (sub.billing_interval_label_ar || sub.billing_interval || "—")
    );

    if (window.maApplySubscriptionExperience) {
      window.maApplySubscriptionExperience(sub, {
        prefix: "ma-plans",
        planPillId: "ma-plans-current-pill",
      });
    }

    var trialEl = byId("ma-plans-current-trial");
    var planExpEl = byId("ma-plans-current-expires");
    var trialDot = byId("ma-plans-trial-dot");
    var interval = sub.billing_interval || "";
    var trialing = interval === "trial" || !!(sub.is_trialing || sub.plan_status === "trialing");
    if (trialEl) {
      trialEl.hidden = !trialing;
      if (trialing) {
        trialEl.textContent =
          "تنتهي التجربة: " + (sub.trial_expires_at_ar || sub.subscription_expires_at_ar || "—");
      }
    }
    if (planExpEl) {
      var showPlanExp = interval === "monthly" || interval === "annual" || interval === "manual_custom";
      planExpEl.hidden = !showPlanExp;
      var expDot = byId("ma-plans-expires-dot");
      if (expDot) expDot.hidden = !showPlanExp;
      if (showPlanExp) {
        planExpEl.textContent =
          "انتهاء الباقة: " + (sub.plan_expires_at_ar || sub.subscription_expires_at_ar || "—");
      }
    }
    if (trialDot) trialDot.hidden = !trialing;

    var benefits = byId("ma-plans-benefits");
    if (benefits) benefits.hidden = !(sub.current_benefits_ar && sub.current_benefits_ar.length);
  }

  function renderPlansGrid(catalog, subscription) {
    var grid = byId("ma-plans-grid");
    if (!grid || !catalog || !Array.isArray(catalog.plans)) return;
    var currentPlan = subscription && subscription.current_plan ? subscription.current_plan : "";
    var html = catalog.plans
      .map(function (plan) {
        var isCurrent = plan.plan_id === currentPlan;
        var popular = !!plan.most_popular;
        var features = (plan.features_ar || [])
          .map(function (f) {
            return "<li>" + escapeHtml(f) + "</li>";
          })
          .join("");
        return (
          '<article class="ma-plan-card' +
          (popular ? " is-popular" : "") +
          (isCurrent ? " is-current" : "") +
          '" data-plan-id="' +
          escapeHtml(plan.plan_id) +
          '">' +
          (popular ? '<span class="ma-plan-badge">الأكثر شيوعاً</span>' : "") +
          (isCurrent ? '<span class="ma-plan-current-badge">باقتك الحالية</span>' : "") +
          '<h3 class="ma-plan-name">' +
          escapeHtml(plan.label_ar) +
          "</h3>" +
          '<p class="ma-plan-note">' +
          escapeHtml(plan.upgrade_path_note_ar || "") +
          "</p>" +
          '<div class="ma-plan-prices">' +
          '<div class="ma-plan-price-main">' +
          escapeHtml(plan.monthly_label_ar) +
          "</div>" +
          '<div class="ma-plan-price-sub">' +
          escapeHtml(plan.annual_label_ar) +
          "</div>" +
          "</div>" +
          '<ul class="ma-plan-features">' +
          features +
          "</ul>" +
          "</article>"
        );
      })
      .join("");
    grid.innerHTML = html;
    setText("ma-plans-footnote", catalog.footnote_ar || "");
  }

  function loadPlansCatalog() {
    if (loading) return;
    loading = true;
    fetch("/api/merchant/plans-catalog", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return;
        lastPayload = data;
        applyCurrentPlan(data.subscription);
        renderPlansGrid(data.catalog, data.subscription);
      })
      .catch(function () {
        setText("ma-plans-current-summary", "تعذّر تحميل الباقات");
      })
      .finally(function () {
        loading = false;
      });
  }

  window.maInitPlansPage = function () {
    loadPlansCatalog();
  };

  function bind() {
    if (bound) return;
    bound = true;
    window.addEventListener("hashchange", function () {
      var h = (window.location.hash || "").toLowerCase();
      if (h.indexOf("#plans") === 0) {
        loadPlansCatalog();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
