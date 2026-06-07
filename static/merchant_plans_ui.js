/* Merchant dashboard — plans comparison (read-only) */
(function () {
  "use strict";

  var bound = false;
  var loading = false;
  var lastPayload = null;

  var WARN_CATALOG_AR = "تعذّر عرض بطاقات المقارنة مؤقتاً — باقتك الحالية ظاهرة أعلاه.";
  var WARN_SUBSCRIPTION_AR = "تعذّر عرض ملخص الباقة مؤقتاً — بطاقات الأسعار ظاهرة أدناه.";
  var WARN_BOTH_AR = "تعذّر تحميل الباقات — حاول تحديث الصفحة.";

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

  function setPlansWarning(message) {
    var el = byId("ma-plans-current-summary");
    if (!el) return;
    if (!message) {
      return;
    }
    el.textContent = message;
    el.classList.add("ma-plans-warning");
  }

  function clearPlansWarning(defaultSummary) {
    var el = byId("ma-plans-current-summary");
    if (!el) return;
    el.classList.remove("ma-plans-warning");
    if (defaultSummary) {
      el.textContent = defaultSummary;
    }
  }

  function parsePlansCatalogResponse(data) {
    if (!data || typeof data !== "object") {
      return { ok: false, subscription: null, catalog: null };
    }
    var subscription = data.subscription && typeof data.subscription === "object" ? data.subscription : null;
    var catalog = data.catalog && typeof data.catalog === "object" ? data.catalog : null;
    if (catalog && catalog.plans && !Array.isArray(catalog.plans)) {
      catalog = null;
    }
    return {
      ok: !!data.ok,
      subscription: subscription,
      catalog: catalog,
    };
  }

  function buildDefaultSummary(sub) {
    if (!sub) return "—";
    var label = sub.current_plan_label_ar || sub.current_plan || "—";
    return (
      "أنت على باقة " +
      label +
      " — المصدر: " +
      (sub.plan_source_label_ar || sub.plan_source || "—")
    );
  }

  function applyCurrentPlanCore(sub) {
    if (!sub) return;
    var label = sub.current_plan_label_ar || sub.current_plan || "—";
    setText("ma-plans-current-source", "المصدر: " + (sub.plan_source_label_ar || sub.plan_source || "—"));
    setText("ma-plans-current-status", "الحالة: " + (sub.status_badge_label_ar || sub.plan_status_label_ar || "—"));
    setText(
      "ma-plans-current-interval",
      "الفترة: " + (sub.billing_interval_label_ar || sub.billing_interval || "—")
    );

    var pill = byId("ma-plans-current-pill");
    if (pill) {
      pill.hidden = false;
      pill.textContent = label;
      pill.className =
        "ma-sub-plan-pill is-" + (sub.plan_badge_class || sub.current_plan || "starter");
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
  }

  function applyCurrentPlanExperience(sub) {
    if (!sub || typeof window.maApplySubscriptionExperience !== "function") {
      return;
    }
    window.maApplySubscriptionExperience(sub, {
      prefix: "ma-plans",
      planPillId: "ma-plans-current-pill",
    });
  }

  function applyCurrentPlan(sub) {
    if (!sub) return buildDefaultSummary(null);
    var summary = buildDefaultSummary(sub);
    clearPlansWarning(summary);
    applyCurrentPlanCore(sub);
    try {
      applyCurrentPlanExperience(sub);
    } catch (_err) {
      /* core summary already rendered */
    }
    var benefits = byId("ma-plans-benefits");
    if (benefits) {
      benefits.hidden = !(sub.current_benefits_ar && sub.current_benefits_ar.length);
    }
    return summary;
  }

  function renderPlansGrid(catalog, subscription) {
    var grid = byId("ma-plans-grid");
    if (!grid) return false;
    if (!catalog || !Array.isArray(catalog.plans) || !catalog.plans.length) {
      grid.innerHTML = "";
      return false;
    }
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
    return true;
  }

  function renderPlansPayload(data) {
    var parsed = parsePlansCatalogResponse(data);
    var subscriptionOk = false;
    var catalogOk = false;
    var summary = null;

    if (parsed.subscription) {
      try {
        summary = applyCurrentPlan(parsed.subscription);
        subscriptionOk = true;
      } catch (_subErr) {
        subscriptionOk = false;
      }
    }

    if (parsed.catalog) {
      try {
        catalogOk = renderPlansGrid(parsed.catalog, parsed.subscription);
      } catch (_catErr) {
        catalogOk = false;
      }
    }

    if (parsed.ok && (subscriptionOk || catalogOk)) {
      if (subscriptionOk && !catalogOk) {
        setPlansWarning(summary || WARN_CATALOG_AR);
      } else if (catalogOk && !subscriptionOk) {
        setPlansWarning(WARN_SUBSCRIPTION_AR);
      } else if (summary) {
        clearPlansWarning(summary);
      }
      return true;
    }

    if (parsed.ok) {
      setPlansWarning(WARN_BOTH_AR);
      return false;
    }

    setPlansWarning(WARN_BOTH_AR);
    return false;
  }

  function loadPlansCatalog() {
    if (loading) return;
    loading = true;
    fetch("/api/merchant/plans-catalog", { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) {
          throw new Error("http_" + r.status);
        }
        return r.json();
      })
      .then(function (data) {
        lastPayload = data;
        renderPlansPayload(data);
      })
      .catch(function () {
        if (lastPayload && lastPayload.ok) {
          renderPlansPayload(lastPayload);
          return;
        }
        setPlansWarning(WARN_BOTH_AR);
      })
      .finally(function () {
        loading = false;
      });
  }

  window.maInitPlansPage = function () {
    loadPlansCatalog();
  };

  window.maRenderPlansPayload = renderPlansPayload;

  function bind() {
    if (bound) return;
    bound = true;
    window.addEventListener("hashchange", function () {
      var h = (window.location.hash || "").toLowerCase();
      if (h.indexOf("#plans") === 0) {
        loadPlansCatalog();
      }
    });
    var h0 = (window.location.hash || "").toLowerCase();
    if (h0.indexOf("#plans") === 0) {
      loadPlansCatalog();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
