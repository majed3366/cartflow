/**
 * Platform Cart Event Sources (adapters).
 *
 * Each adapter implements the same interface:
 *   { platform: string, init: function(bridge) { ... } }
 *
 * Adapters ONLY detect platform-specific cart signals and call
 * `bridge.reportSignal(platform, detected_by, event_type, extra)`.
 * They never open the widget and contain no business/display logic.
 *
 * Zid is fully implemented. Salla/Shopify are interface stubs (architecture
 * ready, detection intentionally not implemented yet). Generic is a light,
 * platform-neutral fallback for custom storefronts.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;

  function warn(tag, e) {
    try {
      console.warn("[CF CART SOURCE WARN]", tag, e);
    } catch (eW) {}
  }

  function textNum(s) {
    var n = Number(String(s == null ? "" : s).replace(/[^0-9.\-]/g, ""));
    return isFinite(n) ? n : null;
  }

  function closestMatch(el, selector) {
    try {
      if (el && typeof el.closest === "function") {
        return el.closest(selector);
      }
    } catch (eC) {}
    return null;
  }

  function isCartPagePath() {
    try {
      var p = String(window.location.pathname || "").toLowerCase();
      var href = String(window.location.href || "").toLowerCase();
      return (
        /\/cart(?:[\/?#]|$)/.test(p) ||
        /\/checkout(?:[\/?#]|$)/.test(p) ||
        /\/basket(?:[\/?#]|$)/.test(p) ||
        /\/(cart|checkout|basket)(?:[\/?#]|$)/.test(href)
      );
    } catch (eP) {
      return false;
    }
  }

  var ADD_TO_CART_SELECTOR = [
    "[data-add-to-cart]",
    "[data-action='add-to-cart']",
    ".add-to-cart",
    ".btn-add-to-cart",
    ".product-add-to-cart",
    "button[name='add']",
    "a[href*='cart/add' i]",
    "[onclick*='addToCart' i]",
    "[onclick*='add_to_cart' i]",
    "[class*='add-to-cart' i]",
    "[class*='add_to_cart' i]",
  ].join(",");

  var ADD_TO_CART_TEXT = /(add to cart|add to bag|أضف(?:ها)?\s*(?:إلى|الى|ل)?\s*(?:السلة|العربة|سلة)|اضف\s*للسلة|أضف\s*للسلة|加入购物车)/i;

  var CART_COUNT_SELECTOR = [
    "[data-cart-count]",
    "[data-cart-items-count]",
    ".cart-count",
    ".cart-counter",
    ".cart-badge",
    ".header-cart .count",
    ".mini-cart-count",
    "[class*='cart' i] [class*='count' i]",
    "[class*='cart' i] [class*='badge' i]",
  ].join(",");

  var CART_ITEM_SELECTOR = [
    ".cart-item",
    "[data-cart-item]",
    ".cart-products .product",
    "tr.cart-row",
    ".shopping-cart .item",
    "li.cart-line",
  ].join(",");

  var CART_NETWORK_RE =
    /(cart\/add|add[-_]?to[-_]?cart|addproduct|update[-_]?cart|\/cart\b|\/api\/.*cart|\/checkout\/)/i;

  // ---------------------------------------------------------------------------
  // Zid adapter (fully implemented, layered detection)
  // ---------------------------------------------------------------------------

  // During the initial page-load window, count-based layers only hydrate the
  // baseline (state only); they never dispatch a normalized cart event. This
  // prevents the existing cart from looking like a fresh add-to-cart on load.
  var ZID_LOAD_WINDOW_MS = 3000;

  var zidCartEventSource = {
    platform: "zid",
    _bridge: null,
    _lastCount: null,
    _lastTotal: null,
    _hydrated: false,
    _loadWindowActive: true,
    _globalsTries: 0,

    init: function (bridge) {
      this._bridge = bridge;
      var self = this;
      try {
        setTimeout(function () {
          self._loadWindowActive = false;
        }, ZID_LOAD_WINDOW_MS);
      } catch (eW) {
        this._loadWindowActive = false;
      }
      this._pollGlobals();
      this._scanCartDom();
      this._urlHeuristic();
      this._installClickListener();
      this._installBadgeObserver();
      this._installNetworkObserver();
    },

    _signal: function (detectedBy, eventType, extra) {
      try {
        this._bridge.reportSignal("zid", detectedBy, eventType, extra || {});
      } catch (eS) {
        warn("zid_signal", eS);
      }
    },

    _diag: function (layerName, emittedType, count, total, reason) {
      var url = "";
      try {
        url = String(window.location.href || "").slice(0, 512);
      } catch (eU) {}
      try {
        console.log("[CF ZID DETECTION LAYER]", {
          layer_name: layerName,
          emitted_event_type: emittedType || null,
          cart_count: count != null ? count : null,
          cart_total: total != null ? total : null,
          page_url: url,
          trigger_reason: reason,
        });
      } catch (eD) {}
    },

    /**
     * Count/total-driven layers funnel through here. Root-cause guard against
     * false positives: the first observation (and anything during the initial
     * page-load window) ONLY hydrates baseline state — it never dispatches.
     * A normalized event is emitted afterwards only on a real cart mutation
     * (count increased/decreased, total changed, or emptied).
     */
    _maybeEmitFromCount: function (layerName, detectedBy, count, total) {
      if (count == null) {
        return;
      }
      if (this._loadWindowActive || !this._hydrated) {
        this._hydrated = true;
        this._lastCount = count;
        this._lastTotal = total != null ? total : this._lastTotal;
        this._diag(
          layerName,
          null,
          count,
          total,
          this._loadWindowActive
            ? "initial_load_window_hydration_only"
            : "post_load_baseline_hydration"
        );
        return;
      }
      var prevCount = this._lastCount;
      var prevTotal = this._lastTotal;
      var totalChanged =
        total != null && prevTotal != null && total !== prevTotal;
      if (count === prevCount && !totalChanged) {
        return;
      }
      this._lastCount = count;
      if (total != null) {
        this._lastTotal = total;
      }
      if (count <= 0) {
        if (prevCount != null && prevCount > 0) {
          this._diag(layerName, "cart_empty", count, total, "cart_emptied");
          this._signal(detectedBy, "cart_empty", {
            items_count: 0,
            cart_total: total,
          });
        }
        return;
      }
      var type;
      var reason;
      if (prevCount != null && count > prevCount) {
        type = "add_to_cart";
        reason = "cart_count_increased";
      } else if (prevCount != null && count < prevCount) {
        type = "cart_updated";
        reason = "cart_count_decreased";
      } else {
        type = "cart_updated";
        reason = "cart_total_changed";
      }
      this._diag(layerName, type, count, total, reason);
      this._signal(detectedBy, type, { items_count: count, cart_total: total });
    },

    // Layer 1: Zid global cart/store objects.
    _readGlobalCart: function () {
      try {
        if (Array.isArray(window.cart)) {
          return {
            count: window.cart.length,
            total: typeof window.cart_total === "number" ? window.cart_total : null,
          };
        }
        var c = window.cart;
        if (c && typeof c === "object") {
          var cnt =
            c.products_count != null
              ? Number(c.products_count)
              : Array.isArray(c.products)
              ? c.products.length
              : Array.isArray(c.items)
              ? c.items.length
              : null;
          var tot =
            c.total != null
              ? Number(c.total)
              : c.total_price != null
              ? Number(c.total_price)
              : null;
          if (cnt != null || tot != null) {
            return { count: cnt, total: tot };
          }
        }
        var z = window.zid || window.Zid;
        if (z && z.cart && typeof z.cart === "object") {
          var zc = z.cart;
          var zcnt =
            zc.products_count != null
              ? Number(zc.products_count)
              : Array.isArray(zc.products)
              ? zc.products.length
              : null;
          return {
            count: zcnt,
            total: zc.total != null ? Number(zc.total) : null,
          };
        }
      } catch (eG) {}
      return null;
    },

    _pollGlobals: function () {
      var self = this;
      function tick() {
        self._globalsTries += 1;
        var g = self._readGlobalCart();
        if (g && g.count != null) {
          self._maybeEmitFromCount("global_cart_object", "platform_api", g.count, g.total);
        }
        if (self._globalsTries < 20) {
          setTimeout(tick, 1000);
        }
      }
      try {
        setTimeout(tick, 0);
      } catch (eT) {}
    },

    // Layer 2: cart DOM on the cart page.
    _scanCartDom: function () {
      if (!isCartPagePath()) {
        return;
      }
      var self = this;
      function scan() {
        try {
          var rows = document.querySelectorAll(CART_ITEM_SELECTOR);
          if (rows && rows.length > 0) {
            self._maybeEmitFromCount("cart_page_dom", "dom_observer", rows.length, null);
          }
        } catch (eD) {}
      }
      try {
        setTimeout(scan, 300);
        setTimeout(scan, 1500);
      } catch (eS) {}
    },

    // Layer 3: add-to-cart button click detection.
    _installClickListener: function () {
      var self = this;
      try {
        document.addEventListener(
          "click",
          function (ev) {
            try {
              var t = ev.target;
              if (!t) {
                return;
              }
              var hit = closestMatch(t, ADD_TO_CART_SELECTOR);
              if (!hit) {
                var label = "";
                try {
                  label = String(
                    (t.textContent || t.value || t.getAttribute("aria-label") || "")
                  ).trim();
                } catch (eLbl) {}
                if (label && ADD_TO_CART_TEXT.test(label) && label.length <= 40) {
                  hit = t;
                }
              }
              if (!hit) {
                return;
              }
              // Explicit user action — always a real signal, even on first load.
              self._diag(
                "add_to_cart_click",
                "add_to_cart",
                self._lastCount,
                self._lastTotal,
                "explicit_add_to_cart_click"
              );
              self._signal("dom_observer", "add_to_cart", {});
              // Re-read globals shortly after the click resolves (baseline sync).
              setTimeout(function () {
                var g = self._readGlobalCart();
                if (g && g.count != null) {
                  self._maybeEmitFromCount(
                    "global_cart_object",
                    "platform_api",
                    g.count,
                    g.total
                  );
                }
              }, 1200);
            } catch (eClick) {}
          },
          true
        );
      } catch (eL) {
        warn("zid_click_listener", eL);
      }
    },

    // Layer 4: cart badge/count mutation observer.
    _installBadgeObserver: function () {
      var self = this;
      if (typeof window.MutationObserver !== "function") {
        return;
      }
      function readBadges() {
        try {
          var nodes = document.querySelectorAll(CART_COUNT_SELECTOR);
          var best = null;
          var i;
          for (i = 0; i < nodes.length; i++) {
            var v = textNum(nodes[i].textContent);
            if (v != null && (best == null || v > best)) {
              best = v;
            }
          }
          return best;
        } catch (eR) {
          return null;
        }
      }
      try {
        var initial = readBadges();
        if (initial != null) {
          self._maybeEmitFromCount("cart_badge_observer", "dom_observer", initial, null);
        }
        var obs = new MutationObserver(function () {
          var v = readBadges();
          if (v != null) {
            self._maybeEmitFromCount("cart_badge_observer", "dom_observer", v, null);
          }
        });
        obs.observe(document.documentElement || document.body, {
          subtree: true,
          childList: true,
          characterData: true,
        });
      } catch (eO) {
        warn("zid_badge_observer", eO);
      }
    },

    // Layer 5: network/fetch/XHR observer for cart requests (safe, non-blocking).
    _installNetworkObserver: function () {
      var self = this;
      // A cart request never dispatches by itself. It only re-reads the
      // authoritative cart, which emits solely on a real mutation. Only
      // mutating methods (or unknown) trigger the re-read; a GET /cart on
      // page load can no longer manufacture a false event.
      function onCartRequest(url, method) {
        try {
          if (!url || !CART_NETWORK_RE.test(String(url))) {
            return;
          }
          var m = String(method || "").toUpperCase();
          var mutating =
            m === "" ||
            m === "POST" ||
            m === "PUT" ||
            m === "PATCH" ||
            m === "DELETE";
          if (!mutating) {
            return;
          }
          setTimeout(function () {
            var g = self._readGlobalCart();
            if (g && g.count != null) {
              self._maybeEmitFromCount(
                "network_request",
                "network_intercept",
                g.count,
                g.total
              );
            }
          }, 800);
        } catch (eCr) {}
      }
      try {
        if (typeof window.fetch === "function" && !window.__cfCartFetchWrapped) {
          window.__cfCartFetchWrapped = true;
          var origFetch = window.fetch;
          window.fetch = function (input, init) {
            try {
              var url = typeof input === "string" ? input : input && input.url;
              var method =
                (init && init.method) ||
                (input && typeof input === "object" && input.method) ||
                "GET";
              onCartRequest(url, method);
            } catch (eF) {}
            return origFetch.apply(this, arguments);
          };
        }
      } catch (eFw) {
        warn("zid_fetch_wrap", eFw);
      }
      try {
        var XHR = window.XMLHttpRequest;
        if (XHR && XHR.prototype && !XHR.prototype.__cfCartWrapped) {
          XHR.prototype.__cfCartWrapped = true;
          var origOpen = XHR.prototype.open;
          XHR.prototype.open = function (method, url) {
            try {
              this.__cfCartUrl = url;
              this.__cfCartMethod = method;
            } catch (eU) {}
            return origOpen.apply(this, arguments);
          };
          var origSend = XHR.prototype.send;
          XHR.prototype.send = function () {
            try {
              var u = this.__cfCartUrl;
              var mth = this.__cfCartMethod;
              this.addEventListener("load", function () {
                onCartRequest(u, mth);
              });
            } catch (eSnd) {}
            return origSend.apply(this, arguments);
          };
        }
      } catch (eXw) {
        warn("zid_xhr_wrap", eXw);
      }
    },

    // Layer 6: URL/cart-page heuristic (fallback only).
    // Being on a cart page is NOT a cart mutation. This layer no longer
    // dispatches on load — it only records that we are on a cart page.
    // A normalized event still requires an explicit add or a real change.
    _urlHeuristic: function () {
      if (!isCartPagePath()) {
        return;
      }
      var self = this;
      setTimeout(function () {
        self._diag(
          "url_cart_page",
          null,
          self._lastCount,
          self._lastTotal,
          "url_fallback_no_emit_on_load"
        );
      }, 2500);
    },
  };

  // ---------------------------------------------------------------------------
  // Salla adapter — interface stub (architecture ready; not implemented yet).
  // ---------------------------------------------------------------------------

  var sallaCartEventSource = {
    platform: "salla",
    init: function (bridge) {
      this._bridge = bridge;
      try {
        console.log("[CF CART SOURCE STUB]", {
          source_platform: "salla",
          implemented: false,
          note: "interface ready; add Salla detection layers here",
        });
      } catch (eS) {}
    },
  };

  // ---------------------------------------------------------------------------
  // Shopify adapter — interface stub (architecture ready; not implemented yet).
  // ---------------------------------------------------------------------------

  var shopifyCartEventSource = {
    platform: "shopify",
    init: function (bridge) {
      this._bridge = bridge;
      try {
        console.log("[CF CART SOURCE STUB]", {
          source_platform: "shopify",
          implemented: false,
          note: "interface ready; add Shopify detection layers here",
        });
      } catch (eS) {}
    },
  };

  // ---------------------------------------------------------------------------
  // Generic adapter — light platform-neutral fallback for custom storefronts.
  // ---------------------------------------------------------------------------

  var genericCartEventSource = {
    platform: "generic",
    _bridge: null,

    init: function (bridge) {
      this._bridge = bridge;
      var self = this;
      // Add-to-cart click (selector + text heuristic only).
      try {
        document.addEventListener(
          "click",
          function (ev) {
            try {
              var t = ev.target;
              if (!t) {
                return;
              }
              var hit = closestMatch(t, ADD_TO_CART_SELECTOR);
              if (hit) {
                self._bridge.reportSignal("generic", "dom_observer", "add_to_cart", {});
              }
            } catch (eC) {}
          },
          true
        );
      } catch (eL) {
        warn("generic_click_listener", eL);
      }
      // URL cart-page fallback.
      try {
        if (isCartPagePath()) {
          setTimeout(function () {
            self._bridge.reportSignal("generic", "url_cart_page", "cart_detected", {});
          }, 2500);
        }
      } catch (eU) {}
    },
  };

  Cf.CartSources = {
    zidCartEventSource: zidCartEventSource,
    sallaCartEventSource: sallaCartEventSource,
    shopifyCartEventSource: shopifyCartEventSource,
    genericCartEventSource: genericCartEventSource,
  };
})();
