/**
 * CartFlow Merchant UI V2 — Home painter.
 * Consumes GET /api/dashboard/summary → home_executive_summary_v1.
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
    var ops = [];
    rest.forEach(function (sec) {
      var lane = laneOf(sec);
      if (lane === "evidence" && evidence.length < 2) evidence.push(sec);
      else if (sec.id === "health" && !primary) secondary.push(sec);
      else secondary.push(sec);
    });
    return { primary: primary, evidence: evidence, secondary: secondary, ops: ops };
  }

  function blockHtml(sec, quiet) {
    if (!sec) return "";
    var diagnosis = String(sec.diagnosis_ar || sec.summary_ar || "").trim();
    var meaning = String(sec.recommendation_ar || "").trim();
    var status = String(sec.status_ar || "").trim();
    var href = String(sec.view_details_href || "").trim();
    var html =
      '<article class="cf2-home__block cf2-knowledge" data-hes-section="' +
      esc(sec.id || "") +
      '">';
    html +=
      '<p class="cf2-home__lane">' +
      esc(
        laneOf(sec) === "evidence"
          ? "الدليل"
          : laneOf(sec) === "momentum"
            ? "الحركة"
            : laneOf(sec) === "recovery"
              ? "الاسترداد"
              : laneOf(sec) === "condition"
                ? "الحالة"
                : "معرفة"
      ) +
      "</p>";
    html +=
      '<h3 class="cf2-home__block-title">' + esc(sec.title_ar || "") + "</h3>";
    if (status) {
      html +=
        '<div class="cf2-home__meta"><span class="cf2-badge">' +
        esc(status) +
        "</span></div>";
    }
    if (diagnosis) {
      html +=
        '<p class="cf2-home__block-body">' + esc(diagnosis) + "</p>";
    }
    if (meaning) {
      html +=
        '<p class="cf2-home__block-body" style="margin-top:8px">' +
        esc(meaning) +
        "</p>";
    }
    if (href && !quiet) {
      html +=
        '<p class="cf2-home__action"><a class="cf2-btn cf2-btn--quiet" href="' +
        esc(href) +
        '">عرض التفاصيل ←</a></p>';
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
    var html = '<section class="cf2-home" data-cf2="home">';
    html +=
      '<div class="cf2-home__spine">' +
      '<p class="cf2-home__kicker">فهم تنفيذي</p>' +
      '<p class="cf2-home__spine-line">أوضح حقيقة الآن · ثم المعنى · ثم القرار</p>' +
      "</div>";

    if (parts.primary) {
      var p = parts.primary;
      var why = String(p.diagnosis_ar || p.summary_ar || "").trim();
      var meaning = String(p.recommendation_ar || "").trim();
      var status = String(p.status_ar || "").trim();
      var href = String(p.view_details_href || "").trim();
      html +=
        '<div class="cf2-home__dominant cf2-decision" data-cf2-gravity="primary" data-hes-section="' +
        esc(p.id || "") +
        '">';
      html += '<p class="cf2-home__lane">القرار</p>';
      html +=
        '<h2 class="cf2-home__title">' + esc(p.title_ar || "") + "</h2>";
      if (status) {
        html +=
          '<div class="cf2-home__meta"><span class="cf2-badge cf2-badge--info">' +
          esc(status) +
          "</span></div>";
      }
      if (why) {
        html += '<p class="cf2-home__why">' + esc(why) + "</p>";
      }
      if (meaning) {
        html += '<p class="cf2-home__meaning">' + esc(meaning) + "</p>";
      }
      if (href) {
        html +=
          '<p class="cf2-home__action"><a class="cf2-btn" href="' +
          esc(href) +
          '">عرض التفاصيل ←</a></p>';
      }
      html += "</div>";
    }

    html += '<div class="cf2-home__grid">';
    html += '<div class="cf2-home__evidence cf2-evidence">';
    if (parts.evidence.length) {
      parts.evidence.forEach(function (sec) {
        html += blockHtml(sec, false);
      });
    } else {
      html +=
        '<p class="cf2-empty" style="padding:8px 0">الأدلة غير كافية لتكثيف أقوى — نتابع بشفافية.</p>';
    }
    html += "</div>";
    html += '<div class="cf2-home__secondary">';
    parts.secondary.forEach(function (sec) {
      html += blockHtml(sec, true);
    });
    html += "</div></div>";

    html += '<hr class="cf2-divider" />';
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
    root.innerHTML = '<p class="cf2-loading">جاري تحميل الملخص…</p>';
    try {
      var res = await fetch("/api/dashboard/summary", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("summary_http_" + res.status);
      var data = await res.json();
      paint(root, data);
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
