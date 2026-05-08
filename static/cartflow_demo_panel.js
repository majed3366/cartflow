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

  var demoScenarioActive = false;
  window.cartflowDemoIsScenarioActive = function () {
    return demoScenarioActive;
  };
  window.cartflowDemoSetScenarioActive = function (v) {
    demoScenarioActive = !!v;
  };

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

  function demoSetTrackingCartId(cid) {
    var c = (cid != null ? String(cid).trim() : "") || "";
    if (!c) {
      return;
    }
    try {
      window.sessionStorage.setItem("cartflow_cart_event_id", c.slice(0, 255));
    } catch (e) {
      /* ignore */
    }
  }

  function demoCartIdForRecoverySession(session) {
    var s = session != null ? String(session).trim() : "";
    if (!s || s === "—") {
      return "";
    }
    return s.slice(0, 220) + "_demo_cart";
  }

  function cfDemoSumCartTotals(arr) {
    if (!arr || !Array.isArray(arr)) {
      return 0;
    }
    var sum = 0;
    var anyRow = false;
    var i;
    var row;
    var p;
    var pr;
    var qRaw;
    var q;
    for (i = 0; i < arr.length; i++) {
      row = arr[i];
      if (!row || typeof row !== "object") {
        continue;
      }
      p = row.price != null ? row.price : row.unit_price != null ? row.unit_price : null;
      if (p == null) {
        p = row.amount != null ? row.amount : row.total;
      }
      if (p == null) {
        continue;
      }
      pr = typeof p === "number" ? p : parseFloat(String(p));
      if (isNaN(pr)) {
        continue;
      }
      qRaw =
        row.quantity != null ? row.quantity : row.qty != null ? row.qty : 1;
      q = typeof qRaw === "number" ? qRaw : parseFloat(String(qRaw));
      if (isNaN(q) || q < 0) {
        q = 1;
      }
      sum += pr * q;
      anyRow = true;
    }
    return anyRow ? sum : 0;
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
  var _pendingDemoScheduled = null;

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
          if (_pendingDemoScheduled) {
            setText("cf-demo-last-status", "scheduled");
            setText("cf-demo-queue", _pendingDemoScheduled.queue);
            setText("cf-demo-last-wa", _pendingDemoScheduled.wa);
            setText("cf-demo-current-step", "pending (sequence running)");
            setText("cf-demo-recovery-message", _pendingDemoScheduled.msg);
          } else {
            setText("cf-demo-last-status", "—");
            setText("cf-demo-queue", "—");
            setText("cf-demo-last-wa", "—");
            setText("cf-demo-current-step", "—");
            setText("cf-demo-recovery-message", "—");
          }
        } else {
          if (_pendingDemoScheduled) {
            _pendingDemoScheduled = null;
          }
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
        } else if (logs && logs.length === 0 && _pendingDemoScheduled) {
          /* recovery line already set with pending state */
        } else {
          setText("cf-demo-recovery-message", "—");
        }
      })
      .catch(function () {
        setText("cf-demo-last-status", "error");
      });
  }

  function logDemo() {
    var args = ["[cartflow demo]"].concat(
      Array.prototype.slice.call(arguments)
    );
    try {
      console.log.apply(console, args);
    } catch (e) {
      /* ignore */
    }
  }

  function postJson(url, body) {
    return fetch(api(url), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r
          .json()
          .then(
            function (j) {
              return { ok: r.ok, status: r.status, body: j != null ? j : {} };
            },
            function () {
              return { ok: r.ok, status: r.status, body: {} };
            }
          );
      })
      .catch(function (err) {
        logDemo("postJson fetch error", err);
        return { ok: false, status: 0, body: { _fetch_error: String(err) } };
      });
  }

  function attachCfTestPhoneToBody(body) {
    if (!body || typeof body !== "object") {
      return body;
    }
    try {
      if (typeof window.cartflowReadCfTestCustomerPhone === "function") {
        var t = window.cartflowReadCfTestCustomerPhone();
        if (t) {
          body.cf_test_phone = String(t).trim().slice(0, 100);
        }
      }
    } catch (eCf) {
      /* ignore */
    }
    return body;
  }

  function getFirstStepMessage() {
    if (sequenceSteps[0] && sequenceSteps[0].message) {
      return String(sequenceSteps[0].message);
    }
    return "—";
  }

  function applyPanelFromScheduledResponse(demoRes) {
    var sec =
      demoRes && demoRes.recovery_delay_seconds != null
        ? String(demoRes.recovery_delay_seconds)
        : "—";
    var msg = getFirstStepMessage();
    _pendingDemoScheduled = {
      queue: "queued (delay " + sec + "s) — DB will update when sequence runs",
      msg: msg,
      wa: msg,
    };
    setText("cf-demo-last-status", "scheduled");
    setText("cf-demo-queue", _pendingDemoScheduled.queue);
    setText("cf-demo-last-wa", _pendingDemoScheduled.wa);
    setText("cf-demo-current-step", "pending (sequence running)");
    setText("cf-demo-recovery-message", msg);
  }

  function applyPanelFromSkippedResponseIfBlank(demoRes) {
    if (!demoRes || !demoRes.recovery_skipped) {
      return;
    }
    var n = el("cf-demo-last-status");
    var t = n && n.textContent ? n.textContent.trim() : "—";
    if (t !== "—" && t !== "" && t !== "error") {
      return;
    }
    if (demoRes.recovery_state === "converted") {
      setText("cf-demo-last-status", "skipped_converted");
      setText("cf-demo-queue", "recovery_skipped (converted on server)");
      return;
    }
    if (demoRes.recovery_state === "sent") {
      setText("cf-demo-last-status", "skipped_delay");
    }
    if (demoRes.recovery_state === "pending") {
      setText("cf-demo-last-status", "skipped_duplicate");
    }
  }

  function pollPanelRefresh(attempt) {
    var max = 8;
    if (attempt >= max) {
      return;
    }
    setTimeout(function () {
      void refresh();
      pollPanelRefresh(attempt + 1);
    }, 450 * (1 + attempt));
  }

  function triggerAbandon() {
    if (isClientConverted()) {
      logDemo("trigger blocked: sessionStorage", CARTFLOW_CONVERTED_KEY, "=1");
      setText("cf-demo-last-status", "blocked_converted");
      setText("cf-demo-queue", "Use “Reset demo session” or clear cartflow_converted to retest");
      setText("cf-demo-recovery-message", "—");
      return Promise.resolve();
    }
    if (typeof window.cart === "undefined" || !window.cart) {
      window.cart = [];
    }
    if (!Array.isArray(window.cart) || window.cart.length === 0) {
      window.cart.push({ name: "Demo line item", price: 1 });
    }
    var store = getStoreSlug();
    var session = getSessionId();
    logDemo("Trigger abandoned cart clicked");
    logDemo("cart length", window.cart.length, "store_slug", store, "session_id", session);
    if (!session || session === "—") {
      logDemo("abandon aborted: no session_id");
      setText("cf-demo-last-status", "error_no_session");
      return Promise.resolve();
    }
    var cartId = demoCartIdForRecoverySession(session);
    demoSetTrackingCartId(cartId);
    var body = attachCfTestPhoneToBody({
      event: "cart_abandoned",
      store: store,
      session_id: session,
      cart_id: cartId,
      cart: window.cart,
    });
    return postJson("/api/cart-event", body)
      .then(function (res) {
        var j = (res && res.body) || {};
        logDemo("API response", { httpOk: res.ok, status: res.status, body: j });
        if (!res.ok) {
          setText("cf-demo-last-status", "http_error_" + (res.status || 0));
          return refresh();
        }
        if (j.recovery_scheduled) {
          demoScenarioActive = true;
          if (typeof window.cartflowMarkRecoveryFlowStarted === "function") {
            window.cartflowMarkRecoveryFlowStarted();
          }
          if (typeof window.cartflowDemoArmStoreWidget === "function") {
            window.cartflowDemoArmStoreWidget();
          }
          if (!sequenceSteps || sequenceSteps.length === 0) {
            return loadSequence().then(function () {
              applyPanelFromScheduledResponse(j);
              pollPanelRefresh(0);
              nudgeWidgetIdle();
              return refresh();
            });
          }
          applyPanelFromScheduledResponse(j);
          pollPanelRefresh(0);
          nudgeWidgetIdle();
          return refresh();
        }
        _pendingDemoScheduled = null;
        demoScenarioActive = false;
        return refresh().then(function () {
          applyPanelFromSkippedResponseIfBlank(j);
        });
      });
  }

  function nudgeWidgetIdle() {
    try {
      document.documentElement.dispatchEvent(
        new MouseEvent("click", { bubbles: true, cancelable: true })
      );
    } catch (e) {
      try {
        var ev = document.createEvent("MouseEvents");
        ev.initEvent("click", true, true);
        document.documentElement.dispatchEvent(ev);
      } catch (e2) {
        /* ignore */
      }
    }
  }

  function newDemoSessionId() {
    if (typeof window.crypto !== "undefined" && window.crypto.randomUUID) {
      return "s_" + window.crypto.randomUUID();
    }
    return "s_" + String(Date.now()) + "_" + String(Math.random());
  }

  function clearStateForStartScenario() {
    _pendingDemoScheduled = null;
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
      window.sessionStorage.removeItem("cartflow_recovery_flow_started");
      window.sessionStorage.removeItem("cartflow_return_tracker_dedupe");
      window.sessionStorage.removeItem("cartflow_cart_event_id");
      if (typeof window.cartflowClearDurableRecoveryReturnState === "function") {
        window.cartflowClearDurableRecoveryReturnState();
      }
    } catch (e) {
      /* ignore */
    }
    var newSid = newDemoSessionId();
    if (typeof window.cartflowResetRecoverySessionIdForDemo === "function") {
      window.cartflowResetRecoverySessionIdForDemo(newSid);
    } else {
      try {
        window.sessionStorage.setItem(CARTFLOW_SESSION_KEY, newSid);
      } catch (e) {
        /* ignore */
      }
    }
  }

  function startDemoScenario() {
    if (isClientConverted()) {
      setClientConverted(false);
    }
    logDemo("Start Demo Scenario clicked");
    demoScenarioActive = true;
    clearStateForStartScenario();
    var pick = null;
    if (window.CF_DEMO_PRODUCTS) {
      pick = window.CF_DEMO_PRODUCTS.earbuds || window.CF_DEMO_PRODUCTS.hoodie;
    }
    if (!pick) {
      pick = { name: "CartFlow demo item", price: 1, description: "—" };
    } else {
      pick = Object.assign({}, pick);
    }
    if (typeof window.cartflowDemoSetCart === "function") {
      window.cartflowDemoSetCart([pick]);
    } else {
      if (typeof window.cart === "undefined" || !window.cart) {
        window.cart = [];
      }
      window.cart = [pick];
      try {
        var k = window.CARTFLOW_DEMO_CART_KEY || "demo_cart";
        localStorage.setItem(k, JSON.stringify(window.cart));
      } catch (e) {
        /* ignore */
      }
    }
    logDemo(
      "Start scenario — cart length",
      window.cart.length,
      "store_slug",
      getStoreSlug(),
      "session_id",
      getSessionId()
    );
    return loadSequence()
      .then(function () {
        var store = getStoreSlug();
        var session = getSessionId();
        if (!session || session === "—") {
          setText("cf-demo-last-status", "error_no_session");
          return { ok: false, status: 0, body: { _aborted: true } };
        }
        var cartIdRow = demoCartIdForRecoverySession(session);
        demoSetTrackingCartId(cartIdRow);
        var body = attachCfTestPhoneToBody({
          event: "cart_abandoned",
          store: store,
          session_id: session,
          cart_id: cartIdRow,
          cart_total: (function () {
            var cartArr =
              typeof window.cart !== "undefined" && window.cart != null && Array.isArray(window.cart)
                ? window.cart
                : [];
            var t = cfDemoSumCartTotals(cartArr);
            return t > 0 ? t : 1200;
          })(),
          cart: window.cart,
        });
        return postJson("/api/cart-event", body);
      })
      .then(function (res) {
        if (res && res.body && res.body._aborted) {
          demoScenarioActive = false;
          return;
        }
        var j = (res && res.body) || {};
        logDemo("API response (Start Demo Scenario)", {
          httpOk: res.ok,
          status: res.status,
          body: j,
        });
        if (!res || !res.ok) {
          demoScenarioActive = false;
          setText("cf-demo-last-status", "http_error_" + (res.status || 0));
          return refresh();
        }
        if (j.recovery_scheduled) {
          demoScenarioActive = true;
          if (typeof window.cartflowMarkRecoveryFlowStarted === "function") {
            window.cartflowMarkRecoveryFlowStarted();
          }
          if (typeof window.cartflowDemoArmStoreWidget === "function") {
            window.cartflowDemoArmStoreWidget();
          }
          if (!sequenceSteps || sequenceSteps.length === 0) {
            return loadSequence().then(function () {
              applyPanelFromScheduledResponse(j);
              pollPanelRefresh(0);
              nudgeWidgetIdle();
              showRecoveryMessageForStep(1);
              return refresh();
            });
          }
          applyPanelFromScheduledResponse(j);
          pollPanelRefresh(0);
          nudgeWidgetIdle();
          showRecoveryMessageForStep(1);
          return refresh();
        }
        _pendingDemoScheduled = null;
        demoScenarioActive = false;
        return refresh()
          .then(function () {
            applyPanelFromSkippedResponseIfBlank(j);
            showRecoveryMessageForStep(1);
          });
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
    }).then(function (res) {
      var j = (res && res.body) || {};
      if (j && j.ok) {
        setClientConverted(true);
        if (typeof window.cartflowClearDurableRecoveryReturnState === "function") {
          window.cartflowClearDurableRecoveryReturnState();
        }
      }
      logDemo("API response (conversion)", { httpOk: res.ok, status: res.status, body: j });
      return refresh();
    });
  }

  function resetDemoSession() {
    demoScenarioActive = false;
    _pendingDemoScheduled = null;
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
      window.sessionStorage.removeItem("cartflow_demo_store_widget_armed");
      window.sessionStorage.removeItem("cartflow_recovery_flow_started");
      window.sessionStorage.removeItem("cartflow_return_tracker_dedupe");
      window.sessionStorage.removeItem("cartflow_cart_event_id");
      if (typeof window.cartflowClearDurableRecoveryReturnState === "function") {
        window.cartflowClearDurableRecoveryReturnState();
      }
    } catch (e) {
      /* ignore */
    }
    var newSid = newDemoSessionId();
    if (typeof window.cartflowResetRecoverySessionIdForDemo === "function") {
      window.cartflowResetRecoverySessionIdForDemo(newSid);
    } else {
      try {
        window.sessionStorage.setItem(CARTFLOW_SESSION_KEY, newSid);
      } catch (e) {
        /* ignore */
      }
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

  window.cartflowStartDemoScenario = startDemoScenario;

  function wire() {
    var b;
    b = el("cf-btn-start-scenario");
    if (b) b.addEventListener("click", function () { void startDemoScenario(); });
    b = el("cf-btn-start-in-panel");
    if (b) b.addEventListener("click", function () { void startDemoScenario(); });
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
    if (el("cf-demo-panel")) {
      loadSequence().then(function () {
        return refresh();
      });
    }
    wire();
  }
})();
