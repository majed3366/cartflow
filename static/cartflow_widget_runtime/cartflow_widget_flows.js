/**
 * Customer flows (cart recovery + exit-intent branching). Bridges triggers ↔ UI ↔ API ↔ phone module.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var FLOW_VERSION = "v2-config-before-paint-1";
  var SS_V2_PHONE_PROMPT_DONE = "cartflow_cf_v2_optional_phone_done";
  /** Polling cadence/caps for `/api/cartflow/ready` bootstrap (avoid unbounded churn). */
  var READY_POLL_INTERVAL_MS = 120;
  var MAX_READY_POLL_DURATION_MS = 75000;
  var MAX_READY_POLL_TICKS =
    Math.ceil(MAX_READY_POLL_DURATION_MS / READY_POLL_INTERVAL_MS) + 1;

  /** Set while `ensureStep1Then` is waiting; public-config completion pings this if still pending. */
  var notifyStep1PublicConfigHydrated = null;

  /** Short in-widget hints only — persuasion stays in background recovery/WhatsApp. */
  var RECOVERY_SUGGESTIONS = {
    price: [
      "راجع خيارات الدفع المتاحة",
      "قارن السعر بقيمة المنتج ومواصفاته",
      "اطلع على تفاصيل المنتج قبل إكمال الطلب",
    ],
    shipping: [
      "راجع تكلفة الشحن المتاحة",
      "تحقق من مدة الشحن المتوقعة",
      "اطلع على أي عروض شحن متوفرة",
    ],
    quality: [
      "راجع مواصفات المنتج",
      "اطلع على تقييمات العملاء",
      "تحقق من تفاصيل المنتج قبل الشراء",
    ],
    delivery: [
      "اعرف موعد الوصول المتوقع",
      "راجع خيارات التوصيل المتاحة",
      "اطلع على تفاصيل التوصيل قبل إكمال الطلب",
    ],
    warranty: [
      "اعرف مدة الضمان",
      "راجع سياسة الاستبدال والاسترجاع",
      "اطلع على شروط الضمان",
    ],
    thinking: [
      "مقارنة بين الخيارات",
      "توضيح ما يهمك قبل الإكمال",
      "متابعة لاحقة عند الحاجة",
    ],
    other: [],
  };

  function isDemoPath() {
    return /\b\/demo\//i.test(String(window.location.pathname || ""));
  }

  function isMerchantActivationMode() {
    try {
      var qs = new URLSearchParams(window.location.search || "");
      return String(qs.get("merchant_activation") || "").trim() === "1";
    } catch (eMa) {
      return false;
    }
  }

  function primaryHex() {
    var th = Cf.Theme;
    if (th && typeof th.resolvedPrimary === "function") {
      return th.resolvedPrimary(null);
    }
    var M = Cf.Config.merchant();
    return (M && M.widget_primary_color) || "#888888";
  }

  /** Keep cart totals / VIP mirrors in sync; V2 bundle does not load legacy cartflow_widget.js. */
  function mirrorCartTotals() {
    try {
      Cf.State.mirrorCartTotalsFromGlobals();
    } catch (eM) {}
  }

  function emitGuide(name, detail) {
    if (!isDemoPath()) {
      return;
    }
    try {
      document.dispatchEvent(
        new CustomEvent(name, { bubbles: true, detail: detail || {} })
      );
    } catch (eDm) {}
  }

  function merchantAllowsUi() {
    var M = Cf.Config.merchant();
    return !!(M && M.widget_enabled !== false && Date.now() >= (M.prompt_not_before_ms || 0));
  }

  function globalSuppressionAbort() {
    var tr = Cf.Config.widgetTrigger();
    if (
      Cf.State.readDismissSuppress() &&
      tr &&
      tr.suppress_after_widget_dismiss !== false
    ) {
      return true;
    }
    return false;
  }

  function shouldBlockCartTriggers() {
    var tr = Cf.Config.widgetTrigger();
    if (
      tr &&
      tr.suppress_when_checkout_started !== false &&
      Cf.State.checkoutPathActive()
    ) {
      return true;
    }
    if (!Cf.Config.widgetGloballyAllowed()) {
      return true;
    }
    return false;
  }

  function st() {
    return Cf.State.internals;
  }

  function cfArbitrationShadowObserveOpen(entrypoint, tagNote) {
    try {
      if (Cf.Arbitration && typeof Cf.Arbitration.observeWidgetOpenAttempt === "function") {
        Cf.Arbitration.observeWidgetOpenAttempt({
          entrypoint: entrypoint,
          trigger_source: String(tagNote || "cart_recovery"),
          tag_note: String(tagNote || ""),
        });
      }
    } catch (eArbSh) {}
  }

  function cfArbitrationShadowObserveTrigger(triggerSource, phase) {
    try {
      if (Cf.Arbitration && typeof Cf.Arbitration.observeTriggerSignal === "function") {
        Cf.Arbitration.observeTriggerSignal({
          trigger_source: String(triggerSource || "unknown"),
          phase: phase || "trigger_fired",
        });
      }
    } catch (eArbTr) {}
  }

  /** Exit-intent vs cart recovery: do not replace UI if bubble or shell chrome is already visible (incl. minimized launcher). */
  function v2ShellOccupiedPreventExitIntentDuplicates() {
    try {
      if (st().bubbleShown) {
        return true;
      }
    } catch (eBs) {}
    try {
      var sh = st().shell;
      if (sh && sh.isOpen === true) {
        return true;
      }
    } catch (eSh) {}
    return false;
  }

  function setBubbleShown(bit) {
    st().bubbleShown = !!bit;
    try {
      if (window.CartFlowState) {
        window.CartFlowState.widgetShown = !!bit;
      }
    } catch (eS) {}
  }

  function isStorefrontRecoveryMode() {
    try {
      return window.CARTFLOW_RECOVERY_WIDGET_MODE === true;
    } catch (eRm) {
      return false;
    }
  }

  function isRealStorefrontEmbed() {
    try {
      if (Cf.Config && typeof Cf.Config.isRealStorefrontEmbed === "function") {
        return Cf.Config.isRealStorefrontEmbed();
      }
    } catch (eEmb) {}
    return isStorefrontRecoveryMode();
  }

  function storefrontUiBlocked() {
    if (!isRealStorefrontEmbed()) {
      return false;
    }
    if (st().v2MerchantConfigFailed) {
      return true;
    }
    return !st().v2MerchantConfigResolved;
  }

  function logConfigBeforeFirstUi() {
    if (!isRealStorefrontEmbed() || st().v2ConfigLoggedBeforeUi) {
      return;
    }
    st().v2ConfigLoggedBeforeUi = true;
    try {
      var M = Cf.Config.merchant();
      console.log("[CF STOREFRONT CONFIG BEFORE FIRST UI]", {
        widget_name: M && M.widget_brand_name,
        widget_primary_color: M && M.widget_primary_color,
        config_resolved: st().v2MerchantConfigResolved,
      });
    } catch (eLog) {}
  }

  var EXIT_INTENT_PRESET_BY_TONE = {
    friendly:
      "هلا 👋\nفيه خيارات ممكن تعجبك 👍\nتحب أشوفها لك بسرعة؟",
    formal:
      "مرحباً 👋\nيمكنني مساعدتك في استعراض خيارات مناسبة لك\nهل ترغب بالاطلاع عليها؟",
    sales:
      "قبل ما تطلع 👋\nعندي خيارات ممكن تناسبك أكثر 👌\nخلني أوريك الأفضل الآن",
  };

  function strTrim(s) {
    return String(s == null ? "" : s).trim();
  }

  function getExitIntentOpeningText() {
    try {
      var M = Cf.Config && Cf.Config.merchant ? Cf.Config.merchant() : null;
      var mode =
        M && M.exit_intent_template_mode != null
          ? String(M.exit_intent_template_mode).trim().toLowerCase()
          : "preset";
      var custom =
        M && M.exit_intent_custom_text != null
          ? strTrim(M.exit_intent_custom_text)
          : "";
      if (mode === "custom" && custom !== "") {
        return String(M.exit_intent_custom_text).replace(/\r\n/g, "\n");
      }
      var tone =
        M &&
        M.exit_intent_template_tone != null &&
        EXIT_INTENT_PRESET_BY_TONE[M.exit_intent_template_tone]
          ? M.exit_intent_template_tone
          : "friendly";
      return EXIT_INTENT_PRESET_BY_TONE[tone];
    } catch (eEi) {
      return EXIT_INTENT_PRESET_BY_TONE.friendly;
    }
  }

  function getCartRecoveryQuestion(tagNote) {
    var tag = String(tagNote || "");
    if (tag.indexOf("exit_intent") >= 0) {
      return getExitIntentOpeningText();
    }
    return "تبي أساعدك تكمل طلبك؟";
  }

  function recoverySuggestionBullets(reasonKey) {
    var rk = String(reasonKey || "other").toLowerCase();
    var list = RECOVERY_SUGGESTIONS[rk];
    return Array.isArray(list) ? list.slice() : [];
  }

  function markWidgetDismissed() {
    try {
      window.sessionStorage.setItem("cartflow_cf_suppress_after_dismiss", "1");
    } catch (eDs) {}
    setBubbleShown(false);
  }

  function minimizeWidgetPolite() {
    setBubbleShown(false);
    try {
      if (Cf.Shell && typeof Cf.Shell.minimizeLauncher === "function") {
        Cf.Shell.minimizeLauncher();
        return;
      }
    } catch (eMin) {}
    try {
      Cf.Ui.hideBubble();
    } catch (eHb) {}
  }

  function gracefulCloseWidget() {
    try {
      console.log("[CF RECOVERY FLOW COMPLETE CLOSE]");
    } catch (eLog) {}
    try {
      if (Cf.State && typeof Cf.State.clearHesitationTimers === "function") {
        Cf.State.clearHesitationTimers();
      }
    } catch (eClr) {}
    var inner = st();
    if (inner.exitInactivityTimer != null) {
      try {
        clearTimeout(inner.exitInactivityTimer);
      } catch (eEx) {}
      inner.exitInactivityTimer = null;
    }
    inner.cfV2HesitationDeadlineAt = null;
    inner.cfV2HesitationDeferredBaseAt = null;
    try {
      if (
        Cf.State &&
        typeof Cf.State.clearV2HesitationDeadlinePersisted === "function"
      ) {
        Cf.State.clearV2HesitationDeadlinePersisted();
      }
    } catch (eDl) {}
    markWidgetDismissed();
    minimizeWidgetPolite();
  }

  function showContinuationForPending() {
    var rk = String(st().pending_reason_key || "other").toLowerCase();
    var det = st().pending_reason_detail || {};
    var subCat = det.sub_category != null ? det.sub_category : null;
    showContinuationQuiet(rk, subCat);
  }

  function optionalPhonePromptAlreadyDone() {
    try {
      return window.sessionStorage.getItem(SS_V2_PHONE_PROMPT_DONE) === "1";
    } catch (eP) {
      return false;
    }
  }

  function markOptionalPhonePromptDone() {
    try {
      window.sessionStorage.setItem(SS_V2_PHONE_PROMPT_DONE, "1");
    } catch (eM) {}
  }

  function handleThanksAfterReason(reasonKey) {
    var rk = String(reasonKey || st().pending_reason_key || "other").toLowerCase();
    var payload = st().pending_reason_payload || { reason: rk };
    var detail = st().pending_reason_detail || {};
    var subCat = detail.sub_category != null ? detail.sub_category : null;
    var textHint =
      detail.custom_text != null ? String(detail.custom_text) : "";

    try {
      console.log("[CF V2 THANKS]", { reason_key: rk });
    } catch (eTh) {}

    if (Cf.State.hasValidStoredPhone()) {
      runBackgroundReasonPhoneSave({
        payload: Object.assign({}, payload),
        phoneNorm: Cf.State.getStoredPhoneNorm(),
        subHint: subCat != null ? String(subCat) : "",
        textHint: textHint,
        reasonKey: rk,
        kind: "reason_phone",
      });
      gracefulCloseWidget();
      return;
    }

    if (optionalPhonePromptAlreadyDone()) {
      gracefulCloseWidget();
      return;
    }
    markOptionalPhonePromptDone();

    Cf.Ui.renderOptionalPhoneFollowup({
      primaryColor: primaryHex(),
      title: "اترك رقمك للمتابعة",
      onBack: showContinuationForPending,
      onSave: function (pn) {
        return Cf.Phone.postReasonMerged(
          Object.assign({}, payload),
          pn,
          subCat != null ? String(subCat) : "",
          textHint,
          rk
        ).then(function () {
          st().background_save_failed = false;
          try {
            if (Cf.Shell && typeof Cf.Shell.showSuccess === "function") {
              Cf.Shell.showSuccess("تم حفظ الرقم");
            }
          } catch (eOkMsg) {}
          try {
            console.log("[CF PHONE SAVE ACK SUCCESS]");
          } catch (ePs) {}
          window.setTimeout(function () {
            gracefulCloseWidget();
          }, 700);
        });
      },
      onSkip: function () {
        gracefulCloseWidget();
      },
    });
    setBubbleShown(true);
  }

  function scrollToCartOrCheckout() {
    try {
      var el =
        document.querySelector('[href*="cart"],[href*="checkout"], #cart,[data-cart-drawer],[data-route="cart"]') ||
        document.getElementById("cart-drawer-toggle");
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ block: "center" });
      }
      if (el && el.click) {
        el.click();
      }
    } catch (eScr) {}
  }

  function handoffAssistThenOpenWa() {
    try {
      console.log("[CF ASSIST HANDOFF] continuation_only=true open_whatsapp=true");
    } catch (eHf) {}
    return Cf.Api.fetchPublicConfig()
      .then(function (cfg) {
        Cf.Config.applyPayload(cfg, "public_config");
        try {
          if (cfg && cfg.whatsapp_url) {
            window.open(cfg.whatsapp_url, "_blank", "noopener,noreferrer");
          }
        } catch (eW) {}
        return Cf.Api.postAssistHandoff().catch(function () {});
      })
      .catch(function () {});
  }

  function runBackgroundReasonPhoneSave(meta) {
    meta = meta || {};
    try {
      console.log("[CF V2 BACKGROUND SAVE]", {
        phase: "start",
        kind: meta.kind || "reason_phone",
        reason_key: String(meta.reasonKey || ""),
      });
    } catch (eVs) {}
    try {
      console.log("[CF BACKGROUND SAVE START]", {
        reason_key: String(meta.reasonKey || ""),
        kind: meta.kind || "reason_phone",
      });
    } catch (eSt) {}
    st().background_save_failed = false;
    Cf.Phone.postReasonMerged(
      meta.payload,
      meta.phoneNorm,
      meta.subHint,
      meta.textHint,
      meta.reasonKey
    )
      .then(function () {
        try {
          console.log("[CF BACKGROUND SAVE SUCCESS]");
        } catch (eOk) {}
        st().background_retry_meta = null;
        st().background_save_failed = false;
      })
      .catch(function () {
        try {
          console.log("[CF BACKGROUND SAVE FAILED]");
        } catch (eF) {}
        st().background_save_failed = true;
        st().background_retry_meta = Object.assign({}, meta, {
          kind: meta.kind || "reason_phone",
          continuationSub: meta.continuationSub,
        });
        try {
          if (Cf.Shell && Cf.Shell.showError) {
            Cf.Shell.showError("تعذّر حفظ البيانات. حاول مرة أخرى لاحقاً.");
          }
        } catch (eE) {}
        showContinuationQuiet(meta.reasonKey, meta.continuationSub);
      });
  }

  function runBackgroundReasonOnly(payload, rk, continuationSub) {
    try {
      console.log("[CF V2 BACKGROUND SAVE]", {
        phase: "start",
        kind: "reason_only",
        reason_key: String(rk || ""),
      });
    } catch (eVs2) {}
    try {
      console.log("[CF BACKGROUND SAVE START]", {
        reason_key: String(rk || ""),
        kind: "reason_only",
      });
    } catch (eSt2) {}
    st().background_save_failed = false;
    var payloadCopy = Object.assign({}, payload || {});
    Cf.Api.postReason(payloadCopy)
      .then(function (j) {
        if (!Cf.Api.reasonPostOk(j)) {
          try {
            console.log("[CF BACKGROUND SAVE FAILED]");
          } catch (eFj) {}
          st().background_save_failed = true;
          st().background_retry_meta = {
            kind: "reason_only",
            payload: payloadCopy,
            reasonKey: rk,
            continuationSub: continuationSub,
          };
          try {
            if (Cf.Shell && Cf.Shell.showError) {
              Cf.Shell.showError(
                "تعذّر حفظ البيانات. يمكنك الضغط على «إعادة إرسال»."
              );
            }
          } catch (eSe) {}
          showContinuationQuiet(rk, continuationSub);
          return;
        }
        try {
          console.log("[CF BACKGROUND SAVE SUCCESS]");
        } catch (eOk2) {}
        st().background_retry_meta = null;
        st().background_save_failed = false;
      })
      .catch(function () {
        try {
          console.log("[CF BACKGROUND SAVE FAILED]");
        } catch (eFc) {}
        st().background_save_failed = true;
        st().background_retry_meta = {
          kind: "reason_only",
          payload: payloadCopy,
          reasonKey: rk,
          continuationSub: continuationSub,
        };
        try {
          if (Cf.Shell && Cf.Shell.showError) {
            Cf.Shell.showError("تعذّر حفظ البيانات. حاول مرة أخرى لاحقاً.");
          }
        } catch (eSe2) {}
        showContinuationQuiet(rk, continuationSub);
      });
  }

  function showContinuationQuiet(reasonKey, subCategory) {
    try {
      var b = Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
      if (b) {
        b.removeAttribute("data-cf-after-reason-phone-step");
      }
    } catch (eRm2) {}
    var rk = String(reasonKey || "other").toLowerCase();
    Cf.Ui.renderContinuation({
      primaryColor: primaryHex(),
      bullets: recoverySuggestionBullets(rk),
      reasonKey: rk,
      compactRecovery: true,
      onContinueCart: function () {
        scrollToCartOrCheckout();
      },
      onThanks: function () {
        handleThanksAfterReason(rk);
      },
      onBackReasons: function () {
        mountReasonList();
      },
      onStartNewTest:
        isMerchantActivationMode() &&
        typeof window.cartflowStartNewMerchantTestLifecycle === "function"
          ? function () {
              try {
                window.cartflowStartNewMerchantTestLifecycle({
                  reason: "widget_start_new_test_action",
                });
                try {
                  console.log(
                    "[TEST SESSION RESET] reason=widget_start_new_test_action"
                  );
                } catch (eLogRs) {}
                window.location.reload();
              } catch (eRs) {}
            }
          : null,
    });
    setBubbleShown(true);
  }

  /** ---- Reason flow internals ---- */

  function openReasonPath(reasonKey, payload, detail) {
    detail = detail || {};
    var rk = String(reasonKey || "").toLowerCase();
    var subCat =
      detail.sub_category != null ? detail.sub_category : null;
    var ackPerf0 =
      typeof performance !== "undefined" && performance.now
        ? performance.now()
        : Date.now();

    if (st().reason_save_in_flight) {
      try {
        console.log("[CF REASON CLICK IGNORED]", {
          reason_key: rk,
          why: "in_flight",
        });
      } catch (eIgn) {}
      return;
    }

    st().pending_reason_key = rk;
    st().pending_reason_payload = Object.assign({}, payload || {});
    st().pending_reason_detail = Object.assign({}, detail || {});
    try {
      console.log("[CF REASON SELECTED V2]", { reason_key: rk });
    } catch (eR) {}

    function setReasonButtonsDisabled(disabled) {
      try {
        var root = Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
        if (!root) return;
        root.querySelectorAll("[data-cf-reason-key], .cf-reason-btn, button[data-reason]").forEach(
          function (btn) {
            if (disabled) btn.setAttribute("disabled", "true");
            else btn.removeAttribute("disabled");
            btn.setAttribute("aria-busy", disabled ? "true" : "false");
          }
        );
      } catch (eDis) {}
    }

    /** Sync selected ack only — «جاري الحفظ…» is deferred (slow path). */
    function acknowledgeReasonPick() {
      try {
        var root = Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
        if (!root) return;
        root.setAttribute("data-cf-reason-transition", "selected");
        root.querySelectorAll("[data-cf-reason-key]").forEach(function (btn) {
          var key = String(btn.getAttribute("data-cf-reason-key") || "").toLowerCase();
          btn.setAttribute("disabled", "true");
          btn.setAttribute("aria-busy", "true");
          if (!btn.getAttribute("data-cf-reason-label")) {
            btn.setAttribute("data-cf-reason-label", btn.textContent || "");
          }
          var base = btn.getAttribute("data-cf-reason-label") || "";
          if (key === rk) {
            btn.setAttribute("data-cf-reason-selected", "1");
            btn.setAttribute("aria-pressed", "true");
            btn.textContent = "✓ " + base;
            btn.style.outline = "2px solid rgba(255,255,255,.92)";
            btn.style.outlineOffset = "1px";
            btn.style.filter = "brightness(1.12)";
            btn.style.opacity = "1";
            btn.style.fontWeight = "700";
          } else {
            btn.removeAttribute("data-cf-reason-selected");
            btn.setAttribute("aria-pressed", "false");
            btn.textContent = base;
            btn.style.outline = "";
            btn.style.filter = "";
            btn.style.opacity = "0.45";
            btn.style.fontWeight = "";
          }
        });
        var ackMs = Math.round(
          ((typeof performance !== "undefined" && performance.now
            ? performance.now()
            : Date.now()) -
            ackPerf0) *
            10
        ) / 10;
        console.log("[CF REASON ACK]", { reason_key: rk, ack_ms: ackMs });
      } catch (eAck) {}
    }

    function showReasonSavingSlowPath() {
      reasonLoadingShown = true;
      try {
        var root = Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
        if (root) root.setAttribute("data-cf-reason-transition", "saving");
        var mount =
          Cf.Shell && Cf.Shell.getContentMount
            ? Cf.Shell.getContentMount()
            : root
            ? root.querySelector("[data-cf-content], .cf-content")
            : null;
        var status = root ? root.querySelector("[data-cf-reason-status]") : null;
        if (!status && mount) {
          status = document.createElement("p");
          status.setAttribute("data-cf-reason-status", "1");
          status.style.cssText =
            "margin:0 0 8px;font-size:12px;line-height:1.4;font-weight:600;color:#e2e8f0;";
          var row = mount.querySelector("[data-cf-reason-row-v2]");
          if (row && row.parentNode) {
            row.parentNode.insertBefore(status, row);
          } else {
            mount.insertBefore(status, mount.firstChild);
          }
        }
        if (status) status.textContent = "جاري الحفظ…";
        if (Cf.Shell && typeof Cf.Shell.showFooterMessage === "function") {
          Cf.Shell.showFooterMessage({ message: "جاري الحفظ…" });
        }
        console.log("[CF REASON SAVE SLOW PATH]", {
          threshold_ms: PERSIST_LOADING_THRESHOLD_MS,
        });
      } catch (eSlow) {}
    }

    function clearReasonLoadingTimer() {
      if (reasonLoadingTimer != null) {
        try {
          window.clearTimeout(reasonLoadingTimer);
        } catch (eCt) {}
        reasonLoadingTimer = null;
      }
    }

    function logReasonPersistTiming() {
      try {
        var ms = Math.round(
          ((typeof performance !== "undefined" && performance.now
            ? performance.now()
            : Date.now()) -
            persistPerf0) *
            10
        ) / 10;
        console.log("[CF REASON PERSIST TIMING]", {
          ms: ms,
          slow_path: !!reasonLoadingShown,
          threshold_ms: PERSIST_LOADING_THRESHOLD_MS,
        });
      } catch (eT) {}
    }

    function clearReasonPickVisual() {
      try {
        var root = Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
        if (!root) return;
        root.removeAttribute("data-cf-reason-transition");
        root.querySelectorAll("[data-cf-reason-key]").forEach(function (btn) {
          var base = btn.getAttribute("data-cf-reason-label");
          if (base != null) btn.textContent = base;
          btn.removeAttribute("data-cf-reason-selected");
          btn.removeAttribute("aria-pressed");
          btn.removeAttribute("data-cf-reason-label");
          btn.style.outline = "";
          btn.style.filter = "";
          btn.style.opacity = "";
          btn.style.fontWeight = "";
        });
        var status = root.querySelector("[data-cf-reason-status]");
        if (status && status.parentNode) status.parentNode.removeChild(status);
      } catch (eClr) {}
    }

    function failReasonPersist(msg) {
      clearReasonLoadingTimer();
      logReasonPersistTiming();
      st().reason_save_in_flight = false;
      st().background_save_failed = true;
      clearReasonPickVisual();
      setReasonButtonsDisabled(false);
      try {
        if (Cf.Shell && Cf.Shell.showError) {
          Cf.Shell.showError(
            msg || "تعذّر حفظ السبب. حاول مرة أخرى."
          );
        }
      } catch (eSe) {}
    }

    function persistThenAdvance(cartBridgeResult) {
      st().background_save_failed = false;
      setReasonButtonsDisabled(true);

      var payloadCopy = Object.assign({}, payload || {});
      if (
        cartBridgeResult &&
        cartBridgeResult.reason_orphan_risk &&
        !cartBridgeResult.persisted
      ) {
        payloadCopy.cf_reason_orphan_risk = true;
        try {
          if (
            Cf.StorefrontCartBridge &&
            typeof Cf.StorefrontCartBridge.getDiagnostics === "function"
          ) {
            payloadCopy.cf_cart_bridge_diagnostic =
              Cf.StorefrontCartBridge.getDiagnostics();
          }
        } catch (eDiag) {}
        try {
          console.log("[CF REASON ORPHAN RISK]", {
            reason_key: rk,
            cart_bridge: payloadCopy.cf_cart_bridge_diagnostic,
          });
        } catch (eOr) {}
      }

      try {
        console.log("[CF REASON PERSIST START]", { reason_key: rk });
      } catch (ePs) {}

      Cf.Api.postReason(payloadCopy)
        .then(function (j) {
          if (!Cf.Api.reasonPostOk(j)) {
            failReasonPersist(
              "تعذّر حفظ السبب. يمكنك المحاولة مرة أخرى."
            );
            st().background_retry_meta = {
              kind: "reason_only",
              payload: payloadCopy,
              reasonKey: rk,
              continuationSub: subCat,
            };
            return;
          }
          clearReasonLoadingTimer();
          logReasonPersistTiming();
          st().reason_save_in_flight = false;
          st().background_retry_meta = null;
          st().background_save_failed = false;
          try {
            if (Cf.Shell && typeof Cf.Shell.hideFooterMessage === "function") {
              Cf.Shell.hideFooterMessage();
            }
          } catch (eHf) {}
          try {
            console.log("[CF REASON PERSIST SUCCESS]", { reason_key: rk });
          } catch (eOk) {}
          showContinuation(rk, subCat);
        })
        .catch(function () {
          failReasonPersist("تعذّر حفظ السبب. حاول مرة أخرى.");
          st().background_retry_meta = {
            kind: "reason_only",
            payload: payloadCopy,
            reasonKey: rk,
            continuationSub: subCat,
          };
        });
    }

    // Selected immediately → persist in background → loading only if slow
    var PERSIST_LOADING_THRESHOLD_MS = 400;
    var persistPerf0 =
      typeof performance !== "undefined" && performance.now
        ? performance.now()
        : Date.now();
    var reasonLoadingShown = false;
    var reasonLoadingTimer = null;
    acknowledgeReasonPick();
    st().reason_save_in_flight = true;
    reasonLoadingTimer = window.setTimeout(
      showReasonSavingSlowPath,
      PERSIST_LOADING_THRESHOLD_MS
    );

    if (
      Cf.StorefrontCartBridge &&
      typeof Cf.StorefrontCartBridge.ensureCartTruthBeforeReason === "function"
    ) {
      Cf.StorefrontCartBridge.ensureCartTruthBeforeReason()
        .then(function (res) {
          persistThenAdvance(res);
        })
        .catch(function () {
          persistThenAdvance({ reason_orphan_risk: true, persisted: false });
        });
      return;
    }
    persistThenAdvance(null);
  }

  function showContinuation(reasonKey, subCategory) {
    try {
      var b = Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
      if (b) {
        b.removeAttribute("data-cf-after-reason-phone-step");
      }
    } catch (eRm) {}
    emitGuide("cartflow-demo-reason-confirmed", {
      reason: reasonKey,
      sub_category:
        subCategory != null && String(subCategory).trim()
          ? String(subCategory).trim()
          : null,
    });
    showContinuationQuiet(reasonKey, subCategory);
  }

  function mountReasonList() {
    st().background_retry_meta = null;
    st().background_save_failed = false;
    var rows =
      Cf.Config && typeof Cf.Config.buildVisibleReasonRows === "function"
        ? Cf.Config.buildVisibleReasonRows()
        : [];
    Cf.Ui.renderReasonGrid({
      primaryColor: primaryHex(),
      rows: rows,
      onPick: function (item) {
        if (item.r === "other") {
          Cf.Ui.renderOtherRecoveryForm({
            primaryColor: primaryHex(),
            onBack: mountReasonList,
            onContinueCart: function (note) {
              var noteStr = String(note || "").trim();
              var payload = { reason: "other" };
              if (noteStr) {
                payload.custom_text = noteStr;
              }
              st().pending_reason_key = "other";
              st().pending_reason_payload = Object.assign({}, payload);
              st().pending_reason_detail = { custom_text: noteStr };
              runBackgroundReasonOnly(payload, "other", null);
              scrollToCartOrCheckout();
            },
            onThanks: function (note) {
              var noteStr = String(note || "").trim();
              var payload = { reason: "other" };
              if (noteStr) {
                payload.custom_text = noteStr;
              }
              st().pending_reason_key = "other";
              st().pending_reason_payload = Object.assign({}, payload);
              st().pending_reason_detail = { custom_text: noteStr };
              runBackgroundReasonOnly(payload, "other", null);
              handleThanksAfterReason("other");
            },
          });
          return;
        }
        openReasonPath(item.r, { reason: item.r }, {});
      },
      onBack: function () {
        showBubbleCartRecovery("cart_prompt_back_from_reason_list");
      },
    });
    emitGuide("cartflow-demo-reason-list-visible", {});
    setBubbleShown(true);
  }

  function showBubbleCartRecovery(tagNote) {
    var _tagS = String(tagNote || "");
    if (_tagS.indexOf("exit_intent") >= 0) {
      if (Cf.Arbitration && typeof Cf.Arbitration.gateExitIntentOpen === "function") {
        var gate = Cf.Arbitration.gateExitIntentOpen({
          trigger_source: _tagS,
          entrypoint: "showBubbleCartRecovery",
        });
        if (!gate || !gate.allowed) {
          return;
        }
        if (gate.openTag) {
          tagNote = gate.openTag;
        }
      } else {
        cfArbitrationShadowObserveOpen("showBubbleCartRecovery", tagNote);
      }
    } else {
      cfArbitrationShadowObserveOpen("showBubbleCartRecovery", tagNote);
    }
    _tagS = String(tagNote || "");
    if (storefrontUiBlocked()) {
      try {
        console.log("[CF WIDGET BLOCKED V2]", {
          gate: st().v2MerchantConfigFailed ? "config_load_failed" : "config_not_resolved",
        });
      } catch (eCfg) {}
      return;
    }
    logConfigBeforeFirstUi();
    if (!merchantAllowsUi()) {
      try {
        console.log("[CF WIDGET BLOCKED V2]", { gate: "merchant_delay_or_disabled" });
      } catch (eB) {}
      return;
    }
    if (
      _tagS !== "manual_debug" &&
      Cf.State.hesitationDelayWallActive &&
      Cf.State.hesitationDelayWallActive()
    ) {
      try {
        console.log("[CF WIDGET BLOCKED V2]", {
          gate: "hesitation_delay_pending",
          remaining_ms:
            Cf.State.hesitationDelayRemainingMs &&
            Cf.State.hesitationDelayRemainingMs(),
        });
      } catch (eHx) {}
      return;
    }
    if (!Cf.Config.widgetGloballyAllowed()) {
      return;
    }
    if (globalSuppressionAbort()) {
      try {
        console.log("[CF WIDGET BLOCKED V2]", { gate: "suppress_after_dismiss" });
      } catch (eB2) {}
      return;
    }
    if (shouldBlockCartTriggers()) {
      return;
    }
    if (Cf.State.sessionConvertedBlock()) {
      return;
    }
    mirrorCartTotals();

    if (Cf.Shell && typeof Cf.Shell.setLastTriggerSource === "function") {
      Cf.Shell.setLastTriggerSource(String(tagNote || "cart_recovery"));
    }

    Cf.Ui.renderYesNo({
      primaryColor: primaryHex(),
      question: getCartRecoveryQuestion(tagNote),
      yes: "نعم",
      no: "لا",
      onYes: function () {
        try {
          if (CartFlowState) {
            CartFlowState.userRejectedHelp = false;
            CartFlowState.rejectionTimestamp = null;
          }
        } catch (eY) {}
        mountReasonList();
      },
      onNo: function () {
        try {
          if (window.CartFlowState) {
            window.CartFlowState.userRejectedHelp = true;
            window.CartFlowState.rejectionTimestamp = Date.now();
          }
        } catch (eNr) {}
        markWidgetDismissed();
        minimizeWidgetPolite();
      },
    });
    setBubbleShown(true);
    emitGuide("cartflow-demo-reason-list-visible", {});
    try {
      console.log("[CF WIDGET SHOW]", { tag: String(tagNote || "cart_recovery"), layer: "v2" });
    } catch (eShw) {}
    try {
      console.log("[CF WIDGET SHOW V2]", { tag: String(tagNote || "cart_recovery") });
    } catch (eSh) {}
  }

  /** Exit intent branches */

  function showExitNoCart() {
    if (Cf.Arbitration && typeof Cf.Arbitration.gateExitIntentOpen === "function") {
      var gate = Cf.Arbitration.gateExitIntentOpen({
        trigger_source: "exit_intent",
        entrypoint: "showExitNoCart",
      });
      if (!gate || !gate.allowed) {
        return;
      }
    } else {
      cfArbitrationShadowObserveOpen("showExitNoCart", "exit_intent");
    }
    if (storefrontUiBlocked()) {
      return;
    }
    logConfigBeforeFirstUi();
    if (!merchantAllowsUi()) {
      return;
    }
    if (
      Cf.State.hesitationDelayWallActive &&
      Cf.State.hesitationDelayWallActive()
    ) {
      try {
        console.log("[CF WIDGET BLOCKED V2]", {
          gate: "exit_intent_hesitation_delay_pending",
          remaining_ms:
            Cf.State.hesitationDelayRemainingMs &&
            Cf.State.hesitationDelayRemainingMs(),
        });
      } catch (eEx) {}
      return;
    }
    if (Cf.State.sessionConvertedBlock()) {
      return;
    }
    Cf.Ui.renderYesNo({
      primaryColor: primaryHex(),
      question: "تحتاج مساعدة قبل ما تطلع؟",
      yes: "نعم",
      no: "لا",
      onYes: function () {
        Cf.Ui.renderBrowsingChoices({
          primaryColor: primaryHex(),
          title: "اختَر واحد يخدمك الآن 👇",
          buttons: [
            {
              label: "أبحث عن منتج",
              onActivate: function () {
                try {
                  if (typeof window.cartflowBrowseProducts === "function") {
                    window.cartflowBrowseProducts();
                  }
                } catch (eBp) {}
              },
            },
            {
              label: "عندي سؤال",
              onActivate: function () {
                handoffAssistThenOpenWa();
              },
            },
            {
              label: "أحتاج مساعدة",
              onActivate: function () {
                handoffAssistThenOpenWa();
              },
            },
          ],
        });
      },
      onNo: function () {
        minimizeWidgetPolite();
      },
    });
    setBubbleShown(true);
  }

  /** ---- Bootstrap ---- */

  function ensureStep1Then(cb) {
    cb = typeof cb === "function" ? cb : function () {};
    if (isDemoPath()) {
      st().step1Ready = true;
      cb();
      return;
    }
    if (st().step1Ready) {
      cb();
      return;
    }

    var finalized = false;
    var pollT0 = Date.now();
    var pollTickIx = 0;

    function finalizeOnce(reason) {
      if (finalized) {
        return;
      }
      finalized = true;
      notifyStep1PublicConfigHydrated = null;

      st().step1Ready = true;
      if (st().step1Poll != null) {
        try {
          clearInterval(st().step1Poll);
        } catch (eCi) {}
        st().step1Poll = null;
      }
      try {
        console.log("[CF READY POLL STOP] reason=" + String(reason || "unknown"));
      } catch (ePl) {}

      cb();
    }

    notifyStep1PublicConfigHydrated = function () {
      try {
        if (!finalized && st().v2PublicConfigHydrated) {
          finalizeOnce("config_loaded");
        }
      } catch (eN1) {}
    };

    function tick() {
      pollTickIx += 1;
      Cf.Api.fetchReady().then(function (j) {
        if (j && j.ready_blocked) {
          finalizeOnce("ready_blocked");
          return;
        }
        Cf.Config.applyPayload(j, "ready");
        mirrorCartTotals();

        if (!finalized && j && j.after_step1) {
          finalizeOnce("after_step1");
          return;
        }
        if (!finalized && st().v2PublicConfigHydrated) {
          finalizeOnce("config_loaded");
          return;
        }

        var elapsed = Date.now() - pollT0;
        if (
          !finalized &&
          (pollTickIx >= MAX_READY_POLL_TICKS || elapsed >= MAX_READY_POLL_DURATION_MS)
        ) {
          finalizeOnce("max_attempts");
        }
      });
    }

    tick();
    if (!st().step1Poll) {
      st().step1Poll = setInterval(tick, READY_POLL_INTERVAL_MS);
    }
  }

  function startFlows() {
    if (Cf._v2FlowsStarted === true) {
      return;
    }
    Cf._v2FlowsStarted = true;

    function bootTriggersAfterConfig() {
      ensureStep1Then(function () {
        if (!merchantAllowsUi()) {
          try {
            console.log("[CartflowWidgetRuntimeV2] merchant gate pauses hesitation UI");
          } catch (eM) {}
        }

        Cf.Triggers.init({
          flowsRef: {},
          fireCartRecovery: function (tag) {
            cfArbitrationShadowObserveTrigger(String(tag || "cart_timer"), "fire_cart_recovery");
            if (st().bubbleShown) {
              return;
            }
            showBubbleCartRecovery(String(tag || "cart_timer"));
          },
          fireExitNoCart: function () {
            var src = isStorefrontRecoveryMode()
              ? "exit_intent_storefront_recovery"
              : "exit_intent";
            if (Cf.Arbitration && typeof Cf.Arbitration.gateExitIntentOpen === "function") {
              var gate = Cf.Arbitration.gateExitIntentOpen({
                trigger_source: src,
                entrypoint: "fireExitNoCart",
                phase: "fire_exit_no_cart",
              });
              if (!gate || !gate.allowed) {
                return;
              }
              return;
            }
            cfArbitrationShadowObserveTrigger("exit_intent", "fire_exit_no_cart");
            if (isStorefrontRecoveryMode()) {
              showBubbleCartRecovery("exit_intent_storefront_recovery");
              return;
            }
            if (!Cf.Triggers.haveCartApprox()) {
              showExitNoCart();
            }
          },
          fireExitWithCart: function () {
            if (!Cf.Triggers.haveCartApprox()) {
              return;
            }
            if (shouldBlockCartTriggers()) {
              return;
            }
            if (v2ShellOccupiedPreventExitIntentDuplicates()) {
              try {
                console.log("[CF TRIGGER BLOCKED] reason=already_open");
              } catch (eBl) {}
              return;
            }
            var openTag = "exit_intent_with_cart";
            if (Cf.Arbitration && typeof Cf.Arbitration.gateExitIntentOpen === "function") {
              var gate = Cf.Arbitration.gateExitIntentOpen({
                trigger_source: "exit_intent_with_cart",
                entrypoint: "fireExitWithCart",
                phase: "fire_exit_with_cart",
              });
              if (!gate || !gate.allowed) {
                return;
              }
              if (gate.openTag) {
                openTag = gate.openTag;
              }
            } else {
              cfArbitrationShadowObserveTrigger("exit_intent_with_cart", "fire_exit_with_cart");
            }
            showBubbleCartRecovery(openTag);
          },
        });

        try {
          console.log("[CF V2 FULLY ISOLATED]", { flows: FLOW_VERSION });
        } catch (eIso) {}

        emitGuide("cartflow-demo-bubble-visible", {});
        try {
          console.log("[CARTFLOW WIDGET V2 FLOWS]", FLOW_VERSION);
        } catch (eFs) {}
      });
    }

    function afterPublicConfig(pc) {
      var ok = pc && typeof pc === "object" && pc.ok !== false;
      if (ok) {
        Cf.Config.applyPayload(pc, "public_config_first");
        mirrorCartTotals();
        st().v2PublicConfigHydrated = true;
        if (isRealStorefrontEmbed()) {
          st().v2MerchantConfigResolved = true;
          try {
            console.log("[CF CONFIG LOADED V2]", {
              source: "public_config_first",
              before_first_ui: true,
              store_slug: Cf.Api.storeSlug && Cf.Api.storeSlug(),
            });
          } catch (eCl) {}
        }
        try {
          if (typeof notifyStep1PublicConfigHydrated === "function") {
            notifyStep1PublicConfigHydrated();
          }
        } catch (ePc) {}
      } else if (isRealStorefrontEmbed()) {
        st().v2MerchantConfigFailed = true;
        try {
          console.log("[CF CONFIG LOAD FAILED]", {
            store_slug: Cf.Api.storeSlug && Cf.Api.storeSlug(),
            ready_blocked: !!(pc && pc.ready_blocked),
          });
        } catch (eCf) {}
        return;
      }

      if (isRealStorefrontEmbed()) {
        Cf.Api.fetchReady().then(function (j) {
          Cf.Config.applyPayload(j || {}, "primed");
          mirrorCartTotals();
          bootTriggersAfterConfig();
        });
      } else {
        bootTriggersAfterConfig();
      }
    }

    if (isRealStorefrontEmbed()) {
      Cf.Api.fetchPublicConfig().then(afterPublicConfig);
      return;
    }

    Cf.Api.fetchReady().then(function (j) {
      Cf.Config.applyPayload(j || {}, "primed");
      mirrorCartTotals();
      Cf.Api.fetchPublicConfig().then(afterPublicConfig);
    });
  }

  var Flows = {
    start: startFlows,
    showBubbleCartRecovery: showBubbleCartRecovery,
    FLOW_VERSION: FLOW_VERSION,
    emitGuideEvent: emitGuide,
    scrollToCartOrCheckout: scrollToCartOrCheckout,
  };
  window.CartflowWidgetRuntime.Flows = Flows;

  /** Dev hook for manual smoke tests without timers. */
  window.cartflowRuntimeV2ShowCartBubble = showBubbleCartRecovery;
})();
