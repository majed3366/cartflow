/**
 * MSR V1 — Merchant Surface Realization (MEIF consumer).
 * Reveals existing packages only. No business logic. No new intelligence.
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

  function lineage(it) {
    return (it && it.source_lineage) || {};
  }

  function explainOf(it) {
    var lin = lineage(it);
    return lin.explainability || it.explainability || {};
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

  function confidenceLabel(it) {
    var c =
      it.confidence_label ||
      it.confidence_level ||
      it.confidence ||
      lineage(it).confidence ||
      "";
    if (!c || c === "n/a" || c === "none") return "";
    var ar = {
      high: "ثقة عالية",
      medium: "ثقة متوسطة",
      low: "ثقة منخفضة",
      very_high: "ثقة مرتفعة جداً",
      insufficient: "أدلة غير كافية",
      unknown: "ثقة غير محددة",
    };
    return ar[String(c).toLowerCase()] || String(c);
  }

  function titleOf(it) {
    var ex = explainOf(it);
    return (
      it.merchant_statement_ar ||
      ex.what_happened_ar ||
      it.merchant_value ||
      it.information_class ||
      "ملاحظة"
    );
  }

  function suggestedAction(it) {
    var ex = explainOf(it);
    if (ex.next_step_ar) return ex.next_step_ar;
    if (ex.suggested_action_ar) return ex.suggested_action_ar;
    var cls = String(it.information_class || "");
    var trust = String(it.trust_class || "");
    var src = String(it.source_type || "");
    if (trust === "recommendation" || cls === "commercial_guidance") {
      return "راجع التوصية في مساحة القرار قبل التنفيذ.";
    }
    if (src === "operational_truth" && cls === "critical_attention") {
      return "ابدأ من السلال أو مساحة القرار — هذه أولوية تشغيلية.";
    }
    if (src === "operational_truth" && cls === "operational_health") {
      return "راقب الإيقاع التشغيلي؛ لا إجراء فوري إن لم يتصاعد الانتباه.";
    }
    if (cls === "knowledge" || trust === "interpretation") {
      return "اعتبرها سياقاً — ليست أمراً بالتنفيذ.";
    }
    if (trust === "observation") {
      return "للمراقبة فقط — ليست توصية تشغيل.";
    }
    return "";
  }

  function renderDecisionCard(it) {
    var ex = explainOf(it);
    var why = ex.why_true_ar || "";
    var evidence = ex.evidence_ar || "";
    var conf = confidenceLabel(it);
    var action = suggestedAction(it);
    var gkey = lineage(it).guidance_key || "";
    if (!why && gkey) {
      why = "مرتبط بتوجيه تشغيلي محكوم («" + gkey + "»).";
    }
    if (!evidence && lineage(it).truth_id) {
      evidence =
        "حقيقة تشغيلية: " +
        String(lineage(it).truth_id) +
        (lineage(it).count != null ? " · العدد " + lineage(it).count : "");
    }
    if (!evidence && it.source_type) {
      evidence = "مصدر محكوم: " + String(it.source_type);
    }
    var parts = [];
    parts.push(
      '<article class="meif-card meif-card--decision" data-trust="' +
        esc(it.trust_class || "") +
        '">'
    );
    parts.push('<div class="meif-card__head">' + trustBadge(it));
    if (conf) {
      parts.push('<span class="meif-chip">' + esc(conf) + "</span>");
    }
    if (it.freshness_state) {
      parts.push(
        '<span class="meif-chip meif-chip--mute">' +
          esc(String(it.freshness_state)) +
          "</span>"
      );
    }
    parts.push("</div>");
    parts.push(
      '<h4 class="meif-card__title">' + esc(titleOf(it)) + "</h4>"
    );
    if (why) {
      parts.push(
        '<p class="meif-card__row"><span class="meif-k">لماذا</span> ' +
          esc(why) +
          "</p>"
      );
    }
    if (evidence) {
      parts.push(
        '<p class="meif-card__row"><span class="meif-k">الدليل</span> ' +
          esc(evidence) +
          "</p>"
      );
    }
    if (conf) {
      parts.push(
        '<p class="meif-card__row"><span class="meif-k">الثقة</span> ' +
          esc(conf) +
          "</p>"
      );
    }
    if (action) {
      parts.push(
        '<p class="meif-card__action"><span class="meif-k">الخطوة المقترحة</span> ' +
          esc(action) +
          "</p>"
      );
    }
    parts.push("</article>");
    return parts.join("");
  }

  function renderBriefCard(it, opts) {
    opts = opts || {};
    var action = opts.withAction ? suggestedAction(it) : "";
    var conf = confidenceLabel(it);
    return (
      '<article class="meif-card" data-trust="' +
      esc(it.trust_class || "") +
      '">' +
      '<div class="meif-card__head">' +
      trustBadge(it) +
      (conf ? '<span class="meif-chip">' + esc(conf) + "</span>" : "") +
      "</div>" +
      '<div class="meif-card__title">' +
      esc(titleOf(it)) +
      "</div>" +
      (action
        ? '<p class="meif-card__action">' + esc(action) + "</p>"
        : "") +
      "</article>"
    );
  }

  function renderCardList(items, emptyAr, mode) {
    var list = Array.isArray(items) ? items : [];
    if (!list.length) {
      return '<p class="meif-empty">' + esc(emptyAr || "لا عناصر محكومة الآن.") + "</p>";
    }
    return (
      '<div class="meif-cards">' +
      list
        .map(function (it) {
          return mode === "decision"
            ? renderDecisionCard(it)
            : renderBriefCard(it, { withAction: mode === "action" });
        })
        .join("") +
      "</div>"
    );
  }

  function healthVerdict(ops, home) {
    var carts = Number(ops.abandoned_carts || 0);
    var purchases = Number(ops.purchase_truth || 0);
    var critical = ((home.sections || {}).critical_attention || []).length;
    if (!ops.has_durable_carts && carts === 0) {
      return {
        tone: "quiet",
        title: "لا نشاط سلات مسجّل بعد",
        body: "CartFlow جاهز للمراقبة — لم تُسجَّل سلات في حقيقة المتجر حتى الآن.",
      };
    }
    if (critical > 0 || carts >= 5) {
      return {
        tone: "attention",
        title: "متجرك يحتاج انتباهك اليوم",
        body:
          "هناك أولويات تشغيلية ظاهرة. ابدأ من «ما يستحق الانتباه» قبل فتح التفاصيل.",
      };
    }
    if (purchases > 0) {
      return {
        tone: "stable",
        title: "الإيقاع التشغيلي مستقر نسبياً",
        body:
          "توجد سلات ومشتريات موثّقة. راجع الملخص ثم انتقل للتفاصيل عند الحاجة فقط.",
      };
    }
    return {
      tone: "watch",
      title: "CartFlow يراقب متجرك",
      body: "هناك نشاط مسجّل. ركّز على الانتباه الحرج قبل أي صفحة تفصيلية.",
    };
  }

  function suppressSetupTheatre(home) {
    if (!home || !home.suppress_setup_theatre) return;
    [
      "#ma-setup-readiness-panel",
      "#ma-activation-journey",
      ".ma-setup-experience",
      "[data-ma-setup-theatre]",
    ].forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.hidden = true;
        el.setAttribute("data-meh-suppressed", "1");
      });
    });
  }

  function renderDecisionBlock(dec) {
    if (!dec || typeof dec !== "object") return "";
    if (dec.has_decision) {
      return (
        '<div class="meif-decision" data-decision="1" data-decision-status="DECISION">' +
        '<p class="meif-decision__eyebrow">قرار اليوم</p>' +
        '<h4 class="meif-decision__title" data-decision-text="1">' +
        esc(String(dec.decision || "")) +
        "</h4>" +
        '<p class="meif-card__row"><strong>لماذا:</strong> ' +
        esc(String(dec.why || "")) +
        "</p>" +
        '<p class="meif-card__row"><strong>الأثر المتوقع:</strong> ' +
        esc(String(dec.expected_business_impact || "")) +
        "</p>" +
        '<p class="meif-card__action" data-decision-action="1"><strong>المطلوب منك:</strong> ' +
        esc(String(dec.required_merchant_action || "")) +
        "</p>" +
        '<p class="meif-card__row"><strong>مقياس النجاح:</strong> ' +
        esc(String(dec.success_metric || "")) +
        "</p>" +
        '<p class="meif-card__row"><strong>نافذة المراجعة:</strong> ' +
        esc(String(dec.review_window || "")) +
        " · <strong>ثقة القرار:</strong> " +
        esc(String(dec.decision_confidence || "")) +
        "</p>" +
        (dec.evidence_summary
          ? '<p class="meif-card__row meif-card__evidence"><strong>الأدلة:</strong> ' +
            esc(String(dec.evidence_summary)) +
            "</p>"
          : "") +
        "</div>"
      );
    }
    return (
      '<div class="meif-decision meif-decision--none" data-decision="1" data-decision-status="NO_DECISION">' +
      '<p class="meif-decision__eyebrow">لا قرار</p>' +
      '<h4 class="meif-decision__title">NO DECISION</h4>' +
      '<p class="meif-card__row"><strong>الدليل الناقص:</strong> ' +
      esc(String(dec.missing_evidence || "أدلة غير كافية.")) +
      "</p>" +
      (dec.evidence_summary
        ? '<p class="meif-card__row meif-card__evidence"><strong>ما يتوفر الآن:</strong> ' +
          esc(String(dec.evidence_summary)) +
          "</p>"
        : "") +
      "</div>"
    );
  }

  function renderFindingCard(it, surface) {
    var fid = String((it && it.finding_id) || "");
    var ftype = String((it && it.finding_type) || "");
    if (!fid || !ftype) {
      pushRenderDiag({
        finding_id: fid || null,
        finding_type: ftype || null,
        surface_requested: surface,
        renderer_invoked: true,
        render_accepted: false,
        render_skipped: true,
        skip_reason: "missing_finding_id_or_type",
      });
      return "";
    }
    var title = String(it.title || it.merchant_statement_ar || "");
    var explanation = String(it.explanation || "");
    var evidence = String(it.evidence_summary || "");
    var confidence = String(it.confidence || "");
    var action = String(it.recommended_action || "");
    var confAr = confidenceLabel({ confidence: confidence }) || confidence;
    var dec = (it && it.merchant_decision_v1) || null;
    pushRenderDiag({
      finding_id: fid,
      finding_type: ftype,
      surface_requested: surface,
      renderer_invoked: true,
      render_accepted: true,
      render_skipped: false,
      skip_reason: null,
    });
    return (
      '<article class="meif-card meif-card--finding" data-mebf="1" data-finding-id="' +
      esc(fid) +
      '" data-finding-type="' +
      esc(ftype) +
      '" data-has-decision="' +
      (dec && dec.has_decision ? "1" : "0") +
      '">' +
      '<div class="meif-card__head">' +
      '<span class="meif-trust meif-trust--observation">استنتاج تجاري</span>' +
      (confAr
        ? '<span class="meif-conf">' + esc(confAr) + "</span>"
        : "") +
      "</div>" +
      renderDecisionBlock(dec) +
      '<h4 class="meif-card__title" data-mebf-title="1">' +
      esc(title) +
      "</h4>" +
      (explanation
        ? '<p class="meif-card__row" data-mebf-explanation="1">' +
          esc(explanation) +
          "</p>"
        : "") +
      (evidence
        ? '<p class="meif-card__row meif-card__evidence" data-mebf-evidence="1"><strong>الأدلة:</strong> ' +
          esc(evidence) +
          "</p>"
        : "") +
      (!dec && action
        ? '<p class="meif-card__action" data-mebf-action="1"><strong>الخطوة المقترحة:</strong> ' +
          esc(action) +
          "</p>"
        : "") +
      '<p class="meif-card__meta"><code data-mebf-id="1">' +
      esc(fid) +
      "</code> · <code>" +
      esc(ftype) +
      "</code></p>" +
      "</article>"
    );
  }

  function renderFindingsBlock(items, surface, emptyMsg) {
    var list = Array.isArray(items) ? items : [];
    var html =
      '<div class="meif-cards meif-cards--findings" data-mebf-surface="' +
      esc(surface) +
      '">';
    var painted = 0;
    for (var i = 0; i < list.length; i++) {
      var card = renderFindingCard(list[i], surface);
      if (card) {
        html += card;
        painted += 1;
      }
    }
    if (!painted) {
      html +=
        '<p class="meif-empty">' +
        esc(emptyMsg || "لا استنتاجات تجارية مُلزمة بعد.") +
        "</p>";
    }
    html += "</div>";
    return { html: html, painted: painted };
  }

  var _mebfRenderDiagnostics = [];

  function pushRenderDiag(row) {
    _mebfRenderDiagnostics.push(row || {});
  }

  function publishRenderDiagnostics(summary, surface) {
    var pkg = meif(summary) || {};
    var binding = pkg.business_findings_binding_v1 || {};
    var merged = [];
    var base = Array.isArray(binding.diagnostics) ? binding.diagnostics : [];
    for (var i = 0; i < base.length; i++) {
      merged.push(Object.assign({}, base[i]));
    }
    for (var j = 0; j < _mebfRenderDiagnostics.length; j++) {
      var d = _mebfRenderDiagnostics[j];
      if (!d) continue;
      var hit = null;
      for (var k = 0; k < merged.length; k++) {
        if (merged[k].finding_id && merged[k].finding_id === d.finding_id) {
          hit = merged[k];
          break;
        }
      }
      if (hit) {
        hit.renderer_invoked = !!d.renderer_invoked;
        hit.render_accepted = !!d.render_accepted;
        hit.render_skipped = !!d.render_skipped;
        hit.skip_reason = d.skip_reason || hit.skip_reason;
        hit.surface_rendered = surface;
      } else {
        merged.push(
          Object.assign({ surface_rendered: surface }, d)
        );
      }
    }
    window.__mebfRenderDiagnostics = {
      binding_version: binding.binding_version || "mebf_v1",
      surface: surface,
      findings_bound: binding.findings_bound,
      home_bound: binding.home_bound,
      diagnostics: merged,
      paint_events: _mebfRenderDiagnostics.slice(),
    };
    try {
      document.documentElement.setAttribute(
        "data-mebf-painted",
        String(
          _mebfRenderDiagnostics.filter(function (x) {
            return x && x.render_accepted;
          }).length
        )
      );
    } catch (e) {}
  }

  function applyHome(summary) {
    var pkg = meif(summary);
    if (!pkg || !pkg.ok || !pkg.pages || !pkg.pages.home) return false;
    var home = pkg.pages.home;
    var root = document.getElementById("ma-home-experience-root");
    if (!root) return false;
    /* Home Executive Summary / Situation portfolio owns Home — do not overwrite. */
    if (
      root.querySelector("[data-hes='1']") ||
      (summary && summary.home_surface_mode === "executive_summary_v1")
    ) {
      return false;
    }
    _mebfRenderDiagnostics = [];
    var ops = home.operational_truth || {};
    var sections = home.sections || {};
    var cue = home.chronology_cue || {};
    var verdict = healthVerdict(ops, home);
    var watching = ops.has_durable_carts || Number(ops.abandoned_carts || 0) > 0;
    var html = "";
    html +=
      '<section class="meif-surface meif-home" data-meif="1" data-msr="1" data-mebf="1">' +
      '<header class="meif-brief">' +
      '<p class="meif-eyebrow">إحاطة تنفيذية</p>' +
      "<h2>" +
      esc(verdict.title) +
      "</h2>" +
      '<p class="meif-lede">' +
      esc(verdict.body) +
      "</p>" +
      '<div class="meif-watch meif-watch--' +
      esc(verdict.tone) +
      '">' +
      '<span class="meif-trust meif-trust--fact">حقيقة</span> ' +
      (watching
        ? "CartFlow يراقب متجرك الآن ضمن نافذة المراجعة الحالية."
        : "CartFlow جاهز للمراقبة — بانتظار تسجيل نشاط.") +
      "</div>" +
      "</header>";

    /* Gate 2 — Home never explains decisions; route to Cart Workspace. */
    var decisions = sections.merchant_decisions || [];
    html +=
      '<section class="meif-block meif-block--decisions" aria-label="قرارات اليوم" data-decision-home="1">' +
      "<h3>قرارات اليوم</h3>" +
      '<p class="meif-lede">' +
      (decisions.length
        ? "توجد قرارات تحتاج مراجعتك في مساحة القرار."
        : "لا تتوفر أدلة كافية لإصدار قرار اليوم.") +
      "</p>" +
      '<p class="meif-next"><a href="#workspace">عرض التفاصيل ← مساحة القرار</a></p>' +
      "</section>";
    var findingsBlock = { painted: false, html: "" };

    html +=
      '<section class="meif-block meif-block--facts" aria-label="صحة المتجر">' +
      "<h3>هل متجري بصحة جيدة اليوم؟</h3>" +
      '<ul class="meif-facts">' +
      "<li><strong>" +
      esc(String(ops.abandoned_carts != null ? ops.abandoned_carts : "—")) +
      "</strong><span>سلات مسجّلة</span></li>" +
      "<li><strong>" +
      esc(String(ops.purchase_truth != null ? ops.purchase_truth : "—")) +
      "</strong><span>مشتريات موثّقة</span></li>" +
      "<li><strong>" +
      esc(String(ops.hesitation_reasons != null ? ops.hesitation_reasons : "—")) +
      "</strong><span>أسباب تردد</span></li>" +
      "</ul></section>";

    html +=
      '<section class="meif-block meif-block--priority" aria-label="الانتباه">' +
      "<h3>ما الذي يستحق انتباهك أولاً؟</h3>" +
      renderCardList(
        sections.critical_attention,
        ops.has_durable_carts
          ? "هناك سلات مسجّلة — افتح السلال أو مساحة القرار."
          : "لا انتباه حرج محكوم الآن.",
        "action"
      ) +
      "</section>";

    html +=
      '<section class="meif-block" aria-label="الملخص التنفيذي">' +
      "<h3>ماذا يجب أن تعرف قبل أي صفحة تفصيلية؟</h3>" +
      (findingsBlock.painted
        ? '<p class="meif-lede">الملخص أعلاه مبني على استنتاجات تجارية مُلزمة (Business Findings).</p>'
        : renderCardList(
            sections.executive_summary,
            "لا ملخص تنفيذي محكوم بعد.",
            "brief"
          )) +
      "</section>";

    html +=
      '<div class="meif-split">' +
      '<section class="meif-block" aria-label="تحسّن">' +
      "<h3>ماذا تحسّن أو ظهر حديثاً؟</h3>" +
      renderCardList(
        sections.knowledge_highlights,
        "لا إشارات معرفة مترجمة بعد.",
        "brief"
      ) +
      "</section>" +
      '<section class="meif-block" aria-label="تشغيل">' +
      "<h3>الصحة التشغيلية</h3>" +
      renderCardList(
        sections.operational_health,
        "لا حالة تشغيلية محكومة بعد.",
        "brief"
      ) +
      "</section>" +
      "</div>";

    html +=
      '<section class="meif-block" aria-label="إرشاد">' +
      "<h3>ما الذي يستحق قراراً؟</h3>" +
      '<p class="meif-next"><a href="#workspace">افتح مساحة القرار للتفسير الكامل ←</a></p>' +
      "</section>";

    if (cue.as_of) {
      html +=
        '<footer class="meif-chrono">' +
        '<span class="meif-trust meif-trust--fact">حقيقة زمنية</span> ' +
        esc(cue.label_ar || "نافذة المراجعة") +
        " · " +
        esc(String(cue.assembly_window || "")) +
        " · " +
        esc(String(cue.as_of)) +
        (cue.note_ar ? "<br>" + esc(cue.note_ar) : "") +
        "</footer>";
    }

    html += "</section>";
    root.className = "ma-home-experience meif-home-root";
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    var loading = document.getElementById("ma-home-experience-loading");
    if (loading) loading.hidden = true;
    suppressSetupTheatre(home);
    publishRenderDiagnostics(summary, "home");
    return true;
  }

  function applyCarts(summary) {
    var pkg = meif(summary);
    if (!pkg || !pkg.pages || !pkg.pages.carts) return;
    var carts = pkg.pages.carts;
    var loading = document.getElementById("ma-carts-unified-loading");
    var banner = document.getElementById("meif-carts-truth-banner");
    var focus = document.getElementById("meif-carts-focus-root");
    var ops = carts.operational_truth || {};

    /* Constitution: operational list owns Carts — suppress duplicate MEIF executive banner. */
    if (banner) {
      banner.hidden = true;
      banner.innerHTML = "";
    }
    if (carts.forbid_please_wait && loading) {
      loading.hidden = true;
      loading.setAttribute("aria-busy", "false");
    }

    var header = document.querySelector("#page-carts .page-h1");
    var sub = document.querySelector("#page-carts .page-sub");
    if (header && ops.has_durable_carts) {
      header.textContent = "السلال";
    }
    if (sub && ops.has_durable_carts) {
      sub.textContent = "حالة كل سلة والإجراء التشغيلي التالي.";
    }

    if (focus && !focus.querySelector("[data-cs-surface='carts']")) {
      /* publication banner painted by commerce_situations_surfaces_v1 */
    }
  }

  function applyCommunication(summary) {
    /* Fallback only — commerce_situations_surfaces_v1 owns Communication facts. */
    var pkg = meif(summary);
    var root = document.getElementById("meif-communication-root");
    if (!root) return false;
    if (
      summary &&
      summary.merchant_publication_v1 &&
      summary.merchant_publication_v1.ok
    ) {
      return false;
    }
    var comm =
      pkg && pkg.pages && pkg.pages.communication
        ? pkg.pages.communication
        : {};
    var ops = comm.operational_truth || {};
    var pub =
      summary && summary.merchant_publication_v1
        ? summary.merchant_publication_v1
        : {};
    var cc =
      pub && pub.communication_condition && typeof pub.communication_condition === "object"
        ? pub.communication_condition
        : {};
    var sent = Number(ops.mock_whatsapp_sent || ops.whatsapp_sent || 0);
    var delivered = Number(ops.delivered_total || ops.whatsapp_delivered || 0);
    var replied = Number(ops.replied_total || ops.customer_replies || 0);
    var returned = Number(ops.returned_total || ops.recovery_success || 0);
    var noPhone = Number(ops.no_phone_total || ops.missing_phone || 0);
    if (!noPhone && summary && summary.home_teaser_inputs_v1) {
      var ht = summary.home_teaser_inputs_v1;
      noPhone = Number((ht.communication && ht.communication.no_phone) || 0);
    }
    var schedules = Number(ops.recovery_schedules || 0);
    var constrained = !!(cc.constrained || cc.normal_forbidden || noPhone > 0);
    var needsFollow = schedules > 0 || constrained;
    var statusAr =
      (cc.summary_ar || comm.status_message_ar || "").trim() ||
      (constrained
        ? "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل."
        : "تواصل العملاء يسير بشكل طبيعي.");

    var actions = [];
    if (noPhone > 0 || constrained) {
      actions.push(
        '<a href="#carts?tab=nophone">عرض العملاء بلا رقم ←</a>'
      );
    }
    if (schedules > 0) {
      actions.push('<a href="#carts?tab=waiting">عرض ما بانتظار الإرسال ←</a>');
    }
    actions.push('<a href="#messages">سجل الرسائل ←</a>');
    if (constrained) {
      actions.push('<a href="#whatsapp">ضبط التواصل ←</a>');
    }

    root.className = "meif-communication-root";
    root.innerHTML =
      '<section class="meif-surface meif-comms" data-meif="1" data-constitution="communication">' +
      "<h2>ماذا حدث في التواصل مع العملاء؟</h2>" +
      '<p class="meif-lede">' +
      esc(statusAr) +
      "</p>" +
      '<ul class="meif-facts meif-facts--3">' +
      "<li><strong>" +
      esc(String(sent)) +
      "</strong><span>تم الإرسال</span></li>" +
      "<li><strong>" +
      esc(String(delivered || "—")) +
      "</strong><span>تم التسليم</span></li>" +
      "<li><strong>" +
      esc(String(replied || "—")) +
      "</strong><span>تم الرد</span></li>" +
      "<li><strong>" +
      esc(String(returned || "—")) +
      "</strong><span>عاد العميل</span></li>" +
      "<li><strong>" +
      esc(String(noPhone)) +
      "</strong><span>لا يوجد رقم</span></li>" +
      "<li><strong>" +
      esc(needsFollow ? "نعم" : "لا") +
      "</strong><span>يحتاج متابعة</span></li>" +
      "</ul>" +
      '<p class="meif-next">' +
      actions.join(" · ") +
      "</p></section>";
    return true;
  }

  function applyDecision(summary) {
    /* Gate 2 — Cart Workspace is sole Decision Owner. MEIF Decision retired. */
    var root = document.getElementById("meif-decision-root");
    if (!root) return false;
    if (!window.CARTFLOW_DECISION_DUAL_STACK_V1) {
      root.innerHTML = "";
      root.hidden = true;
      return false;
    }
    var pkg = meif(summary);
    if (!pkg || !pkg.pages || !pkg.pages.decision_workspace) {
      return false;
    }
    var dw = pkg.pages.decision_workspace;
    var sections = dw.sections || {};
    var dFindings =
      sections.business_findings ||
      (sections.review_items || []).filter(function (it) {
        return it && (it.finding_id || it.bfl_binding);
      });
    var dBlock = renderFindingsBlock(
      dFindings,
      "decision_workspace",
      "لا استنتاجات تجارية تحتاج قراراً بعد."
    );
    root.hidden = false;
    root.innerHTML =
      '<section class="meif-surface meif-decision" data-meif="1" data-msr="1" data-mebf="1">' +
      '<p class="meif-eyebrow">مساحة القرار (مسار مزدوج — تراجع)</p>' +
      "<h2>لماذا يحدث هذا، وما القرار المطلوب؟</h2>" +
      '<p class="meif-lede">مسار تراجع فقط — المالك الدستوري هو Cart Workspace.</p>' +
      '<section class="meif-block meif-block--findings"><h3>استنتاجات تحتاج قراراً</h3>' +
      dBlock.html +
      "</section>" +
      '<p class="meif-next"><a href="#workspace">افتح مساحة القرار ←</a></p>' +
      "</section>";
    return true;
  }

  window.maApplyMerchantExperienceIntegrationV1 = function (summary) {
    if (!window.CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1) return false;
    var pkg = meif(summary);
    if (!pkg || !pkg.enabled) return false;
    var homeOk = applyHome(summary);
    applyCarts(summary);
    applyCommunication(summary);
    applyDecision(summary);
    return homeOk;
  };
})();
