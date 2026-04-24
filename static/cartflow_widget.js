/**
 * CartFlow — minimal cart helper bubble (no framework, no backend).
 * Injects after 3s; on /cart/* only; shows after 8s inactivity.
 */
(function () {
  "use strict";

  var ARM_DELAY_MS = 3000;
  var IDLE_MS = 8000;
  var shown = false;
  var idleTimer = null;
  var events = ["mousemove", "keydown", "scroll", "click", "touchstart"];

  function isCartPage() {
    return /\/cart/i.test(window.location.pathname + window.location.search);
  }

  function postObjection(type) {
    var base = (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
    var url = base ? base + "/track/objection" : "/track/objection";
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: type }),
    }).catch(function () {});
  }

  function showBubble() {
    if (shown) return;
    shown = true;
    clearTimeout(idleTimer);
    events.forEach(function (e) {
      document.removeEventListener(e, resetIdle, true);
    });

    var w = document.createElement("div");
    w.setAttribute("dir", "rtl");
    w.setAttribute("lang", "ar");
    w.setAttribute("data-cartflow-bubble", "1");
    w.style.cssText =
      "position:fixed;right:12px;bottom:12px;z-index:2147483640;max-width:260px;" +
      "padding:10px 12px;border-radius:12px;background:#1e1b4b;color:#f5f3ff;" +
      "font:14px/1.4 system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.2);" +
      "pointer-events:auto;touch-action:manipulation;isolation:isolate;";

    var btnStyle =
      "cursor:pointer;border:0;border-radius:8px;padding:6px 14px;font:inherit;" +
      "font-weight:600;background:#7c3aed;color:#fff;";

    // إيقاف الانتشار فقط لنقرة مباشرة على الحاوية — لا تُلغى نقرات الأبناء
    w.addEventListener("click", function (ev) {
      if (ev.target === w) {
        ev.stopPropagation();
      }
    }, false);

    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 8px 0;";
    p.textContent = "تبغى أساعدك تكمل طلبك؟ 👋";

    var row0 = document.createElement("div");
    row0.style.cssText =
      "display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-start;margin-top:2px;";

    var btnYes = document.createElement("button");
    btnYes.type = "button";
    btnYes.textContent = "نعم";
    btnYes.setAttribute("aria-label", "نعم");
    btnYes.style.cssText = btnStyle;

    var btnNo = document.createElement("button");
    btnNo.type = "button";
    btnNo.textContent = "لا";
    btnNo.setAttribute("aria-label", "لا");
    btnNo.style.cssText = btnStyle;
    btnNo.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      if (w && w.parentNode) {
        w.parentNode.removeChild(w);
      }
    });

    // مستمع ‎نعم‎ — تتابع نفس تدفق الاعتراض
    btnYes.addEventListener(
      "click",
      function onYes(ev) {
        if (w.getAttribute("data-cf-yes") === "1") return;
        w.setAttribute("data-cf-yes", "1");
        ev.stopPropagation();
        ev.preventDefault();
        console.log("user_interested");
        while (w.lastChild) {
          w.removeChild(w.lastChild);
        }
        var p2 = document.createElement("p");
        p2.id = "cf-objection-msg";
        p2.style.cssText = "margin:0 0 8px 0;";
        p2.textContent = "تمام 👌 وش أكثر شيء متردد فيه؟";
        w.appendChild(p2);
        var row = document.createElement("div");
        row.style.cssText =
          "display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;";
        var bPrice = document.createElement("button");
        bPrice.id = "cf-price-btn";
        bPrice.type = "button";
        bPrice.textContent = "السعر";
        bPrice.style.cssText = btnStyle;
        var bQ = document.createElement("button");
        bQ.id = "cf-quality-btn";
        bQ.type = "button";
        bQ.textContent = "الجودة";
        bQ.style.cssText = btnStyle;
        row.appendChild(bPrice);
        row.appendChild(bQ);
        w.appendChild(row);

        var objectionDone = false;
        function hideObjectionButtons() {
          if (row && row.parentNode) {
            row.parentNode.removeChild(row);
          }
        }

        const priceBtn = document.getElementById("cf-price-btn");
        const qualityBtn = document.getElementById("cf-quality-btn");
        if (priceBtn) {
          priceBtn.addEventListener("click", function () {
            if (objectionDone) {
              return;
            }
            objectionDone = true;
            console.log("objection_price");
            postObjection("price");
            // 1) وِجه فقط — بلا خصم
            p2.textContent =
              "أفهمك 👌 كثير يهتمون بالسعر… لكن غالبًا اللي ياخذونه يرجعون له مرة ثانية لأنه فعلاً يستاهل قيمته.";
            hideObjectionButtons();
            // 2–4) ‎6–8‎ ث: إن بقي مستخدماً بلا ‎move/scroll‎ — رسالة تالية (بدون خصم بعد)
            var delayMs = 6000 + Math.floor(Math.random() * 2001);
            var followText =
              "لو حاب، أقدر أعطيك كود بسيط يساعدك تبدأ 🙌";
            var priceIdleTid = null;
            function clearPriceFollowUp() {
              if (priceIdleTid !== null) {
                clearTimeout(priceIdleTid);
                priceIdleTid = null;
              }
              document.removeEventListener("mousemove", onPriceActivity, true);
              window.removeEventListener("scroll", onPriceActivity, true);
            }
            function onPriceActivity() {
              clearPriceFollowUp();
            }
            function showFollowIfStillIdle() {
              clearPriceFollowUp();
              if (!p2 || !w || !w.parentNode) {
                return;
              }
              p2.textContent = followText;
              var rowFollow = document.createElement("div");
              rowFollow.style.cssText =
                "display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;";
              var fNo = document.createElement("button");
              fNo.type = "button";
              fNo.textContent = "لا";
              fNo.style.cssText = btnStyle;
              fNo.addEventListener("click", function (ev) {
                ev.stopPropagation();
                if (w && w.parentNode) {
                  w.parentNode.removeChild(w);
                }
              });
              var fYes = document.createElement("button");
              fYes.type = "button";
              fYes.textContent = "نعم";
              fYes.style.cssText = btnStyle;
              fYes.addEventListener("click", function (ev) {
                ev.stopPropagation();
                if (rowFollow && rowFollow.parentNode) {
                  rowFollow.parentNode.removeChild(rowFollow);
                }
                p2.textContent = "هذا كودك: SAVE10";
                var copyBtn = document.createElement("button");
                copyBtn.type = "button";
                copyBtn.textContent = "نسخ الكود";
                copyBtn.style.cssText = btnStyle;
                copyBtn.addEventListener("click", function (e) {
                  e.stopPropagation();
                  function onCopySuccess() {
                    copyBtn.textContent = "تم النسخ ✅";
                    console.log("coupon_copied");
                  }
                  function fallbackCopy() {
                    var inp = document.createElement("input");
                    inp.setAttribute("type", "text");
                    inp.value = "SAVE10";
                    inp.setAttribute("readonly", "");
                    inp.style.cssText = "position:fixed;left:-9999px;opacity:0";
                    document.body.appendChild(inp);
                    inp.select();
                    inp.setSelectionRange(0, 99999);
                    try {
                      if (document.execCommand("copy")) {
                        onCopySuccess();
                      }
                    } catch (err) {}
                    if (inp.parentNode) {
                      document.body.removeChild(inp);
                    }
                  }
                  if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard
                      .writeText("SAVE10")
                      .then(function () {
                        onCopySuccess();
                      })
                      .catch(function () {
                        fallbackCopy();
                      });
                  } else {
                    fallbackCopy();
                  }
                });
                w.appendChild(copyBtn);
              });
              rowFollow.appendChild(fYes);
              rowFollow.appendChild(fNo);
              w.appendChild(rowFollow);
            }
            priceIdleTid = setTimeout(showFollowIfStillIdle, delayMs);
            document.addEventListener("mousemove", onPriceActivity, true);
            window.addEventListener("scroll", onPriceActivity, true);
          });
        }
        if (qualityBtn) {
          qualityBtn.addEventListener("click", function () {
            if (objectionDone) {
              return;
            }
            objectionDone = true;
            console.log("objection_quality");
            postObjection("quality");
            p2.textContent =
              "واضح إنك تهتم بالجودة 👍 وهذا اختيار ذكي… المنتج هذا من أكثر الأشياء اللي الناس ترجع تشتريه بسبب جودته.";
            hideObjectionButtons();
          });
        }
      },
      false
    );

    row0.appendChild(btnYes);
    row0.appendChild(btnNo);
    w.appendChild(p);
    w.appendChild(row0);
    document.body.appendChild(w);
  }

  function resetIdle() {
    if (shown) return;
    clearTimeout(idleTimer);
    idleTimer = setTimeout(showBubble, IDLE_MS);
  }

  function arm() {
    if (!isCartPage()) return;
    events.forEach(function (e) {
      document.addEventListener(e, resetIdle, true);
    });
    resetIdle();
  }

  setTimeout(arm, ARM_DELAY_MS);
})();
