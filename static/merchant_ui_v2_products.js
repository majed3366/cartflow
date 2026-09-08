/**
 * CartFlow Merchant UI V2 — Products commercial truth V1.2.
 * Presentation only. Server read model unchanged. No fixtures. No ranker.
 */
(function (global) {
  "use strict";

  var MARKER = "products-commercial-truth-v1";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function metric(numHtml, label) {
    return (
      '<span class="cf2-prd__metric">' +
      '<span class="cf2-prd__metric-n">' +
      numHtml +
      '</span><span class="cf2-prd__metric-l">' +
      label +
      "</span></span>"
    );
  }

  function evidenceStrip(p) {
    var parts = [];
    parts.push(metric(String(Number(p.cart_count || 0)), "سلال"));
    if (p.cart_value_ar) {
      parts.push(metric(esc(p.cart_value_ar), "قيمة السلال"));
    }
    if (p.purchase_known === false) {
      parts.push(
        '<span class="cf2-prd__metric"><span class="cf2-prd__metric-l">مشتريات غير متوفرة</span></span>'
      );
    } else {
      parts.push(metric(String(Number(p.purchases || 0)), "مشتريات"));
    }
    if (p.revenue_ar) {
      parts.push(metric(esc(p.revenue_ar), "إيراد"));
    }
    return parts.join('<span class="cf2-prd__dot" aria-hidden="true">·</span>');
  }

  function hesitationCount(p) {
    var hes = p.hesitation_reason_counts || {};
    var n = 0;
    var k;
    for (k in hes) {
      if (Object.prototype.hasOwnProperty.call(hes, k)) {
        n += Number(hes[k] || 0);
      }
    }
    return n;
  }

  function truthStrength(p) {
    if (p.missing_name || p.name_is_merchant_title === false) {
      return "degraded";
    }
    var purchN = Number(p.purchases || 0);
    if (hesitationCount(p) > 0 || (p.purchase_known && purchN > 0)) {
      return "rich";
    }
    return "limited";
  }

  function shortenSignal(raw) {
    return String(raw || "").replace(
      "أسباب تردد مسجّلة لهذا المنتج",
      "أسباب تردد لهذا المنتج"
    );
  }

  function paintCard(p, opts) {
    opts = opts || {};
    var kind = p.presentation_kind || "";
    var strength = truthStrength(p);
    var html =
      '<article class="cf2-prd__card" data-cf2-prd-card="1" data-cf2-prd-kind="' +
      esc(kind) +
      '" data-cf2-product-truth-strength="' +
      esc(strength) +
      '" data-cf2-prd-id="' +
      esc(p.product_id || "") +
      '"' +
      (opts.primary ? ' data-cf2-prd-primary="1"' : "") +
      ">";
    html += '<h2 class="cf2-prd__name">' + esc(p.product_name || "") + "</h2>";
    if (!p.name_is_merchant_title && p.product_identity) {
      html +=
        '<p class="cf2-prd__identity">' + esc(p.product_identity) + "</p>";
    }
    if (p.price_ar) {
      html += '<p class="cf2-prd__price">' + esc(p.price_ar) + "</p>";
    }
    html +=
      '<p class="cf2-prd__strip" data-cf2-prd-strip="1">' +
      evidenceStrip(p) +
      "</p>";
    if (p.signal_ar) {
      html +=
        '<div class="cf2-prd__signal" data-cf2-prd-signal="1"><p class="cf2-prd__signal-k">' +
        esc(p.signal_heading_ar || "أبرز إشارة") +
        '</p><p class="cf2-prd__signal-v">' +
        esc(shortenSignal(p.signal_ar)) +
        "</p></div>";
    }
    var exp = p.exposure || {};
    var heading = exp.heading_ar || "بيانات الزيارة";
    var value = exp.value_ar || "";
    var line = value ? heading + ": " + value : heading;
    html +=
      '<p class="cf2-prd__exposure" data-cf2-prd-exposure="' +
      esc(exp.state || "") +
      '"><span class="cf2-prd__exposure-line">' +
      esc(line) +
      "</span>";
    if (exp.note_ar) {
      html +=
        '<span class="cf2-prd__exposure-n">' + esc(exp.note_ar) + "</span>";
    }
    html += "</p></article>";
    return html;
  }

  function paint(pkg) {
    pkg = pkg || {};
    var html =
      '<section class="cf2-prd" data-cf2="products-commercial-truth-v1" data-cf2-prd="1" data-cf2-prd-v="1.2" data-cf2-frontend-ranking="0" data-cf2-frontend-fixtures="0">';
    var note = pkg.note_ar || (pkg.store_context && pkg.store_context.body_ar) || "";
    var ctx = pkg.store_context || {};
    if (note || (ctx.href && ctx.cta_ar)) {
      html += '<header class="cf2-prd__intro" data-cf2-prd-boundary="store">';
      if (note) {
        html += '<p class="cf2-prd__note">' + esc(note) + "</p>";
      }
      if (ctx.href && ctx.cta_ar) {
        html +=
          '<p class="cf2-prd__cta"><a class="cf2-prd__nav" href="' +
          esc(ctx.href) +
          '">' +
          esc(ctx.cta_ar) +
          "</a></p>";
      }
      html += "</header>";
    }
    var products = Array.isArray(pkg.products) ? pkg.products : [];
    var groups = Array.isArray(pkg.groups) ? pkg.groups : [];
    if (!products.length) {
      html +=
        '<p class="cf2-prd__empty">لا توجد حقيقة منتج مسجّلة لهذا المتجر بعد.</p>';
      html += "</section>";
      return html;
    }
    if (pkg.primary) {
      html += '<div class="cf2-prd__lead">';
      html += paintCard(pkg.primary, { primary: true });
      html += "</div>";
    }
    groups.forEach(function (g) {
      var rows = products.filter(function (p) {
        if (pkg.primary && p.product_id === pkg.primary.product_id) return false;
        return p.presentation_kind === g.id;
      });
      if (!rows.length) return;
      html +=
        '<section class="cf2-prd__group" data-cf2-prd-group="' +
        esc(g.id || "") +
        '">';
      if (g.label_ar) {
        html +=
          '<p class="cf2-prd__group-label">' + esc(g.label_ar) + "</p>";
      }
      rows.forEach(function (p) {
        html += paintCard(p, {});
      });
      html += "</section>";
    });
    html += "</section>";
    return html;
  }

  function loadAndPaint(root) {
    if (!root) return Promise.resolve();
    root.innerHTML = '<p class="cf2-loading">جاري تحميل حقيقة المنتجات…</p>';
    return fetch("/api/dashboard/products", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("http_" + r.status);
        return r.json();
      })
      .then(function (pkg) {
        root.innerHTML = paint(pkg);
      })
      .catch(function () {
        root.innerHTML =
          '<p class="cf2-prd__empty">تعذّر تحميل حقيقة المنتجات.</p>';
      });
  }

  function applyPayloadAndPaint(root, payload) {
    if (!root) return;
    root.innerHTML = paint(payload);
  }

  global.CartFlowUiV2Products = {
    loadAndPaint: loadAndPaint,
    applyPayloadAndPaint: applyPayloadAndPaint,
    paint: paint,
    marker: MARKER,
  };
})(window);
