/* Merchant dashboard — WhatsApp mode UX (read/save via /api/recovery-settings) */
(function () {
  "use strict";

  var bound = false;
  var readinessCtaBound = false;
  var loading = false;
  var lastSettingsData = null;
  var journeyChangeOpen = false;

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
    var hidden = byId("ma-wa-mode-hidden");
    if (hidden && hidden.value) return hidden.value;
    return "cartflow_managed";
  }

  function setSelectedWhatsappMode(mode) {
    var key = (mode || "cartflow_managed").toString().toLowerCase();
    if (key !== "merchant_whatsapp") key = "cartflow_managed";
    var hidden = byId("ma-wa-mode-hidden");
    if (hidden) hidden.value = key;
  }

  function renderModeSelection(d) {
    var root = byId("ma-wa-mode-selection-root");
    if (!root) return;
    var sel = d.whatsapp_mode_selection || {};
    var options = Array.isArray(sel.options) ? sel.options : [];
    if (!options.length) {
      root.innerHTML = "";
      return;
    }
    var title = sel.title_ar || "كيف تريد التواصل مع عملائك؟";
    var cards = options
      .map(function (opt) {
        var key = opt.key || "";
        var isSelected = !!opt.selected;
        var isCartflow = key === "cartflow_managed";
        var bullets = Array.isArray(opt.bullets_ar) ? opt.bullets_ar : [];
        var bulletsHtml = bullets
          .map(function (b) {
            return "<li>" + escHtml(b) + "</li>";
          })
          .join("");
        return (
          '<button type="button" class="ma-wa-mode-card' +
          (isCartflow ? " is-cartflow" : " is-merchant") +
          (isSelected ? " is-selected" : "") +
          '" data-ma-wa-mode="' +
          escHtml(key) +
          '" aria-pressed="' +
          (isSelected ? "true" : "false") +
          '">' +
          '<div class="ma-wa-mode-card-head">' +
          '<p class="ma-wa-mode-card-title">' +
          escHtml(opt.title_ar || opt.label_ar || key) +
          "</p>" +
          (opt.recommended
            ? '<span class="ma-wa-mode-card-badge">موصى به</span>'
            : "") +
          "</div>" +
          (bulletsHtml
            ? '<ul class="ma-wa-mode-card-bullets">' + bulletsHtml + "</ul>"
            : "") +
          "</button>"
        );
      })
      .join("");
    root.innerHTML =
      '<div class="ma-wa-mode-selection">' +
      '<p class="ma-wa-mode-selection-title">' +
      escHtml(title) +
      "</p>" +
      '<div class="ma-wa-mode-cards">' +
      cards +
      "</div></div>";
    root.querySelectorAll("[data-ma-wa-mode]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var nextMode = btn.getAttribute("data-ma-wa-mode");
        if (!nextMode || nextMode === selectedWhatsappMode()) return;
        setSelectedWhatsappMode(nextMode);
        hideMsgs();
        postSettings(buildSaveBody({ whatsapp_mode: nextMode }))
          .then(function (x) {
            if (x.data && x.data.ok) {
              fillForm(x.data);
              showOk();
            } else {
              showErr((x.data && x.data.error) || "تعذّر حفظ اختيار واتساب");
              if (lastSettingsData) fillForm(lastSettingsData);
            }
          })
          .catch(function () {
            showErr("خطأ في الشبكة أثناء حفظ اختيار واتساب");
            if (lastSettingsData) fillForm(lastSettingsData);
          });
      });
    });
  }

  function renderMerchantOwnedPanel(d) {
    var panel = byId("ma-wa-merchant-owned-panel");
    if (!panel) return;
    var block = d.whatsapp_mode_merchant_panel || {};
    if (!block.visible) {
      panel.hidden = true;
      panel.innerHTML = "";
      return;
    }
    panel.hidden = false;
    var connectHref = block.connect_page_href || "/dashboard#whatsapp-connect";
    panel.innerHTML =
      '<p class="ma-wa-merchant-owned-panel-title">حالة واتساب أعمال الخاص بي</p>' +
      '<div class="ma-wa-merchant-owned-row">' +
      '<span class="ma-wa-merchant-owned-k">ربط منصة الأعمال:</span>' +
      "<span>" +
      escHtml(block.meta_pairing_status_ar || "—") +
      "</span></div>" +
      (block.meta_pairing_instruction_ar
        ? '<div class="ma-wa-merchant-owned-row">' +
          '<span class="ma-wa-merchant-owned-k">الخطوة التالية:</span>' +
          "<span>" +
          escHtml(block.meta_pairing_instruction_ar) +
          "</span></div>"
        : "") +
      '<div class="ma-wa-merchant-owned-row">' +
      '<span class="ma-wa-merchant-owned-k">Embedded Signup:</span>' +
      "<span>" +
      escHtml(block.embedded_signup_status_ar || "—") +
      "</span></div>" +
      (block.embedded_signup_next_action_ar
        ? '<div class="ma-wa-merchant-owned-row">' +
          '<span class="ma-wa-merchant-owned-k">إجراء الربط:</span>' +
          "<span>" +
          escHtml(block.embedded_signup_next_action_ar) +
          "</span></div>"
        : "") +
      (block.connect_page_note_ar
        ? '<p class="ma-fw-field-hint" style="margin:8px 0 0;">' +
          escHtml(block.connect_page_note_ar) +
          "</p>"
        : "") +
      '<div class="ma-wa-merchant-owned-connect">' +
      '<button type="button" class="ma-fw-save ma-sc-btn-secondary" data-ma-wa-open-connect>' +
      escHtml(block.connect_page_label_ar || "صفحة ربط واتساب") +
      "</button></div>";
    var connectBtn = panel.querySelector("[data-ma-wa-open-connect]");
    if (connectBtn) {
      connectBtn.addEventListener("click", function () {
        if (window.goTo) {
          window.goTo("whatsapp-connect");
        } else {
          window.location.href = connectHref;
        }
      });
    }
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

    if (action === "open_whatsapp_business_guide") {
      postSettings({ whatsapp_onboarding_journey_status: "in_progress" }).catch(
        function () {}
      );
      var guideUrl = (behavior.external_url || "").trim() || "https://business.whatsapp.com/";
      window.open(guideUrl, "_blank", "noopener,noreferrer");
      showCtaGuidance(
        (behavior.explanation_ar || behavior.inline_guidance_ar || "").trim() ||
          "يلزم وجود واتساب أعمال لاستخدام استرجاع واتساب."
      );
      return;
    }

    if (action === "prepare_new_number") {
      openAdvancedOptions();
      scrollToWaSettings();
      highlightField("ma-wa-store-number");
      showCtaGuidance(
        (behavior.inline_guidance_ar || "").trim() ||
          "جهّز رقماً مخصصاً للاسترجاع، فعّل عليه واتساب أعمال، ثم أدخله هنا."
      );
      return;
    }

    if (action === "open_meta_advanced_placeholder") {
      scrollToWaSettings();
      var metaNote =
        (behavior.placeholder_ar || "").trim() ||
        "الربط المتقدم قيد التجهيز حالياً.";
      var metaSecondary = (behavior.secondary_note_ar || "").trim();
      showCtaGuidance(
        metaSecondary ? metaNote + " " + metaSecondary : metaNote
      );
      postSettings({ whatsapp_onboarding_journey_status: "in_progress" }).catch(
        function () {}
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
        journeyChangeOpen = false;
        fillForm(x.data);
        showOk();
      } else {
        showErr((x.data && x.data.error) || "تعذّر حفظ المسار");
      }
      return x;
    });
  }

  function renderJourneyOptionsHtml(options, selectedKey) {
    var badgeLabel = "المسار الحالي";
    return options
      .map(function (opt) {
        var isCurrent = !!(selectedKey && opt.key === selectedKey);
        return (
          '<button type="button" class="ma-wa-journey-option' +
          (isCurrent ? " is-current" : "") +
          '" data-ma-wa-journey-key="' +
          escHtml(opt.key || "") +
          '">' +
          (isCurrent
            ? '<span class="ma-wa-journey-option-badge">' + escHtml(badgeLabel) + "</span>"
            : "") +
          '<span class="ma-wa-journey-option-title">' +
          escHtml(opt.label_ar || "") +
          "</span>" +
          '<span class="ma-wa-journey-option-desc">' +
          escHtml(opt.description_ar || "") +
          "</span></button>"
        );
      })
      .join("");
  }

  function renderJourneySelectorPanel(journeys, selectedKey, showSafety) {
    var options = Array.isArray(journeys.options) ? journeys.options : [];
    var safety = (journeys.change_journey_safety_ar || "").trim();
    return (
      '<div class="ma-wa-journey-selector" id="ma-wa-journey-selector">' +
      '<p class="ma-wa-journey-title">' +
      escHtml(journeys.title_ar || "كيف تريد استخدام واتساب؟") +
      "</p>" +
      (showSafety && safety
        ? '<p class="ma-wa-journey-change-safety">' + escHtml(safety) + "</p>"
        : "") +
      '<div class="ma-wa-journey-options">' +
      renderJourneyOptionsHtml(options, selectedKey) +
      "</div></div>"
    );
  }

  function bindReadinessCtaOnce() {
    if (readinessCtaBound) return;
    var page = byId("page-whatsapp");
    if (!page) return;
    readinessCtaBound = true;
    page.addEventListener("click", function (e) {
      var changeJourneyBtn = e.target.closest("[data-ma-wa-change-journey]");
      if (changeJourneyBtn) {
        e.preventDefault();
        journeyChangeOpen = true;
        if (lastSettingsData) renderReadinessCard(lastSettingsData);
        var selector = document.querySelector(".ma-wa-journey-selector");
        if (selector) {
          selector.classList.add("ma-wa-cta-highlight");
          selector.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        return;
      }
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

  function renderJourneyBlock(journeys, opts) {
    opts = opts || {};
    if (!journeys) return "";
    var selected = journeys.selected_key;
    if (!selected) {
      return renderJourneySelectorPanel(journeys, null, false);
    }
    if (journeyChangeOpen) {
      return renderJourneySelectorPanel(journeys, selected, true);
    }
    var currentLabel = journeys.current_path_label_ar || "مسار واتساب الحالي:";
    var changeCta = journeys.change_journey_cta_ar || "تغيير مسار واتساب";
    var guidance = journeys.guidance || {};
    var completion = guidance.completion || {};
    var isCompleted = !!completion.is_completed;
    var steps = Array.isArray(guidance.steps_ar) ? guidance.steps_ar : [];
    var stepsHtml = steps
      .map(function (step) {
        return "<li>" + escHtml(step) + "</li>";
      })
      .join("");
    var summaryItems = Array.isArray(completion.summary_items_ar)
      ? completion.summary_items_ar
      : [];
    var summaryHtml = summaryItems
      .map(function (item) {
        return "<li>" + escHtml(item) + "</li>";
      })
      .join("");
    var placeholder = (guidance.placeholder_ar || "").trim();
    var secondary = (guidance.secondary_note_ar || "").trim();
    var explanation = (guidance.explanation_ar || "").trim();
    var statusAr = (guidance.status_ar || "").trim();
    var statusBadgeClass = (guidance.status_badge_class || "").trim();
    var progressPct = Number(guidance.progress_pct);
    if (!isFinite(progressPct)) progressPct = 0;
    var reviewCta = (completion.review_settings_cta_ar || "تعديل إعدادات واتساب").trim();
    var selectedDesc = (journeys.selected_description_ar || "").trim();
    if (!selectedDesc && selected) {
      var journeyOptions = Array.isArray(journeys.options) ? journeys.options : [];
      for (var oi = 0; oi < journeyOptions.length; oi++) {
        if (journeyOptions[oi].key === selected) {
          selectedDesc = (journeyOptions[oi].description_ar || "").trim();
          break;
        }
      }
    }
    return (
      '<div class="ma-wa-journey-selected' +
      (isCompleted ? " is-journey-completed" : "") +
      '">' +
      (opts.hideCurrentPathLabel
        ? ""
        : '<p class="ma-wa-readiness-k">' + escHtml(currentLabel) + "</p>") +
      '<p class="ma-wa-journey-selected-label">' +
      escHtml(journeys.selected_label_ar || "") +
      "</p>" +
      (isCompleted && selectedDesc
        ? '<p class="ma-wa-journey-path-desc">' + escHtml(selectedDesc) + "</p>"
        : "") +
      (statusAr
        ? '<span class="ma-wa-journey-status-badge ' +
          escHtml(statusBadgeClass) +
          '">' +
          escHtml(statusAr) +
          "</span>"
        : "") +
      (isCompleted && (completion.badge_ar || "").trim()
        ? '<p class="ma-wa-journey-completed-badge">' +
          escHtml(completion.badge_ar) +
          "</p>"
        : "") +
      (isCompleted && (completion.headline_ar || "").trim()
        ? '<p class="ma-wa-journey-completed-headline">' +
          escHtml(completion.headline_ar) +
          "</p>"
        : "") +
      (summaryHtml
        ? '<ul class="ma-wa-journey-completion-summary">' + summaryHtml + "</ul>"
        : "") +
      '<div class="ma-wa-journey-actions">' +
      '<button type="button" class="ma-wa-journey-change-btn" data-ma-wa-change-journey>' +
      escHtml(changeCta) +
      "</button>" +
      (isCompleted && !opts.hideReviewCta
        ? '<button type="button" class="ma-wa-journey-review-btn" data-cf-wa-primary-cta>' +
          escHtml(reviewCta) +
          "</button>"
        : "") +
      "</div>" +
      (isCompleted && (completion.readiness_separation_note_ar || "").trim()
        ? '<p class="ma-wa-journey-readiness-note">' +
          escHtml(completion.readiness_separation_note_ar) +
          "</p>"
        : "") +
      (!isCompleted && statusAr
        ? '<div class="ma-wa-journey-progress" role="progressbar" aria-valuenow="' +
          progressPct +
          '" aria-valuemin="0" aria-valuemax="100">' +
          '<div class="ma-wa-journey-progress-bar" style="width:' +
          progressPct +
          '%"></div></div>'
        : "") +
      (!isCompleted && explanation
        ? '<p class="ma-wa-journey-explanation">' + escHtml(explanation) + "</p>"
        : "") +
      (!isCompleted && placeholder
        ? '<p class="ma-wa-journey-placeholder">' + escHtml(placeholder) + "</p>"
        : "") +
      (!isCompleted && secondary
        ? '<p class="ma-wa-journey-secondary">' + escHtml(secondary) + "</p>"
        : "") +
      (!isCompleted && stepsHtml
        ? '<div class="ma-wa-journey-steps"><p class="ma-wa-readiness-k">خطوات التفعيل:</p><ol class="ma-wa-journey-steps-list">' +
          stepsHtml +
          "</ol></div>"
        : "") +
      "</div>"
    );
  }

  function renderCompletedJourneyVisibility(visibility, productionSending, ctaLabel) {
    if (!visibility || !visibility.active) return "";
    var current = visibility.current_journey || {};
    var status = visibility.journey_status || {};
    var mgmt = visibility.path_management || {};
    var sending = productionSending || {};
    return (
      '<div class="ma-wa-completed-sections">' +
      '<section class="ma-wa-completed-section ma-wa-completed-section-journey">' +
      '<h3 class="ma-wa-completed-section-title">' +
      escHtml(current.title_ar || "مسار واتساب الحالي") +
      "</h3>" +
      (current.mode_line_ar
        ? '<p class="ma-wa-completed-section-value">' + escHtml(current.mode_line_ar) + "</p>"
        : "") +
      '<p class="ma-wa-completed-section-path">' +
      escHtml(current.path_label_ar || "") +
      "</p>" +
      (current.path_description_ar
        ? '<p class="ma-wa-completed-section-desc">' +
          escHtml(current.path_description_ar) +
          "</p>"
        : "") +
      (current.context_ar
        ? '<p class="ma-wa-completed-section-context">' + escHtml(current.context_ar) + "</p>"
        : "") +
      "</section>" +
      '<section class="ma-wa-completed-section ma-wa-completed-section-status">' +
      '<h3 class="ma-wa-completed-section-title">' +
      escHtml(status.title_ar || "حالة المسار") +
      "</h3>" +
      '<p class="ma-wa-completed-section-badge">' +
      escHtml(status.badge_ar || "✓ مكتمل") +
      "</p>" +
      (status.description_ar
        ? '<p class="ma-wa-completed-section-desc">' + escHtml(status.description_ar) + "</p>"
        : "") +
      "</section>" +
      '<section class="ma-wa-completed-section ma-wa-completed-section-sending">' +
      '<h3 class="ma-wa-completed-section-title">' +
      escHtml(sending.title_ar || "حالة الإرسال") +
      "</h3>" +
      '<p class="ma-wa-completed-section-value">' +
      escHtml(sending.status_ar || "—") +
      "</p>" +
      (sending.explanation_ar
        ? '<p class="ma-wa-completed-section-desc">' + escHtml(sending.explanation_ar) + "</p>"
        : "") +
      (sending.meta_pairing_instruction_ar
        ? '<div class="ma-wa-meta-pairing-instruction" role="note">' +
          '<p class="ma-wa-readiness-k">الخطوة التالية</p>' +
          '<p class="ma-wa-meta-pairing-steps">' +
          escHtml(sending.meta_pairing_instruction_ar) +
          "</p></div>"
        : "") +
      (mgmt.no_action_ar
        ? '<p class="ma-wa-completed-section-no-action">' + escHtml(mgmt.no_action_ar) + "</p>"
        : "") +
      "</section>" +
      '<section class="ma-wa-completed-section ma-wa-completed-section-management">' +
      '<h3 class="ma-wa-completed-section-title">' +
      escHtml(mgmt.title_ar || "إدارة المسار") +
      "</h3>" +
      '<div class="ma-wa-completed-section-actions">' +
      '<button type="button" class="ma-wa-journey-change-btn" data-ma-wa-change-journey>' +
      escHtml(mgmt.change_journey_cta_ar || "تغيير مسار واتساب") +
      "</button>" +
      '<button type="button" class="ma-wa-readiness-cta" data-cf-wa-primary-cta>' +
      escHtml(ctaLabel || mgmt.edit_settings_cta_ar || "تعديل إعدادات واتساب") +
      "</button>" +
      "</div></section></div>"
    );
  }

  function renderProductionSendingReadiness(block) {
    if (!block) return "";
    return (
      '<div class="ma-wa-production-sending">' +
      '<p class="ma-wa-readiness-k">' +
      escHtml(block.title_ar || "حالة الإرسال") +
      "</p>" +
      '<p class="ma-wa-production-sending-status">' +
      escHtml(block.status_ar || "—") +
      "</p>" +
      (block.explanation_ar
        ? '<p class="ma-wa-production-sending-explanation">' +
          escHtml(block.explanation_ar) +
          "</p>"
        : "") +
      (block.meta_pairing_instruction_ar
        ? '<div class="ma-wa-meta-pairing-instruction" role="note">' +
          '<p class="ma-wa-readiness-k">الخطوة التالية</p>' +
          '<p class="ma-wa-meta-pairing-steps">' +
          escHtml(block.meta_pairing_instruction_ar) +
          "</p></div>"
        : "") +
      "</div>"
    );
  }

  function renderReadinessDiagnosticTemp() {
    return "";
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
        var statusLine = (item.status_ar || "").trim();
        var text = statusLine
          ? escHtml(item.label_ar || "") + ": " + escHtml(statusLine)
          : escHtml(item.mark_ar || "") + " " + escHtml(item.label_ar || "");
        return (
          '<li class="ma-wa-readiness-step' +
          cls +
          (item.merchant_presentation ? " is-merchant-presentation" : "") +
          '">' +
          text +
          "</li>"
        );
      })
      .join("");
    var completedUx = cr.merchant_completed_ux || {};
    var productionSending = cr.production_sending_readiness || {};
    var journeyCompleted = !!(
      completedUx.active ||
      af.journey_completed ||
      (af.cta_behavior && af.cta_behavior.journey_completed)
    );
    var ctaLabel = af.primary_cta_label_ar || "فتح الإعدادات";
    var nextAction = af.next_action_ar || "";
    var outcome = af.expected_outcome_ar || cr.expected_outcome_ar || "—";
    var badgeAr = cr.merchant_readiness_badge_ar || cr.readiness_overall_ar || "—";
    var monitorCard = byId("ma-wa-status-monitor-card");
    if (monitorCard) monitorCard.hidden = !!journeyCompleted;

    if (journeyCompleted) {
      if (journeyChangeOpen && journeys && journeys.selected_key) {
        root.hidden = false;
        root.setAttribute("aria-busy", "false");
        root.innerHTML =
          '<section class="ma-wa-readiness-card ma-wa-readiness-card-completed" dir="rtl" aria-label="جاهزية واتساب">' +
          '<div class="ma-wa-journey-panel ma-wa-journey-panel-completed">' +
          '<p class="ma-wa-readiness-section-k">مسار واتساب</p>' +
          renderJourneyBlock(journeys) +
          "</div></section>";
        return;
      }
      var journeyVisibility =
        cr.merchant_journey_visibility ||
        { active: true, path_management: { no_action_ar: completedUx.no_action_ar } };
      root.hidden = false;
      root.setAttribute("aria-busy", "false");
      root.innerHTML =
        '<section class="ma-wa-readiness-card ma-wa-readiness-card-completed" dir="rtl" aria-label="جاهزية واتساب">' +
        renderCompletedJourneyVisibility(journeyVisibility, productionSending, ctaLabel) +
        "</section>";
      return;
    }

    root.hidden = false;
    root.setAttribute("aria-busy", "false");
    root.innerHTML =
      '<section class="ma-wa-readiness-card" dir="rtl" aria-label="جاهزية واتساب">' +
      '<div class="ma-wa-journey-panel">' +
      '<p class="ma-wa-readiness-section-k">مسار واتساب</p>' +
      renderJourneyBlock(journeys) +
      "</div>" +
      renderProductionSendingReadiness(productionSending) +
      '<div class="ma-wa-readiness-production">' +
      '<div class="ma-wa-readiness-head">' +
      '<div><p class="ma-wa-readiness-section-k">جاهزية الإنتاج</p>' +
      '<h2 class="ma-wa-readiness-title">جاهزية واتساب</h2>' +
      '<p class="ma-wa-readiness-sub">' +
      escHtml(checklist.headline_ar || "كيف تصبح جاهزاً للإنتاج") +
      "</p></div>" +
      '<span class="ma-wa-readiness-badge">' +
      escHtml(badgeAr) +
      "</span></div>" +
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
      (checklistHtml
        ? '<div class="ma-wa-readiness-checklist"><p class="ma-wa-readiness-k">' +
          escHtml(checklist.remaining_title_ar || "المتبقي:") +
          '</p><ul class="ma-wa-readiness-checklist-list">' +
          checklistHtml +
          "</ul></div>"
        : "") +
      '<p class="ma-wa-readiness-outcome"><strong>النتيجة المتوقعة:</strong> ' +
      escHtml(outcome) +
      "</p>" +
      '<details class="ma-wa-readiness-details-muted">' +
      '<summary>تفاصيل الحالة</summary>' +
      '<div class="ma-wa-readiness-meta ma-wa-readiness-meta-muted">' +
      '<div><span class="ma-wa-readiness-k">حالة الاتصال</span> ' +
      escHtml(cr.connection_state_ar || "—") +
      "</div>" +
      '<div><span class="ma-wa-readiness-k">الوضع</span> ' +
      escHtml(cr.whatsapp_mode_label_ar || "—") +
      "</div></div></details>" +
      "</div>" +
      "</section>";
  }

  function setReadOnly(d) {
    if (!d) return;
    applyConnectionPill(d);
    renderModeSelection(d);
    renderMerchantOwnedPanel(d);
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
    setSelectedWhatsappMode(mode);
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
