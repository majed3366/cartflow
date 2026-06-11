/**
 * Storefront Cart Bridge — platform-agnostic normalized cart contract (v1).
 *
 * Adapters produce NormalizedStorefrontCart payloads; Cart Bridge Core validates
 * and posts to POST /api/cart-event. Recovery core stays platform-neutral.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;

  function num(v) {
    if (typeof v === "number") {
      return isFinite(v) ? v : null;
    }
    if (v == null || v === "") {
      return null;
    }
    var n = Number(String(v).replace(/[^0-9.\-]/g, ""));
    return isFinite(n) ? n : null;
  }

  function str(v, maxLen) {
    var s = String(v == null ? "" : v).trim();
    if (!s) {
      return null;
    }
    return maxLen ? s.slice(0, maxLen) : s;
  }

  /**
   * @typedef {Object} NormalizedStorefrontCartItem
   * @property {string|null} product_id
   * @property {string|null} variant_id
   * @property {string|null} name
   * @property {number|null} quantity
   * @property {number|null} unit_price
   * @property {number|null} total_price
   * @property {string|null} image_url
   * @property {string|null} product_url
   */

  /**
   * Required normalized cart payload for persistence.
   * @typedef {Object} NormalizedStorefrontCart
   * @property {string} platform
   * @property {string} store_slug
   * @property {string|null} canonical_store_slug
   * @property {string} session_id
   * @property {string} cart_id
   * @property {string|null} cart_token
   * @property {number} cart_value
   * @property {string|null} currency
   * @property {number} item_count
   * @property {Array<Object>} items
   * @property {string} source
   * @property {number} observed_at
   */

  function normalizeItem(raw) {
    raw = raw || {};
    return {
      product_id: str(raw.product_id, 128),
      variant_id: str(raw.variant_id, 128),
      name: str(raw.name, 255),
      quantity: num(raw.quantity),
      unit_price: num(raw.unit_price),
      total_price: num(raw.total_price),
      image_url: str(raw.image_url, 512),
      product_url: str(raw.product_url, 512),
    };
  }

  function legacyCartArrayFromItems(items) {
    var out = [];
    var i;
    for (i = 0; i < (items || []).length; i++) {
      var it = items[i] || {};
      out.push({
        name: it.name || "",
        qty: it.quantity != null ? it.quantity : 1,
        quantity: it.quantity != null ? it.quantity : 1,
        price: it.unit_price != null ? it.unit_price : it.total_price,
        product_id: it.product_id || undefined,
        url: it.product_url || undefined,
      });
    }
    return out;
  }

  /**
   * Validate normalized cart for persistence. Returns { ok, errors[], cart }.
   */
  function validateNormalizedCart(raw) {
    var errors = [];
    var cart = raw && typeof raw === "object" ? raw : {};
    var storeSlug = str(cart.store_slug, 255);
    var sessionId = str(cart.session_id, 512);
    var cartId = str(cart.cart_id, 255);
    var cartValue = num(cart.cart_value);
    var itemCount = num(cart.item_count);
    if (!storeSlug) {
      errors.push("missing_store_slug");
    }
    if (!sessionId) {
      errors.push("missing_session_id");
    }
    if (!cartId) {
      errors.push("missing_cart_id");
    }
    if (cartValue == null) {
      errors.push("missing_cart_value");
    }
    if (itemCount == null) {
      itemCount = Array.isArray(cart.items) ? cart.items.length : 0;
    }
    if (cartValue != null && cartValue <= 0) {
      errors.push("empty_cart_value");
    }
    if (itemCount <= 0) {
      errors.push("empty_item_count");
    }
    return {
      ok: errors.length === 0,
      errors: errors,
      cart: {
        platform: str(cart.platform, 32) || "generic",
        store_slug: storeSlug || "",
        canonical_store_slug: str(cart.canonical_store_slug, 255),
        session_id: sessionId || "",
        cart_id: cartId || "",
        cart_token: str(cart.cart_token, 255),
        cart_value: cartValue != null ? cartValue : 0,
        currency: str(cart.currency, 16),
        item_count: itemCount,
        items: Array.isArray(cart.items)
          ? cart.items.map(normalizeItem)
          : [],
        source: str(cart.source, 64) || "unknown",
        observed_at:
          typeof cart.observed_at === "number" ? cart.observed_at : Date.now(),
      },
    };
  }

  function dedupeKey(cart) {
    return [
      cart.canonical_store_slug || cart.store_slug || "",
      cart.session_id || "",
      cart.cart_id || "",
      cart.cart_token || "",
      String(cart.item_count != null ? cart.item_count : ""),
      cart.cart_value != null ? cart.cart_value.toFixed(4) : "",
      cart.source || "",
    ].join("|");
  }

  function toCartEventPayload(cart, reason) {
    var r = String(reason || "add").toLowerCase();
    var allowed = { add: 1, remove: 1, clear: 1, abandon: 1, page_load: 1 };
    if (!allowed[r]) {
      r = "add";
    }
    return {
      event: "cart_state_sync",
      reason: r,
      store: cart.store_slug,
      session_id: cart.session_id,
      cart_id: cart.cart_id,
      cart_total: cart.cart_value,
      items_count: cart.item_count,
      cart: legacyCartArrayFromItems(cart.items),
      cf_storefront_cart_bridge: {
        platform: cart.platform,
        canonical_store_slug: cart.canonical_store_slug,
        cart_token: cart.cart_token,
        source: cart.source,
        observed_at: cart.observed_at,
        currency: cart.currency,
      },
    };
  }

  Cf.StorefrontCartBridgeContract = {
    num: num,
    str: str,
    normalizeItem: normalizeItem,
    validateNormalizedCart: validateNormalizedCart,
    dedupeKey: dedupeKey,
    toCartEventPayload: toCartEventPayload,
    legacyCartArrayFromItems: legacyCartArrayFromItems,
  };
})();
