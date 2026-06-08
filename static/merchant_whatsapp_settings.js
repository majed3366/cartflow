/* Merchant dashboard — WhatsApp mode UX (read/save via /api/recovery-settings) */
(function () {
  "use strict";

  var bound = false;
  var readinessCtaBound = false;
  var loading = false;
  var lastSettingsData = null;

  var READINESS_LOADING_AR = "جاري التحقق من جاهزية واتساب...";
  var READINESS_ERROR_AR =
    "تعذر التحقق من جاهزية واتساب حالياً. حاول تحديث الصفحة.";

  function byId(id) {
    return document.getElementById(id);
  }

  function setBoxVisible(el, on) {
    if (!el) return;
    el.style.display = on ? "" : "none";
  }

  function showErr(msg) {
    var el = byId("ma-wa-settings-err");
    var ok = byId("ma-wa-settings-ok");
    setBoxVisible(ok, false);
    if (el) {
      el.textContent = msg || "تعذّر الحفظ";
      setBoxVisible(el, true);
    }
  }

  function showOk() {
    var el = byId("ma-wa-settings-err");
    var ok = byId("ma-wa-settings-ok");
    setBoxVisible(el, false);
    setBoxVisible(ok, true);
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-wa-settings-err"), false);
    setBoxVisible(byId("ma-wa-settings-ok"), false);
  }

  function selectedWhatsappMode() {
    var managed = byId("ma-wa-mode-managed");
    if (managed && managed.checked) return "cartflow_managed";
    return "merchant_whatsapp";
  }

  function setLegacyEnableCtaVisible(visible) {
    var cta = byId("ma-wa-enable-recovery-btn");
    if (cta) cta.hidden = !visible;
  }

  function showReadinessLoading() {
    var root = byId("ma-wa-readiness-root");
    setLegacyEnableCtaVisible(false);
    if (!root) return;
    root.hidden = false;
    root.setAttribute("aria-busy", "true");
    root.innerHTML =
      '<section class="ma-wa-readiness-card ma-wa-readiness-loading" dir="rtl" aria-busy="true">' +
      '<p class="ma-wa-readiness-loading-text">' +
      escHtml(READINESS_LOADING_AR) +
      "</p></section>";
  }

  function showReadinessError(msg) {
    var root = byId("ma-wa-readiness-root");
    setLegacyEnableCtaVisible(false);
    if (!root) return;
    root.hidden = false;
    root.setAttribute("aria-busy", "false");
    root.innerHTML =
      '<section class="ma-wa-readiness-card ma-wa-readiness-error" dir="rtl">' +
      '<p class="ma-wa-readiness-error-text">' +
      escHtml(msg || READINESS_ERROR_AR) +
      "</p></section>";
  }

  function applyConnectionPill(d) {
    var pill = byId("ma-wa-connection-pill");
    if (!pill || !d) return;
    var label =
      d.whatsapp_connection_state_ar ||
      d.whatsapp_customer_connection_status_ar ||
      "غير متصل";
    var key =
      (d.whatsapp_connection_readiness &&
        d.whatsapp_connection_readiness.connection_state_legacy_pill_key) ||
      d.whatsapp_customer_connection_status ||
      "not_connected";
    pill.textContent = label;
    pill.className = "ma-wa-connection-pill is-" + key;
    var summary = byId("ma-wa-connection-summary");
    if (summary) {
      var cr = d.whatsapp_connection_readiness || {};
      var pt = cr.production_truth || {};
      summary.textContent =
        pt.action_required_ar ||
        pt.why_not_connected_ar ||
        pt.why_paused_ar ||
        d.whatsapp_connection_summary_ar ||
        d.whatsapp_status_display ||
        "—";
    }
    var hasActionFirst =
      d.whatsapp_connection_readiness &&
      d.whatsapp_connection_readiness.action_first;
    if (hasActionFirst) {
      setLegacyEnableCtaVisible(false);
    } else {
      var paused =
        d.whatsapp_connection_state === "paused" ||
        d.whatsapp_customer_connection_status === "not_connected";
      setLegacyEnableCtaVisible(
        d.whatsapp_recovery_enabled === false || paused
      );
    }
  }

  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showCtaGuidance(msg) {
    var el = byId("ma-wa-cta-guidance");
    if (!el) return;
    var text = (msg || "").trim();
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.textContent = text;
    el.hidden = false;
  }

  function clearCtaHighlights() {
    document.querySelectorAll(".ma-wa-cta-highlight").forEach(function (node) {
      node.classList.remove("ma-wa-cta-highlight");
    });
  }

  function highlightField(fieldId) {
    var el = byId(fieldId);
    if (!el) return;
    var row = el.closest(".setting-row") || el.closest("label") || el.parentElement;
    if (row) row.classList.add("ma-wa-cta-highlight");
    try {
      el.focus({ preventScroll: true });
    } catch (_e) {
      el.focus();
    }
  }

  function openAdvancedOptions() {
    var details = document.querySelector(".ma-wa-advanced");
    if (details) details.open = true;
  }

  function scrollToWaSettings() {
    var target =
      byId("ma-wa-settings-form") ||
      document.querySelector(".ma-wa-customers-card") ||
      byId("page-whatsapp");
    if (target && target.scrollIntoView) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function handlePrimaryCtaClick(behavior) {
    clearCtaHighlights();
    var action = behavior && behavior.cta_action;
    if (!action) {
      scrollToWaSettings();
      showCtaGuidance("راجع إعدادات واتساب أدناه لإكمال الخطوة التالية.");
      return;
    }

    if (action === "open_journey_selector") {
      var selector = document.querySelector(".ma-wa-journey-selector");
      if (selector) {
        selector.classList.add("ma-wa-cta-highlight");
        selector.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        scrollToWaSettings();
      }
      showCtaGuidance(
        (behavior.inline_guidance_ar || "").trim() || "كيف تريد استخدام واتساب؟"
      );
      return;
    }

    if (action === "open_advanced_merchant") {
      openAdvancedOptions();
      scrollToWaSettings();
      showCtaGuidance(
        (behavior.placeholder_ar || "").trim() ||
          "ربط واتساب المتجر قيد التجهيز. حالياً يمكنك استخدام CartFlow Managed للتشغيل التجريبي."
      );
      return;
    }

    if (action === "show_provider_status") {
      scrollToWaSettings();
      var statusCard = document.querySelector(".ma-wa-customers-card");
      if (statusCard) statusCard.classList.add("ma-wa-cta-highlight");
      showCtaGuidance(
        (behavior.status_explanation_ar || "").trim() ||
          (behavior.inline_guidance_ar || "").trim() ||
          "قناة واتساب تحتاج متابعة قبل الإنتاج الكامل."
      );
      return;
    }

    if (action === "focus_resume") {
      openAdvancedOptions();
      scrollToWaSettings();
      var recovery = byId("ma-wa-recovery-enabled");
      if (recovery && !recovery.checked) {
        highlightField("ma-wa-recovery-enabled");
        showCtaGuidance(
          (behavior.inline_guidance_ar || "").trim() ||
            "فعّل استرجاع واتساب من الإعدادات أدناه."
        );
        return;
      }
      showCtaGuidance(
        (behavior.placeholder_ar || "").trim() ||
          "يمكن استئناف واتساب من إعدادات التشغيل عند توفره."
      );
      return;
    }

    // scroll_settings (default for cartflow_managed + connected)
    openAdvancedOptions();
    scrollToWaSettings();
    var fields = Array.isArray(behavior.highlight_fields)
      ? behavior.highlight_fields
      : [];
    fields.forEach(function (field) {
      if (field === "store_number") highlightField("ma-wa-store-number");
      if (field === "recovery_enabled") highlightField("ma-wa-recovery-enabled");
    });
    if ((behavior.inline_guidance_ar || "").trim()) {
      showCtaGuidance(behavior.inline_guidance_ar);
    } else {
      showCtaGuidance("");
    }
  }

  function saveOnboardingJourney(key) {
    hideMsgs();
    return postSettings({ whatsapp_onboarding_journey: key }).then(function (x) {
      if (x.data && x.data.ok) {
        fillForm(x.data);
        showOk();
      } else {
        showErr((x.data && x.data.error) || "تعذّر حفظ المسار");
      }
      return x;
    });
  }

  function bindReadinessCtaOnce() {
    if (readinessCtaBound) return;
    var page = byId("page-whatsapp");
    if (!page) return;
    readinessCtaBound = true;
    page.addEventListener("click", function (e) {
      var journeyBtn = e.target.closest("[data-ma-wa-journey-key]");
      if (journeyBtn) {
        e.preventDefault();
        var key = journeyBtn.getAttribute("data-ma-wa-journey-key");
        if (key) saveOnboardingJourney(key).catch(function () {
          showErr("خطأ في الشبكة أثناء حفظ المسار");
        });
        return;
      }
      var btn = e.target.closest("[data-cf-wa-primary-cta]");
      if (!btn) return;
      e.preventDefault();
      var cr =
        lastSettingsData && lastSettingsData.whatsapp_connection_readiness;
      var behavior =
        cr && cr.action_first && cr.action_first.cta_behavior
          ? cr.action_first.cta_behavior
          : null;
      handlePrimaryCtaClick(behavior);
    });
  }

  function renderJourneyBlock(journeys) {
    if (!journeys) return "";
    var selected = journeys.selected_key;
    var options = Array.isArray(journeys.options) ? journeys.options : [];
    if (!selected) {
      var optsHtml = options
        .map(function (opt) {
          return (
            '<button type="button" class="ma-wa-journey-option" data-ma-wa-journey-key="' +
            escHtml(opt.key || "") +
            '">' +
            '<span class="ma-wa-journey-option-title">' +
            escHtml(opt.label_ar || "") +
            "</span>" +
            '<span class="ma-wa-journey-option-desc">' +
            escHtml(opt.description_ar || "") +
            "</span></button>"
          );
        })
        .join("");
      return (
        '<div class="ma-wa-journey-selector" id="ma-wa-journey-selector">' +
        '<p class="ma-wa-journey-title">' +
        escHtml(journeys.title_ar || "كيف تريد استخدام واتساب؟") +
        "</p>" +
        '<div class="ma-wa-journey-options">' +
        optsHtml +
        "</div></div>"
      );
    }
    var guidance = journeys.guidance || {};
    var steps = Array.isArray(guidance.steps_ar) ? guidance.steps_ar : [];
    var stepsHtml = steps
      .map(function (step, idx) {
        return "<li>" + escHtml(step) + "</li>";
      })
      .join("");
    var placeholder = (guidance.placeholder_ar || "").trim();
    return (
      '<div class="ma-wa-journey-selected">' +
      '<p class="ma-wa-readiness-k">المسار المختار:</p>' +
      '<p class="ma-wa-journey-selected-label">' +
      escHtml(journeys.selected_label_ar || "") +
      "</p>" +
      (placeholder
        ? '<p class="ma-wa-journey-placeholder">' + escHtml(placeholder) + "</p>"
        : "") +
      (stepsHtml
        ? '<div class="ma-wa-journey-steps"><p class="ma-wa-readiness-k">خطوات التفعيل:</p><ol class="ma-wa-journey-steps-list">' +
          stepsHtml +
          "</ol></div>"
        : "") +
      "</div>"
    );
  }

  function renderReadinessCard(d) {
    var root = byId("ma-wa-readiness-root");
    if (!root || !d) return;
    var cr = d.whatsapp_connection_readiness;
    if (!cr) {
      showReadinessError(READINESS_ERROR_AR);
      return;
    }
    var journeys = d.whatsapp_onboarding_journeys || cr.whatsapp_onboarding_journeys;
    var checklist = cr.setup_checklist || {};
    var af = cr.action_first || {};
    var items = Array.isArray(checklist.checklist_ar) ? checklist.checklist_ar : [];
    var checklistHtml = items
      .map(function (item) {
        var cls = item.complete ? " is-complete" : "";
        return (
          '<li class="ma-wa-readiness-step' +
          cls +
          '">' +
          escHtml(item.mark_ar || "") +
          " " +
          escHtml(item.label_ar || "") +
          "</li>"
        );
      })
      .join("");
    var ctaLabel = af.primary_cta_label_ar || "فتح الإعدادات";
    var nextAction = af.next_action_ar || "";
    var outcome = af.expected_outcome_ar || cr.expected_outcome_ar || "—";
    root.hidden = false;
    root.setAttribute("aria-busy", "false");
    root.innerHTML =
      '<section class="ma-wa-readiness-card" dir="rtl" aria-label="جاهزية واتساب">' +
      '<div class="ma-wa-readiness-head">' +
      '<div><h2 class="ma-wa-readiness-title">جاهزية واتساب</h2>' +
      '<p class="ma-wa-readiness-sub">' +
      escHtml(checklist.headline_ar || "كيف تصبح جاهزاً للإنتاج") +
      "</p></div>" +
      '<span class="ma-wa-readiness-badge">' +
      escHtml(cr.readiness_overall_ar || "—") +
      "</span></div>" +
      renderJourneyBlock(journeys) +
      // 1) Next Action — lead with action + single primary CTA
      '<div class="ma-wa-readiness-action">' +
      '<p class="ma-wa-readiness-action-title">' +
      escHtml(af.title_ar || "") +
      "</p>" +
      (nextAction
        ? '<p class="ma-wa-readiness-action-next">الخطوة التالية: ' +
          escHtml(nextAction) +
          "</p>"
        : "") +
      '<button type="button" class="ma-wa-readiness-cta" data-cf-wa-primary-cta>' +
      escHtml(ctaLabel) +
      "</button>" +
      "</div>" +
      // 2) Remaining steps
      (checklistHtml
        ? '<div class="ma-wa-readiness-checklist"><p class="ma-wa-readiness-k">' +
          escHtml(checklist.remaining_title_ar || "المتبقي:") +
          '</p><ul class="ma-wa-readiness-checklist-list">' +
          checklistHtml +
          "</ul></div>"
        : "") +
      // 3) Outcome
      '<p class="ma-wa-readiness-outcome"><strong>النتيجة المتوقعة:</strong> ' +
      escHtml(outcome) +
      "</p>" +
      // 4) Technical status — demoted
      '<div class="ma-wa-readiness-meta ma-wa-readiness-meta-muted">' +
      '<div><span class="ma-wa-readiness-k">حالة الاتصال</span> ' +
      escHtml(cr.connection_state_ar || "—") +
      "</div>" +
      '<div><span class="ma-wa-readiness-k">الوضع</span> ' +
      escHtml(cr.whatsapp_mode_label_ar || "—") +
      "</div></div>" +
      "</section>";
  }

  function setReadOnly(d) {
    if (!d) return;
    applyConnectionPill(d);
    renderReadinessCard(d);
    var st = byId("ma-wa-status-display");
    if (st) st.textContent = d.whatsapp_status_display || "—";
    var ls = byId("ma-wa-last-send-status");
    if (ls) ls.textContent = d.last_send_status_ar || "—";
    var at = byId("ma-wa-last-send");
    if (at) {
      var t = d.last_send_at_ar || "";
      if (t && t !== "—") at.textContent = t;
    }
    var hint = byId("ma-wa-provider-hint");
    if (hint) hint.textContent = d.whatsapp_provider_mode_hint_ar || "";
    var desc = byId("ma-wa-mode-desc");
    if (desc) desc.textContent = d.whatsapp_mode_description_ar || desc.textContent;
  }

  function fillForm(d) {
    if (!d) return;
    lastSettingsData = d;
    var num = byId("ma-wa-store-number");
    if (num) num.value = d.store_whatsapp_number || "";
    var en = byId("ma-wa-recovery-enabled");
    if (en) en.checked = d.whatsapp_recovery_enabled !== false;
    var mode = (d.whatsapp_mode || "cartflow_managed").toString().toLowerCase();
    var managed = byId("ma-wa-mode-managed");
    var merchant = byId("ma-wa-mode-merchant");
    if (managed) managed.checked = mode !== "merchant_whatsapp";
    if (merchant) merchant.checked = mode === "merchant_whatsapp";
    var provider = byId("ma-wa-provider-mode");
    if (provider) {
      var m = (d.whatsapp_provider_mode || "sandbox").toString().toLowerCase();
      if (m !== "sandbox" && m !== "test" && m !== "production") m = "sandbox";
      provider.value = m;
    }
    setReadOnly(d);
  }

  function buildSaveBody(extra) {
    extra = extra || {};
    return {
      store_whatsapp_number: (byId("ma-wa-store-number") && byId("ma-wa-store-number").value) || "",
      whatsapp_recovery_enabled:
        extra.whatsapp_recovery_enabled != null
          ? !!extra.whatsapp_recovery_enabled
          : !!(byId("ma-wa-recovery-enabled") && byId("ma-wa-recovery-enabled").checked),
      whatsapp_mode: extra.whatsapp_mode || selectedWhatsappMode(),
      whatsapp_provider_mode:
        (byId("ma-wa-provider-mode") && byId("ma-wa-provider-mode").value) || "sandbox",
    };
  }

  function postSettings(body) {
    return fetch("/api/recovery-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) {
        return { status: r.status, data: d };
      });
    });
  }

  function loadSettings() {
    if (loading) return Promise.resolve();
    loading = true;
    showReadinessLoading();
    hideMsgs();
    return fetch("/api/recovery-settings")
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (x.data && x.data.ok) {
          fillForm(x.data);
        } else {
          showReadinessError(READINESS_ERROR_AR);
          showErr((x.data && x.data.error) || "تعذّر تحميل الإعدادات");
        }
      })
      .catch(function () {
        showReadinessError(READINESS_ERROR_AR);
        showErr("خطأ في الشبكة أثناء التحميل");
      })
      .finally(function () {
        loading = false;
      });
  }

  function onSubmit(e) {
    e.preventDefault();
    hideMsgs();
    var btn = byId("ma-wa-settings-save");
    if (btn) btn.disabled = true;
    postSettings(buildSaveBody())
      .then(function (x) {
        if (x.data && x.data.ok) {
          fillForm(x.data);
          showOk();
        } else {
          showErr((x.data && x.data.error) || "فشل الحفظ");
        }
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء الحفظ");
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function onEnableRecovery() {
    hideMsgs();
    var btn = byId("ma-wa-enable-recovery-btn");
    if (btn) btn.disabled = true;
    postSettings(buildSaveBody({ whatsapp_recovery_enabled: true }))
      .then(function (x) {
        if (x.data && x.data.ok) {
          fillForm(x.data);
          showOk();
        } else {
          showErr((x.data && x.data.error) || "فشل التفعيل");
        }
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء التفعيل");
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function bindOnce() {
    if (bound) return;
    var form = byId("ma-wa-settings-form");
    if (!form) return;
    bound = true;
    bindReadinessCtaOnce();
    form.addEventListener("submit", onSubmit);
    var enableBtn = byId("ma-wa-enable-recovery-btn");
    if (enableBtn) enableBtn.addEventListener("click", onEnableRecovery);
    var modeRadios = form.querySelectorAll('input[name="whatsapp_mode"]');
    modeRadios.forEach(function (radio) {
      radio.addEventListener("change", function () {
        var managed = selectedWhatsappMode() === "cartflow_managed";
        var desc = byId("ma-wa-mode-desc");
        if (desc) {
          desc.textContent = managed
            ? "CartFlow يتولى الإرسال والمتابعة — وأنت تحدد متى وكيف يتم الاسترجاع."
            : "رسائل العملاء من بنية واتساب تخص متجرك — للمتاجر المتقدمة.";
        }
      });
    });
    var provider = byId("ma-wa-provider-mode");
    if (provider) {
      provider.addEventListener("change", function () {
        var hint = byId("ma-wa-provider-hint");
        if (!hint) return;
        var v = provider.value;
        if (v === "sandbox") {
          hint.textContent = "وضع تجربة — مناسب للاختبار وليس للإنتاج";
        } else if (v === "production") {
          hint.textContent = "";
        } else {
          hint.textContent = "وضع اختبار";
        }
      });
    }
  }

  window.maInitWhatsappSettingsPage = function () {
    bindOnce();
    loadSettings();
  };

  window.maHandleWhatsappReadinessCta = function () {
    var cr =
      lastSettingsData && lastSettingsData.whatsapp_connection_readiness;
    var behavior =
      cr && cr.action_first && cr.action_first.cta_behavior
        ? cr.action_first.cta_behavior
        : null;
    handlePrimaryCtaClick(behavior);
  };
})();
