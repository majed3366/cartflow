/**
 * CartFlow Merchant UI V2 — Visual Language helpers (presentation only).
 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var CO_LABELS = {
    attention: "انتباه",
    decision: "قرار",
    evidence: "دليل",
    convergence: "تكثيف",
    uncertainty: "عدم يقين",
    insufficient: "أدلة ناقصة",
    hesitation: "تردّد",
    momentum: "زخم",
    movement: "حركة",
    recovery: "استرداد",
    blocked: "توقّف",
  };

  function commerceObject(kind, label) {
    var k = String(kind || "evidence");
    var lab = label || CO_LABELS[k] || k;
    return (
      '<span class="cf2-co cf2-co--' +
      esc(k) +
      '" data-cf2-co="' +
      esc(k) +
      '" title="' +
      esc(lab) +
      '">' +
      '<span class="cf2-co__glyph" aria-hidden="true"></span>' +
      '<span class="cf2-co__label">' +
      esc(lab) +
      "</span></span>"
    );
  }

  function densityFromCount(n) {
    if (n >= 4) return "converging";
    if (n >= 3) return "aligned";
    if (n <= 1) return "sparse";
    return "gathering";
  }

  function evidenceField(count, density) {
    var n = Math.max(1, Math.min(5, Number(count) || 1));
    var d = density || densityFromCount(n);
    if (d === "mid") d = "gathering";
    if (d === "dense") d = "converging";
    var widths =
      d === "converging"
        ? [98, 92, 86, 78, 70]
        : d === "aligned"
          ? [88, 80, 72, 62]
          : d === "sparse"
            ? [48, 32, 20]
            : [72, 60, 48, 36];
    var html =
      '<div class="cf2-evfield" data-cf2-density="' +
      esc(d) +
      '" data-cf2-evidence-n="' +
      esc(String(n)) +
      '" aria-hidden="true">';
    for (var i = 0; i < Math.min(n + (d === "sparse" ? 1 : 0), widths.length); i++) {
      html +=
        '<span class="cf2-evfield__bar" style="width:' +
        widths[i] +
        '%"></span>';
    }
    html += "</div>";
    return html;
  }

  function momentumTrace(steps, activeIdx) {
    if (!steps || !steps.length) return "";
    var html = '<div class="cf2-mtrace" data-cf2-grammar="momentum">';
    steps.forEach(function (step, i) {
      if (i) html += '<span class="cf2-mtrace__arrow" aria-hidden="true"></span>';
      html +=
        '<span class="cf2-mtrace__step' +
        (i === activeIdx ? " is-active" : "") +
        '">' +
        esc(step) +
        "</span>";
    });
    html += "</div>";
    return html;
  }

  function mapHomeObjects(sec) {
    var id = String((sec && sec.id) || "");
    var empty = !!(sec && sec.empty);
    var rec = String((sec && sec.recommendation_ar) || "");
    var diag = String((sec && (sec.diagnosis_ar || sec.summary_ar)) || "");
    var objs = [];
    if (id === "decisions") {
      objs.push("attention");
      if (/أدلة|غير كافية|insufficient|لا يكفي/i.test(diag + rec) || empty) {
        objs.push("insufficient");
        objs.push("uncertainty");
      } else {
        objs.push("convergence");
        objs.push("decision");
      }
    } else if (id === "observations" || id === "situations") {
      objs.push("evidence");
      if (/تردّد|تردد|hesitat/i.test(diag)) objs.push("hesitation");
      else objs.push("convergence");
    } else if (id === "carts") {
      objs.push("momentum");
      objs.push("movement");
    } else if (id === "communication") {
      objs.push("recovery");
      if (/ناقص|غير|لا يوجد/i.test(diag)) objs.push("blocked");
    } else if (id === "health") {
      objs.push("attention");
      if (/يتطلب|متابعة|ناقص/i.test(String(sec.status_ar || "") + diag)) {
        objs.push("hesitation");
      }
    } else {
      objs.push("evidence");
    }
    return objs;
  }

  function tensionFromCard(card) {
    var ready = String((card && card.execution_readiness) || "");
    if (ready === "NEEDS_MORE_EVIDENCE" || ready === "BLOCKED") return "high";
    if (ready === "EXTERNAL_DEPENDENCY") return "open";
    if (
      ready === "READY" ||
      (card && card.execution_available === true)
    ) {
      return "resolved";
    }
    var conf = String(
      (card && (card.confidence || card.confidence_ar)) || ""
    ).toLowerCase();
    if (conf.indexOf("low") >= 0 || conf.indexOf("منخفض") >= 0) return "open";
    if (conf.indexOf("high") >= 0 || conf.indexOf("مرتفع") >= 0) return "resolved";
    return "low";
  }

  global.CartFlowUiV2Lang = {
    esc: esc,
    commerceObject: commerceObject,
    evidenceField: evidenceField,
    densityFromCount: densityFromCount,
    momentumTrace: momentumTrace,
    mapHomeObjects: mapHomeObjects,
    tensionFromCard: tensionFromCard,
    CO_LABELS: CO_LABELS,
  };
})(typeof window !== "undefined" ? window : globalThis);
