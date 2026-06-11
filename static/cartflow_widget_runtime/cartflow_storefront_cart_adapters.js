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
      if (body && typeof body === "object") {
        zidCachedCartBody = body;
        zidCachedAt = Date.now();
      }
    },

    cacheCartItemResponse: function (body) {
      if (!body || typeof body !== "object") {
        return;
      }
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
      if (zidCachedCartBody && Date.now() - zidCachedAt < 15000) {
        var cached = normalizeZidCartApiBody(zidCachedCartBody, "zid_api_v1_cart_cached");
        if (cached.item_count > 0 && cached.cart_value > 0) {
          return Promise.resolve(cached);
        }
      }
      return self.fetchZidCartApi().then(function (fromApi) {
        if (fromApi && fromApi.item_count > 0 && fromApi.cart_value > 0) {
          return fromApi;
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
