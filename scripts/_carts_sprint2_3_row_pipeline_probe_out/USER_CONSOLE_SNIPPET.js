/**
 * Paste in desktop carts console AFTER deploy of ui-setup-v8i-cart-row-trace-v1
 * and AFTER counters update but rows look empty. Then resize to mobile and paste again.
 * Copy both JSON blobs for comparison.
 */
(function () {
  var build = window.MERCHANT_SETUP_RENDER_BUILD;
  var probe =
    typeof window.__maCartsRowProbe === "function"
      ? window.__maCartsRowProbe()
      : null;
  var out = {
    captured_at: new Date().toISOString(),
    viewport_w: window.innerWidth,
    is_desktop: !!(
      window.matchMedia && window.matchMedia("(min-width: 900px)").matches
    ),
    build: build,
    build_ok: build === "ui-setup-v8i-cart-row-trace-v1",
    filt_all: (document.getElementById("ma-filt-all") || {}).textContent || null,
    filt_sent: (document.getElementById("ma-filt-sent") || {}).textContent || null,
    probe: probe,
    first_zero_visible: (function () {
      var t = window.__maCartsRowTrace || [];
      for (var i = 0; i < t.length; i++) {
        var e = t[i];
        var vis =
          (e.dom && e.dom.visible_queue_item_count) != null
            ? e.dom.visible_queue_item_count
            : e.visible_queue_items;
        if (vis === 0 && (e.rows_count > 0 || e.page_rows > 0 || e.memory_rows > 0)) {
          return { index: i, stage: e.stage, entry: e };
        }
      }
      return null;
    })(),
  };
  console.log("[SPRINT 2.3 ROW PROBE]", out);
  try {
    copy(JSON.stringify(out, null, 2));
    console.log("Copied JSON to clipboard");
  } catch (_e) {
    console.log(JSON.stringify(out, null, 2));
  }
  return out;
})();
