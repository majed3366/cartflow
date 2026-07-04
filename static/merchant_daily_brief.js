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

  function renderEmptyState(host, payload) {
    var st = (payload && payload.empty_state_ar) || {};
    host.innerHTML =
      '<div class="ma-daily-brief-empty">' +
      '<p class="ma-daily-brief-empty-title">' +
      esc(st.title_ar || "يوم هادئ في متجرك") +
      "</p>" +
      '<p class="ma-daily-brief-empty-msg">' +
      esc(
        st.message_ar ||
          "لا توجد قرارات تتطلب انتباهك اليوم — CartFlow يتابع الحالات الروتينية تلقائياً"
      ) +
      "</p>" +
      "</div>";
  }

  function renderBriefItem(item) {
    var cls = String(item.decision_class || "").trim();
    var severity =
      cls === "critical_action"
        ? "critical"
        : cls === "suggested_action"
          ? "suggested"
          : cls === "needs_attention"
            ? "attention"
            : "observation";
    var h =
      '<article class="ma-daily-brief-item" data-severity="' +
      esc(severity) +
      '">';
    h +=
      '<div class="ma-daily-brief-item-head">' +
      '<span class="ma-daily-brief-class">' +
      esc(item.decision_class_label_ar || "—") +
      "</span>";
    if (item.commercial_goal_label_ar) {
      h +=
        '<span class="ma-daily-brief-goal">' +
        esc(item.commercial_goal_label_ar) +
        "</span>";
    }
    h += "</div>";
    h += '<div class="ma-daily-brief-oia">';
    h +=
      '<div class="ma-daily-brief-block"><span class="ma-daily-brief-label">ماذا حدث؟</span><p class="ma-daily-brief-text">' +
      esc(item.what_ar || "—") +
      "</p></div>";
    h +=
      '<div class="ma-daily-brief-block"><span class="ma-daily-brief-label">لماذا يهمك؟</span><p class="ma-daily-brief-text">' +
      esc(item.why_ar || "—") +
      "</p></div>";
    if (item.action_present && item.action_ar) {
      h +=
        '<div class="ma-daily-brief-block ma-daily-brief-action"><span class="ma-daily-brief-label">ماذا تفعل؟</span><p class="ma-daily-brief-text">' +
        esc(item.action_ar) +
        "</p></div>";
    }
    h += "</div>";
    h +=
      '<div class="ma-daily-brief-meta">' +
      "<span>الثقة: " +
      esc(item.confidence_label_ar || item.confidence || "—") +
      "</span>" +
      " · <span>المصدر: " +
      esc(item.evidence_source_ar || "—") +
      "</span>" +
      "</div>";
    h += "</article>";
    return h;
  }

  function applyDailyBriefPayload(payload) {
    var root = byId("ma-daily-brief-root");
    var host = byId("ma-daily-brief-body");
    if (!root || !host) return;

    if (!payload || !payload.ok) {
      renderEmptyState(host, null);
      return;
    }

    var items = payload.items || [];
    if (payload.empty || !items.length) {
      renderEmptyState(host, payload);
      return;
    }

    host.innerHTML =
      '<div class="ma-daily-brief-list">' +
      items.map(renderBriefItem).join("") +
      "</div>";
  }

  function fetchDailyBrief() {
    var host = byId("ma-daily-brief-body");
    if (!host) return Promise.resolve();

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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootDailyBrief);
  } else {
    bootDailyBrief();
  }
})();
