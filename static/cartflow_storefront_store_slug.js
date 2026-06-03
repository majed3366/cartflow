/**
 * Platform-neutral storefront store slug resolver (Zid, Salla, explicit embed attrs).
 * Sets no globals except window.cartflowResolveStorefrontStoreSlug.
 */
(function cartflowStorefrontStoreSlugResolver() {
  "use strict";

  var SANDBOX = { demo: 1, demo2: 1, default: 1 };
  var _demoFallbackLogged = false;

  function normalizeSlug(raw) {
    var s = String(raw == null ? "" : raw).trim();
    if (!s) {
      return "";
    }
    return s.length > 255 ? s.slice(0, 255) : s;
  }

  function isSandboxSlug(slug) {
    return !!SANDBOX[String(slug || "").trim().toLowerCase()];
  }

  function extractSlugFromHostname(host) {
    var h = String(host || "").toLowerCase().trim();
    if (!h) {
      return "";
    }
    var patterns = [
      { suffix: ".zid.store" },
      { suffix: ".salla.sa" },
      { suffix: ".salla.store" },
    ];
    var i;
    for (i = 0; i < patterns.length; i++) {
      var suf = patterns[i].suffix;
      if (h.length > suf.length && h.slice(-suf.length) === suf) {
        var sub = h.slice(0, -suf.length);
        if (sub && sub.indexOf(".") === -1 && /^[a-z0-9_-]+$/i.test(sub)) {
          return sub;
        }
      }
    }
    return "";
  }

  function extractSlugFromStoreUrl(raw) {
    var s = normalizeSlug(raw);
    if (!s) {
      return "";
    }
    try {
      var u = new URL(s.indexOf("://") >= 0 ? s : "https://" + s);
      var fromHost = extractSlugFromHostname(u.hostname);
      if (fromHost) {
        return fromHost;
      }
    } catch (eUrl) {
      /* ignore */
    }
    return "";
  }

  function findWidgetLoaderScript() {
    try {
      var scripts = document.getElementsByTagName("script");
      var i;
      for (i = scripts.length - 1; i >= 0; i--) {
        var node = scripts[i];
        var src = String(node.src || "");
        if (src.indexOf("widget_loader") !== -1) {
          return node;
        }
      }
    } catch (eFind) {
      /* ignore */
    }
    return null;
  }

  function slugFromScriptAttributes(node) {
    if (!node) {
      return { slug: "", source: "" };
    }
    var ds =
      node.getAttribute("data-store") || node.getAttribute("data-store-slug") || "";
    ds = normalizeSlug(ds);
    if (ds) {
      return { slug: ds, source: "script_data_store" };
    }
    return { slug: "", source: "" };
  }

  function slugFromLoaderUrlQuery(node) {
    if (!node || !node.src) {
      return { slug: "", source: "" };
    }
    try {
      var qu = new URL(node.src, window.location.href).searchParams;
      var fromQs = normalizeSlug(qu.get("store") || qu.get("store_slug") || "");
      if (fromQs) {
        return { slug: fromQs, source: "loader_url_query" };
      }
    } catch (eQs) {
      /* ignore */
    }
    return { slug: "", source: "" };
  }

  function readGlobalValue(raw) {
    if (raw == null) {
      return "";
    }
    if (typeof raw === "object") {
      return "";
    }
    var s = normalizeSlug(raw);
    if (!s) {
      return "";
    }
    if (s.indexOf("://") >= 0 || s.indexOf(".") >= 0) {
      var fromUrl = extractSlugFromStoreUrl(s);
      if (fromUrl) {
        return fromUrl;
      }
    }
    return s;
  }

  function slugFromPlatformGlobals() {
    var candidates = [];
    try {
      if (window.store && typeof window.store === "object") {
        candidates.push(window.store.permalink);
        candidates.push(window.store.url);
        candidates.push(window.store.uuid);
        candidates.push(window.store.id);
      }
    } catch (eSt) {
      /* ignore */
    }
    try {
      if (window.zid && window.zid.store && typeof window.zid.store === "object") {
        candidates.push(window.zid.store.permalink);
        candidates.push(window.zid.store.url);
        candidates.push(window.zid.store.uuid);
        candidates.push(window.zid.store.id);
      }
    } catch (eZid) {
      /* ignore */
    }
    var i;
    for (i = 0; i < candidates.length; i++) {
      var slug = readGlobalValue(candidates[i]);
      if (slug) {
        return { slug: slug, source: "platform_global" };
      }
    }
    return { slug: "", source: "" };
  }

  function slugFromHostname() {
    try {
      var fromHost = extractSlugFromHostname(window.location.hostname);
      if (fromHost) {
        return { slug: fromHost, source: "hostname_permalink" };
      }
    } catch (eHost) {
      /* ignore */
    }
    return { slug: "", source: "" };
  }

  function slugFromMerchantActivationQuery() {
    try {
      var qs = new URLSearchParams(window.location.search || "");
      if (String(qs.get("merchant_activation") || "").trim() !== "1") {
        return { slug: "", source: "" };
      }
      var slug = normalizeSlug(qs.get("store_slug") || qs.get("store") || "");
      if (slug && !isSandboxSlug(slug)) {
        return { slug: slug, source: "merchant_activation_query" };
      }
    } catch (eMa) {
      /* ignore */
    }
    return { slug: "", source: "" };
  }

  function slugFromDomAttribute() {
    try {
      var m = document.querySelector("[data-cartflow-store]");
      if (m && m.getAttribute("data-cartflow-store")) {
        var slug = normalizeSlug(m.getAttribute("data-cartflow-store"));
        if (slug) {
          return { slug: slug, source: "dom_data_cartflow_store" };
        }
      }
    } catch (eDom) {
      /* ignore */
    }
    return { slug: "", source: "" };
  }

  function acceptCandidate(result, allowSandbox) {
    if (!result || !result.slug) {
      return null;
    }
    if (!allowSandbox && isSandboxSlug(result.slug)) {
      return null;
    }
    return result;
  }

  function logResolved(result) {
    try {
      console.log("[CF STORE SLUG RESOLVED]", {
        slug: result.slug,
        source: result.source,
      });
    } catch (eLog) {
      /* ignore */
    }
  }

  function logDemoFallback() {
    if (_demoFallbackLogged) {
      return;
    }
    _demoFallbackLogged = true;
    try {
      console.warn("[CF STORE SLUG FALLBACK DEMO]");
    } catch (eWarn) {
      /* ignore */
    }
  }

  function resolveStorefrontStoreSlug(opts) {
    opts = opts || {};
    var allowSandbox = opts.allowSandbox === true;

    try {
      if (
        !opts.skipWindowSlug &&
        typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
        window.CARTFLOW_STORE_SLUG !== null
      ) {
        var preset = normalizeSlug(window.CARTFLOW_STORE_SLUG);
        if (preset && (allowSandbox || !isSandboxSlug(preset))) {
          var presetResult = { slug: preset, source: "window_cartflow_store_slug" };
          logResolved(presetResult);
          return presetResult;
        }
      }
    } catch (ePreset) {
      /* ignore */
    }

    var loader = findWidgetLoaderScript();
    var chain = [
      slugFromScriptAttributes(loader),
      slugFromLoaderUrlQuery(loader),
      slugFromPlatformGlobals(),
      slugFromHostname(),
      slugFromMerchantActivationQuery(),
      slugFromDomAttribute(),
    ];

    var i;
    for (i = 0; i < chain.length; i++) {
      var hit = acceptCandidate(chain[i], allowSandbox);
      if (hit) {
        logResolved(hit);
        return hit;
      }
    }

    if (isPlatformStorefrontHost()) {
      try {
        console.warn("[CF STORE SLUG UNRESOLVED PLATFORM HOST]");
      } catch (ePlat) {}
      return { slug: "", source: "platform_host_unresolved" };
    }

    logDemoFallback();
    return { slug: "demo", source: "fallback_demo" };
  }

  function isPlatformStorefrontHost() {
    try {
      return !!extractSlugFromHostname(window.location.hostname);
    } catch (eHostChk) {
      return false;
    }
  }

  window.cartflowResolveStorefrontStoreSlug = resolveStorefrontStoreSlug;
  window.cartflowExtractStoreSlugFromHostname = extractSlugFromHostname;
})();
