/**
 * Merchant Home Experience — Product Excellence V2 presentation.
 * Consumes merchant_home_experience_v1 from GET /api/dashboard/summary.
 * Presentation only — never selects, ranks, or mints knowledge.
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

  function buildHeroTitle(attention, whileAway) {
    var n = ((attention && attention.items) || []).length;
    if (n === 1) return "CartFlow يتابع — أمر واحد يحتاجك";
    if (n > 1) return "CartFlow يتابع — " + n + " أمور تحتاجك";
    if (((whileAway && whileAway.items) || []).length) {
      return "CartFlow يتابع متجرك";
    }
    return "CartFlow يتابع متجرك — يوم هادئ";
  }

  function buildHeroStory(whileAway, attention) {
    var parts = [];
    ((whileAway && whileAway.items) || []).forEach(function (item) {
      var h = String(item.headline_ar || "").trim();
      if (h) parts.push(h);
    });
    var att = ((attention && attention.items) || []).length;
    if (att && !parts.length) {
      parts.push(att === 1 ? "أمر واحد يحتاج انتباهك" : att + " أمور تحتاج انتباهك");
    }
    if (!parts.length) {
      return (
        (whileAway && whileAway.empty_message_ar) ||
        "CartFlow يتابع متجرك."
      );
    }
    return parts.slice(0, 4).join(" · ");
  }

  function renderPeV2Hero(greeting, whileAway, attention) {
    greeting = greeting || {};
    var greet = String(greeting.greeting_ar || greetingArFallback()).trim();
    var name = String(greeting.merchant_name_ar || "متجرك").trim();
    var date = String(greeting.date_ar || "").trim();
    var shellDate = byId("ma-home-date-shell");
    if (!date && shellDate) date = String(shellDate.textContent || "").trim();

    var items = (whileAway && whileAway.items) || [];
    var statsHtml = "";
    if (items.length) {
      statsHtml = '<div class="v2-hero-stats" aria-label="ما أنجزه CartFlow">';
      items.slice(0, 4).forEach(function (item) {
        statsHtml +=
          '<span class="v2-hero-stat"><span class="v2-hero-stat-icon">✓</span> ' +
          esc(item.headline_ar || "—") +
          "</span>";
      });
      statsHtml += "</div>";
    }

    return (
      '<section class="v2-hero" aria-label="قصة اليوم">' +
      '<div class="v2-hero-glow" aria-hidden="true"></div>' +
      '<p class="v2-hero-kicker">' +
      esc(greet) +
      "، " +
      esc(name) +
      (date ? " · " + esc(date) : "") +
      "</p>" +
      '<h1 class="v2-hero-title">' +
      esc(buildHeroTitle(attention, whileAway)) +
      "</h1>" +
      '<p class="v2-hero-story">' +
      esc(buildHeroStory(whileAway, attention)) +
      "</p>" +
      statsHtml +
      "</section>"
    );
  }

  function renderPeV2ActionCard(attention) {
    attention = attention || {};
    var items = attention.items || [];
    if (!items.length) {
      return (
        '<aside class="v2-whisper ma-pe-v2-calm">' +
        '<p class="v2-whisper-label">' +
        esc(attention.title_ar || "يحتاج انتباهك اليوم") +
        "</p>" +
        '<p class="v2-whisper-text">' +
        esc(attention.empty_message_ar || "لا أمور تتطلب انتباهك الآن") +
        "</p></aside>"
      );
    }
    var item = items[0];
    var btnLabel = String(item.action_ar || "عرض السلال").trim();
    return (
      '<article class="v2-action-card is-attention">' +
      '<p class="v2-action-eyebrow">يحتاجك الآن</p>' +
      '<h2 class="v2-action-headline">' +
      esc(item.headline_ar || "—") +
      "</h2>" +
      (item.why_ar
        ? '<p class="v2-action-why">' + esc(item.why_ar) + "</p>"
        : "") +
      '<a class="v2-btn" href="#" role="button" onclick="if(window.goToSection){goToSection(\'carts\');}return false;">' +
      esc(btnLabel) +
      "</a></article>"
    );
  }

  function renderPeV2Understanding(section) {
    section = section || {};
    var items = section.items || [];
    if (!items.length) {
      return (
        '<aside class="v2-whisper" id="ma-home-understanding">' +
        '<p class="v2-whisper-label">' +
        esc(section.title_ar || "فهم المتجر") +
        "</p>" +
        '<p class="v2-whisper-text">' +
        esc(section.empty_message_ar || "لا توجد استنتاجات كافية بعد.") +
        "</p></aside>"
      );
    }
    var item = items[0];
    var text =
      String(item.observation_ar || item.impact_ar || item.title_ar || "").trim() ||
      "—";
    return (
      '<aside class="v2-whisper" id="ma-home-understanding">' +
      '<p class="v2-whisper-label">' +
      esc(section.title_ar || "فهم المتجر") +
      "</p>" +
      '<p class="v2-whisper-text">' +
      esc(text) +
      "</p></aside>"
    );
  }

  function renderPeV2QuickNav(section) {
    section = section || {};
    var items = (section.items || []).filter(function (item) {
      return item.visible !== false;
    });
    if (!items.length) return "";
    var html =
      '<nav class="v2-nav-links" aria-labelledby="ma-home-nav-title">' +
      '<span id="ma-home-nav-title" class="visually-hidden">' +
      esc(section.title_ar || "انتقال سريع") +
      "</span>";
    items.forEach(function (item) {
      var badge =
        item.badge_count > 0
          ? " (" + esc(item.badge_count) + ")"
          : "";
      var type = String(item.nav_type || "").trim();
      if (type === "anchor") {
        html +=
          '<a href="' +
          esc(String(item.href || "#").trim()) +
          '">' +
          esc(item.label_ar || "") +
          badge +
          "</a>";
      } else {
        html +=
          '<a href="#" role="button"' +
          navItemOnclick(item) +
          ">" +
          esc(item.label_ar || "") +
          badge +
          "</a>";
      }
    });
    html += "</nav>";
    return html;
  }

  function applyHomeExperience(payload) {
    var root = byId("ma-home-experience-root");
    if (!root) return;

    root.classList.remove(
      "ma-home-experience--loading",
      "ma-home-experience--calm",
      "ma-home-experience--legacy"
    );
    root.classList.add("ma-pe-v2-home");

    if (!payload || !payload.ok) {
      root.classList.add("ma-home-experience--calm");
      root.innerHTML =
        renderPeV2Hero(null, null, null) +
        '<aside class="v2-whisper ma-pe-v2-calm"><p class="v2-whisper-text">CartFlow يتابع متجرك — جرّب تحديث الصفحة.</p></aside>';
      return;
    }

    var html = renderPeV2Hero(payload.greeting, payload.while_away, payload.attention_today);
    html += renderPeV2ActionCard(payload.attention_today);
    html += renderPeV2Understanding(payload.store_understanding);
    html += renderPeV2QuickNav(payload.quick_nav);

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
