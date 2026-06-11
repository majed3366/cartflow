/**
 * Storefront Cart Source Adapters — platform-specific cart readers (v1).
 *
 * Adapters NEVER post to CartFlow. They only detect platform context and read
 * normalized cart snapshots via readCart().
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var Contract = Cf.StorefrontCartBridgeContract || {};

  function num(v) {
    return Contract.num ? Contract.num(v) : null;
  }

  function str(v, maxLen) {
    return Contract.str ? Contract.str(v, maxLen) : null;
  }

  function stableCartflowCartId() {
    var key = "cartflow_cart_event_id";
    try {
      var existing = window.sessionStorage.getItem(key);
      if (existing && String(existing).trim()) {
        return String(existing).trim().slice(0, 255);
      }
    } catch (e0) {}
    var nid =
      typeof window.crypto !== "undefined" && window.crypto.randomUUID
        ? "cf_cart_" + window.crypto.randomUUID()
        : "cf_cart_" + String(Date.now()) + "_" + String(Math.random()).slice(2, 10);
    try {
      window.sessionStorage.setItem(key, nid);
    } catch (e1) {}
    return nid.slice(0, 255);
  }

  function resolveStoreSlug() {
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

  function resolveSessionId() {
    try {
      if (typeof window.cartflowGetSessionId === "function") {
        var sid = window.cartflowGetSessionId();
        if (sid) {
          return String(sid).trim();
        }
      }
    } catch (eS) {}
    try {
      if (Cf.Api && typeof Cf.Api.sessionId === "function") {
        var sid2 = Cf.Api.sessionId();
        if (sid2) {
          return String(sid2).trim();
        }
      }
    } catch (eA) {}
    return "";
  }

  function resolveCanonicalSlug() {
    try {
      if (window.CARTFLOW_CANONICAL_STORE_SLUG) {
        return String(window.CARTFLOW_CANONICAL_STORE_SLUG).trim();
      }
    } catch (eC) {}
    return null;
  }

  function logRawZid(body, sourceTag, phase) {
    body = body || {};
    var products = Array.isArray(body.products) ? body.products : [];
    try {
      console.log("[CF CART BRIDGE RAW ZID]", {
        timestamp: Date.now(),
        phase: phase || "unknown",
        source_tag: sourceTag || null,
        total_value: body.total_value,
        products_subtotal: body.products_subtotal,
        products_count: body.products_count,
        products_len: products.length,
        cart_id: body.id != null ? body.id : null,
        session_id: body.session_id != null ? body.session_id : null,
      });
    } catch (eLog) {}
  }

  function zidBodyMetrics(body) {
    body = body || {};
    var products = Array.isArray(body.products) ? body.products : [];
    var itemCount = num(body.products_count);
    if (itemCount == null) {
      itemCount = products.length;
    }
    var cartValue = num(body.total_value);
    if (cartValue == null) {
      cartValue = num(body.products_subtotal);
    }
    if (cartValue == null && body.total && typeof body.total === "object") {
      cartValue = num(body.total.value);
    }
    return {
      itemCount: itemCount != null ? itemCount : 0,
      cartValue: cartValue != null ? cartValue : 0,
      productsLen: products.length,
    };
  }

  function zidBodyIsPopulated(body) {
    var m = zidBodyMetrics(body);
    return m.cartValue > 0 && m.itemCount > 0;
  }

  function zidBodyIsEmpty(body) {
    var m = zidBodyMetrics(body);
    return m.cartValue <= 0 && m.itemCount <= 0;
  }

  function mapZidProducts(products) {
    var items = [];
    var i;
    for (i = 0; i < (products || []).length; i++) {
      var p = products[i] || {};
      var qty = num(p.quantity);
      if (qty == null || qty <= 0) {
        qty = 1;
      }
      var unit =
        num(p.price) != null
          ? num(p.price)
          : num(p.net_price) != null
          ? num(p.net_price)
          : num(p.gross_price);
      var total =
        num(p.total) != null
          ? num(p.total)
          : unit != null
          ? unit * qty
          : null;
      var img = null;
      try {
        if (p.images && p.images[0]) {
          img =
            p.images[0].origin ||
            (p.images[0].thumbs && p.images[0].thumbs.small) ||
            null;
        }
      } catch (eI) {}
      items.push({
        product_id: str(p.product_id || p.id, 128),
        variant_id: str(p.parent_id, 128),
        name: str(p.name, 255),
        quantity: qty,
        unit_price: unit,
        total_price: total,
        image_url: str(img, 512),
        product_url: str(p.url, 512),
      });
    }
    return items;
  }

  function normalizeZidCartApiBody(body, source) {
    body = body || {};
    logRawZid(body, source || "zid_api_v1_cart", "normalizeZidCartApiBody");
    var products = Array.isArray(body.products) ? body.products : [];
    var items = mapZidProducts(products);
    var itemCount =
      num(body.products_count) != null
        ? num(body.products_count)
        : items.length;
    var cartValue =
      num(body.total_value) != null
        ? num(body.total_value)
        : num(body.products_subtotal) != null
        ? num(body.products_subtotal)
        : null;
    if (cartValue == null && body.total && typeof body.total === "object") {
      cartValue = num(body.total.value);
    }
    var currency = null;
    try {
      currency =
        (body.currency &&
          body.currency.cart_currency &&
          body.currency.cart_currency.code) ||
        null;
    } catch (eCur) {}
    var token = str(body.id || body.session_id, 255);
    return {
      platform: "zid",
      store_slug: resolveStoreSlug(),
      canonical_store_slug: resolveCanonicalSlug(),
      session_id: resolveSessionId(),
      cart_id: stableCartflowCartId(),
      cart_token: token,
      cart_value: cartValue != null ? cartValue : 0,
      currency: currency,
      item_count: itemCount != null ? itemCount : items.length,
      items: items,
      source: source || "zid_api_v1_cart",
      observed_at: Date.now(),
      raw_source: { zid_cart_id: token },
    };
  }

  // ---------------------------------------------------------------------------
  // Zid adapter
  // ---------------------------------------------------------------------------

  var zidCachedCartBody = null;
  var zidCachedAt = 0;

  var zidStorefrontCartAdapter = {
    sourceName: "zid",
    platform: "zid",

    canHandle: function () {
      try {
        return /\.zid\.store$/i.test(String(window.location.hostname || ""));
      } catch (eH) {
        return false;
      }
    },

    detect: function () {
      return this.canHandle();
    },

    cacheCartBody: function (body) {
      if (!body || typeof body !== "object") {
        return;
      }
      logRawZid(body, "cacheCartBody", "cacheCartBody");
      if (
        zidCachedCartBody &&
        zidBodyIsPopulated(zidCachedCartBody) &&
        zidBodyIsEmpty(body)
      ) {
        try {
          console.log("[CF CART BRIDGE CACHE KEEP]", {
            reason: "ignore_empty_overwrite",
            kept_products_count: zidBodyMetrics(zidCachedCartBody).itemCount,
            kept_total_value: zidBodyMetrics(zidCachedCartBody).cartValue,
          });
        } catch (eKeep) {}
        return;
      }
      var m = zidBodyMetrics(body);
      try {
        console.log("[CF CART BRIDGE CACHE UPDATE]", {
          products_count: m.itemCount,
          total_value: m.cartValue,
          products_len: m.productsLen,
        });
      } catch (eUp) {}
      zidCachedCartBody = body;
      zidCachedAt = Date.now();
    },

    cacheCartItemResponse: function (body) {
      if (!body || typeof body !== "object") {
        return;
      }
      logRawZid(body, "post_cart_items_raw", "cacheCartItemResponse_in");
      var item = body.item;
      if (!item) {
        return;
      }
      var partial = {
        products: [item],
        products_count: num(body.cart_items_quantity) || 1,
        total_value: num(item.price) != null ? num(item.price) : num(item.total),
        products_subtotal: num(item.price),
      };
      logRawZid(partial, "cacheCartItemResponse_partial", "cacheCartItemResponse_out");
      this.cacheCartBody(partial);
    },

    readGlobalFallback: function () {
      try {
        if (Array.isArray(window.cart) && window.cart.length > 0) {
          var items = [];
          var sum = 0;
          var i;
          for (i = 0; i < window.cart.length; i++) {
            var row = window.cart[i] || {};
            var p = num(row.price != null ? row.price : row.unit_price);
            var q = num(row.qty != null ? row.qty : row.quantity);
            if (q == null) {
              q = 1;
            }
            if (p != null) {
              sum += p * q;
            }
            items.push({
              product_id: str(row.product_id || row.id, 128),
              name: str(row.name || row.title, 255),
              quantity: q,
              unit_price: p,
              total_price: p != null ? p * q : null,
            });
          }
          return {
            platform: "zid",
            store_slug: resolveStoreSlug(),
            canonical_store_slug: resolveCanonicalSlug(),
            session_id: resolveSessionId(),
            cart_id: stableCartflowCartId(),
            cart_token: null,
            cart_value: typeof window.cart_total === "number" ? window.cart_total : sum,
            currency: null,
            item_count: items.length,
            items: items,
            source: "window_cart_fallback",
            observed_at: Date.now(),
          };
        }
      } catch (eG) {}
      return null;
    },

    fetchZidCartApi: function () {
      var self = this;
      if (typeof window.fetch !== "function") {
        return Promise.resolve(null);
      }
      var url = "/api/v1/cart";
      try {
        url = new URL("/api/v1/cart", window.location.origin).href;
      } catch (eU) {}
      return window
        .fetch(url, { credentials: "same-origin", cache: "no-store" })
        .then(function (r) {
          if (!r.ok) {
            return null;
          }
          return r.json();
        })
        .then(function (body) {
          if (body && typeof body === "object") {
            self.cacheCartBody(body);
            if (zidBodyIsPopulated(body)) {
              return normalizeZidCartApiBody(body, "zid_api_v1_cart");
            }
            if (zidCachedCartBody && zidBodyIsPopulated(zidCachedCartBody)) {
              return normalizeZidCartApiBody(
                zidCachedCartBody,
                "zid_api_v1_cart_cached"
              );
            }
            return normalizeZidCartApiBody(body, "zid_api_v1_cart");
          }
          return null;
        })
        .catch(function () {
          return null;
        });
    },

    readCart: function () {
      var self = this;
      try {
        console.log("[CF CART BRIDGE TIMING]", {
          step: "readCart_start",
          timestamp: Date.now(),
          cache_age_ms:
            zidCachedAt > 0 ? Date.now() - zidCachedAt : null,
          has_cache: !!zidCachedCartBody,
        });
      } catch (eRc) {}
      if (zidCachedCartBody && Date.now() - zidCachedAt < 15000) {
        var cached = normalizeZidCartApiBody(zidCachedCartBody, "zid_api_v1_cart_cached");
        if (cached.item_count > 0 && cached.cart_value > 0) {
          try {
            console.log("[CF CART BRIDGE TIMING]", {
              step: "readCart_cache_hit",
              timestamp: Date.now(),
              source: "zid_api_v1_cart_cached",
              cart_value: cached.cart_value,
              item_count: cached.item_count,
            });
          } catch (eHit) {}
          return Promise.resolve(cached);
        }
        try {
          console.log("[CF CART BRIDGE TIMING]", {
            step: "readCart_cache_miss_low_value",
            timestamp: Date.now(),
            cart_value: cached.cart_value,
            item_count: cached.item_count,
          });
        } catch (eMiss) {}
      }
      try {
        console.log("[CF CART BRIDGE TIMING]", {
          step: "fetchZidCartApi_start",
          timestamp: Date.now(),
        });
      } catch (eFs) {}
      return self.fetchZidCartApi().then(function (fromApi) {
        if (fromApi && fromApi.item_count > 0 && fromApi.cart_value > 0) {
          return fromApi;
        }
        if (zidCachedCartBody && Date.now() - zidCachedAt < 15000) {
          var recheck = normalizeZidCartApiBody(
            zidCachedCartBody,
            "zid_api_v1_cart_cached"
          );
          if (recheck.item_count > 0 && recheck.cart_value > 0) {
            return recheck;
          }
        }
        var fb = self.readGlobalFallback();
        if (fb && fb.item_count > 0 && fb.cart_value > 0) {
          return fb;
        }
        return fromApi || fb || null;
      });
    },

    normalize: function (raw) {
      if (!raw) {
        return null;
      }
      if (raw.platform === "zid" && raw.items) {
        return raw;
      }
      if (raw.products) {
        return normalizeZidCartApiBody(raw, "zid_normalize");
      }
      return null;
    },
  };

  // ---------------------------------------------------------------------------
  // Stubs — same interface, not yet implemented
  // ---------------------------------------------------------------------------

  function stubAdapter(name) {
    return {
      sourceName: name,
      platform: name,
      canHandle: function () {
        return false;
      },
      detect: function () {
        return false;
      },
      readCart: function () {
        return Promise.resolve(null);
      },
      normalize: function () {
        return null;
      },
    };
  }

  var genericStorefrontCartAdapter = {
    sourceName: "generic",
    platform: "generic",
    canHandle: function () {
      return true;
    },
    detect: function () {
      return true;
    },
    readCart: function () {
      var zid = zidStorefrontCartAdapter;
      if (zid.canHandle()) {
        return zid.readCart();
      }
      var fb = zid.readGlobalFallback();
      if (fb) {
        fb.platform = "generic";
        fb.source = "window_cart_generic";
        return Promise.resolve(fb);
      }
      return Promise.resolve(null);
    },
    normalize: function (raw) {
      return raw;
    },
  };

  Cf.StorefrontCartAdapters = {
    list: function () {
      return [
        zidStorefrontCartAdapter,
        stubAdapter("salla"),
        stubAdapter("shopify"),
        genericStorefrontCartAdapter,
      ];
    },
    select: function () {
      var adapters = Cf.StorefrontCartAdapters.list();
      var i;
      for (i = 0; i < adapters.length; i++) {
        if (adapters[i].canHandle && adapters[i].canHandle()) {
          return adapters[i];
        }
      }
      return genericStorefrontCartAdapter;
    },
    zid: zidStorefrontCartAdapter,
    generic: genericStorefrontCartAdapter,
  };
})();
