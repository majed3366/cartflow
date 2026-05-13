/**
 * Customer flows (cart recovery + exit-intent branching). Bridges triggers ↔ UI ↔ API ↔ phone module.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var FLOW_VERSION = "v2-layer-alpha1";

  var CONTINUATION = {
    price: "أفهم 👍\nخلني أساعدك بخيار أنسب أو أوضح لك القيمة بشكل أفضل.",
    shipping: "واضح إن الشحن مهم لك 👍\nأقدر أوضح لك خيارات الشحن أو الأسرع للطلب.",
    delivery: "أكيد 👍\nخلني أوضح لك مدة التوصيل المتوقعة بشكل أدق.",
    quality: "أتفهم 👍\nأقدر أوضح لك الجودة والتفاصيل بشكل أفضل.",
    warranty: "أكيد 👍\nأوضح لك سياسة الضمان والاستبدال بكل بساطة.",
    thinking:
      "خذ وقتك 👍\nأقدر أقارن لك بين الخيارات أو أوضح اللي يهمك قبل لا تكمّل.",
    other: "تمام 👍\nأنا معك إذا احتجت أي توضيح قبل تكمل الطلب.",
  };

  var PRICE_SUB_ROWS = [
    { r: "price_discount_request", label: "أبحث عن كود خصم" },
    { r: "price_budget_issue", label: "السعر أعلى من ميزانيتي" },
    { r: "price_cheaper_alternative", label: "أريد خيار أرخص" },
  ];

  function isDemoPath() {
    return /\b\/demo\//i.test(String(window.location.pathname || ""));
  }

  function primaryHex() {
    var M = Cf.Config.merchant();
    return (M && M.widget_primary_color) || "#6366f1";
  }

  function injectLegacyCartflowWidget() {
    try {
      if (document.querySelector("script[data-cf-legacy-widget-v2-fallback=\"1\"]")) {
        return;
      }
      window.__CF_LOAD_LEGACY_CARTFLOW_WIDGET = true;
      var s = document.createElement("script");
      var v =
        window.__cartflow_runtime_v2_build ||
        window.CARTFLOW_RUNTIME_VERSION ||
        "layered-runtime-v1";
      s.src = "/static/cartflow_widget.js?v=" + encodeURIComponent(String(v));
      s.async = true;
      s.setAttribute("data-cf-legacy-widget-v2-fallback", "1");
      (document.body || document.documentElement).appendChild(s);
      try {
        console.warn("[CartflowWidgetRuntimeV2] delegating VIP to legacy bundle");
      } catch (eC) {}
    } catch (eInj) {}
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

  function mirrorAndVipGate() {
    Cf.State.mirrorCartTotalsFromGlobals();
    try {
      if (window.cartflowState && window.cartflowState.isVip === true) {
        injectLegacyCartflowWidget();
        return true;
      }
    } catch (eVi) {}
    return false;
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

  function setBubbleShown(bit) {
    st().bubbleShown = !!bit;
    try {
      if (window.CartFlowState) {
        window.CartFlowState.widgetShown = !!bit;
      }
    } catch (eS) {}
  }

  function getCartRecoveryQuestion() {
    return "تبي أساعدك تكمل طلبك؟";
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
    return Cf.Api
      .postReason({ reason: "human_support" })
      .then(function (pj) {
        if (!Cf.Api.reasonPostOk(pj)) {
          return;
        }
        return Cf.Api.fetchPublicConfig().then(function (cfg) {
          Cf.Config.applyPayload(cfg, "public_config");
          try {
            if (cfg && cfg.whatsapp_url) {
              window.open(cfg.whatsapp_url, "_blank", "noopener,noreferrer");
            }
          } catch (eW) {}
        });
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
            Cf.Shell.showError(
              "تعذّر حفظ البيانات. يمكنك الضغط على «إعادة إرسال»."
            );
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
            Cf.Shell.showError(
              "تعذّر حفظ البيانات. يمكنك الضغط على «إعادة إرسال»."
            );
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
    var retryMeta = st().background_retry_meta;
    Cf.Ui.renderContinuation({
      primaryColor: primaryHex(),
      messages: CONTINUATION,
      reasonKey: reasonKey,
      retryLabel: "إعادة إرسال",
      onContinueCart: function () {
        scrollToCartOrCheckout();
      },
      onAssist: function () {
        handoffAssistThenOpenWa();
      },
      onBackReasons: function () {
        mountReasonList();
      },
      onRetryBackgroundSave:
        retryMeta != null
          ? function () {
              var m = st().background_retry_meta;
              if (!m) {
                return;
              }
              if (m.kind === "reason_only") {
                runBackgroundReasonOnly(
                  Object.assign({}, m.payload),
                  m.reasonKey,
                  m.continuationSub
                );
              } else {
                runBackgroundReasonPhoneSave(Object.assign({}, m));
              }
            }
          : null,
    });
    setBubbleShown(true);
  }

  /** ---- Reason flow internals ---- */

  function openReasonPhoneImmediate(reasonKey, payload, detail) {
    var rk = String(reasonKey || "").toLowerCase();
    detail = detail || {};
    st().pending_reason_key = rk;
    st().pending_reason_payload = Object.assign({}, payload || {});
    st().pending_reason_detail = Object.assign({}, detail || {});
    try {
      console.log("[CF REASON SELECTED V2]", { reason_key: rk });
    } catch (eR) {}
    try {
      console.log("[CF UX REASON INSTANT]", { reason_key: rk });
    } catch (eUx) {}

    Cf.Ui.renderPhoneStep({
      primaryColor: primaryHex(),
      optimisticSave: true,
      onBack: function () {
        mountReasonList();
      },
      onSave: function (pn) {
        try {
          console.log("[CF UX PHONE INSTANT]", { reason_key: rk });
        } catch (ePh) {}
        var subCat =
          detail.sub_category != null ? detail.sub_category : null;
        showContinuation(rk, subCat);
        runBackgroundReasonPhoneSave({
          payload: Object.assign({}, payload || {}),
          phoneNorm: pn,
          subHint: subCat != null ? String(subCat) : "",
          textHint:
            detail.custom_text != null ? String(detail.custom_text) : "",
          reasonKey: rk,
          continuationSub: subCat,
          kind: "reason_phone",
        });
        return Promise.resolve();
      },
    });
    setBubbleShown(true);
    try {
      var root =
        Cf.Shell && Cf.Shell.getRoot ? Cf.Shell.getRoot() : null;
      if (root) {
        root.setAttribute("data-cf-after-reason-phone-step", "1");
      }
    } catch (eAt) {}
  }

  function openReasonPath(reasonKey, payload, detail) {
    detail = detail || {};
    var rk = String(reasonKey || "").toLowerCase();
    var pcm = String(Cf.Config.phoneCaptureMode() || "after_reason").toLowerCase();
    var has = Cf.State.hasValidStoredPhone();
    var subCat =
      detail.sub_category != null ? detail.sub_category : null;

    if (pcm === "none") {
      st().pending_reason_key = rk;
      st().pending_reason_payload = Object.assign({}, payload || {});
      st().pending_reason_detail = Object.assign({}, detail || {});
      try {
        console.log("[CF UX REASON INSTANT]", {
          reason_key: rk,
          path: "to_continuation_direct",
          pcm: pcm,
        });
      } catch (eUr) {}

      showContinuation(rk, subCat);
      runBackgroundReasonOnly(
        Object.assign({}, payload || {}),
        rk,
        subCat
      );
      return;
    }

    if (pcm === "after_reason") {
      openReasonPhoneImmediate(rk, payload, detail);
      return;
    }

    if (!has) {
      openReasonPhoneImmediate(rk, payload, detail);
      return;
    }

    st().pending_reason_key = rk;
    st().pending_reason_payload = Object.assign({}, payload || {});
    st().pending_reason_detail = Object.assign({}, detail || {});
    try {
      console.log("[CF UX REASON INSTANT]", {
        reason_key: rk,
        path: "to_continuation_direct",
        pcm: pcm,
      });
    } catch (eUr2) {}

    showContinuation(rk, subCat);
    runBackgroundReasonOnly(
      Object.assign({}, payload || {}),
      rk,
      subCat
    );
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
        if (item.r === "price") {
          Cf.Ui.renderPriceBranches({
            primaryColor: primaryHex(),
            options: PRICE_SUB_ROWS.map(function (x) {
              return { r: x.r, label: x.label };
            }),
            onPick: function (sub) {
              openReasonPath(
                "price",
                { reason: "price", sub_category: sub.r },
                { sub_category: sub.r }
              );
            },
            onBack: mountReasonList,
          });
          return;
        }
        if (item.r === "other") {
          Cf.Ui.renderOtherDraftForm({
            primaryColor: primaryHex(),
            onBack: mountReasonList,
            onSubmit: function (note) {
              openReasonPath(
                "other",
                { reason: "other", custom_text: note },
                { custom_text: note }
              );
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
    if (!merchantAllowsUi()) {
      try {
        console.log("[CF WIDGET BLOCKED V2]", { gate: "merchant_delay_or_disabled" });
      } catch (eB) {}
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
    if (mirrorAndVipGate()) {
      return;
    }

    if (Cf.Shell && typeof Cf.Shell.setLastTriggerSource === "function") {
      Cf.Shell.setLastTriggerSource(String(tagNote || "cart_recovery"));
    }

    Cf.Ui.renderYesNo({
      primaryColor: primaryHex(),
      question: getCartRecoveryQuestion(),
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
          if (Cf.Shell && typeof Cf.Shell.minimizeLauncher === "function") {
            Cf.Shell.minimizeLauncher();
          } else {
            Cf.Ui.hideBubble();
          }
        } catch (eNo) {
          Cf.Ui.hideBubble();
        }
        setBubbleShown(false);
        try {
          if (window.CartFlowState) {
            window.CartFlowState.userRejectedHelp = true;
            window.CartFlowState.rejectionTimestamp = Date.now();
          }
        } catch (eNr) {}
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
    if (!merchantAllowsUi()) {
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
        Cf.Ui.hideBubble();
        setBubbleShown(false);
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

    function tick() {
      Cf.Api.fetchReady().then(function (j) {
        Cf.Config.applyPayload(j, "ready");
        mirrorAndVipGate();
        if (j && j.after_step1) {
          st().step1Ready = true;
          if (st().step1Poll != null) {
            clearInterval(st().step1Poll);
            st().step1Poll = null;
          }
          cb();
        }
      });
    }

    tick();
    if (!st().step1Poll) {
      st().step1Poll = setInterval(tick, 120);
    }
  }

  function startFlows() {
    if (Cf._v2FlowsStarted === true) {
      return;
    }
    Cf._v2FlowsStarted = true;

    Cf.Api.fetchReady().then(function (j) {
      Cf.Config.applyPayload(j || {}, "primed");
      mirrorAndVipGate();
      if (window.cartflowState && window.cartflowState.isVip === true) {
        return;
      }

      Cf.Api.fetchPublicConfig().then(function (pc) {
        if (pc && typeof pc === "object" && pc.ok !== false) {
          Cf.Config.applyPayload(pc, "public_config_first");
          mirrorAndVipGate();
        }
      });

      if (window.cartflowState && window.cartflowState.isVip === true) {
        return;
      }

      ensureStep1Then(function () {
        if (mirrorAndVipGate()) {
          return;
        }
        if (!merchantAllowsUi()) {
          try {
            console.log("[CartflowWidgetRuntimeV2] merchant gate pauses hesitation UI");
          } catch (eM) {}
        }

        Cf.Triggers.init({
          flowsRef: {},
          fireCartRecovery: function (tag) {
            if (st().bubbleShown) {
              return;
            }
            showBubbleCartRecovery(String(tag || "cart_timer"));
          },
          fireExitNoCart: function () {
            if (!Cf.Triggers.haveCartApprox()) {
              showExitNoCart();
            }
          },
          fireExitWithCart: function () {
            if (Cf.Triggers.haveCartApprox()) {
              if (shouldBlockCartTriggers()) {
                return;
              }
              showBubbleCartRecovery("exit_intent_with_cart");
            }
          },
        });

        emitGuide("cartflow-demo-bubble-visible", {});
        try {
          console.log("[CARTFLOW WIDGET V2 FLOWS]", FLOW_VERSION);
        } catch (eFs) {}
      });
    });
  }

  var Flows = {
    start: startFlows,
    showBubbleCartRecovery: showBubbleCartRecovery,
    FLOW_VERSION: FLOW_VERSION,
    injectLegacyFallback: injectLegacyCartflowWidget,
    emitGuideEvent: emitGuide,
    scrollToCartOrCheckout: scrollToCartOrCheckout,
  };
  window.CartflowWidgetRuntime.Flows = Flows;

  /** Dev hook for manual smoke tests without timers. */
  window.cartflowRuntimeV2ShowCartBubble = showBubbleCartRecovery;
})();
