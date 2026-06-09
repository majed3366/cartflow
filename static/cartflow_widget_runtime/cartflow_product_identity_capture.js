/**
 * Product identity capture v1 — normalize storefront cart → CartLineEmitV1[].
 *
 * Additive only: exposes window.cartflowCaptureProductLines / cartflowAttachProductLines.
 * Never throws; on failure returns lines=[].
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var MAX_LINES = 20;

  function strTrim(v, maxLen) {
    if (v == null || v === "") {
      return "";
    }
    var s = String(v).trim();
    if (!s) {
      return "";
    }
    return s.length > maxLen ? s.slice(0, maxLen) : s;
  }

  function numPrice(v) {
    if (v == null || v === "") {
      return undefined;
    }
    if (typeof v === "number" && isFinite(v)) {
      return v;
    }
    var n = Number(String(v).replace(/[^0-9.\-]/g, ""));
    return isFinite(n) ? n : undefined;
  }

  function numQty(v) {
    if (v == null || v === "") {
      return 1;
    }
    if (typeof v === "number" && isFinite(v) && v >= 0) {
      return v > 0 ? v : 1;
    }
    var n = parseFloat(String(v));
    if (!isFinite(n) || n <= 0) {
      return 1;
    }
    return n;
  }

  function lineProductId(it) {
    var pid = strTrim(it.product_id, 128);
    if (pid) {
      return pid;
    }
    var prod = it.product;
    if (prod && typeof prod === "object") {
      pid = strTrim(prod.id, 128);
      if (pid) {
        return pid;
      }
    }
    var vid = strTrim(it.variant_id, 128);
    var rawId = strTrim(it.id, 128);
    if (rawId && !vid) {
      return rawId;
    }
    return "";
  }

  function lineVariantId(it) {
    return strTrim(it.variant_id, 128);
  }

  function lineSku(it) {
    return strTrim(it.sku || it.product_num, 128);
  }

  function lineName(it) {
    var n =
      it.name ||
      it.title ||
      it.product_name ||
      (it.product && it.product.name) ||
      "";
    return strTrim(n, 200);
  }

  function lineUnitPrice(it) {
    var p =
      it.unit_price != null
        ? it.unit_price
        : it.price != null
        ? it.price
        : it.sale_price != null
        ? it.sale_price
        : it.amount != null
        ? it.amount
        : it.line_price != null
        ? it.line_price
        : it.total;
    return numPrice(p);
  }

  function normalizeLineItem(raw) {
    if (!raw || typeof raw !== "object") {
      return null;
    }
    var name = lineName(raw);
    var productId = lineProductId(raw);
    var variantId = lineVariantId(raw);
    var sku = lineSku(raw);
    var unitPrice = lineUnitPrice(raw);
    var quantity = numQty(raw.quantity != null ? raw.quantity : raw.qty);

    if (!name && !productId && !variantId && !sku) {
      return null;
    }

    var out = { name: name || "", quantity: quantity };
    if (productId) {
      out.product_id = productId;
    }
    if (variantId) {
      out.variant_id = variantId;
    }
    if (sku) {
      out.sku = sku;
    }
    if (unitPrice !== undefined) {
      out.unit_price = unitPrice;
    }
    return out;
  }

  function extractRawLines() {
    try {
      if (typeof window.cart !== "undefined" && window.cart != null) {
        if (Array.isArray(window.cart) && window.cart.length > 0) {
          return { items: window.cart, source: "window.cart" };
        }
        var c = window.cart;
        if (c && typeof c === "object") {
          if (Array.isArray(c.products) && c.products.length > 0) {
            return { items: c.products, source: "window.cart.products" };
          }
          if (Array.isArray(c.items) && c.items.length > 0) {
            return { items: c.items, source: "window.cart.items" };
          }
        }
      }
      var z = window.zid || window.Zid;
      if (z && z.cart && typeof z.cart === "object") {
        var zc = z.cart;
        if (Array.isArray(zc.products) && zc.products.length > 0) {
          return { items: zc.products, source: "zid.cart.products" };
        }
        if (Array.isArray(zc.items) && zc.items.length > 0) {
          return { items: zc.items, source: "zid.cart.items" };
        }
      }
    } catch (eExt) {
      /* ignore */
    }
    return { items: [], source: "none" };
  }

  function logIdentity(linesLen, source) {
    try {
      console.log(
        "[PRODUCT IDENTITY] lines=" + String(linesLen) + " source=" + String(source || "none")
      );
    } catch (eLog) {
      /* ignore */
    }
  }

  function captureProductLines() {
    try {
      var extracted = extractRawLines();
      var lines = [];
      var items = extracted.items || [];
      var i;
      for (i = 0; i < items.length && lines.length < MAX_LINES; i++) {
        var norm = normalizeLineItem(items[i]);
        if (norm) {
          lines.push(norm);
        }
      }
      logIdentity(lines.length, extracted.source);
      return { lines: lines, source: extracted.source };
    } catch (eCap) {
      logIdentity(0, "none");
      return { lines: [], source: "none" };
    }
  }

  function attachProductLines(payload) {
    if (!payload || typeof payload !== "object") {
      return payload;
    }
    try {
      var cap = captureProductLines();
      payload.lines = cap.lines && cap.lines.length ? cap.lines : [];
    } catch (eAtt) {
      payload.lines = [];
    }
    return payload;
  }

  window.cartflowCaptureProductLines = captureProductLines;
  window.cartflowAttachProductLines = attachProductLines;

  window.CartflowWidgetRuntime.ProductIdentity = {
    capture: captureProductLines,
    attach: attachProductLines,
    MAX_LINES: MAX_LINES,
  };
})();
