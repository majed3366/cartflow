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

  function isPublicSandboxStoreSlug(slug) {
    var s = String(slug || "").trim().toLowerCase();
    return !s || s === "demo" || s === "demo2" || s === "default";
  }

  function extractSlugFromHostnameInline(host) {
    if (typeof window.cartflowExtractStoreSlugFromHostname === "function") {
      return String(window.cartflowExtractStoreSlugFromHostname(host) || "").trim();
    }
    var h = String(host || "").toLowerCase().trim();
    if (!h) {
      return "";
    }
    var suffixes = [".zid.store", ".salla.sa", ".salla.store"];
    var i;
    for (i = 0; i < suffixes.length; i++) {
      var suf = suffixes[i];
      if (h.length > suf.length && h.slice(-suf.length) === suf) {
        var sub = h.slice(0, -suf.length);
        if (sub && sub.indexOf(".") === -1 && /^[a-z0-9_-]+$/i.test(sub)) {
          return sub;
        }
      }
    }
    return "";
  }

  function isPlatformStorefrontHost() {
    try {
      if (typeof window.cartflowIsPlatformStorefrontHost === "function") {
        return !!window.cartflowIsPlatformStorefrontHost();
      }
    } catch (eFn) {}
    try {
      return !!extractSlugFromHostnameInline(window.location.hostname);
    } catch (ePlat) {}
    return false;
  }

  function slugFromHostnameInline() {
    return extractSlugFromHostnameInline(window.location.hostname);
  }

  function storeSlugFromWidgetLoaderScript() {
    if (typeof window.cartflowResolveStorefrontStoreSlug === "function") {
      var resolved = window.cartflowResolveStorefrontStoreSlug();
      if (resolved && resolved.slug) {
        return String(resolved.slug).trim();
      }
    }
    try {
      var scripts = document.getElementsByTagName("script");
      var i;
      for (i = scripts.length - 1; i >= 0; i--) {
        var node = scripts[i];
        var src = String(node.src || "");
        if (src.indexOf("widget_loader") === -1) {
          continue;
        }
        var ds =
          node.getAttribute("data-store") ||
          node.getAttribute("data-store-slug") ||
          "";
        if (ds && String(ds).trim()) {
          return String(ds).trim();
        }
        if (src) {
          try {
            var qu = new URL(src, window.location.href).searchParams;
            var fromQs = qu.get("store") || qu.get("store_slug") || "";
            if (fromQs && String(fromQs).trim()) {
              return String(fromQs).trim();
            }
          } catch (eQs) {
            /* ignore */
          }
        }
      }
    } catch (eWl) {}
    return "";
  }

  function storeSlugFromMerchantActivationQuery() {
    try {
      var qs = new URLSearchParams(window.location.search || "");
      if (String(qs.get("merchant_activation") || "").trim() !== "1") {
        return "";
      }
      var slug = String(qs.get("store_slug") || qs.get("store") || "").trim();
      if (slug && !isPublicSandboxStoreSlug(slug)) {
        return slug;
      }
    } catch (eQ) {}
    return "";
  }

  function merchantActivationMode() {
    try {
      var qs = new URLSearchParams(window.location.search || "");
      return String(qs.get("merchant_activation") || "").trim() === "1";
    } catch (eQm) {
      return false;
    }
  }

  function storeSlug() {
    if (typeof window.cartflowResolveStorefrontStoreSlug === "function") {
      var resolved = window.cartflowResolveStorefrontStoreSlug();
      if (resolved && resolved.slug) {
        return String(resolved.slug).trim();
      }
      if (isPlatformStorefrontHost()) {
        return "";
      }
    }
    var fromHost = slugFromHostnameInline();
    if (fromHost && !isPublicSandboxStoreSlug(fromHost)) {
      return fromHost;
    }
    try {
      if (
        typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
        window.CARTFLOW_STORE_SLUG !== null &&
        String(window.CARTFLOW_STORE_SLUG).trim()
      ) {
        var fromWin = String(window.CARTFLOW_STORE_SLUG).trim();
        if (!isPublicSandboxStoreSlug(fromWin)) {
          return fromWin;
        }
        if (isPlatformStorefrontHost()) {
          return fromHost || "";
        }
      }
    } catch (eSl) {}
    var fromLoader = storeSlugFromWidgetLoaderScript();
    if (fromLoader && !isPublicSandboxStoreSlug(fromLoader)) {
      return fromLoader;
    }
    var fromMa = storeSlugFromMerchantActivationQuery();
    if (fromMa) {
      return fromMa;
    }
    var m = typeof document !== "undefined" ? document.querySelector("[data-cartflow-store]") : null;
    if (m && m.getAttribute("data-cartflow-store")) {
      var fromAttr = String(m.getAttribute("data-cartflow-store")).trim();
      if (fromAttr && !isPublicSandboxStoreSlug(fromAttr)) {
        return fromAttr;
      }
    }
    if (fromHost) {
      return fromHost;
    }
    if (isPlatformStorefrontHost()) {
      try {
        console.warn("[CF STORE SLUG UNRESOLVED PLATFORM HOST]");
      } catch (ePlatApi) {}
      return "";
    }
    try {
      console.warn("[CF STORE SLUG FALLBACK DEMO]");
    } catch (eDemo) {}
    return "demo";
  }

  function sessionId() {
    if (typeof window.cartflowGetSessionId === "function") {
      var fromFn = String(window.cartflowGetSessionId() || "").trim();
      if (fromFn) {
        return fromFn;
      }
    }
    var storageKey = "cartflow_recovery_session_id";
    try {
      var sid =
        (window.sessionStorage && window.sessionStorage.getItem(storageKey)) ||
        (window.localStorage && window.localStorage.getItem(storageKey)) ||
        "";
      sid = String(sid || "").trim();
      if (sid) {
        return sid;
      }
      sid =
        "cf-" +
        Date.now().toString(36) +
        "-" +
        Math.random().toString(36).slice(2, 10);
      if (window.sessionStorage) {
        window.sessionStorage.setItem(storageKey, sid);
      }
      return sid;
    } catch (eSid) {
      return (
        "cf-" +
        Date.now().toString(36) +
        "-" +
        Math.random().toString(36).slice(2, 10)
      );
    }
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

  function postAssistHandoff() {
    var url = apiBase()
      ? apiBase() + "/api/cartflow/assist-handoff"
      : "/api/cartflow/assist-handoff";
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        store_slug: storeSlug(),
        session_id: sessionId(),
        merchant_activation: merchantActivationMode(),
      }),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) {
          return { ok: false, status: r.status, body: j };
        }
        return j;
      });
    });
  }

  function postReason(payload) {
    var url = apiBase()
      ? apiBase() + "/api/cartflow/reason"
      : "/api/cartflow/reason";
    var body = {
      store_slug: storeSlug(),
      session_id: sessionId(),
      reason: payload.reason,
      merchant_activation: merchantActivationMode(),
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

  var _sessionReadyCached = null;
  var _sessionPublicConfigCached = null;
  var _readyFetchInFlight = null;
  var _readyLastNetworkDoneAt = 0;
  var _readyBlocked = false;
  var _readyBlockedLogged = false;
  var READY_NETWORK_MIN_GAP_MS = 2200;

  function logReadyBlockedOnce(reason) {
    if (_readyBlockedLogged) {
      return;
    }
    _readyBlockedLogged = true;
    try {
      console.warn("[CF READY BLOCKED]", String(reason || "unknown"));
    } catch (eLog) {
      /* ignore */
    }
  }

  function markReadyBlocked(reason) {
    _readyBlocked = true;
    logReadyBlockedOnce(reason);
  }

  function fetchReady() {
    if (/\b\/demo\//i.test(String(window.location.pathname || ""))) {
      return Promise.resolve({ demo: true, after_step1: true, ok: true });
    }
    if (_readyBlocked) {
      return Promise.resolve(
        _sessionReadyCached != null
          ? _sessionReadyCached
          : { ok: false, after_step1: false, ready_blocked: true }
      );
    }
    if (_sessionReadyCached != null && _sessionReadyCached.after_step1) {
      return Promise.resolve(_sessionReadyCached);
    }
    var gapNow = Date.now();
    if (
      _readyFetchInFlight == null &&
      _sessionReadyCached != null &&
      !_sessionReadyCached.after_step1 &&
      _readyLastNetworkDoneAt > 0 &&
      gapNow - _readyLastNetworkDoneAt < READY_NETWORK_MIN_GAP_MS
    ) {
      return Promise.resolve(_sessionReadyCached);
    }
    if (_readyFetchInFlight != null) {
      try {
        console.log("[CF READY REQUEST SKIPPED_DUPLICATE]");
      } catch (eSkip) {}
      return _readyFetchInFlight;
    }
    var b = apiBase();
    var u =
      (b || "") +
      "/api/cartflow/ready" +
      "?store_slug=" +
      encodeURIComponent(storeSlug()) +
      "&session_id=" +
      encodeURIComponent(sessionId());
    _readyFetchInFlight = fetch(u, { method: "GET" })
      .then(function (r) {
        if (!r.ok) {
          if (r.status === 422 || r.status >= 500) {
            markReadyBlocked("http_" + r.status);
          }
        }
        return r.json().then(function (j) {
          _readyLastNetworkDoneAt = Date.now();
          if (j != null && typeof j === "object") {
            if (j.after_step1) {
              _sessionReadyCached = j;
            } else if (j.ok !== false) {
              _sessionReadyCached = j;
            }
          }
          return j;
        });
      })
      .catch(function () {
        _readyLastNetworkDoneAt = Date.now();
        markReadyBlocked("network_or_cors");
        return _sessionReadyCached != null
          ? _sessionReadyCached
          : { ok: false, after_step1: false, ready_blocked: true };
      })
      .finally(function () {
        _readyFetchInFlight = null;
      });
    return _readyFetchInFlight;
  }

  function fetchPublicConfig() {
    if (_sessionPublicConfigCached != null) {
      return Promise.resolve(_sessionPublicConfigCached);
    }
    if (_readyBlocked) {
      return Promise.resolve(
        _sessionPublicConfigCached != null
          ? _sessionPublicConfigCached
          : { ok: false, ready_blocked: true }
      );
    }
    var bb = apiBase();
    var rt = "";
    try {
      rt =
        typeof window.CARTFLOW_RUNTIME_VERSION === "string"
          ? window.CARTFLOW_RUNTIME_VERSION
          : typeof window.__cartflow_loader_build === "string"
            ? window.__cartflow_loader_build
            : "";
    } catch (eRt) {}
    var u =
      (bb || "") +
      "/api/cartflow/public-config" +
      "?store_slug=" +
      encodeURIComponent(storeSlug()) +
      cartTotalSuffix() +
      (rt ? "&_rt=" + encodeURIComponent(rt) : "");
    return fetch(u, { method: "GET" })
      .then(function (r) {
        return r.json().then(function (j) {
          if (j != null && typeof j === "object" && j.ok !== false) {
            _sessionPublicConfigCached = j;
          }
          return j;
        });
      })
      .catch(function () {
        markReadyBlocked("public_config_network_or_cors");
        return { ok: false, ready_blocked: true };
      });
  }

  var Api = {
    apiBase: apiBase,
    storeSlug: storeSlug,
    sessionId: sessionId,
    postReason: postReason,
    postAssistHandoff: postAssistHandoff,
    fetchReady: fetchReady,
    fetchPublicConfig: fetchPublicConfig,
    reasonPostOk: cfCartflowReasonPostOk,
  };
  window.CartflowWidgetRuntime.Api = Api;
})();
