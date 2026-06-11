/**
 * Platform-neutral Cart Event Bridge.
 *
 * Architecture:
 *   Platform Cart Sources (adapters)
 *     -> Cart Event Bridge (normalize + dedupe)
 *       -> Normalized CartFlowCartEvent
 *         -> Trigger Orchestrator (Cf.Triggers.onNormalizedCartEvent)
 *           -> Widget display rules (gates inside orchestrator)
 *
 * Adapters ONLY emit normalized cart events. They never open the widget.
 * The Trigger Orchestrator alone decides display (Enable / Exit Intent /
 * Hesitation / Delay / Frequency / Suppression gates are unchanged).
 *
 * Normalized contract (CartFlowCartEvent):
 *   {
 *     source_platform: "zid" | "salla" | "shopify" | "generic",
 *     event_type: "cart_detected" | "add_to_cart" | "cart_updated"
 *                 | "cart_removed" | "cart_empty",
 *     store_slug, session_id, cart_id?, cart_total?, currency?, items_count?,
 *     product_id?, product_name?, product_price?, raw_source?,
 *     detected_by: "platform_api" | "dom_observer" | "network_intercept"
 *                  | "url_cart_page" | "manual_bridge",
 *     timestamp
 *   }
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;

  var ARM_EVENT_TYPES = {
    add_to_cart: 1,
    cart_detected: 1,
    cart_updated: 1,
  };

  var bridgeState = {
    has_cart: false,
    last_event: null,
    last_event_at: null,
    hesitation_armed_from_cart_event: false,
    sources_started: [],
  };

  var started = false;
  var lastDispatchKey = "";
  var lastDispatchAt = 0;
  var lastBackendSyncKey = "";
  var lastBackendSyncAt = 0;
  var BACKEND_SYNC_DEBOUNCE_MS = 2000;

  function blog(tag, meta) {
    try {
      if (meta !== undefined && meta !== null) {
        console.log(tag, meta);
      } else {
        console.log(tag);
      }
    } catch (eL) {}
  }

  function num(v) {
    if (typeof v === "number") {
      return isFinite(v) ? v : undefined;
    }
    if (v == null || v === "") {
      return undefined;
    }
    var n = Number(String(v).replace(/[^0-9.\-]/g, ""));
    return isFinite(n) ? n : undefined;
  }

  function sessionId() {
    try {
      if (typeof window.cartflowGetSessionId === "function") {
        var s = window.cartflowGetSessionId();
        if (s) {
          return String(s);
        }
      }
    } catch (eS) {}
    try {
      if (window.CARTFLOW_SESSION_ID) {
        return String(window.CARTFLOW_SESSION_ID);
      }
    } catch (eS2) {}
    return "";
  }

  function storeSlug() {
    try {
      if (Cf.Api && typeof Cf.Api.storeSlug === "function") {
        var s = Cf.Api.storeSlug();
        if (s) {
          return String(s).trim();
        }
      }
    } catch (eA) {}
    try {
      if (window.CARTFLOW_STORE_SLUG) {
        return String(window.CARTFLOW_STORE_SLUG).trim();
      }
    } catch (eW) {}
    return "";
  }

  function normalizeEvent(raw) {
    raw = raw || {};
    var evt = {
      source_platform: String(raw.source_platform || "generic"),
      event_type: String(raw.event_type || "cart_updated"),
      store_slug: raw.store_slug != null ? String(raw.store_slug) : storeSlug(),
      session_id: raw.session_id != null ? String(raw.session_id) : sessionId(),
      detected_by: String(raw.detected_by || "manual_bridge"),
      timestamp: typeof raw.timestamp === "number" ? raw.timestamp : Date.now(),
    };
    var cartTotal = num(raw.cart_total);
    var itemsCount = num(raw.items_count);
    var productPrice = num(raw.product_price);
    if (raw.cart_id != null) {
      evt.cart_id = String(raw.cart_id);
    }
    if (cartTotal !== undefined) {
      evt.cart_total = cartTotal;
    }
    if (raw.currency != null) {
      evt.currency = String(raw.currency);
    }
    if (itemsCount !== undefined) {
      evt.items_count = itemsCount;
    }
    if (raw.product_id != null) {
      evt.product_id = String(raw.product_id);
    }
    if (raw.product_name != null) {
      evt.product_name = String(raw.product_name).slice(0, 200);
    }
    if (productPrice !== undefined) {
      evt.product_price = productPrice;
    }
    if (raw.raw_source && typeof raw.raw_source === "object") {
      evt.raw_source = raw.raw_source;
    }
    return evt;
  }

  function cartDetectedFromEvent(evt) {
    if (evt.event_type === "cart_removed" || evt.event_type === "cart_empty") {
      return false;
    }
    if (typeof evt.items_count === "number") {
      return evt.items_count > 0;
    }
    if (typeof evt.cart_total === "number") {
      return evt.cart_total > 0;
    }
    return ARM_EVENT_TYPES[evt.event_type] === 1;
  }

  function routeToOrchestrator(evt) {
    try {
      if (Cf.Triggers && typeof Cf.Triggers.onNormalizedCartEvent === "function") {
        var armed = Cf.Triggers.onNormalizedCartEvent(evt);
        if (armed === true) {
          bridgeState.hesitation_armed_from_cart_event = true;
        }
      }
    } catch (eR) {}
  }

  function syncBackendCartState(evt) {
    if (!evt) {
      return;
    }
    var persistTypes = { add_to_cart: 1, cart_updated: 1, cart_detected: 1 };
    if (!persistTypes[evt.event_type]) {
      return;
    }
    var key =
      "backend_sync|" +
      evt.event_type +
      "|" +
      (evt.session_id || "") +
      "|" +
      (evt.cart_id || "") +
      "|" +
      (evt.items_count != null ? evt.items_count : "") +
      "|" +
      (evt.cart_total != null ? evt.cart_total : "");
    var now = Date.now();
    if (
      key === lastBackendSyncKey &&
      now - lastBackendSyncAt < BACKEND_SYNC_DEBOUNCE_MS
    ) {
      return;
    }
    lastBackendSyncKey = key;
    lastBackendSyncAt = now;
    try {
      if (
        Cf.StorefrontCartBridge &&
        typeof Cf.StorefrontCartBridge.persistFromTrigger === "function"
      ) {
        blog("[CF CART EVENT BRIDGE BACKEND SYNC]", {
          event_type: evt.event_type,
          store_slug: evt.store_slug,
          session_id: evt.session_id,
          path: "storefront_cart_bridge_core",
        });
        Cf.StorefrontCartBridge.persistFromTrigger(evt);
        return;
      }
    } catch (eBridge) {}
    try {
      if (typeof window.cartflowSyncCartState === "function") {
        blog("[CF CART EVENT BRIDGE BACKEND SYNC]", {
          event_type: evt.event_type,
          store_slug: evt.store_slug,
          session_id: evt.session_id,
          reason: "add",
          path: "legacy_window_cart",
        });
        window.cartflowSyncCartState("add");
      }
    } catch (eSync) {}
  }

  /** Bridge entry: adapters call this with a (possibly partial) event. */
  function emit(raw) {
    var evt = normalizeEvent(raw);
    var detected = cartDetectedFromEvent(evt);
    bridgeState.has_cart = detected;
    bridgeState.last_event = evt;
    bridgeState.last_event_at = evt.timestamp;

    blog("[CF CART EVENT NORMALIZED]", {
      source_platform: evt.source_platform,
      event_type: evt.event_type,
      store_slug: evt.store_slug,
      session_id: evt.session_id,
      cart_total: evt.cart_total != null ? evt.cart_total : null,
      items_count: evt.items_count != null ? evt.items_count : null,
      detected_by: evt.detected_by,
    });

    var key =
      evt.event_type +
      "|" +
      (evt.items_count != null ? evt.items_count : "") +
      "|" +
      (evt.cart_total != null ? evt.cart_total : "");
    var now = Date.now();
    if (key === lastDispatchKey && now - lastDispatchAt < 1500) {
      return evt;
    }
    lastDispatchKey = key;
    lastDispatchAt = now;

    blog("[CF CART EVENT BRIDGE DISPATCH]", {
      event_type: evt.event_type,
      routed_to: "trigger_orchestrator",
    });

    routeToOrchestrator(evt);
    syncBackendCartState(evt);
    return evt;
  }

  /** Shared helper for adapters: logs [CF CART EVENT SOURCE] then emits. */
  function reportSignal(platform, detectedBy, eventType, extra) {
    extra = extra || {};
    var cartDetected =
      eventType !== "cart_removed" && eventType !== "cart_empty";
    blog("[CF CART EVENT SOURCE]", {
      source_platform: platform,
      detected_by: detectedBy,
      event_type: eventType,
      items_count: extra.items_count != null ? extra.items_count : null,
      cart_total: extra.cart_total != null ? extra.cart_total : null,
      cart_detected: cartDetected,
    });
    return emit({
      source_platform: platform,
      event_type: eventType,
      detected_by: detectedBy,
      items_count: extra.items_count,
      cart_total: extra.cart_total,
      cart_id: extra.cart_id,
      currency: extra.currency,
      product_id: extra.product_id,
      product_name: extra.product_name,
      product_price: extra.product_price,
      raw_source: extra.raw_source,
    });
  }

  function hasCart() {
    return bridgeState.has_cart === true;
  }

  /** Read-only snapshot consumed by the runtime-truth beacon. */
  function getState() {
    var e = bridgeState.last_event || {};
    return {
      last_event_type: e.event_type != null ? e.event_type : null,
      last_event_source_platform: e.source_platform != null ? e.source_platform : null,
      last_detected_by: e.detected_by != null ? e.detected_by : null,
      last_items_count: e.items_count != null ? e.items_count : null,
      last_cart_total: e.cart_total != null ? e.cart_total : null,
      last_event_at: bridgeState.last_event_at != null ? bridgeState.last_event_at : null,
      hesitation_armed_from_cart_event:
        bridgeState.hesitation_armed_from_cart_event === true,
      sources_started: bridgeState.sources_started.slice(),
    };
  }

  var api = {
    emit: emit,
    reportSignal: reportSignal,
    hasCart: hasCart,
    getState: getState,
    storeSlug: storeSlug,
    sessionId: sessionId,
  };

  // ---------------------------------------------------------------------------
  // Platform detection + auto-start
  // ---------------------------------------------------------------------------

  function shouldAutoStart() {
    try {
      var p = String(window.location.pathname || "");
      if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
        return false;
      }
    } catch (eP) {}
    return true;
  }

  function detectPlatform() {
    var h = "";
    try {
      h = String(window.location.hostname || "").toLowerCase();
    } catch (eH) {}
    if (/\.zid\.store$/.test(h)) {
      return "zid";
    }
    if (/\.salla\.(sa|store)$/.test(h) || /(^|\.)salla\./.test(h)) {
      return "salla";
    }
    if (/\.myshopify\.com$/.test(h) || /(^|\.)shopify\./.test(h)) {
      return "shopify";
    }
    return "generic";
  }

  function start() {
    if (started) {
      return;
    }
    started = true;
    if (!shouldAutoStart()) {
      return;
    }
    var plat = detectPlatform();
    var Sources = Cf.CartSources || {};
    var adapter =
      Sources[plat + "CartEventSource"] || Sources.genericCartEventSource;
    try {
      if (adapter && typeof adapter.init === "function") {
        adapter.init(api);
        bridgeState.sources_started.push(plat);
        blog("[CF CART BRIDGE STARTED]", {
          source_platform: plat,
          detected_host: (function () {
            try {
              return window.location.hostname;
            } catch (e) {
              return "";
            }
          })(),
        });
      }
    } catch (eStart) {
      try {
        console.warn("[CF CART BRIDGE WARN]", "adapter_init_failed", eStart);
      } catch (eW) {}
    }
  }

  function scheduleStart() {
    try {
      setTimeout(start, 0);
    } catch (e0) {}
    try {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, false);
      }
      window.addEventListener("load", start, false);
    } catch (eEv) {}
  }

  Cf.CartBridge = {
    emit: emit,
    reportSignal: reportSignal,
    hasCart: hasCart,
    getState: getState,
    start: start,
    storeSlug: storeSlug,
    sessionId: sessionId,
  };

  scheduleStart();
})();
