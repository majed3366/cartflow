/**
 * CartFlow Merchant UI V2 — Final Home product composition V1.1
 * Merchant meaning first. Frozen visual grammar second (sparing).
 * Desktop: one executive composition — no duplicated truths.
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

  function truthText(sec) {
    return String(
      (sec && (sec.diagnosis_ar || sec.summary_ar || sec.recommendation_ar)) || ""
    )
      .replace(/\s+/g, " ")
      .trim();
  }

  /** Same commercial diagnosis in different clothing — drop it. */
  function isDuplicateTruth(primaryText, secText) {
    var a = String(primaryText || "")
      .replace(/\s+/g, " ")
      .trim();
    var b = String(secText || "")
      .replace(/\s+/g, " ")
      .trim();
    if (!a || !b) return false;
    if (a === b) return true;
    var short = a.length <= b.length ? a : b;
    var long = a.length <= b.length ? b : a;
    if (short.length < 28) return false;
    var needle = short.slice(0, Math.min(56, short.length));
    return long.indexOf(needle) !== -1;
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
    var primaryTruth = truthText(primary);
    var rest = list.filter(function (s) {
      return s && s !== primary && !isDuplicateTruth(primaryTruth, truthText(s));
    });
    var know = [];
    var watch = [];
    var learning = [];
    rest.forEach(function (sec) {
      var lane = laneOf(sec);
      var diag = truthText(sec);
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

  function tierLabel(tier) {
    if (tier === "know") return "اعرف الآن";
    if (tier === "watch") return "راقب";
    return "ما زال يتعلّم";
  }

  function railItem(sec, tier) {
    var diagnosis = truthText(sec);
    var html =
      '<article class="cf2-home__rail-item" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-tier="' +
      esc(tier) +
      '">';
    html +=
      '<p class="cf2-home__tier">' + esc(tierLabel(tier)) + "</p>";
    html +=
      '<h3 class="cf2-home__rail-title">' + esc(sec.title_ar || "") + "</h3>";
    if (diagnosis) {
      html +=
        '<p class="cf2-home__rail-body">' + esc(diagnosis) + "</p>";
    }
    html += "</article>";
    return html;
  }

  function floorItem(sec, tier) {
    var diagnosis = truthText(sec);
    var html =
      '<article class="cf2-home__item" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-tier="' +
      esc(tier) +
      '">';
    html +=
      '<p class="cf2-home__tier">' + esc(tierLabel(tier)) + "</p>";
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
    var html =
      '<section class="cf2-home" data-cf2="home-final-v11">';

    if (!parts.primary) {
      html += "</section>";
      return html;
    }

    var p = parts.primary;
    var why = truthText(p);
    var meaning = String(p.recommendation_ar || "").trim();
    var href = String(p.view_details_href || "").trim();
    var weak = isWeakText(why + meaning) || !!p.empty;
    var tension = weak ? "open" : "resolved";
    var distinctCount = parts.know.length + parts.watch.length + parts.learning.length;
    var evCount = why ? 2 : 1;
    if (distinctCount) evCount += 1;
    var density = weak
      ? "insufficient"
      : lang
        ? lang.densityFromCount(evCount)
        : "gathering";
    var confidence = confidenceCopy(weak, density);
    var action = actionCopy(weak, meaning);

    /* Rail: distinct truths only — prefer operational KNOW, then WATCH, then LEARNING */
    var rail = [];
    parts.know.forEach(function (sec) {
      rail.push({ sec: sec, tier: "know" });
    });
    parts.watch.forEach(function (sec) {
      rail.push({ sec: sec, tier: "watch" });
    });
    parts.learning.forEach(function (sec) {
      rail.push({ sec: sec, tier: "learning" });
    });
    rail = rail.slice(0, 3);
    var railIds = {};
    rail.forEach(function (r) {
      if (r.sec && r.sec.id) railIds[r.sec.id] = true;
    });

    html +=
      '<div class="cf2-home__board" data-cf2-tension="' +
      esc(tension) +
      '" data-cf2-rail="' +
      (rail.length ? "on" : "empty") +
      '">';

    html += '<div class="cf2-home__primary">';
    html += primaryMark(weak, laneOf(p));
    html += '<p class="cf2-home__eyebrow">الأهم الآن</p>';
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
    html += '<div class="cf2-home__stance">';
    html +=
      '<p class="cf2-home__stance-label">' +
      esc(weak ? "الوضع الآن" : "ماذا تفعل؟") +
      "</p>";
    html +=
      '<p class="cf2-home__stance-body">' + esc(action) + "</p>";
    if (href) {
      var btnClass = weak ? "cf2-btn cf2-btn--quiet" : "cf2-btn";
      var btnLabel = weak ? "عرض الأساس" : "افتح القرار";
      html +=
        '<div class="cf2-home__action"><a class="' +
        btnClass +
        '" href="' +
        esc(href) +
        '">' +
        esc(btnLabel) +
        "</a></div>";
    }
    html += "</div>";
    html += "</div>";

    if (rail.length) {
      html +=
        '<aside class="cf2-home__rail" aria-label="معرفة إضافية عن المتجر">';
      html +=
        '<p class="cf2-home__rail-label">ما يراقبه CartFlow أيضًا</p>';
      rail.forEach(function (r) {
        html += railItem(r.sec, r.tier);
      });
      html += "</aside>";
    }

    html += "</div>";

    /* Floor: only leftovers not already in the rail — rarely used */
    function notInRail(sec) {
      return !(sec && sec.id && railIds[sec.id]);
    }
    var floorKnow = parts.know.filter(notInRail);
    var floorWatch = parts.watch.filter(notInRail);
    var floorLearn = parts.learning.filter(notInRail);
    var floor =
      floorKnow.length || floorWatch.length || floorLearn.length;
    if (floor) {
      html +=
        '<div class="cf2-home__floor" aria-label="معرفة إضافية">';
      floorKnow.forEach(function (sec) {
        html += floorItem(sec, "know");
      });
      floorWatch.forEach(function (sec) {
        html += floorItem(sec, "watch");
      });
      floorLearn.forEach(function (sec) {
        html += floorItem(sec, "learning");
      });
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
