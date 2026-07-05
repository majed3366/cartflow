/**
 * Merchant Home Experience v1 — composition consumer (presentation only).
 * Consumes merchant_home_experience_v1 from GET /api/dashboard/summary.
 * Never selects, ranks, or mints knowledge.
 */
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

  function greetingArFallback() {
    var h = new Date().getHours();
    if (h >= 5 && h < 12) return "صباح الخير";
    return "مساء الخير";
  }

  function renderGreeting(g) {
    g = g || {};
    var greet = String(g.greeting_ar || greetingArFallback()).trim();
    var name = String(g.merchant_name_ar || "متجرك").trim();
    var date = String(g.date_ar || "").trim();
    var shellDate = byId("ma-home-date-shell");
    if (!date && shellDate) date = String(shellDate.textContent || "").trim();
    return (
      '<header class="ma-home-greeting">' +
      '<p class="ma-home-greeting-text">' +
      esc(greet) +
      "</p>" +
      '<p class="ma-home-greeting-name">' +
      esc(name) +
      "</p>" +
      (date ? '<p class="ma-home-greeting-date">' + esc(date) + "</p>" : "") +
      "</header>"
    );
  }

  function renderWhileAway(section) {
    section = section || {};
    var items = section.items || [];
    var html =
      '<section class="ma-home-block ma-home-block--achievements" aria-labelledby="ma-home-away-title">' +
      '<h2 class="ma-home-block-title" id="ma-home-away-title">' +
      esc(section.title_ar || "بينما كنت بعيداً") +
      "</h2>";
    if (section.lead_ar) {
      html += '<p class="ma-home-block-lead">' + esc(section.lead_ar) + "</p>";
    }
    if (!items.length) {
      html +=
        '<p class="ma-home-block-empty">' +
        esc(section.empty_message_ar || "CartFlow يتابع متجرك.") +
        "</p>";
    } else {
      html += '<ul class="ma-home-story-list">';
      items.forEach(function (item) {
        html +=
          '<li class="ma-home-story-item ma-home-story-item--achievement">' +
          '<span class="ma-home-story-icon" aria-hidden="true">✓</span>' +
          '<div class="ma-home-story-body">' +
          '<p class="ma-home-story-headline">' +
          esc(item.headline_ar || "—") +
          "</p>";
        if (item.detail_ar && item.detail_ar !== item.headline_ar) {
          html +=
            '<p class="ma-home-story-detail">' + esc(item.detail_ar) + "</p>";
        }
        html += "</div></li>";
      });
      html += "</ul>";
    }
    html += "</section>";
    return html;
  }

  function renderAttention(section) {
    section = section || {};
    var items = section.items || [];
    var html =
      '<section class="ma-home-block ma-home-block--attention" aria-labelledby="ma-home-attention-title">' +
      '<h2 class="ma-home-block-title" id="ma-home-attention-title">' +
      esc(section.title_ar || "يحتاج انتباهك اليوم") +
      "</h2>";
    if (section.lead_ar) {
      html += '<p class="ma-home-block-lead">' + esc(section.lead_ar) + "</p>";
    }
    if (!items.length) {
      html +=
        '<div class="ma-home-calm">' +
        '<p class="ma-home-calm-msg">' +
        esc(section.empty_message_ar || "لا أمور تتطلب انتباهك الآن") +
        "</p></div>";
    } else {
      html += '<ul class="ma-home-attention-list">';
      items.forEach(function (item, idx) {
        var sev = String(item.severity || "attention").trim();
        html +=
          '<li class="ma-home-attention-item" data-severity="' +
          esc(sev) +
          '" data-index="' +
          idx +
          '">' +
          '<p class="ma-home-attention-headline">' +
          esc(item.headline_ar || "—") +
          "</p>";
        if (item.why_ar) {
          html +=
            '<p class="ma-home-attention-why">' + esc(item.why_ar) + "</p>";
        }
        if (item.action_ar) {
          html +=
            '<p class="ma-home-attention-action"><strong>الإجراء:</strong> ' +
            esc(item.action_ar) +
            "</p>";
        }
        html += "</li>";
      });
      html += "</ul>";
    }
    html += "</section>";
    return html;
  }

  function renderUnderstanding(section) {
    section = section || {};
    var items = section.items || [];
    var html =
      '<section class="ma-home-block ma-home-block--understanding" id="ma-home-understanding" aria-labelledby="ma-home-understanding-title">' +
      '<h2 class="ma-home-block-title" id="ma-home-understanding-title">' +
      esc(section.title_ar || "فهم المتجر") +
      "</h2>";
    if (section.lead_ar) {
      html += '<p class="ma-home-block-lead">' + esc(section.lead_ar) + "</p>";
    }
    if (!items.length) {
      html +=
        '<p class="ma-home-block-empty">' +
        esc(section.empty_message_ar || "لا توجد استنتاجات كافية بعد.") +
        "</p>";
    } else {
      html += '<div class="ma-home-understanding-stack">';
      items.forEach(function (item) {
        html +=
          '<article class="ma-home-understanding-card">' +
          '<h3 class="ma-home-understanding-title">' +
          esc(item.title_ar || "—") +
          "</h3>";
        if (item.observation_ar) {
          html +=
            '<p class="ma-home-understanding-obs">' +
            esc(item.observation_ar) +
            "</p>";
        }
        if (item.impact_ar) {
          html +=
            '<p class="ma-home-understanding-impact">' +
            esc(item.impact_ar) +
            "</p>";
        }
        if (item.action_ar) {
          html +=
            '<p class="ma-home-understanding-action">' +
            esc(item.action_ar) +
            "</p>";
        }
        html += "</article>";
      });
      html += "</div>";
    }
    html += "</section>";
    return html;
  }

  function navItemOnclick(item) {
    var type = String(item.nav_type || "").trim();
    if (type === "cart_tab" && item.cart_tab) {
      return (
        ' onclick="if(window.goToCartTab){goToCartTab(\'' +
        esc(item.cart_tab) +
        "');}return false;\""
      );
    }
    if (type === "settings" && item.settings_page) {
      return (
        ' onclick="if(window.goTo){goTo(\'' +
        esc(item.settings_page) +
        "');}return false;\""
      );
    }
    return "";
  }

  function renderQuickNav(section) {
    section = section || {};
    var items = (section.items || []).filter(function (item) {
      return item.visible !== false;
    });
    var html =
      '<nav class="ma-home-block ma-home-block--nav" aria-labelledby="ma-home-nav-title">' +
      '<h2 class="ma-home-block-title ma-home-block-title--nav" id="ma-home-nav-title">' +
      esc(section.title_ar || "انتقال سريع") +
      "</h2>" +
      '<ul class="ma-home-nav-list">';
    items.forEach(function (item) {
      var badge =
        item.badge_count > 0
          ? '<span class="ma-home-nav-badge">' + esc(item.badge_count) + "</span>"
          : "";
      var href = String(item.href || "#").trim();
      var type = String(item.nav_type || "").trim();
      if (type === "anchor") {
        html +=
          '<li><a class="ma-home-nav-link" href="' +
          esc(href) +
          '">' +
          esc(item.label_ar || "") +
          badge +
          "</a></li>";
      } else {
        html +=
          '<li><a class="ma-home-nav-link" href="#" role="button"' +
          navItemOnclick(item) +
          ">" +
          esc(item.label_ar || "") +
          badge +
          "</a></li>";
      }
    });
    html += "</ul></nav>";
    return html;
  }

  function applyHomeExperience(payload) {
    var root = byId("ma-home-experience-root");
    if (!root) return;

    root.classList.remove("ma-home-experience--loading", "ma-home-experience--calm");

    if (!payload || !payload.ok) {
      root.classList.add("ma-home-experience--calm");
      root.innerHTML =
        renderGreeting(null) +
        '<div class="ma-home-calm"><p class="ma-home-calm-msg">CartFlow يتابع متجرك — جرّب تحديث الصفحة.</p></div>';
      return;
    }

    var html = renderGreeting(payload.greeting);
    html += renderWhileAway(payload.while_away);
    html += renderAttention(payload.attention_today);
    html += renderUnderstanding(payload.store_understanding);
    html += renderQuickNav(payload.quick_nav);

    if (payload.empty_calm) {
      root.classList.add("ma-home-experience--calm");
    }

    root.innerHTML = html;
  }

  function bootHomeShell() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    var root = byId("ma-home-experience-root");
    if (!root) return;
    var greetShell = byId("ma-home-greeting-shell");
    if (greetShell) greetShell.textContent = greetingArFallback();
  }

  window.maApplyHomeExperience = applyHomeExperience;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootHomeShell);
  } else {
    bootHomeShell();
  }
})();
