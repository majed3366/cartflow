/* Merchant dashboard — current plan (read-only) */
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

  function applySubscription(d) {
    if (!d) return;
    var label = d.current_plan_label_ar || d.current_plan;
    setText("ma-sub-plan-display", label);
    setText("ma-sub-source-display", d.plan_source_label_ar || d.plan_source);
    setText("ma-sub-status-display", d.plan_status_label_ar || d.plan_status);
    setText("ma-sub-started-display", d.plan_started_at_ar);
    setText("ma-sub-expires-display", d.plan_expires_at_ar);
    setText("ma-sub-updated-display", d.subscription_updated_at_ar);
    var trialRow = byId("ma-sub-trial-row");
    var trialing = !!(d.is_trialing || d.plan_status === "trialing");
    if (trialRow) trialRow.hidden = !trialing;
    if (trialing) {
      setText("ma-sub-trial-expires-display", d.trial_expires_at_ar);
    }
    var pill = byId("ma-sub-plan-pill");
    if (pill) {
      pill.textContent = label || "—";
      pill.classList.toggle("is-starter", d.current_plan === "starter");
      pill.classList.toggle("is-growth", d.current_plan === "growth");
      pill.classList.toggle("is-pro", d.current_plan === "pro");
    }
  }

  function loadSubscription() {
    if (loading) return;
    loading = true;
    fetch("/api/merchant/subscription", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok && data.subscription) {
          applySubscription(data.subscription);
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
