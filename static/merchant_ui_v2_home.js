/**
 * CartFlow Merchant UI V2 — Home executive composition V1.3
 * + Page-Specific Semantic Composition V1: gravity well + satellites.
 * Board gravity encodes attention. No repeated attention glyph / CO clause.
 * Current HES truth. semantic-visual-model-v1 drivers unchanged.
 */
(function (global) {
  "use strict";

  function L() {
    return global.CartFlowUiV2Lang || null;
  }

  function S() {
    return global.CartFlowSemanticVisualV1 || null;
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

  function statusNeedsFollow(status) {
    var s = String(status || "").trim();
    return s === "يتطلب متابعة" || s === "يحتاج تدخلاً عاجلاً";
  }

  function truthText(sec) {
    return String(
      (sec && (sec.diagnosis_ar || sec.summary_ar || sec.recommendation_ar)) || ""
    )
      .replace(/\s+/g, " ")
      .trim();
  }

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
      if (lane === "condition" || statusNeedsFollow(status)) {
        know.push(sec);
      } else if (lane === "evidence" || sec.empty) {
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

  function confidenceCopy(density) {
    if (density === "LOW") return "الأدلة ما زالت محدودة";
    if (density === "PRESENT") return "توجد أدلة كافية لاتخاذ قرار";
    return "";
  }

  function actionCopy(meaning, sufficiency) {
    if (sufficiency === "INSUFFICIENT") {
      return "لا يلزم تغيير تجاري الآن — واصل المراقبة حتى تتضح الإشارة.";
    }
    if (meaning) return meaning;
    return "راجع التفاصيل عندما تكون جاهزًا لاتخاذ قرار.";
  }

  function sceneSpine() {
    return (
      '<header class="cf2-home__spine">' +
      '<p class="cf2-home__kicker">مشهد تنفيذي</p>' +
      '<p class="cf2-home__spine-line">الحالة · الدليل · المعنى · القرار</p>' +
      "</header>"
    );
  }

  /** Momentum is NOT_CURRENTLY_SUPPORTED — never emit a semantic journey. */
  /** Page-specific composition: no shared CO clause / attention glyph as page badge. */

  function tierLabel(tier) {
    if (tier === "know") return "اعرف الآن";
    if (tier === "watch") return "راقب";
    return "ما زال يتعلّم";
  }

  function satelliteDistance(tier) {
    if (tier === "know") return "near";
    if (tier === "watch") return "mid";
    return "far";
  }

  function monitorItem(sec, tier) {
    var diagnosis = truthText(sec);
    var html =
      '<article class="cf2-home__monitor-item cf2-home__satellite" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-tier="' +
      esc(tier) +
      '" data-cf2-lane="' +
      esc(laneOf(sec)) +
      '" data-cf2-satellite="1" data-cf2-distance="' +
      esc(satelliteDistance(tier)) +
      '">';
    html +=
      '<p class="cf2-home__tier">' + esc(tierLabel(tier)) + "</p>";
    html +=
      '<h3 class="cf2-home__monitor-title">' +
      esc(sec.title_ar || "") +
      "</h3>";
    if (diagnosis) {
      html +=
        '<p class="cf2-home__monitor-body">' + esc(diagnosis) + "</p>";
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
        '<section class="cf2-home" data-cf2="home-stage-closure-v1" data-cf2-grammar="attention-gravity" data-cf2-truth="empty" data-cf2-silence="quiet">' +
        sceneSpine() +
        '<p class="cf2-empty">' +
        esc(pkg.lede_ar || "لا تتوفر معرفة كافية الآن.") +
        '</p><hr class="cf2-taper" /></section>'
      );
    }
    var parts = split(sections);
    var lang = L();
    var html =
      '<section class="cf2-home" data-cf2="home-stage-closure-v1" data-cf2-grammar="attention-gravity" data-cf2-model="semantic-visual-model-v1" data-cf2-organism="gravity-well" data-cf2-composition="page-specific-v1">';
    html += sceneSpine();

    if (!parts.primary) {
      html +=
        '<p class="cf2-empty">' +
        esc(pkg.lede_ar || "لا تتوفر معرفة كافية الآن.") +
        '</p><hr class="cf2-taper" /></section>';
      return html;
    }

    var p = parts.primary;
    var why = truthText(p);
    var meaning = String(p.recommendation_ar || "").trim();
    var href = String(p.view_details_href || "").trim();
    var sem = S() ? S().projectHomeSurface(pkg, p) : null;
    var silence = sem ? sem.core_silence : "ACTIVE";
    var density = sem ? sem.density : "NEUTRAL";
    var attention = sem ? sem.attention_intensity : "NONE";
    var confidence = confidenceCopy(density);
    var action = actionCopy(meaning, sem ? sem.evidence_sufficiency : "UNKNOWN");
    var boardEdge =
      silence === "QUIET"
        ? "quiet"
        : attention === "PRIMARY"
          ? "attention"
          : "neutral";
    var gravity =
      silence === "QUIET" || attention === "NONE"
        ? "none"
        : attention === "PRIMARY"
          ? "primary"
          : "secondary";

    var monitor = [];
    parts.know.forEach(function (sec) {
      monitor.push({ sec: sec, tier: "know" });
    });
    parts.watch.forEach(function (sec) {
      monitor.push({ sec: sec, tier: "watch" });
    });
    parts.learning.forEach(function (sec) {
      monitor.push({ sec: sec, tier: "learning" });
    });
    monitor = monitor.slice(0, 3);
    var monitorIds = {};
    monitor.forEach(function (r) {
      if (r.sec && r.sec.id) monitorIds[r.sec.id] = true;
    });

    html +=
      '<div class="cf2-home__board" data-cf2-edge="' +
      esc(boardEdge) +
      '" data-cf2-gravity="' +
      esc(gravity) +
      '" data-cf2-attention="' +
      esc(String(attention || "NONE").toLowerCase()) +
      '" data-cf2-silence="' +
      esc(silence.toLowerCase()) +
      '" data-cf2-monitor="' +
      (monitor.length ? "on" : "empty") +
      '">';

    /* ——— Primary reading path (gravity well — no CO clause) ——— */
    html += '<div class="cf2-home__scene">';
    html += '<div class="cf2-home__lead">';
    html += '<div class="cf2-home__lead-text">';
    html += '<p class="cf2-home__lane">مركز الجاذبية</p>';
    html += '<p class="cf2-home__eyebrow">الأهم الآن</p>';
    html +=
      '<h2 class="cf2-home__title">' + esc(p.title_ar || "") + "</h2>";
    html += "</div></div>";

    if (why) {
      html += '<p class="cf2-home__why">' + esc(why) + "</p>";
    }

    html +=
      '<div class="cf2-home__evidence" data-cf2-density="' +
      esc(String(density || "NEUTRAL").toLowerCase()) +
      '">';
    if (confidence) {
      html +=
        '<p class="cf2-home__confidence">' + esc(confidence) + "</p>";
    }
    if (
      silence !== "QUIET" &&
      lang &&
      lang.evidenceFieldFromSufficiency &&
      density !== "NEUTRAL"
    ) {
      html +=
        '<div class="cf2-home__field" aria-hidden="true">' +
        lang.evidenceFieldFromSufficiency(density) +
        "</div>";
    }
    html += "</div>";

    html +=
      '<div class="cf2-home__stance cf2-terminus" data-cf2-wait="' +
      esc(sem ? String(sem.wait_kind || "UNKNOWN").toLowerCase() : "unknown") +
      '">';
    html +=
      '<p class="cf2-home__stance-label">' +
      esc(
        sem && sem.evidence_sufficiency === "INSUFFICIENT"
          ? "الوضع الآن"
          : "ماذا تفعل؟"
      ) +
      "</p>";
    html +=
      '<p class="cf2-home__stance-body">' + esc(action) + "</p>";
    if (href) {
      var btnClass =
        sem && sem.evidence_sufficiency === "INSUFFICIENT"
          ? "cf2-btn cf2-btn--quiet"
          : "cf2-btn";
      var btnLabel =
        sem && sem.evidence_sufficiency === "INSUFFICIENT"
          ? "عرض الأساس"
          : "افتح القرار";
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

    /* ——— Monitoring: embedded continuation, not a sidebar column ——— */
    if (monitor.length) {
      html += '<div class="cf2-home__orbit-axis" aria-hidden="true"></div>';
      html +=
        '<aside class="cf2-home__monitor" data-cf2-orbit="satellites" aria-label="ما يراقبه CartFlow أيضًا">';
      html +=
        '<p class="cf2-home__monitor-label">ما يراقبه CartFlow أيضًا</p>';
      html += '<div class="cf2-home__monitor-row" data-cf2-orbit-row="1">';
      monitor.forEach(function (r) {
        html += monitorItem(r.sec, r.tier);
      });
      html += "</div></aside>";
    }

    html += "</div>";

    function notInMonitor(sec) {
      return !(sec && sec.id && monitorIds[sec.id]);
    }
    var floorKnow = parts.know.filter(notInMonitor);
    var floorWatch = parts.watch.filter(notInMonitor);
    var floorLearn = parts.learning.filter(notInMonitor);
    if (floorKnow.length || floorWatch.length || floorLearn.length) {
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
    render: render,
  };
})(typeof window !== "undefined" ? window : globalThis);
