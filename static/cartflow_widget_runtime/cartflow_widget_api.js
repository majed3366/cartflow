/**
 * Fetch / POST façade for widget runtime (no triggers, no DOM).
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  function apiBase() {
    try {
      if (typeof window.CARTFLOW_API_BASE === "string" && window.CARTFLOW_API_BASE.trim()) {
        return String(window.CARTFLOW_API_BASE).replace(/\/+$/, "");
      }
    } catch (eAb) {}
    return "";
  }

  function storeSlug() {
    try {
      if (
        typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
        window.CARTFLOW_STORE_SLUG !== null &&
        String(window.CARTFLOW_STORE_SLUG).trim()
      ) {
        return String(window.CARTFLOW_STORE_SLUG).trim();
      }
    } catch (eSl) {}
    var m = typeof document !== "undefined" ? document.querySelector("[data-cartflow-store]") : null;
    if (m && m.getAttribute("data-cartflow-store")) {
      return String(m.getAttribute("data-cartflow-store")).trim();
    }
    return "demo";
  }

  function sessionId() {
    if (typeof window.cartflowGetSessionId === "function") {
      return String(window.cartflowGetSessionId() || "").trim();
    }
    return "";
  }

  function cfCartflowReasonPostOk(j) {
    if (!j || typeof j !== "object") {
      return false;
    }
    if (j.ok === true) {
      return true;
    }
    if (j.ok === false || j.error) {
      return false;
    }
    return true;
  }

  function postReason(payload) {
    var url = apiBase()
      ? apiBase() + "/api/cartflow/reason"
      : "/api/cartflow/reason";
    var body = {
      store_slug: storeSlug(),
      session_id: sessionId(),
      reason: payload.reason,
    };
    if (payload.custom_text != null && String(payload.custom_text) !== "") {
      body.custom_text = String(payload.custom_text);
    }
    if (payload.customer_phone != null && String(payload.customer_phone).trim() !== "") {
      body.customer_phone = String(payload.customer_phone).trim();
    }
    if (payload.sub_category != null && String(payload.sub_category) !== "") {
      body.sub_category = String(payload.sub_category);
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

  function cartTotalSuffix() {
    try {
      var cart = typeof window.cart !== "undefined" && Array.isArray(window.cart) ? window.cart : [];
      if (!cart.length) {
        return "";
      }
      var sum = 0;
      var any = false;
      var i;
      for (i = 0; i < cart.length; i++) {
        var row = cart[i];
        if (!row) {
          continue;
        }
        var p =
          row.price != null
            ? row.price
            : row.unit_price != null
            ? row.unit_price
            : row.selling_price != null
            ? row.selling_price
            : row.total != null && row.quantity == null
            ? row.total
            : null;
        if (p == null) {
          continue;
        }
        var pr = typeof p === "number" ? p : parseFloat(String(p));
        if (isNaN(pr)) {
          continue;
        }
        var qRaw = row.quantity != null ? row.quantity : row.qty != null ? row.qty : 1;
        var q = typeof qRaw === "number" ? qRaw : parseFloat(String(qRaw));
        if (isNaN(q) || q < 0) {
          q = 1;
        }
        sum += pr * q;
        any = true;
      }
      if (!any) {
        return "";
      }
      return "&cart_total=" + encodeURIComponent(String(sum));
    } catch (eCt) {
      return "";
    }
  }

  function fetchReady() {
    if (/\b\/demo\//i.test(String(window.location.pathname || ""))) {
      return Promise.resolve({ demo: true, after_step1: true, ok: true });
    }
    var b = apiBase();
    var u =
      (b || "") +
      "/api/cartflow/ready" +
      "?store_slug=" +
      encodeURIComponent(storeSlug()) +
      "&session_id=" +
      encodeURIComponent(sessionId());
    return fetch(u, { method: "GET" }).then(function (r) {
      return r.json();
    });
  }

  function fetchPublicConfig() {
    var bb = apiBase();
    var u =
      (bb || "") +
      "/api/cartflow/public-config" +
      "?store_slug=" +
      encodeURIComponent(storeSlug()) +
      cartTotalSuffix();
    return fetch(u, { method: "GET" }).then(function (r) {
      return r.json();
    });
  }

  var Api = {
    apiBase: apiBase,
    storeSlug: storeSlug,
    sessionId: sessionId,
    postReason: postReason,
    fetchReady: fetchReady,
    fetchPublicConfig: fetchPublicConfig,
    reasonPostOk: cfCartflowReasonPostOk,
  };
  window.CartflowWidgetRuntime.Api = Api;
})();
