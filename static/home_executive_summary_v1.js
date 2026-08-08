/**
 * Home Executive Summary — Merchant Experience Rebuild V1.
 * Product truth unchanged. Presentation rebuilt: Truth → Meaning → Priority → Decision → Action.
 * Not a stack of equal cards.
 */
(function () {
  "use strict";

  var HOME_QUESTION_AR = "ماذا يجب أن أعرف الآن عن متجري؟";

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function hideOrvSibling() {
    var orv = document.getElementById("observation-reality-validation-root");
    if (orv) {
      orv.innerHTML = "";
      orv.hidden = true;
    }
  }

  function gravityOf(sec) {
    if (!sec) return "quiet";
    if (sec.dominant || sec.id === "decisions") return "primary";
    var rank = Number(sec.executive_rank || 99);
    if (rank <= 2) return "secondary";
    if (rank <= 3) return "tertiary";
    return "quiet";
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

  function momentumOf(sec) {
    if (!sec || sec.empty) return "calm";
    if (sec.recommendation_ar || sec.view_details_href) return "forward";
    return "forming";
  }

  function diagnosisText(sec) {
    return String(
      (sec && (sec.diagnosis_ar || sec.summary_ar)) || ""
    ).trim();
  }

  function recommendationText(sec) {
    return String((sec && sec.recommendation_ar) || "").trim();
  }

  function renderInsight(sec, role) {
    if (!sec) return "";
    var gravity = gravityOf(sec);
    var lane = laneOf(sec);
    var momentum = momentumOf(sec);
    var rank = Number(sec.executive_rank || 0) || 9;
    var diagnosis = diagnosisText(sec);
    var recommendation = recommendationText(sec);
    var status = String(sec.status_ar || "").trim();
    var href = String(sec.view_details_href || "").trim() || "#";
    var empty = !!sec.empty;
    var note = "";
    if (sec.id === "carts" && sec.cart_level_action_ar && !empty) {
      var cartNote = String(sec.cart_level_action_ar || "").trim();
      if (cartNote && cartNote !== recommendation) note = cartNote;
    }

    var roleClass =
      role === "primary"
        ? " cx-insight--primary"
        : role === "secondary"
          ? " cx-insight--secondary"
          : " cx-insight--quiet";

    var html =
      '<article class="cx-insight' +
      roleClass +
      (empty ? " cx-insight--empty" : "") +
      '" data-hes-section="' +
      esc(sec.id || "") +
      '"' +
      (sec.dominant || sec.id === "decisions" ? ' data-hes-dominant="1"' : "") +
      (sec.executive_rank
        ? ' data-hes-rank="' + esc(String(sec.executive_rank)) + '"'
        : "") +
      ' data-cf-sig="home-section"' +
      ' data-cf-gravity="' +
      esc(gravity) +
      '"' +
      ' data-cf-rank="' +
      esc(String(rank)) +
      '"' +
      ' data-cf-momentum="' +
      esc(momentum) +
      '"' +
      ' data-cf-lane="' +
      esc(lane) +
      '"' +
      ' data-cf-has-decision="' +
      (sec.id === "decisions" || sec.dominant ? "1" : "0") +
      '"' +
      ' data-diagnosis="home_diagnosis_language_v1"' +
      ' data-cx-role="' +
      esc(role) +
      '">';

    html += '<header class="cx-insight__head">';
    html +=
      '<p class="cx-insight__lane">' +
      esc(
        lane === "decision"
          ? "القرار"
          : lane === "condition"
            ? "الحالة"
            : lane === "evidence"
              ? "الدليل"
              : lane === "momentum"
                ? "الحركة"
                : lane === "recovery"
                  ? "الاسترداد"
                  : "معرفة"
      ) +
      "</p>";
    html += "<h3 class=\"cx-insight__title\">" + esc(sec.title_ar || "") + "</h3>";
    if (status) {
      html +=
        '<span class="cx-insight__status cf-badge" data-hes-status="1">' +
        esc(status) +
        "</span>";
    }
    html += "</header>";

    if (diagnosis) {
      html +=
        '<p class="cx-insight__diagnosis" data-hes-diagnosis="1">' +
        esc(diagnosis) +
        "</p>";
    } else if (!recommendation) {
      html +=
        '<p class="cx-insight__summary" data-hes-summary="1">' +
        esc(sec.summary_ar || "") +
        "</p>";
    }

    if (recommendation) {
      html +=
        '<p class="cx-insight__meaning" data-hes-recommendation="1">' +
        esc(recommendation) +
        "</p>";
    }

    if (note) {
      html += '<p class="cx-insight__note">' + esc(note) + "</p>";
    }

    if (!empty) {
      html +=
        '<p class="cx-insight__action"><a class="cf-btn cf-btn--quiet" href="' +
        esc(href) +
        '" data-hes-view-details="' +
        esc(sec.id || "") +
        '">عرض التفاصيل ←</a></p>';
    }

    html += "</article>";
    return html;
  }

  function splitComposition(sections) {
    var list = (sections || []).slice().sort(function (a, b) {
      var ra = parseInt((a && a.executive_rank) || 99, 10);
      var rb = parseInt((b && b.executive_rank) || 99, 10);
      return ra - rb;
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
    var condition = null;
    for (i = 0; i < rest.length; i++) {
      if (rest[i].id === "health") {
        condition = rest[i];
        break;
      }
    }
    rest = rest.filter(function (s) {
      return s !== condition;
    });

    var evidence = [];
    var secondary = [];
    rest.forEach(function (sec) {
      if (laneOf(sec) === "evidence" && evidence.length < 2) {
        evidence.push(sec);
      } else {
        secondary.push(sec);
      }
    });

    return {
      primary: primary,
      condition: condition,
      evidence: evidence,
      secondary: secondary,
    };
  }

  function paintShell(root, pkg) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    var errLede =
      pkg.error || (!sections.length && pkg.lede_ar)
        ? String(pkg.lede_ar || "تعذّر تحميل الملخص — أعد المحاولة.")
        : "";

    var html =
      '<section class="cx-home" data-hes="1" data-hes-stabilization="1" data-executive-control="1" data-constitution="home_constitution_v2" data-diagnosis-language="home_diagnosis_language_v1" data-cx="home" data-cf-sig="home" aria-label="' +
      esc(pkg.title_ar || HOME_QUESTION_AR) +
      '">';

    if (errLede && !sections.length) {
      html +=
        '<p class="cx-home__empty cf-empty" data-hes-attach-empty="1">' +
        esc(errLede) +
        "</p>";
    } else {
      var parts = splitComposition(sections);
      var hasPrimary = !!parts.primary;
      var openCount =
        (parts.primary ? 1 : 0) +
        (parts.condition ? 1 : 0) +
        parts.evidence.length +
        parts.secondary.length;

      html +=
        '<div class="cx-home__spine" data-cf-grammar="attention">' +
        '<p class="cx-home__spine-kicker">فهم تنفيذي</p>' +
        '<p class="cx-home__spine-line">أوضح حقيقة الآن · ثم المعنى · ثم القرار</p>' +
        "</div>";

      html +=
        '<div class="cx-home__field" data-cf-open-count="' +
        esc(String(openCount)) +
        '" data-cf-breathing="' +
        (hasPrimary ? "focused" : "open") +
        '">';

      if (parts.condition) {
        html +=
          '<div class="cx-home__condition" data-cf-grammar="attention">' +
          renderInsight(parts.condition, "secondary") +
          "</div>";
      }

      html += '<div class="cx-home__core">';
      if (parts.primary) {
        html +=
          '<div class="cx-home__decision cf-decision-surface" data-cf-grammar="decision-mass">' +
          renderInsight(parts.primary, "primary") +
          "</div>";
      }
      if (parts.evidence.length) {
        html +=
          '<div class="cx-home__evidence cf-evidence-surface" data-cf-grammar="evidence" data-cf-evidence-density="' +
          (parts.evidence.length > 1 ? "high" : "mid") +
          '">';
        parts.evidence.forEach(function (sec) {
          html += renderInsight(sec, "secondary");
        });
        html += "</div>";
      }
      html += "</div>";

      html += '<div class="cf-grammar-silence" data-cf-grammar="silence" aria-hidden="true"></div>';

      if (parts.secondary.length) {
        html +=
          '<div class="cx-home__secondary" data-cf-grammar="taper" aria-label="معرفة ثانوية">';
        parts.secondary.forEach(function (sec) {
          html += renderInsight(sec, "quiet");
        });
        html += "</div>";
      }

      html += '<div class="cf-grammar-taper" aria-hidden="true"></div>';
      html += "</div>";
    }

    html += "</section>";

    root.className = "ma-home-experience cx-home-root";
    root.setAttribute("data-cx", "home-root");
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    var loading = document.getElementById("ma-home-experience-loading");
    if (loading) loading.hidden = true;
    hideOrvSibling();
  }

  window.maApplyHomeExecutiveSummaryV1 = function (summary) {
    var root =
      document.getElementById("ma-home-experience-root") ||
      document.getElementById("home-executive-summary-root");
    if (!root) return false;
    var pkg =
      summary &&
      summary.home_executive_summary_v1 &&
      typeof summary.home_executive_summary_v1 === "object"
        ? summary.home_executive_summary_v1
        : null;
    if (!pkg || pkg.enabled === false) return false;
    try {
      paintShell(root, pkg);
      return true;
    } catch (e) {
      return false;
    }
  };
})();
