/* Merchant dashboard — subscription experience V2 (read-only) */
(function () {
  "use strict";

  var bound = false;
  var loading = false;

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

  function applyBadge(el, label, className) {
    if (!el) return;
    el.hidden = !label;
    el.textContent = label || "—";
    el.className = el.className.replace(/\bis-(starter|growth|pro|active|trial|expired|cancelled|neutral|manual|marketplace|cartflow)\b/g, "").trim();
    if (className) {
      el.classList.add(className);
    }
  }

  function applyHealth(el, message, tone) {
    if (!el) return;
    el.hidden = !message;
    el.textContent = message || "";
    el.className = "ma-sub-health";
    if (tone) el.classList.add("is-" + tone);
  }

  function renderBenefits(listId, containerId, items) {
    var list = byId(listId);
    var container = containerId ? byId(containerId) : null;
    if (!list) return;
    var rows = Array.isArray(items) ? items : [];
    if (container) container.hidden = rows.length === 0;
    list.innerHTML = rows
      .map(function (item) {
        return "<li>" + escapeHtml(item) + "</li>";
      })
      .join("");
  }

  function renderDiscovery(containerId, sections) {
    var container = byId(containerId);
    if (!container) return;
    var rows = Array.isArray(sections) ? sections : [];
    if (!rows.length) {
      container.innerHTML = "";
      container.hidden = true;
      return;
    }
    container.hidden = false;
    container.innerHTML = rows
      .map(function (section) {
        var items = (section.items_ar || [])
          .map(function (item) {
            return "<li>" + escapeHtml(item) + "</li>";
          })
          .join("");
        return (
          '<div class="ma-sub-discovery-block">' +
          '<div class="ma-sub-discovery-title">' +
          escapeHtml(section.title_ar || "") +
          "</div>" +
          '<ul class="ma-sub-discovery-list">' +
          items +
          "</ul></div>"
        );
      })
      .join("");
  }

  function applySubscriptionExperience(d, opts) {
    if (!d) return;
    opts = opts || {};
    var prefix = opts.prefix || "ma-sub";
    var label = d.current_plan_label_ar || d.current_plan;
    var interval = d.billing_interval || "";
    var trialing = interval === "trial" || !!(d.is_trialing || d.plan_status === "trialing");
    var monthlyOrAnnual = interval === "monthly" || interval === "annual";

    setText(prefix + "-plan-display", label);
    setText(prefix + "-source-display", d.plan_source_label_ar || d.plan_source);
    setText(prefix + "-status-display", d.status_badge_label_ar || d.plan_status_label_ar || d.plan_status);
    setText(prefix + "-interval-display", d.billing_interval_label_ar || interval || "—");
    setText(prefix + "-started-display", d.plan_started_at_ar);
    setText(prefix + "-updated-display", d.subscription_updated_at_ar);

    var planPill = byId(opts.planPillId || prefix + "-plan-pill");
    applyBadge(planPill, label, "ma-sub-plan-pill is-" + (d.plan_badge_class || d.current_plan || "starter"));
    applyBadge(
      byId(prefix + "-status-pill"),
      d.status_badge_label_ar || d.plan_status_label_ar,
      "ma-sub-status-pill " + (d.status_badge_class || "")
    );
    applyBadge(
      byId(prefix + "-source-pill"),
      d.source_badge_label_ar || d.plan_source_label_ar,
      "ma-sub-source-pill " + (d.source_badge_class || "")
    );

    applyHealth(byId(prefix + "-health"), d.subscription_health_ar, d.subscription_health_tone);

    var daysEl = byId(prefix + "-days");
    if (daysEl) {
      var daysLabel = d.days_remaining_label_ar;
      daysEl.hidden = !daysLabel || daysLabel === "—";
      daysEl.textContent = daysLabel || "";
    }

    var trialRow = byId(prefix + "-trial-row");
    var planExpiresRow = byId(prefix + "-plan-expires-row");
    if (trialRow) trialRow.hidden = !trialing;
    if (planExpiresRow) planExpiresRow.hidden = trialing && !monthlyOrAnnual;

    if (trialing) {
      setText(prefix + "-trial-expires-display", d.trial_expires_at_ar || d.subscription_expires_at_ar);
    }
    if (monthlyOrAnnual || interval === "manual_custom" || (!trialing && d.plan_expires_at_ar)) {
      setText(prefix + "-expires-display", d.plan_expires_at_ar || d.subscription_expires_at_ar);
    } else if (!trialing) {
      setText(prefix + "-expires-display", d.subscription_expires_at_ar || d.plan_expires_at_ar);
    }

    renderBenefits(prefix + "-benefits-list", prefix + "-benefits", d.current_benefits_ar);
    renderDiscovery(prefix + "-discovery", d.upgrade_discovery_sections_ar);
  }

  window.maApplySubscriptionExperience = applySubscriptionExperience;

  function loadSubscription() {
    if (loading) return;
    loading = true;
    fetch("/api/merchant/subscription", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok && data.subscription) {
          applySubscriptionExperience(data.subscription, { prefix: "ma-sub" });
        }
      })
      .catch(function () {
        /* read-only card — silent fail */
      })
      .finally(function () {
        loading = false;
      });
  }

  function bind() {
    if (bound) return;
    bound = true;
    loadSubscription();
    window.addEventListener("hashchange", function () {
      var h = (window.location.hash || "").toLowerCase();
      if (h.indexOf("#settings") === 0 || h.indexOf("#plans") === 0) {
        loadSubscription();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
