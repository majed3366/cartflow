/* Lazy-load merchant dashboard JSON sections (shell-first). Not storefront widget V2. */
/* MERCHANT_SETUP_RENDER_BUILD=ui-setup-v5-demo-reusable */
(function () {
  "use strict";

  var MERCHANT_SETUP_RENDER_BUILD = "ui-setup-v5-demo-reusable";

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

  function stripSkel(el) {
    if (!el) return;
    el.classList.remove("ma-dash-skel");
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) {
      el.textContent = t == null ? "" : String(t);
      stripSkel(el);
    }
  }

  var cachedMerchantActivation = null;
  var cachedMerchantSetupExperience = null;
  var merchantDashboardRefreshToken = "";
  var merchantRefreshInFlight = false;
  var merchantRefreshTimer = null;

  function isUnifiedSetup(mse) {
    if (!mse || typeof mse !== "object") return false;
    if (mse.unified_p0 === true) return true;
    if (mse.unified_p0 === false) return false;
    var steps = mse.steps || [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].phase) return true;
    }
    return false;
  }

  function shouldRenderUnifiedSetup(mse) {
    if (!isUnifiedSetup(mse)) return false;
    if (mse.setup_mode === false) return false;
    if (mse.show_card === false) return false;
    return true;
  }

  function logSetupRenderDebug(label, payload) {
    try {
      console.info(
        "[CartFlow] MERCHANT_SETUP_RENDER_BUILD=" + MERCHANT_SETUP_RENDER_BUILD
      );
      if (payload) {
        console.info("[CartFlow] " + label, payload);
      }
    } catch (_e) {
      /* ignore */
    }
  }

  function logClientRefresh(label, payload) {
    try {
      if (payload) {
        console.info("[CLIENT REFRESH] " + label, payload);
      } else {
        console.info("[CLIENT REFRESH] " + label);
      }
    } catch (_e) {
      /* ignore */
    }
  }

  function ingestRefreshToken(d, source) {
    if (!d || !d.merchant_dashboard_refresh_token) return;
    var next = String(d.merchant_dashboard_refresh_token || "");
    if (!next) return;
    if (next !== merchantDashboardRefreshToken) {
      merchantDashboardRefreshToken = next;
      logClientRefresh("token_update", {
        source: source || "",
        token: merchantDashboardRefreshToken,
      });
    }
  }

  function probeSetupExperienceRoot() {
    var root = byId("ma-setup-experience-root");
    var home = byId("page-home");
    if (!root) {
      return { found: false };
    }
    var cs = window.getComputedStyle ? window.getComputedStyle(root) : null;
    return {
      found: true,
      hiddenProperty: !!root.hidden,
      hasHiddenAttr: root.hasAttribute("hidden"),
      innerHTMLLength: (root.innerHTML || "").length,
      display: cs ? cs.display : null,
      visibility: cs ? cs.visibility : null,
      parentPageHomeActive: !!(home && home.classList.contains("active")),
      dataUnified: root.getAttribute("data-ma-setup-unified"),
    };
  }

  window.maProbeSetupExperienceRoot = probeSetupExperienceRoot;

  function isDashboardHomeActive() {
    var home = byId("page-home");
    return !!(home && home.classList.contains("active"));
  }

  function hideActivationOffHome() {
    var root = byId("ma-activation-root");
    if (!root) return;
    root.hidden = true;
    root.setAttribute("hidden", "");
    root.classList.remove("ma-activation-on-home");
  }

  function showActivationRoot(root) {
    if (!root) return;
    root.hidden = false;
    root.removeAttribute("hidden");
    root.classList.add("ma-activation-on-home");
  }

  function hideActivationRootClear(root) {
    if (!root) return;
    root.hidden = true;
    root.setAttribute("hidden", "");
    root.classList.remove("ma-activation-on-home");
    root.innerHTML = "";
  }

  function syncHomeActivationFromCache() {
    var act = cachedMerchantActivation;
    var mse = cachedMerchantSetupExperience;
    var home = byId("page-home");
    if (act && home) {
      applyHomeAdaptiveStage(act);
    }
    if (!isDashboardHomeActive()) {
      hideActivationOffHome();
      return;
    }
    if (!act) {
      return;
    }
    if (!isUnifiedSetup(mse)) {
      applyMerchantActivation(act);
    } else {
      hideActivationForUnifiedSetup(mse);
    }
    if (
      shouldHideUnifiedSetupCard(act, mse) ||
      (isUnifiedSetup(mse) && mse && mse.setup_mode === false)
    ) {
      var setupRoot = byId("ma-setup-experience-root");
      if (setupRoot && isDashboardHomeActive()) {
        renderUnifiedSetupDemoToolsOnly(mse, setupRoot);
      }
    } else if (shouldRenderUnifiedSetup(mse) && isDashboardHomeActive()) {
      applyMerchantSetupExperience(mse);
    }
  }

  function setNavBadge(id, n) {
    var el = byId(id);
    if (!el) return;
    var v = parseInt(n, 10) || 0;
    el.textContent = String(v);
    el.style.display = v > 0 ? "" : "none";
  }

  function sectionFromHref(href) {
    var h = String(href || "");
    var i = h.indexOf("#");
    if (i < 0) return "";
    return h.slice(i + 1);
  }

  function setupStepsHtml(steps) {
    if (!steps || !steps.length) return "";
    var html = '<ul class="ma-onb-checklist">';
    for (var i = 0; i < steps.length; i++) {
      var st = steps[i];
      var done = !!st.is_complete;
      var mark = done ? "✓" : "◯";
      var href = st.action_href || "#settings";
      var sec = sectionFromHref(href);
      var goAttr = sec
        ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
        : "";
      html +=
        '<li class="ma-onb-checklist-item' +
        (done ? " is-done" : " is-pending") +
        '">' +
        '<span class="ma-onb-check" aria-hidden="true">' +
        mark +
        "</span>" +
        '<div class="ma-onb-check-body">' +
        '<p class="ma-onb-check-title">' +
        esc(st.title_ar) +
        "</p>" +
        '<p class="ma-onb-check-outcome-label">النتيجة</p>' +
        '<p class="ma-onb-check-outcome">' +
        esc(st.outcome_ar) +
        "</p>" +
        (done
          ? ""
          : '<a class="ma-setup-step-action" href="' +
            esc(href) +
            '"' +
            goAttr +
            ">انتقل لهذه الخطوة</a>") +
        "</div></li>";
    }
    html += "</ul>";
    return html;
  }

  function applyOnboardingHomeFocus(mse) {
    var home = byId("page-home");
    if (!home) return;
    var setupMode = shouldRenderUnifiedSetup(mse);
    home.classList.toggle("ma-setup-mode", setupMode);
    home.classList.toggle("ma-setup-daily-peek", setupMode);
    home.classList.remove("ma-onboarding-focus");
  }

  function hideActivationForUnifiedSetup(mse) {
    var root = byId("ma-activation-root");
    if (!root) return;
    if (isUnifiedSetup(mse)) {
      root.hidden = true;
      root.innerHTML = "";
      root.classList.remove("ma-activation-on-home");
      return;
    }
  }

  /** Hide unified setup only when prod path finished (setup_mode === false). */
  function shouldHideUnifiedSetupCard(act, mse) {
    if (!act || !mse || !isUnifiedSetup(mse) || !act.hide_setup_card) {
      return false;
    }
    return mse.setup_mode === false;
  }

  function showSetupExperienceRoot(root) {
    if (!root) return;
    root.hidden = false;
    root.removeAttribute("hidden");
  }

  function applyHomeOperationalAlerts(alerts) {
    var root = byId("ma-home-alerts-root");
    if (!root) return;
    var lines = alerts || [];
    if (!lines.length) {
      root.hidden = true;
      root.innerHTML = "";
      return;
    }
    var lis = "";
    for (var i = 0; i < lines.length; i++) {
      lis += "<li>" + esc(lines[i]) + "</li>";
    }
    root.hidden = false;
    root.innerHTML =
      '<div class="ma-home-alerts-inner">' +
      '<p class="ma-home-alerts-title">تنبيهات تشغيلية</p>' +
      '<ul class="ma-home-alerts-list">' +
      lis +
      "</ul></div>";
  }

  function applyHomeAdaptiveStage(act) {
    var home = byId("page-home");
    if (!home) return;
    var stage = (act && act.home_stage) || "activation";
    home.setAttribute("data-ma-home-stage", stage);
    home.classList.remove(
      "ma-home-stage-activation",
      "ma-home-stage-activated",
      "ma-home-stage-production"
    );
    home.classList.add("ma-home-stage-" + stage);
    applyHomeOperationalAlerts(act && act.operational_alerts_ar);
  }

  function normalizeActivationDisplay(raw) {
    return String(raw == null ? "" : raw)
      .trim()
      .toLowerCase();
  }

  function resolveActivationRenderPlan(act) {
    var rawDisplay = act && act.activation_display;
    var display = normalizeActivationDisplay(rawDisplay);
    var plan = {
      display: rawDisplay || "prominent",
      renderMode: "prominent",
      template: "activation_prominent_v1",
      fallback: null,
    };
    if (!display) {
      plan.fallback = "missing_activation_display_default_prominent";
      return plan;
    }
    if (display === "prominent") {
      plan.renderMode = "prominent";
      plan.template = "activation_prominent_v1";
      return plan;
    }
    if (display === "compact") {
      plan.renderMode = "compact";
      plan.template = "activation_compact_v1";
      return plan;
    }
    if (display === "hidden") {
      plan.renderMode = "compact";
      plan.template = "activation_compact_v1";
      plan.fallback = "server_hidden_upgraded_to_compact_on_home";
      return plan;
    }
    plan.fallback = "unknown_activation_display_coerced_prominent";
    return plan;
  }

  function logActivationRender(plan, act) {
    console.log(
      "[ACTIVATION RENDER]\n" +
        "display=" +
        String(plan.display) +
        "\n" +
        "render_mode=" +
        String(plan.renderMode) +
        "\n" +
        "template=" +
        String(plan.template) +
        "\n" +
        "fallback=" +
        String(plan.fallback || "") +
        "\n" +
        "home_stage=" +
        String((act && act.home_stage) || "")
    );
  }

  function buildActivationMilestonesHtml(milestones) {
    var msHtml = "";
    var i;
    for (i = 0; i < milestones.length; i++) {
      var m = milestones[i];
      var done = !!m.done;
      msHtml +=
        '<li class="' +
        (done ? "is-done" : "is-pending") +
        '">' +
        '<span class="ma-act-mark" aria-hidden="true">' +
        (done ? "✓" : "○") +
        "</span>" +
        "<span>" +
        esc(m.title_ar || "") +
        (m.hint_ar
          ? '<span class="ma-act-hint">' + esc(m.hint_ar) + "</span>"
          : "") +
        "</span></li>";
    }
    return msHtml;
  }

  function buildActivationTimelineHtml(states) {
    var stHtml = "";
    var i;
    for (i = 0; i < states.length; i++) {
      var st = states[i];
      var liCls = "";
      if (st.reached) liCls += " is-reached";
      if (st.current) liCls += " is-current";
      stHtml +=
        '<li class="' +
        liCls +
        '">' +
        esc(st.label_ar || "") +
        "</li>";
    }
    return stHtml;
  }

  function bindActivationCompactExpand(root) {
    var card = byId("ma-activation-card-inner");
    var expandBtn = root.querySelector("[data-ma-act-expand]");
    if (expandBtn && card) {
      expandBtn.addEventListener("click", function () {
        card.classList.toggle("ma-activation-expanded");
        expandBtn.textContent = card.classList.contains("ma-activation-expanded")
          ? "إخفاء التفاصيل"
          : "تفاصيل التفعيل";
      });
    }
  }

  function renderActivationProminent(act, root) {
    var milestones = act.milestones || [];
    var states = act.summary_states || [];
    var working = !!act.activation_working;
    var title = working
      ? "CartFlow يعمل على متجرك"
      : "تفعيل سريع — أول نجاح";
    var lead =
      act.next_step_ar ||
      "جرّب متجر الاختبار ثم راقب السلال هنا.";
    var msHtml = buildActivationMilestonesHtml(milestones);
    var stHtml = buildActivationTimelineHtml(states);
    var testUrl = act.test_store_url || "/dashboard/test-widget";
    var delay = act.delay_hint_ar
      ? '<p class="ma-activation-delay">' + esc(act.delay_hint_ar) + "</p>"
      : "";
    var timelineBlock = stHtml
      ? '<ul class="ma-activation-timeline">' + stHtml + "</ul>"
      : "";
    showActivationRoot(root);
    root.setAttribute("data-ma-activation-render-mode", "prominent");
    root.innerHTML =
      '<div class="ma-activation-card ma-activation-prominent" id="ma-activation-card-inner">' +
      "<h2 class=\"ma-activation-title\">" +
      esc(title) +
      "</h2>" +
      '<p class="ma-activation-lead">' +
      esc(lead) +
      "</p>" +
      timelineBlock +
      '<ul class="ma-activation-milestones">' +
      msHtml +
      "</ul>" +
      '<div class="ma-activation-actions">' +
      '<a class="ma-activation-btn ma-activation-btn-primary" href="' +
      esc(testUrl) +
      '" target="_blank" rel="noopener">فتح متجر الاختبار</a>' +
      '<a class="ma-activation-btn ma-activation-btn-secondary" href="/dashboard#carts" onclick="if(window.goTo){goTo(\'carts\');}return false;">عرض السلال</a>' +
      "</div>" +
      delay +
      "</div>";
  }

  function renderActivationCompact(act, root) {
    var milestones = act.milestones || [];
    var states = act.summary_states || [];
    var lead =
      act.next_step_ar ||
      "جرّب متجر الاختبار ثم راقب السلال هنا.";
    var msHtml = buildActivationMilestonesHtml(milestones);
    var stHtml = buildActivationTimelineHtml(states);
    var testUrl = act.test_store_url || "/dashboard/test-widget";
    var delay = act.delay_hint_ar
      ? '<p class="ma-activation-delay">' + esc(act.delay_hint_ar) + "</p>"
      : "";
    var summaryLines = act.activation_summary_lines_ar || [];
    var compactBody = "";
    var i;
    for (i = 0; i < summaryLines.length; i++) {
      compactBody +=
        '<span class="ma-activation-compact-line">' +
        esc(summaryLines[i]) +
        "</span>";
    }
    if (act.last_activity_ar) {
      compactBody +=
        '<span class="ma-activation-compact-line">آخر نشاط: ' +
        esc(act.last_activity_ar) +
        "</span>";
    }
    var timelineBlock = stHtml
      ? '<ul class="ma-activation-timeline">' + stHtml + "</ul>"
      : "";
    showActivationRoot(root);
    root.setAttribute("data-ma-activation-render-mode", "compact");
    root.innerHTML =
      '<div class="ma-activation-card ma-activation-compact" id="ma-activation-card-inner">' +
      "<h2 class=\"ma-activation-title\">" +
      esc("حالة التفعيل") +
      "</h2>" +
      '<div class="ma-activation-compact-body">' +
      compactBody +
      '<button type="button" class="ma-activation-compact-toggle" data-ma-act-expand="1">تفاصيل التفعيل</button>' +
      "</div>" +
      timelineBlock +
      '<ul class="ma-activation-milestones">' +
      msHtml +
      "</ul>" +
      '<div class="ma-activation-actions">' +
      '<a class="ma-activation-btn ma-activation-btn-primary" href="' +
      esc(testUrl) +
      '" target="_blank" rel="noopener">فتح متجر الاختبار</a>' +
      '<a class="ma-activation-btn ma-activation-btn-secondary" href="/dashboard#carts" onclick="if(window.goTo){goTo(\'carts\');}return false;">عرض السلال</a>' +
      "</div>" +
      delay +
      '<p class="ma-activation-lead">' +
      esc(lead) +
      "</p>" +
      "</div>";
    bindActivationCompactExpand(root);
  }

  function applyMerchantActivation(act) {
    var root = byId("ma-activation-root");
    if (!root) return;
    if (!isDashboardHomeActive()) {
      hideActivationOffHome();
      return;
    }
    if (!act || typeof act !== "object") {
      hideActivationRootClear(root);
      return;
    }
    var plan = resolveActivationRenderPlan(act);
    logActivationRender(plan, act);
    if (plan.renderMode === "compact") {
      renderActivationCompact(act, root);
      return;
    }
    if (plan.renderMode === "prominent") {
      renderActivationProminent(act, root);
      return;
    }
    hideActivationRootClear(root);
  }

  function applyHomeLayoutAfterSetup(act, mse) {
    cachedMerchantActivation = act;
    cachedMerchantSetupExperience = mse;
    syncHomeActivationFromCache();
  }

  function unifiedStepShortLabel(titleAr) {
    var t = String(titleAr || "").trim();
    if (t.length <= 28) return t;
    return t.slice(0, 26) + "…";
  }

  function isDemoStoreHref(href) {
    return String(href || "").indexOf("/demo/store") >= 0;
  }

  function demoRetryHref(st, href) {
    var h = href || (st && st.action_href) || "";
    if (!isDemoStoreHref(h)) {
      return h;
    }
    if (h.indexOf("reset_demo=1") >= 0) {
      return h;
    }
    return h + (h.indexOf("?") >= 0 ? "&" : "?") + "reset_demo=1";
  }

  function unifiedSetupStepActionsHtml(st) {
    if (!st || st.locked) {
      return "";
    }
    var href = st.action_href || "#settings";
    var sec = sectionFromHref(href);
    var goAttr = sec
      ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
      : "";
    var extTarget = isDemoStoreHref(href) ? ' target="_blank" rel="noopener"' : "";
    if (st.repeatable_demo) {
      var done = !!st.is_complete;
      var cur = !!st.is_current;
      var badge = esc(st.completed_badge_ar || "تمت التجربة ✅");
      var startLbl = esc(st.start_action_label_ar || "ابدأ التجربة");
      var retryLbl = esc(st.retry_action_label_ar || "إعادة التجربة");
      if (done) {
        return (
          '<p class="ma-setup-demo-done-badge" role="status">' +
          badge +
          "</p>" +
          '<a class="ma-setup-step-action ma-setup-demo-retry" href="' +
          esc(demoRetryHref(st, href)) +
          '"' +
          goAttr +
          extTarget +
          ">" +
          retryLbl +
          "</a>"
        );
      }
      if (cur) {
        return (
          '<a class="ma-setup-step-action ma-setup-demo-start" href="' +
          esc(href) +
          '"' +
          goAttr +
          extTarget +
          ">" +
          startLbl +
          "</a>"
        );
      }
      return (
        '<a class="ma-setup-step-action" href="' +
        esc(href) +
        '"' +
        goAttr +
        extTarget +
        ">" +
        esc(st.action_label_ar || startLbl) +
        "</a>"
      );
    }
    if (!st.is_complete && !st.is_current) {
      return (
        '<a class="ma-setup-step-action" href="' +
        esc(href) +
        '"' +
        goAttr +
        ">" +
        esc(st.action_label_ar || "انتقل للخطوة") +
        "</a>"
      );
    }
    return "";
  }

  function renderUnifiedSetupDemoToolsOnly(mse, root) {
    if (!mse || !root) {
      return;
    }
    var demoSteps = [];
    var steps = mse.steps || [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].repeatable_demo && !steps[i].locked) {
        demoSteps.push(steps[i]);
      }
    }
    var testUrl = esc(mse.test_store_url || "/dashboard/test-widget");
    var testExt = isDemoStoreHref(mse.test_store_url || mse.action_href)
      ? ' target="_blank" rel="noopener"'
      : "";
    var rows = "";
    for (i = 0; i < demoSteps.length; i++) {
      rows +=
        '<li class="ma-setup-demo-tool-row">' +
        '<p class="ma-setup-demo-tool-title">' +
        esc(demoSteps[i].title_ar || "") +
        "</p>" +
        unifiedSetupStepActionsHtml(demoSteps[i]) +
        "</li>";
    }
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-setup-unified", "1");
    root.setAttribute("data-ma-setup-demo-tools", "1");
    root.innerHTML =
      '<div class="ma-setup-panel ma-unified-setup-panel ma-setup-v3 ma-setup-demo-tools">' +
      '<p class="ma-setup-v2-eyebrow">أدوات التجربة</p>' +
      '<p class="ma-setup-v2-context">يمكن لفريقك إعادة التجربة في أي وقت — الإكمال لا يعطّل الأزرار.</p>' +
      '<div class="ma-setup-hero-actions ma-setup-demo-tools-primary">' +
      '<a class="ma-setup-btn-primary" href="' +
      testUrl +
      '"' +
      testExt +
      ">فتح متجر الاختبار</a>" +
      '<a class="ma-setup-btn-secondary" href="/dashboard#carts" onclick="if(window.goTo){goTo(\'carts\');}return false;">عرض السلال</a>' +
      "</div>" +
      (rows
        ? '<ul class="ma-setup-demo-tools-list">' + rows + "</ul>"
        : "") +
      "</div>";
    logSetupRenderDebug("setup_render_demo_tools", {
      demo_steps: demoSteps.length,
    });
  }

  function unifiedSetupProgressHtml(steps) {
    if (!steps || !steps.length) return "";
    var html =
      '<div class="ma-setup-timeline-v3" role="list" aria-label="مسار الإعداد"><div class="ma-setup-timeline-v3-track">';
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      var done = !!st.is_complete && !st.locked;
      var cur = !!st.is_current && !st.locked;
      var locked = !!st.locked;
      var state = locked
        ? "is-upcoming"
        : done
          ? "is-done"
          : cur
            ? "is-current"
            : "is-upcoming";
      html +=
        '<span class="ma-setup-timeline-v3-step ' +
        state +
        '" role="listitem" title="' +
        esc(st.title_ar || "") +
        '"><span class="ma-setup-timeline-v3-dot" aria-hidden="true"></span></span>';
    }
    html +=
      '</div><div class="ma-setup-timeline-v3-legend" aria-hidden="true">' +
      '<span class="ma-setup-timeline-v3-legend-item"><span class="ma-setup-timeline-v3-dot is-done"></span> مكتمل</span>' +
      '<span class="ma-setup-timeline-v3-legend-item"><span class="ma-setup-timeline-v3-dot is-current"></span> الحالي</span>' +
      '<span class="ma-setup-timeline-v3-legend-item"><span class="ma-setup-timeline-v3-dot is-upcoming"></span> قادم</span>' +
      "</div></div>";
    return html;
  }

  function unifiedSetupStepsHtml(steps) {
    if (!steps || !steps.length) return "";
    var html = '<ul class="ma-onb-checklist ma-unified-setup-steps">';
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      if (st.locked) {
        html +=
          '<li class="ma-onb-checklist-item is-locked">' +
          '<span class="ma-onb-check" aria-hidden="true">🔒</span>' +
          '<div class="ma-onb-check-body">' +
          '<p class="ma-onb-check-title">' +
          esc(st.title_ar || "") +
          '</p><p class="ma-unified-locked-banner">يفتح بعد إثبات التجربة</p>' +
          '<p class="ma-onb-check-outcome ma-unified-locked-hint">' +
          esc(st.outcome_ar || "") +
          "</p></div></li>";
        continue;
      }
      var done = !!st.is_complete;
      var cur = !!st.is_current;
      var phaseTag =
        st.phase === "production"
          ? '<span class="ma-unified-phase ma-unified-phase-prod">إنتاج</span>'
          : '<span class="ma-unified-phase">تجربة</span>';
      var mark = done ? "✓" : cur ? "▶" : "◯";
      html +=
        '<li class="ma-onb-checklist-item' +
        (done ? " is-done" : " is-pending") +
        (cur ? " is-current" : "") +
        '">' +
        '<span class="ma-onb-check" aria-hidden="true">' +
        mark +
        "</span>" +
        '<div class="ma-onb-check-body">' +
        phaseTag +
        '<p class="ma-onb-check-title">' +
        esc(st.title_ar || "") +
        "</p>" +
        '<p class="ma-onb-check-outcome-label">النتيجة</p>' +
        '<p class="ma-onb-check-outcome">' +
        esc(st.outcome_ar || "") +
        "</p>";
      if (st.proof_ar && !cur) {
        html +=
          '<p class="ma-unified-proof"><span class="ma-unified-proof-k">الإثبات:</span> ' +
          esc(st.proof_ar) +
          "</p>";
      }
      html += unifiedSetupStepActionsHtml(st);
      html += "</div></li>";
    }
    html += "</ul>";
    return html;
  }

  function unifiedSetupHeroHtml(mse) {
    var currentStep = esc(mse.current_step_ar || "—");
    var currentOutcome = esc(mse.current_outcome_ar || "—");
    var rawHref = mse.action_href || mse.test_store_url || "/dashboard/test-widget";
    var steps = mse.steps || [];
    var curStep = null;
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].is_current && !steps[i].locked) {
        curStep = steps[i];
        break;
      }
    }
    if (curStep && curStep.repeatable_demo && curStep.is_complete) {
      rawHref = demoRetryHref(curStep, rawHref);
    }
    var primaryHref = esc(rawHref);
    var primaryLabel = esc(mse.action_label_ar || "ابدأ هذه الخطوة");
    if (curStep && curStep.repeatable_demo && !curStep.is_complete) {
      primaryLabel = esc(
        curStep.start_action_label_ar || mse.action_label_ar || "ابدأ التجربة"
      );
    }
    var isExternalTest = isDemoStoreHref(rawHref);
    var primaryTarget = isExternalTest ? ' target="_blank" rel="noopener"' : "";
    return (
      '<section class="ma-setup-hero ma-setup-hero-v3" aria-label="الخطوة الحالية">' +
      '<p class="ma-setup-hero-eyebrow">الخطوة الحالية</p>' +
      '<h3 class="ma-setup-hero-title">' +
      currentStep +
      "</h3>" +
      '<p class="ma-setup-hero-sub">' +
      currentOutcome +
      "</p>" +
      '<div class="ma-setup-hero-actions">' +
      '<a class="ma-setup-btn-primary ma-setup-hero-cta" href="' +
      primaryHref +
      '"' +
      primaryTarget +
      ">" +
      primaryLabel +
      "</a>" +
      "</div></section>"
    );
  }

  function unifiedSetupCompletedCollapsedHtml(steps) {
    var done = [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i].is_complete && !steps[i].locked) {
        done.push(steps[i]);
      }
    }
    if (!done.length) return "";
    var lis = "";
    for (i = 0; i < done.length; i++) {
      lis +=
        '<li class="ma-setup-done-line"><span aria-hidden="true">✓</span> ' +
        esc(done[i].title_ar || "") +
        "</li>";
    }
    return (
      '<details class="ma-setup-done-collapse">' +
      "<summary><span class=\"ma-setup-done-summary-icon\" aria-hidden=\"true\">✓</span> " +
      done.length +
      " خطوة مكتملة</summary>" +
      '<ul class="ma-setup-done-list">' +
      lis +
      "</ul></details>"
    );
  }

  function unifiedSetupNextLockedHtml(steps) {
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i].locked) {
        return (
          '<p class="ma-setup-locked-v3" role="status">يفتح بعد إثبات التجربة</p>'
        );
      }
    }
    return "";
  }

  function unifiedSetupUpcomingCompactHtml(steps) {
    var upcoming = [];
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      if (!st.locked && !st.is_complete && !st.is_current) {
        upcoming.push(st);
      }
    }
    if (!upcoming.length) return "";
    var rows = "";
    for (i = 0; i < upcoming.length; i++) {
      rows +=
        '<div class="ma-setup-upcoming-v3-row">' +
        "<span>" +
        esc(upcoming[i].title_ar || "") +
        "</span></div>";
    }
    return (
      '<details class="ma-setup-upcoming-v3">' +
      "<summary>الخطوات القادمة (" +
      upcoming.length +
      ")</summary>" +
      '<div class="ma-setup-upcoming-v3-body">' +
      rows +
      "</div></details>"
    );
  }

  function hasActivationJourneyV2(mse) {
    return !!(mse && mse.activation_journey_v2 && mse.onboarding_journey_v2);
  }

  function journeyStepMark(status) {
    if (status === "done") return "✅";
    if (status === "current") return "▶";
    return "🔒";
  }

  function journeyStepActionHtml(st) {
    if (!st || st.status !== "current") return "";
    var href = st.action_href || "#home";
    var sec = sectionFromHref(href);
    var goAttr = sec
      ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
      : "";
    var extTarget =
      String(href).indexOf("/demo/store") >= 0
        ? ' target="_blank" rel="noopener"'
        : "";
    return (
      '<a class="ma-journey-v2-action ma-setup-btn-primary" href="' +
      esc(href) +
      '"' +
      goAttr +
      extTarget +
      ">" +
      esc(st.action_label_ar || "متابعة") +
      "</a>"
    );
  }

  function renderActivationJourneyV2(journey, root, mse) {
    var steps = journey.steps || [];
    var pct = parseInt(journey.progress_percent, 10) || 0;
    var label = esc(journey.progress_label_ar || "");
    var title = esc(journey.journey_title_ar || "تفعيل المتجر");
    var listHtml = "";
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      var cls =
        "ma-journey-v2-step is-" +
        String(st.status || "locked").replace(/[^a-z]/g, "");
      listHtml +=
        '<li class="' +
        cls +
        '">' +
        '<span class="ma-journey-v2-mark" aria-hidden="true">' +
        journeyStepMark(st.status) +
        "</span>" +
        '<div class="ma-journey-v2-body">' +
        '<p class="ma-journey-v2-title">' +
        esc(st.title_ar || "") +
        "</p>" +
        '<p class="ma-journey-v2-why">' +
        esc(st.why_ar || "") +
        "</p>" +
        journeyStepActionHtml(st) +
        "</div></li>";
    }
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-setup-unified", "1");
    root.setAttribute("data-ma-journey-v2", "1");
    root.innerHTML =
      '<div class="ma-setup-panel ma-journey-v2-panel">' +
      '<div class="ma-journey-v2-head">' +
      "<h2 class=\"ma-journey-v2-title-main\">" +
      title +
      "</h2>" +
      '<div class="ma-journey-v2-progress" role="status">' +
      '<div class="ma-journey-v2-progress-meta">' +
      '<span class="ma-journey-v2-progress-label">' +
      label +
      "</span>" +
      '<span class="ma-journey-v2-progress-pct">' +
      pct +
      "٪</span></div>" +
      '<div class="ma-journey-v2-progress-bar" aria-hidden="true">' +
      '<div class="ma-journey-v2-progress-fill" style="width:' +
      pct +
      '%;"></div></div></div></div>' +
      '<ul class="ma-journey-v2-checklist" aria-label="خطوات التفعيل">' +
      listHtml +
      "</ul>" +
      (mse && mse.delay_hint_ar
        ? '<p class="ma-journey-v2-hint">' + esc(mse.delay_hint_ar) + "</p>"
        : "") +
      "</div>";
  }

  function renderJourneyReadinessCard(journey, root) {
    var card = journey.readiness_card;
    if (!card) return;
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-journey-v2", "ready");
    var lines = (card.checklist_ar || [])
      .map(function (line) {
        return (
          '<li class="ma-journey-ready-line"><span aria-hidden="true">✓</span> ' +
          esc(line) +
          "</li>"
        );
      })
      .join("");
    root.innerHTML =
      '<div class="ma-setup-panel ma-journey-ready-card">' +
      "<h2 class=\"ma-journey-ready-title\">" +
      esc(card.title_ar || "") +
      "</h2>" +
      '<p class="ma-journey-ready-lead">' +
      esc(card.lead_ar || "") +
      "</p>" +
      '<ul class="ma-journey-ready-checklist">' +
      lines +
      "</ul>" +
      '<p class="ma-journey-ready-footer">' +
      esc(card.footer_ar || "") +
      "</p>" +
      '<a class="ma-setup-btn-primary ma-journey-ready-cta" href="' +
      esc(card.cta_href || "/dashboard#carts") +
      '" onclick="if(window.goTo){goTo(\'carts\');}return false;">' +
      esc(card.cta_label_ar || "الذهاب إلى لوحة السلال") +
      "</a></div>";
  }

  function applyActivationJourneyNavLocks(journey) {
    var locks = (journey && journey.nav_locks) || {};
    document.querySelectorAll(".ma-context-sidebar .nav-item[data-nav]").forEach(
      function (btn) {
        var page = btn.getAttribute("data-nav") || "";
        var lock = locks[page];
        var locked = !!(lock && lock.unlocked === false);
        btn.classList.toggle("is-journey-locked", locked);
        if (locked) {
          btn.setAttribute("data-journey-lock", "1");
          btn.setAttribute("title", lock.reason_ar || "");
        } else {
          btn.removeAttribute("data-journey-lock");
          btn.removeAttribute("title");
        }
      }
    );
  }

  function applyJourneyEmptyStates(journey) {
    if (!journey || journey.onboarding_complete) return;
    var hints = journey.empty_states || {};
    var cartsEmpty = document.querySelector("#page-carts tbody tr td.empty-state");
    if (cartsEmpty && hints.carts) {
      var h = hints.carts;
      cartsEmpty.innerHTML =
        '<div class="ma-journey-empty">' +
        '<div class="empty-icon">🛒</div>' +
        '<div class="empty-text ma-journey-empty-title">' +
        esc(h.title_ar || "") +
        "</div>" +
        '<p class="ma-journey-empty-body">' +
        esc(h.body_ar || "") +
        "</p>" +
        '<a class="ma-setup-btn-primary ma-journey-empty-cta" href="' +
        esc(h.cta_href || "#") +
        '">' +
        esc(h.cta_label_ar || "متابعة") +
        "</a></div>";
    }
    var msgEmpty = document.querySelector("#page-messages .empty-state");
    if (msgEmpty && hints.messages) {
      var hm = hints.messages;
      msgEmpty.innerHTML =
        '<div class="ma-journey-empty">' +
        '<div class="empty-icon">💬</div>' +
        '<div class="empty-text ma-journey-empty-title">' +
        esc(hm.title_ar || "") +
        "</div>" +
        '<p class="ma-journey-empty-body">' +
        esc(hm.body_ar || "") +
        "</p>" +
        '<a class="ma-setup-btn-primary ma-journey-empty-cta" href="' +
        esc(hm.cta_href || "#whatsapp") +
        '" onclick="if(window.goTo){goTo(\'whatsapp\');}return false;">' +
        esc(hm.cta_label_ar || "متابعة") +
        "</a></div>";
    }
  }

  function ensureJourneyGateElement(page) {
    var pageEl = byId("page-" + page);
    if (!pageEl) return null;
    var gateId = "ma-journey-gate-" + page;
    var gate = byId(gateId);
    if (!gate) {
      gate = document.createElement("div");
      gate.id = gateId;
      gate.className = "ma-journey-gate";
      gate.hidden = true;
      gate.setAttribute("hidden", "");
      pageEl.insertBefore(gate, pageEl.firstChild);
    }
    return gate;
  }

  function maApplyJourneyPageGate(page) {
    var journey = window.__maActivationJourney;
    if (!journey || journey.onboarding_complete) {
      document.querySelectorAll(".ma-journey-gate").forEach(function (g) {
        g.hidden = true;
        g.setAttribute("hidden", "");
      });
      document.querySelectorAll(".page.active .ma-page-inner").forEach(function (el) {
        el.classList.remove("ma-journey-gated");
      });
      return;
    }
    var gatedPages = ["settings", "whatsapp", "trigger-templates", "widget"];
    var i;
    for (i = 0; i < gatedPages.length; i++) {
      var p = gatedPages[i];
      var gate = ensureJourneyGateElement(p);
      var lock = journey.nav_locks && journey.nav_locks[p];
      var pageEl = byId("page-" + p);
      if (!gate || !pageEl) continue;
      if (p === page && lock && lock.unlocked === false) {
        gate.hidden = false;
        gate.removeAttribute("hidden");
        gate.innerHTML =
          '<div class="ma-journey-gate-card">' +
          '<p class="ma-journey-gate-kicker">🔒 ' +
          esc(lock.required_step_title_ar || "") +
          "</p>" +
          '<h3 class="ma-journey-gate-title">أكمل الخطوة السابقة أولاً</h3>' +
          '<p class="ma-journey-gate-body">' +
          esc(lock.reason_ar || "أكمل الخطوات بالترتيب لفتح هذا القسم.") +
          "</p>" +
          '<a class="ma-setup-btn-primary" href="' +
          esc(lock.cta_href || "/dashboard#home") +
          '">' +
          esc(lock.cta_label_ar || "متابعة الإعداد") +
          "</a></div>";
        pageEl.classList.add("ma-journey-gated");
      } else {
        gate.hidden = true;
        gate.setAttribute("hidden", "");
        if (p === page) pageEl.classList.remove("ma-journey-gated");
      }
    }
  }

  window.maApplyJourneyPageGate = maApplyJourneyPageGate;

  function applyActivationJourneySideEffects(journey) {
    window.__maActivationJourney = journey || null;
    applyActivationJourneyNavLocks(journey);
    applyJourneyEmptyStates(journey);
    try {
      var raw = (location.hash || "").split("?")[0].toLowerCase();
      var page = raw.replace(/^#/, "") || "home";
      maApplyJourneyPageGate(page);
    } catch (e) {
      maApplyJourneyPageGate("home");
    }
  }

  function renderUnifiedSetupExperience(mse, root) {
    var ready = !mse.setup_mode;
    var title = esc(mse.card_title_ar || "متجرك قريب من التشغيل الكامل");
    var contextLine =
      "اتبع الخطوة الحالية — لوحة التحكم اليومية تنتظرك بعد الإعداد.";
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-setup-unified", "1");
    root.innerHTML =
      '<div class="ma-setup-panel ma-onb-panel ma-unified-setup-panel ma-setup-v2 ma-setup-v3">' +
      (ready
        ? '<h2 class="ma-setup-home-title">' +
          title +
          "</h2>" +
          '<p class="ma-onb-celebration">' +
          esc(
            mse.celebration_message_ar ||
              "يمكن لـ CartFlow الآن البدء بمتابعة السلال."
          ) +
          "</p>"
        : '<p class="ma-setup-v2-eyebrow">' +
          esc(title) +
          "</p>" +
          '<p class="ma-setup-v2-context">' +
          esc(contextLine) +
          "</p>" +
          '<div class="ma-setup-v2-focus">' +
          unifiedSetupProgressHtml(steps) +
          unifiedSetupHeroHtml(mse) +
          unifiedSetupNextLockedHtml(steps) +
          unifiedSetupUpcomingCompactHtml(steps) +
          unifiedSetupCompletedCollapsedHtml(steps) +
          "</div>" +
          '<div class="ma-setup-v2-optional">' +
          '<div class="ma-setup-steps-toolbar">' +
          '<button type="button" class="ma-setup-btn-secondary" id="ma-setup-toggle-btn" aria-expanded="false" aria-controls="ma-setup-steps-panel">عرض كل خطوات الإعداد</button>' +
          "</div>" +
          '<div id="ma-setup-steps-panel" class="ma-setup-steps ma-setup-steps-full hidden"' +
          ' role="region" aria-label="جميع خطوات الإعداد">' +
          unifiedSetupStepsHtml(steps) +
          "</div></div>" +
          '<p class="ma-setup-daily-peek-note">معاينة يومية (نظرة عامة · ملخص الشهر · آخر السلال) بالأسفل — باهتة حتى تنهي الإعداد.</p>') +
      "</div>";

    var btn = byId("ma-setup-toggle-btn");
    var panel = byId("ma-setup-steps-panel");
    if (btn && panel) {
      btn.addEventListener("click", function () {
        panel.classList.toggle("hidden");
        var collapsed = panel.classList.contains("hidden");
        btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
        btn.textContent = collapsed
          ? "عرض كل خطوات الإعداد"
          : "إخفاء قائمة الإعداد";
      });
    }
  }

  function applyMerchantSetupExperience(mse) {
    var root = byId("ma-setup-experience-root");
    applyOnboardingHomeFocus(mse);
    hideActivationForUnifiedSetup(mse);
    if (!root) return;
    if (!mse || mse.show_card === false) {
      root.hidden = true;
      root.setAttribute("hidden", "");
      root.innerHTML = "";
      logSetupRenderDebug("setup_skip", { reason: "show_card_false", mse: !!mse });
      return;
    }
    if (shouldRenderUnifiedSetup(mse)) {
      if (hasActivationJourneyV2(mse)) {
        var journey = mse.activation_journey_v2;
        if (mse.onboarding_complete && journey.readiness_card) {
          renderJourneyReadinessCard(journey, root);
        } else {
          renderActivationJourneyV2(journey, root, mse);
        }
        applyActivationJourneySideEffects(journey);
      } else {
        renderUnifiedSetupExperience(mse, root);
      }
      showSetupExperienceRoot(root);
      logSetupRenderDebug("setup_render_unified", probeSetupExperienceRoot());
      return;
    }
    if (isUnifiedSetup(mse) && mse.setup_mode === false) {
      renderUnifiedSetupDemoToolsOnly(mse, root);
      logSetupRenderDebug("setup_render_demo_tools", probeSetupExperienceRoot());
      return;
    }
    var steps = mse.steps || [];
    var totalSteps = parseInt(mse.total_steps, 10) || steps.length || 5;
    var completed =
      parseInt(mse.completed_steps, 10) ||
      steps.filter(function (s) {
        return s.is_complete;
      }).length;
    var remaining = parseInt(mse.remaining_setup_count, 10);
    if (isNaN(remaining)) remaining = Math.max(0, totalSteps - completed);
    var ready = !!(mse.onboarding_complete || mse.first_recovery_ready);
    var title = esc(mse.card_title_ar || "إعداد متجرك");
    var lead = esc(
      mse.card_lead_ar ||
        mse.celebration_message_ar ||
        "أكمل الخطوات للوصول إلى أول جاهزية للاسترجاع."
    );
    var currentStep = esc(mse.current_step_ar || mse.next_step_ar || "—");
    var currentOutcome = esc(
      mse.current_outcome_ar || mse.outcome_summary_ar || "—"
    );
    var progressLabel = completed + " / " + totalSteps + " مكتمل";
    var panelOpen = !ready;
    showSetupExperienceRoot(root);
    root.innerHTML =
      '<div class="ma-setup-panel ma-onb-panel">' +
      '<h2 class="ma-setup-home-title">' +
      title +
      "</h2>" +
      (lead ? '<p class="ma-setup-panel-lead">' + lead + "</p>" : "") +
      (ready
        ? '<p class="ma-onb-celebration">' +
          esc(
            mse.celebration_message_ar ||
              "يمكن لـ CartFlow الآن البدء بمتابعة السلال."
          ) +
          "</p>"
        : '<div class="ma-onb-progress-row">' +
          '<span class="ma-onb-progress-k">التقدّم</span>' +
          '<span class="ma-onb-progress-v">' +
          esc(progressLabel) +
          "</span></div>" +
          '<div class="ma-setup-home-meta ma-onb-current">' +
          '<div class="ma-setup-home-row"><span class="ma-setup-home-k">الخطوة الحالية</span><span class="ma-setup-home-v">' +
          currentStep +
          "</span></div>" +
          '<div class="ma-setup-home-row"><span class="ma-setup-home-k">النتيجة المتوقعة</span><span class="ma-setup-home-v">' +
          currentOutcome +
          "</span></div></div>" +
          '<div class="ma-setup-actions">' +
          '<button type="button" class="ma-setup-btn-primary" id="ma-setup-toggle-btn" aria-expanded="' +
          (panelOpen ? "true" : "false") +
          '" aria-controls="ma-setup-steps-panel">أكمل الإعداد</button>' +
          '<a class="ma-setup-btn-secondary" href="' +
          esc(mse.action_href || "#settings") +
          '" onclick="var s=\'' +
          esc(sectionFromHref(mse.action_href || "")) +
          "';if(window.goTo&&s){goTo(s);}return false;\">انتقل للخطوة</a>" +
          "</div>" +
          '<div id="ma-setup-steps-panel" class="ma-setup-steps"' +
          (panelOpen ? "" : " hidden") +
          ' role="region" aria-label="خطوات الإعداد">' +
          setupStepsHtml(steps) +
          "</div>") +
      "</div>";

    var btn = byId("ma-setup-toggle-btn");
    var panel = byId("ma-setup-steps-panel");
    if (btn && panel) {
      btn.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
        btn.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
      });
    }
  }

  function applyTopbarReadiness(d) {
    var sk = (d.wa_state_key || "").trim();
    var badge = d.wa_badge_ar || "—";
    var pPill = byId("ma-page-whatsapp-ready-pill");
    var pTxt = byId("ma-page-whatsapp-ready-text");
    if (pPill && pTxt) {
      pPill.classList.toggle("wa-muted", sk !== "ready");
      pTxt.textContent = badge;
    }
  }

  function reasonWeekRowHtml(rr) {
    var pct = parseFloat(rr.count_pct) || 0;
    var col = esc(rr.fill_color || "#6C5CE7");
    return (
      '<div class="r-row">' +
      '<div class="r-head"><span class="r-name">' +
      esc(rr.label_ar) +
      '</span><span class="r-pct">' +
      Math.round(pct) +
      "٪</span></div>" +
      '<div class="track"><div class="fill" style="width:' +
      pct +
      "%;background:" +
      col +
      ';"></div></div></div>'
    );
  }

  function reasonMonthRowHtml(rb) {
    var pct = parseFloat(rb.count_pct) || 0;
    var col = esc(rb.fill_color || "#6C5CE7");
    return (
      '<div class="r-big">' +
      '<div class="r-big-head"><span class="r-big-name">' +
      esc(rb.label_ar) +
      '</span><span class="r-big-pct">' +
      Math.round(pct) +
      "٪</span></div>" +
      '<div class="track-lg"><div class="fill-lg" style="width:' +
      pct +
      "%;background:" +
      col +
      ';"></div></div></div>'
    );
  }

  function applySummary(d) {
    if (!d || !d.ok) {
      logSetupRenderDebug("summary_skip", { ok: !!(d && d.ok) });
      return;
    }
    var dbg =
      d.merchant_setup_render_debug ||
      (d.merchant_setup_experience &&
        d.merchant_setup_experience.MERCHANT_SETUP_RENDER_BUILD
        ? {
            MERCHANT_SETUP_RENDER_BUILD:
              d.merchant_setup_experience.MERCHANT_SETUP_RENDER_BUILD,
            unified_p0: d.merchant_setup_experience.unified_p0,
            setup_mode: d.merchant_setup_experience.setup_mode,
            show_card: d.merchant_setup_experience.show_card,
          }
        : null);
    logSetupRenderDebug("summary_payload", dbg);
    setText("ma-topbar-date", d.merchant_ar_date_header || "");
    ingestRefreshToken(d, "summary");
    applyTopbarReadiness(d);
    applyMerchantSetupExperience(d.merchant_setup_experience);
    if (
      d.merchant_setup_experience &&
      d.merchant_setup_experience.activation_journey_v2
    ) {
      applyActivationJourneySideEffects(
        d.merchant_setup_experience.activation_journey_v2
      );
    }
    applyHomeLayoutAfterSetup(d.merchant_activation, d.merchant_setup_experience);
    logSetupRenderDebug("summary_dom", probeSetupExperienceRoot());

    setText("ma-kpi-abandoned", d.merchant_kpi_abandoned_fmt || "0");
    setText("ma-kpi-recovered", d.merchant_kpi_recovered_fmt || "0");
    setText("ma-kpi-wa", d.merchant_kpi_wa_sent_fmt || "0");
    setText("ma-kpi-revenue", d.merchant_kpi_revenue_fmt || "0");

    var pct = parseFloat(d.merchant_kpi_recovered_pct_vs_abandoned) || 0;
    var note = byId("ma-kpi-recovered-note");
    if (note) {
      stripSkel(note);
      if (pct > 0) {
        note.textContent = "↑ نسبة " + Math.round(pct) + "٪";
        note.className = "kpi-note up";
      } else {
        note.textContent = "—";
        note.className = "kpi-note neutral";
      }
    }

    setText("ma-month-abandoned", d.merchant_month_abandoned_fmt || "0");
    setText("ma-month-recovered", d.merchant_month_recovered_fmt || "0");
    setText("ma-month-pct", (d.merchant_month_recovery_pct_fmt || "0") + "٪");
    setText("ma-month-revenue", (d.merchant_month_revenue_fmt || "0") + " ر");

    var wk = byId("ma-reasons-week-body");
    if (wk) {
      var rowsW = d.merchant_reason_rows_week || [];
      var htmlW = "";
      if (!rowsW.length) {
        htmlW =
          '<div class="empty-text" style="padding:12px;color:var(--muted);">لا توجد بيانات أسباب التردد لهذا الأسبوع</div>';
      } else {
        htmlW = rowsW.map(reasonWeekRowHtml).join("");
      }
      if (d.merchant_reason_insight_ar) {
        htmlW +=
          '<div class="r-insight">' + esc(d.merchant_reason_insight_ar) + "</div>";
      }
      wk.innerHTML = htmlW;
    }

    var mo = byId("ma-reasons-month-body");
    if (mo) {
      var h3 = mo.querySelector("h3");
      var h3txt = h3 ? h3.outerHTML : "<h3>توزيع الأسباب — آخر 30 يوماً</h3>";
      var rowsM = d.merchant_reason_rows_month || [];
      if (!rowsM.length) {
        mo.innerHTML =
          h3txt +
          '<div class="empty-text" style="padding:16px;">لا توجد بيانات أسباب كافية لهذه الفترة</div>';
      } else {
        mo.innerHTML = h3txt + rowsM.map(reasonMonthRowHtml).join("");
      }
    }

    var ins = byId("ma-reasons-insights");
    if (ins) {
      var lines = d.merchant_reason_recommendations_ar || [];
      var body = lines
        .map(function (ln) {
          return '<div class="ib-item">📌 ' + esc(ln) + "</div>";
        })
        .join("");
      if (!body) {
        body = '<div class="ib-item">—</div>';
      }
      ins.innerHTML = '<div class="ib-title">💡 توصيات</div>' + body;
    }

    setNavBadge("ma-nav-badge-abandoned", d.merchant_nav_badge_abandoned);
    setNavBadge("ma-nav-badge-followup", d.merchant_nav_badge_followup);
    setNavBadge("ma-nav-badge-vip", d.merchant_nav_badge_vip);

    var sm = byId("ma-settings-month-cart-line");
    if (sm) {
      sm.textContent =
        (d.merchant_month_abandoned_fmt || "0") + " سلة مسجّلة";
    }
  }

  var MERCHANT_INTERVENTION_PRIMARY_KEYS = {
    channel_failed: 1,
    needs_phone: 1,
    needs_reason: 1,
    attempts_exhausted: 1,
    stopped_manual: 1,
  };

  var MERCHANT_REASON_GOAL_AR = {
    price: "معالجة قلق السعر",
    price_high: "معالجة قلق السعر",
    shipping: "طمأنة حول الشحن",
    delivery: "طمأنة حول الشحن",
    thinking: "دعم اتخاذ القرار",
    warranty: "طمأنة حول الجودة",
    quality: "طمأنة حول الجودة",
    human_support: "طمأنة حول الجودة",
    trust: "طمأنة حول الجودة",
  };

  function merchantReasonGoalAr(reasonTag) {
    var k = String(reasonTag || "")
      .trim()
      .toLowerCase();
    if (!k) return "";
    return MERCHANT_REASON_GOAL_AR[k] || "متابعة سبب التردد";
  }

  function merchantTruncateText(text, maxLen) {
    var raw = String(text || "").trim();
    if (!raw) return "";
    if (raw.length <= maxLen) return raw;
    return raw.slice(0, maxLen - 1).trim() + "…";
  }

  function merchantPreviewFromWhatsappLine(line) {
    var s = String(line || "").trim();
    if (!s || s.indexOf("—") < 0) return "";
    var tail = s.split("—").slice(1).join("—").trim();
    if (tail.indexOf("(") === 0 && tail.lastIndexOf(")") === tail.length - 1) {
      tail = tail.slice(1, -1).trim();
    }
    if (tail && tail.indexOf("ننتظر") !== 0) return tail;
    return "";
  }

  function merchantSentMessageLine(mc) {
    var prev =
      String(mc.message_preview || "").trim() ||
      merchantPreviewFromWhatsappLine(mc.merchant_whatsapp_line_ar);
    if (prev) return '"' + merchantTruncateText(prev, 80) + '"';
    return "تم إرسال رسالة مناسبة لسبب التردد";
  }

  function merchantAttemptsDisplayAr(fr) {
    fr = fr || {};
    var raw = String(fr.attempts_ar || "").trim();
    var inbound = String(fr.inbound_message || "").trim();
    var replied = !!inbound;
    if (!replied) {
      var line = String(fr.last_message_line_ar || "").trim();
      replied =
        line.length > 0 &&
        line.indexOf("لا يوجد رد") < 0 &&
        line.indexOf("يتابع النظام") < 0;
    }
    var m = raw.match(/(\d+)\s*رسالة/);
    var n = m ? parseInt(m[1], 10) : 0;
    if (raw.indexOf("عدد الرسائل:") === 0) return raw;
    if (raw.indexOf("تمت متابعة") === 0) return raw;
    if (raw.indexOf("أُرسلت رسالة —") === 0) return raw;
    if (raw.indexOf("تم إرسال أول") === 0) return raw;
    if (raw.indexOf("لم تبدأ") === 0) return raw;
    if (n >= 3) return "عدد الرسائل: " + n;
    if (n === 2) return "تمت متابعة إضافية";
    if (n === 1) return "أُرسلت رسالة — لا توجد متابعات إضافية بعد";
    if (replied) return "تم إرسال أول رسالة استرداد";
    if (n === 0 && raw.indexOf("لا توجد") >= 0) {
      return replied ? "تم إرسال أول رسالة استرداد" : "لم تبدأ عملية الاسترداد بعد";
    }
    return raw || "—";
  }

  function merchantReplyPreview(fr) {
    var raw = String((fr && fr.inbound_message) || "").trim();
    if (!raw && fr && fr.last_message_line_ar) {
      var line = String(fr.last_message_line_ar).trim();
      if (
        line &&
        line.indexOf("لا يوجد رد") < 0 &&
        line.indexOf("يتابع النظام") < 0
      ) {
        raw = line;
      }
    }
    if (!raw) return "";
    return '"' + merchantTruncateText(raw, 60) + '"';
  }

  function merchantNeedsIntervention(mc) {
    if (!mc) return false;
    if (mc.merchant_next_action_urgent) return true;
    var pk = String(mc.merchant_lifecycle_primary_key || "")
      .trim()
      .toLowerCase();
    return !!MERCHANT_INTERVENTION_PRIMARY_KEYS[pk];
  }


  function merchantLifecycleCompact(mc) {
    var pk = String(mc.merchant_lifecycle_primary_key || "")
      .trim()
      .toLowerCase();
    var coarse = String(
      mc.merchant_coarse_status || mc.recovery_status || ""
    )
      .trim()
      .toLowerCase();
    var needs = merchantNeedsIntervention(mc);
    var pur = String(mc.merchant_purchase_line_ar || "").trim();
    var ret = String(mc.merchant_return_line_ar || "").trim();
    var status = "قيد المتابعة";
    var action = "النظام يتابع تلقائياً";
    var waiting = "النظام يتابع تلقائياً";
    if (pk === "customer_replied" || coarse === "replied" || coarse === "engaged") {
      status = "تفاعل العميل";
      action = "بدأ النظام متابعة الاعتراض";
      waiting = "النظام يتابع تلقائياً";
    } else if (pur || pk === "purchase_complete" || coarse === "converted") {
      status = "اكتمل الشراء";
      action = "انتهت مهمة الاسترجاع";
      waiting = "—";
    } else if (ret || pk === "customer_returned" || coarse === "returned") {
      status = "عاد للموقع";
      action = "أوقفنا الرسائل";
      waiting = "—";
    } else if (
      pk === "awaiting_customer_after_send" ||
      pk === "message_sent" ||
      coarse === "sent"
    ) {
      status = "أُرسلت رسالة";
      action = "—";
      waiting = "ننتظر تفاعل العميل";
    } else if (
      pk === "delay_waiting" ||
      pk === "no_engagement_yet" ||
      pk === "automation_paused" ||
      pk === "pending_schedule" ||
      coarse === "pending"
    ) {
      status = "بانتظار الإرسال";
      action = "—";
      waiting = "بانتظار وقت الإرسال";
    } else if (
      pk === "channel_failed" ||
      pk === "needs_phone" ||
      pk === "needs_reason" ||
      pk === "attempts_exhausted"
    ) {
      status = "يحتاج إجراء";
      action = "راجع الإعدادات";
      waiting = "—";
    }
    var isSent =
      pk === "awaiting_customer_after_send" ||
      pk === "message_sent" ||
      coarse === "sent";
    var isInteraction =
      pk === "customer_replied" || coarse === "replied" || coarse === "engaged";
    return {
      status: status,
      action: action,
      waiting: waiting,
      needsIntervention: needs,
      messageLine: isSent ? merchantSentMessageLine(mc) : "",
      goalLine: merchantReasonGoalAr(mc.reason_tag) || "",
      isSent: isSent,
      isInteraction: isInteraction,
    };
  }

  function merchantLifecycleCompactHtml(mc) {
    var c = merchantLifecycleCompact(mc);
    var h =
      '<div class="recovery-truth recovery-truth-compact" aria-label="ملخص المسار">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> ' +
      esc(c.status) +
      "</div>";
    if (c.messageLine) {
      h +=
        '<div class="recovery-truth-line"><strong>الرسالة:</strong> ' +
        esc(c.messageLine) +
        "</div>";
    }
    if (c.goalLine) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> ' +
        esc(c.goalLine) +
        "</div>";
    } else if (c.isSent) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> اختار النظام رسالة مناسبة بناءً على سبب التردد.</div>';
    }
    if (c.waiting && c.waiting !== "—") {
      h +=
        '<div class="recovery-truth-line"><strong>الانتظار:</strong> ' +
        esc(c.waiting) +
        "</div>";
    }
    h += merchantFollowupClarityHtml(mc);
    if (c.action && c.action !== "—" && !c.isSent) {
      h +=
        '<div class="recovery-truth-line"><strong>الإجراء:</strong> ' +
        esc(c.action) +
        "</div>";
    }
    h +=
      '<div class="recovery-truth-line' +
      (c.needsIntervention ? "" : " recovery-truth-muted") +
      '"><strong>تدخل:</strong> ' +
      (c.needsIntervention ? "نعم" : "لا") +
      "</div>";
    return h + "</div>";
  }

  function followupCompactHtml(fr) {
    fr = fr || {};
    var goal = merchantReasonGoalAr(fr.reason_tag_raw || fr.reason_tag_ar);
    var reply = merchantReplyPreview(fr);
    var h =
      '<div class="recovery-truth recovery-truth-compact" aria-label="ملخص التفاعل">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> تفاعل العميل</div>';
    if (reply) {
      h +=
        '<div class="recovery-truth-line"><strong>رد العميل:</strong> ' +
        esc(reply) +
        "</div>";
    }
    h +=
      '<div class="recovery-truth-line"><strong>الإجراء:</strong> بدأ النظام متابعة الاعتراض</div>';
    if (goal) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> ' +
        esc(goal) +
        "</div>";
    } else if (fr.reason_tag_raw) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> اختار النظام رسالة مناسبة بناءً على سبب التردد.</div>';
    }
    h +=
      '<div class="recovery-truth-line"><strong>الانتظار:</strong> النظام يتابع تلقائياً</div>';
    h +=
      '<div class="recovery-truth-line recovery-truth-muted"><strong>تدخل:</strong> لا</div>';
    return h + "</div>";
  }

  function merchantNextLineShort(mc) {
    return merchantLifecycleCompact(mc).status;
  }

  var lastNormalCartsPageRows = [];

  function isArchivedVisual(mc) {
    if (!mc) return false;
    if (mc.customer_lifecycle_is_archived_visual === true) return true;
    return String(mc.customer_lifecycle_state || "").trim() === "archived";
  }

  function cartLifecycleStatusClass(mc) {
    if (isArchivedVisual(mc)) return "s-archived";
    return (
      mc.customer_lifecycle_status_row_class ||
      mc.merchant_status_row_class ||
      "s-waiting"
    );
  }

  function cartLifecycleStatusLabel(mc) {
    if (isArchivedVisual(mc)) return "✓ مؤرشفة";
    return (
      mc.customer_lifecycle_label_ar || mc.merchant_status_label_ar || "—"
    );
  }

  function sortCartsArchivedLast(rows) {
    return rows.slice().sort(function (a, b) {
      var aa = isArchivedVisual(a) ? 1 : 0;
      var bb = isArchivedVisual(b) ? 1 : 0;
      if (aa !== bb) return aa - bb;
      return 0;
    });
  }

  function cartRowMatchesFilterMode(mc, mode) {
    var m = (mode || "all").trim().toLowerCase();
    if (m === "completed") m = "recovered";
    if (m === "all") return true;
    if (!mc) return false;
    var primary = String(mc.merchant_cart_primary_bucket || "")
      .trim()
      .toLowerCase();
    if (primary && (primary === m || (m === "recovered" && primary === "completed"))) {
      return true;
    }
    var bucket = String(mc.merchant_cart_bucket || "").trim().toLowerCase();
    if (
      bucket &&
      (bucket === m || (m === "recovered" && bucket === "completed"))
    ) {
      return true;
    }
    var tabs = mc.merchant_cart_visible_tabs;
    if (Array.isArray(tabs)) {
      for (var i = 0; i < tabs.length; i++) {
        var tk = String(tabs[i] || "").trim().toLowerCase();
        if (tk === m || (m === "recovered" && tk === "completed")) return true;
      }
    }
    if (m === "recovered") {
      return isCompletedDashboardRow(mc);
    }
    return false;
  }

  function isCompletedDashboardRow(mc) {
    if (!mc) return false;
    var lc = String(mc.customer_lifecycle_state || "").trim().toLowerCase();
    if (lc === "completed") return true;
    if (String(mc.merchant_coarse_status || "").trim().toLowerCase() === "converted") {
      return true;
    }
    if (String(mc.customer_lifecycle_completed_variant || "").trim() === "purchased") {
      return true;
    }
    var primary = String(mc.merchant_cart_primary_bucket || "").trim().toLowerCase();
    if (primary === "recovered" || primary === "completed") return true;
    var bucket = String(mc.merchant_cart_bucket || "").trim().toLowerCase();
    if (bucket === "recovered" || bucket === "completed") return true;
    var tabs = mc.merchant_cart_visible_tabs;
    if (Array.isArray(tabs)) {
      for (var i = 0; i < tabs.length; i++) {
        var tk = String(tabs[i] || "").trim().toLowerCase();
        if (tk === "recovered" || tk === "completed") return true;
      }
    }
    var lbl = String(
      mc.customer_lifecycle_label_ar || mc.merchant_status_label_ar || ""
    );
    if (lbl.indexOf("تم الشراء") >= 0) return true;
    if (lbl.indexOf("تمت الاستعادة") >= 0) return true;
    if (lbl.indexOf("تم الاسترجاع") >= 0) return true;
    if (mc.merchant_cart_is_terminal === true && lbl.indexOf("تم") >= 0) {
      return true;
    }
    return false;
  }

  function trLooksCompletedRow(tr) {
    if (!tr) return false;
    if (tr.getAttribute("data-ma-completed") === "1") return true;
    if (tr.getAttribute("data-ma-archived-visual") === "1") return false;
    var filter = (tr.getAttribute("data-ma-filter") || "").trim().toLowerCase();
    if (filter === "recovered" || filter === "completed") return true;
    var primary = (tr.getAttribute("data-ma-primary-bucket") || "")
      .trim()
      .toLowerCase();
    if (primary === "recovered" || primary === "completed") return true;
    try {
      var tabs = JSON.parse(tr.getAttribute("data-ma-visible-tabs") || "[]");
      if (Array.isArray(tabs)) {
        for (var i = 0; i < tabs.length; i++) {
          var tk = String(tabs[i] || "").trim().toLowerCase();
          if (tk === "recovered" || tk === "completed") return true;
        }
      }
    } catch (eTabs) {
      /* ignore */
    }
    var txt = tr.textContent || "";
    if (txt.indexOf("تم الشراء") >= 0) return true;
    if (txt.indexOf("تمت الاستعادة") >= 0) return true;
    return false;
  }

  function completedCartsFromRows(rows) {
    return sortCartsArchivedLast(rows || []).filter(function (mc) {
      return isCompletedDashboardRow(mc);
    });
  }

  function completedRowsHtmlFromAllTableDom() {
    var src = document.querySelector("#ma-tbody-all-carts");
    if (!src) return "";
    var html = "";
    var n = 0;
    src.querySelectorAll("tr[data-ma-filter]").forEach(function (tr) {
      if (!trLooksCompletedRow(tr)) return;
      html += tr.outerHTML;
      n += 1;
    });
    return n ? html : "";
  }

  function logCompletedTab(total, completed, source) {
    try {
      console.log(
        "[COMPLETED TAB] rows_total=" +
          String(total == null ? 0 : total) +
          " completed_rows=" +
          String(completed == null ? 0 : completed) +
          (source ? " source=" + source : "")
      );
    } catch (eLog) {
      /* ignore */
    }
  }

  function applyCompletedCartsTable(rows) {
    var tbody = byId("ma-tbody-completed");
    var total = (rows || []).length;
    if (!tbody) {
      logCompletedTab(total, 0, "missing_tbody");
      return;
    }
    var completed = completedCartsFromRows(rows);
    if (completed.length) {
      tbody.innerHTML = completed.map(cartRowFull).join("");
      bindCustomerLifecycleActions(tbody);
      logCompletedTab(total, completed.length, "payload");
      return;
    }
    var domHtml = completedRowsHtmlFromAllTableDom();
    if (domHtml) {
      tbody.innerHTML = domHtml;
      bindCustomerLifecycleActions(tbody);
      var domCount = tbody.querySelectorAll("tr[data-ma-filter]").length;
      logCompletedTab(total, domCount, "dom_from_all_tab");
      return;
    }
    tbody.innerHTML =
      '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">✅</div><div class="empty-text">لا توجد سلال مكتملة حالياً ضمن نطاق متجرك</div></td></tr>';
    logCompletedTab(total, 0, "empty");
  }

  window.maRefreshCompletedCartsTable = function () {
    var rows = lastNormalCartsPageRows || [];
    if (!rows.length && window.__maNormalCartsPageRows) {
      rows = window.__maNormalCartsPageRows;
    }
    applyCompletedCartsTable(rows);
    if (
      !rows.length &&
      !window.__maCompletedTabFetchPending &&
      typeof fetchSection === "function"
    ) {
      window.__maCompletedTabFetchPending = true;
      fetchSection(
        "/api/dashboard/normal-carts",
        function (d) {
          window.__maCompletedTabFetchPending = false;
          applyNormalCarts(d);
        },
        "normal_carts_completed_retry"
      );
    }
  };

  function cartLifecycleActionBtnHtml(mc) {
    var rk = String(mc.recovery_key || "").trim();
    var act = String(mc.customer_lifecycle_dashboard_action || "").trim();
    if (!rk) return "";
    if (act === "archive") {
      return (
        '<div class="recovery-truth-actions"><button type="button" class="cf-lc-btn cf-lc-btn-archive" data-lc-archive data-recovery-key="' +
        esc(rk) +
        '"><span class="cf-lc-btn-icon" aria-hidden="true">🗂</span> نقل للأرشيف</button></div>'
      );
    }
    if (act === "reopen") {
      return (
        '<div class="recovery-truth-actions"><button type="button" class="cf-lc-btn cf-lc-btn-reopen" data-lc-reopen data-recovery-key="' +
        esc(rk) +
        '"><span class="cf-lc-btn-icon" aria-hidden="true">↩</span> إعادة فتح</button></div>'
      );
    }
    return "";
  }

  function customerLifecycleArchivedCompactHtml(mc) {
    var h =
      '<div class="recovery-truth recovery-truth-compact customer-lifecycle-v1 customer-lifecycle-archived" aria-label="سلة مؤرشفة">';
    h +=
      '<div class="lc-archived-head"><span class="lc-archived-badge">مؤرشفة ✓</span></div>';
    h +=
      '<p class="lc-archived-line">تم إغلاق هذه الحالة من العرض النشط.</p>';
    h +=
      '<p class="lc-archived-line lc-archived-muted">لن يرسل النظام متابعات لهذه الحالة أثناء الأرشفة.</p>';
    h += cartLifecycleActionBtnHtml(mc);
    return h + "</div>";
  }

  function merchantFollowupClarityHtml(mc) {
    if (!mc) return "";
    var prog = String(mc.merchant_followup_progress_ar || "").trim();
    var seq = String(mc.merchant_followup_sequence_line_ar || "").trim();
    var nxt = String(mc.merchant_followup_next_line_ar || "").trim();
    if (!prog && !seq && !nxt) return "";
    var h =
      '<div class="recovery-truth-followup-clarity" aria-label="تقدم المتابعة">';
    if (prog) {
      h +=
        '<div class="recovery-truth-line merchant-followup-progress"><strong>المتابعة:</strong> ' +
        esc(prog) +
        "</div>";
    }
    if (seq) {
      h +=
        '<div class="recovery-truth-line recovery-truth-muted merchant-followup-sequence">' +
        esc(seq) +
        "</div>";
    }
    if (nxt) {
      h +=
        '<div class="recovery-truth-line merchant-followup-next">' +
        esc(nxt) +
        "</div>";
    }
    return h + "</div>";
  }

  function continuationDecisionExplanationHtml(mc) {
    var expl =
      mc.customer_lifecycle_continuation_explanation_ar ||
      mc.normal_recovery_continuation_explanation_ar ||
      "";
    expl = String(expl || "").trim();
    if (!expl) return "";
    return (
      '<div class="recovery-truth-line recovery-truth-highlight customer-lifecycle-cont-expl">' +
      esc(expl) +
      "</div>"
    );
  }

  function customerLifecycleExplanationHtml(mc) {
    if (!mc || !mc.customer_lifecycle_state) {
      return merchantLifecycleCompactHtml(mc);
    }
    if (isArchivedVisual(mc)) {
      return customerLifecycleArchivedCompactHtml(mc);
    }
    var h =
      '<div class="recovery-truth recovery-truth-compact customer-lifecycle-v1" aria-label="حالة دورة العميل">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> ' +
      esc(mc.customer_lifecycle_label_ar || "—") +
      "</div>";
    if (mc.customer_lifecycle_what_happened_ar) {
      h +=
        '<div class="recovery-truth-line"><strong>ماذا حدث؟</strong> ' +
        esc(mc.customer_lifecycle_what_happened_ar) +
        "</div>";
    }
    if (mc.customer_lifecycle_system_did_ar) {
      h +=
        '<div class="recovery-truth-line"><strong>ماذا فعل النظام؟</strong> ' +
        esc(mc.customer_lifecycle_system_did_ar) +
        "</div>";
    }
    if (mc.customer_lifecycle_what_next_ar) {
      h +=
        '<div class="recovery-truth-line"><strong>التالي:</strong> ' +
        esc(mc.customer_lifecycle_what_next_ar) +
        "</div>";
    }
    if (mc.customer_lifecycle_next_followup_line_ar) {
      h +=
        '<div class="recovery-truth-line"><strong>المتابعة:</strong> ' +
        esc(mc.customer_lifecycle_next_followup_line_ar) +
        "</div>";
    }
    h += merchantFollowupClarityHtml(mc);
    h +=
      '<div class="recovery-truth-line"><strong>تدخل التاجر:</strong> ' +
      esc(mc.customer_lifecycle_merchant_needed_ar || "لا") +
      "</div>";
    h += continuationDecisionExplanationHtml(mc);
    h += cartLifecycleActionBtnHtml(mc);
    return h + "</div>";
  }

  function patchCartRowArchivedVisual(rk, archived, lifecycle) {
    var key = String(rk || "").trim();
    if (!key) return;
    lastNormalCartsPageRows.forEach(function (mc) {
      if (String(mc.recovery_key || "").trim() !== key) return;
      if (archived) {
        mc.customer_lifecycle_is_archived_visual = true;
        mc.customer_lifecycle_state = "archived";
        mc.customer_lifecycle_label_ar = "مؤرشفة";
        mc.customer_lifecycle_dashboard_action = "reopen";
        mc.customer_lifecycle_status_row_class = "s-archived";
        mc.merchant_status_row_class = "s-archived";
        mc.merchant_status_label_ar = "مؤرشفة";
        mc.merchant_next_action_urgent = false;
      } else if (lifecycle && typeof lifecycle === "object") {
        Object.keys(lifecycle).forEach(function (k) {
          if (lifecycle[k] !== undefined && lifecycle[k] !== null) {
            mc[k] = lifecycle[k];
          }
        });
        if (lifecycle.merchant_status_label_ar) {
          mc.merchant_status_label_ar = lifecycle.merchant_status_label_ar;
        }
        if (lifecycle.merchant_status_row_class) {
          mc.merchant_status_row_class = lifecycle.merchant_status_row_class;
        }
        mc.merchant_next_action_urgent = false;
      } else {
        mc.customer_lifecycle_is_archived_visual = false;
      }
    });
  }

  function rerenderAllCartsTable() {
    var allb = byId("ma-tbody-all-carts");
    if (!allb) return;
    var sorted = sortCartsArchivedLast(lastNormalCartsPageRows);
    allb.innerHTML = sorted.map(cartRowFull).join("");
    bindCustomerLifecycleActions(allb);
  }

  function lifecycleTruthHtml(mc) {
    return customerLifecycleExplanationHtml(mc);
  }

  function bindCustomerLifecycleActions(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll("[data-lc-archive]").forEach(function (btn) {
      if (btn._lcBound) return;
      btn._lcBound = true;
      btn.addEventListener("click", function () {
        var rk = btn.getAttribute("data-recovery-key") || "";
        if (!rk) return;
        fetch("/api/dashboard/cart-lifecycle/archive", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ recovery_key: rk }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d && d.ok) {
              patchCartRowArchivedVisual(rk, true);
              rerenderAllCartsTable();
              fetchSection(
                "/api/dashboard/normal-carts",
                applyNormalCarts,
                "normal-carts"
              );
            }
          })
          .catch(function () {});
      });
    });
    root.querySelectorAll("[data-lc-reopen]").forEach(function (btn) {
      if (btn._lcBound) return;
      btn._lcBound = true;
      btn.addEventListener("click", function () {
        var rk = btn.getAttribute("data-recovery-key") || "";
        if (!rk) return;
        fetch("/api/dashboard/cart-lifecycle/reopen", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ recovery_key: rk }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d && d.ok) {
              patchCartRowArchivedVisual(rk, false, d.lifecycle || null);
              rerenderAllCartsTable();
              fetchSection(
                "/api/dashboard/normal-carts",
                applyNormalCarts,
                "normal-carts"
              );
            }
          })
          .catch(function () {});
      });
    });
  }

  function cartRowHome(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var phoneOk =
      (mc.merchant_phone_line_ar || "").indexOf("متوفر") >= 0;
    var ph = phoneOk
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    var urg = mc.merchant_next_action_urgent ? " urgent" : "";
    return (
      "<tr>" +
      "<td><div class=\"camt\">" +
      v.toLocaleString("en-US") +
      ' ر</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(cartLifecycleStatusClass(mc)) +
      '\"><span class="sd"></span>' +
      esc(cartLifecycleStatusLabel(mc)) +
      "</span></td>" +
      "<td>" +
      (isArchivedVisual(mc)
        ? ""
        : '<div class="next' +
          urg +
          '">' +
          esc(merchantNextLineShort(mc) || mc.merchant_next_action_ar || "—") +
          "</div>") +
      lifecycleTruthHtml(mc) +
      "</td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function cartRowFull(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var hasPh = !!mc.merchant_has_customer_phone;
    var ph = hasPh
      ? '<span class="ph-ok">✓</span>'
      : '<span class="ph-no">✗</span>';
    var b = esc(mc.merchant_cart_bucket || "other");
    var primary = esc(mc.merchant_cart_primary_bucket || b);
    var tabsJson = "[]";
    try {
      tabsJson = esc(JSON.stringify(mc.merchant_cart_visible_tabs || []));
    } catch (eTabs) {
      tabsJson = "[]";
    }
    var urg =
      mc.merchant_next_action_urgent && !isArchivedVisual(mc) ? " urgent" : "";
    var archived = isArchivedVisual(mc);
    var statusLbl = cartLifecycleStatusLabel(mc);
    var nextLbl =
      mc.customer_lifecycle_label_ar ||
      merchantNextLineShort(mc) ||
      mc.merchant_next_action_ar ||
      "—";
    var completedRow = isCompletedDashboardRow(mc);
    return (
      '<tr data-ma-filter="' +
      b +
      '" data-ma-primary-bucket="' +
      primary +
      '" data-ma-visible-tabs="' +
      tabsJson +
      '"' +
      (completedRow ? ' data-ma-completed="1"' : "") +
      (archived ? ' class="ma-row-archived" data-ma-archived-visual="1"' : "") +
      ">" +
      "<td><div class=\"camt\">" +
      v.toLocaleString("en-US") +
      ' ر</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(cartLifecycleStatusClass(mc)) +
      '\"><span class="sd"></span>' +
      esc(statusLbl) +
      "</span></td>" +
      "<td>" +
      (archived
        ? ""
        : '<div class="next' + urg + '">' + esc(nextLbl) + "</div>") +
      lifecycleTruthHtml(mc) +
      "</td>" +
      '<td><div class="ctime">' +
      esc(mc.merchant_last_seen_display || "—") +
      "</div></td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function applyNormalCarts(d) {
    if (!d || !d.ok) return;
    ingestRefreshToken(d, "normal-carts");
    lastNormalCartsPageRows = d.merchant_carts_page_rows || [];
    window.__maNormalCartsPageRows = lastNormalCartsPageRows;
    var home = byId("ma-tbody-home-carts");
    if (home) {
      var tr = d.merchant_table_rows || [];
      if (!tr.length) {
        home.innerHTML =
          '<tr><td colspan="5" class="empty-text" style="text-align:center;padding:24px;color:var(--muted);">لا توجد سلال ضمن النشاط الحالي</td></tr>';
      } else {
        home.innerHTML = tr.map(cartRowHome).join("");
      }
    }
    var allb = byId("ma-tbody-all-carts");
    if (allb) {
      var pr = sortCartsArchivedLast(lastNormalCartsPageRows);
      if (!pr.length) {
        allb.innerHTML =
          '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">🛒</div><div class="empty-text">لا توجد سلال متروكة مسجّلة حالياً ضمن نطاق متجرك</div></td></tr>';
      } else {
        allb.innerHTML = pr.map(cartRowFull).join("");
      }
      bindCustomerLifecycleActions(allb);
    }
    applyCompletedCartsTable(lastNormalCartsPageRows);
    var fc = d.merchant_cart_filter_counts || {};
    function sf(k, id) {
      var el = byId(id);
      if (el) el.textContent = String(fc[k] != null ? fc[k] : 0);
    }
    sf("all", "ma-filt-all");
    sf("recovered", "ma-filt-recovered");
    sf("sent", "ma-filt-sent");
    sf("attention", "ma-filt-attention");
    sf("nophone", "ma-filt-nophone");
    if (d.merchant_nav_badge_abandoned != null) {
      setNavBadge("ma-nav-badge-abandoned", d.merchant_nav_badge_abandoned);
    } else if (fc.waiting != null) {
      setNavBadge("ma-nav-badge-abandoned", fc.waiting);
    }
    if (window.merchantAppReinitCartFilters) {
      window.merchantAppReinitCartFilters();
    }
    try {
      var hashRaw = (location.hash || "").split("?")[0].toLowerCase();
      var hashQs = (location.hash || "").split("?")[1] || "";
      var tab = new URLSearchParams(hashQs).get("tab");
      if (hashRaw === "#completed" && typeof window.maRefreshCompletedCartsTable === "function") {
        window.maRefreshCompletedCartsTable();
      } else if (tab && typeof window.applyCartTabFilters === "function") {
        window.applyCartTabFilters(tab);
      }
    } catch (eHash) {
      /* ignore */
    }
  }

  function applyVipHomeBanner(ban) {
    var host = byId("ma-home-vip-banner");
    if (!host) return;
    if (!ban || !ban.amount_line) {
      host.style.display = "none";
      host.innerHTML = "";
      return;
    }
    host.style.display = "";
    var btn =
      window.maVipAutomation && typeof window.maVipAutomation.renderBannerBtn === "function"
        ? window.maVipAutomation.renderBannerBtn(ban)
        : "";
    if (!btn) {
      var href = ban.contact_href || "";
      btn = href
        ? '<a class="va-btn" href="' + esc(href) + '">تواصل يدوي (VIP) ←</a>'
        : '<span class="va-btn is-disabled" role="button" aria-disabled="true">تواصل يدوي (VIP) ←</span>';
    }
    host.innerHTML =
      '<div class="vip-alert"><div class="va-icon">👑</div><div class="va-body">' +
      '<div class="va-title">عميل VIP يحتاج تدخلك — لن يُرسَل له واتساب تلقائياً</div>' +
      '<div class="va-sub">' +
      esc(ban.amount_line) +
      "</div></div>" +
      btn +
      "</div>";
  }

  function vipItemHtml(vr) {
    var btn =
      window.maVipAutomation && typeof window.maVipAutomation.renderHomeItemBtn === "function"
        ? window.maVipAutomation.renderHomeItemBtn(vr)
        : "";
    if (!btn) {
      var href = vr.contact_href || "";
      btn = href
        ? '<a class="vbtn" href="' + esc(href) + '">تواصل يدوي (VIP)</a>'
        : '<span class="vbtn is-disabled">تواصل يدوي (VIP)</span>';
    }
    return (
      '<div class="vip-item">' +
      '<div class="vav">' +
      esc(vr.avatar_letter || "") +
      "</div>" +
      '<div class="vi"><div class="vamt">' +
      esc(vr.amount_display) +
      ' ريال</div><div class="vtm">' +
      esc(vr.subtitle_ar) +
      '</div></div><span class="vtag">VIP</span>' +
      btn +
      "</div>"
    );
  }

  function vipRowTable(vr) {
    var btn =
      window.maVipAutomation && typeof window.maVipAutomation.renderTableAction === "function"
        ? window.maVipAutomation.renderTableAction(vr)
        : "";
    if (!btn) {
      var href = vr.contact_href || "";
      btn = href
        ? '<a class="va-btn" href="' +
          esc(href) +
          '" rel="noopener noreferrer">تواصل يدوي (VIP) ←</a>'
        : '<span class="va-btn is-disabled">تواصل يدوي (VIP) ←</span>';
    }
    var hp = vr.has_phone
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    return (
      "<tr><td><div class=\"camt\">" +
      esc(vr.amount_display) +
      ' ريال</div></td><td><div class="ctime">' +
      esc(vr.subtitle_ar) +
      "</div></td><td>" +
      hp +
      "</td><td>" +
      btn +
      "</td></tr>"
    );
  }

  function vipPageEmptyHtml() {
    return (
      '<tr><td colspan="4" class="empty-state" style="border:none;">' +
      '<div class="empty-icon">👑</div>' +
      '<div class="empty-text">لا توجد سلال VIP نشطة تحتاج تدخلك الآن</div>' +
      '<p class="ma-vip-load-diag">آخر تحقق: تم تحميل البيانات بنجاح</p>' +
      "</td></tr>"
    );
  }

  function vipPageErrorHtml() {
    return (
      '<tr><td colspan="4" style="text-align:center;padding:24px;color:#991b1b;">' +
      "تعذر تحميل سلال VIP" +
      "</td></tr>"
    );
  }

  function applyVipCartsFailed() {
    var tb = byId("ma-tbody-vip-page");
    if (tb) tb.innerHTML = vipPageErrorHtml();
    var list = byId("ma-vip-home-list");
    if (list) {
      list.innerHTML =
        '<div class="empty-state" style="color:#991b1b;"><div class="empty-text">تعذر تحميل سلال VIP</div></div>';
    }
  }

  function applyVipCarts(d) {
    if (!d || !d.ok) {
      applyVipCartsFailed();
      return;
    }
    if (window.maVipAutomation) {
      if (d.merchant_automation_mode) {
        window.maVipAutomation.setMode(d.merchant_automation_mode);
      }
      window.maVipAutomation.storePayload(d);
    }
    applyVipHomeBanner(d.merchant_vip_banner || null);
    var list = byId("ma-vip-home-list");
    if (list) {
      var rows = d.merchant_vip_rows || [];
      if (!rows.length) {
        list.innerHTML =
          '<div class="empty-state"><div class="empty-icon">👑</div><div class="empty-text">لا سلال VIP تحتاج تدخلك حالياً</div><p class="ma-vip-load-diag">آخر تحقق: تم تحميل البيانات بنجاح</p></div>';
      } else {
        list.innerHTML = rows.map(vipItemHtml).join("");
      }
    }
    var tb = byId("ma-tbody-vip-page");
    if (tb) {
      var pr = d.merchant_vip_page_rows || [];
      if (!pr.length) {
        tb.innerHTML = vipPageEmptyHtml();
      } else {
        tb.innerHTML = pr.map(vipRowTable).join("");
      }
    }
    setNavBadge("ma-nav-badge-vip", d.merchant_nav_badge_vip);
  }

  function followRowHtml(fr) {
    var cv = fr.cart_value;
    var camt =
      cv != null && cv !== ""
        ? '<div class="camt">' +
          Math.round(parseFloat(cv)) +
          " ر</div>"
        : '<div class="camt">—</div>';
    var digits = !!fr.customer_wa_digits;
    var ph = digits
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    var act = followupCompactHtml(fr);
    return (
      "<tr>" +
      "<td>" +
      camt +
      '<div class="ctime">' +
      esc(fr.replied_at || "—") +
      "</div></td>" +
      '<td><span class="chip c-other">' +
      esc(fr.reason_tag_ar || fr.reason_ar || "—") +
      "</span></td>" +
      '<td><div class="msg-text" style="margin:0;">' +
      esc(fr.last_message_line_ar || "—") +
      '</div></td><td><div class="ctime" style="font-size:12px;font-weight:600;">' +
      esc(merchantAttemptsDisplayAr(fr)) +
      "</div></td><td>" +
      ph +
      "</td><td>" +
      act +
      "</td></tr>"
    );
  }

  function applyFollowups(d) {
    if (!d || !d.ok) return;
    var tb = byId("ma-tbody-followups");
    if (tb) {
      var fr = d.merchant_followup_rows || [];
      if (!fr.length) {
        tb.innerHTML =
          '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">🔔</div><div class="empty-text">لا توجد سلال تفاعل حالياً</div></td></tr>';
      } else {
        tb.innerHTML = fr.map(followRowHtml).join("");
      }
    }
    setNavBadge("ma-nav-badge-followup", d.merchant_nav_badge_followup);
  }

  // Communication Timeline rows are driven by this array (modal reads by index).
  var cfMsgRows = [];

  function messageRowHtml(mr, idx) {
    // Communication Timeline row: who / what type / when / delivery outcome.
    // Cart value, reason tag, lifecycle and next-step intentionally excluded —
    // those belong to the Carts page. Full text/timeline lives in the modal.
    var dots = mr.delivery_dots || "";
    var outcome = mr.delivery_outcome_ar || mr.delivery_status_ar || mr.status_ar || "—";
    var replyBadge = mr.customer_reply_ar
      ? '<span class="msg-reply-badge">💬 رد العميل</span>'
      : "";
    var dotsHtml = dots
      ? '<span class="msg-dots" title="' + esc(outcome) + '">' + esc(dots) + "</span>"
      : "";
    return (
      '<div class="msg-row" data-msg-index="' +
      idx +
      '">' +
      '<div class="msg-avatar">💬</div>' +
      '<div class="msg-body">' +
      '<div class="msg-header">' +
      '<div class="msg-name">' +
      esc(mr.message_type_ar || mr.title_ar || "رسالة استرداد") +
      '</div><div class="msg-time">' +
      esc(mr.time_ar || "—") +
      "</div></div>" +
      '<div class="msg-meta"><span class="msg-phone" dir="ltr">' +
      esc(mr.phone_masked || "—") +
      "</span>" +
      dotsHtml +
      "</div>" +
      '<div class="msg-tags">' +
      '<span class="st ' +
      esc(mr.delivery_status_class || mr.status_row_class || "s-sent") +
      '\"><span class="sd"></span>' +
      esc(outcome) +
      "</span>" +
      replyBadge +
      '<button type="button" class="ma-msg-view" onclick="cfOpenMessageModal(this)">عرض الرسالة</button>' +
      "</div></div></div>"
    );
  }

  var cfMsgModalCartId = "";

  function cfSetMsgField(id, val) {
    var el = byId(id);
    if (el) {
      el.textContent = val == null || val === "" ? "—" : String(val);
    }
  }

  function cfRenderDeliveryTimeline(steps) {
    var host = byId("ma-msg-delivery");
    if (!host) return;
    if (!steps || !steps.length) {
      host.innerHTML = '<span class="ma-msg-empty">—</span>';
      return;
    }
    host.innerHTML = steps
      .map(function (s) {
        return (
          '<span class="ma-msg-step ma-msg-step-' +
          esc(s.state || "pending") +
          '"><span class="ma-msg-step-dot">' +
          esc(s.emoji || "⚪") +
          '</span>' +
          esc(s.label_ar || "") +
          "</span>"
        );
      })
      .join('<span class="ma-msg-step-sep">↓</span>');
  }

  function cfRenderCommTimeline(events) {
    var host = byId("ma-msg-comm");
    if (!host) return;
    if (!events || !events.length) {
      host.innerHTML = '<span class="ma-msg-empty">—</span>';
      return;
    }
    host.innerHTML = events
      .map(function (ev) {
        return (
          '<div class="ma-msg-tl-item">' +
          '<span class="ma-msg-tl-emoji">' +
          esc(ev.emoji || "•") +
          "</span>" +
          '<span class="ma-msg-tl-label">' +
          esc(ev.label_ar || "") +
          "</span>" +
          '<span class="ma-msg-tl-at">' +
          esc(ev.at_ar || "") +
          "</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function cfOpenMessageModal(el) {
    try {
      var row = el && el.closest ? el.closest(".msg-row") : null;
      if (!row) return;
      var idx = parseInt((row.dataset || {}).msgIndex, 10);
      var mr =
        !isNaN(idx) && cfMsgRows && cfMsgRows[idx] ? cfMsgRows[idx] : null;
      if (!mr) {
        // SSR fallback (lazy data not yet loaded): basic fields from data-*.
        var d = row.dataset || {};
        mr = {
          full_message_ar: d.msgFull,
          phone_masked: d.msgPhone,
          template_ar: d.msgTemplate,
          sent_full_ar: d.msgSent,
          provider_status_ar: d.msgProvider,
          recovery_key: d.msgKey,
          cart_id: d.msgCart,
        };
      }
      cfSetMsgField("ma-msg-full", mr.full_message_ar || "—");
      cfSetMsgField("ma-msg-phone", mr.phone_masked || "—");
      cfSetMsgField("ma-msg-template", mr.template_ar || mr.message_type_ar || "—");
      cfSetMsgField("ma-msg-sent", mr.sent_full_ar || mr.time_ar || "—");
      cfSetMsgField("ma-msg-provider", mr.provider_status_ar || "—");
      cfSetMsgField("ma-msg-sid", mr.provider_message_sid || "—");
      cfSetMsgField("ma-msg-key", mr.recovery_key || "—");
      cfSetMsgField("ma-msg-provider-resp", mr.provider_response_ar || "—");
      cfSetMsgField("ma-msg-session", mr.session_id || "—");
      cfSetMsgField("ma-msg-cartid", mr.cart_id || "—");
      cfSetMsgField("ma-msg-logid", mr.log_id || "—");

      cfRenderDeliveryTimeline(mr.delivery_timeline);
      cfRenderCommTimeline(mr.communication_timeline);

      var replyWrap = byId("ma-msg-reply-wrap");
      if (replyWrap) {
        if (mr.customer_reply_ar) {
          cfSetMsgField("ma-msg-reply", mr.customer_reply_ar);
          replyWrap.hidden = false;
        } else {
          cfSetMsgField("ma-msg-reply", "لا يوجد رد");
          replyWrap.hidden = false;
        }
      }

      cfMsgModalCartId = mr.cart_id || "";
      var openCartBtn = byId("ma-msg-open-cart");
      if (openCartBtn) {
        openCartBtn.disabled = false;
      }
      var m = byId("ma-msg-modal");
      if (m) {
        m.hidden = false;
        m.classList.add("open");
      }
    } catch (eOpen) {}
  }

  function cfCloseMessageModal() {
    var m = byId("ma-msg-modal");
    if (m) {
      m.hidden = true;
      m.classList.remove("open");
    }
  }

  function cfOpenRelatedCart() {
    cfCloseMessageModal();
    try {
      if (typeof window.goTo === "function") {
        window.goTo("carts");
        return;
      }
    } catch (eGo) {}
    try {
      window.location.hash = "#carts";
    } catch (eHash) {}
  }

  try {
    document.addEventListener(
      "keydown",
      function (ev) {
        if (ev && ev.key === "Escape") {
          cfCloseMessageModal();
        }
      },
      false
    );
  } catch (eKd) {}

  window.cfOpenMessageModal = cfOpenMessageModal;
  window.cfCloseMessageModal = cfCloseMessageModal;
  window.cfOpenRelatedCart = cfOpenRelatedCart;

  function applyMessages(d) {
    if (!d || !d.ok) return;
    ingestRefreshToken(d, "messages");
    var card = byId("ma-messages-card");
    if (!card) return;
    var rows = d.merchant_message_history_rows || [];
    cfMsgRows = rows;
    if (!rows.length) {
      card.innerHTML =
        '<div class="empty-state" style="padding:40px 20px;"><div class="empty-icon">💬</div><div class="empty-text">لا توجد رسائل مرسلة بعد</div></div>';
    } else {
      card.innerHTML = rows
        .map(function (mr, i) {
          return messageRowHtml(mr, i);
        })
        .join("");
    }
    setText("ma-wa-last-send", d.merchant_wa_last_send_ar || "—");
  }

  function setCk(id, on) {
    var el = byId(id);
    if (el) el.checked = !!on;
  }

  function setRadio(name, val) {
    var q = document.querySelector(
      'input[name="' + name + '"][value="' + val + '"]'
    );
    if (q) q.checked = true;
  }

  function setSel(id, val) {
    var el = byId(id);
    if (!el) return;
    el.value = val == null ? "" : String(val);
    try {
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {}
  }

  function reasonEditorRowHtml(r) {
    var k = esc(String(r.key || "").trim().toLowerCase());
    var lab = esc(r.label_ar || "");
    var on = r.enabled ? " checked" : "";
    return (
      '<tr data-mw-reason-row>' +
      "<td>" +
      '<input type="hidden" class="mw-reason-key" value="' +
      k +
      '">' +
      '<p class="ma-fw-field-hint" style="margin:0 0 4px 0;font-size:12px;opacity:0.85;">هذا النص هو ما يظهر للعميل داخل الودجيت.</p>' +
      '<input class="ma-fw-input mw-reason-label" type="text" maxlength="80" value="' +
      lab +
      '" dir="rtl" autocomplete="off">' +
      '</td><td class="ma-fw-td-center"><input class="mw-reason-on" type="checkbox"' +
      on +
      "></td>" +
      '<td class="ma-fw-td-center">' +
      '<button type="button" class="ma-fw-mini" data-mw-reason-up title="تحريك لأعلى">↑</button>' +
      '<button type="button" class="ma-fw-mini" data-mw-reason-down title="تحريك لأسفل">↓</button>' +
      "</td></tr>"
    );
  }

  function applyWidgetPanel(d) {
    if (!d || !d.ok) return;
    var wp = d.merchant_widget_panel || {};
    var tg = wp.trigger || {};
    var boot = byId("ma-widget-bootstrap");
    if (boot) {
      try {
        boot.textContent = JSON.stringify(wp);
      } catch (e) {}
    }
    var wn = byId("mw-widget-name");
    if (wn) wn.value = String(wp.widget_name || "مساعد المتجر");
    var wc = byId("mw-widget-color");
    if (wc) wc.value = String(wp.widget_primary_color || "#6C5CE7");
    setCk("mw-widget-enabled", wp.cartflow_widget_enabled !== false);

    var tb = byId("mw-reason-tbody");
    if (tb) {
      var rr = wp.reason_rows || [];
      tb.innerHTML = rr.map(reasonEditorRowHtml).join("");
    }

    setCk("mw-exit-enabled", tg.exit_intent_enabled !== false);
    setSel("mw-exit-delay", String(parseInt(tg.exit_intent_delay_seconds, 10) || 0));
    setSel("mw-exit-sens", String(tg.exit_intent_sensitivity || "medium"));
    setSel("mw-exit-freq", String(tg.exit_intent_frequency || "per_session"));

    setCk("mw-hes-enabled", tg.hesitation_trigger_enabled !== false);
    var hesSec = parseInt(tg.hesitation_after_seconds, 10);
    if (!isFinite(hesSec)) hesSec = 20;
    var presets = [0, 5, 10, 20, 30, 15, 45, 60, 90, 120];
    var sel = presets.indexOf(hesSec) >= 0 ? String(hesSec) : "custom";
    setSel("mw-hes-sec", sel);
    var hsc = byId("mw-hes-sec-custom");
    if (hsc) {
      hsc.value = String(hesSec);
      hsc.style.display = sel === "custom" ? "" : "none";
    }
    var lbl = byId("mw-hes-sec-custom-label");
    if (lbl) lbl.style.display = sel === "custom" ? "" : "none";

    setSel("mw-hes-cond", String(tg.hesitation_condition || "after_cart_add"));
    setSel("mw-scope", String(tg.visibility_page_scope || "all"));

    setCk("mw-sup-dismiss", tg.suppress_after_widget_dismiss !== false);
    setCk("mw-sup-purchase", tg.suppress_after_purchase !== false);
    setCk("mw-sup-checkout", tg.suppress_when_checkout_started !== false);

    setRadio("mw-phone", String(tg.widget_phone_capture_mode || "after_reason"));

    setText("ma-settings-widget-title", d.merchant_widget_title_ar || "—");
    var we = byId("ma-settings-widget-enabled");
    if (we) {
      we.textContent = d.merchant_widget_installed ? "نعم" : "لا";
    }

    if (window.cartflowMerchantWidgetPanelRebindReasons) {
      window.cartflowMerchantWidgetPanelRebindReasons();
    } else if (window.cartflowMerchantWidgetPanelRefresh) {
      window.cartflowMerchantWidgetPanelRefresh();
    }
  }

  function fetchSection(url, applyFn, label) {
    var u = String(url || "");
    var sep = u.indexOf("?") >= 0 ? "&" : "?";
    var bust = "_ts=" + Date.now();
    return fetch(u + sep + bust, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        applyFn(d);
      })
      .catch(function () {
        /* section failed — shell remains */
      });
  }

  function refreshCoreSections(reason) {
    if (merchantRefreshInFlight) return;
    merchantRefreshInFlight = true;
    logClientRefresh("refresh_start", {
      reason: reason || "unknown",
      token: merchantDashboardRefreshToken,
    });
    Promise.allSettled([
      fetchSection("/api/dashboard/summary", applySummary, "summary"),
      fetchSection("/api/dashboard/normal-carts", applyNormalCarts, "normal_carts"),
      fetchSection("/api/dashboard/messages", applyMessages, "messages"),
    ]).finally(function () {
      merchantRefreshInFlight = false;
      logClientRefresh("refresh_end", {
        reason: reason || "unknown",
        token: merchantDashboardRefreshToken,
      });
    });
  }

  function checkRefreshState() {
    var u = "/api/dashboard/refresh-state?_ts=" + Date.now();
    return fetch(u, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.ok) return;
        var next = String(d.merchant_dashboard_refresh_token || "");
        if (!next) return;
        if (!merchantDashboardRefreshToken) {
          merchantDashboardRefreshToken = next;
          logClientRefresh("token_init", { token: next });
          return;
        }
        if (next !== merchantDashboardRefreshToken) {
          var prev = merchantDashboardRefreshToken;
          merchantDashboardRefreshToken = next;
          logClientRefresh("token_changed", { from: prev, to: next });
          refreshCoreSections("refresh_token_changed");
        }
      })
      .catch(function () {
        /* ignore refresh watcher failures */
      });
  }

  function startRefreshWatcher() {
    if (merchantRefreshTimer) return;
    checkRefreshState();
    merchantRefreshTimer = window.setInterval(function () {
      if (document.hidden) return;
      checkRefreshState();
    }, 5000);
  }

  function bootLazyDashboard() {
    logSetupRenderDebug("boot", {
      hasRenderUnified: typeof renderUnifiedSetupExperience === "function",
      hasShouldHide: typeof shouldHideUnifiedSetupCard === "function",
    });
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-kpi-abandoned")) return;

    /* لا ‎recovery-trend‎ هنا — كان يستهلك اتصال DB دون تحديث الواجهة (الرسم في ‎dashboard_v1‎). */
    var jobs = [
      fetchSection("/api/dashboard/summary", applySummary, "summary"),
      fetchSection("/api/dashboard/normal-carts", applyNormalCarts, "normal_carts"),
      fetch("/api/dashboard/vip-carts", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(applyVipCarts).catch(applyVipCartsFailed),
      fetchSection("/api/dashboard/followups", applyFollowups, "followups"),
      fetchSection("/api/dashboard/widget-panel", applyWidgetPanel, "widget_panel"),
      fetchSection("/api/dashboard/messages", applyMessages, "messages"),
    ];
    Promise.allSettled(jobs);
    startRefreshWatcher();
  }

  window.maApplyVipCartsPayload = applyVipCarts;
  window.maSyncHomeActivation = syncHomeActivationFromCache;
  window.MERCHANT_SETUP_RENDER_BUILD = MERCHANT_SETUP_RENDER_BUILD;

  window.addEventListener("hashchange", function () {
    syncHomeActivationFromCache();
    try {
      var hashRaw = (location.hash || "").split("?")[0].toLowerCase();
      if (
        hashRaw === "#completed" &&
        typeof window.maRefreshCompletedCartsTable === "function"
      ) {
        window.maRefreshCompletedCartsTable();
      }
    } catch (eHash) {
      /* ignore */
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootLazyDashboard);
  } else {
    bootLazyDashboard();
  }
})();
