/**
 * MEIF + MEH V1 — merchant page consumer for governed integration packages.
 * No business logic. Renders packages with trust-class labeling.
 */
(function () {
  "use strict";

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function meif(summary) {
    return (summary && summary.merchant_experience_integration_v1) || null;
  }

  function trustBadge(it) {
    var label = it.trust_class_ar || it.trust_class || "";
    if (!label) return "";
    return (
      '<span class="meif-trust meif-trust--' +
      esc(it.trust_class || "observation") +
      '">' +
      esc(label) +
      "</span>"
    );
  }

  function renderItemList(items, emptyAr) {
    var list = Array.isArray(items) ? items : [];
    if (!list.length) {
      return '<p class="meif-empty">' + esc(emptyAr || "لا عناصر محكومة الآن.") + "</p>";
    }
    return (
      '<ul class="meif-list">' +
      list
        .map(function (it) {
          var title =
            it.merchant_statement_ar ||
            it.merchant_value ||
            it.information_class ||
            "ملاحظة";
          var meta = [
            it.information_class || "",
            it.presentation_intent || "",
            it.freshness_state || "",
          ]
            .filter(Boolean)
            .join(" · ");
          return (
            '<li class="meif-item" data-trust="' +
            esc(it.trust_class || "") +
            '">' +
            trustBadge(it) +
            '<div class="meif-item__title">' +
            esc(title) +
            "</div>" +
            (meta
              ? '<div class="meif-item__meta">' + esc(meta) + "</div>"
              : "") +
            "</li>"
          );
        })
        .join("") +
      "</ul>"
    );
  }

  function suppressSetupTheatre(home) {
    if (!home || !home.suppress_setup_theatre) return;
    var selectors = [
      "#ma-setup-readiness-panel",
      "#ma-activation-journey",
      ".ma-setup-experience",
      "[data-ma-setup-theatre]",
    ];
    selectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.hidden = true;
        el.setAttribute("data-meh-suppressed", "1");
      });
    });
  }

  function applyHome(summary) {
    var pkg = meif(summary);
    if (!pkg || !pkg.ok || !pkg.pages || !pkg.pages.home) return false;
    var home = pkg.pages.home;
    var root = document.getElementById("ma-home-experience-root");
    if (!root) return false;
    var ops = home.operational_truth || {};
    var sections = home.sections || {};
    var cue = home.chronology_cue || {};
    var html = "";
    html +=
      '<section class="meif-home" data-meif="1" data-meh="1">' +
      '<header class="meif-home__header">' +
      "<h2>ما الذي يجب أن تعرفه الآن؟</h2>" +
      '<p class="meif-home__ops"><span class="meif-trust meif-trust--fact">حقيقة</span> سلات مسجّلة: ' +
      esc(String(ops.abandoned_carts != null ? ops.abandoned_carts : "—")) +
      " · مشتريات موثّقة: " +
      esc(String(ops.purchase_truth != null ? ops.purchase_truth : "—")) +
      " · أسباب تردد: " +
      esc(String(ops.hesitation_reasons != null ? ops.hesitation_reasons : "—")) +
      "</p>";
    if (cue.as_of) {
      html +=
        '<p class="meif-item__meta">' +
        esc(cue.label_ar || "نافذة المراجعة") +
        ": " +
        esc(String(cue.assembly_window || "")) +
        " · as_of " +
        esc(String(cue.as_of)) +
        (cue.note_ar ? " — " + esc(cue.note_ar) : "") +
        "</p>";
    }
    html += "</header>";
    html +=
      '<section class="meif-block"><h3>ملخص تنفيذي</h3>' +
      renderItemList(sections.executive_summary, "لا ملخص تنفيذي محكوم بعد.") +
      "</section>";
    html +=
      '<section class="meif-block"><h3>انتباه حرج</h3>' +
      renderItemList(
        sections.critical_attention,
        ops.has_durable_carts
          ? "هناك سلات مسجّلة — راجع مساحة القرار أو السلال."
          : "لا انتباه حرج محكوم الآن."
      ) +
      "</section>";
    html +=
      '<section class="meif-block"><h3>صحة تشغيلية</h3>' +
      renderItemList(sections.operational_health, "لا حالة تشغيلية محكومة بعد.") +
      "</section>";
    html +=
      '<section class="meif-block"><h3>معرفة</h3>' +
      renderItemList(sections.knowledge_highlights, "لا معرفة مترجمة بعد.") +
      "</section>";
    html +=
      '<section class="meif-block"><h3>إرشاد تجاري</h3>' +
      renderItemList(
        sections.commercial_guidance_highlights,
        "لا توصية تشغيلية موجّهة الآن."
      ) +
      "</section>";
    if (
      sections.monitoring_observations &&
      sections.monitoring_observations.length
    ) {
      html +=
        '<section class="meif-block"><h3>ملاحظات مراقبة (ليست توصيات)</h3>' +
        renderItemList(sections.monitoring_observations, "") +
        "</section>";
    }
    html += "</section>";
    root.className = "ma-home-experience meif-home-root";
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    suppressSetupTheatre(home);
    return true;
  }

  function applyCartsGate(summary) {
    var pkg = meif(summary);
    if (!pkg || !pkg.pages || !pkg.pages.carts) return;
    var carts = pkg.pages.carts;
    var loading = document.getElementById("ma-carts-unified-loading");
    var banner = document.getElementById("meif-carts-truth-banner");
    if (banner) {
      banner.hidden = false;
      banner.innerHTML =
        '<span class="meif-trust meif-trust--fact">حقيقة</span> ' +
        esc(carts.status_message_ar || "");
    }
    if (carts.forbid_please_wait && loading) {
      loading.hidden = true;
      loading.setAttribute("aria-busy", "false");
    }
  }

  function applyCommunication(summary) {
    var pkg = meif(summary);
    var root = document.getElementById("meif-communication-root");
    if (!root || !pkg || !pkg.pages || !pkg.pages.communication) return false;
    var comm = pkg.pages.communication;
    var ops = comm.operational_truth || {};
    root.innerHTML =
      '<section class="meif-comms" data-meif="1" data-meh="1">' +
      "<h2>التواصل — متابعة التشغيل</h2>" +
      "<p><span class=\"meif-trust meif-trust--fact\">حقيقة</span> " +
      esc(comm.status_message_ar || "") +
      "</p>" +
      '<p class="meif-item__meta">إرسال: ' +
      esc(String(ops.mock_whatsapp_sent != null ? ops.mock_whatsapp_sent : 0)) +
      " · جداول: " +
      esc(String(ops.recovery_schedules != null ? ops.recovery_schedules : 0)) +
      "</p>" +
      renderItemList(
        (comm.sections && comm.sections.composition_items) || [],
        "لا عناصر تواصل محكومة بعد — هذه ليست صفحة إعدادات واتساب."
      ) +
      '<p><a href="#messages">سجل الرسائل المرسلة</a> · <a href="#whatsapp">إعدادات واتساب</a></p>' +
      "</section>";
    return true;
  }

  function applyDecision(summary) {
    var pkg = meif(summary);
    var root = document.getElementById("meif-decision-root");
    if (!root || !pkg || !pkg.pages || !pkg.pages.decision_workspace) return false;
    var dw = pkg.pages.decision_workspace;
    var sections = dw.sections || {};
    root.innerHTML =
      '<section class="meif-decision" data-meif="1" data-meh="1">' +
      "<h2>لماذا يحدث هذا، وما الذي يجب مراجعته؟</h2>" +
      '<section class="meif-block"><h3>عناصر للمراجعة</h3>' +
      renderItemList(sections.review_items, "لا عناصر مراجعة محكومة بعد.") +
      "</section>" +
      '<section class="meif-block"><h3>سياق المعرفة</h3>' +
      renderItemList(sections.knowledge_context, "لا سياق معرفة مترجم بعد.") +
      "</section></section>";
    return true;
  }

  window.maApplyMerchantExperienceIntegrationV1 = function (summary) {
    if (!window.CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1) return false;
    var pkg = meif(summary);
    if (!pkg || !pkg.enabled) return false;
    var homeOk = applyHome(summary);
    applyCartsGate(summary);
    applyCommunication(summary);
    applyDecision(summary);
    return homeOk;
  };
})();
