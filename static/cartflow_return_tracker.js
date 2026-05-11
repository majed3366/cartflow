/**
 * Return-to-site tracker — loaded by widget_loader (CartFlow runtime). Do not auto-run.
 * Dedupe: localStorage throttle cartflow_return_tracker_throttle_v1
 * State: localStorage cartflow_recovery_return_state_v1
 */
(function () {
  "use strict";

  var LS_KEY = "cartflow_recovery_return_state_v1";
  /** Cross-tab throttle; avoids blocking resend after reload / later revisit (pathname+SS dedupe was too strict). */
  var THROTTLE_LS_KEY = "cartflow_return_tracker_throttle_v1";
  var THROTTLE_MIN_MS = 45000;
  var CF_TEST_PHONE_LS = "cartflow_test_customer_phone";
  var SS_RECOVERY_FLOW = "cartflow_recovery_flow_started";
  var SS_SESSION_ID = "cartflow_recovery_session_id";
  var SS_CART_EVENT_ID = "cartflow_cart_event_id";
  var MODULE_VERSION = "return-tracker-runtime-v1";

  function apiCartEventUrl() {
    var base = (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
    return base ? base + "/api/cart-event" : "/api/cart-event";
  }

  function readJsonLs(key) {
    try {
      var raw = window.localStorage.getItem(key);
      if (!raw || !String(raw).trim()) {
        return null;
      }
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function isConverted() {
    try {
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (e) {
      return false;
    }
  }

  function inferReturnContext() {
    var path = (
      window.location && window.location.pathname
        ? String(window.location.pathname)
        : ""
    ).toLowerCase();
    if (path.indexOf("/checkout") !== -1) {
      return "checkout";
    }
    if (path.indexOf("/cart") !== -1) {
      return "cart";
    }
    if (path.indexOf("/product") !== -1) {
      return "product";
    }
    if (/\/store\/[^/]+\/[^/]+/.test(path)) {
      return "product";
    }
    return "page";
  }

  function pageStoreSlug() {
    try {
      if (
        typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
        window.CARTFLOW_STORE_SLUG !== null &&
        String(window.CARTFLOW_STORE_SLUG).trim() !== ""
      ) {
        return String(window.CARTFLOW_STORE_SLUG).trim();
      }
    } catch (e) {
      /* ignore */
    }
    return "";
  }

  function readCfTestPhone() {
    try {
      if (
        typeof window.__CARTFLOW_CF_TEST_PHONE === "string" &&
        window.__CARTFLOW_CF_TEST_PHONE.trim()
      ) {
        return String(window.__CARTFLOW_CF_TEST_PHONE).trim().slice(0, 100);
      }
    } catch (eW) {
      /* ignore */
    }
    try {
      var ls = window.localStorage.getItem(CF_TEST_PHONE_LS);
      if (ls != null && String(ls).trim()) {
        return String(ls).trim().slice(0, 100);
      }
    } catch (eLs) {
      /* ignore */
    }
    return "";
  }

  function readOptionalCustomerPhone() {
    try {
      if (
        typeof window.CARTFLOW_CUSTOMER_PHONE === "string" &&
        window.CARTFLOW_CUSTOMER_PHONE.trim()
      ) {
        return String(window.CARTFLOW_CUSTOMER_PHONE).trim().slice(0, 100);
      }
    } catch (eP) {
      /* ignore */
    }
    return "";
  }

  function validRecoveryState(o) {
    if (!o || o.v !== 1) {
      return false;
    }
    if (o.recovery_flow_started !== "1" && o.recovery_flow_started !== true) {
      return false;
    }
    if (!o.session_id || !String(o.session_id).trim()) {
      return false;
    }
    if (!o.cart_id || !String(o.cart_id).trim()) {
      return false;
    }
    return true;
  }

  /** When durable LS is empty but same-tab session still has recovery IDs (e.g. LS cleared). */
  function buildRecoveryStateFromSessionStorage() {
    try {
      if (isConverted()) {
        return null;
      }
      var flow = window.sessionStorage.getItem(SS_RECOVERY_FLOW) || "";
      if (flow !== "1") {
        return null;
      }
      var sid = window.sessionStorage.getItem(SS_SESSION_ID) || "";
      var cid = window.sessionStorage.getItem(SS_CART_EVENT_ID) || "";
      if (!String(sid).trim() || !String(cid).trim()) {
        return null;
      }
      var store = pageStoreSlug() || "demo";
      return {
        v: 1,
        recovery_flow_started: "1",
        session_id: String(sid).trim().slice(0, 300),
        cart_id: String(cid).trim().slice(0, 255),
        store_slug: store,
      };
    } catch (e) {
      return null;
    }
  }

  function hasAfterRecoveryReplySignal() {
    try {
      if (window.sessionStorage.getItem("cartflow_reason_tag")) {
        return true;
      }
    } catch (e1) {
      /* ignore */
    }
    try {
      var eng = window.localStorage.getItem("cartflow_recovery_engagement_v1");
      if (eng != null && String(eng).trim()) {
        return true;
      }
    } catch (e2) {
      /* ignore */
    }
    try {
      var raw = window.localStorage.getItem(LS_KEY);
      if (raw && String(raw).trim()) {
        var o = JSON.parse(raw);
        if (o && o.reason_tag && String(o.reason_tag).trim()) {
          return true;
        }
      }
    } catch (e3) {
      /* ignore */
    }
    return false;
  }

  function skip(status, reason) {
    try {
      status.last_skip_reason = reason;
      console.log("[RETURN TRACKER SKIPPED] reason=" + reason);
    } catch (e) {
      /* ignore */
    }
  }

  function runOnce(status) {
    status.last_skip_reason = null;
    status.return_state_found = false;
    status.return_event_sent = false;

    if (isConverted()) {
      skip(status, "session_converted");
      return;
    }

    var st = readJsonLs(LS_KEY);
    if (!validRecoveryState(st)) {
      st = buildRecoveryStateFromSessionStorage();
    }
    if (!validRecoveryState(st)) {
      skip(status, "no_recovery_state");
      return;
    }

    status.return_state_found = true;

    var session_id = String(st.session_id).trim().slice(0, 300);
    var cart_id = String(st.cart_id).trim().slice(0, 255);
    var storeFromState = st.store_slug != null ? String(st.store_slug).trim() : "";
    var store_slug = storeFromState || pageStoreSlug() || "demo";
    var pageSlug = pageStoreSlug();
    if (pageSlug && storeFromState && storeFromState !== pageSlug) {
      skip(status, "store_slug_mismatch");
      return;
    }

    var recovery_return_context = inferReturnContext();
    var return_context = hasAfterRecoveryReplySignal()
      ? "after_recovery_reply"
      : recovery_return_context;

    var dedupeCore = session_id + "|" + cart_id;
    var nowMs = Date.now();
    try {
      var trRaw = window.localStorage.getItem(THROTTLE_LS_KEY);
      var tr = trRaw ? JSON.parse(trRaw) : null;
      if (
        tr &&
        tr.k === dedupeCore &&
        typeof tr.t === "number" &&
        nowMs - tr.t < THROTTLE_MIN_MS
      ) {
        skip(status, "dedupe_throttle");
        return;
      }
    } catch (eTh) {
      /* ignore */
    }

    try {
      console.log("[RETURN TRACKER]", {
        phase: "state",
        session_id: session_id,
        cart_id: cart_id,
        store_slug: store_slug,
        recovery_return_context: recovery_return_context,
        return_context: return_context,
      });
    } catch (eSt) {
      /* ignore */
    }

    var bodyObj = {
      event_type: "user_returned_to_site",
      store_slug: store_slug,
      store: store_slug,
      session_id: session_id,
      cart_id: cart_id,
      recovery_return_context: recovery_return_context,
      return_context: return_context,
      return_timestamp: new Date().toISOString(),
    };
    if (recovery_return_context === "checkout") {
      bodyObj.return_visit_kind = "active_commercial_reengagement";
      bodyObj.active_commercial_reengagement = true;
      bodyObj.user_returned_to_site = true;
      bodyObj.returned_checkout_page = true;
    } else {
      bodyObj.return_visit_kind = "passive_return_visit";
      bodyObj.passive_return_visit = true;
    }
    var cfPh = readCfTestPhone();
    if (cfPh) {
      bodyObj.cf_test_phone = cfPh;
    }
    var custPh = readOptionalCustomerPhone();
    if (custPh) {
      bodyObj.phone = custPh;
    }

    try {
      window
        .fetch(apiCartEventUrl(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyObj),
        })
        .then(function (r) {
          return r
            .json()
            .then(function (j) {
              return { ok: r.ok, status: r.status, body: j };
            })
            .catch(function () {
              return { ok: r.ok, status: r.status, body: null };
            });
        })
        .then(function (res) {
          var ok =
            res && res.ok && res.body && res.body.ok !== false;
          if (ok) {
            try {
              window.localStorage.setItem(
                THROTTLE_LS_KEY,
                JSON.stringify({ k: dedupeCore, t: Date.now() })
              );
            } catch (eOk) {
              /* ignore */
            }
            try {
              console.log(
                "[RETURN TRACKER EVENT SENT] store_slug=" +
                  store_slug +
                  " session_id=" +
                  session_id +
                  " cart_id=" +
                  cart_id +
                  " context=" +
                  return_context
              );
            } catch (eLg) {
              /* ignore */
            }
            status.return_event_sent = true;
            status.last_skip_reason = null;
          } else {
            skip(status, "backend_reject_or_network");
          }
        })
        .catch(function (err) {
          try {
            console.warn("[RETURN TRACKER ERROR]", "fetch_chain", err);
          } catch (eW) {
            /* ignore */
          }
          skip(status, "fetch_failed");
        });
    } catch (eF) {
      try {
        console.warn("[RETURN TRACKER ERROR]", "fetch_throw", eF);
      } catch (eW2) {
        /* ignore */
      }
      skip(status, "fetch_throw");
    }
  }

  /**
   * @param {object} status — window.CARTFLOW_RUNTIME_STATUS
   * @param {object} runtime — window.CartFlowRuntime
   */
  function initReturnTracker(status, runtime) {
    if (window.__CARTFLOW_RETURN_TRACKER_EXECUTED__) {
      return;
    }
    window.__CARTFLOW_RETURN_TRACKER_EXECUTED__ = true;

    try {
      status.return_tracker_loaded = true;
      console.log("[RETURN TRACKER]", "init", MODULE_VERSION);
    } catch (eI) {
      /* ignore */
    }

    var health = { ok: true, ran: false, version: MODULE_VERSION };

    try {
      runOnce(status);
      health.ran = true;
    } catch (eRun) {
      health.ok = false;
      try {
        status.last_skip_reason = "return_tracker_crash";
        console.warn("[RETURN TRACKER ERROR]", eRun);
      } catch (eL) {
        /* ignore */
      }
    }

    try {
      runtime.returnTracker = {
        version: MODULE_VERSION,
        getHealth: function () {
          return health;
        },
        getDebug: function () {
          try {
            return {
              last_skip_reason: status.last_skip_reason,
              return_state_found: status.return_state_found,
              return_event_sent: status.return_event_sent,
            };
          } catch (eDbg) {
            return {};
          }
        },
      };
    } catch (eRt) {
      /* ignore */
    }
  }

  window.__cartflowInitReturnTracker = initReturnTracker;
  window.__cartflowReturnTrackerVersion = MODULE_VERSION;
})();
