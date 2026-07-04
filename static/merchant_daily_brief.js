(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(text, max) {
    var t = String(text || "").trim();
    if (!t) return "";
    if (t.length <= max) return t;
    return t.slice(0, Math.max(0, max - 1)).trim() + "…";
  }

  function greetingAr() {
    var h = new Date().getHours();
    if (h >= 5 && h < 12) return "صباح الخير";
    return "مساء الخير";
  }

  function formatTodayAr(briefDate) {
    try {
      var d = briefDate ? new Date(briefDate + "T12:00:00") : new Date();
      return d.toLocaleDateString("ar-SA", {
        weekday: "long",
        day: "numeric",
        month: "long",
      });
    } catch (e) {
      return "";
    }
  }

  function attentionCountLabel(count) {
    if (count === 0) return "لا أمور تتطلب انتباهك الآن";
    if (count === 1) return "أمر واحد يستحق انتباهك";
    if (count === 2) return "أمران يستحقان انتباهك";
    if (count >= 3 && count <= 10) return count + " أمور تستحق انتباهك";
    return count + " أمراً";
  }

  function severityOf(item) {
    var cls = String((item && item.decision_class) || "").trim();
    if (cls === "critical_action") return "critical";
    if (cls === "suggested_action") return "suggested";
    if (cls === "needs_attention") return "attention";
    return "observation";
  }

  /** Action/problem first — never decision class as hero title. */
  function primaryHeadline(item) {
    if (item.action_present && item.action_ar) return String(item.action_ar).trim();
    return String(item.what_ar || "").trim() || "—";
  }

  function secondaryMetaLine(item) {
    var parts = [];
    var cls = String(item.decision_class_label_ar || "").trim();
    if (cls) parts.push(cls);
    var conf = String(item.confidence_label_ar || item.confidence || "").trim();
    if (conf) parts.push("ثقة " + conf);
    var src = String(item.evidence_source_ar || "").trim();
    if (src && src !== "—") parts.push(src);
    return parts.join(" · ");
  }

  function queueCardMeta(item) {
    var cls = String(item.decision_class_label_ar || "").trim() || "—";
    var conf = String(item.confidence_label_ar || "").trim();
    return conf ? cls + " · " + conf : cls;
  }

  function emptyStateHtml(payload) {
    var st = (payload && payload.empty_state_ar) || {};
    return (
      '<div class="ma-brief-calm">' +
      '<div class="ma-brief-calm-icon" aria-hidden="true">✓</div>' +
      '<p class="ma-brief-calm-title">' +
      esc(st.title_ar || "CartFlow يتابع متجرك") +
      "</p>" +
      '<p class="ma-brief-calm-msg">' +
      esc(
        st.message_ar ||
          "لا يلزم تدخلك الآن — نتابع الحالات الروتينية تلقائياً"
      ) +
      "</p>" +
      "</div>"
    );
  }

  function renderBriefingHeader(payload, count) {
    var today = formatTodayAr(payload && payload.brief_date);
    var shellToday = byId("ma-brief-today-shell");
    if (!today && shellToday) today = String(shellToday.textContent || "").trim();
    return (
      '<header class="ma-brief-header">' +
      '<p class="ma-brief-greeting">' +
      esc(greetingAr()) +
      "</p>" +
      '<p class="ma-brief-today">' +
      esc(today || "") +
      "</p>" +
      '<p class="ma-brief-attention-count">' +
      esc(attentionCountLabel(count)) +
      "</p>" +
      "</header>"
    );
  }

  function renderHeroItem(item) {
    var severity = severityOf(item);
    var headline = truncate(primaryHeadline(item), 84);
    var why = truncate(item.why_ar, 52);
    var meta = secondaryMetaLine(item);
    var showWhy = why && why !== headline;

    var h =
      '<article class="ma-brief-hero" data-severity="' +
      esc(severity) +
      '" aria-label="الأولوية الأولى">';
    h += '<div class="ma-brief-hero-rail" aria-hidden="true"></div>';
    h += '<div class="ma-brief-hero-body">';
    h += '<p class="ma-brief-hero-headline">' + esc(headline) + "</p>";
    if (showWhy) {
      h += '<p class="ma-brief-hero-why">' + esc(why) + "</p>";
    }
    if (meta) {
      h += '<p class="ma-brief-hero-meta">' + esc(meta) + "</p>";
    }
    h += "</div></article>";
    return h;
  }

  function renderQueueCard(item) {
    var severity = severityOf(item);
    return (
      '<li class="ma-brief-card" data-severity="' +
      esc(severity) +
      '">' +
      '<p class="ma-brief-card-headline">' +
      esc(truncate(primaryHeadline(item), 44)) +
      "</p>" +
      '<p class="ma-brief-card-meta">' +
      esc(queueCardMeta(item)) +
      "</p>" +
      "</li>"
    );
  }

  function applyDailyBriefPayload(payload) {
    var root = byId("ma-daily-brief-root");
    var host = byId("ma-daily-brief-body");
    if (!root || !host) return;

    root.classList.remove("ma-brief-has-items", "ma-brief-is-empty", "ma-brief-is-loading");

    if (!payload || !payload.ok) {
      root.classList.add("ma-brief-is-empty");
      host.innerHTML = renderBriefingHeader(null, 0) + emptyStateHtml(null);
      return;
    }

    var items = payload.items || [];
    if (payload.empty || !items.length) {
      root.classList.add("ma-brief-is-empty");
      host.innerHTML = renderBriefingHeader(payload, 0) + emptyStateHtml(payload);
      return;
    }

    root.classList.add("ma-brief-has-items");
    var hero = items[0];
    var rest = items.slice(1);
    var html = renderBriefingHeader(payload, items.length);
    html += '<div class="ma-brief-focus">' + renderHeroItem(hero) + "</div>";
    if (rest.length) {
      html +=
        '<div class="ma-brief-queue-wrap">' +
        '<p class="ma-brief-queue-label">باقي الأمور</p>' +
        '<ul class="ma-brief-grid" aria-label="باقي الأمور">' +
        rest.map(renderQueueCard).join("") +
        "</ul></div>";
    }
    host.innerHTML = html;
  }

  function renderInstantShell() {
    var root = byId("ma-daily-brief-root");
    var host = byId("ma-daily-brief-body");
    if (!root || !host || root.classList.contains("ma-brief-has-items")) return;
    if (root.classList.contains("ma-brief-is-empty") && host.querySelector(".ma-brief-calm")) {
      return;
    }
    root.classList.add("ma-brief-is-loading");
    var todayEl = byId("ma-brief-today-shell");
    var today = todayEl ? String(todayEl.textContent || "").trim() : "";
    host.innerHTML =
      '<header class="ma-brief-header">' +
      '<p class="ma-brief-greeting">' +
      esc(greetingAr()) +
      "</p>" +
      '<p class="ma-brief-today">' +
      esc(today) +
      "</p>" +
      '<p class="ma-brief-attention-count ma-brief-attention-count--pending">' +
      esc("جاري تجميع ما يستحق انتباهك…") +
      "</p>" +
      "</header>";
  }

  function fetchDailyBrief(options) {
    var opts = options || {};
    var host = byId("ma-daily-brief-body");
    if (!host) return Promise.resolve();

    if (!opts.silent) {
      renderInstantShell();
    }

    var url = "/api/dashboard/daily-brief?_ts=" + Date.now();
    return fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) {
          applyDailyBriefPayload(null);
          return null;
        }
        return r.json();
      })
      .then(function (d) {
        if (d) applyDailyBriefPayload(d);
        return d;
      })
      .catch(function () {
        applyDailyBriefPayload(null);
      });
  }

  function bootDailyBriefShell() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-daily-brief-root")) return;
    var greet = byId("ma-brief-greeting-shell");
    if (greet) greet.textContent = greetingAr();
  }

  window.maApplyDailyBriefPayload = applyDailyBriefPayload;
  window.maFetchDailyBrief = fetchDailyBrief;
  window.maRenderDailyBriefShell = renderInstantShell;

  window.__maDailyBriefTestHooks = {
    greetingAr: greetingAr,
    attentionCountLabel: attentionCountLabel,
    primaryHeadline: primaryHeadline,
    secondaryMetaLine: secondaryMetaLine,
    truncate: truncate,
    applyDailyBriefPayload: applyDailyBriefPayload,
    renderInstantShell: renderInstantShell,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootDailyBriefShell);
  } else {
    bootDailyBriefShell();
  }
})();
