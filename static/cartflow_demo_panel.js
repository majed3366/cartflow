/**
 * CartFlow demo panel — /demo/store/cart, /demo/cart, /demo/store2/cart only.
 * Does not load on production widget pages.
 */
(function () {
  "use strict";

  var CARTFLOW_SESSION_KEY = "cartflow_recovery_session_id";
  var CARTFLOW_CONVERTED_KEY = "cartflow_converted";
  var REASON_TAG_KEY = "cartflow_reason_tag";
  var REASON_SUB_TAG_KEY = "cartflow_reason_sub_tag";

  function getStoreSlug() {
    if (typeof window.CARTFLOW_STORE_SLUG === "string" && window.CARTFLOW_STORE_SLUG.trim()) {
      return window.CARTFLOW_STORE_SLUG.trim();
    }
    return "demo";
  }

  function getSessionId() {
    if (typeof window.cartflowGetSessionId === "function") {
      return window.cartflowGetSessionId();
    }
    try {
      var s = window.sessionStorage.getItem(CARTFLOW_SESSION_KEY);
      return s || "—";
    } catch (e) {
      return "—";
    }
  }

  function api(path) {
    return path;
  }

  function el(id) {
    return document.getElementById(id);
  }

  function setText(id, s) {
    var n = el(id);
    if (n) n.textContent = s != null ? String(s) : "—";
  }

  var sequenceSteps = [];

  function loadSequence() {
    return fetch(api("/demo/cartflow/sequence"))
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j && j.ok && j.steps) {
          sequenceSteps = j.steps;
        }
      })
      .catch(function () {
        sequenceSteps = [];
      });
  }

  function showRecoveryMessageForStep(n) {
    var i;
    for (i = 0; i < sequenceSteps.length; i++) {
      if (sequenceSteps[i] && Number(sequenceSteps[i].step) === n) {
        setText("cf-demo-recovery-message", sequenceSteps[i].message || "—");
        setText("cf-demo-current-step", String(n));
        return;
      }
    }
    setText("cf-demo-recovery-message", "—");
  }

  function isClientConverted() {
    try {
      return window.sessionStorage.getItem(CARTFLOW_CONVERTED_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function setClientConverted(v) {
    try {
      if (v) {
        window.sessionStorage.setItem(CARTFLOW_CONVERTED_KEY, "1");
      } else {
        window.sessionStorage.removeItem(CARTFLOW_CONVERTED_KEY);
      }
    } catch (e) {
      /* ignore */
    }
  }

  function refresh() {
    var store = getStoreSlug();
    var session = getSessionId();
    setText("cf-demo-store", store);
    setText("cf-demo-session", session);
    if (isClientConverted()) {
      setText("cf-demo-conversion", "converted");
    } else {
      setText("cf-demo-conversion", "not marked");
    }

    var u =
      api("/demo/cartflow/logs") +
      "?store_slug=" +
      encodeURIComponent(store) +
      "&session_id=" +
      encodeURIComponent(session);
    return fetch(u)
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        var last = null;
        if (!j || !j.ok) {
          setText("cf-demo-last-status", "—");
          setText("cf-demo-queue", "—");
          setText("cf-demo-last-wa", "—");
          return;
        }
        var logs = j.logs || [];
        if (logs.length === 0) {
          setText("cf-demo-last-status", "—");
          setText("cf-demo-queue", "—");
          setText("cf-demo-last-wa", "—");
          setText("cf-demo-current-step", "—");
        } else {
          last = logs[0];
          setText("cf-demo-last-status", last.status != null ? last.status : "—");
          setText("cf-demo-queue", last.status || "—");
          setText("cf-demo-last-wa", last.message || "—");
          if (last.step != null) {
            setText("cf-demo-current-step", String(last.step));
          } else {
            setText("cf-demo-current-step", "—");
          }
          if (last.status === "stopped_converted") {
            setText("cf-demo-conversion", "converted");
          }
        }
        var list = el("cf-demo-logs");
        if (list) {
          list.innerHTML = "";
          logs.forEach(function (row) {
            var li = document.createElement("li");
            li.appendChild(
              document.createTextNode(
                (row.created_at || "") +
                  " step=" +
                  (row.step != null ? row.step : "—") +
                  " [" +
                  (row.status || "") +
                  "] " +
                  (row.message || "").slice(0, 80)
              )
            );
            list.appendChild(li);
          });
        }
        if (last && last.message) {
          setText("cf-demo-recovery-message", last.message);
        } else {
          setText("cf-demo-recovery-message", "—");
        }
      })
      .catch(function () {
        setText("cf-demo-last-status", "error");
      });
  }

  function postJson(url, body) {
    return fetch(api(url), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json();
    });
  }

  function triggerAbandon() {
    try {
      if (window.sessionStorage.getItem(CARTFLOW_CONVERTED_KEY) === "1") {
        console.log("cartflow demo: skip cart-event (converted)");
        return Promise.resolve();
      }
    } catch (e) {
      /* ignore */
    }
    if (typeof window.cart === "undefined" || !window.cart) {
      window.cart = [];
    }
    if (!Array.isArray(window.cart) || window.cart.length === 0) {
      window.cart.push({ name: "Demo line item", price: 1 });
    }
    return postJson("/api/cart-event", {
      event: "cart_abandoned",
      store: getStoreSlug(),
      session_id: getSessionId(),
      cart: window.cart,
    }).then(function (j) {
      console.log("cartflow demo abandon", j);
      return refresh();
    });
  }

  function triggerConversion() {
    var sid = getSessionId();
    if (!sid || sid === "—") {
      setText("cf-demo-conversion", "no session");
      return Promise.resolve();
    }
    return postJson("/api/conversion", {
      store_slug: getStoreSlug(),
      session_id: sid,
      purchase_completed: true,
    })
      .then(function (j) {
        if (j && j.ok) {
          setClientConverted(true);
        }
        console.log("cartflow demo conversion", j);
        return refresh();
      })
      .catch(function (e) {
        console.log(e);
        return refresh();
      });
  }

  function resetDemoSession() {
    var cartKey =
      typeof window.CARTFLOW_DEMO_CART_KEY === "string" &&
      window.CARTFLOW_DEMO_CART_KEY.trim()
        ? String(window.CARTFLOW_DEMO_CART_KEY).trim()
        : "demo_cart";
    try {
      localStorage.removeItem(cartKey);
    } catch (e) {
      /* ignore */
    }
    try {
      window.sessionStorage.removeItem(REASON_TAG_KEY);
      window.sessionStorage.removeItem(REASON_SUB_TAG_KEY);
      window.sessionStorage.removeItem(CARTFLOW_CONVERTED_KEY);
      window.sessionStorage.removeItem(CARTFLOW_SESSION_KEY);
    } catch (e) {
      /* ignore */
    }
    var newSid;
    if (typeof window.crypto !== "undefined" && window.crypto.randomUUID) {
      newSid = "s_" + window.crypto.randomUUID();
    } else {
      newSid = "s_" + String(Date.now()) + "_" + String(Math.random());
    }
    try {
      window.sessionStorage.setItem(CARTFLOW_SESSION_KEY, newSid);
    } catch (e) {
      /* ignore */
    }
    try {
      if (Array.isArray(window.cart)) {
        window.cart.length = 0;
      } else {
        window.cart = [];
      }
    } catch (e) {
      /* ignore */
    }
    try {
      location.reload();
    } catch (e) {
      /* ignore */
    }
  }

  function wire() {
    var b;
    b = el("cf-btn-reset-demo");
    if (b) b.addEventListener("click", function () { resetDemoSession(); });
    b = el("cf-btn-abandon");
    if (b) b.addEventListener("click", function () { void triggerAbandon(); });
    b = el("cf-btn-s1");
    if (b) b.addEventListener("click", function () { showRecoveryMessageForStep(1); });
    b = el("cf-btn-s2");
    if (b) b.addEventListener("click", function () { showRecoveryMessageForStep(2); });
    b = el("cf-btn-s3");
    if (b) b.addEventListener("click", function () { showRecoveryMessageForStep(3); });
    b = el("cf-btn-convert");
    if (b) b.addEventListener("click", function () { void triggerConversion(); });
    b = el("cf-btn-refresh");
    if (b) b.addEventListener("click", function () { void refresh(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  function onReady() {
    if (!el("cf-demo-panel")) {
      return;
    }
    loadSequence().then(function () {
      return refresh();
    });
    wire();
  }
})();
