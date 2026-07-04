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
    if (!t) return "—";
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

  function itemCountLabel(count) {
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

  function headlineForItem(item) {
    if (item.action_present && item.action_ar) return item.action_ar;
    return item.what_ar || "—";
  }

  function priorityLabelAr(severity) {
    if (severity === "critical") return "عاجل";
    if (severity === "suggested") return "مقترح";
    if (severity === "attention") return "انتباه";
    return "متابعة";
  }

  function emptyStateHtml(payload) {
    var st = (payload && payload.empty_state_ar) || {};
    return (
      '<div class="ma-brief-calm">' +
      '<div class="ma-brief-calm-icon" aria-hidden="true">✓</div>' +
      '<p class="ma-brief-calm-title">' +
      esc(st.title_ar || "يوم هادئ") +
      "</p>" +
      '<p class="ma-brief-calm-msg">' +
      esc(
        st.message_ar ||
          "CartFlow يتابع الحالات الروتينية — لا يلزم تدخلك الآن"
      ) +
      "</p>" +
      "</div>"
    );
  }

  function renderEmptyState(host, payload) {
    host.innerHTML = emptyStateHtml(payload);
  }

  function renderHeroItem(item) {
    var severity = severityOf(item);
    var headline = truncate(headlineForItem(item), 72);
    var context = truncate(item.what_ar, 64);
    var why = truncate(item.why_ar, 56);
    var showContext = context && context !== headline;

    var h =
      '<article class="ma-brief-hero" data-severity="' +
      esc(severity) +
      '" aria-label="الأولوية الأولى">';
    h += '<div class="ma-brief-hero-rail" aria-hidden="true"></div>';
    h += '<div class="ma-brief-hero-body">';
    h +=
      '<div class="ma-brief-hero-top">' +
      '<span class="ma-brief-hero-kicker">الأولوية الآن</span>' +
      '<span class="ma-brief-priority-tag">' +
      esc(priorityLabelAr(severity)) +
      "</span>" +
      "</div>";
    h += '<p class="ma-brief-hero-headline">' + esc(headline) + "</p>";
    if (showContext) {
      h += '<p class="ma-brief-hero-context">' + esc(context) + "</p>";
    }
    h +=
      '<p class="ma-brief-hero-why">' +
      esc(why) +
      " · ثقة " +
      esc(item.confidence_label_ar || item.confidence || "—") +
      "</p>";
    if (item.action_present && item.action_ar) {
      h +=
        '<div class="ma-brief-hero-action">' +
        '<span class="ma-brief-action-arrow" aria-hidden="true">←</span>' +
        esc(item.action_ar) +
        "</div>";
    }
    h += "</div></article>";
    return h;
  }

  function renderCompactRow(item, index) {
    var severity = severityOf(item);
    var headline = truncate(headlineForItem(item), 48);
    var why = truncate(item.why_ar, 40);

    return (
      '<li class="ma-brief-row" data-severity="' +
      esc(severity) +
      '">' +
      '<span class="ma-brief-row-num" aria-hidden="true">' +
      esc(String(index)) +
      "</span>" +
      '<div class="ma-brief-row-main">' +
      '<p class="ma-brief-row-headline">' +
      esc(headline) +
      "</p>" +
      '<p class="ma-brief-row-sub">' +
      esc(why) +
      "</p>" +
      "</div>" +
      '<span class="ma-brief-row-priority" aria-label="' +
      esc(priorityLabelAr(severity)) +
      '"></span>' +
      "</li>"
    );
  }

  function renderBriefingHeader(payload, count) {
    var today = formatTodayAr(payload.brief_date);
    var greet = greetingAr();
    return (
      '<header class="ma-brief-header">' +
      '<p class="ma-brief-greeting">' +
      esc(greet) +
      "</p>" +
      '<p class="ma-brief-today">' +
      (today ? esc(today) : "") +
      (count > 0
        ? ' · <span class="ma-brief-count">' + esc(itemCountLabel(count)) + "</span>"
        : "") +
      "</p>" +
      "</header>"
    );
  }

  function applyDailyBriefPayload(payload) {
    var root = byId("ma-daily-brief-root");
    var host = byId("ma-daily-brief-body");
    if (!root || !host) return;

    root.classList.remove("ma-brief-has-items", "ma-brief-is-empty");

    if (!payload || !payload.ok) {
      root.classList.add("ma-brief-is-empty");
      renderEmptyState(host, null);
      return;
    }

    var items = payload.items || [];
    if (payload.empty || !items.length) {
      root.classList.add("ma-brief-is-empty");
      host.innerHTML =
        renderBriefingHeader(payload, 0) + emptyStateHtml(payload);
      return;
    }

    root.classList.add("ma-brief-has-items");
    var hero = items[0];
    var rest = items.slice(1);
    var html = renderBriefingHeader(payload, items.length);
    html += '<div class="ma-brief-focus">' + renderHeroItem(hero) + "</div>";
    if (rest.length) {
      html +=
        '<ol class="ma-brief-queue" aria-label="باقي الأمور">' +
        rest.map(function (item, i) {
          return renderCompactRow(item, i + 2);
        }).join("") +
        "</ol>";
    }
    host.innerHTML = html;
  }

  function fetchDailyBrief() {
    var host = byId("ma-daily-brief-body");
    if (!host) return Promise.resolve();

    host.innerHTML = '<p class="ma-brief-loading">جاري تجهيز ملخص يومك…</p>';

    var url = "/api/dashboard/daily-brief?_ts=" + Date.now();
    return fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) {
          renderEmptyState(host, null);
          return null;
        }
        return r.json();
      })
      .then(function (d) {
        if (d) applyDailyBriefPayload(d);
      })
      .catch(function () {
        renderEmptyState(host, null);
      });
  }

  function bootDailyBrief() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-daily-brief-root")) return;
    fetchDailyBrief();
  }

  window.maApplyDailyBriefPayload = applyDailyBriefPayload;
  window.maFetchDailyBrief = fetchDailyBrief;

  window.__maDailyBriefTestHooks = {
    greetingAr: greetingAr,
    itemCountLabel: itemCountLabel,
    headlineForItem: headlineForItem,
    truncate: truncate,
    applyDailyBriefPayload: applyDailyBriefPayload,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootDailyBrief);
  } else {
    bootDailyBrief();
  }
})();
