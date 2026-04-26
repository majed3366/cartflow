/**
 * إرشادات خطوات التجربة — صفحات ‎/demo/*‎ فقط (يُحمّل من ‎demo_store‎).
 */
(function () {
  "use strict";

  var path = (window.location.pathname || "") + (window.location.search || "");
  if (!/\/demo\//i.test(path)) {
    return;
  }

  var STEPS = [
    "كل منتج في السلة = فرصة بيع تستحق المتابعة",
    "لاحظ كيف ما نخلي العميل يطلع بسهولة",
    "نفهم تردّده… ونحوّله إلى خطوة بدل ما يضيع",
    "🎯 كل عميل يحصل على حل مناسب له",
  ];

  var OUTCOME_INTRO =
    "📲 العميل ما يضيع… نكمل معه تلقائيًا حسب سبب تردده";
  var OUTCOME_TAGLINE = "🎯 كل عميل يحصل على حل مناسب له";
  var SUB_EXAMPLES = {
    price_discount_request: "عرض يلائم وضعه — ويقرّب قراره بدون ضغط.",
    price_budget_issue: "نقترح له خياراً أنسب لميزانيته — بلطف.",
    price_cheaper_alternative: "نرشّح له بديلاً يلبي توقّعه — بسرعة.",
  };

  var DISMISS_KEY = "cf_demo_guide_dismissed";
  var stepIdx = 0;
  var autoT = null;
  var root = null;
  var waHint = null;

  function readDismissed() {
    try {
      return window.sessionStorage.getItem(DISMISS_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function setDismissed() {
    try {
      window.sessionStorage.setItem(DISMISS_KEY, "1");
    } catch (e) {
      /* ignore */
    }
  }

  function clearAuto() {
    if (autoT) {
      clearTimeout(autoT);
      autoT = null;
    }
  }

  function scheduleAuto() {
    clearAuto();
    autoT = setTimeout(function () {
      if (!root || root.hasAttribute("hidden")) {
        return;
      }
      if (stepIdx < STEPS.length - 1) {
        stepIdx += 1;
        paint();
        scheduleAuto();
      }
    }, 12000);
  }

  function paint() {
    if (!root) {
      return;
    }
    var t = root.querySelector("[data-cf-guide-step-text]");
    if (t) {
      t.textContent = STEPS[stepIdx];
    }
    var dots = root.querySelectorAll("[data-cf-guide-dot]");
    var i;
    for (i = 0; i < dots.length; i++) {
      dots[i].style.background = i === stepIdx ? "#7c3aed" : "#d6d3d1";
      dots[i].style.transform = i === stepIdx ? "scale(1.15)" : "scale(1)";
    }
  }

  function bumpMin(minIdx) {
    if (minIdx > stepIdx) {
      stepIdx = minIdx;
      paint();
    }
    if (stepIdx >= STEPS.length - 1) {
      clearAuto();
    }
  }

  function cartHasItems() {
    return window.cart && Array.isArray(window.cart) && window.cart.length > 0;
  }

  function showWaHint(detail) {
    if (!waHint) {
      return;
    }
    var sub = detail && detail.sub_category ? String(detail.sub_category) : "";
    var extra = sub && SUB_EXAMPLES[sub] ? SUB_EXAMPLES[sub] : "";
    var body = waHint.querySelector("[data-cf-wa-hint-body]");
    if (body) {
      body.innerHTML = "";
      var p0 = document.createElement("p");
      p0.style.cssText = "margin:0 0 6px 0;font-weight:700;";
      p0.textContent = OUTCOME_INTRO;
      body.appendChild(p0);
      var pTag = document.createElement("p");
      pTag.style.cssText = "margin:0 0 8px 0;font-size:0.84rem;opacity:0.95;line-height:1.4;";
      pTag.textContent = OUTCOME_TAGLINE;
      body.appendChild(pTag);
      if (extra) {
        var p1 = document.createElement("p");
        p1.style.cssText = "margin:0;font-size:0.78rem;opacity:0.9;";
        p1.textContent = extra;
        body.appendChild(p1);
      }
    }
    waHint.removeAttribute("hidden");
    waHint.style.opacity = "0";
    waHint.style.transform = "translateY(6px)";
    requestAnimationFrame(function () {
      waHint.style.transition = "opacity 0.25s ease, transform 0.25s ease";
      waHint.style.opacity = "1";
      waHint.style.transform = "translateY(0)";
    });
    clearTimeout(waHint._hideT);
    waHint._hideT = setTimeout(function () {
      waHint.style.opacity = "0";
      waHint.style.transform = "translateY(6px)";
      setTimeout(function () {
        waHint.setAttribute("hidden", "");
      }, 280);
    }, 9000);
  }

  function mount() {
    if (document.getElementById("cf-demo-guide")) {
      return;
    }
    root = document.createElement("aside");
    root.id = "cf-demo-guide";
    root.className = "cf-demo-guide";
    root.setAttribute("dir", "rtl");
    root.setAttribute("lang", "ar");
    root.setAttribute("aria-label", "إرشاد التجربة");

    var inner =
      '<div class="cf-demo-guide-inner">' +
      '<div class="cf-demo-guide-head">' +
      '<span class="cf-demo-guide-title">شو راح تلاحظ؟</span>' +
      '<button type="button" class="cf-demo-guide-close" data-cf-guide-dismiss aria-label="إخفاء">×</button>' +
      "</div>" +
      '<p class="cf-demo-guide-step" data-cf-guide-step-text></p>' +
      '<div class="cf-demo-guide-dots" role="tablist">' +
      '<span data-cf-guide-dot></span><span data-cf-guide-dot></span>' +
      '<span data-cf-guide-dot></span><span data-cf-guide-dot></span>' +
      "</div>" +
      '<button type="button" class="cf-demo-guide-next" data-cf-guide-next>التالي</button>' +
      "</div>";

    root.innerHTML = inner;
    document.body.appendChild(root);

    waHint = document.createElement("div");
    waHint.id = "cf-demo-wa-hint";
    waHint.className = "cf-demo-wa-hint";
    waHint.setAttribute("hidden", "");
    waHint.setAttribute("dir", "rtl");
    waHint.innerHTML =
      '<div class="cf-demo-wa-hint-inner" data-cf-wa-hint-body></div>';
    document.body.appendChild(waHint);

    root.querySelector("[data-cf-guide-dismiss]").addEventListener("click", function () {
      root.setAttribute("hidden", "");
      setDismissed();
      clearAuto();
    });

    root.querySelector("[data-cf-guide-next]").addEventListener("click", function () {
      if (stepIdx < STEPS.length - 1) {
        stepIdx += 1;
        paint();
        scheduleAuto();
      }
    });

    if (readDismissed()) {
      root.setAttribute("hidden", "");
      return;
    }

    if (cartHasItems()) {
      stepIdx = 1;
    }
    paint();
    scheduleAuto();
  }

  function init() {
    mount();
    if (!root || readDismissed()) {
      /* still wire listeners for WA hint if remounted */
    }

    document.addEventListener("cf-demo-cart-updated", function () {
      if (cartHasItems()) {
        bumpMin(1);
      }
    });

    document.addEventListener("cartflow-demo-bubble-visible", function () {
      bumpMin(1);
    });

    document.addEventListener("cartflow-demo-reason-list-visible", function () {
      bumpMin(2);
    });

    document.addEventListener("cartflow-demo-reason-confirmed", function (ev) {
      var d = (ev && ev.detail) || {};
      bumpMin(3);
      showWaHint(d);
    });

    document.addEventListener("cf-demo-replay-reset", function () {
      try {
        window.sessionStorage.removeItem(DISMISS_KEY);
      } catch (e) {
        /* ignore */
      }
      stepIdx = cartHasItems() ? 1 : 0;
      clearAuto();
      if (waHint) {
        clearTimeout(waHint._hideT);
        waHint.setAttribute("hidden", "");
        waHint.style.opacity = "";
        waHint.style.transform = "";
      }
      if (root) {
        root.removeAttribute("hidden");
        paint();
        scheduleAuto();
      } else {
        mount();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
