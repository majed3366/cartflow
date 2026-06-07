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
    setText("ma-sub-plan-display", d.current_plan_label_ar || d.current_plan);
    setText("ma-sub-source-display", d.plan_source_label_ar || d.plan_source);
    setText("ma-sub-status-display", d.plan_status_label_ar || d.plan_status);
    setText("ma-sub-started-display", d.plan_started_at_ar);
    setText("ma-sub-expires-display", d.plan_expires_at_ar);
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
      if ((window.location.hash || "").indexOf("settings") >= 0) {
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
