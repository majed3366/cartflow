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

  var zidCartEventSource = {
    platform: "zid",
    _bridge: null,
    _lastCount: null,
    _globalsTries: 0,

    init: function (bridge) {
      this._bridge = bridge;
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

    _maybeEmitFromCount: function (detectedBy, count, total) {
      if (count == null) {
        return;
      }
      if (this._lastCount != null && count === this._lastCount) {
        return;
      }
      var prev = this._lastCount;
      this._lastCount = count;
      if (count <= 0) {
        if (prev != null && prev > 0) {
          this._signal(detectedBy, "cart_empty", { items_count: 0, cart_total: total });
        }
        return;
      }
      var type =
        prev == null ? "cart_detected" : count > prev ? "add_to_cart" : "cart_updated";
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
          self._maybeEmitFromCount("platform_api", g.count, g.total);
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
            self._maybeEmitFromCount("dom_observer", rows.length, null);
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
              self._signal("dom_observer", "add_to_cart", {});
              // Re-read globals shortly after the click resolves.
              setTimeout(function () {
                var g = self._readGlobalCart();
                if (g && g.count != null) {
                  self._maybeEmitFromCount("platform_api", g.count, g.total);
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
          self._maybeEmitFromCount("dom_observer", initial, null);
        }
        var obs = new MutationObserver(function () {
          var v = readBadges();
          if (v != null) {
            self._maybeEmitFromCount("dom_observer", v, null);
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
      function onCartRequest(url) {
        try {
          if (!url || !CART_NETWORK_RE.test(String(url))) {
            return;
          }
          self._signal("network_intercept", "cart_updated", {});
          setTimeout(function () {
            var g = self._readGlobalCart();
            if (g && g.count != null) {
              self._maybeEmitFromCount("platform_api", g.count, g.total);
            }
          }, 800);
        } catch (eCr) {}
      }
      try {
        if (typeof window.fetch === "function" && !window.__cfCartFetchWrapped) {
          window.__cfCartFetchWrapped = true;
          var origFetch = window.fetch;
          window.fetch = function (input) {
            try {
              var url = typeof input === "string" ? input : input && input.url;
              onCartRequest(url);
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
            } catch (eU) {}
            return origOpen.apply(this, arguments);
          };
          var origSend = XHR.prototype.send;
          XHR.prototype.send = function () {
            try {
              var u = this.__cfCartUrl;
              this.addEventListener("load", function () {
                onCartRequest(u);
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
    _urlHeuristic: function () {
      if (!isCartPagePath()) {
        return;
      }
      var self = this;
      setTimeout(function () {
        // Only fire if no stronger signal already set the count.
        if (self._lastCount == null) {
          self._signal("url_cart_page", "cart_detected", {});
        }
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
