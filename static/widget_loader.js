/**
 * Unified CartFlow runtime bootstrap: return tracker + widget load after window.load.
 * Layered V2 (‎cartflow_widget_runtime‎) is the **default** for storefronts using this shim.
 * Legacy ‎cartflow_widget.js‎ loads **only** when ‎window.__CARTFLOW_ALLOW_LEGACY_WIDGET‎ === true **and**
 * ‎window.CARTFLOW_WIDGET_RUNTIME_V2‎ is not true — explicit rollback / QA (see console ‎ALLOWED‎ / ‎BLOCKED‎ logs).
 * ‎/demo/store*‎ sets ‎CARTFLOW_WIDGET_RUNTIME_V2‎ (**primary V2**; unchanged product behavior).
 *
 * Logs: ‎[CF LEGACY WIDGET LOAD BLOCKED]‎ (default-V2 substituted for accidental legacy path);
 *       ‎[CF LEGACY WIDGET LOAD ALLOWED]‎ (legacy opt-in). ‎GET /dev/widget-test‎ bypasses this file.
 * Cross-origin embed (Zid): sets ‎CARTFLOW_RECOVERY_WIDGET_MODE‎ — approved cart-recovery V2, not browsing assistant.
 */
(function () {
  "use strict";

  var RUNTIME_VERSION = "v2-zid-cart-sync-v1";

  function cartflowExtractHostnameSlugInline(host) {
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

  function cartflowIsPlatformStoreHostInline() {
    try {
      if (typeof window.cartflowIsPlatformStorefrontHost === "function") {
        return !!window.cartflowIsPlatformStorefrontHost();
      }
    } catch (eFn) {}
    return !!cartflowExtractHostnameSlugInline(window.location.hostname);
  }

  function cartflowWidgetLoaderScriptUrl() {
    try {
      var scripts = document.getElementsByTagName("script");
      var i;
      for (i = scripts.length - 1; i >= 0; i--) {
        var src = String(scripts[i].src || "");
        if (src.indexOf("widget_loader") !== -1 && src.indexOf("/static/") !== -1) {
          return src;
        }
      }
    } catch (eUrl) {
      /* ignore */
    }
    return "";
  }

  /** Resolve /static/* against the host that served widget_loader.js (Zid embed safe). */
  function cartflowStaticAssetUrl(pathUnderStatic) {
    var rel = String(pathUnderStatic || "").replace(/^\/+/, "");
    try {
      var loaderUrl = cartflowWidgetLoaderScriptUrl();
      if (loaderUrl) {
        var u = new URL(loaderUrl, window.location.href);
        var marker = "/static/widget_loader.js";
        var p = u.pathname || "";
        var ix = p.indexOf(marker);
        if (ix >= 0) {
          return u.origin + p.substring(0, ix) + "/static/" + rel;
        }
        return u.origin + "/static/" + rel;
      }
    } catch (eAsset) {
      /* ignore */
    }
    return "/static/" + rel;
  }

  function cartflowEnsureEmbedOriginFromLoader() {
    try {
      var loaderUrl = cartflowWidgetLoaderScriptUrl();
      if (!loaderUrl) {
        return;
      }
      var u = new URL(loaderUrl, window.location.href);
      var p = u.pathname || "";
      var ix = p.indexOf("/static/widget_loader.js");
      if (ix >= 0) {
        window.__CARTFLOW_STATIC_ROOT__ = u.origin + p.substring(0, ix) + "/static/";
      } else {
        window.__CARTFLOW_STATIC_ROOT__ = u.origin + "/static/";
      }
      if (u.origin && u.origin !== window.location.origin) {
        window.CARTFLOW_API_BASE = u.origin;
      }
    } catch (eOrig) {
      /* ignore */
    }
  }

  cartflowEnsureEmbedOriginFromLoader();

  function cartflowEnsureStoreSlugResolverLoaded() {
    if (typeof window.cartflowResolveStorefrontStoreSlug === "function") {
      return;
    }
    var url =
      cartflowStaticAssetUrl("cartflow_storefront_store_slug.js") +
      "?v=" +
      encodeURIComponent(RUNTIME_VERSION);
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", url, false);
      xhr.send(null);
      if (xhr.status >= 200 && xhr.status < 300 && xhr.responseText) {
        (0, eval)(xhr.responseText);
      }
    } catch (eResolverLoad) {
      /* runtime api may still resolve later */
    }
  }

  function cartflowApplyResolvedStoreSlug() {
    cartflowEnsureStoreSlugResolverLoaded();
    var slug = "";
    var source = "";
    if (typeof window.cartflowResolveStorefrontStoreSlug === "function") {
      var resolved = window.cartflowResolveStorefrontStoreSlug();
      if (resolved && resolved.slug) {
        slug = String(resolved.slug).trim();
        source = resolved.source || "";
      }
    }
    if (!slug) {
      slug = cartflowExtractHostnameSlugInline(window.location.hostname);
      if (slug) {
        source = "hostname_inline_fallback";
      }
    }
    if (slug && slug !== "demo") {
      window.CARTFLOW_STORE_SLUG = slug;
      return;
    }
    if (cartflowIsPlatformStoreHostInline()) {
      try {
        if (window.CARTFLOW_STORE_SLUG === "demo") {
          delete window.CARTFLOW_STORE_SLUG;
        }
      } catch (eClr) {
        window.CARTFLOW_STORE_SLUG = "";
      }
      try {
        console.warn("[CF STORE SLUG UNRESOLVED PLATFORM HOST]");
      } catch (ePlat) {}
      return;
    }
    if (slug === "demo") {
      window.CARTFLOW_STORE_SLUG = slug;
    }
  }

  /** Cross-origin embed (e.g. Zid): approved cart-recovery V2, not browsing assistant. */
  function cartflowIsStorefrontEmbed() {
    try {
      var apiBase = window.CARTFLOW_API_BASE;
      if (!apiBase || !String(apiBase).trim()) {
        return false;
      }
      var pageOrigin = String(window.location.origin || "").replace(/\/+$/, "");
      var loaderOrigin = String(apiBase).replace(/\/+$/, "");
      return !!(pageOrigin && loaderOrigin && pageOrigin !== loaderOrigin);
    } catch (eEmb) {
      return false;
    }
  }

  function cartflowEnsureStorefrontRecoveryMode() {
    if (!cartflowIsStorefrontEmbed()) {
      return;
    }
    try {
      window.CARTFLOW_WIDGET_RUNTIME_V2 = true;
      window.CARTFLOW_RUNTIME_VERSION = RUNTIME_VERSION;
      window.CARTFLOW_RECOVERY_WIDGET_MODE = true;
      console.log("[CARTFLOW RECOVERY MODE] storefront_embed=true runtime=" + RUNTIME_VERSION);
    } catch (eMode) {
      /* ignore */
    }
  }

  cartflowEnsureStorefrontRecoveryMode();

  function cartflowAllowLegacyWidgetExplicit() {
    try {
      return window.__CARTFLOW_ALLOW_LEGACY_WIDGET === true;
    } catch (eLeg) {
      return false;
    }
  }

  /** /demo/store, /demo/store/cart, … — primary V2 storefront; never legacy blob here. */
  function cartflowIsDemoStorePrimaryV2Path() {
    try {
      return /^\/demo\/store(?:\/|$)/i.test(
        String(window.location.pathname || "")
      );
    } catch (eP) {
      return false;
    }
  }
  var RETURN_TRACKER_SRC =
    cartflowStaticAssetUrl("cartflow_return_tracker.js") +
    "?v=" +
    encodeURIComponent(RUNTIME_VERSION);

  function cartflowLoaderPerfDemoDevLog(line) {
    try {
      var p = window.location.pathname || "";
      if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
        console.log(line);
      }
    } catch (eL) {
      /* ignore */
    }
  }

  function probeTrackingLoaded() {
    try {
      return (
        typeof window.cartflowGetSessionId === "function" ||
        typeof window.cartflowMarkRecoveryFlowStarted === "function" ||
        typeof window.cartflowSyncCartState === "function"
      );
    } catch (e) {
      return false;
    }
  }

  try {
    window.CARTFLOW_RUNTIME_STATUS = {
      tracking_loaded: probeTrackingLoaded(),
      return_tracker_loaded: false,
      return_state_found: false,
      return_event_sent: false,
      last_skip_reason: null,
      runtime_version: RUNTIME_VERSION,
    };
  } catch (eSt) {
    try {
      window.CARTFLOW_RUNTIME_STATUS = {
        tracking_loaded: false,
        return_tracker_loaded: false,
        return_state_found: false,
        return_event_sent: false,
        last_skip_reason: "status_init_failed",
        runtime_version: RUNTIME_VERSION,
      };
    } catch (e2) {
      /* ignore */
    }
  }

  try {
    window.CartFlowRuntime = {
      widget: null,
      tracking: {
        probeLoaded: probeTrackingLoaded,
      },
      returnTracker: null,
      observability: {
        getStatus: function () {
          try {
            if (window.CARTFLOW_RUNTIME_STATUS) {
              window.CARTFLOW_RUNTIME_STATUS.tracking_loaded =
                probeTrackingLoaded();
            }
            return window.CARTFLOW_RUNTIME_STATUS;
          } catch (eG) {
            return null;
          }
        },
      },
    };
  } catch (eRt) {
    try {
      window.CartFlowRuntime = {
        widget: null,
        tracking: null,
        returnTracker: null,
        observability: null,
      };
    } catch (e3) {
      /* ignore */
    }
  }

  try {
    console.log("[CARTFLOW RUNTIME] bootstrap_start", RUNTIME_VERSION);
  } catch (eLb) {
    /* ignore */
  }

  function cartflowPostWidgetSeenBeacon(origin, payloadJson) {
    var url = String(origin || "").replace(/\/+$/, "") + "/api/storefront/widget-seen";
    if (navigator.sendBeacon) {
      try {
        navigator.sendBeacon(url, new Blob([payloadJson], { type: "application/json" }));
      } catch (eSb) {
        console.warn("[CF WIDGET SEEN BEACON WARN]", "sendBeacon_failed", eSb);
      }
    } else {
      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payloadJson,
        credentials: "omit",
        keepalive: true,
      }).catch(function (eFetch) {
        console.warn("[CF WIDGET SEEN BEACON WARN]", "fetch_failed", eFetch);
      });
    }
  }

  function cartflowScheduleWidgetSeenBeacon() {
    setTimeout(function () {
      try {
        var p = window.location.pathname || "";
        if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
          return;
        }
        cartflowApplyResolvedStoreSlug();
        var slug = "";
        try {
          slug = window.CARTFLOW_STORE_SLUG || "";
        } catch (eS0) {
          slug = "";
        }
        if (!slug) {
          slug = cartflowExtractHostnameSlugInline(window.location.hostname);
        }
        if (!slug || slug === "demo") {
          if (cartflowIsPlatformStoreHostInline()) {
            return;
          }
          return;
        }
        console.log("[WIDGET STOREFRONT LOAD] store=" + slug);
        var origin = "";
        try {
          var loaderNode = document.querySelector('script[src*="widget_loader"]');
          if (loaderNode && loaderNode.src) {
            origin = new URL(loaderNode.src, window.location.href).origin;
          }
        } catch (eO) {
          origin = "";
        }
        if (!origin) {
          return;
        }
        var payload = JSON.stringify({
          store: slug,
          store_slug: slug,
          runtime_version: RUNTIME_VERSION,
          page_url: String(window.location.href || "").slice(0, 2048),
          timestamp: new Date().toISOString(),
        });
        cartflowPostWidgetSeenBeacon(origin, payload);
      } catch (eBeacon) {
        console.warn("[CF WIDGET SEEN BEACON WARN]", "beacon_crash", eBeacon);
      }
    }, 0);
  }

  cartflowScheduleWidgetSeenBeacon();

  (function cartflowInitStoreSlugFromLoaderTag() {
    try {
      cartflowApplyResolvedStoreSlug();
    } catch (eInitSlug) {
      /* ignore */
    }
  })();

  window.__cartflow_loader_build = RUNTIME_VERSION;
  try {
    console.log("[CARTFLOW RUNTIME] loader_build=" + RUNTIME_VERSION);
  } catch (eB) {
    /* ignore */
  }

  function scheduleReturnTrackerModule() {
    try {
      if (window.__CARTFLOW_RT_SCRIPT_SCHEDULED__) {
        return;
      }
      window.__CARTFLOW_RT_SCRIPT_SCHEDULED__ = true;
    } catch (eF) {
      return;
    }

    var s = document.createElement("script");
    s.src = RETURN_TRACKER_SRC;
    s.async = true;
    s.onload = function () {
      try {
        var st = window.CARTFLOW_RUNTIME_STATUS;
        var rt = window.CartFlowRuntime;
        if (typeof window.cartflowEnsureDurableReturnStateFromSession === "function") {
          window.cartflowEnsureDurableReturnStateFromSession();
        }
        if (
          st &&
          rt &&
          typeof window.__cartflowInitReturnTracker === "function"
        ) {
          window.__cartflowInitReturnTracker(st, rt);
        } else {
          try {
            st.return_tracker_loaded = false;
            st.last_skip_reason = "return_tracker_init_missing";
            console.warn("[RETURN TRACKER ERROR]", "init_fn_missing");
          } catch (eM) {
            /* ignore */
          }
        }
      } catch (eOn) {
        try {
          if (window.CARTFLOW_RUNTIME_STATUS) {
            window.CARTFLOW_RUNTIME_STATUS.last_skip_reason =
              "return_tracker_onload_crash";
          }
          console.warn("[RETURN TRACKER ERROR]", eOn);
        } catch (eW) {
          /* ignore */
        }
      }
    };
    s.onerror = function () {
      try {
        if (window.CARTFLOW_RUNTIME_STATUS) {
          window.CARTFLOW_RUNTIME_STATUS.return_tracker_loaded = false;
          window.CARTFLOW_RUNTIME_STATUS.last_skip_reason =
            "return_tracker_script_load_failed";
        }
        console.warn("[RETURN TRACKER ERROR]", "script_load_failed");
      } catch (eEr) {
        /* ignore */
      }
    };
    try {
      (document.head || document.body || document.documentElement).appendChild(
        s
      );
    } catch (eApp) {
      try {
        window.CARTFLOW_RUNTIME_STATUS.last_skip_reason =
          "return_tracker_script_append_failed";
        console.warn("[RETURN TRACKER ERROR]", eApp);
      } catch (eZ) {
        /* ignore */
      }
    }
  }

  try {
    scheduleReturnTrackerModule();
  } catch (eSch) {
    try {
      console.warn("[RETURN TRACKER ERROR]", "schedule_crash", eSch);
    } catch (eC) {
      /* ignore */
    }
  }

  try {
    console.log("[CARTFLOW RUNTIME] return_tracker_scheduled");
  } catch (eL2) {
    /* ignore */
  }

  function cartflowBlockWidgetAfterConversion() {
    try {
      if (
        typeof window.cartflowIsSessionConverted === "function" &&
        window.cartflowIsSessionConverted()
      ) {
        return true;
      }
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (e) {
      return false;
    }
  }

  function loadWidget() {
    if (cartflowBlockWidgetAfterConversion()) {
      return;
    }
    try {
      if (window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ === true) {
        cartflowLoaderPerfDemoDevLog(
          "[CF PERF] widget loader skipped duplicate"
        );
        return;
      }
    } catch (eAct) {
      /* ignore */
    }

    try {
      var scripts = document.getElementsByTagName("script");
      var si;
      for (si = 0; si < scripts.length; si++) {
        var prevSrc = scripts[si].getAttribute("src") || "";
        if (
          prevSrc.indexOf("/static/cartflow_widget_runtime/cartflow_widget_loader.js") >= 0
        ) {
          cartflowLoaderPerfDemoDevLog(
            "[CF PERF] layered widget runtime already queued"
          );
          window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
          return;
        }
        if (prevSrc.indexOf("/static/cartflow_widget.js") >= 0) {
          cartflowLoaderPerfDemoDevLog(
            "[CF PERF] widget loader skipped duplicate"
          );
          window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
          return;
        }
      }
    } catch (eScr) {
      /* ignore */
    }

    try {
      if (window.CartFlowRuntime) {
        window.CartFlowRuntime.widget = { loading: true };
      }
    } catch (eWm) {
      /* ignore */
    }

    window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
    try {
      if (cartflowIsDemoStorePrimaryV2Path()) {
        window.CARTFLOW_WIDGET_RUNTIME_V2 = true;
      }
      cartflowEnsureStorefrontRecoveryMode();
    } catch (eV2set) {}

    var runtimeV2Explicit = window.CARTFLOW_WIDGET_RUNTIME_V2 === true;
    var legacyExplicit = cartflowAllowLegacyWidgetExplicit();

    /** Default storefront: V2. Legacy paths require ‎window.__CARTFLOW_ALLOW_LEGACY_WIDGET‎ before load fires. */
    var loadLayeredV2 = runtimeV2Explicit || !legacyExplicit;

    if (!runtimeV2Explicit && legacyExplicit) {
      try {
        console.log("[CF LEGACY WIDGET LOAD ALLOWED]");
      } catch (eAl) {}
    } else if (!runtimeV2Explicit && !legacyExplicit) {
      try {
        console.log("[CF LEGACY WIDGET LOAD BLOCKED]");
      } catch (eBl) {}
    }

    var s = document.createElement("script");
    if (loadLayeredV2) {
      s.src =
        cartflowStaticAssetUrl("cartflow_widget_runtime/cartflow_widget_loader.js") +
        "?v=" +
        encodeURIComponent(RUNTIME_VERSION);
    } else {
      s.src =
        cartflowStaticAssetUrl("cartflow_widget.js") +
        "?v=" +
        encodeURIComponent(RUNTIME_VERSION);
    }
    s.async = true;
    (document.body || document.documentElement).appendChild(s);
  }

  if (document.readyState === "complete") {
    loadWidget();
  } else {
    window.addEventListener("load", loadWidget);
  }
})();
