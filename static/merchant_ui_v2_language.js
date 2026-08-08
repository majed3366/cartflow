/**
 * CartFlow Merchant UI V2 — Visual Language Maturity V1 helpers.
 * Presentation only. Canonical object + evidence + tension mapping.
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
    "ev-sparse": "دليل متناثر",
    "ev-gathering": "تجميع دليل",
    "ev-aligned": "دليل متوافق",
    "ev-converging": "تكثيف دليل",
    evidence: "دليل",
    convergence: "تكثيف",
    insufficient: "أدلة ناقصة",
    uncertainty: "عدم يقين",
    meaning: "معنى يتشكّل",
    "decision-forming": "قرار يتشكّل",
    "decision-ready": "قرار جاهز",
    decision: "قرار",
    hesitation: "تردّد",
    waiting: "انتظار",
    recovery: "استرداد",
    "recovery-opportunity": "فرصة استرداد",
    "recovery-continue": "استمرار استرداد",
    "return": "عودة",
    momentum: "زخم",
    movement: "حركة",
    complete: "اكتمال",
    blocked: "توقّف",
  };

  /** Normalize legacy aliases → canonical kinds */
  function canonicalKind(kind) {
    var k = String(kind || "evidence");
    if (k === "evidence") return "ev-sparse";
    if (k === "convergence") return "ev-converging";
    if (k === "decision") return "decision-ready";
    return k;
  }

  function commerceObject(kind, label) {
    var raw = String(kind || "evidence");
    var k = canonicalKind(raw);
    var lab = label || CO_LABELS[raw] || CO_LABELS[k] || k;
    return (
      '<span class="cf2-co cf2-co--' +
      esc(k) +
      (raw !== k ? " cf2-co--" + esc(raw) : "") +
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

  function densityFromCount(n, opts) {
    opts = opts || {};
    if (opts.insufficient) return "insufficient";
    if (opts.mixed) return "mixed";
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
          : d === "mixed"
            ? [80, 44, 70, 36]
            : d === "insufficient"
              ? [36, 22, 14]
              : d === "sparse"
                ? [48, 32, 20]
                : [72, 60, 48, 36];
    var html =
      '<div class="cf2-evfield" data-cf2-density="' +
      esc(d) +
      '" data-cf2-evidence-n="' +
      esc(String(n)) +
      '" aria-hidden="true">';
    var countBars =
      d === "sparse" || d === "insufficient"
        ? Math.min(n + 1, widths.length)
        : Math.min(Math.max(n, 2), widths.length);
    for (var i = 0; i < countBars; i++) {
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
    var html =
      '<div class="cf2-mtrace" data-cf2-grammar="momentum" data-cf2-motion="continue">';
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
    var text = diag + rec;
    var weak = /أدلة|غير كافية|insufficient|لا يكفي|منخفض/i.test(text) || empty;
    var objs = [];
    if (id === "decisions") {
      objs.push("attention");
      if (weak) {
        objs.push("insufficient");
        objs.push("uncertainty");
      } else {
        objs.push("ev-converging");
        objs.push("decision-ready");
      }
    } else if (id === "observations" || id === "situations") {
      if (weak) objs.push("ev-sparse");
      else objs.push("ev-gathering");
      if (/تردّد|تردد|hesitat/i.test(diag)) objs.push("hesitation");
      else objs.push("meaning");
    } else if (id === "carts") {
      objs.push("momentum");
      objs.push("movement");
    } else if (id === "communication") {
      if (/ناقص|غير|لا يوجد/i.test(diag)) {
        objs.push("recovery-opportunity");
        objs.push("blocked");
      } else {
        objs.push("recovery-continue");
        objs.push("return");
      }
    } else if (id === "health") {
      objs.push("attention");
      if (/يتطلب|متابعة|ناقص/i.test(String(sec.status_ar || "") + diag)) {
        objs.push("hesitation");
        objs.push("waiting");
      } else {
        objs.push("complete");
      }
    } else {
      objs.push("ev-sparse");
    }
    return objs;
  }

  function tensionFromCard(card) {
    var ready = String((card && card.execution_readiness) || "");
    if (ready === "NEEDS_MORE_EVIDENCE") return "open";
    if (ready === "BLOCKED") return "high";
    if (ready === "EXTERNAL_DEPENDENCY") return "waiting";
    if (
      ready === "READY" ||
      (card && card.execution_available === true)
    ) {
      return "ready";
    }
    var conf = String(
      (card && (card.confidence || card.confidence_ar)) || ""
    ).toLowerCase();
    if (conf.indexOf("low") >= 0 || conf.indexOf("منخفض") >= 0) return "open";
    if (conf.indexOf("high") >= 0 || conf.indexOf("مرتفع") >= 0) return "ready";
    return "forming";
  }

  function mapWorkspaceObjects(card) {
    var tension = tensionFromCard(card);
    var objs = [];
    if (tension === "open") {
      objs = ["ev-sparse", "insufficient", "uncertainty"];
    } else if (tension === "high") {
      objs = ["ev-gathering", "hesitation", "blocked"];
    } else if (tension === "waiting") {
      objs = ["meaning", "waiting", "recovery-opportunity"];
    } else if (tension === "ready" || tension === "resolved") {
      objs = ["ev-converging", "decision-ready", "recovery-continue"];
    } else {
      objs = ["ev-aligned", "meaning", "decision-forming"];
    }
    return objs;
  }

  global.CartFlowUiV2Lang = {
    esc: esc,
    commerceObject: commerceObject,
    canonicalKind: canonicalKind,
    evidenceField: evidenceField,
    densityFromCount: densityFromCount,
    momentumTrace: momentumTrace,
    mapHomeObjects: mapHomeObjects,
    mapWorkspaceObjects: mapWorkspaceObjects,
    tensionFromCard: tensionFromCard,
    CO_LABELS: CO_LABELS,
  };
})(typeof window !== "undefined" ? window : globalThis);
