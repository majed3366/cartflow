/**
 * Knowledge Layer — merchant dashboard surface (read-only display).
 * Consumes GET /api/knowledge/report — no insight generation here.
 *
 * TODO(vip-knowledge-separation): VIP cards belong to Action/Attention surfaces,
 * not Knowledge Layer surfaces. Do not render VIP insights in this module.
 */
(function () {
  "use strict";

  var MAX_CARDS = 5;
  var MIN_CARDS = 3;

  var GENERIC_WATCH_PHRASE = "راقب هذا المؤشر خلال الأيام القادمة";

  var REASON_AR = {
    price: "السعر",
    quality: "الجودة",
    shipping: "الشحن",
    delivery: "التوصيل",
    warranty: "الضمان",
    other: "سبب آخر",
    thinking: "يفكّر",
  };

  var REASON_IMPACT_AR = {
    price: "معظم حالات التردد المسجلة مرتبطة بالسعر.",
    quality: "معظم حالات التردد المسجلة مرتبطة بالجودة.",
    shipping: "معظم حالات التردد المسجلة مرتبطة بالشحن.",
    delivery: "معظم حالات التردد المسجلة مرتبطة بالتوصيل.",
    warranty: "معظم حالات التردد المسجلة مرتبطة بالضمان.",
    other: "حالات التردد موزعة على أسباب متنوعة.",
    thinking: "بعض العملاء يحتاجون وقتاً إضافياً قبل الشراء.",
  };

  var REASON_ACTION_AR = {
    price: "راجع التسعير أو وضّح قيمة المنتج بشكل أكبر.",
    quality: "وضّح مواصفات المنتج وضمانات الجودة في صفحة المنتج.",
    shipping: "راجع تكلفة أو مدة الشحن المعروضة للعميل.",
    delivery: "وضّح خيارات التوصيل والمدة المتوقعة بوضوح.",
    warranty: "أبرز سياسة الضمان وخدمة ما بعد البيع.",
    other: "راجع تجربة الشراء من صفحة المنتج حتى الدفع.",
    thinking: "قد يساعد توضيح العروض أو ضمانات الإرجاع في تقريب القرار.",
  };

  var BOTTLENECK_AR = {
    failed: "فشل الإرسال",
    ignored: "رفض العميل المساعدة",
    stopped: "توقّف المسار",
    no_reply: "لم يرد العميل",
  };

  var INSIGHT_PRIORITY = {
    hesitation_top_reason: 100,
    recovery_activity_summary: 90,
    recovery_bottleneck: 85,
    conversion_cart_to_purchase: 80,
    hesitation_distribution: 70,
    traffic_cart_demand_trend: 60,
    store_health_overview: 50,
    conversion_funnel_gaps: 40,
    conversion_no_carts: 30,
    recovery_insufficient_sample: 20,
    hesitation_insufficient_sample: 20,
    traffic_visitor_unavailable: 5,
  };

  var SEVERITY_RANK = { critical: 4, warning: 3, notice: 2, info: 1 };
  var CONF_RANK = { high: 4, medium: 3, low: 2, insufficient: 1 };

  var OIA_LABEL_OBSERVATION = "الملاحظة";
  var OIA_LABEL_IMPACT = "التأثير";
  var OIA_LABEL_ACTION = "الإجراء المقترح";

  var lastKnowledgeContext = { window_days: 7 };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function localizeReason(raw) {
    var k = (raw || "").trim().toLowerCase();
    return REASON_AR[k] || REASON_AR.other;
  }

  function localizeBottleneck(raw) {
    var k = (raw || "").trim().toLowerCase();
    return BOTTLENECK_AR[k] || "يحتاج متابعة";
  }

  function comparisonPeriodLabel(windowDays) {
    var d = parseInt(windowDays, 10) || 7;
    if (d === 7) return "مقارنة بالأسبوع السابق";
    if (d === 30) return "مقارنة بآخر 30 يوماً";
    return "مقارنة بآخر " + String(d) + " يوماً";
  }

  function topReasonFromDistribution(dist) {
    if (!dist) return "";
    var best = "";
    var bestN = -1;
    Object.keys(dist).forEach(function (k) {
      var n = parseInt(dist[k], 10) || 0;
      if (n > bestN) {
        bestN = n;
        best = k;
      }
    });
    return best;
  }

  function formatDistributionObservation(dist) {
    if (!dist) return "لا يوجد توزيع مسجّل بعد.";
    var parts = [];
    Object.keys(dist)
      .sort(function (a, b) {
        return (parseInt(dist[b], 10) || 0) - (parseInt(dist[a], 10) || 0);
      })
      .forEach(function (k) {
        parts.push(localizeReason(k) + ": " + String(dist[k]));
      });
    return parts.length ? parts.join(" · ") : "لا يوجد توزيع مسجّل بعد.";
  }

  function cardTitle(ins) {
    var key = (ins && ins.insight_key) || "";
    if (key === "recovery_bottleneck") return "أكبر فرصة لتحسين الاسترجاع";
    if (key === "traffic_cart_demand_trend") return "اتجاه الطلب (سلات مهجورة)";
    return (ins && ins.title_ar) || "";
  }

  function buildHesitationTopReasonOIA(ins, ev) {
    var reason = localizeReason(ev.top_reason);
    var reasonKey = (ev.top_reason || "other").trim().toLowerCase();
    var obs = reason + " هو السبب الأكثر تسجيلاً حالياً.";
    if (ev.top_count != null && ev.hesitation_total != null) {
      obs +=
        " (" + String(ev.top_count) + " من " + String(ev.hesitation_total) + " حالة تردد).";
    }
    return {
      title: cardTitle(ins),
      observation: obs,
      impact: REASON_IMPACT_AR[reasonKey] || REASON_IMPACT_AR.other,
      action: REASON_ACTION_AR[reasonKey] || REASON_ACTION_AR.other,
    };
  }

  function buildHesitationDistributionOIA(ins, ev) {
    var topKey = topReasonFromDistribution(ev.distribution);
    var action = "ركز أولاً على السبب الأكثر تكراراً.";
    if (topKey) {
      action = "ركز أولاً على «" + localizeReason(topKey) + "» لأنه الأكثر تكراراً.";
    }
    return {
      title: cardTitle(ins),
      observation: formatDistributionObservation(ev.distribution),
      impact:
        "يساعدك على معرفة ما إذا كانت المشكلة مركزة في سبب واحد أو موزعة بين عدة أسباب.",
      action: action,
    };
  }

  function buildRecoveryBottleneckOIA(ins, ev) {
    var b0 = (ev.bottlenecks && ev.bottlenecks[0]) || {};
    var bk = (b0.key || b0.label || "no_reply").trim().toLowerCase();
    var obsMap = {
      no_reply: "لم يرد العميل على الرسائل في أغلب الحالات.",
      failed: "فشل إرسال الرسائل في أغلب الحالات المسجّلة.",
      ignored: "رفض العميل المساعدة في أغلب الحالات المسجّلة.",
      stopped: "توقّف مسار الاسترجاع في أغلب الحالات المسجّلة.",
    };
    var impactMap = {
      no_reply: "عدم التفاعل يقلل فرص تحويل التردد إلى حوار.",
      failed: "فشل الإرسال يمنع الوصول إلى العميل في الوقت المناسب.",
      ignored: "رفض المساعدة يحدّ من فرص متابعة العميل تلقائياً.",
      stopped: "توقّف المسار يترك سلات دون متابعة كاملة.",
    };
    var actionMap = {
      no_reply: "تأكد من صحة بيانات التواصل ونص الرسالة وتوقيت الإرسال.",
      failed: "تحقق من إعدادات واتساب وحالة رقم التواصل.",
      ignored: "راجع نص الرسالة الأولى وتوقيت ظهور الودجت.",
      stopped: "راجع إعدادات الاسترجاع وعدد المحاولات المسموح بها.",
    };
    var obs = obsMap[bk] || "هناك نقطة ضغط واضحة في مسار الاسترجاع.";
    if (b0.count != null) {
      obs += " (" + String(b0.count) + " حدث — " + localizeBottleneck(bk) + ").";
    }
    return {
      title: cardTitle(ins),
      observation: obs,
      impact: impactMap[bk] || "قد يحدّ ذلك من فعالية الاسترجاع الحالية.",
      action: actionMap[bk] || "راجع إعدادات الاسترجاع وبيانات التواصل.",
    };
  }

  function buildRecoveryActivitySummaryOIA(ins, ev) {
    var sent = ev.messages_sent != null ? ev.messages_sent : 0;
    var replies = ev.replies != null ? ev.replies : 0;
    var purchases = ev.purchases != null ? ev.purchases : 0;
    var returns = ev.returns != null ? ev.returns : 0;
    return {
      title: cardTitle(ins),
      observation:
        "رسائل مُرسَلة: " +
        String(sent) +
        " · ردود: " +
        String(replies) +
        " · عائدون للموقع: " +
        String(returns) +
        " · مشتريات: " +
        String(purchases) +
        ".",
      impact: "يوضح مدى تقدم جهود الاسترجاع الحالية.",
      action: "استمر بجمع البيانات حتى تظهر أنماط أوضح.",
    };
  }

  function buildCartTrendOIA(ins, ev, ctx) {
    var period = comparisonPeriodLabel(ctx.window_days);
    var cur = ev.cart_count != null ? ev.cart_count : 0;
    var prev = ev.prev_cart_count != null ? ev.prev_cart_count : 0;
    var trend = (ev.trend || "stable").trim().toLowerCase();
    var obs;
    if (trend === "up") {
      obs = "عدد السلات المسجلة أعلى من الفترة المقارنة (" + period + ").";
    } else if (trend === "down") {
      obs = "عدد السلات المسجلة أقل من الفترة المقارنة (" + period + ").";
    } else {
      obs = "عدد السلات المسجلة مستقر نسبياً (" + period + ").";
    }
    obs +=
      " الحالي: " +
      String(cur) +
      " · المقارنة: " +
      String(prev) +
      ". (مؤشر طلب من CartFlow وليس عدد زوار.)";
    var impactMap = {
      up: "هناك اهتمام أكبر بالمنتجات.",
      down: "الاهتمام بالسلات أقل من الفترة المقارنة.",
      stable: "الطلب على السلات ثابت نسبياً.",
    };
    var actionMap = {
      up: "راقب ما إذا كانت الزيادة تتحول إلى مبيعات فعلية.",
      down: "راجع أسباب التردد وتابع السلات التي لم تُكمل الشراء.",
      stable: "استمر بمراقبة السلات ومسارات الاسترجاع.",
    };
    return {
      title: cardTitle(ins),
      observation: obs,
      impact: impactMap[trend] || impactMap.stable,
      action: actionMap[trend] || actionMap.stable,
    };
  }

  function buildConversionCartToPurchaseOIA(ins, ev) {
    var purchases = ev.purchase_count != null ? ev.purchase_count : 0;
    var carts = ev.cart_count != null ? ev.cart_count : ins.sample_size || 0;
    return {
      title: cardTitle(ins),
      observation:
        String(purchases) + " عملية شراء مؤكدة من " + String(carts) + " سلة في نافذة البيانات.",
      impact: "يوضح ما إذا كانت السلات تتحول إلى شراء فعلي.",
      action: "تابع السلال المفتوحة التي لم تُكمل الشراء بعد.",
    };
  }

  function buildStoreHealthOIA(ins, ev) {
    var signals = (ev.signals || []).slice();
    var obs =
      signals.length > 0
        ? "إشارات البيانات الحالية: " + signals.join("، ") + "."
        : replaceKnownTokens(ins.message_ar || "البيانات الأساسية متاحة.");
    return {
      title: cardTitle(ins),
      observation: obs,
      impact: "تساعدك على فهم جاهزية البيانات قبل الاعتماد على الاستنتاجات.",
      action: "تأكد أن بيانات المتجر والودجت تصل بشكل صحيح.",
    };
  }

  function replaceKnownTokens(text) {
    var s = String(text || "");
    Object.keys(REASON_AR).forEach(function (k) {
      var ar = REASON_AR[k];
      s = s.split("«" + k + "»").join("«" + ar + "»");
    });
    Object.keys(BOTTLENECK_AR).forEach(function (k) {
      s = s.split(k).join(BOTTLENECK_AR[k]);
    });
    return s;
  }

  function isGenericWatchAction(text) {
    return (text || "").trim() === GENERIC_WATCH_PHRASE;
  }

  function buildGenericOIA(ins, ev, ctx) {
    return {
      title: cardTitle(ins),
      observation: replaceKnownTokens(ins.message_ar || "—"),
      impact: "قد يؤثر ذلك على فهمك لما يحدث في المتجر.",
      action: isGenericWatchAction(ins.recommended_action_ar)
        ? "راجع البيانات المصدرية وتأكد من اكتمال التتبع."
        : replaceKnownTokens(ins.recommended_action_ar || ""),
    };
  }

  var OIA_BUILDERS = {
    hesitation_top_reason: buildHesitationTopReasonOIA,
    hesitation_distribution: buildHesitationDistributionOIA,
    recovery_bottleneck: buildRecoveryBottleneckOIA,
    recovery_activity_summary: buildRecoveryActivitySummaryOIA,
    traffic_cart_demand_trend: buildCartTrendOIA,
    conversion_cart_to_purchase: buildConversionCartToPurchaseOIA,
    store_health_overview: buildStoreHealthOIA,
  };

  /**
   * Reusable Observation → Impact → Action card model for present and future insights.
   */
  function buildKnowledgeCardOIA(ins, ctx) {
    var key = (ins && ins.insight_key) || "";
    var ev = (ins && ins.evidence) || {};
    var builder = OIA_BUILDERS[key] || buildGenericOIA;
    var card = builder(ins, ev, ctx || lastKnowledgeContext);
    return {
      title: card.title || cardTitle(ins),
      observation: card.observation || "",
      impact: card.impact || "",
      action: card.action || "",
    };
  }

  function renderOIABlock(label, text) {
    if (!text) return "";
    return (
      '<div class="ma-knowledge-oia-block">' +
      '<p class="ma-knowledge-oia-label">' +
      esc(label) +
      "</p>" +
      '<p class="ma-knowledge-oia-text">' +
      esc(text) +
      "</p>" +
      "</div>"
    );
  }

  function renderOIACard(ins, ctx) {
    var oia = buildKnowledgeCardOIA(ins, ctx);
    return (
      '<article class="ma-knowledge-insight" data-insight-key="' +
      esc(ins.insight_key || "") +
      '" data-category="' +
      esc(ins.category || "") +
      '" data-severity="' +
      esc(ins.severity || "info") +
      '">' +
      '<h3 class="ma-knowledge-insight-title">' +
      esc(oia.title) +
      "</h3>" +
      '<div class="ma-knowledge-oia-stack">' +
      renderOIABlock(OIA_LABEL_OBSERVATION, oia.observation) +
      renderOIABlock(OIA_LABEL_IMPACT, oia.impact) +
      renderOIABlock(OIA_LABEL_ACTION, oia.action) +
      "</div>" +
      "</article>"
    );
  }

  function insightScore(ins) {
    if (!ins) return 0;
    var base = INSIGHT_PRIORITY[ins.insight_key] || 25;
    var sev = SEVERITY_RANK[(ins.severity || "").toLowerCase()] || 1;
    var conf = CONF_RANK[(ins.confidence || "").toLowerCase()] || 1;
    if ((ins.confidence || "").toLowerCase() === "insufficient") {
      return base * 0.2;
    }
    return base + sev * 5 + conf * 3;
  }

  function pickTopInsights(insights) {
    var list = (insights || []).slice();
    if (!list.length) return [];
    list.sort(function (a, b) {
      return insightScore(b) - insightScore(a);
    });
    var actionable = list.filter(function (i) {
      return (i.confidence || "").toLowerCase() !== "insufficient";
    });
    var pool = actionable.length ? actionable : [];
    if (pool.length <= MAX_CARDS) return pool;
    var n = Math.min(MAX_CARDS, Math.max(MIN_CARDS, pool.length));
    return pool.slice(0, n);
  }

  function renderEmptyState(host) {
    host.innerHTML =
      '<div class="ma-knowledge-empty">' +
      '<p class="ma-knowledge-empty-title">لا توجد بيانات كافية حالياً لإعطاء استنتاجات موثوقة.</p>' +
      '<p class="ma-knowledge-empty-sub">استمر في جمع النشاط وسيعرض CartFlow استنتاجات عندما تتوفر بيانات كافية.</p>' +
      "</div>";
  }

  function renderInsightCards(host, insights, ctx) {
    var cards = pickTopInsights(insights);
    if (!cards.length) {
      renderEmptyState(host);
      return;
    }
    host.innerHTML =
      '<div class="ma-knowledge-cards">' +
      cards.map(function (ins) {
        return renderOIACard(ins, ctx);
      }).join("") +
      "</div>";
  }

  function applyKnowledgePayload(payload) {
    var root = byId("ma-knowledge-root");
    var host = byId("ma-knowledge-body");
    if (!root || !host) return;

    if (!payload || !payload.ok || !payload.insights) {
      renderEmptyState(host);
      return;
    }

    lastKnowledgeContext = {
      window_days: payload.window_days || 7,
    };

    var actionable = (payload.insights || []).some(function (i) {
      return (i.confidence || "").toLowerCase() !== "insufficient";
    });
    if (!actionable) {
      renderEmptyState(host);
      return;
    }
    renderInsightCards(host, payload.insights, lastKnowledgeContext);
  }

  function fetchKnowledgeReport() {
    var host = byId("ma-knowledge-body");
    if (!host) return Promise.resolve();

    var url = "/api/knowledge/report?window_days=7&_ts=" + Date.now();
    return fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) {
          renderEmptyState(host);
          return null;
        }
        return r.json();
      })
      .then(function (d) {
        if (d) applyKnowledgePayload(d);
      })
      .catch(function () {
        renderEmptyState(host);
      });
  }

  function bootKnowledgeLayer() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-knowledge-root")) return;
    fetchKnowledgeReport();
  }

  window.maApplyKnowledgePayload = applyKnowledgePayload;
  window.maFetchKnowledgeReport = fetchKnowledgeReport;

  window.__maKnowledgeTestHooks = {
    pickTopInsights: pickTopInsights,
    buildKnowledgeCardOIA: buildKnowledgeCardOIA,
    comparisonPeriodLabel: comparisonPeriodLabel,
    applyKnowledgePayload: applyKnowledgePayload,
    renderEmptyState: renderEmptyState,
    localizeReason: localizeReason,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootKnowledgeLayer);
  } else {
    bootKnowledgeLayer();
  }
})();
