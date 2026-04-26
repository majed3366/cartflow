/**
 * CartFlow — عرض سبب التردد بعد ‎step1‎ استرجاع (بلا مزوّد واتساب في الودجت).
 * ‎/demo/‎: يتخطّى انتظار ‎step1‎ (تجارب). باقي المسارات: حتى ‎GET /api/cartflow/ready‎.
 */
(function () {
  "use strict";

  var ARM_DELAY_MS = 3000;
  var IDLE_MS = 8000;
  var REASON_TAG_KEY = "cartflow_reason_tag";
  var shown = false;
  var idleTimer = null;
  var step1Ready = false;
  var step1Poll = null;
  var events = ["mousemove", "keydown", "scroll", "click", "touchstart"];

  var REASON_REPLIES = {
    price:
      "أفهمك، السعر مهم. المنتج قيمته مقابل الجودة والاستخدام، وإذا تحب أقدر أساعدك بخيار أنسب.",
    quality:
      "أكيد الجودة مهمة. المنتج مختار بعناية، وتقدر تطمئن من التفاصيل والتقييمات قبل الشراء.",
    warranty:
      "الضمان مهم خصوصًا للأجهزة. تقدر تتأكد من سياسة الضمان، وإذا تبغى أساعدك أو أوصلك بالمتجر.",
    shipping:
      "الشحن مهم. تقدر تتأكد من مدة الشحن والتوصيل قبل إكمال الطلب.",
    thinking:
      "خذ وقتك، وإذا احتجت مقارنة أو توضيح أنا هنا أساعدك.",
  };

  function isSessionConverted() {
    try {
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (e) {
      return false;
    }
  }

  function isCartPage() {
    return /\/cart/i.test(window.location.pathname + window.location.search);
  }

  function getStoreSlug() {
    if (
      typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
      window.CARTFLOW_STORE_SLUG !== null &&
      String(window.CARTFLOW_STORE_SLUG).trim() !== ""
    ) {
      return String(window.CARTFLOW_STORE_SLUG).trim();
    }
    return "demo";
  }

  function getSessionId() {
    if (typeof window.cartflowGetSessionId === "function") {
      return window.cartflowGetSessionId();
    }
    return "—";
  }

  function setReasonTag(tag) {
    try {
      if (tag) {
        window.sessionStorage.setItem(REASON_TAG_KEY, String(tag));
      }
    } catch (e) {
      /* ignore */
    }
  }

  if (typeof window.cartflowGetReasonTag !== "function") {
    window.cartflowGetReasonTag = function () {
      try {
        return window.sessionStorage.getItem(REASON_TAG_KEY) || null;
      } catch (e) {
        return null;
      }
    };
  }

  function haveCartForWidget() {
    if (isSessionConverted()) {
      return false;
    }
    var p = (window.location.pathname || "") + (window.location.search || "");
    if (p.indexOf("/demo/") < 0) {
      return true;
    }
    if (typeof window.cart === "undefined" || window.cart === null) {
      return false;
    }
    if (!Array.isArray(window.cart)) {
      return false;
    }
    return window.cart.length > 0;
  }

  function apiBase() {
    return (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
  }

  function postReason(payload) {
    var url = apiBase() ? apiBase() + "/api/cartflow/reason" : "/api/cartflow/reason";
    var body = {
      store_slug: getStoreSlug(),
      session_id: getSessionId(),
      reason: payload.reason,
    };
    if (payload.custom_text != null && String(payload.custom_text) !== "") {
      body.custom_text = String(payload.custom_text);
    }
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) {
          return { ok: false, status: r.status, body: j };
        }
        return j;
      });
    });
  }

  function isDemoPath() {
    var p = (window.location.pathname || "") + (window.location.search || "");
    return /\/demo\//i.test(p);
  }

  function fetchReadyThen(cb) {
    if (isDemoPath()) {
      step1Ready = true;
      cb();
      return;
    }
    var b = apiBase();
    var u =
      (b || "") +
      "/api/cartflow/ready" +
      "?store_slug=" +
      encodeURIComponent(getStoreSlug()) +
      "&session_id=" +
      encodeURIComponent(getSessionId());
    fetch(u, { method: "GET" })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j && j.after_step1) {
          step1Ready = true;
          if (step1Poll !== null) {
            clearInterval(step1Poll);
            step1Poll = null;
          }
          cb();
        }
      })
      .catch(function () {});
  }

  function ensureStep1ThenStartIdle() {
    if (step1Ready) {
      resetIdle();
      return;
    }
    fetchReadyThen(function () {
      if (!shown) {
        resetIdle();
      }
    });
    if (step1Poll === null) {
      step1Poll = setInterval(function () {
        if (shown) {
          if (step1Poll !== null) {
            clearInterval(step1Poll);
            step1Poll = null;
          }
          return;
        }
        fetchReadyThen(function () {
          if (step1Ready && !shown) {
            resetIdle();
          }
        });
      }, 5000);
    }
  }

  var btnStyle =
    "cursor:pointer;border:0;border-radius:8px;padding:6px 14px;font:inherit;" +
    "font-weight:600;background:#7c3aed;color:#fff;";

  function showBubble() {
    if (isSessionConverted() || !step1Ready) {
      return;
    }
    if (shown) {
      return;
    }
    if (!haveCartForWidget()) {
      return;
    }
    shown = true;
    if (step1Poll !== null) {
      clearInterval(step1Poll);
      step1Poll = null;
    }
    clearTimeout(idleTimer);
    events.forEach(function (e) {
      document.removeEventListener(e, resetIdle, true);
    });

    var w = document.createElement("div");
    w.setAttribute("dir", "rtl");
    w.setAttribute("lang", "ar");
    w.setAttribute("data-cartflow-bubble", "1");
    w.style.cssText =
      "position:fixed;right:12px;bottom:12px;z-index:2147483640;max-width:300px;" +
      "padding:10px 12px;border-radius:12px;background:#1e1b4b;color:#f5f3ff;" +
      "font:14px/1.4 system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.2);" +
      "pointer-events:auto;touch-action:manipulation;isolation:isolate;";

    w.addEventListener(
      "click",
      function (ev) {
        if (ev.target === w) {
          ev.stopPropagation();
        }
      },
      false
    );

    var p0 = document.createElement("p");
    p0.style.cssText = "margin:0 0 8px 0;";
    p0.textContent = "تبي أساعدك تكمل طلبك؟";

    var row0 = document.createElement("div");
    row0.style.cssText =
      "display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-start;margin-top:2px;";

    var btnY = document.createElement("button");
    btnY.type = "button";
    btnY.textContent = "نعم";
    btnY.style.cssText = btnStyle;

    var btnN = document.createElement("button");
    btnN.type = "button";
    btnN.textContent = "لا";
    btnN.style.cssText = btnStyle;
    btnN.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      if (w && w.parentNode) {
        w.parentNode.removeChild(w);
      }
    });

    function showReasonMessageOnly(text) {
      while (w.lastChild) {
        w.removeChild(w.lastChild);
      }
      var p = document.createElement("p");
      p.style.cssText = "margin:0;font-size:14px;line-height:1.55;";
      p.textContent = text;
      w.appendChild(p);
    }

    btnY.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      if (w.getAttribute("data-cf-yes") === "1") {
        return;
      }
      w.setAttribute("data-cf-yes", "1");
      while (w.lastChild) {
        w.removeChild(w.lastChild);
      }
      var p2 = document.createElement("p");
      p2.style.cssText = "margin:0 0 8px 0;";
      p2.textContent = "وش أكثر شيء مخليك متردد؟ تبيني أساعدك";
      w.appendChild(p2);
      var row = document.createElement("div");
      row.setAttribute("data-cf-reason-row", "1");
      row.style.cssText =
        "display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;max-height:220px;overflow-y:auto;";

      var options = [
        { label: "السعر", r: "price" },
        { label: "الجودة", r: "quality" },
        { label: "الضمان", r: "warranty" },
        { label: "الشحن", r: "shipping" },
        { label: "أفكر", r: "thinking" },
        { label: "سبب آخر", r: "_other" },
      ];

      function showStandardResponse(rkey) {
        setReasonTag(rkey);
        postReason({ reason: rkey })
          .then(function (j) {
            if (j && j.ok) {
              var msg = REASON_REPLIES[rkey] || "شكراً لملاحظتك.";
              showReasonMessageOnly(msg);
            }
          })
          .catch(function () {});
      }

      options.forEach(function (o) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = o.label;
        b.style.cssText = btnStyle;
        b.addEventListener("click", function (e) {
          e.stopPropagation();
          e.preventDefault();
          if (o.r === "_other") {
            while (w.lastChild) {
              w.removeChild(w.lastChild);
            }
            p2 = document.createElement("p");
            p2.style.cssText = "margin:0 0 8px 0;";
            p2.textContent = "اكتب السبب أو اطلب تحويلك لصاحب المتجر";
            w.appendChild(p2);
            var ta = document.createElement("textarea");
            ta.setAttribute("rows", "3");
            ta.setAttribute("placeholder", "…");
            ta.setAttribute("aria-label", "سبب آخر");
            ta.style.cssText =
              "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:8px;margin-bottom:8px;font:inherit;color:#1e1b4b;resize:vertical;min-height:3.5em;";
            w.appendChild(ta);
            var row2 = document.createElement("div");
            row2.style.cssText = "display:flex;flex-direction:column;gap:6px;margin-top:4px;";
            var bSend = document.createElement("button");
            bSend.type = "button";
            bSend.textContent = "إرسال السبب";
            bSend.style.cssText = btnStyle;
            bSend.addEventListener("click", function (e2) {
              e2.stopPropagation();
              e2.preventDefault();
              var t = (ta.value || "").trim();
              if (!t) {
                return;
              }
              bSend.setAttribute("disabled", "true");
              postReason({ reason: "other", custom_text: t })
                .then(function (j) {
                  if (j && j.ok) {
                    setReasonTag("other");
                    showReasonMessageOnly(
                      "تم تسجيل ملاحظتك، وبنحاول نساعدك بأفضل خيار."
                    );
                  } else {
                    bSend.removeAttribute("disabled");
                  }
                })
                .catch(function () {
                  bSend.removeAttribute("disabled");
                });
            });
            var bHandoff = document.createElement("button");
            bHandoff.type = "button";
            bHandoff.textContent = "تحويل لصاحب المتجر";
            bHandoff.style.cssText = btnStyle;
            bHandoff.addEventListener("click", function (e3) {
              e3.stopPropagation();
              e3.preventDefault();
              bHandoff.setAttribute("disabled", "true");
              postReason({ reason: "human_support" })
                .then(function (j) {
                  if (!(j && j.ok)) {
                    return null;
                  }
                  setReasonTag("human_support");
                  var bb = apiBase();
                  var cfgUrl =
                    (bb || "") +
                    "/api/cartflow/public-config" +
                    "?store_slug=" +
                    encodeURIComponent(getStoreSlug());
                  return fetch(cfgUrl, { method: "GET" });
                })
                .then(function (resp) {
                  if (!resp) {
                    return;
                  }
                  if (!resp.ok) {
                    return;
                  }
                  return resp.json();
                })
                .then(function (cfg) {
                  if (cfg && cfg.whatsapp_url) {
                    window.open(
                      cfg.whatsapp_url,
                      "_blank",
                      "noopener,noreferrer"
                    );
                  }
                })
                .catch(function () {})
                .then(function () {
                  bHandoff.removeAttribute("disabled");
                });
            });
            row2.appendChild(bSend);
            row2.appendChild(bHandoff);
            w.appendChild(row2);
          } else {
            showStandardResponse(o.r);
          }
        });
        row.appendChild(b);
      });
      w.appendChild(row);
    }, false);

    row0.appendChild(btnY);
    row0.appendChild(btnN);
    w.appendChild(p0);
    w.appendChild(row0);
    document.body.appendChild(w);
  }

  function resetIdle() {
    if (isSessionConverted() || !step1Ready) {
      return;
    }
    if (shown) {
      return;
    }
    clearTimeout(idleTimer);
    idleTimer = setTimeout(showBubble, IDLE_MS);
  }

  function arm() {
    if (isSessionConverted() || !isCartPage()) {
      return;
    }
    if (isDemoPath()) {
      step1Ready = true;
    }
    events.forEach(function (e) {
      document.addEventListener(e, resetIdle, true);
    });
    ensureStep1ThenStartIdle();
  }

  setTimeout(arm, ARM_DELAY_MS);
})();
