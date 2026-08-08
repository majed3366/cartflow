/**
 * CartFlow Merchant UI V2 — Home executive commerce scene.
 * Truth → Meaning → Gravity → Decision. Visual language primitives.
 */
(function (global) {
  "use strict";

  function L() {
    return global.CartFlowUiV2Lang || null;
  }

  function esc(s) {
    return L() ? L().esc(s) : String(s == null ? "" : s);
  }

  function laneOf(sec) {
    var id = String((sec && sec.id) || "");
    if (id === "decisions") return "decision";
    if (id === "health") return "condition";
    if (id === "observations" || id === "situations") return "evidence";
    if (id === "carts") return "momentum";
    if (id === "communication") return "recovery";
    return "knowledge";
  }

  function split(sections) {
    var list = (sections || []).slice().sort(function (a, b) {
      return (
        parseInt((a && a.executive_rank) || 99, 10) -
        parseInt((b && b.executive_rank) || 99, 10)
      );
    });
    var primary = null;
    var i;
    for (i = 0; i < list.length; i++) {
      if (list[i] && (list[i].dominant || list[i].id === "decisions")) {
        primary = list[i];
        break;
      }
    }
    if (!primary && list.length) primary = list[0];
    var rest = list.filter(function (s) {
      return s && s !== primary;
    });
    var evidence = [];
    var secondary = [];
    rest.forEach(function (sec) {
      if (laneOf(sec) === "evidence" && evidence.length < 2) evidence.push(sec);
      else secondary.push(sec);
    });
    return { primary: primary, evidence: evidence, secondary: secondary };
  }

  function objectRow(kinds) {
    if (!L() || !kinds || !kinds.length) return "";
    var html = '<div class="cf2-co-row" data-cf2-grammar="commerce-objects">';
    kinds.forEach(function (k) {
      html += L().commerceObject(k);
    });
    html += "</div>";
    return html;
  }

  /** Momentum only from sections that exist — never invent a full fake journey. */
  function buildMomentum(parts, weak) {
    var all = []
      .concat(parts.primary ? [parts.primary] : [])
      .concat(parts.evidence || [])
      .concat(parts.secondary || []);
    var steps = [];
    var active = 0;
    var text = all
      .map(function (s) {
        return String(
          (s && (s.diagnosis_ar || s.summary_ar || s.recommendation_ar)) || ""
        );
      })
      .join(" ");
    if (/تردّد|تردد|hesitat/i.test(text)) steps.push("تردّد");
    if (all.some(function (s) {
      return laneOf(s) === "evidence" || laneOf(s) === "condition";
    })) {
      steps.push("دليل");
    }
    if (all.some(function (s) {
      return laneOf(s) === "decision";
    })) {
      steps.push("قرار");
    }
    if (all.some(function (s) {
      return laneOf(s) === "momentum";
    })) {
      steps.push("حركة");
    }
    if (all.some(function (s) {
      return laneOf(s) === "recovery";
    })) {
      steps.push("استرداد");
    }
    if (steps.length < 2) return { steps: [], active: 0 };
    if (weak) {
      active = Math.max(0, steps.indexOf("دليل"));
      if (active < 0) active = 0;
    } else if (steps.indexOf("قرار") >= 0) {
      active = steps.indexOf("قرار");
    } else {
      active = steps.length - 1;
    }
    return { steps: steps, active: active };
  }

  function capsule(sec) {
    if (!sec || !L()) return "";
    var diagnosis = String(sec.diagnosis_ar || sec.summary_ar || "").trim();
    var kinds = L().mapHomeObjects(sec).slice(0, 2);
    var html =
      '<article class="cf2-capsule" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-lane="' +
      esc(laneOf(sec)) +
      '">';
    html += objectRow(kinds);
    html +=
      '<p class="cf2-capsule__lane">' +
      esc(
        laneOf(sec) === "evidence"
          ? "دليل"
          : laneOf(sec) === "momentum"
            ? "حركة"
            : laneOf(sec) === "recovery"
              ? "استرداد"
              : laneOf(sec) === "condition"
                ? "حالة"
                : "معرفة"
      ) +
      "</p>";
    html +=
      '<h3 class="cf2-capsule__title">' + esc(sec.title_ar || "") + "</h3>";
    if (sec.status_ar) {
      html +=
        '<span class="cf2-badge">' + esc(sec.status_ar) + "</span>";
    }
    if (diagnosis) {
      html +=
        '<p class="cf2-capsule__body">' + esc(diagnosis) + "</p>";
    }
    html += "</article>";
    return html;
  }

  function render(pkg) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    if (!sections.length) {
      return (
        '<div class="cf2-scene"><p class="cf2-empty">' +
        esc(pkg.lede_ar || "لا تتوفر معرفة كافية الآن.") +
        "</p></div>"
      );
    }
    var parts = split(sections);
    var lang = L();
    var html =
      '<section class="cf2-scene" data-cf2="home-scene" data-cf2-grammar="attention-gravity">';

    html +=
      '<header class="cf2-scene__spine">' +
      '<p class="cf2-scene__kicker">مشهد تنفيذي</p>' +
      '<p class="cf2-scene__spine-line">الحالة · الدليل · المعنى · القرار</p>' +
      "</header>";

    if (parts.primary) {
      var p = parts.primary;
      var why = String(p.diagnosis_ar || p.summary_ar || "").trim();
      var meaning = String(p.recommendation_ar || "").trim();
      var href = String(p.view_details_href || "").trim();
      var kinds = lang ? lang.mapHomeObjects(p) : ["attention", "decision"];
      var weak =
        /أدلة|غير كافية|insufficient|لا يكفي|منخفض/i.test(why + meaning);
      var tension = weak ? "open" : "resolved";
      var evCount = parts.evidence.length + (why ? 2 : 1);

      html +=
        '<div class="cf2-scene__gravity" data-cf2-tension="' +
        esc(tension) +
        '">';
      html +=
        '<div class="cf2-scene__gravity-main">';
      html += objectRow(kinds);
      html += '<p class="cf2-scene__lane">مركز الجاذبية</p>';
      html +=
        '<h2 class="cf2-scene__title">' + esc(p.title_ar || "") + "</h2>";
      if (p.status_ar) {
        html +=
          '<div class="cf2-scene__meta"><span class="cf2-badge cf2-badge--info">' +
          esc(p.status_ar) +
          "</span></div>";
      }
      if (why) {
        html += '<p class="cf2-scene__why">' + esc(why) + "</p>";
      }
      if (meaning) {
        html +=
          '<p class="cf2-scene__meaning" data-cf2-grammar="understanding">' +
          esc(meaning) +
          "</p>";
      }
      if (lang) {
        var mom = buildMomentum(parts, weak);
        if (mom.steps.length >= 2) {
          html += lang.momentumTrace(mom.steps, mom.active);
        }
      }
      if (href) {
        html +=
          '<p class="cf2-scene__terminus"><a class="cf2-btn" href="' +
          esc(href) +
          '">عرض التفاصيل ←</a></p>';
      }
      html += "</div>";

      html +=
        '<aside class="cf2-scene__density cf2-evidence" data-cf2-grammar="evidence-density">';
      html += '<p class="cf2-scene__lane">كثافة الدليل</p>';
      if (lang) {
        html += lang.evidenceField(evCount, weak ? "sparse" : "mid");
      }
      parts.evidence.forEach(function (sec) {
        var d = String(sec.diagnosis_ar || sec.summary_ar || "").trim();
        html +=
          '<div class="cf2-scene__ev-item"><p class="cf2-scene__ev-title">' +
          esc(sec.title_ar || "") +
          "</p>";
        if (d) {
          html += '<p class="cf2-scene__ev-body">' + esc(d) + "</p>";
        }
        html += "</div>";
      });
      if (!parts.evidence.length) {
        html +=
          '<p class="cf2-scene__ev-body">الأدلة ما زالت مفتوحة — عدم اليقين حالة صادقة.</p>';
      }
      html += "</aside>";
      html += "</div>";
    }

    html += '<div class="cf2-silence" aria-hidden="true"></div>';

    if (parts.secondary.length) {
      html +=
        '<div class="cf2-scene__orbit" data-cf2-grammar="secondary" aria-label="معرفة ثانوية">';
      parts.secondary.forEach(function (sec) {
        html += capsule(sec);
      });
      html += "</div>";
    }

    html += '<hr class="cf2-taper" />';
    html += "</section>";
    return html;
  }

  function paint(root, summary) {
    if (!root) return false;
    var pkg =
      summary &&
      summary.home_executive_summary_v1 &&
      typeof summary.home_executive_summary_v1 === "object"
        ? summary.home_executive_summary_v1
        : null;
    if (!pkg || pkg.enabled === false) {
      root.innerHTML =
        '<p class="cf2-empty">تعذّر تحميل الملخص التنفيذي.</p>';
      return false;
    }
    root.innerHTML = render(pkg);
    return true;
  }

  async function loadAndPaint(root) {
    if (!root) return;
    root.innerHTML = '<p class="cf2-loading">جاري تحميل المشهد…</p>';
    try {
      var res = await fetch("/api/dashboard/summary", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("summary_http_" + res.status);
      paint(root, await res.json());
    } catch (e) {
      root.innerHTML =
        '<p class="cf2-error">تعذّر تحميل معرفة المتجر. أعد المحاولة.</p>';
    }
  }

  global.CartFlowUiV2Home = {
    loadAndPaint: loadAndPaint,
    paint: paint,
  };
})(typeof window !== "undefined" ? window : globalThis);
