/**
 * CartFlow Merchant UI V2 — Final Home product composition.
 * Merchant meaning first. Frozen visual grammar second (sparing).
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

  function isWeakText(text) {
    return /أدلة|غير كافية|insufficient|لا يكفي|منخفض|محدود/i.test(
      String(text || "")
    );
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
    var know = [];
    var watch = [];
    var learning = [];
    rest.forEach(function (sec) {
      var lane = laneOf(sec);
      var diag = String(sec.diagnosis_ar || sec.summary_ar || "");
      var status = String(sec.status_ar || "");
      if (lane === "condition" || /يتطلب|متابعة|عاجل/i.test(status + diag)) {
        know.push(sec);
      } else if (lane === "evidence" || isWeakText(diag) || sec.empty) {
        learning.push(sec);
      } else {
        watch.push(sec);
      }
    });
    return {
      primary: primary,
      know: know.slice(0, 2),
      watch: watch.slice(0, 2),
      learning: learning.slice(0, 2),
    };
  }

  function confidenceCopy(weak, density) {
    if (weak || density === "insufficient" || density === "sparse") {
      return "الأدلة ما زالت محدودة";
    }
    if (density === "gathering") return "بدأت الإشارة تتكرر";
    if (density === "aligned" || density === "mixed") {
      return "الأدلة أصبحت أكثر اتساقًا";
    }
    if (density === "converging") return "توجد أدلة كافية لاتخاذ قرار";
    return "الأدلة ما زالت محدودة";
  }

  function actionCopy(weak, meaning) {
    if (weak) {
      return "لا يلزم تغيير تجاري الآن — واصل المراقبة حتى تتضح الإشارة.";
    }
    if (meaning) return meaning;
    return "راجع التفاصيل عندما تكون جاهزًا لاتخاذ قرار.";
  }

  /** One dominant object only — no gallery. Label hidden (grammar silent). */
  function primaryMark(weak, lane) {
    if (!L()) return "";
    var kind = "attention";
    if (!weak && lane === "decision") kind = "decision-ready";
    else if (!weak && lane === "recovery") kind = "recovery-continue";
    else if (weak) kind = "attention";
    return (
      '<div class="cf2-home__mark" aria-hidden="true">' +
      L().commerceObject(kind, " ") +
      "</div>"
    );
  }

  function secondaryItem(sec, tier) {
    var diagnosis = String(sec.diagnosis_ar || sec.summary_ar || "").trim();
    var html =
      '<article class="cf2-home__item" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-tier="' +
      esc(tier) +
      '">';
    html +=
      '<p class="cf2-home__tier">' +
      esc(
        tier === "know"
          ? "اعرف الآن"
          : tier === "watch"
            ? "راقب"
            : "ما زال يتعلّم"
      ) +
      "</p>";
    html +=
      '<h3 class="cf2-home__item-title">' + esc(sec.title_ar || "") + "</h3>";
    if (diagnosis) {
      html +=
        '<p class="cf2-home__item-body">' + esc(diagnosis) + "</p>";
    }
    html += "</article>";
    return html;
  }

  function render(pkg) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    if (!sections.length) {
      return (
        '<div class="cf2-home"><p class="cf2-empty">' +
        esc(pkg.lede_ar || "لا تتوفر معرفة كافية الآن.") +
        "</p></div>"
      );
    }
    var parts = split(sections);
    var lang = L();
    var html = '<section class="cf2-home" data-cf2="home-final">';

    if (parts.primary) {
      var p = parts.primary;
      var why = String(p.diagnosis_ar || p.summary_ar || "").trim();
      var meaning = String(p.recommendation_ar || "").trim();
      var href = String(p.view_details_href || "").trim();
      var weak = isWeakText(why + meaning) || !!p.empty;
      var tension = weak ? "open" : "resolved";
      var evCount = why ? 2 : 1;
      if (parts.learning.length) evCount += 1;
      if (parts.know.length) evCount += 1;
      var density = weak
        ? "insufficient"
        : lang
          ? lang.densityFromCount(evCount)
          : "gathering";
      var confidence = confidenceCopy(weak, density);
      var action = actionCopy(weak, meaning);

      html +=
        '<div class="cf2-home__primary" data-cf2-tension="' +
        esc(tension) +
        '">';
      html += '<div class="cf2-home__primary-main">';
      html += primaryMark(weak, laneOf(p));
      html +=
        '<p class="cf2-home__eyebrow">الأهم الآن</p>';
      html +=
        '<h2 class="cf2-home__title">' + esc(p.title_ar || "") + "</h2>";
      if (why) {
        html += '<p class="cf2-home__why">' + esc(why) + "</p>";
      }
      html +=
        '<p class="cf2-home__confidence" data-cf2-density="' +
        esc(density) +
        '">' +
        esc(confidence) +
        "</p>";
      if (lang) {
        html +=
          '<div class="cf2-home__field" aria-hidden="true">' +
          lang.evidenceField(evCount, density) +
          "</div>";
      }
      html +=
        '<div class="cf2-home__stance"><p class="cf2-home__stance-label">ماذا تفعل؟</p><p class="cf2-home__stance-body">' +
        esc(action) +
        "</p></div>";
      if (href) {
        html +=
          '<div class="cf2-home__action cf2-terminus"><a class="cf2-btn" href="' +
          esc(href) +
          '">' +
          esc(weak ? "راجع التفاصيل" : "افتح القرار") +
          "</a></div>";
      }
      html += "</div>";

      /* Supporting facts from related sections — merchant text only */
      var support = parts.learning.concat(parts.know).slice(0, 2);
      if (support.length) {
        html +=
          '<aside class="cf2-home__support" aria-label="ما يدعم هذا الحكم">';
        html += '<p class="cf2-home__support-label">لماذا يقول CartFlow ذلك؟</p>';
        support.forEach(function (sec) {
          var d = String(sec.diagnosis_ar || sec.summary_ar || "").trim();
          if (!d && !sec.title_ar) return;
          html += '<div class="cf2-home__support-item">';
          if (sec.title_ar) {
            html +=
              '<p class="cf2-home__support-title">' +
              esc(sec.title_ar) +
              "</p>";
          }
          if (d) {
            html +=
              '<p class="cf2-home__support-body">' + esc(d) + "</p>";
          }
          html += "</div>";
        });
        html += "</aside>";
      }
      html += "</div>";
    }

    var secondary =
      parts.know.length || parts.watch.length || parts.learning.length;
    if (secondary) {
      html +=
        '<div class="cf2-home__secondary" aria-label="معرفة إضافية">';
      if (parts.know.length) {
        html += '<div class="cf2-home__band" data-cf2-band="know">';
        parts.know.forEach(function (sec) {
          html += secondaryItem(sec, "know");
        });
        html += "</div>";
      }
      if (parts.watch.length) {
        html += '<div class="cf2-home__band" data-cf2-band="watch">';
        parts.watch.forEach(function (sec) {
          html += secondaryItem(sec, "watch");
        });
        html += "</div>";
      }
      if (parts.learning.length) {
        html += '<div class="cf2-home__band" data-cf2-band="learning">';
        parts.learning.forEach(function (sec) {
          /* skip if already used as primary support only once — still ok to show quieter */
          html += secondaryItem(sec, "learning");
        });
        html += "</div>";
      }
      html += "</div>";
    }

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
        '<p class="cf2-empty">تعذّر تحميل معرفة المتجر.</p>';
      return false;
    }
    root.innerHTML = render(pkg);
    return true;
  }

  async function loadAndPaint(root) {
    if (!root) return;
    root.innerHTML = '<p class="cf2-loading">جاري تحميل معرفة متجرك…</p>';
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
