/* Lazy-load merchant dashboard JSON sections (shell-first). Not storefront widget V2. */
/* MERCHANT_SETUP_RENDER_BUILD=ui-setup-v5-demo-reusable */
(function () {
  "use strict";

  var MERCHANT_SETUP_RENDER_BUILD = "ui-setup-v5-demo-reusable";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatMerchantSar(amount) {
    if (typeof window.formatMerchantSar === "function") {
      return window.formatMerchantSar(amount);
    }
    var n = Math.round(parseFloat(amount) || 0);
    return n.toLocaleString("en-US") + "\u00a0ر.س";
  }

  function formatMerchantSarHtml(amount) {
    if (typeof window.formatMerchantSarHtml === "function") {
      return window.formatMerchantSarHtml(amount);
    }
    var text = formatMerchantSar(amount);
    if (!text) return "";
    return (
      '<span class="cf-currency-atom cftyp-currency" data-cf-currency="1">' +
      esc(text) +
      "</span>"
    );
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function stripSkel(el) {
    if (!el) return;
    el.classList.remove("ma-dash-skel");
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) {
      el.textContent = t == null ? "" : String(t);
      stripSkel(el);
    }
  }

  var cachedMerchantActivation = null;
  var cachedMerchantSetupExperience = null;
  var merchantDashboardRefreshToken = "";
  var merchantRefreshInFlight = false;
  var merchantRefreshTimer = null;
  var normalCartsFetchGen = 0;
  var normalCartsAppliedGen = 0;
  var normalCartsBootInFlight = false;
  var normalCartsBootComplete = false;
  var normalCartsHasRenderedRows = false;
  var lastNormalCartsFilterCounts = {};
  var NORMAL_CARTS_CACHE_KEY = "ma_normal_carts_cache_v2";
  var NORMAL_CARTS_CACHE_KEY_V1 = "ma_normal_carts_cache_v1";
  var DEPRECATED_LIFECYCLE_WHAT_NEXT_AR = {
    "اطلب من العميل إكمال بيانات التواصل في الودجيت.":
      "لا توجد وسيلة تواصل متاحة حالياً — سيبدأ التواصل تلقائياً عند توفر بيانات التواصل.",
    "أضف رقم العميل ليكمل النظام المسار.":
      "لا توجد وسيلة تواصل متاحة حالياً — سيبدأ التواصل تلقائياً عند توفر بيانات التواصل.",
    "راجع السلة واتخذ إجراءً يدوياً عند الحاجة.":
      "أوقف CartFlow المسار الآلي مؤقتاً بانتظار إزالة العائق أو اكتمال البيانات.",
    "راجع إعدادات الاسترجاع أو انتظر اكتمال بيانات السلة.":
      "بانتظار اكتمال بيانات السلة — سيتابع CartFlow تلقائياً عند الجاهزية.",
  };
  var VIP_CARTS_CACHE_KEY = "ma_vip_carts_cache_v1";
  var vipCartsFetchGen = 0;
  var vipCartsAppliedGen = 0;
  var vipCartsHasRenderedRows = false;
  var lastVipPageRows = [];
  var lastVipHomeRows = [];
  var lastVipBanner = null;

  function isUnifiedSetup(mse) {
    if (!mse || typeof mse !== "object") return false;
    if (mse.unified_p0 === true) return true;
    if (mse.unified_p0 === false) return false;
    var steps = mse.steps || [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].phase) return true;
    }
    return false;
  }

  function shouldRenderUnifiedSetup(mse) {
    if (!isUnifiedSetup(mse)) return false;
    if (mse.setup_mode === false) return false;
    if (mse.show_card === false) return false;
    return true;
  }

  function logSetupRenderDebug(label, payload) {
    try {
      console.info(
        "[CartFlow] MERCHANT_SETUP_RENDER_BUILD=" + MERCHANT_SETUP_RENDER_BUILD
      );
      if (payload) {
        console.info("[CartFlow] " + label, payload);
      }
    } catch (_e) {
      /* ignore */
    }
  }

  function logClientRefresh(label, payload) {
    try {
      if (payload) {
        console.info("[CLIENT REFRESH] " + label, payload);
      } else {
        console.info("[CLIENT REFRESH] " + label);
      }
    } catch (_e) {
      /* ignore */
    }
  }

  function ingestRefreshToken(d, source) {
    if (!d || !d.merchant_dashboard_refresh_token) return;
    var next = String(d.merchant_dashboard_refresh_token || "");
    if (!next) return;
    var prev = merchantDashboardRefreshToken;
    if (next !== prev) {
      merchantDashboardRefreshToken = next;
      logClientRefresh("token_update", {
        source: source || "",
        token: merchantDashboardRefreshToken,
      });
      scheduleNormalCartsTokenRefetch("token_" + (source || "payload"));
    }
  }

  function scheduleNormalCartsTokenRefetch(label) {
    if (!label) label = "token_refetch";
    if (normalCartsBootInFlight && !normalCartsBootComplete) {
      window.__maNormalCartsTokenRefetchAfterBoot = label;
      return;
    }
    fetchNormalCarts(label);
  }

  function sanitizeNormalCartRowLifecycleCopy(row) {
    if (!row || typeof row !== "object") return row;
    var wn = String(row.customer_lifecycle_what_next_ar || "");
    var replacement = DEPRECATED_LIFECYCLE_WHAT_NEXT_AR[wn];
    if (!replacement) return row;
    var out = Object.assign({}, row);
    out.customer_lifecycle_what_next_ar = replacement;
    return out;
  }

  function sanitizeNormalCartRows(rows) {
    if (!rows || !rows.length) return rows || [];
    var out = [];
    var i;
    for (i = 0; i < rows.length; i++) {
      out.push(sanitizeNormalCartRowLifecycleCopy(rows[i]));
    }
    return out;
  }

  function normalCartsPayloadSource(d) {
    if (!d) return "unknown";
    if (d.__ma_payload_source) return String(d.__ma_payload_source);
    if (d.snapshot_mode || d._snapshot) return "snapshot";
    if (normalCartsIsDegraded(d)) return "degraded";
    return "fetch";
  }

  function normalCartsCountAll(fc) {
    if (!fc) return 0;
    var n = parseInt(fc.all, 10);
    return isFinite(n) ? n : 0;
  }

  function normalCartsPayloadIsPartialOrThin(d) {
    if (!d) return true;
    if (normalCartsIsDegraded(d)) return true;
    if (d.snapshot_stale || d.snapshot_degraded) return true;
    if (d.dashboard_partial || d.dashboard_timeout) return true;
    var snap = d._snapshot;
    if (snap && (snap.degraded || snap.stale)) return true;
    return false;
  }

  function normalCartsFilterCountsExplicitZero(fc) {
    if (!fc || typeof fc !== "object") return false;
    var n = parseInt(fc.all, 10);
    return isFinite(n) && n === 0;
  }

  function normalCartsIsConfirmedFullEmpty(d, pageRows) {
    if (pageRows && pageRows.length) return false;
    if (normalCartsPayloadIsPartialOrThin(d)) return false;
    if (hasCanonicalStoreCartCounts(d)) {
      var storeFc = resolveMerchantStoreCartCounts(d);
      var storeAll = parseInt(storeFc.all, 10);
      return isFinite(storeAll) && storeAll === 0;
    }
    if (!normalCartsFilterCountsExplicitZero((d && d.merchant_cart_filter_counts) || {})) {
      return false;
    }
    var src = normalCartsPayloadSource(d);
    if (src === "snapshot" || (d && d.snapshot_mode)) return false;
    if (d && d._snapshot) return false;
    return true;
  }

  function hasCanonicalStoreCartCounts(d) {
    var store = (d && d.merchant_store_cart_counts) || {};
    return store.active_total != null || store.waiting_total != null;
  }

  function resolveMerchantStoreCartCounts(d) {
    var store = (d && d.merchant_store_cart_counts) || {};
    if (hasCanonicalStoreCartCounts(d)) {
      return {
        all: store.active_total != null ? store.active_total : 0,
        waiting: store.waiting_total != null ? store.waiting_total : 0,
        sent: store.sent_total != null ? store.sent_total : 0,
        attention: store.engaged_total != null ? store.engaged_total : 0,
        recovered: store.completed_total != null ? store.completed_total : 0,
        nophone: store.no_phone_total != null ? store.no_phone_total : 0,
      };
    }
    return (d && d.merchant_cart_filter_counts) || {};
  }

  function deriveVisiblePageCounts(rows, archivedRows) {
    var pageFc = deriveFilterCountsFromRows(rows || []);
    pageFc.archived = archivedRows ? archivedRows.length : 0;
    return pageFc;
  }

  function applyNoPhoneFilterVisibility(storeFc) {
    var btn = document.querySelector('#ma-cart-filters [data-filter="nophone"]');
    if (!btn) return;
    var n = parseInt(storeFc && storeFc.nophone, 10);
    btn.style.display = isFinite(n) && n > 0 ? "" : "none";
  }

  function deriveFilterCountsFromRows(rows) {
    var counts = {
      all: 0,
      sent: 0,
      attention: 0,
      recovered: 0,
      nophone: 0,
      waiting: 0,
    };
    if (!rows || !rows.length) return counts;
    counts.all = rows.length;
    var i;
    for (i = 0; i < rows.length; i++) {
      var row = rows[i] || {};
      var tabs = row.merchant_cart_visible_tabs;
      if (!Array.isArray(tabs)) tabs = [];
      if (!tabs.length) {
        var b = String(
          row.merchant_cart_bucket || row.merchant_cart_primary_bucket || ""
        )
          .trim()
          .toLowerCase();
        if (b) tabs = [b];
      }
      var j;
      for (j = 0; j < tabs.length; j++) {
        var t = String(tabs[j] || "").trim().toLowerCase();
        if (t === "sent") counts.sent += 1;
        else if (t === "attention") counts.attention += 1;
        else if (t === "recovered") counts.recovered += 1;
        else if (t === "nophone") counts.nophone += 1;
        else if (t === "waiting") counts.waiting += 1;
      }
    }
    return counts;
  }

  function normalCartsShouldRejectThinPayload(d, pageRows) {
    var prevN = lastNormalCartsPageRows.length;
    if (prevN < 1) return false;
    var incomingN = pageRows ? pageRows.length : 0;
    if (hasCanonicalStoreCartCounts(d)) {
      if (
        incomingN === 0 &&
        !normalCartsPayloadIsPartialOrThin(d) &&
        incomingN === 0
      ) {
        return false;
      }
      if (incomingN >= prevN) return false;
      return incomingN < prevN && normalCartsPayloadIsPartialOrThin(d);
    }
    var incomingAll = normalCartsCountAll(
      (d && d.merchant_cart_filter_counts) || {}
    );
    if (
      incomingN === 0 &&
      !normalCartsPayloadIsPartialOrThin(d) &&
      incomingAll === 0
    ) {
      return false;
    }
    if (incomingN >= prevN) return false;
    var prevAll = normalCartsCountAll(lastNormalCartsFilterCounts);
    if (prevAll <= 0) prevAll = prevN;
    var partialFlags = normalCartsPayloadIsPartialOrThin(d);
    var countSuspect =
      incomingAll <= 0 || incomingAll < prevAll || incomingAll < incomingN;
    if (incomingN < prevN && (partialFlags || countSuspect)) {
      return true;
    }
    return false;
  }

  function migrateNormalCartsCacheV1ToV2() {
    try {
      if (sessionStorage.getItem(NORMAL_CARTS_CACHE_KEY)) return false;
      var raw = sessionStorage.getItem(NORMAL_CARTS_CACHE_KEY_V1);
      if (!raw) return false;
      var c = JSON.parse(raw);
      if (!c || !c.rows || !c.rows.length) return false;
      sessionStorage.setItem(NORMAL_CARTS_CACHE_KEY, raw);
      logClientRefresh("normal_carts_cache_v1_migrated", { rows: c.rows.length });
      return true;
    } catch (_migrateErr) {
      return false;
    }
  }

  function effectiveFilterCounts(incoming, pageRows, payload) {
    if (payload && hasCanonicalStoreCartCounts(payload)) {
      return resolveMerchantStoreCartCounts(payload);
    }
    var fc = incoming || {};
    var rowsN = pageRows ? pageRows.length : 0;
    if (!rowsN) return fc;
    var incomingAll = normalCartsCountAll(fc);
    var prevAll = normalCartsCountAll(lastNormalCartsFilterCounts);
    if (incomingAll <= 0) {
      if (prevAll > 0) {
        logClientRefresh("normal_carts_counts_preserved", {
          rows_count: rowsN,
          incoming_all: incomingAll,
          preserved_all: prevAll,
        });
        return lastNormalCartsFilterCounts;
      }
      var derived = deriveFilterCountsFromRows(pageRows);
      if (derived.all > 0) {
        logClientRefresh("normal_carts_counts_derived", {
          rows_count: rowsN,
          derived_all: derived.all,
        });
        return derived;
      }
    }
    if (incomingAll > 0 && incomingAll < rowsN) {
      var derivedMismatch = deriveFilterCountsFromRows(pageRows);
      if (derivedMismatch.all === rowsN) {
        logClientRefresh("normal_carts_counts_derived_mismatch", {
          rows_count: rowsN,
          incoming_all: incomingAll,
          derived_all: derivedMismatch.all,
        });
        return derivedMismatch;
      }
    }
    return fc;
  }

  function prepareNormalCartsPayload(d, source) {
    if (!d) return d;
    var rows = sanitizeNormalCartRows(normalCartsPayloadRows(d));
    var archived = sanitizeNormalCartRows(
      (d && d.merchant_archived_carts_page_rows) || []
    );
    var table = sanitizeNormalCartRows((d && d.merchant_table_rows) || []);
    var out = Object.assign({}, d);
    out.merchant_carts_page_rows = rows;
    out.merchant_archived_carts_page_rows = archived;
    if (table.length) {
      out.merchant_table_rows = table;
    } else if (rows.length) {
      out.merchant_table_rows = rows.slice(0, 8);
    }
    if (source) out.__ma_payload_source = source;
    return out;
  }

  function persistNormalCartsCache(d) {
    try {
      if (!d || !d.ok) return;
      var prepared = prepareNormalCartsPayload(d, normalCartsPayloadSource(d));
      var rows = normalCartsPayloadRows(prepared);
      if (!rows.length) return;
      sessionStorage.setItem(
        NORMAL_CARTS_CACHE_KEY,
        JSON.stringify({
          rows: rows,
          archived: (prepared && prepared.merchant_archived_carts_page_rows) || [],
          table: (prepared && prepared.merchant_table_rows) || [],
          fc: (prepared && prepared.merchant_cart_filter_counts) || {},
          token: (prepared && prepared.merchant_dashboard_refresh_token) || "",
          saved_at: Date.now(),
        })
      );
    } catch (_cacheErr) {
      /* ignore */
    }
  }

  function hydrateNormalCartsCache() {
    try {
      migrateNormalCartsCacheV1ToV2();
      var raw = sessionStorage.getItem(NORMAL_CARTS_CACHE_KEY);
      if (!raw) return false;
      var c = JSON.parse(raw);
      if (!c || !c.rows || !c.rows.length) return false;
      lastNormalCartsFilterCounts = c.fc || {};
      renderNormalCartsTables(
        prepareNormalCartsPayload(
          {
            ok: true,
            merchant_carts_page_rows: c.rows,
            merchant_archived_carts_page_rows: c.archived || [],
            merchant_table_rows: c.table && c.table.length ? c.table : c.rows.slice(0, 8),
            merchant_cart_filter_counts: c.fc || {},
          },
          "cache"
        )
      );
      if (c.token) {
        merchantDashboardRefreshToken = String(c.token);
      }
      normalCartsHasRenderedRows = true;
      logClientRefresh("normal_carts_cache_hydrate", { rows: c.rows.length });
      return true;
    } catch (_hydrateErr) {
      return false;
    }
  }

  function cartIdInNormalRows(cartId) {
    var cid = String(cartId || "").trim();
    if (!cid) return false;
    var i;
    for (i = 0; i < lastNormalCartsPageRows.length; i++) {
      if (String(lastNormalCartsPageRows[i].cart_id || "").trim() === cid) {
        return true;
      }
    }
    return false;
  }

  function startPendingNewCartWatcher() {
    var cid = "";
    try {
      cid = String(sessionStorage.getItem("cartflow_cart_event_id") || "").trim();
    } catch (_ssErr) {
      cid = "";
    }
    if (!cid || window.__maPendingCartWatchActive) return;
    if (cartIdInNormalRows(cid)) return;
    window.__maPendingCartWatchActive = true;
    var tries = 0;
    function tick() {
      tries += 1;
      if (cartIdInNormalRows(cid) || tries > 25) {
        window.__maPendingCartWatchActive = false;
        return;
      }
      fetchNormalCarts("pending_cart_poll");
      window.setTimeout(tick, 1200);
    }
    window.setTimeout(tick, 400);
  }

  function rerenderCartsFromMemory(reason) {
    if (!lastNormalCartsPageRows.length) {
      if (hydrateNormalCartsCache()) {
        logClientRefresh("carts_rerender_cache", { reason: reason || "" });
        return;
      }
      showNormalCartsLoadingState("جاري تحميل السلال…");
      return;
    }
    renderNormalCartsTables(
      prepareNormalCartsPayload(
        {
          ok: true,
          merchant_carts_page_rows: lastNormalCartsPageRows,
          merchant_archived_carts_page_rows: lastArchivedCartsPageRows,
          merchant_table_rows: lastNormalCartsPageRows.slice(0, 8),
          merchant_cart_filter_counts: lastNormalCartsFilterCounts,
        },
        "memory"
      )
    );
    logClientRefresh("carts_rerender_memory", {
      reason: reason || "",
      rows: lastNormalCartsPageRows.length,
    });
  }

  function syncCartsPageOnHashChange() {
    var hashRaw = (location.hash || "").split("?")[0].toLowerCase();
    if (
      hashRaw !== "#carts" &&
      hashRaw !== "#followup" &&
      hashRaw !== "#completed"
    ) {
      return;
    }
    rerenderCartsFromMemory("hashchange");
    if (!lastNormalCartsPageRows.length) {
      fetchNormalCarts("hash_carts_empty");
    }
    startPendingNewCartWatcher();
  }

  function ensureNormalCartsPageReady(source) {
    var hashRaw = (location.hash || "").split("?")[0].toLowerCase();
    if (
      hashRaw !== "#carts" &&
      hashRaw !== "#followup" &&
      hashRaw !== "#completed" &&
      hashRaw !== "#home"
    ) {
      return;
    }
    if (lastNormalCartsPageRows.length) {
      rerenderCartsFromMemory("ensure_" + (source || ""));
      return;
    }
    if (hydrateNormalCartsCache()) {
      return;
    }
    if (normalCartsBootInFlight) {
      showNormalCartsLoadingState("جاري تحميل السلال…");
      return;
    }
    fetchNormalCarts(source || "carts_ensure");
  }

  function probeSetupExperienceRoot() {
    var root = byId("ma-setup-experience-root");
    var setupPage = byId("page-home-setup");
    if (!root) {
      return { found: false };
    }
    var cs = window.getComputedStyle ? window.getComputedStyle(root) : null;
    return {
      found: true,
      hiddenProperty: !!root.hidden,
      hasHiddenAttr: root.hasAttribute("hidden"),
      innerHTMLLength: (root.innerHTML || "").length,
      display: cs ? cs.display : null,
      visibility: cs ? cs.visibility : null,
      parentPageSetupActive: !!(setupPage && setupPage.classList.contains("active")),
      dataUnified: root.getAttribute("data-ma-setup-unified"),
    };
  }

  window.maProbeSetupExperienceRoot = probeSetupExperienceRoot;

  function isHomeSectionActive() {
    var pages = ["page-home", "page-home-setup", "page-home-month", "page-home-test-tools"];
    var i;
    for (i = 0; i < pages.length; i++) {
      var el = byId(pages[i]);
      if (el && el.classList.contains("active")) return true;
    }
    return false;
  }

  function isDashboardHomeActive() {
    var home = byId("page-home");
    return !!(home && home.classList.contains("active"));
  }

  function clearTestToolsRoot(root) {
    if (!root) return;
    root.innerHTML = "";
    root.hidden = true;
    root.setAttribute("hidden", "");
  }

  function showTestToolsRoot(root) {
    if (!root) return;
    root.hidden = false;
    root.removeAttribute("hidden");
  }

  function showActivationRoot(root) {
    if (!root) return;
    root.hidden = false;
    root.removeAttribute("hidden");
    root.classList.add("ma-activation-on-home");
  }

  function hideActivationRootClear(root) {
    if (!root) return;
    root.hidden = true;
    root.setAttribute("hidden", "");
    root.classList.remove("ma-activation-on-home");
    root.innerHTML = "";
  }

  function hasUnifiedDemoSteps(mse) {
    if (!mse) return false;
    if (mse.test_store_url) return true;
    var steps = mse.steps || [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].repeatable_demo && !steps[i].locked) return true;
    }
    return false;
  }

  function showTestToolsEmptyState(root) {
    if (!root) return;
    showTestToolsRoot(root);
    root.innerHTML =
      '<div class="card ma-test-tools-empty">' +
      '<p class="ma-test-tools-empty-title">لا توجد أدوات تجربة الآن</p>' +
      '<p class="ma-test-tools-empty-body">تظهر هنا روابط متجر الاختبار وإعادة التجربة عندما يكون مسار الإعداد الموحّد نشطاً.</p>' +
      "</div>";
  }

  function applyTestToolsPage(mse) {
    var testToolsRoot = byId("ma-test-tools-root");
    if (!testToolsRoot) return;
    if (hasUnifiedDemoSteps(mse)) {
      renderUnifiedSetupDemoToolsOnly(mse, testToolsRoot);
    } else {
      showTestToolsEmptyState(testToolsRoot);
    }
  }

  function syncHomeActivationFromCache() {
    var act = cachedMerchantActivation;
    var mse = cachedMerchantSetupExperience;
    var home = byId("page-home");
    var setupRoot = byId("ma-setup-experience-root");
    var testToolsRoot = byId("ma-test-tools-root");
    if (act && home) {
      applyHomeAdaptiveStage(act);
    }
    if (!act && !mse) {
      return;
    }
    if (!isUnifiedSetup(mse)) {
      applyMerchantActivation(act);
      if (testToolsRoot) {
        showTestToolsEmptyState(testToolsRoot);
      }
    } else {
      hideActivationForUnifiedSetup(mse);
      applyTestToolsPage(mse);
    }
    if (
      shouldHideUnifiedSetupCard(act, mse) ||
      (isUnifiedSetup(mse) && mse && mse.setup_mode === false)
    ) {
      if (setupRoot) {
        setupRoot.hidden = true;
        setupRoot.setAttribute("hidden", "");
        setupRoot.innerHTML = "";
      }
    } else if (shouldRenderUnifiedSetup(mse)) {
      applyMerchantSetupExperience(mse);
    } else if (mse && setupRoot && mse.show_card !== false) {
      applyMerchantSetupExperience(mse);
    }
  }

  function setNavBadge(id, n) {
    var el = byId(id);
    if (!el) return;
    var v = parseInt(n, 10) || 0;
    el.textContent = String(v);
    el.style.display = v > 0 ? "" : "none";
  }

  function sectionFromHref(href) {
    var h = String(href || "");
    var i = h.indexOf("#");
    if (i < 0) return "";
    return h.slice(i + 1);
  }

  function setupStepsHtml(steps) {
    if (!steps || !steps.length) return "";
    var html = '<ul class="ma-onb-checklist">';
    for (var i = 0; i < steps.length; i++) {
      var st = steps[i];
      var done = !!st.is_complete;
      var mark = done ? "✓" : "◯";
      var href = st.action_href || "#settings";
      var sec = sectionFromHref(href);
      var goAttr = sec
        ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
        : "";
      html +=
        '<li class="ma-onb-checklist-item' +
        (done ? " is-done" : " is-pending") +
        '">' +
        '<span class="ma-onb-check" aria-hidden="true">' +
        mark +
        "</span>" +
        '<div class="ma-onb-check-body">' +
        '<p class="ma-onb-check-title">' +
        esc(st.title_ar) +
        "</p>" +
        '<p class="ma-onb-check-outcome-label">النتيجة</p>' +
        '<p class="ma-onb-check-outcome">' +
        esc(st.outcome_ar) +
        "</p>" +
        (done
          ? ""
          : '<a class="ma-setup-step-action" href="' +
            esc(href) +
            '"' +
            goAttr +
            ">انتقل لهذه الخطوة</a>") +
        "</div></li>";
    }
    html += "</ul>";
    return html;
  }

  function applyOnboardingHomeFocus(mse) {
    var setupPage = byId("page-home-setup");
    if (!setupPage) return;
    var setupMode = shouldRenderUnifiedSetup(mse);
    setupPage.classList.toggle("ma-setup-mode", setupMode);
    setupPage.classList.remove("ma-onboarding-focus");
  }

  function hideActivationForUnifiedSetup(mse) {
    var root = byId("ma-activation-root");
    if (!root) return;
    if (isUnifiedSetup(mse)) {
      root.hidden = true;
      root.innerHTML = "";
      root.classList.remove("ma-activation-on-home");
      return;
    }
  }

  /** Hide unified setup only when prod path finished (setup_mode === false). */
  function shouldHideUnifiedSetupCard(act, mse) {
    if (!act || !mse || !isUnifiedSetup(mse) || !act.hide_setup_card) {
      return false;
    }
    return mse.setup_mode === false;
  }

  function showSetupExperienceRoot(root) {
    if (!root) return;
    root.hidden = false;
    root.removeAttribute("hidden");
  }

  function recoveryStatusFromWaCard(wa) {
    if (!wa || typeof wa !== "object") {
      return { ok: false, label: "—", hint: "" };
    }
    var key = String(wa.state_key || "").trim();
    if (key === "ready") {
      return {
        ok: true,
        label: wa.badge_ar || "جاهز",
        hint: wa.description_ar || wa.impact_ar || "",
      };
    }
    if (key === "disabled") {
      return {
        ok: false,
        label: wa.badge_ar || "غير مفعل",
        hint: wa.description_ar || wa.impact_ar || "",
      };
    }
    if (key === "sandbox") {
      return {
        ok: false,
        label: wa.badge_ar || "تجريبي",
        hint: wa.description_ar || wa.impact_ar || "",
      };
    }
    return {
      ok: false,
      label: wa.badge_ar || wa.title_ar || "يحتاج متابعة",
      hint: wa.description_ar || wa.impact_ar || "",
    };
  }

  function readinessRowHtml(icon, title, statusLabel, ok, hint, href, goPage) {
    var cls = ok ? "is-ready" : "is-pending";
    var mark = ok ? "✓" : "○";
    var goAttr = goPage
      ? ' onclick="if(window.goTo){goTo(\'' + goPage + "');}return false;\""
      : "";
    return (
      '<div class="ma-readiness-row ' +
      cls +
      '">' +
      '<span class="ma-readiness-icon" aria-hidden="true">' +
      icon +
      "</span>" +
      '<div class="ma-readiness-body">' +
      '<p class="ma-readiness-row-title">' +
      esc(title) +
      "</p>" +
      '<p class="ma-readiness-row-status">' +
      mark +
      " " +
      esc(statusLabel) +
      "</p>" +
      (hint
        ? '<p class="ma-readiness-row-hint">' + esc(hint) + "</p>"
        : "") +
      "</div>" +
      (href
        ? '<a class="ma-readiness-row-link" href="' +
          esc(href) +
          '"' +
          goAttr +
          ">انتقل</a>"
        : "") +
      "</div>"
    );
  }

  function applySetupReadinessPanel(d) {
    var root = byId("ma-setup-readiness-root");
    if (!root || !d) return;
    var sc = d.store_connection || {};
    var wa =
      d.whatsapp_readiness_card ||
      {
        state_key: d.wa_state_key || "setup",
        badge_ar: d.wa_badge_ar || "—",
        title_ar: "",
        description_ar: "",
        impact_ar: "",
      };
    var mse = d.merchant_setup_experience || {};
    var pct = parseInt(mse.readiness_percent, 10);
    if (isNaN(pct)) pct = 0;
    pct = Math.max(0, Math.min(100, pct));
    var stateLabel = mse.setup_state_label_ar || "—";
    var nextStep = mse.next_step_ar || wa.next_action_ar || "";
    var storeOk = !!(sc.store_connected_ok || sc.connected);
    var widgetOk = !!sc.widget_installed_ok;
    var waOk = String(wa.state_key || "") === "ready";
    var recovery = recoveryStatusFromWaCard(wa);
    var rows =
      readinessRowHtml(
        "🏪",
        "ربط المتجر",
        sc.status_label_ar || "—",
        storeOk,
        sc.status_description_ar || sc.pending_setup_message_ar || "",
        "/dashboard#settings",
        "settings"
      ) +
      readinessRowHtml(
        "💬",
        "واتساب",
        wa.badge_ar || wa.title_ar || "—",
        waOk,
        wa.description_ar || "",
        "/dashboard#whatsapp",
        "whatsapp"
      ) +
      readinessRowHtml(
        "🧩",
        "الودجيت",
        sc.widget_status_label_ar || "—",
        widgetOk,
        sc.widget_status_description_ar || "",
        "/dashboard#widget",
        "widget"
      ) +
      readinessRowHtml(
        "🔄",
        "الاسترجاع",
        recovery.label,
        recovery.ok,
        recovery.hint,
        "/dashboard#whatsapp",
        "whatsapp"
      );
    root.innerHTML =
      '<div class="ma-readiness-panel card">' +
      '<div class="ma-readiness-head">' +
      '<h2 class="ma-readiness-title" id="ma-setup-readiness-title">هل متجرك جاهز؟</h2>' +
      '<p class="ma-readiness-lead">حالة الربط والتفعيل — بدون أدوات تجربة.</p>' +
      "</div>" +
      '<div class="ma-readiness-progress">' +
      '<div class="ma-readiness-progress-meta">' +
      '<span class="ma-readiness-pct">' +
      pct +
      "٪</span>" +
      '<span class="ma-readiness-state">' +
      esc(stateLabel) +
      "</span>" +
      "</div>" +
      '<div class="ma-readiness-track"><div class="ma-readiness-fill" style="width:' +
      pct +
      '%"></div></div>' +
      "</div>" +
      '<div class="ma-readiness-rows">' +
      rows +
      "</div>" +
      (nextStep
        ? '<p class="ma-readiness-next"><span class="ma-readiness-next-k">الخطوة التالية</span> ' +
          esc(nextStep) +
          "</p>"
        : "") +
      "</div>";
  }

  function applySetupReadinessPanelWithFallback(d) {
    if (!d) return;
    if (d.store_connection) {
      applySetupReadinessPanel(d);
      return;
    }
    fetch("/api/merchant/store-connection", { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        var merged = {};
        var k;
        for (k in d) {
          if (Object.prototype.hasOwnProperty.call(d, k)) merged[k] = d[k];
        }
        merged.store_connection = (body && body.store_connection) || {};
        applySetupReadinessPanel(merged);
      })
      .catch(function () {
        applySetupReadinessPanel(d);
      });
  }

  function hydrateSetupReadinessFromCache(extra) {
    extra = extra || {};
    var d = {
      merchant_setup_experience: cachedMerchantSetupExperience,
      merchant_activation: cachedMerchantActivation,
      wa_state_key: extra.wa_state_key || "",
      wa_badge_ar: extra.wa_badge_ar || "",
      whatsapp_readiness_card: extra.whatsapp_readiness_card || null,
      store_connection: extra.store_connection || null,
    };
    applySetupReadinessPanelWithFallback(d);
  }

  function bootSetupReadinessHydration() {
    hydrateSetupReadinessFromCache();
    fetch("/api/merchant/store-connection", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        hydrateSetupReadinessFromCache({
          store_connection: (body && body.store_connection) || {},
        });
      })
      .catch(function () {});
    fetch("/api/merchant/setup-experience", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        if (body && body.ok && body.merchant_setup_experience) {
          cachedMerchantSetupExperience = body.merchant_setup_experience;
          syncHomeActivationFromCache();
          hydrateSetupReadinessFromCache();
        }
      })
      .catch(function () {});
  }

  function activationSetupActionsHtml(act) {
    var href = (act && act.action_href) || "/dashboard#settings";
    var sec = sectionFromHref(href);
    var goAttr = sec
      ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
      : "";
    return (
      '<div class="ma-activation-actions">' +
      '<a class="ma-activation-btn ma-activation-btn-primary" href="' +
      esc(href) +
      '"' +
      goAttr +
      ">متابعة الإعداد</a>" +
      '<a class="ma-activation-btn ma-activation-btn-secondary" href="/dashboard#home-test-tools" onclick="if(window.maHomeNav){maHomeNav(\'test-tools\');}return false;">أدوات التجربة</a>' +
      "</div>"
    );
  }

  function applyHomeOperationalAlerts(alerts) {
    var root = byId("ma-home-alerts-root");
    if (!root) return;
    var lines = alerts || [];
    if (!lines.length) {
      root.hidden = true;
      root.innerHTML = "";
      return;
    }
    var lis = "";
    for (var i = 0; i < lines.length; i++) {
      lis += "<li>" + esc(lines[i]) + "</li>";
    }
    root.hidden = false;
    root.innerHTML =
      '<div class="ma-home-alerts-inner">' +
      '<p class="ma-home-alerts-title">تنبيهات تشغيلية</p>' +
      '<ul class="ma-home-alerts-list">' +
      lis +
      "</ul></div>";
  }

  function applyHomeAdaptiveStage(act) {
    var home = byId("page-home");
    if (!home) return;
    var stage = (act && act.home_stage) || "activation";
    home.setAttribute("data-ma-home-stage", stage);
    home.classList.remove(
      "ma-home-stage-activation",
      "ma-home-stage-activated",
      "ma-home-stage-production"
    );
    home.classList.add("ma-home-stage-" + stage);
    applyHomeOperationalAlerts(act && act.operational_alerts_ar);
  }

  function normalizeActivationDisplay(raw) {
    return String(raw == null ? "" : raw)
      .trim()
      .toLowerCase();
  }

  function resolveActivationRenderPlan(act) {
    var rawDisplay = act && act.activation_display;
    var display = normalizeActivationDisplay(rawDisplay);
    var plan = {
      display: rawDisplay || "prominent",
      renderMode: "prominent",
      template: "activation_prominent_v1",
      fallback: null,
    };
    if (!display) {
      plan.fallback = "missing_activation_display_default_prominent";
      return plan;
    }
    if (display === "prominent") {
      plan.renderMode = "prominent";
      plan.template = "activation_prominent_v1";
      return plan;
    }
    if (display === "compact") {
      plan.renderMode = "compact";
      plan.template = "activation_compact_v1";
      return plan;
    }
    if (display === "hidden") {
      plan.renderMode = "compact";
      plan.template = "activation_compact_v1";
      plan.fallback = "server_hidden_upgraded_to_compact_on_home";
      return plan;
    }
    plan.fallback = "unknown_activation_display_coerced_prominent";
    return plan;
  }

  function logActivationRender(plan, act) {
    console.log(
      "[ACTIVATION RENDER]\n" +
        "display=" +
        String(plan.display) +
        "\n" +
        "render_mode=" +
        String(plan.renderMode) +
        "\n" +
        "template=" +
        String(plan.template) +
        "\n" +
        "fallback=" +
        String(plan.fallback || "") +
        "\n" +
        "home_stage=" +
        String((act && act.home_stage) || "")
    );
  }

  function buildActivationMilestonesHtml(milestones) {
    var msHtml = "";
    var i;
    for (i = 0; i < milestones.length; i++) {
      var m = milestones[i];
      var done = !!m.done;
      msHtml +=
        '<li class="' +
        (done ? "is-done" : "is-pending") +
        '">' +
        '<span class="ma-act-mark" aria-hidden="true">' +
        (done ? "✓" : "○") +
        "</span>" +
        "<span>" +
        esc(m.title_ar || "") +
        (m.hint_ar
          ? '<span class="ma-act-hint">' + esc(m.hint_ar) + "</span>"
          : "") +
        "</span></li>";
    }
    return msHtml;
  }

  function buildActivationTimelineHtml(states) {
    var stHtml = "";
    var i;
    for (i = 0; i < states.length; i++) {
      var st = states[i];
      var liCls = "";
      if (st.reached) liCls += " is-reached";
      if (st.current) liCls += " is-current";
      stHtml +=
        '<li class="' +
        liCls +
        '">' +
        esc(st.label_ar || "") +
        "</li>";
    }
    return stHtml;
  }

  function bindActivationCompactExpand(root) {
    var card = byId("ma-activation-card-inner");
    var expandBtn = root.querySelector("[data-ma-act-expand]");
    if (expandBtn && card) {
      expandBtn.addEventListener("click", function () {
        card.classList.toggle("ma-activation-expanded");
        expandBtn.textContent = card.classList.contains("ma-activation-expanded")
          ? "إخفاء التفاصيل"
          : "تفاصيل التفعيل";
      });
    }
  }

  function renderActivationProminent(act, root) {
    var milestones = act.milestones || [];
    var states = act.summary_states || [];
    var working = !!act.activation_working;
    var title = working
      ? "CartFlow يعمل على متجرك"
      : "جاهزية التفعيل";
    var lead =
      act.next_step_ar ||
      "أكمل خطوات الإعداد لتفعيل الاسترجاع على متجرك.";
    var msHtml = buildActivationMilestonesHtml(milestones);
    var stHtml = buildActivationTimelineHtml(states);
    var delay = act.delay_hint_ar
      ? '<p class="ma-activation-delay">' + esc(act.delay_hint_ar) + "</p>"
      : "";
    var timelineBlock = stHtml
      ? '<ul class="ma-activation-timeline">' + stHtml + "</ul>"
      : "";
    showActivationRoot(root);
    root.setAttribute("data-ma-activation-render-mode", "prominent");
    root.innerHTML =
      '<div class="ma-activation-card ma-activation-prominent" id="ma-activation-card-inner">' +
      "<h2 class=\"ma-activation-title\">" +
      esc(title) +
      "</h2>" +
      '<p class="ma-activation-lead">' +
      esc(lead) +
      "</p>" +
      timelineBlock +
      '<ul class="ma-activation-milestones">' +
      msHtml +
      "</ul>" +
      activationSetupActionsHtml(act) +
      delay +
      "</div>";
  }

  function renderActivationCompact(act, root) {
    var milestones = act.milestones || [];
    var states = act.summary_states || [];
    var lead =
      act.next_step_ar ||
      "أكمل خطوات الإعداد لتفعيل الاسترجاع على متجرك.";
    var msHtml = buildActivationMilestonesHtml(milestones);
    var stHtml = buildActivationTimelineHtml(states);
    var delay = act.delay_hint_ar
      ? '<p class="ma-activation-delay">' + esc(act.delay_hint_ar) + "</p>"
      : "";
    var summaryLines = act.activation_summary_lines_ar || [];
    var compactBody = "";
    var i;
    for (i = 0; i < summaryLines.length; i++) {
      compactBody +=
        '<span class="ma-activation-compact-line">' +
        esc(summaryLines[i]) +
        "</span>";
    }
    if (act.last_activity_ar) {
      compactBody +=
        '<span class="ma-activation-compact-line">آخر نشاط: ' +
        esc(act.last_activity_ar) +
        "</span>";
    }
    var timelineBlock = stHtml
      ? '<ul class="ma-activation-timeline">' + stHtml + "</ul>"
      : "";
    showActivationRoot(root);
    root.setAttribute("data-ma-activation-render-mode", "compact");
    root.innerHTML =
      '<div class="ma-activation-card ma-activation-compact" id="ma-activation-card-inner">' +
      "<h2 class=\"ma-activation-title\">" +
      esc("حالة التفعيل") +
      "</h2>" +
      '<div class="ma-activation-compact-body">' +
      compactBody +
      '<button type="button" class="ma-activation-compact-toggle" data-ma-act-expand="1">تفاصيل التفعيل</button>' +
      "</div>" +
      timelineBlock +
      '<ul class="ma-activation-milestones">' +
      msHtml +
      "</ul>" +
      activationSetupActionsHtml(act) +
      delay +
      '<p class="ma-activation-lead">' +
      esc(lead) +
      "</p>" +
      "</div>";
    bindActivationCompactExpand(root);
  }

  function applyMerchantActivation(act) {
    var root = byId("ma-activation-root");
    if (!root) return;
    if (!act || typeof act !== "object") {
      hideActivationRootClear(root);
      return;
    }
    var plan = resolveActivationRenderPlan(act);
    logActivationRender(plan, act);
    if (plan.renderMode === "compact") {
      renderActivationCompact(act, root);
      return;
    }
    if (plan.renderMode === "prominent") {
      renderActivationProminent(act, root);
      return;
    }
    hideActivationRootClear(root);
  }

  function applyHomeLayoutAfterSetup(act, mse) {
    cachedMerchantActivation = act;
    cachedMerchantSetupExperience = mse;
    syncHomeActivationFromCache();
  }

  function unifiedStepShortLabel(titleAr) {
    var t = String(titleAr || "").trim();
    if (t.length <= 28) return t;
    return t.slice(0, 26) + "…";
  }

  function isDemoStoreHref(href) {
    return String(href || "").indexOf("/demo/store") >= 0;
  }

  function merchantDemoStoreHref(mse) {
    var raw = (mse && mse.test_store_url) || "";
    if (isDemoStoreHref(raw)) {
      return raw;
    }
    return "/dashboard/test-widget";
  }

  function demoRetryHref(st, href) {
    var h = href || (st && st.action_href) || "";
    if (!isDemoStoreHref(h)) {
      return h;
    }
    if (h.indexOf("reset_demo=1") >= 0) {
      return h;
    }
    return h + (h.indexOf("?") >= 0 ? "&" : "?") + "reset_demo=1";
  }

  function unifiedSetupStepActionsHtml(st) {
    if (!st || st.locked) {
      return "";
    }
    var href = st.action_href || "#settings";
    var sec = sectionFromHref(href);
    var goAttr = sec
      ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
      : "";
    var extTarget = isDemoStoreHref(href) ? ' target="_blank" rel="noopener"' : "";
    if (st.repeatable_demo) {
      return (
        '<a class="ma-setup-step-action" href="/dashboard#home-test-tools" onclick="if(window.maHomeNav){maHomeNav(\'test-tools\');}return false;">أدوات التجربة</a>'
      );
    }
    if (!st.is_complete && !st.is_current) {
      return (
        '<a class="ma-setup-step-action" href="' +
        esc(href) +
        '"' +
        goAttr +
        ">" +
        esc(st.action_label_ar || "انتقل للخطوة") +
        "</a>"
      );
    }
    return "";
  }

  function renderUnifiedSetupDemoToolsOnly(mse, root) {
    if (!mse || !root) {
      return;
    }
    var demoSteps = [];
    var steps = mse.steps || [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].repeatable_demo && !steps[i].locked) {
        demoSteps.push(steps[i]);
      }
    }
    var testHref = merchantDemoStoreHref(mse);
    var testUrl = esc(testHref);
    var testExt = ' target="_blank" rel="noopener"';
    var rows = "";
    for (i = 0; i < demoSteps.length; i++) {
      rows +=
        '<li class="ma-setup-demo-tool-row">' +
        '<p class="ma-setup-demo-tool-title">' +
        esc(demoSteps[i].title_ar || "") +
        "</p>" +
        unifiedSetupStepActionsHtml(demoSteps[i]) +
        "</li>";
    }
    showTestToolsRoot(root);
    root.setAttribute("data-ma-setup-unified", "1");
    root.setAttribute("data-ma-setup-demo-tools", "1");
    root.innerHTML =
      '<div class="ma-setup-panel ma-unified-setup-panel ma-setup-v3 ma-setup-demo-tools">' +
      '<p class="ma-setup-v2-eyebrow">أدوات التجربة</p>' +
      '<p class="ma-setup-v2-context">يمكن لفريقك إعادة التجربة في أي وقت — الإكمال لا يعطّل الأزرار.</p>' +
      '<div class="ma-setup-hero-actions ma-setup-demo-tools-primary">' +
      '<a class="ma-setup-btn-primary" href="' +
      testUrl +
      '"' +
      testExt +
      ">فتح متجر الاختبار</a>" +
      '<a class="ma-setup-btn-secondary" href="/dashboard#carts" onclick="if(window.goTo){goTo(\'carts\');}return false;">عرض السلال</a>' +
      "</div>" +
      (rows
        ? '<ul class="ma-setup-demo-tools-list">' + rows + "</ul>"
        : "") +
      "</div>";
    logSetupRenderDebug("setup_render_demo_tools", {
      demo_steps: demoSteps.length,
    });
  }

  function unifiedSetupProgressHtml(steps) {
    if (!steps || !steps.length) return "";
    var html =
      '<div class="ma-setup-timeline-v3" role="list" aria-label="مسار الإعداد"><div class="ma-setup-timeline-v3-track">';
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      var done = !!st.is_complete && !st.locked;
      var cur = !!st.is_current && !st.locked;
      var locked = !!st.locked;
      var state = locked
        ? "is-upcoming"
        : done
          ? "is-done"
          : cur
            ? "is-current"
            : "is-upcoming";
      html +=
        '<span class="ma-setup-timeline-v3-step ' +
        state +
        '" role="listitem" title="' +
        esc(st.title_ar || "") +
        '"><span class="ma-setup-timeline-v3-dot" aria-hidden="true"></span></span>';
    }
    html +=
      '</div><div class="ma-setup-timeline-v3-legend" aria-hidden="true">' +
      '<span class="ma-setup-timeline-v3-legend-item"><span class="ma-setup-timeline-v3-dot is-done"></span> مكتمل</span>' +
      '<span class="ma-setup-timeline-v3-legend-item"><span class="ma-setup-timeline-v3-dot is-current"></span> الحالي</span>' +
      '<span class="ma-setup-timeline-v3-legend-item"><span class="ma-setup-timeline-v3-dot is-upcoming"></span> قادم</span>' +
      "</div></div>";
    return html;
  }

  function unifiedSetupStepsHtml(steps) {
    if (!steps || !steps.length) return "";
    var html = '<ul class="ma-onb-checklist ma-unified-setup-steps">';
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      if (st.locked) {
        html +=
          '<li class="ma-onb-checklist-item is-locked">' +
          '<span class="ma-onb-check" aria-hidden="true">🔒</span>' +
          '<div class="ma-onb-check-body">' +
          '<p class="ma-onb-check-title">' +
          esc(st.title_ar || "") +
          '</p><p class="ma-unified-locked-banner">يفتح بعد إثبات التجربة</p>' +
          '<p class="ma-onb-check-outcome ma-unified-locked-hint">' +
          esc(st.outcome_ar || "") +
          "</p></div></li>";
        continue;
      }
      var done = !!st.is_complete;
      var cur = !!st.is_current;
      var phaseTag =
        st.phase === "production"
          ? '<span class="ma-unified-phase ma-unified-phase-prod">إنتاج</span>'
          : '<span class="ma-unified-phase">تجربة</span>';
      var mark = done ? "✓" : cur ? "▶" : "◯";
      html +=
        '<li class="ma-onb-checklist-item' +
        (done ? " is-done" : " is-pending") +
        (cur ? " is-current" : "") +
        '">' +
        '<span class="ma-onb-check" aria-hidden="true">' +
        mark +
        "</span>" +
        '<div class="ma-onb-check-body">' +
        phaseTag +
        '<p class="ma-onb-check-title">' +
        esc(st.title_ar || "") +
        "</p>" +
        '<p class="ma-onb-check-outcome-label">النتيجة</p>' +
        '<p class="ma-onb-check-outcome">' +
        esc(st.outcome_ar || "") +
        "</p>";
      if (st.proof_ar && !cur) {
        html +=
          '<p class="ma-unified-proof"><span class="ma-unified-proof-k">الإثبات:</span> ' +
          esc(st.proof_ar) +
          "</p>";
      }
      html += unifiedSetupStepActionsHtml(st);
      html += "</div></li>";
    }
    html += "</ul>";
    return html;
  }

  function unifiedSetupHeroHtml(mse) {
    var currentStep = esc(mse.current_step_ar || "—");
    var currentOutcome = esc(mse.current_outcome_ar || "—");
    var rawHref = mse.action_href || mse.test_store_url || "/dashboard/test-widget";
    var steps = mse.steps || [];
    var curStep = null;
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] && steps[i].is_current && !steps[i].locked) {
        curStep = steps[i];
        break;
      }
    }
    var primaryLabel = esc(mse.action_label_ar || "ابدأ هذه الخطوة");
    if (curStep && curStep.repeatable_demo) {
      rawHref = "/dashboard#home-test-tools";
      primaryLabel = "انتقل إلى أدوات التجربة";
    }
    var primaryHref = esc(rawHref);
    var isExternalTest =
      !(curStep && curStep.repeatable_demo) && isDemoStoreHref(rawHref);
    var primaryTarget = isExternalTest ? ' target="_blank" rel="noopener"' : "";
    var primaryGo =
      curStep && curStep.repeatable_demo
        ? ' onclick="if(window.maHomeNav){maHomeNav(\'test-tools\');}return false;"'
        : "";
    return (
      '<section class="ma-setup-hero ma-setup-hero-v3" aria-label="الخطوة الحالية">' +
      '<p class="ma-setup-hero-eyebrow">الخطوة الحالية</p>' +
      '<h3 class="ma-setup-hero-title">' +
      currentStep +
      "</h3>" +
      '<p class="ma-setup-hero-sub">' +
      currentOutcome +
      "</p>" +
      '<div class="ma-setup-hero-actions">' +
      '<a class="ma-setup-btn-primary ma-setup-hero-cta" href="' +
      primaryHref +
      '"' +
      primaryTarget +
      primaryGo +
      ">" +
      primaryLabel +
      "</a>" +
      "</div></section>"
    );
  }

  function unifiedSetupCompletedCollapsedHtml(steps) {
    var done = [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i].is_complete && !steps[i].locked) {
        done.push(steps[i]);
      }
    }
    if (!done.length) return "";
    var lis = "";
    for (i = 0; i < done.length; i++) {
      lis +=
        '<li class="ma-setup-done-line"><span aria-hidden="true">✓</span> ' +
        esc(done[i].title_ar || "") +
        "</li>";
    }
    return (
      '<details class="ma-setup-done-collapse">' +
      "<summary><span class=\"ma-setup-done-summary-icon\" aria-hidden=\"true\">✓</span> " +
      done.length +
      " خطوة مكتملة</summary>" +
      '<ul class="ma-setup-done-list">' +
      lis +
      "</ul></details>"
    );
  }

  function unifiedSetupNextLockedHtml(steps) {
    var i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i].locked) {
        return (
          '<p class="ma-setup-locked-v3" role="status">يفتح بعد إثبات التجربة</p>'
        );
      }
    }
    return "";
  }

  function unifiedSetupUpcomingCompactHtml(steps) {
    var upcoming = [];
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      if (!st.locked && !st.is_complete && !st.is_current) {
        upcoming.push(st);
      }
    }
    if (!upcoming.length) return "";
    var rows = "";
    for (i = 0; i < upcoming.length; i++) {
      rows +=
        '<div class="ma-setup-upcoming-v3-row">' +
        "<span>" +
        esc(upcoming[i].title_ar || "") +
        "</span></div>";
    }
    return (
      '<details class="ma-setup-upcoming-v3">' +
      "<summary>الخطوات القادمة (" +
      upcoming.length +
      ")</summary>" +
      '<div class="ma-setup-upcoming-v3-body">' +
      rows +
      "</div></details>"
    );
  }

  function hasActivationJourneyV2(mse) {
    return !!(mse && mse.activation_journey_v2 && mse.onboarding_journey_v2);
  }

  function journeyStepMark(status) {
    if (status === "done") return "✅";
    if (status === "current") return "▶";
    return "🔒";
  }

  function journeyStepActionHtml(st) {
    if (!st || st.status !== "current") return "";
    var href = st.action_href || "#home";
    var sec = sectionFromHref(href);
    var goAttr = sec
      ? ' onclick="if(window.goTo){goTo(\'' + sec + "');}return false;\""
      : "";
    var extTarget =
      String(href).indexOf("/demo/store") >= 0
        ? ' target="_blank" rel="noopener"'
        : "";
    return (
      '<a class="ma-journey-v2-action ma-setup-btn-primary" href="' +
      esc(href) +
      '"' +
      goAttr +
      extTarget +
      ">" +
      esc(st.action_label_ar || "متابعة") +
      "</a>"
    );
  }

  function renderActivationJourneyV2(journey, root, mse) {
    var steps = journey.steps || [];
    var pct = parseInt(journey.progress_percent, 10) || 0;
    var label = esc(journey.progress_label_ar || "");
    var title = esc(journey.journey_title_ar || "تفعيل المتجر");
    var listHtml = "";
    var i;
    for (i = 0; i < steps.length; i++) {
      var st = steps[i];
      var cls =
        "ma-journey-v2-step is-" +
        String(st.status || "locked").replace(/[^a-z]/g, "");
      listHtml +=
        '<li class="' +
        cls +
        '">' +
        '<span class="ma-journey-v2-mark" aria-hidden="true">' +
        journeyStepMark(st.status) +
        "</span>" +
        '<div class="ma-journey-v2-body">' +
        '<p class="ma-journey-v2-title">' +
        esc(st.title_ar || "") +
        "</p>" +
        '<p class="ma-journey-v2-why">' +
        esc(st.why_ar || "") +
        "</p>" +
        journeyStepActionHtml(st) +
        "</div></li>";
    }
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-setup-unified", "1");
    root.setAttribute("data-ma-journey-v2", "1");
    root.innerHTML =
      '<div class="ma-setup-panel ma-journey-v2-panel">' +
      '<div class="ma-journey-v2-head">' +
      "<h2 class=\"ma-journey-v2-title-main\">" +
      title +
      "</h2>" +
      '<div class="ma-journey-v2-progress" role="status">' +
      '<div class="ma-journey-v2-progress-meta">' +
      '<span class="ma-journey-v2-progress-label">' +
      label +
      "</span>" +
      '<span class="ma-journey-v2-progress-pct">' +
      pct +
      "٪</span></div>" +
      '<div class="ma-journey-v2-progress-bar" aria-hidden="true">' +
      '<div class="ma-journey-v2-progress-fill" style="width:' +
      pct +
      '%;"></div></div></div></div>' +
      '<ul class="ma-journey-v2-checklist" aria-label="خطوات التفعيل">' +
      listHtml +
      "</ul>" +
      (mse && mse.delay_hint_ar
        ? '<p class="ma-journey-v2-hint">' + esc(mse.delay_hint_ar) + "</p>"
        : "") +
      "</div>";
  }

  function renderJourneyReadinessCard(journey, root) {
    var card = journey.readiness_card;
    if (!card) return;
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-journey-v2", "ready");
    var lines = (card.checklist_ar || [])
      .map(function (line) {
        return (
          '<li class="ma-journey-ready-line"><span aria-hidden="true">✓</span> ' +
          esc(line) +
          "</li>"
        );
      })
      .join("");
    root.innerHTML =
      '<div class="ma-setup-panel ma-journey-ready-card">' +
      "<h2 class=\"ma-journey-ready-title\">" +
      esc(card.title_ar || "") +
      "</h2>" +
      '<p class="ma-journey-ready-lead">' +
      esc(card.lead_ar || "") +
      "</p>" +
      '<ul class="ma-journey-ready-checklist">' +
      lines +
      "</ul>" +
      '<p class="ma-journey-ready-footer">' +
      esc(card.footer_ar || "") +
      "</p>" +
      '<a class="ma-setup-btn-primary ma-journey-ready-cta" href="' +
      esc(card.cta_href || "/dashboard#carts") +
      '" onclick="if(window.goTo){goTo(\'carts\');}return false;">' +
      esc(card.cta_label_ar || "الذهاب إلى لوحة السلال") +
      "</a></div>";
  }

  function applyActivationJourneyNavLocks(journey) {
    var locks = (journey && journey.nav_locks) || {};
    document.querySelectorAll(".ma-context-sidebar .nav-item[data-nav]").forEach(
      function (btn) {
        var page = btn.getAttribute("data-nav") || "";
        var lock = locks[page];
        var locked = !!(lock && lock.unlocked === false);
        btn.classList.toggle("is-journey-locked", locked);
        if (locked) {
          btn.setAttribute("data-journey-lock", "1");
          btn.setAttribute("title", lock.reason_ar || "");
        } else {
          btn.removeAttribute("data-journey-lock");
          btn.removeAttribute("title");
        }
      }
    );
  }

  function applyJourneyEmptyStates(journey) {
    if (!journey || journey.onboarding_complete) return;
    var hints = journey.empty_states || {};
    var cartsEmpty = document.querySelector("#page-carts tbody tr td.empty-state");
    if (cartsEmpty && hints.carts) {
      var h = hints.carts;
      cartsEmpty.innerHTML =
        '<div class="ma-journey-empty">' +
        '<div class="empty-icon">🛒</div>' +
        '<div class="empty-text ma-journey-empty-title">' +
        esc(h.title_ar || "") +
        "</div>" +
        '<p class="ma-journey-empty-body">' +
        esc(h.body_ar || "") +
        "</p>" +
        '<a class="ma-setup-btn-primary ma-journey-empty-cta" href="' +
        esc(h.cta_href || "#") +
        '">' +
        esc(h.cta_label_ar || "متابعة") +
        "</a></div>";
    }
    var msgEmpty = document.querySelector("#page-messages .empty-state");
    if (msgEmpty && hints.messages) {
      var hm = hints.messages;
      msgEmpty.innerHTML =
        '<div class="ma-journey-empty">' +
        '<div class="empty-icon">💬</div>' +
        '<div class="empty-text ma-journey-empty-title">' +
        esc(hm.title_ar || "") +
        "</div>" +
        '<p class="ma-journey-empty-body">' +
        esc(hm.body_ar || "") +
        "</p>" +
        '<a class="ma-setup-btn-primary ma-journey-empty-cta" href="' +
        esc(hm.cta_href || "#whatsapp") +
        '" onclick="if(window.goTo){goTo(\'whatsapp\');}return false;">' +
        esc(hm.cta_label_ar || "متابعة") +
        "</a></div>";
    }
  }

  function ensureJourneyGateElement(page) {
    var pageEl = byId("page-" + page);
    if (!pageEl) return null;
    var gateId = "ma-journey-gate-" + page;
    var gate = byId(gateId);
    if (!gate) {
      gate = document.createElement("div");
      gate.id = gateId;
      gate.className = "ma-journey-gate";
      gate.hidden = true;
      gate.setAttribute("hidden", "");
      pageEl.insertBefore(gate, pageEl.firstChild);
    }
    return gate;
  }

  function maApplyJourneyPageGate(page) {
    var journey = window.__maActivationJourney;
    if (!journey || journey.onboarding_complete) {
      document.querySelectorAll(".ma-journey-gate").forEach(function (g) {
        g.hidden = true;
        g.setAttribute("hidden", "");
      });
      document.querySelectorAll(".page.active .ma-page-inner").forEach(function (el) {
        el.classList.remove("ma-journey-gated");
      });
      return;
    }
    var gatedPages = ["settings", "whatsapp", "trigger-templates", "widget"];
    var i;
    for (i = 0; i < gatedPages.length; i++) {
      var p = gatedPages[i];
      var gate = ensureJourneyGateElement(p);
      var lock = journey.nav_locks && journey.nav_locks[p];
      var pageEl = byId("page-" + p);
      if (!gate || !pageEl) continue;
      if (p === page && lock && lock.unlocked === false) {
        gate.hidden = false;
        gate.removeAttribute("hidden");
        gate.innerHTML =
          '<div class="ma-journey-gate-card">' +
          '<p class="ma-journey-gate-kicker">🔒 ' +
          esc(lock.required_step_title_ar || "") +
          "</p>" +
          '<h3 class="ma-journey-gate-title">أكمل الخطوة السابقة أولاً</h3>' +
          '<p class="ma-journey-gate-body">' +
          esc(lock.reason_ar || "أكمل الخطوات بالترتيب لفتح هذا القسم.") +
          "</p>" +
          '<a class="ma-setup-btn-primary" href="' +
          esc(lock.cta_href || "/dashboard#home") +
          '">' +
          esc(lock.cta_label_ar || "متابعة الإعداد") +
          "</a></div>";
        pageEl.classList.add("ma-journey-gated");
      } else {
        gate.hidden = true;
        gate.setAttribute("hidden", "");
        if (p === page) pageEl.classList.remove("ma-journey-gated");
      }
    }
  }

  window.maApplyJourneyPageGate = maApplyJourneyPageGate;

  function applyActivationJourneySideEffects(journey) {
    window.__maActivationJourney = journey || null;
    applyActivationJourneyNavLocks(journey);
    applyJourneyEmptyStates(journey);
    try {
      var raw = (location.hash || "").split("?")[0].toLowerCase();
      var page = raw.replace(/^#/, "") || "home";
      maApplyJourneyPageGate(page);
    } catch (e) {
      maApplyJourneyPageGate("home");
    }
  }

  function renderUnifiedSetupExperience(mse, root) {
    var ready = !mse.setup_mode;
    var title = esc(mse.card_title_ar || "متجرك قريب من التشغيل الكامل");
    var contextLine =
      "اتبع الخطوة الحالية — لوحة التحكم اليومية تنتظرك بعد الإعداد.";
    showSetupExperienceRoot(root);
    root.setAttribute("data-ma-setup-unified", "1");
    root.innerHTML =
      '<div class="ma-setup-panel ma-onb-panel ma-unified-setup-panel ma-setup-v2 ma-setup-v3">' +
      (ready
        ? '<h2 class="ma-setup-home-title">' +
          title +
          "</h2>" +
          '<p class="ma-onb-celebration">' +
          esc(
            mse.celebration_message_ar ||
              "يمكن لـ CartFlow الآن البدء بمتابعة السلال."
          ) +
          "</p>"
        : '<p class="ma-setup-v2-eyebrow">' +
          esc(title) +
          "</p>" +
          '<p class="ma-setup-v2-context">' +
          esc(contextLine) +
          "</p>" +
          '<div class="ma-setup-v2-focus">' +
          unifiedSetupProgressHtml(steps) +
          unifiedSetupHeroHtml(mse) +
          unifiedSetupNextLockedHtml(steps) +
          unifiedSetupUpcomingCompactHtml(steps) +
          unifiedSetupCompletedCollapsedHtml(steps) +
          "</div>" +
          '<div class="ma-setup-v2-optional">' +
          '<div class="ma-setup-steps-toolbar">' +
          '<button type="button" class="ma-setup-btn-secondary" id="ma-setup-toggle-btn" aria-expanded="false" aria-controls="ma-setup-steps-panel">عرض كل خطوات الإعداد</button>' +
          "</div>" +
          '<div id="ma-setup-steps-panel" class="ma-setup-steps ma-setup-steps-full hidden"' +
          ' role="region" aria-label="جميع خطوات الإعداد">' +
          unifiedSetupStepsHtml(steps) +
          "</div></div>") +
      "</div>";

    var btn = byId("ma-setup-toggle-btn");
    var panel = byId("ma-setup-steps-panel");
    if (btn && panel) {
      btn.addEventListener("click", function () {
        panel.classList.toggle("hidden");
        var collapsed = panel.classList.contains("hidden");
        btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
        btn.textContent = collapsed
          ? "عرض كل خطوات الإعداد"
          : "إخفاء قائمة الإعداد";
      });
    }
  }

  function applyMerchantSetupExperience(mse) {
    var root = byId("ma-setup-experience-root");
    applyOnboardingHomeFocus(mse);
    hideActivationForUnifiedSetup(mse);
    if (!root) return;
    if (!mse || mse.show_card === false) {
      root.hidden = true;
      root.setAttribute("hidden", "");
      root.innerHTML = "";
      logSetupRenderDebug("setup_skip", { reason: "show_card_false", mse: !!mse });
      return;
    }
    if (shouldRenderUnifiedSetup(mse)) {
      if (hasActivationJourneyV2(mse)) {
        var journey = mse.activation_journey_v2;
        if (mse.onboarding_complete && journey.readiness_card) {
          renderJourneyReadinessCard(journey, root);
        } else {
          renderActivationJourneyV2(journey, root, mse);
        }
        applyActivationJourneySideEffects(journey);
      } else {
        renderUnifiedSetupExperience(mse, root);
      }
      showSetupExperienceRoot(root);
      logSetupRenderDebug("setup_render_unified", probeSetupExperienceRoot());
      return;
    }
    if (isUnifiedSetup(mse) && mse.setup_mode === false) {
      root.hidden = true;
      root.setAttribute("hidden", "");
      root.innerHTML = "";
      var testToolsRoot = byId("ma-test-tools-root");
      if (testToolsRoot) {
        renderUnifiedSetupDemoToolsOnly(mse, testToolsRoot);
      }
      logSetupRenderDebug("setup_render_demo_tools", probeSetupExperienceRoot());
      return;
    }
    var steps = mse.steps || [];
    var totalSteps = parseInt(mse.total_steps, 10) || steps.length || 5;
    var completed =
      parseInt(mse.completed_steps, 10) ||
      steps.filter(function (s) {
        return s.is_complete;
      }).length;
    var remaining = parseInt(mse.remaining_setup_count, 10);
    if (isNaN(remaining)) remaining = Math.max(0, totalSteps - completed);
    var ready = !!(mse.onboarding_complete || mse.first_recovery_ready);
    var title = esc(mse.card_title_ar || "إعداد متجرك");
    var lead = esc(
      mse.card_lead_ar ||
        mse.celebration_message_ar ||
        "أكمل الخطوات للوصول إلى أول جاهزية للاسترجاع."
    );
    var currentStep = esc(mse.current_step_ar || mse.next_step_ar || "—");
    var currentOutcome = esc(
      mse.current_outcome_ar || mse.outcome_summary_ar || "—"
    );
    var progressLabel = completed + " / " + totalSteps + " مكتمل";
    var panelOpen = !ready;
    showSetupExperienceRoot(root);
    root.innerHTML =
      '<div class="ma-setup-panel ma-onb-panel">' +
      '<h2 class="ma-setup-home-title">' +
      title +
      "</h2>" +
      (lead ? '<p class="ma-setup-panel-lead">' + lead + "</p>" : "") +
      (ready
        ? '<p class="ma-onb-celebration">' +
          esc(
            mse.celebration_message_ar ||
              "يمكن لـ CartFlow الآن البدء بمتابعة السلال."
          ) +
          "</p>"
        : '<div class="ma-onb-progress-row">' +
          '<span class="ma-onb-progress-k">التقدّم</span>' +
          '<span class="ma-onb-progress-v">' +
          esc(progressLabel) +
          "</span></div>" +
          '<div class="ma-setup-home-meta ma-onb-current">' +
          '<div class="ma-setup-home-row"><span class="ma-setup-home-k">الخطوة الحالية</span><span class="ma-setup-home-v">' +
          currentStep +
          "</span></div>" +
          '<div class="ma-setup-home-row"><span class="ma-setup-home-k">النتيجة المتوقعة</span><span class="ma-setup-home-v">' +
          currentOutcome +
          "</span></div></div>" +
          '<div class="ma-setup-actions">' +
          '<button type="button" class="ma-setup-btn-primary" id="ma-setup-toggle-btn" aria-expanded="' +
          (panelOpen ? "true" : "false") +
          '" aria-controls="ma-setup-steps-panel">أكمل الإعداد</button>' +
          '<a class="ma-setup-btn-secondary" href="' +
          esc(mse.action_href || "#settings") +
          '" onclick="var s=\'' +
          esc(sectionFromHref(mse.action_href || "")) +
          "';if(window.goTo&&s){goTo(s);}return false;\">انتقل للخطوة</a>" +
          "</div>" +
          '<div id="ma-setup-steps-panel" class="ma-setup-steps"' +
          (panelOpen ? "" : " hidden") +
          ' role="region" aria-label="خطوات الإعداد">' +
          setupStepsHtml(steps) +
          "</div>") +
      "</div>";

    var btn = byId("ma-setup-toggle-btn");
    var panel = byId("ma-setup-steps-panel");
    if (btn && panel) {
      btn.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
        btn.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
      });
    }
  }

  function applyTopbarReadiness(d) {
    var sk = (d.wa_state_key || "").trim();
    var badge = d.wa_badge_ar || "—";
    var pPill = byId("ma-page-whatsapp-ready-pill");
    var pTxt = byId("ma-page-whatsapp-ready-text");
    if (pPill && pTxt) {
      pPill.classList.toggle("wa-muted", sk !== "ready");
      pTxt.textContent = badge;
    }
  }

  function reasonWeekRowHtml(rr) {
    var pct = parseFloat(rr.count_pct) || 0;
    var col = esc(rr.fill_color || "#6C5CE7");
    return (
      '<div class="r-row">' +
      '<div class="r-head"><span class="r-name">' +
      esc(rr.label_ar) +
      '</span><span class="r-pct">' +
      Math.round(pct) +
      "٪</span></div>" +
      '<div class="track"><div class="fill" style="width:' +
      pct +
      "%;background:" +
      col +
      ';"></div></div></div>'
    );
  }

  function reasonMonthRowHtml(rb) {
    var pct = parseFloat(rb.count_pct) || 0;
    var col = esc(rb.fill_color || "#6C5CE7");
    return (
      '<div class="r-big">' +
      '<div class="r-big-head"><span class="r-big-name">' +
      esc(rb.label_ar) +
      '</span><span class="r-big-pct">' +
      Math.round(pct) +
      "٪</span></div>" +
      '<div class="track-lg"><div class="fill-lg" style="width:' +
      pct +
      "%;background:" +
      col +
      ';"></div></div></div>'
    );
  }

  function applySummary(d) {
    if (!d || !d.ok) {
      logSetupRenderDebug("summary_skip", { ok: !!(d && d.ok) });
      return;
    }
    var dbg =
      d.merchant_setup_render_debug ||
      (d.merchant_setup_experience &&
        d.merchant_setup_experience.MERCHANT_SETUP_RENDER_BUILD
        ? {
            MERCHANT_SETUP_RENDER_BUILD:
              d.merchant_setup_experience.MERCHANT_SETUP_RENDER_BUILD,
            unified_p0: d.merchant_setup_experience.unified_p0,
            setup_mode: d.merchant_setup_experience.setup_mode,
            show_card: d.merchant_setup_experience.show_card,
          }
        : null);
    logSetupRenderDebug("summary_payload", dbg);
    setText("ma-topbar-date", d.merchant_ar_date_header || "");
    ingestRefreshToken(d, "summary");
    applyTopbarReadiness(d);
    applySetupReadinessPanelWithFallback(d);
    applyMerchantSetupExperience(d.merchant_setup_experience);
    if (
      d.merchant_setup_experience &&
      d.merchant_setup_experience.activation_journey_v2
    ) {
      applyActivationJourneySideEffects(
        d.merchant_setup_experience.activation_journey_v2
      );
    }
    applyHomeLayoutAfterSetup(d.merchant_activation, d.merchant_setup_experience);
    logSetupRenderDebug("summary_dom", probeSetupExperienceRoot());

    if (window.maApplyHomeExperience) {
      window.maApplyHomeExperience(
        d.merchant_home_experience_v1 || { ok: false }
      );
    }

    setText("ma-kpi-abandoned", d.merchant_kpi_abandoned_fmt || "0");
    setText("ma-kpi-recovered", d.merchant_kpi_recovered_fmt || "0");
    setText("ma-kpi-wa", d.merchant_kpi_wa_sent_fmt || "0");
    setText("ma-kpi-revenue", d.merchant_kpi_revenue_fmt || "0");

    var pct = parseFloat(d.merchant_kpi_recovered_pct_vs_abandoned) || 0;
    var note = byId("ma-kpi-recovered-note");
    if (note) {
      stripSkel(note);
      if (pct > 0) {
        note.textContent = "↑ نسبة " + Math.round(pct) + "٪";
        note.className = "kpi-note up";
      } else {
        note.textContent = "—";
        note.className = "kpi-note neutral";
      }
    }

    setText("ma-month-abandoned", d.merchant_month_abandoned_fmt || "0");
    setText("ma-month-recovered", d.merchant_month_recovered_fmt || "0");
    setText("ma-month-pct", (d.merchant_month_recovery_pct_fmt || "0") + "٪");
    setText("ma-month-revenue", formatMerchantSar(String(d.merchant_month_revenue_fmt || "0").replace(/,/g, "")));

    var wk = byId("ma-reasons-week-body");
    if (wk) {
      var rowsW = d.merchant_reason_rows_week || [];
      var htmlW = "";
      if (!rowsW.length) {
        htmlW =
          '<div class="empty-text" style="padding:12px;color:var(--muted);">لا توجد بيانات أسباب التردد لهذا الأسبوع</div>';
      } else {
        htmlW = rowsW.map(reasonWeekRowHtml).join("");
      }
      if (d.merchant_reason_insight_ar) {
        htmlW +=
          '<div class="r-insight">' + esc(d.merchant_reason_insight_ar) + "</div>";
      }
      wk.innerHTML = htmlW;
    }

    var mo = byId("ma-reasons-month-body");
    if (mo) {
      var h3 = mo.querySelector("h3");
      var h3txt = h3 ? h3.outerHTML : "<h3>توزيع الأسباب — آخر 30 يوماً</h3>";
      var rowsM = d.merchant_reason_rows_month || [];
      if (!rowsM.length) {
        mo.innerHTML =
          h3txt +
          '<div class="empty-text" style="padding:16px;">لا توجد بيانات أسباب كافية لهذه الفترة</div>';
      } else {
        mo.innerHTML = h3txt + rowsM.map(reasonMonthRowHtml).join("");
      }
    }

    var ins = byId("ma-reasons-insights");
    if (ins) {
      var lines = d.merchant_reason_recommendations_ar || [];
      var body = lines
        .map(function (ln) {
          return '<div class="ib-item">📌 ' + esc(ln) + "</div>";
        })
        .join("");
      if (!body) {
        body = '<div class="ib-item">—</div>';
      }
      ins.innerHTML = '<div class="ib-title">💡 توصيات</div>' + body;
    }

    setNavBadge(
      "ma-nav-badge-abandoned",
      d.merchant_nav_badge_abandoned != null
        ? d.merchant_nav_badge_abandoned
        : hasCanonicalStoreCartCounts(d)
          ? resolveMerchantStoreCartCounts(d).waiting
          : 0
    );
    setNavBadge("ma-nav-badge-followup", d.merchant_nav_badge_followup);
    setNavBadge("ma-nav-badge-vip", d.merchant_nav_badge_vip);

    var sm = byId("ma-settings-month-cart-line");
    if (sm) {
      sm.textContent =
        (d.merchant_month_abandoned_fmt || "0") + " سلة مسجّلة";
    }
  }

  var MERCHANT_INTERVENTION_PRIMARY_KEYS = {
    channel_failed: 1,
    needs_phone: 1,
    needs_reason: 1,
    attempts_exhausted: 1,
    stopped_manual: 1,
  };

  var MERCHANT_REASON_GOAL_AR = {
    price: "معالجة قلق السعر",
    price_high: "معالجة قلق السعر",
    shipping: "طمأنة حول الشحن",
    delivery: "طمأنة حول الشحن",
    thinking: "دعم اتخاذ القرار",
    warranty: "طمأنة حول الجودة",
    quality: "طمأنة حول الجودة",
    human_support: "طمأنة حول الجودة",
    trust: "طمأنة حول الجودة",
  };

  function merchantReasonGoalAr(reasonTag) {
    var k = String(reasonTag || "")
      .trim()
      .toLowerCase();
    if (!k) return "";
    return MERCHANT_REASON_GOAL_AR[k] || "متابعة سبب التردد";
  }

  function merchantTruncateText(text, maxLen) {
    var raw = String(text || "").trim();
    if (!raw) return "";
    if (raw.length <= maxLen) return raw;
    return raw.slice(0, maxLen - 1).trim() + "…";
  }

  function merchantPreviewFromWhatsappLine(line) {
    var s = String(line || "").trim();
    if (!s || s.indexOf("—") < 0) return "";
    var tail = s.split("—").slice(1).join("—").trim();
    if (tail.indexOf("(") === 0 && tail.lastIndexOf(")") === tail.length - 1) {
      tail = tail.slice(1, -1).trim();
    }
    if (tail && tail.indexOf("ننتظر") !== 0) return tail;
    return "";
  }

  function merchantSentMessageLine(mc) {
    var prev =
      String(mc.message_preview || "").trim() ||
      merchantPreviewFromWhatsappLine(mc.merchant_whatsapp_line_ar);
    if (prev) return '"' + merchantTruncateText(prev, 80) + '"';
    return "تم إرسال رسالة مناسبة لسبب التردد";
  }

  function merchantAttemptsDisplayAr(fr) {
    fr = fr || {};
    var raw = String(fr.attempts_ar || "").trim();
    var inbound = String(fr.inbound_message || "").trim();
    var replied = !!inbound;
    if (!replied) {
      var line = String(fr.last_message_line_ar || "").trim();
      replied =
        line.length > 0 &&
        line.indexOf("لا يوجد رد") < 0 &&
        line.indexOf("يتابع النظام") < 0;
    }
    var m = raw.match(/(\d+)\s*رسالة/);
    var n = m ? parseInt(m[1], 10) : 0;
    if (raw.indexOf("عدد الرسائل:") === 0) return raw;
    if (raw.indexOf("تمت متابعة") === 0) return raw;
    if (raw.indexOf("أُرسلت رسالة —") === 0) return raw;
    if (raw.indexOf("تم إرسال أول") === 0) return raw;
    if (raw.indexOf("لم تبدأ") === 0) return raw;
    if (n >= 3) return "عدد الرسائل: " + n;
    if (n === 2) return "تمت متابعة إضافية";
    if (n === 1) return "أُرسلت رسالة — لا توجد متابعات إضافية بعد";
    if (replied) return "تم إرسال أول رسالة استرداد";
    if (n === 0 && raw.indexOf("لا توجد") >= 0) {
      return replied ? "تم إرسال أول رسالة استرداد" : "لم تبدأ عملية الاسترداد بعد";
    }
    return raw || "—";
  }

  function merchantReplyPreview(fr) {
    var raw = String((fr && fr.inbound_message) || "").trim();
    if (!raw && fr && fr.last_message_line_ar) {
      var line = String(fr.last_message_line_ar).trim();
      if (
        line &&
        line.indexOf("لا يوجد رد") < 0 &&
        line.indexOf("يتابع النظام") < 0
      ) {
        raw = line;
      }
    }
    if (!raw) return "";
    return '"' + merchantTruncateText(raw, 60) + '"';
  }

  function merchantNeedsIntervention(mc) {
    if (!mc) return false;
    if (mc.merchant_next_action_urgent) return true;
    var pk = String(mc.merchant_lifecycle_primary_key || "")
      .trim()
      .toLowerCase();
    return !!MERCHANT_INTERVENTION_PRIMARY_KEYS[pk];
  }


  function merchantLifecycleCompact(mc) {
    var pk = String(mc.merchant_lifecycle_primary_key || "")
      .trim()
      .toLowerCase();
    var coarse = String(
      mc.merchant_coarse_status || mc.recovery_status || ""
    )
      .trim()
      .toLowerCase();
    var needs = merchantNeedsIntervention(mc);
    var pur = String(mc.merchant_purchase_line_ar || "").trim();
    var ret = String(mc.merchant_return_line_ar || "").trim();
    var status = "قيد المتابعة";
    var action = "النظام يتابع تلقائياً";
    var waiting = "النظام يتابع تلقائياً";
    if (pk === "customer_replied" || coarse === "replied" || coarse === "engaged") {
      status = "تفاعل العميل";
      action = "بدأ النظام متابعة الاعتراض";
      waiting = "النظام يتابع تلقائياً";
    } else if (pur || pk === "purchase_complete" || coarse === "converted") {
      status = "اكتمل الشراء";
      action = "انتهت مهمة الاسترجاع";
      waiting = "—";
    } else if (ret || pk === "customer_returned" || coarse === "returned") {
      status = "عاد للموقع";
      action = "أوقفنا الرسائل";
      waiting = "—";
    } else if (
      pk === "awaiting_customer_after_send" ||
      pk === "message_sent" ||
      coarse === "sent"
    ) {
      status = "أُرسلت رسالة";
      action = "—";
      waiting = "ننتظر تفاعل العميل";
    } else if (
      pk === "delay_waiting" ||
      pk === "no_engagement_yet" ||
      pk === "automation_paused" ||
      pk === "pending_schedule" ||
      coarse === "pending"
    ) {
      status = "بانتظار الإرسال";
      action = "—";
      waiting = "بانتظار وقت الإرسال";
    } else if (
      pk === "channel_failed" ||
      pk === "needs_phone" ||
      pk === "needs_reason" ||
      pk === "attempts_exhausted"
    ) {
      status = "يحتاج إجراء";
      action = "راجع الإعدادات";
      waiting = "—";
    }
    var isSent =
      pk === "awaiting_customer_after_send" ||
      pk === "message_sent" ||
      coarse === "sent";
    var isInteraction =
      pk === "customer_replied" || coarse === "replied" || coarse === "engaged";
    return {
      status: status,
      action: action,
      waiting: waiting,
      needsIntervention: needs,
      messageLine: isSent ? merchantSentMessageLine(mc) : "",
      goalLine: merchantReasonGoalAr(mc.reason_tag) || "",
      isSent: isSent,
      isInteraction: isInteraction,
    };
  }

  function merchantLifecycleCompactHtml(mc) {
    var c = merchantLifecycleCompact(mc);
    var h =
      '<div class="recovery-truth recovery-truth-compact" aria-label="ملخص المسار">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> ' +
      esc(c.status) +
      "</div>";
    if (c.messageLine) {
      h +=
        '<div class="recovery-truth-line"><strong>الرسالة:</strong> ' +
        esc(c.messageLine) +
        "</div>";
    }
    if (c.goalLine) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> ' +
        esc(c.goalLine) +
        "</div>";
    } else if (c.isSent) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> اختار النظام رسالة مناسبة بناءً على سبب التردد.</div>';
    }
    if (c.waiting && c.waiting !== "—") {
      h +=
        '<div class="recovery-truth-line"><strong>الانتظار:</strong> ' +
        esc(c.waiting) +
        "</div>";
    }
    h += merchantFollowupClarityHtml(mc);
    if (c.action && c.action !== "—" && !c.isSent) {
      h +=
        '<div class="recovery-truth-line"><strong>الإجراء:</strong> ' +
        esc(c.action) +
        "</div>";
    }
    if (mc && mc.merchant_intervention_executable) {
      h +=
        '<div class="recovery-truth-line"><strong>تدخل:</strong> نعم</div>';
    }
    return h + "</div>";
  }

  var FOLLOWUP_OPTIONAL_MANUAL_CONTACT_LINE_AR =
    "المتابعة الآلية فعّالة، والتواصل اليدوي متاح عند الحاجة.";

  function followupCompactHtml(fr) {
    fr = fr || {};
    var goal = merchantReasonGoalAr(fr.reason_tag_raw || fr.reason_tag_ar);
    var reply = merchantReplyPreview(fr);
    var href = String(fr.contact_wa_href || "").trim();
    var h =
      '<div class="recovery-truth recovery-truth-compact" aria-label="ملخص التفاعل">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> تفاعل العميل</div>';
    if (reply) {
      h +=
        '<div class="recovery-truth-line"><strong>رد العميل:</strong> ' +
        esc(reply) +
        "</div>";
    }
    h +=
      '<div class="recovery-truth-line"><strong>المتابعة:</strong> ' +
      esc(
        href
          ? FOLLOWUP_OPTIONAL_MANUAL_CONTACT_LINE_AR
          : "النظام يتابع تلقائياً"
      ) +
      "</div>";
    if (goal) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> ' +
        esc(goal) +
        "</div>";
    } else if (fr.reason_tag_raw) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> اختار النظام رسالة مناسبة بناءً على سبب التردد.</div>';
    }
    if (href) {
      h +=
        '<div class="recovery-truth-actions"><a class="cf-lc-btn cf-lc-btn-contact" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer"><span class="cf-lc-btn-icon" aria-hidden="true">💬</span> فتح واتساب</a></div>';
    }
    return h + "</div>";
  }

  function merchantNextLineShort(mc) {
    if (mc && mc.customer_lifecycle_label_ar) {
      return String(mc.customer_lifecycle_label_ar).trim();
    }
    return "— لا تتوفر حالة واضحة بعد —";
  }

  var lastNormalCartsPageRows = [];
  var lastArchivedCartsPageRows = [];
  var lastMerchantIntelligencePayload = null;
  var lastMiCartsWorkspaceKey = "";
  var miCartsDidInitialSelect = false;

  function isArchivedVisual(mc) {
    if (!mc) return false;
    if (mc.customer_lifecycle_is_archived_visual === true) return true;
    return String(mc.customer_lifecycle_state || "").trim() === "archived";
  }

  function cartLifecycleStatusClass(mc) {
    if (isArchivedVisual(mc)) return "s-archived";
    return mc.customer_lifecycle_status_row_class || "s-waiting";
  }

  function cartLifecycleStatusLabel(mc) {
    if (isArchivedVisual(mc)) return "✓ مؤرشفة";
    return mc.customer_lifecycle_label_ar || "— لا تتوفر حالة واضحة بعد —";
  }

  function sortCartsArchivedLast(rows) {
    return rows.slice().sort(function (a, b) {
      var aa = isArchivedVisual(a) ? 1 : 0;
      var bb = isArchivedVisual(b) ? 1 : 0;
      if (aa !== bb) return aa - bb;
      return 0;
    });
  }

  function cartRowMatchesFilterMode(mc, mode) {
    var m = (mode || "all").trim().toLowerCase();
    if (m === "completed") m = "recovered";
    if (m === "all") return true;
    if (!mc) return false;
    var primary = String(mc.merchant_cart_primary_bucket || "")
      .trim()
      .toLowerCase();
    if (primary && (primary === m || (m === "recovered" && primary === "completed"))) {
      return true;
    }
    var bucket = String(mc.merchant_cart_bucket || "").trim().toLowerCase();
    if (
      bucket &&
      (bucket === m || (m === "recovered" && bucket === "completed"))
    ) {
      return true;
    }
    var tabs = mc.merchant_cart_visible_tabs;
    if (Array.isArray(tabs)) {
      for (var i = 0; i < tabs.length; i++) {
        var tk = String(tabs[i] || "").trim().toLowerCase();
        if (tk === m || (m === "recovered" && tk === "completed")) return true;
      }
    }
    if (m === "recovered") {
      return isCompletedDashboardRow(mc);
    }
    return false;
  }

  function isArchivedDestinationRow(mc) {
    return isArchivedVisual(mc);
  }

  function isCompletedDashboardRow(mc) {
    if (!mc) return false;
    if (isArchivedDestinationRow(mc)) return true;
    var lc = String(mc.customer_lifecycle_state || "").trim().toLowerCase();
    if (lc === "completed") return true;
    if (String(mc.merchant_coarse_status || "").trim().toLowerCase() === "converted") {
      return true;
    }
    if (String(mc.customer_lifecycle_completed_variant || "").trim() === "purchased") {
      return true;
    }
    var primary = String(mc.merchant_cart_primary_bucket || "").trim().toLowerCase();
    if (primary === "recovered" || primary === "completed") return true;
    var bucket = String(mc.merchant_cart_bucket || "").trim().toLowerCase();
    if (bucket === "recovered" || bucket === "completed") return true;
    var tabs = mc.merchant_cart_visible_tabs;
    if (Array.isArray(tabs)) {
      for (var i = 0; i < tabs.length; i++) {
        var tk = String(tabs[i] || "").trim().toLowerCase();
        if (tk === "recovered" || tk === "completed") return true;
      }
    }
    var lbl = String(mc.customer_lifecycle_label_ar || "");
    if (lbl.indexOf("تم الشراء") >= 0) return true;
    if (lbl.indexOf("تمت الاستعادة") >= 0) return true;
    if (lbl.indexOf("تم الاسترجاع") >= 0) return true;
    if (mc.merchant_cart_is_terminal === true && lbl.indexOf("تم") >= 0) {
      return true;
    }
    return false;
  }

  function trLooksCompletedRow(tr) {
    if (!tr) return false;
    if (tr.getAttribute("data-ma-archived-visual") === "1") return true;
    if (tr.getAttribute("data-ma-completed") === "1") return true;
    var filter = (tr.getAttribute("data-ma-filter") || "").trim().toLowerCase();
    if (filter === "recovered" || filter === "completed") return true;
    var primary = (tr.getAttribute("data-ma-primary-bucket") || "")
      .trim()
      .toLowerCase();
    if (primary === "recovered" || primary === "completed") return true;
    try {
      var tabs = JSON.parse(tr.getAttribute("data-ma-visible-tabs") || "[]");
      if (Array.isArray(tabs)) {
        for (var i = 0; i < tabs.length; i++) {
          var tk = String(tabs[i] || "").trim().toLowerCase();
          if (tk === "recovered" || tk === "completed") return true;
        }
      }
    } catch (eTabs) {
      /* ignore */
    }
    var txt = tr.textContent || "";
    if (txt.indexOf("تم الشراء") >= 0) return true;
    if (txt.indexOf("تمت الاستعادة") >= 0) return true;
    return false;
  }

  function completedCartsFromRows(rows, archivedRows) {
    var seen = {};
    var out = [];
    function push(mc) {
      if (!mc || !isCompletedDashboardRow(mc)) return;
      var rk = String(mc.recovery_key || "").trim();
      var rid = mc.merchant_case_row_id != null ? String(mc.merchant_case_row_id) : "";
      var key = rk || rid || String(mc.session_id || "").trim();
      if (key && seen[key]) return;
      if (key) seen[key] = true;
      out.push(mc);
    }
    (archivedRows || []).forEach(push);
    (rows || []).forEach(push);
    return sortCartsArchivedLast(out);
  }

  function completedRowsHtmlFromAllTableDom() {
    var src = document.querySelector("#ma-tbody-all-carts");
    if (!src) return "";
    var html = "";
    var n = 0;
    src.querySelectorAll("tr[data-ma-filter]").forEach(function (tr) {
      if (!trLooksCompletedRow(tr)) return;
      html += tr.outerHTML;
      n += 1;
    });
    return n ? html : "";
  }

  function logCompletedTab(total, completed, source) {
    try {
      console.log(
        "[COMPLETED TAB] rows_total=" +
          String(total == null ? 0 : total) +
          " completed_rows=" +
          String(completed == null ? 0 : completed) +
          (source ? " source=" + source : "")
      );
    } catch (eLog) {
      /* ignore */
    }
  }

  function applyCompletedCartsTable(rows, archivedRows) {
    var tbody = byId("ma-tbody-completed");
    var total = (rows || []).length + (archivedRows || []).length;
    if (!tbody) {
      logCompletedTab(total, 0, "missing_tbody");
      return;
    }
    var completed = completedCartsFromRows(rows, archivedRows);
    if (completed.length) {
      tbody.innerHTML = completed.map(cartRowTableDisplay).join("");
      bindCustomerLifecycleActions(tbody);
      logCompletedTab(total, completed.length, "payload");
      return;
    }
    var domHtml = completedRowsHtmlFromAllTableDom();
    if (domHtml) {
      tbody.innerHTML = domHtml;
      bindCustomerLifecycleActions(tbody);
      var domCount = tbody.querySelectorAll("tr[data-ma-filter]").length;
      logCompletedTab(total, domCount, "dom_from_all_tab");
      return;
    }
    tbody.innerHTML =
      '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">✅</div><div class="empty-text">لا توجد سلال مكتملة حالياً ضمن نطاق متجرك</div></td></tr>';
    logCompletedTab(total, 0, "empty");
  }

  window.maRefreshCompletedCartsTable = function () {
    var rows = lastNormalCartsPageRows || [];
    var archived = lastArchivedCartsPageRows || [];
    if (!rows.length && window.__maNormalCartsPageRows) {
      rows = window.__maNormalCartsPageRows;
    }
    applyCompletedCartsTable(rows, archived);
    if (
      !rows.length &&
      !window.__maCompletedTabFetchPending &&
      typeof fetchSection === "function"
    ) {
      window.__maCompletedTabFetchPending = true;
      fetchNormalCarts("completed_tab_retry").finally(function () {
        window.__maCompletedTabFetchPending = false;
      });
    }
  };

  function cartDetailProjection(mc) {
    var proj = mc && mc.cart_detail_projection_v1;
    return proj && proj.version === "v1" ? proj : null;
  }

  function merchantInterventionContactBtnHtml(mc) {
    var proj = cartDetailProjection(mc);
    var contact = proj && proj.contact_action;
    if (contact && contact.visible && contact.href) {
      return (
        '<div class="recovery-truth-actions"><a class="cf-lc-btn cf-lc-btn-contact" href="' +
        esc(contact.href) +
        '" target="_blank" rel="noopener noreferrer"><span class="cf-lc-btn-icon" aria-hidden="true">💬</span> ' +
        esc(contact.label_ar || "فتح واتساب") +
        "</a></div>"
      );
    }
    if (!proj && mc && mc.merchant_intervention_executable) {
      var href = String(mc.merchant_intervention_contact_href || "").trim();
      if (!href) return "";
      var lbl = String(mc.merchant_intervention_action_ar || "فتح واتساب").trim();
      return (
        '<div class="recovery-truth-actions"><a class="cf-lc-btn cf-lc-btn-contact" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer"><span class="cf-lc-btn-icon" aria-hidden="true">💬</span> ' +
        esc(lbl) +
        "</a></div>"
      );
    }
    return "";
  }

  function cartLifecycleActionBtnHtml(mc) {
    var proj = cartDetailProjection(mc);
    var lc = proj && proj.lifecycle_ui;
    var rk = lc && lc.recovery_key ? lc.recovery_key : String(mc.recovery_key || "").trim();
    if (!rk) return "";
    var h = merchantInterventionContactBtnHtml(mc);
    if (lc) {
      if (lc.archive_visible) {
        h +=
          '<div class="recovery-truth-actions"><button type="button" class="cf-lc-btn cf-lc-btn-archive" data-lc-archive data-recovery-key="' +
          esc(rk) +
          '"><span class="cf-lc-btn-icon" aria-hidden="true">🗂</span> نقل للأرشيف</button></div>';
      }
      if (lc.reopen_visible) {
        h +=
          '<div class="recovery-truth-actions"><button type="button" class="cf-lc-btn cf-lc-btn-reopen" data-lc-reopen data-recovery-key="' +
          esc(rk) +
          '"><span class="cf-lc-btn-icon" aria-hidden="true">↩</span> إعادة فتح</button></div>';
      }
      return h;
    }
    var act = String(mc.customer_lifecycle_dashboard_action || "").trim();
    if (act === "archive") {
      h +=
        '<div class="recovery-truth-actions"><button type="button" class="cf-lc-btn cf-lc-btn-archive" data-lc-archive data-recovery-key="' +
        esc(rk) +
        '"><span class="cf-lc-btn-icon" aria-hidden="true">🗂</span> نقل للأرشيف</button></div>';
    }
    if (act === "reopen") {
      h +=
        '<div class="recovery-truth-actions"><button type="button" class="cf-lc-btn cf-lc-btn-reopen" data-lc-reopen data-recovery-key="' +
        esc(rk) +
        '"><span class="cf-lc-btn-icon" aria-hidden="true">↩</span> إعادة فتح</button></div>';
    }
    return h;
  }

  var peV2SelectedRecoveryKey = null;

  function cartRecoveryKey(mc) {
    return String((mc && (mc.recovery_key || mc.recovery_session_id)) || "").trim();
  }

  function resolveMerchantExplanation(mc) {
    var proj = cartDetailProjection(mc);
    if (proj && proj.explanation) return proj.explanation;
    var ex = mc && mc.merchant_explanation_v1;
    if (ex && ex.version === "v1") {
      return {
        status_label_ar: ex.status_label_ar,
        what_happened_ar: ex.what_happened_ar,
        system_did_ar: ex.system_did_ar,
        what_next_ar: ex.what_next_ar,
        followup_line_ar: ex.followup_line_ar,
        merchant_action_needed_ar: ex.merchant_action_needed_ar,
        action_required: ex.action_required,
      };
    }
    return null;
  }

  function findCartByRecoveryKey(rk) {
    rk = String(rk || "").trim();
    if (!rk) return null;
    for (var i = 0; i < lastNormalCartsPageRows.length; i++) {
      if (cartRecoveryKey(lastNormalCartsPageRows[i]) === rk) {
        return lastNormalCartsPageRows[i];
      }
    }
    return null;
  }

  function merchantPeV2QueueAccentClass(mc) {
    if (isArchivedVisual(mc)) return "v2-queue-accent--calm";
    if (mc.merchant_next_action_urgent) return "v2-queue-accent--attention";
    var b = String(
      mc.merchant_cart_primary_bucket || mc.merchant_cart_bucket || ""
    )
      .trim()
      .toLowerCase();
    if (b === "attention") return "v2-queue-accent--attention";
    if (b === "sent" || b === "waiting") return "v2-queue-accent--waiting";
    return "v2-queue-accent--calm";
  }

  function merchantPeV2QueueScanLine(mc) {
    var expl = resolveMerchantExplanation(mc);
    var raw =
      (expl && expl.status_label_ar) ||
      (mc && mc.customer_lifecycle_label_ar) ||
      merchantNextLineShort(mc);
    var page = byId("page-carts");
    if (
      page &&
      page.classList.contains("ma-carts--mi-v1") &&
      window.maIntelligenceCartsV1 &&
      typeof window.maIntelligenceCartsV1.merchantFacingText === "function"
    ) {
      return window.maIntelligenceCartsV1.merchantFacingText(raw);
    }
    return String(raw || "").trim();
  }

  function merchantPeV2ConvHeadline(expl, mc) {
    if (expl && expl.status_label_ar) return String(expl.status_label_ar).trim();
    return cartLifecycleStatusLabel(mc);
  }

  function merchantPeV2ConvStatus(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var reason = String(mc.merchant_reason_chip_label_ar || "").trim();
    var bits = [formatMerchantSar(v)];
    if (reason) bits.push(reason);
    return bits.join(" · ");
  }

  function merchantPeV2FlowStep(label, text, iconClass, iconContent) {
    return (
      '<div class="v2-flow-step">' +
      '<span class="v2-flow-icon ' +
      iconClass +
      '">' +
      iconContent +
      "</span>" +
      '<div class="v2-flow-content">' +
      '<p class="v2-flow-label">' +
      esc(label) +
      "</p>" +
      '<p class="v2-flow-text">' +
      esc(text) +
      "</p></div></div>"
    );
  }

  function merchantPeV2FlowConnector() {
    return '<div class="v2-flow-connector" aria-hidden="true"></div>';
  }

  function merchantPeV2FlowHtml(mc, expl) {
    if (!expl) return "";
    var parts = [];
    if (expl.what_happened_ar) {
      parts.push(
        merchantPeV2FlowStep(
          "ما حدث",
          expl.what_happened_ar,
          "v2-flow-icon--happened",
          "١"
        )
      );
    }
    if (expl.system_did_ar) {
      if (parts.length) parts.push(merchantPeV2FlowConnector());
      parts.push(
        merchantPeV2FlowStep(
          "CartFlow",
          expl.system_did_ar,
          "v2-flow-icon--did",
          "✓"
        )
      );
    }
    if (expl.what_next_ar) {
      if (parts.length) parts.push(merchantPeV2FlowConnector());
      parts.push(
        merchantPeV2FlowStep(
          !expl.action_required ? "الانتظار" : "التالي",
          expl.what_next_ar,
          "v2-flow-icon--next",
          "⏳"
        )
      );
    }
    if (expl.merchant_action_needed_ar) {
      if (parts.length) parts.push(merchantPeV2FlowConnector());
      parts.push(
        merchantPeV2FlowStep(
          "إجراءك",
          expl.merchant_action_needed_ar,
          "v2-flow-icon--you",
          "→"
        )
      );
    }
    if (!parts.length) return "";
    return (
      '<div class="v2-flow" aria-label="محادثة الاسترداد">' +
      parts.join("") +
      "</div>"
    );
  }

  function merchantPeV2PrimaryActionHtml(mc) {
    if (!mc) return "";
    var proj = cartDetailProjection(mc);
    var contact = proj && proj.contact_action;
    if (contact && contact.visible && contact.href) {
      return (
        '<a class="v2-btn" href="' +
        esc(contact.href) +
        '" target="_blank" rel="noopener noreferrer">' +
        esc(contact.label_ar || "تواصل مع العميل") +
        "</a>"
      );
    }
    var sa = proj && proj.suggested_action;
    if (sa && sa.visible && sa.label_ar) {
      if (contact && contact.visible && contact.href) {
        return (
          '<a class="v2-btn" href="' +
          esc(contact.href) +
          '" target="_blank" rel="noopener noreferrer">' +
          esc(contact.label_ar || sa.label_ar) +
          "</a>"
        );
      }
      return (
        '<span class="v2-btn v2-btn--label">' + esc(sa.label_ar) + "</span>"
      );
    }
    if (!proj && mc.merchant_intervention_executable) {
      var href = String(mc.merchant_intervention_contact_href || "").trim();
      if (href) {
        var lbl = String(mc.merchant_intervention_action_ar || "تواصل مع العميل").trim();
        return (
          '<a class="v2-btn" href="' +
          esc(href) +
          '" target="_blank" rel="noopener noreferrer">' +
          esc(lbl) +
          "</a>"
        );
      }
    }
    return "";
  }

  function merchantPeV2SecondaryActionsHtml(mc) {
    var proj = cartDetailProjection(mc);
    var lc = proj && proj.lifecycle_ui;
    var rk = lc && lc.recovery_key ? lc.recovery_key : String(mc.recovery_key || "").trim();
    if (!rk) return "";
    var h = "";
    if (lc) {
      if (lc.archive_visible) {
        h +=
          '<button type="button" class="v2-btn v2-btn--ghost" data-lc-archive data-recovery-key="' +
          esc(rk) +
          '">نقل للأرشيف</button>';
      }
      if (lc.reopen_visible) {
        h +=
          '<button type="button" class="v2-btn v2-btn--ghost" data-lc-reopen data-recovery-key="' +
          esc(rk) +
          '">إعادة فتح</button>';
      }
    } else {
      var act = String(mc.customer_lifecycle_dashboard_action || "").trim();
      if (act === "archive") {
        h +=
          '<button type="button" class="v2-btn v2-btn--ghost" data-lc-archive data-recovery-key="' +
          esc(rk) +
          '">نقل للأرشيف</button>';
      }
      if (act === "reopen") {
        h +=
          '<button type="button" class="v2-btn v2-btn--ghost" data-lc-reopen data-recovery-key="' +
          esc(rk) +
          '">إعادة فتح</button>';
      }
    }
    return h;
  }

  function merchantPeV2TimelineHtml(mc, expl) {
    var inner = "";
    inner += merchantProofSurfaceTimelineHtml(mc);
    inner += merchantFollowupClarityHtml(mc);
    if (expl && expl.followup_line_ar) {
      inner +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup">' +
        '<span class="ma-cart-timeline-event-kicker">المتابعة</span>' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(expl.followup_line_ar) +
        "</span></div>";
    }
    var prog = String(
      (cartDetailProjection(mc) && cartDetailProjection(mc).followup_progress_ar) ||
        mc.merchant_followup_progress_ar ||
        ""
    ).trim();
    if (prog) {
      inner +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup ma-cart-timeline-event--muted">' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(prog) +
        "</span></div>";
    }
    inner += merchantCustomerMovementTimelineHtml(mc);
    inner += merchantContinuationTimelineHtml(mc);
    if (!inner) return "";
    return (
      '<details class="ma-pe-v2-timeline-v2">' +
      '<summary class="ma-cart-timeline-summary">التفاصيل والسجل</summary>' +
      '<div class="ma-cart-timeline-body" role="list">' +
      inner +
      "</div></details>"
    );
  }

  function merchantPeV2ConversationHtml(mc, expl) {
    if (!mc) return "";
    if (isArchivedVisual(mc)) {
      return customerLifecycleArchivedCompactHtml(mc);
    }
    return (
      '<div class="ma-pe-v2-conversation v2-conversation" data-mxp="carts-pe-v2" aria-label="محادثة السلة">' +
      merchantCartAchievementHtml(mc) +
      '<p class="v2-conv-status">' +
      esc(merchantPeV2ConvStatus(mc)) +
      "</p>" +
      '<h2 class="v2-conv-headline">' +
      esc(merchantPeV2ConvHeadline(expl, mc)) +
      "</h2>" +
      merchantPeV2FlowHtml(mc, expl) +
      '<div class="v2-conv-footer">' +
      merchantPeV2TimelineHtml(mc, expl) +
      merchantPeV2PrimaryActionHtml(mc) +
      merchantPeV2SecondaryActionsHtml(mc) +
      "</div></div>"
    );
  }

  function merchantPeV2MobilePanelHtml(mc, expl) {
    if (!mc) return "";
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    return (
      '<p class="v2-action-eyebrow">المحددة · ' +
      formatMerchantSarHtml(v) +
      "</p>" +
      '<h2 class="v2-action-headline">' +
      esc(merchantPeV2ConvHeadline(expl, mc)) +
      "</h2>" +
      merchantPeV2PrimaryActionHtml(mc)
    );
  }

  function cartRowDataAttrs(mc) {
    var b = esc(mc.merchant_cart_bucket || "other");
    var primary = esc(mc.merchant_cart_primary_bucket || b);
    var tabsJson = "[]";
    try {
      tabsJson = esc(JSON.stringify(mc.merchant_cart_visible_tabs || []));
    } catch (eTabs) {
      tabsJson = "[]";
    }
    return {
      filter: b,
      primary: primary,
      tabsJson: tabsJson,
      completed: isCompletedDashboardRow(mc),
      archived: isArchivedVisual(mc),
      rk: esc(cartRecoveryKey(mc)),
    };
  }

  function cartQueueItemHtml(mc, selected) {
    var d = cartRowDataAttrs(mc);
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var accent = merchantPeV2QueueAccentClass(mc);
    var scan = merchantPeV2QueueScanLine(mc);
    var time = esc(mc.merchant_time_relative_ar || "—");
    return (
      '<button type="button" class="v2-queue-item' +
      (selected ? " is-selected" : "") +
      '" data-ma-filter="' +
      d.filter +
      '" data-ma-primary-bucket="' +
      d.primary +
      '" data-ma-visible-tabs="' +
      d.tabsJson +
      '" data-recovery-key="' +
      d.rk +
      '">' +
      '<span class="v2-queue-accent ' +
      accent +
      '"></span>' +
      '<div class="v2-queue-body">' +
      '<div class="v2-queue-amount">' +
      formatMerchantSar(v) +
      "</div>" +
      '<p class="v2-queue-scan">' +
      esc(scan) +
      "</p></div>" +
      '<span class="v2-queue-time">' +
      time +
      "</span></button>"
    );
  }

  function cartRowSyncTr(mc) {
    var d = cartRowDataAttrs(mc);
    return (
      '<tr data-ma-filter="' +
      d.filter +
      '" data-ma-primary-bucket="' +
      d.primary +
      '" data-ma-visible-tabs="' +
      d.tabsJson +
      '" data-recovery-key="' +
      d.rk +
      '"' +
      (d.completed ? ' data-ma-completed="1"' : "") +
      (d.archived ? ' class="ma-row-archived" data-ma-archived-visual="1"' : "") +
      ' style="display:none"><td colspan="6"></td></tr>'
    );
  }

  function cartRowTableDisplay(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var hasPh = !!mc.merchant_has_customer_phone;
    var ph = hasPh
      ? '<span class="ph-ok">✓</span>'
      : '<span class="ph-no">✗</span>';
    var d = cartRowDataAttrs(mc);
    var archived = d.archived;
    var statusLbl = cartLifecycleStatusLabel(mc);
    var nextLbl =
      mc.customer_lifecycle_label_ar ||
      merchantNextLineShort(mc) ||
      mc.merchant_next_action_ar ||
      "—";
    var urg =
      mc.merchant_next_action_urgent && !archived ? " urgent" : "";
    return (
      '<tr data-ma-filter="' +
      d.filter +
      '" data-ma-primary-bucket="' +
      d.primary +
      '" data-ma-visible-tabs="' +
      d.tabsJson +
      '" data-recovery-key="' +
      d.rk +
      '"' +
      (d.completed ? ' data-ma-completed="1"' : "") +
      (archived ? ' class="ma-row-archived" data-ma-archived-visual="1"' : "") +
      ">" +
      "<td><div class=\"camt\">" +
      formatMerchantSar(v) +
      '</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(cartLifecycleStatusClass(mc)) +
      '\"><span class="sd"></span>' +
      esc(statusLbl) +
      "</span></td>" +
      "<td>" +
      (archived ? "" : '<div class="next' + urg + '">' + esc(nextLbl) + "</div>") +
      "</td>" +
      '<td><div class="ctime">' +
      esc(mc.merchant_last_seen_display || "—") +
      "</div></td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function renderPeV2CartPanel(mc) {
    var panel = byId("ma-carts-panel-v2");
    var mobile = byId("ma-carts-mobile-panel-v2");
    if (!mc) {
      if (panel) {
        panel.innerHTML =
          '<p class="v2-whisper-text">اختر سلة من الطابور لعرض قصتها.</p>';
      }
      if (mobile) mobile.hidden = true;
      return;
    }
    var expl = resolveMerchantExplanation(mc);
    if (panel) {
      panel.innerHTML = merchantPeV2ConversationHtml(mc, expl);
      bindCustomerLifecycleActions(panel);
    }
    if (mobile) {
      mobile.hidden = false;
      mobile.innerHTML = merchantPeV2MobilePanelHtml(mc, expl);
      bindCustomerLifecycleActions(mobile);
    }
  }

  function selectPeV2Cart(rk) {
    peV2SelectedRecoveryKey = String(rk || "").trim();
    var scope = byId("ma-carts-groups-v2") || byId("ma-carts-queue-v2");
    if (scope) {
      scope.querySelectorAll(".v2-queue-item").forEach(function (btn) {
        btn.classList.toggle(
          "is-selected",
          btn.getAttribute("data-recovery-key") === peV2SelectedRecoveryKey
        );
      });
    }
    renderPeV2CartPanel(findCartByRecoveryKey(peV2SelectedRecoveryKey));
  }

  function bindPeV2CartsQueue(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll(".v2-queue-item").forEach(function (btn) {
      if (btn._peV2Bound) return;
      btn._peV2Bound = true;
      btn.addEventListener("click", function () {
        selectPeV2Cart(btn.getAttribute("data-recovery-key") || "");
      });
    });
  }

  function updatePeV2QueueSubtitle(rows) {
    var sub = byId("ma-carts-queue-sub");
    if (!sub) return;
    if (!rows.length) {
      sub.textContent = "لا توجد سلال نشطة حالياً";
      return;
    }
    var urgent = 0;
    rows.forEach(function (mc) {
      if (mc.merchant_next_action_urgent && !isArchivedVisual(mc)) urgent += 1;
    });
    sub.textContent =
      rows.length +
      " سلة" +
      (urgent ? " · " + urgent + " تحتاجك" : " · CartFlow يتابعها");
    var countEl = byId("ma-carts-group-count");
    if (countEl) countEl.textContent = String(rows.length);
  }

  function renderMiCartsV1Pending(message) {
    var root = byId("ma-carts-groups-v2");
    if (!root) return;
    root.innerHTML =
      '<p class="ma-mi-carts-pending v2-whisper-text">' +
      esc(message || "CartFlow يجهّز فهم المتجر…") +
      "</p>";
  }

  function miCartsWorkspaceKey(d, rows) {
    var mi = window.maIntelligenceCartsV1;
    if (mi && typeof mi.workspaceKey === "function") {
      return mi.workspaceKey(d, rows);
    }
    var store = d && d.merchant_intelligence_store_v1;
    var sig = ((store && store.groups) || [])
      .map(function (g) {
        return [
          String(g.group_id || ""),
          String(g.affected_carts != null ? g.affected_carts : ""),
          String(g.total_cart_value != null ? g.total_cart_value : ""),
          String(g.priority != null ? g.priority : ""),
        ].join(":");
      })
      .join("|");
    return sig + "::" + String(rows.length);
  }

  function updateMiCartsV1QueueSelection() {
    var root = byId("ma-carts-groups-v2");
    if (!root || !root.querySelector(".ma-mi-group")) return false;
    var mi = window.maIntelligenceCartsV1;
    if (mi && typeof mi.updateGroupSelection === "function") {
      mi.updateGroupSelection(root, peV2SelectedRecoveryKey);
      return true;
    }
    root.querySelectorAll(".v2-queue-item").forEach(function (btn) {
      btn.classList.toggle(
        "is-selected",
        btn.getAttribute("data-recovery-key") === peV2SelectedRecoveryKey
      );
    });
    return true;
  }

  function renderMiCartsV1Workspace(d, rows) {
    var mi = window.maIntelligenceCartsV1;
    var root = byId("ma-carts-groups-v2");
    if (!mi || !root) return false;
    var page = byId("page-carts");
    var filters = byId("ma-cart-filters");
    if (page) page.classList.add("ma-carts--mi-v1");
    if (filters) filters.hidden = true;
    if (!mi.hasRenderablePayload(d)) {
      lastMiCartsWorkspaceKey = "";
      renderMiCartsV1Pending("CartFlow يجهّز فهم المتجر…");
      return true;
    }
    var wsKey = miCartsWorkspaceKey(d, rows);
    if (wsKey === lastMiCartsWorkspaceKey && root.querySelector(".ma-mi-group")) {
      var sub = byId("ma-carts-queue-sub");
      if (sub && mi.workspaceSubtitleFromPayload) {
        sub.textContent = mi.workspaceSubtitleFromPayload(d, rows);
      }
      updateMiCartsV1QueueSelection();
      return true;
    }
    lastMiCartsWorkspaceKey = wsKey;
    var empty = byId("ma-carts-queue-empty");
    var deps = {
      esc: esc,
      cartRecoveryKey: cartRecoveryKey,
      primaryActionHtml: merchantPeV2PrimaryActionHtml,
      selectedKey: peV2SelectedRecoveryKey,
      emptyEl: empty,
      bindQueue: bindPeV2CartsQueue,
      onSelectCart: selectPeV2Cart,
      updateSubtitle: function (text) {
        var subEl = byId("ma-carts-queue-sub");
        if (subEl) subEl.textContent = text;
      },
    };
    if (mi.hasValueStories(d)) {
      mi.renderStories(root, d.merchant_value_stories_v1, rows, deps);
    } else {
      mi.renderGroups(root, d.merchant_intelligence_store_v1, rows, deps);
    }
    if (!miCartsDidInitialSelect) {
      miCartsDidInitialSelect = true;
      var firstRk = "";
      root.querySelectorAll("details.ma-mi-group .v2-queue-item").forEach(function (btn) {
        if (!firstRk && btn.style.display !== "none" && !btn.hidden) {
          firstRk = btn.getAttribute("data-recovery-key") || "";
        }
      });
      if (
        !peV2SelectedRecoveryKey ||
        !findCartByRecoveryKey(peV2SelectedRecoveryKey)
      ) {
        selectPeV2Cart(firstRk);
      } else {
        selectPeV2Cart(peV2SelectedRecoveryKey);
      }
    } else {
      updateMiCartsV1QueueSelection();
      if (peV2SelectedRecoveryKey) {
        renderPeV2CartPanel(findCartByRecoveryKey(peV2SelectedRecoveryKey));
      }
    }
    return true;
  }

  function renderPeV2CartsQueue(rows) {
    var queue = byId("ma-carts-queue-v2");
    if (!queue) return;
    var empty = byId("ma-carts-queue-empty");
    updatePeV2QueueSubtitle(rows);
    if (!rows.length) {
      queue.innerHTML = "";
      if (empty) empty.hidden = false;
      selectPeV2Cart("");
      return;
    }
    if (empty) empty.hidden = true;
    var sel = peV2SelectedRecoveryKey;
    var firstRk = "";
    queue.innerHTML = rows
      .map(function (mc) {
        var rk = cartRecoveryKey(mc);
        if (!firstRk) firstRk = rk;
        return cartQueueItemHtml(mc, sel && rk === sel);
      })
      .join("");
    bindPeV2CartsQueue(queue);
    if (!sel || !findCartByRecoveryKey(sel)) {
      selectPeV2Cart(firstRk);
    } else {
      selectPeV2Cart(sel);
    }
  }

  window.maPeV2OnFilterApplied = function () {
    if (byId("page-carts") && byId("page-carts").classList.contains("ma-carts--mi-v1")) {
      return;
    }
    var queue = byId("ma-carts-queue-v2") || byId("ma-carts-groups-v2");
    if (!queue) return;
    var firstRk = "";
    queue.querySelectorAll(".v2-queue-item").forEach(function (btn) {
      if (btn.style.display === "none" || btn.hidden) return;
      if (!firstRk) firstRk = btn.getAttribute("data-recovery-key") || "";
    });
    if (firstRk) {
      selectPeV2Cart(firstRk);
    } else {
      selectPeV2Cart("");
    }
  };

  function customerLifecycleArchivedCompactHtml(mc) {
    return (
      '<div class="ma-pe-v2-conversation v2-conversation ma-pe-v2-conversation--archived" data-mxp="carts-pe-v2" aria-label="سلة مؤرشفة">' +
      '<p class="v2-conv-status">مؤرشفة</p>' +
      '<h2 class="v2-conv-headline">تم إغلاق هذه الحالة</h2>' +
      '<div class="v2-flow">' +
      '<div class="v2-flow-step">' +
      '<span class="v2-flow-icon v2-flow-icon--happened">—</span>' +
      '<div class="v2-flow-content">' +
      '<p class="v2-flow-text">تم إغلاق هذه الحالة من العرض النشط. لن يرسل النظام متابعات أثناء الأرشفة.</p>' +
      "</div></div></div>" +
      '<div class="v2-conv-footer">' +
      merchantPeV2SecondaryActionsHtml(mc) +
      "</div></div>"
    );
  }

  function merchantFollowupClarityHtml(mc) {
    if (!mc) return "";
    var prog = String(mc.merchant_followup_progress_ar || "").trim();
    var seq = String(mc.merchant_followup_sequence_line_ar || "").trim();
    var nxt = String(mc.merchant_followup_next_line_ar || "").trim();
    if (!prog && !seq && !nxt) return "";
    var h = "";
    if (prog) {
      h +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup">' +
        '<span class="ma-cart-timeline-event-kicker">المتابعة</span>' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(prog) +
        "</span></div>";
    }
    if (seq) {
      h +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup ma-cart-timeline-event--muted">' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(seq) +
        "</span></div>";
    }
    if (nxt) {
      h +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup">' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(nxt) +
        "</span></div>";
    }
    return h;
  }

  function continuationDecisionExplanationHtml(mc) {
    var proj = cartDetailProjection(mc);
    var expl = proj ? String(proj.continuation_line_ar || "").trim() : "";
    if (!expl) {
      expl = String(
        (mc &&
          (mc.customer_lifecycle_continuation_explanation_ar ||
            mc.normal_recovery_continuation_explanation_ar)) ||
          ""
      ).trim();
    }
    if (!expl) return "";
    return (
      '<div class="recovery-truth-line recovery-truth-highlight customer-lifecycle-cont-expl">' +
      esc(expl) +
      "</div>"
    );
  }

  function customerLifecycleUnavailableHtml(mc) {
    return (
      '<div class="recovery-truth recovery-truth-compact customer-lifecycle-v1" aria-label="حالة دورة العميل">' +
      '<div class="recovery-truth-line"><strong>الحالة:</strong> ' +
      esc("— لا تتوفر حالة واضحة بعد —") +
      "</div></div>"
    );
  }

  function merchantCartAchievementHtml(mc) {
    var f = mc && mc.merchant_cart_fact_v1;
    if (!f || !f.kind || !f.label_ar) return "";
    return (
      '<div class="ma-cart-achievement-v1" aria-label="إنجاز">' +
      '<span class="ma-cart-achievement-icon" aria-hidden="true">✓</span>' +
      '<span class="ma-cart-achievement-label">' +
      esc(f.label_ar) +
      "</span></div>"
    );
  }

  function merchantRecoveryStoryBeatsHtml(mc, expl) {
    if (!expl) return "";
    var h =
      '<div class="ma-cart-recovery-story-v1" aria-label="قصة الاسترداد">';
    if (expl.status_label_ar) {
      h +=
        '<p class="ma-cart-story-headline">' +
        esc(expl.status_label_ar) +
        "</p>";
    }
    if (expl.what_happened_ar) {
      h +=
        '<div class="ma-cart-story-beat ma-cart-story-beat--what">' +
        '<span class="ma-cart-story-beat-label">ما حدث</span>' +
        '<p class="ma-cart-story-beat-text">' +
        esc(expl.what_happened_ar) +
        "</p></div>";
    }
    if (expl.system_did_ar) {
      h +=
        '<div class="ma-cart-story-beat ma-cart-story-beat--did">' +
        '<span class="ma-cart-story-beat-label">CartFlow</span>' +
        '<p class="ma-cart-story-beat-text">' +
        esc(expl.system_did_ar) +
        "</p></div>";
    }
    if (expl.what_next_ar) {
      var waitingBand = !expl.action_required;
      h +=
        '<div class="ma-cart-story-beat ma-cart-story-beat--next' +
        (waitingBand ? " ma-cart-waiting-band" : "") +
        '">' +
        '<span class="ma-cart-story-beat-label">' +
        (waitingBand ? "الانتظار" : "التالي") +
        "</span>" +
        '<p class="ma-cart-story-beat-text">' +
        esc(expl.what_next_ar) +
        "</p></div>";
    }
    if (expl.merchant_action_needed_ar) {
      h +=
        '<div class="ma-cart-story-beat ma-cart-story-beat--action' +
        (expl.action_required ? " ma-cart-story-beat--action-required" : "") +
        '">' +
        '<span class="ma-cart-story-beat-label">إجراءك</span>' +
        '<p class="ma-cart-story-beat-text">' +
        esc(expl.merchant_action_needed_ar) +
        "</p></div>";
    }
    return h + "</div>";
  }

  function merchantSuggestedActionPrimaryHtml(mc) {
    if (!mc) return "";
    var proj = cartDetailProjection(mc);
    var sa = proj && proj.suggested_action;
    if (sa && sa.visible && sa.label_ar) {
      var label = sa.label_ar;
      var contact = proj && proj.contact_action;
      if (contact && contact.visible && contact.href) {
        var useLabel = contact.label_ar || label;
        return (
          '<div class="ma-cart-suggested-action-v1">' +
          '<a class="ma-cart-action-primary" href="' +
          esc(contact.href) +
          '" target="_blank" rel="noopener noreferrer">' +
          esc(useLabel) +
          "</a></div>"
        );
      }
      return (
        '<div class="ma-cart-suggested-action-v1">' +
        '<span class="ma-cart-action-primary ma-cart-action-primary--label">' +
        esc(label) +
        "</span></div>"
      );
    }
    if (!proj && mc.merchant_intervention_executable) {
      var href = String(mc.merchant_intervention_contact_href || "").trim();
      if (href) {
        var lbl = String(mc.merchant_intervention_action_ar || "فتح واتساب").trim();
        return (
          '<div class="ma-cart-suggested-action-v1">' +
          '<a class="ma-cart-action-primary" href="' +
          esc(href) +
          '" target="_blank" rel="noopener noreferrer">' +
          esc(lbl) +
          "</a></div>"
        );
      }
    }
    return "";
  }

  function merchantCartSecondaryLifecycleHtml(mc) {
    var proj = cartDetailProjection(mc);
    var lc = proj && proj.lifecycle_ui;
    var rk = lc && lc.recovery_key ? lc.recovery_key : String(mc.recovery_key || "").trim();
    if (!rk) return "";
    var h = "";
    if (lc) {
      if (lc.archive_visible) {
        h +=
          '<button type="button" class="ma-cart-action-secondary" data-lc-archive data-recovery-key="' +
          esc(rk) +
          '">نقل للأرشيف</button>';
      }
      if (lc.reopen_visible) {
        h +=
          '<button type="button" class="ma-cart-action-secondary" data-lc-reopen data-recovery-key="' +
          esc(rk) +
          '">إعادة فتح</button>';
      }
    } else {
      var act = String(mc.customer_lifecycle_dashboard_action || "").trim();
      if (act === "archive") {
        h +=
          '<button type="button" class="ma-cart-action-secondary" data-lc-archive data-recovery-key="' +
          esc(rk) +
          '">نقل للأرشيف</button>';
      }
      if (act === "reopen") {
        h +=
          '<button type="button" class="ma-cart-action-secondary" data-lc-reopen data-recovery-key="' +
          esc(rk) +
          '">إعادة فتح</button>';
      }
    }
    if (!h) return "";
    return '<div class="ma-cart-secondary-actions">' + h + "</div>";
  }

  function merchantProofSurfaceTimelineHtml(mc) {
    var ps = mc && mc.merchant_proof_surface_v1;
    if (!ps || ps.version !== "v1") return "";
    var steps = ps.recovery_steps || [];
    var h = "";
    if (ps.why_we_know_ar) {
      h +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--proof">' +
        '<span class="ma-cart-timeline-event-kicker">لماذا نعرف</span>' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(ps.why_we_know_ar) +
        "</span></div>";
    }
    for (var i = steps.length - 1; i >= 0; i--) {
      var st = steps[i];
      if (!st || !st.label_ar) continue;
      var stLabel =
        PROOF_STEP_STATE_AR[String(st.state || "").trim()] || st.state || "";
      h +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--step" role="listitem">' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(st.label_ar) +
        "</span>" +
        '<span class="ma-cart-timeline-event-meta">' +
        esc(stLabel);
      if (st.note_ar) {
        h += " · " + esc(st.note_ar);
      }
      h += "</span></div>";
    }
    var conf = ps.confidence_ar || ps.confidence || "";
    var ev = ps.evidence_label_ar || ps.evidence_source_ar || "";
    if (conf || ev) {
      h +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--meta ma-cart-timeline-event--muted">';
      if (conf) {
        h +=
          '<span class="ma-cart-timeline-event-meta">الثقة: ' + esc(conf) + "</span>";
      }
      if (ev) {
        h +=
          (conf ? " · " : "") +
          '<span class="ma-cart-timeline-event-meta">المصدر: ' +
          esc(ev) +
          "</span>";
      }
      h += "</div>";
    }
    return h;
  }

  function merchantCustomerMovementTimelineHtml(mc) {
    if (!mc || !mc.customer_movement_line_ar) return "";
    return (
      '<div class="ma-cart-timeline-event ma-cart-timeline-event--movement">' +
      '<span class="ma-cart-timeline-event-kicker">' +
      esc(mc.customer_movement_heading_ar || "حركة العميل") +
      "</span>" +
      '<span class="ma-cart-timeline-event-label">' +
      esc(mc.customer_movement_line_ar) +
      "</span></div>"
    );
  }

  function merchantContinuationTimelineHtml(mc) {
    var proj = cartDetailProjection(mc);
    var expl = proj ? String(proj.continuation_line_ar || "").trim() : "";
    if (!expl) {
      expl = String(
        (mc &&
          (mc.customer_lifecycle_continuation_explanation_ar ||
            mc.normal_recovery_continuation_explanation_ar)) ||
          ""
      ).trim();
    }
    if (!expl) return "";
    return (
      '<div class="ma-cart-timeline-event ma-cart-timeline-event--continuation">' +
      '<span class="ma-cart-timeline-event-label">' +
      esc(expl) +
      "</span></div>"
    );
  }

  function merchantCartTimelineHtml(mc, expl) {
    var inner = "";
    inner += merchantProofSurfaceTimelineHtml(mc);
    inner += merchantFollowupClarityHtml(mc);
    if (expl && expl.followup_line_ar) {
      inner +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup">' +
        '<span class="ma-cart-timeline-event-kicker">المتابعة</span>' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(expl.followup_line_ar) +
        "</span></div>";
    }
    var prog = String(
      (cartDetailProjection(mc) && cartDetailProjection(mc).followup_progress_ar) ||
        mc.merchant_followup_progress_ar ||
        ""
    ).trim();
    if (prog) {
      inner +=
        '<div class="ma-cart-timeline-event ma-cart-timeline-event--followup ma-cart-timeline-event--muted">' +
        '<span class="ma-cart-timeline-event-label">' +
        esc(prog) +
        "</span></div>";
    }
    inner += merchantCustomerMovementTimelineHtml(mc);
    inner += merchantContinuationTimelineHtml(mc);
    if (!inner) return "";
    return (
      '<details class="ma-cart-timeline-v1">' +
      '<summary class="ma-cart-timeline-summary">التفاصيل</summary>' +
      '<div class="ma-cart-timeline-body" role="list">' +
      inner +
      "</div></details>"
    );
  }

  function merchantCartWorkspaceFromParts(mc, expl) {
    return merchantPeV2ConversationHtml(mc, expl);
  }

  function merchantCartWorkspaceHtml(mc) {
    return merchantExplanationHtml(mc);
  }

  function merchantExplanationProjectionHtml(mc, expl) {
    return merchantCartWorkspaceFromParts(mc, expl);
  }

  function merchantExplanationHtml(mc) {
    if (!mc) {
      return customerLifecycleUnavailableHtml(mc);
    }
    if (isArchivedVisual(mc)) {
      return customerLifecycleArchivedCompactHtml(mc);
    }
    var proj = cartDetailProjection(mc);
    if (proj && proj.explanation) {
      return merchantExplanationProjectionHtml(mc, proj.explanation);
    }
    var ex = mc.merchant_explanation_v1;
    if (!ex || ex.version !== "v1") {
      return customerLifecycleExplanationLegacyHtml(mc);
    }
    return merchantExplanationProjectionHtml(mc, {
      status_label_ar: ex.status_label_ar,
      what_happened_ar: ex.what_happened_ar,
      system_did_ar: ex.system_did_ar,
      what_next_ar: ex.what_next_ar,
      followup_line_ar: ex.followup_line_ar,
      merchant_action_needed_ar: ex.merchant_action_needed_ar,
      action_required: ex.action_required,
    });
  }

  function customerMovementHtml(mc) {
    if (!mc || !mc.customer_movement_line_ar) return "";
    return (
      '<div class="recovery-truth-line ma-customer-movement-v1">' +
      "<strong>" +
      esc(mc.customer_movement_heading_ar || "حركة العميل:") +
      "</strong> " +
      esc(mc.customer_movement_line_ar) +
      "</div>"
    );
  }

  function merchantCartFactHtml(mc) {
    return merchantCartAchievementHtml(mc);
  }

  var PROOF_STEP_STATE_AR = {
    done: "تم",
    active: "جاري",
    pending: "بانتظار",
    skipped: "—",
    unknown: "غير معروف",
    failed: "تعذّر",
  };

  function merchantProofSurfaceHtml(mc) {
    var ps = mc && mc.merchant_proof_surface_v1;
    if (!ps || ps.version !== "v1") return "";
    var steps = ps.recovery_steps || [];
    var h =
      '<div class="recovery-truth ma-proof-surface-v1" aria-label="دليل CartFlow">' +
      '<div class="recovery-truth-line ma-proof-headline">' +
      "<strong>ملخص CartFlow:</strong> " +
      esc(ps.why_we_know_ar || "—") +
      "</div>" +
      '<div class="recovery-truth-line ma-proof-meta">' +
      "<strong>الثقة:</strong> " +
      esc(ps.confidence_ar || ps.confidence || "غير معروف") +
      " · <strong>المصدر:</strong> " +
      esc(ps.evidence_label_ar || ps.evidence_source_ar || "—") +
      "</div>";
    if (steps.length) {
      h += '<div class="ma-proof-steps" role="list" aria-label="مسار الاسترجاع">';
      for (var i = 0; i < steps.length; i++) {
        var st = steps[i];
        if (!st || !st.label_ar) continue;
        var stLabel = PROOF_STEP_STATE_AR[String(st.state || "").trim()] || st.state || "";
        h +=
          '<div class="ma-proof-step recovery-truth-line" role="listitem">' +
          "<strong>" +
          esc(st.label_ar) +
          ":</strong> " +
          esc(stLabel);
        if (st.note_ar) {
          h += ' <span class="recovery-truth-muted">(' + esc(st.note_ar) + ")</span>";
        }
        h += "</div>";
      }
      h += "</div>";
    }
    return h + "</div>";
  }

  function customerLifecycleExplanationLegacyHtml(mc) {
    if (!mc || !mc.customer_lifecycle_state) {
      return customerLifecycleUnavailableHtml(mc);
    }
    if (isArchivedVisual(mc)) {
      return customerLifecycleArchivedCompactHtml(mc);
    }
    return merchantCartWorkspaceFromParts(mc, {
      status_label_ar: mc.customer_lifecycle_label_ar || "—",
      what_happened_ar: mc.customer_lifecycle_what_happened_ar,
      system_did_ar: mc.customer_lifecycle_system_did_ar,
      what_next_ar: mc.customer_lifecycle_what_next_ar,
      followup_line_ar: mc.customer_lifecycle_next_followup_line_ar,
      merchant_action_needed_ar: mc.customer_lifecycle_merchant_needed_ar,
      action_required: false,
    });
  }

  function customerLifecycleExplanationHtml(mc) {
    return merchantExplanationHtml(mc);
  }

  function findCartRowContext(rk) {
    var key = String(rk || "").trim();
    if (!key) return null;
    var pools = [lastNormalCartsPageRows, lastArchivedCartsPageRows];
    for (var p = 0; p < pools.length; p++) {
      for (var i = 0; i < pools[p].length; i++) {
        var mc = pools[p][i];
        if (String(mc.recovery_key || "").trim() === key) return mc;
        var sid = String(mc.session_id || "").trim();
        if (sid && key.indexOf(":") >= 0) {
          var tail = key.split(":").slice(1).join(":");
          if (tail === sid) return mc;
        }
        var rid = mc.merchant_case_row_id || mc.id;
        if (rid && key === String(rid)) return mc;
      }
    }
    return null;
  }

  function lifecycleActionPayload(mc, rk) {
    var slug = mc && mc.store_slug ? String(mc.store_slug).trim() : "";
    if (!slug && rk.indexOf(":") >= 0) slug = rk.split(":")[0].trim();
    var rowId = mc && (mc.merchant_case_row_id || mc.id);
    return {
      recovery_key: rk,
      store_slug: slug,
      abandoned_cart_id: rowId != null ? rowId : null,
      session_id: mc && mc.session_id ? String(mc.session_id).trim() : "",
      cart_id: mc && mc.cart_id ? String(mc.cart_id).trim() : "",
    };
  }

  function rowMatchesLifecycleKey(mc, rk, rowId) {
    if (!mc) return false;
    var key = String(rk || "").trim();
    if (key && String(mc.recovery_key || "").trim() === key) return true;
    if (rowId != null && String(mc.merchant_case_row_id || mc.id) === String(rowId)) {
      return true;
    }
    return false;
  }

  function applyLifecyclePayloadToRow(mc, lifecycle) {
    if (!mc || !lifecycle || typeof lifecycle !== "object") return;
    Object.keys(lifecycle).forEach(function (k) {
      if (lifecycle[k] !== undefined && lifecycle[k] !== null) {
        mc[k] = lifecycle[k];
      }
    });
    if (lifecycle.merchant_status_label_ar) {
      mc.merchant_status_label_ar = lifecycle.merchant_status_label_ar;
    }
    if (lifecycle.merchant_status_row_class) {
      mc.merchant_status_row_class = lifecycle.merchant_status_row_class;
    }
    mc.merchant_next_action_urgent = false;
  }

  function syncReopenedCartRowMemory(rk, lifecycle) {
    var key = String(rk || "").trim();
    if (!key) return;
    var ctx = findCartRowContext(key);
    var rowId = ctx && (ctx.merchant_case_row_id || ctx.id);
    lastArchivedCartsPageRows = lastArchivedCartsPageRows.filter(function (mc) {
      return !rowMatchesLifecycleKey(mc, key, rowId);
    });
    var activeRow = null;
    lastNormalCartsPageRows.forEach(function (mc) {
      if (rowMatchesLifecycleKey(mc, key, rowId)) activeRow = mc;
    });
    if (!activeRow) {
      activeRow = {};
      if (ctx && typeof ctx === "object") {
        Object.keys(ctx).forEach(function (k) {
          activeRow[k] = ctx[k];
        });
      } else {
        activeRow.recovery_key = key;
      }
      lastNormalCartsPageRows.push(activeRow);
    }
    if (lifecycle && typeof lifecycle === "object") {
      applyLifecyclePayloadToRow(activeRow, lifecycle);
    } else {
      activeRow.customer_lifecycle_is_archived_visual = false;
    }
    lastNormalCartsPageRows.forEach(function (mc) {
      if (mc === activeRow) return;
      if (!rowMatchesLifecycleKey(mc, key, rowId)) return;
      if (lifecycle && typeof lifecycle === "object") {
        applyLifecyclePayloadToRow(mc, lifecycle);
      } else {
        mc.customer_lifecycle_is_archived_visual = false;
      }
    });
  }

  function patchCartRowArchivedVisual(rk, archived, lifecycle) {
    var key = String(rk || "").trim();
    if (!key) return;
    if (!archived) {
      syncReopenedCartRowMemory(key, lifecycle);
      return;
    }
    var ctx = findCartRowContext(key);
    var rowId = ctx && (ctx.merchant_case_row_id || ctx.id);
    lastNormalCartsPageRows.forEach(function (mc) {
      if (!rowMatchesLifecycleKey(mc, key, rowId)) return;
      mc.customer_lifecycle_is_archived_visual = true;
      mc.customer_lifecycle_state = "archived";
      mc.customer_lifecycle_label_ar = "مؤرشفة";
      mc.customer_lifecycle_dashboard_action = "reopen";
      mc.customer_lifecycle_status_row_class = "s-archived";
      mc.merchant_status_row_class = "s-archived";
      mc.merchant_status_label_ar = "مؤرشفة";
      mc.merchant_next_action_urgent = false;
    });
  }

  function refreshCompletedCartsTableAfterLifecycleChange() {
    if (typeof window.maRefreshCompletedCartsTable === "function") {
      window.maRefreshCompletedCartsTable();
      return;
    }
    applyCompletedCartsTable(lastNormalCartsPageRows, lastArchivedCartsPageRows);
  }

  function rerenderAllCartsTable() {
    var allb = byId("ma-tbody-all-carts");
    if (!allb) return;
    var sorted = sortCartsArchivedLast(lastNormalCartsPageRows);
    allb.innerHTML = sorted.map(cartRowFull).join("");
    bindCustomerLifecycleActions(allb);
    if (
      !renderMiCartsV1Workspace(lastMerchantIntelligencePayload, sorted)
    ) {
      renderPeV2CartsQueue(sorted);
    }
  }

  function rerenderHomeCartsTable() {
    var home = byId("ma-tbody-home-carts");
    if (!home || !lastNormalCartsPageRows.length) return;
    home.innerHTML = lastNormalCartsPageRows.map(cartRowHome).join("");
    bindCustomerLifecycleActions(home);
  }

  function lifecycleTruthHtml(mc) {
    return customerLifecycleExplanationHtml(mc);
  }

  function bindCustomerLifecycleActions(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll("[data-lc-archive]").forEach(function (btn) {
      if (btn._lcBound) return;
      btn._lcBound = true;
      btn.addEventListener("click", function () {
        var rk = btn.getAttribute("data-recovery-key") || "";
        if (!rk) return;
        btn.disabled = true;
        var mc = findCartRowContext(rk);
        var payload = lifecycleActionPayload(mc, rk);
        fetch("/api/dashboard/cart-lifecycle/archive", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            btn.disabled = false;
            if (d && d.ok) {
              patchCartRowArchivedVisual(rk, true);
              rerenderAllCartsTable();
              rerenderHomeCartsTable();
              fetchNormalCarts("lifecycle_archive").then(function (payload) {
                if (payload && typeof window.goToCartTab === "function") {
                  window.goToCartTab("completed");
                }
              });
            } else {
              console.error("[LC ARCHIVE FAILED]", d);
            }
          })
          .catch(function (err) {
            btn.disabled = false;
            console.error("[LC ARCHIVE FAILED]", err);
          });
      });
    });
    root.querySelectorAll("[data-lc-reopen]").forEach(function (btn) {
      if (btn._lcBound) return;
      btn._lcBound = true;
      btn.addEventListener("click", function () {
        var rk = btn.getAttribute("data-recovery-key") || "";
        if (!rk) return;
        btn.disabled = true;
        var mc = findCartRowContext(rk);
        var payload = lifecycleActionPayload(mc, rk);
        fetch("/api/dashboard/cart-lifecycle/reopen", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            btn.disabled = false;
            if (d && d.ok) {
              syncReopenedCartRowMemory(rk, d.lifecycle || null);
              rerenderAllCartsTable();
              rerenderHomeCartsTable();
              refreshCompletedCartsTableAfterLifecycleChange();
              fetchNormalCarts("lifecycle_reopen").then(function (payload) {
                if (payload && typeof window.goToCartTab === "function") {
                  window.goToCartTab("all");
                }
              });
            } else {
              console.error("[LC REOPEN FAILED]", d);
            }
          })
          .catch(function (err) {
            btn.disabled = false;
            console.error("[LC REOPEN FAILED]", err);
          });
      });
    });
  }

  function cartRowHome(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var phoneOk =
      (mc.merchant_phone_line_ar || "").indexOf("متوفر") >= 0;
    var ph = phoneOk
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    var urg = mc.merchant_next_action_urgent ? " urgent" : "";
    return (
      "<tr>" +
      "<td><div class=\"camt\">" +
      formatMerchantSar(v) +
      '</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(cartLifecycleStatusClass(mc)) +
      '\"><span class="sd"></span>' +
      esc(cartLifecycleStatusLabel(mc)) +
      "</span></td>" +
      "<td>" +
      (isArchivedVisual(mc)
        ? ""
        : '<div class="next' +
          urg +
          '">' +
          esc(merchantNextLineShort(mc) || mc.merchant_next_action_ar || "—") +
          "</div>") +
      merchantCartWorkspaceHtml(mc) +
      "</td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function cartRowFull(mc) {
    if (byId("ma-carts-groups-v2") || byId("ma-carts-queue-v2")) {
      return cartRowSyncTr(mc);
    }
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var hasPh = !!mc.merchant_has_customer_phone;
    var ph = hasPh
      ? '<span class="ph-ok">✓</span>'
      : '<span class="ph-no">✗</span>';
    var b = esc(mc.merchant_cart_bucket || "other");
    var primary = esc(mc.merchant_cart_primary_bucket || b);
    var tabsJson = "[]";
    try {
      tabsJson = esc(JSON.stringify(mc.merchant_cart_visible_tabs || []));
    } catch (eTabs) {
      tabsJson = "[]";
    }
    var urg =
      mc.merchant_next_action_urgent && !isArchivedVisual(mc) ? " urgent" : "";
    var archived = isArchivedVisual(mc);
    var statusLbl = cartLifecycleStatusLabel(mc);
    var nextLbl =
      mc.customer_lifecycle_label_ar ||
      merchantNextLineShort(mc) ||
      mc.merchant_next_action_ar ||
      "—";
    var completedRow = isCompletedDashboardRow(mc);
    return (
      '<tr data-ma-filter="' +
      b +
      '" data-ma-primary-bucket="' +
      primary +
      '" data-ma-visible-tabs="' +
      tabsJson +
      '"' +
      (completedRow ? ' data-ma-completed="1"' : "") +
      (archived ? ' class="ma-row-archived" data-ma-archived-visual="1"' : "") +
      ">" +
      "<td><div class=\"camt\">" +
      formatMerchantSar(v) +
      '</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(cartLifecycleStatusClass(mc)) +
      '\"><span class="sd"></span>' +
      esc(statusLbl) +
      "</span></td>" +
      "<td>" +
      (archived
        ? ""
        : '<div class="next' + urg + '">' + esc(nextLbl) + "</div>") +
      merchantCartWorkspaceHtml(mc) +
      "</td>" +
      '<td><div class="ctime">' +
      esc(mc.merchant_last_seen_display || "—") +
      "</div></td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function normalCartsLoadingRowHtml(message) {
    return (
      '<tr class="ma-dash-loading-row" data-ma-carts-loading="1">' +
      '<td colspan="6" style="text-align:center;padding:24px;color:var(--muted);">' +
      esc(message || "جاري تحميل السلال…") +
      "</td></tr>"
    );
  }

  function normalCartsHomeLoadingRowHtml(message) {
    return (
      '<tr class="ma-dash-loading-row" data-ma-carts-loading="1">' +
      '<td colspan="5" style="text-align:center;padding:24px;color:var(--muted);">' +
      esc(message || "جاري تحميل السلال…") +
      "</td></tr>"
    );
  }

  function normalCartsIsDegraded(d) {
    if (!d) return true;
    if (d.dashboard_partial || d.dashboard_timeout) return true;
    if (d.snapshot_degraded || d.snapshot_stale) return true;
    var snap = d._snapshot;
    if (snap && (snap.degraded || snap.stale)) return true;
    var perf = d._perf;
    if (perf && (perf.partial || perf.degraded)) return true;
    return false;
  }

  function normalCartsDegradedRetryStage(d) {
    if (!d) return "partial";
    return (
      String(
        d.dashboard_timeout_stage ||
          d.snapshot_reason ||
          (d._perf && d._perf.timeout_stage) ||
          "partial"
      ).trim() || "partial"
    );
  }

  function normalCartsPayloadRows(d) {
    return (d && d.merchant_carts_page_rows) || [];
  }

  function showNormalCartsLoadingState(message) {
    if (normalCartsHasRenderedRows && lastNormalCartsPageRows.length) return;
    var allb = byId("ma-tbody-all-carts");
    if (allb && !allb.querySelector("tr[data-ma-filter]")) {
      allb.innerHTML = normalCartsLoadingRowHtml(message);
    }
    var home = byId("ma-tbody-home-carts");
    if (home && !home.querySelector("tr[data-ma-filter]")) {
      home.innerHTML = normalCartsHomeLoadingRowHtml(message);
    }
  }

  function scheduleNormalCartsRetry(label) {
    if (window.__maNormalCartsPartialRetryPending) return;
    window.__maNormalCartsPartialRetryPending = true;
    logClientRefresh("normal_carts_retry_scheduled", { label: label || "partial" });
    window.setTimeout(function () {
      window.__maNormalCartsPartialRetryPending = false;
      fetchNormalCarts("normal_carts_retry_" + (label || "partial"));
    }, 1200);
  }

  function renderNormalCartsTables(d) {
    var pageRows = normalCartsPayloadRows(d);
    var confirmedEmpty = !!(d && d.__ma_confirmed_empty);
    if (!pageRows.length && !confirmedEmpty) {
      showNormalCartsLoadingState("جاري تحميل السلال…");
      return;
    }
    lastNormalCartsPageRows = pageRows;
    lastArchivedCartsPageRows = (d && d.merchant_archived_carts_page_rows) || [];
    lastMerchantIntelligencePayload = d;
    window.__maNormalCartsPageRows = lastNormalCartsPageRows;
    if (pageRows.length) {
      normalCartsHasRenderedRows = true;
    }
    var home = byId("ma-tbody-home-carts");
    if (home) {
      var tr = (d && d.merchant_table_rows) || [];
      if (!tr.length && !pageRows.length) {
        home.innerHTML =
          '<tr><td colspan="5" class="empty-text" style="text-align:center;padding:24px;color:var(--muted);">لا توجد سلال ضمن النشاط الحالي</td></tr>';
      } else if (tr.length) {
        home.innerHTML = tr.map(cartRowHome).join("");
      } else {
        home.innerHTML = pageRows.slice(0, 8).map(cartRowHome).join("");
      }
      bindCustomerLifecycleActions(home);
    }
    var allb = byId("ma-tbody-all-carts");
    if (allb) {
      var pr = sortCartsArchivedLast(lastNormalCartsPageRows);
      if (!pr.length) {
        allb.innerHTML =
          '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">🛒</div><div class="empty-text">لا توجد سلال متروكة مسجّلة حالياً ضمن نطاق متجرك</div></td></tr>';
      } else {
        allb.innerHTML = pr.map(cartRowFull).join("");
      }
      bindCustomerLifecycleActions(allb);
    }
    var sortedRows = sortCartsArchivedLast(lastNormalCartsPageRows);
    if (!renderMiCartsV1Workspace(d, sortedRows)) {
      renderPeV2CartsQueue(sortedRows);
    }
    applyCompletedCartsTable(lastNormalCartsPageRows, lastArchivedCartsPageRows);
    var storeFc = resolveMerchantStoreCartCounts(d);
    var pageFc =
      (d && d.merchant_visible_page_counts) ||
      deriveVisiblePageCounts(pageRows, lastArchivedCartsPageRows);
    var fc = effectiveFilterCounts(
      (d && d.merchant_cart_filter_counts) || {},
      pageRows,
      d
    );
    lastNormalCartsFilterCounts = fc;
    applyNoPhoneFilterVisibility(fc);
    function sf(k, id) {
      var el = byId(id);
      if (el) el.textContent = String(fc[k] != null ? fc[k] : 0);
    }
    sf("all", "ma-filt-all");
    sf("recovered", "ma-filt-recovered");
    sf("sent", "ma-filt-sent");
    sf("attention", "ma-filt-attention");
    sf("nophone", "ma-filt-nophone");
    try {
      var derivedFc = deriveFilterCountsFromRows(pageRows);
      var completedN = completedCartsFromRows(
        pageRows,
        lastArchivedCartsPageRows || []
      ).length;
      console.log(
        "[COUNTER TOTALS AUDIT] source=" +
          normalCartsPayloadSource(d) +
          " scope=store_total active_total=" +
          String(fc.all != null ? fc.all : 0) +
          " waiting_total=" +
          String(
            d.merchant_nav_badge_abandoned != null
              ? d.merchant_nav_badge_abandoned
              : fc.waiting != null
                ? fc.waiting
                : 0
          ) +
          " sent_total=" +
          String(fc.sent != null ? fc.sent : 0) +
          " engaged_total=" +
          String(fc.attention != null ? fc.attention : 0) +
          " completed_total=" +
          String(fc.recovered != null ? fc.recovered : 0) +
          " archived_total=" +
          String(
            (d.merchant_store_cart_counts &&
              d.merchant_store_cart_counts.archived_total) ||
              (d.merchant_archived_cart_count != null
                ? d.merchant_archived_cart_count
                : 0)
          ) +
          " snapshot_stale=" +
          String(
            !!(d.merchant_counter_health &&
              d.merchant_counter_health.counter_snapshot_stale) ||
              !!(d._snapshot && d._snapshot.stale)
          )
      );
      console.log(
        "[COUNTER PAGE AUDIT] visible_page_rows=" +
          String(pageRows.length) +
          " page_waiting=" +
          String(pageFc.waiting != null ? pageFc.waiting : 0) +
          " page_sent=" +
          String(pageFc.sent != null ? pageFc.sent : 0) +
          " page_engaged=" +
          String(pageFc.attention != null ? pageFc.attention : 0) +
          " page_completed=" +
          String(completedN) +
          " page_all=" +
          String(pageFc.all != null ? pageFc.all : 0)
      );
      console.log(
        "[ROW AUDIT] active_rows=" +
          String(pageRows.length) +
          " archived_rows=" +
          String((lastArchivedCartsPageRows || []).length) +
          " source=" +
          normalCartsPayloadSource(d) +
          " store_fc=" +
          JSON.stringify(fc) +
          " page_fc=" +
          JSON.stringify(pageFc) +
          " derived_fc=" +
          JSON.stringify(derivedFc)
      );
    } catch (_auditLogErr) {
      /* ignore */
    }
    try {
      logClientRefresh("normal_carts_render", {
        rows_count: pageRows.length,
        degraded: normalCartsIsDegraded(d),
        source: normalCartsPayloadSource(d),
        filter_all: fc.all != null ? fc.all : 0,
      });
    } catch (_renderLogErr) {
      /* ignore */
    }
    if (d && d.merchant_nav_badge_abandoned != null) {
      setNavBadge("ma-nav-badge-abandoned", d.merchant_nav_badge_abandoned);
    } else if (fc.waiting != null) {
      setNavBadge("ma-nav-badge-abandoned", fc.waiting);
    }
    if (window.merchantAppReinitCartFilters) {
      window.merchantAppReinitCartFilters();
    }
    reapplyNormalCartFilterAfterRender();
  }

  function reapplyNormalCartFilterAfterRender() {
    try {
      var hashRaw = (location.hash || "").split("?")[0].toLowerCase();
      if (
        hashRaw === "#completed" &&
        typeof window.maRefreshCompletedCartsTable === "function"
      ) {
        window.maRefreshCompletedCartsTable();
        return;
      }
      if (typeof window.applyCartTabFilters !== "function") {
        return;
      }
      var before =
        typeof window.getEffectiveNormalCartFilter === "function"
          ? window.getEffectiveNormalCartFilter()
          : typeof window.getCurrentNormalCartFilter === "function"
            ? window.getCurrentNormalCartFilter()
            : null;
      var urlTab =
        typeof window.getUrlCartTabFromHash === "function"
          ? window.getUrlCartTabFromHash()
          : (function () {
              var hashQs = (location.hash || "").split("?")[1] || "";
              return (new URLSearchParams(hashQs).get("tab") || "").trim();
            })();
      var urlApplies =
        typeof window.urlCartTabShouldApplyToFilterBar === "function"
          ? window.urlCartTabShouldApplyToFilterBar(urlTab)
          : !!(urlTab && urlTab.toLowerCase() !== "all");
      if (urlApplies) {
        window.applyCartTabFilters(urlTab, { persist: true, source: "url_reapply" });
      } else if (before) {
        window.applyCartTabFilters(before, { persist: false, source: "persisted_reapply" });
      } else {
        window.applyCartTabFilters("all", { persist: true, source: "default_reapply" });
      }
      var after =
        typeof window.getCurrentNormalCartFilter === "function"
          ? window.getCurrentNormalCartFilter()
          : null;
      logClientRefresh("cart_filter_reapply", {
        selected_filter_before: before,
        selected_filter_after: after,
        url_tab: urlTab || null,
      });
    } catch (eHash) {
      /* ignore */
    }
  }

  function applyNormalCarts(d, fetchGen) {
    if (!d || !d.ok) return;
    if (fetchGen != null && fetchGen < normalCartsAppliedGen) {
      logClientRefresh("normal_carts_stale_skip", {
        fetchGen: fetchGen,
        appliedGen: normalCartsAppliedGen,
        inflightGen: normalCartsFetchGen,
      });
      return;
    }
    var pageRows = normalCartsPayloadRows(d);
    var degraded = normalCartsIsDegraded(d);
    var partialEmpty = degraded && !pageRows.length;

    if (partialEmpty) {
      logClientRefresh("normal_carts_partial_empty", {
        stage: normalCartsDegradedRetryStage(d),
        hadRows: lastNormalCartsPageRows.length,
        snapshot_degraded: !!d.snapshot_degraded,
      });
      if (lastNormalCartsPageRows.length) {
        rerenderCartsFromMemory("partial_keep");
        scheduleNormalCartsRetry(normalCartsDegradedRetryStage(d));
        return;
      }
      showNormalCartsLoadingState("جاري تحميل السلال…");
      scheduleNormalCartsRetry(normalCartsDegradedRetryStage(d));
      return;
    }

    if (!pageRows.length && !degraded) {
      var fcGuard = d.merchant_cart_filter_counts || {};
      var filterAll = normalCartsCountAll(fcGuard);
      if (filterAll > 0) {
        logClientRefresh("normal_carts_empty_mismatch_retry", { filterAll: filterAll });
        if (lastNormalCartsPageRows.length) {
          rerenderCartsFromMemory("empty_mismatch_keep");
        } else {
          showNormalCartsLoadingState("جاري تحميل السلال…");
        }
        scheduleNormalCartsRetry("empty_mismatch");
        return;
      }
    }

    if (normalCartsShouldRejectThinPayload(d, pageRows)) {
      logClientRefresh("normal_carts_thin_reject", {
        incoming_rows: pageRows.length,
        memory_rows: lastNormalCartsPageRows.length,
        incoming_all: normalCartsCountAll(d.merchant_cart_filter_counts),
        memory_all: normalCartsCountAll(lastNormalCartsFilterCounts),
        partial: normalCartsPayloadIsPartialOrThin(d),
        degraded: degraded,
      });
      if (lastNormalCartsPageRows.length) {
        rerenderCartsFromMemory("thin_keep");
      } else {
        showNormalCartsLoadingState("جاري تحميل السلال…");
      }
      scheduleNormalCartsRetry(normalCartsDegradedRetryStage(d) || "thin");
      return;
    }

    if (!pageRows.length && !normalCartsIsConfirmedFullEmpty(d, pageRows)) {
      logClientRefresh("normal_carts_unconfirmed_empty", {
        source: normalCartsPayloadSource(d),
        snapshot_mode: !!(d && d.snapshot_mode),
        filter_all: normalCartsCountAll((d && d.merchant_cart_filter_counts) || {}),
        hadRows: lastNormalCartsPageRows.length,
      });
      if (lastNormalCartsPageRows.length) {
        rerenderCartsFromMemory("unconfirmed_empty_keep");
      } else {
        showNormalCartsLoadingState("جاري تحميل السلال…");
      }
      scheduleNormalCartsRetry("unconfirmed_empty");
      return;
    }

    ingestRefreshToken(d, "normal-carts");
    var prepared = prepareNormalCartsPayload(d, normalCartsPayloadSource(d));
    if (!pageRows.length && normalCartsIsConfirmedFullEmpty(d, pageRows)) {
      prepared.__ma_confirmed_empty = true;
    }
    renderNormalCartsTables(prepared);
    persistNormalCartsCache(prepared);
    if (fetchGen != null) {
      normalCartsAppliedGen = Math.max(normalCartsAppliedGen, fetchGen);
    }
    normalCartsBootComplete = true;
    logClientRefresh("normal_carts_applied", {
      fetch_label: d._label || "",
      rows_count: normalCartsPayloadRows(prepared).length,
      degraded: degraded,
      partial: !!d.dashboard_partial,
      source: normalCartsPayloadSource(prepared),
      appliedGen: normalCartsAppliedGen,
      selected_filter:
        typeof window.getCurrentNormalCartFilter === "function"
          ? window.getCurrentNormalCartFilter()
          : null,
    });
    startPendingNewCartWatcher();
  }

  function fetchNormalCarts(label) {
    var gen = ++normalCartsFetchGen;
    showNormalCartsLoadingState();
    var u = "/api/dashboard/normal-carts?_ts=" + Date.now();
    if (label) {
      u += "&_label=" + encodeURIComponent(String(label));
    }
    return fetch(u, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        applyNormalCarts(d, gen);
        return d;
      })
      .catch(function (err) {
        logClientRefresh("normal_carts_fetch_failed", { label: label || "", err: String(err) });
        if (lastNormalCartsPageRows.length) {
          scheduleNormalCartsRetry("fetch_error");
        } else {
          showNormalCartsLoadingState("تعذّر تحميل السلال — إعادة المحاولة…");
          scheduleNormalCartsRetry("fetch_error");
        }
      });
  }

  function applyVipCartAlert(ban) {
    var root = byId("ma-cart-alerts-root");
    var host = byId("ma-cart-alerts-vip");
    if (!host) return;
    var hasVipCarts =
      lastVipPageRows.length > 0 ||
      lastVipHomeRows.length > 0 ||
      !!(ban && ban.amount_line);
    if (!hasVipCarts || !ban || !ban.amount_line) {
      host.innerHTML = "";
      if (root) root.hidden = true;
      return;
    }
    if (root) root.hidden = false;
    var btn =
      window.maVipAutomation && typeof window.maVipAutomation.renderBannerBtn === "function"
        ? window.maVipAutomation.renderBannerBtn(ban)
        : "";
    if (!btn) {
      var href = ban.contact_href || "";
      btn = href
        ? '<a class="va-btn" href="' +
          esc(href) +
          '" rel="noopener noreferrer" target="_blank">تواصل يدوي (VIP) ←</a>'
        : '<span class="va-btn is-disabled" role="button" aria-disabled="true">تواصل يدوي (VIP) ←</span>';
    }
    host.innerHTML =
      '<div class="vip-alert"><div class="va-icon">👑</div><div class="va-body">' +
      '<div class="va-title">عميل VIP يحتاج تدخلك — لن يُرسَل له واتساب تلقائياً</div>' +
      '<div class="va-sub">' +
      esc(ban.amount_line) +
      "</div></div>" +
      btn +
      "</div>";
  }

  function vipItemHtml(vr) {
    var btn =
      window.maVipAutomation && typeof window.maVipAutomation.renderHomeItemBtn === "function"
        ? window.maVipAutomation.renderHomeItemBtn(vr)
        : "";
    if (!btn) {
      var href = vr.contact_href || "";
      btn = href
        ? '<a class="vbtn" href="' +
          esc(href) +
          '" rel="noopener noreferrer" target="_blank">تواصل يدوي (VIP)</a>'
        : '<span class="vbtn is-disabled">تواصل يدوي (VIP)</span>';
    }
    return (
      '<div class="vip-item">' +
      '<div class="vav">' +
      esc(vr.avatar_letter || "") +
      "</div>" +
      '<div class="vi"><div class="vamt cf-currency-atom" data-cf-currency="1">' +
      esc(vr.amount_display) +
      "\u00a0ر.س</div><div class=\"vtm\">" +
      esc(vr.subtitle_ar) +
      '</div></div><span class="vtag">VIP</span>' +
      btn +
      "</div>"
    );
  }

  function vipRowTable(vr) {
    var btn =
      window.maVipAutomation && typeof window.maVipAutomation.renderTableAction === "function"
        ? window.maVipAutomation.renderTableAction(vr)
        : "";
    if (!btn) {
      var href = vr.contact_href || "";
      var noPhoneMsg =
        vr.manual_contact_unavailable_ar ||
        "لا يوجد رقم عميل متاح — تواصل يدوي غير ممكن حتى يتوفر رقم العميل";
      btn = href
        ? '<a class="va-btn" href="' +
          esc(href) +
          '" rel="noopener noreferrer" target="_blank">تواصل يدوي (VIP) ←</a>'
        : '<span class="va-btn is-disabled" title="' +
          esc(noPhoneMsg) +
          '">تواصل يدوي (VIP) ←</span><div class="ma-vip-no-phone-ar">' +
          esc(noPhoneMsg) +
          "</div>";
    }
    var hp = vr.has_phone
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no" title="' +
        esc(
          vr.manual_contact_unavailable_ar ||
            "لا يوجد رقم متاح — تواصل يدوي غير ممكن حتى يتوفر رقم العميل"
        ) +
        '">✗ غير متوفر</span>';
    return (
      "<tr><td><div class=\"camt cf-currency-atom\" data-cf-currency=\"1\">" +
      esc(vr.amount_display) +
      "\u00a0ر.س</div></td><td><div class=\"ctime\">" +
      esc(vr.subtitle_ar) +
      "</div></td><td>" +
      hp +
      "</td><td>" +
      btn +
      "</td></tr>"
    );
  }

  function vipPageEmptyHtml() {
    return (
      '<tr><td colspan="4" class="empty-state" style="border:none;">' +
      '<div class="empty-icon">👑</div>' +
      '<div class="empty-text">لا توجد سلال VIP نشطة تحتاج تدخلك الآن</div>' +
      '<p class="ma-vip-load-diag">آخر تحقق: تم تحميل البيانات بنجاح</p>' +
      "</td></tr>"
    );
  }

  function vipPageLoadingRowHtml(message) {
    return (
      '<tr class="ma-dash-loading-row" data-ma-vip-loading="1">' +
      '<td colspan="4" style="text-align:center;padding:24px;color:var(--muted);">' +
      esc(message || "جاري تحميل سلال VIP…") +
      "</td></tr>"
    );
  }

  function vipPageErrorHtml(message) {
    return (
      '<tr><td colspan="4" style="text-align:center;padding:24px;color:#991b1b;">' +
      esc(message || "تعذر تحميل سلال VIP") +
      "</td></tr>"
    );
  }

  function vipCartsPayloadPageRows(d) {
    return (d && d.merchant_vip_page_rows) || [];
  }

  function vipCartsIsDegraded(d) {
    if (!d) return true;
    return !!(d.dashboard_partial || d.dashboard_timeout);
  }

  function persistVipCartsCache(d) {
    try {
      if (!d || !d.ok) return;
      var pageRows = vipCartsPayloadPageRows(d);
      if (!pageRows.length) {
        sessionStorage.removeItem(VIP_CARTS_CACHE_KEY);
        return;
      }
      sessionStorage.setItem(
        VIP_CARTS_CACHE_KEY,
        JSON.stringify({
          page_rows: pageRows,
          home_rows: (d && d.merchant_vip_rows) || pageRows.slice(0, 3),
          banner: (d && d.merchant_vip_banner) || null,
          nav_badge: d.merchant_nav_badge_vip,
          alert_state_ar: d.merchant_vip_alert_state_ar || "",
          automation_mode: d.merchant_automation_mode || "",
          saved_at: Date.now(),
        })
      );
    } catch (_vipCacheErr) {
      /* ignore */
    }
  }

  function hydrateVipCartsCache() {
    try {
      var raw = sessionStorage.getItem(VIP_CARTS_CACHE_KEY);
      if (!raw) return false;
      var c = JSON.parse(raw);
      if (!c || !c.page_rows || !c.page_rows.length) return false;
      renderVipCartsTables({
        ok: true,
        merchant_vip_page_rows: c.page_rows,
        merchant_vip_rows: c.home_rows || c.page_rows.slice(0, 3),
        merchant_vip_banner: c.banner || null,
        merchant_nav_badge_vip: c.nav_badge,
        merchant_vip_alert_state_ar: c.alert_state_ar || "",
        merchant_automation_mode: c.automation_mode || "",
      });
      vipCartsHasRenderedRows = true;
      logClientRefresh("vip_carts_cache_hydrate", { rows: c.page_rows.length });
      return true;
    } catch (_vipHydrateErr) {
      return false;
    }
  }

  function renderVipCartsTables(d) {
    var pageRows = vipCartsPayloadPageRows(d);
    lastVipPageRows = pageRows;
    lastVipHomeRows = (d && d.merchant_vip_rows) || pageRows.slice(0, 3);
    lastVipBanner = (d && d.merchant_vip_banner) || null;
    if (pageRows.length) {
      vipCartsHasRenderedRows = true;
    }
    applyVipCartAlert(lastVipBanner);
    var list = byId("ma-vip-home-list");
    if (list) {
      var alertLine = String((d && d.merchant_vip_alert_state_ar) || "").trim();
      if (!lastVipHomeRows.length) {
        list.innerHTML =
          '<div class="empty-state"><div class="empty-icon">👑</div><div class="empty-text">' +
          esc(alertLine || "لا سلال VIP تحتاج تدخلك حالياً") +
          '</div><p class="ma-vip-load-diag">آخر تحقق: تم تحميل البيانات بنجاح</p></div>';
      } else {
        list.innerHTML = lastVipHomeRows.map(vipItemHtml).join("");
      }
    }
    var tb = byId("ma-tbody-vip-page");
    if (tb) {
      if (!pageRows.length) {
        tb.innerHTML = vipPageEmptyHtml();
      } else {
        tb.innerHTML = pageRows.map(vipRowTable).join("");
      }
    }
    if (d && d.merchant_nav_badge_vip != null) {
      setNavBadge("ma-nav-badge-vip", d.merchant_nav_badge_vip);
    } else if (pageRows.length) {
      setNavBadge("ma-nav-badge-vip", pageRows.length);
    }
  }

  function rerenderVipFromMemory(reason) {
    if (!lastVipPageRows.length) {
      if (hydrateVipCartsCache()) {
        logClientRefresh("vip_rerender_cache", { reason: reason || "" });
      }
      return;
    }
    renderVipCartsTables({
      ok: true,
      merchant_vip_page_rows: lastVipPageRows,
      merchant_vip_rows: lastVipHomeRows,
      merchant_vip_banner: lastVipBanner,
      merchant_nav_badge_vip: lastVipPageRows.length,
    });
    logClientRefresh("vip_rerender_memory", {
      reason: reason || "",
      rows: lastVipPageRows.length,
    });
  }

  function showVipCartsLoadingState(message) {
    if (vipCartsHasRenderedRows && lastVipPageRows.length) return;
    var tb = byId("ma-tbody-vip-page");
    if (tb && !lastVipPageRows.length) {
      tb.innerHTML = vipPageLoadingRowHtml(message);
    }
  }

  function scheduleVipCartsRetry(label) {
    if (window.__maVipCartsPartialRetryPending) return;
    window.__maVipCartsPartialRetryPending = true;
    logClientRefresh("vip_carts_retry_scheduled", { label: label || "partial" });
    window.setTimeout(function () {
      window.__maVipCartsPartialRetryPending = false;
      fetchVipCarts("vip_carts_retry_" + (label || "partial"));
    }, 1200);
  }

  function applyVipCartsFailed(message) {
    if (lastVipPageRows.length || vipCartsHasRenderedRows) {
      rerenderVipFromMemory("fetch_error_keep");
      scheduleVipCartsRetry("fetch_error");
      return;
    }
    var tb = byId("ma-tbody-vip-page");
    if (tb) tb.innerHTML = vipPageErrorHtml(message);
    var list = byId("ma-vip-home-list");
    if (list) {
      list.innerHTML =
        '<div class="empty-state" style="color:#991b1b;"><div class="empty-text">' +
        esc(message || "تعذر تحميل سلال VIP") +
        "</div></div>";
    }
  }

  function applyVipCarts(d, fetchGen) {
    if (fetchGen != null && fetchGen < vipCartsAppliedGen) {
      logClientRefresh("vip_carts_stale_skip", {
        fetchGen: fetchGen,
        appliedGen: vipCartsAppliedGen,
        inflightGen: vipCartsFetchGen,
      });
      return;
    }
    if (!d || !d.ok) {
      if (lastVipPageRows.length || vipCartsHasRenderedRows) {
        rerenderVipFromMemory("ok_false_keep");
        scheduleVipCartsRetry("ok_false");
        return;
      }
      applyVipCartsFailed();
      return;
    }
    var pageRows = vipCartsPayloadPageRows(d);
    var degraded = vipCartsIsDegraded(d);
    var partialEmpty = degraded && !pageRows.length;

    if (partialEmpty) {
      logClientRefresh("vip_carts_partial_empty", {
        stage: d.dashboard_timeout_stage || null,
        hadRows: lastVipPageRows.length,
      });
      if (lastVipPageRows.length || vipCartsHasRenderedRows) {
        rerenderVipFromMemory("partial_keep");
        scheduleVipCartsRetry(d.dashboard_timeout_stage || "partial");
        return;
      }
      showVipCartsLoadingState("جاري تحميل سلال VIP…");
      scheduleVipCartsRetry(d.dashboard_timeout_stage || "partial");
      return;
    }

    if (!pageRows.length && !degraded && (lastVipPageRows.length || vipCartsHasRenderedRows)) {
      var navBadge = parseInt(d.merchant_nav_badge_vip, 10);
      if (isFinite(navBadge) && navBadge > 0) {
        logClientRefresh("vip_carts_empty_mismatch_retry", { navBadge: navBadge });
        rerenderVipFromMemory("empty_mismatch_keep");
        scheduleVipCartsRetry("empty_mismatch");
        return;
      }
    }

    if (window.maVipAutomation) {
      if (d.merchant_automation_mode) {
        window.maVipAutomation.setMode(d.merchant_automation_mode);
      }
      window.maVipAutomation.storePayload(d);
    }
    renderVipCartsTables(d);
    persistVipCartsCache(d);
    if (fetchGen != null) {
      vipCartsAppliedGen = Math.max(vipCartsAppliedGen, fetchGen);
    }
    logClientRefresh("vip_carts_applied", {
      rows: pageRows.length,
      degraded: degraded,
      partial: !!d.dashboard_partial,
      appliedGen: vipCartsAppliedGen,
    });
  }

  function fetchVipCarts(label) {
    var gen = ++vipCartsFetchGen;
    showVipCartsLoadingState();
    var u = "/api/dashboard/vip-carts?_ts=" + Date.now();
    if (label) {
      u += "&_label=" + encodeURIComponent(String(label));
    }
    return fetch(u, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        applyVipCarts(d, gen);
        return d;
      })
      .catch(function (err) {
        logClientRefresh("vip_carts_fetch_failed", {
          label: label || "",
          err: String(err),
        });
        if (lastVipPageRows.length || vipCartsHasRenderedRows) {
          rerenderVipFromMemory("fetch_error_keep");
          scheduleVipCartsRetry("fetch_error");
        } else {
          applyVipCartsFailed();
          scheduleVipCartsRetry("fetch_error");
        }
      });
  }

  function followRowHtml(fr) {
    var cv = fr.cart_value;
    var camt =
      cv != null && cv !== ""
        ? '<div class="camt">' +
          formatMerchantSar(cv) +
          "</div>"
        : '<div class="camt">—</div>';
    var digits = !!fr.customer_wa_digits;
    var ph = digits
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    var act = followupCompactHtml(fr);
    return (
      "<tr>" +
      "<td>" +
      camt +
      '<div class="ctime">' +
      esc(fr.replied_at || "—") +
      "</div></td>" +
      '<td><span class="chip c-other">' +
      esc(fr.reason_tag_ar || fr.reason_ar || "—") +
      "</span></td>" +
      '<td><div class="msg-text" style="margin:0;">' +
      esc(fr.last_message_line_ar || "—") +
      '</div></td><td><div class="ctime">' +
      esc(merchantAttemptsDisplayAr(fr)) +
      "</div></td><td>" +
      ph +
      "</td><td>" +
      act +
      "</td></tr>"
    );
  }

  function applyFollowups(d) {
    if (!d || !d.ok) return;
    var tb = byId("ma-tbody-followups");
    if (tb) {
      var fr = d.merchant_followup_rows || [];
      if (!fr.length) {
        tb.innerHTML =
          '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">🔔</div><div class="empty-text">لا توجد سلال تفاعل حالياً</div></td></tr>';
      } else {
        tb.innerHTML = fr.map(followRowHtml).join("");
      }
    }
    setNavBadge("ma-nav-badge-followup", d.merchant_nav_badge_followup);
  }

  // Communication Timeline rows are driven by this array (modal reads by index).
  var cfMsgRows = [];

  function messageRowHtml(mr, idx) {
    // Communication Timeline row: who / what type / when / delivery outcome.
    // Cart value, reason tag, lifecycle and next-step intentionally excluded —
    // those belong to the Carts page. Full text/timeline lives in the modal.
    var dots = mr.delivery_dots || "";
    var outcome = mr.delivery_outcome_ar || mr.delivery_status_ar || mr.status_ar || "—";
    var replyBadge = mr.customer_reply_ar
      ? '<span class="msg-reply-badge">💬 رد العميل</span>'
      : "";
    var dotsHtml = dots
      ? '<span class="msg-dots" title="' + esc(outcome) + '">' + esc(dots) + "</span>"
      : "";
    return (
      '<div class="msg-row" data-msg-index="' +
      idx +
      '">' +
      '<div class="msg-avatar">💬</div>' +
      '<div class="msg-body">' +
      '<div class="msg-header">' +
      '<div class="msg-name">' +
      esc(mr.message_type_ar || mr.title_ar || "رسالة استرداد") +
      '</div><div class="msg-time">' +
      esc(mr.time_ar || "—") +
      "</div></div>" +
      '<div class="msg-meta"><span class="msg-phone" dir="ltr">' +
      esc(mr.phone_masked || "—") +
      "</span>" +
      dotsHtml +
      "</div>" +
      '<div class="msg-tags">' +
      '<span class="st ' +
      esc(mr.delivery_status_class || mr.status_row_class || "s-sent") +
      '\"><span class="sd"></span>' +
      esc(outcome) +
      "</span>" +
      replyBadge +
      '<button type="button" class="ma-msg-view" onclick="cfOpenMessageModal(this)">عرض الرسالة</button>' +
      "</div></div></div>"
    );
  }

  var cfMsgModalCartId = "";

  function cfSetMsgField(id, val) {
    var el = byId(id);
    if (el) {
      el.textContent = val == null || val === "" ? "—" : String(val);
    }
  }

  function cfRenderDeliveryTimeline(steps) {
    var host = byId("ma-msg-delivery");
    if (!host) return;
    if (!steps || !steps.length) {
      host.innerHTML = '<span class="ma-msg-empty">—</span>';
      return;
    }
    host.innerHTML = steps
      .map(function (s) {
        return (
          '<span class="ma-msg-step ma-msg-step-' +
          esc(s.state || "pending") +
          '"><span class="ma-msg-step-dot">' +
          esc(s.emoji || "⚪") +
          '</span>' +
          esc(s.label_ar || "") +
          "</span>"
        );
      })
      .join('<span class="ma-msg-step-sep">↓</span>');
  }

  function cfRenderCommTimeline(events) {
    var host = byId("ma-msg-comm");
    if (!host) return;
    if (!events || !events.length) {
      host.innerHTML = '<span class="ma-msg-empty">—</span>';
      return;
    }
    host.innerHTML = events
      .map(function (ev) {
        return (
          '<div class="ma-msg-tl-item">' +
          '<span class="ma-msg-tl-emoji">' +
          esc(ev.emoji || "•") +
          "</span>" +
          '<span class="ma-msg-tl-label">' +
          esc(ev.label_ar || "") +
          "</span>" +
          '<span class="ma-msg-tl-at">' +
          esc(ev.at_ar || "") +
          "</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function cfOpenMessageModal(el) {
    try {
      var row = el && el.closest ? el.closest(".msg-row") : null;
      if (!row) return;
      var idx = parseInt((row.dataset || {}).msgIndex, 10);
      var mr =
        !isNaN(idx) && cfMsgRows && cfMsgRows[idx] ? cfMsgRows[idx] : null;
      if (!mr) {
        // SSR fallback (lazy data not yet loaded): basic fields from data-*.
        var d = row.dataset || {};
        mr = {
          full_message_ar: d.msgFull,
          phone_masked: d.msgPhone,
          template_ar: d.msgTemplate,
          sent_full_ar: d.msgSent,
          provider_status_ar: d.msgProvider,
          recovery_key: d.msgKey,
          cart_id: d.msgCart,
        };
      }
      cfSetMsgField("ma-msg-full", mr.full_message_ar || "—");
      cfSetMsgField("ma-msg-phone", mr.phone_masked || "—");
      cfSetMsgField("ma-msg-template", mr.template_ar || mr.message_type_ar || "—");
      cfSetMsgField("ma-msg-sent", mr.sent_full_ar || mr.time_ar || "—");
      cfSetMsgField("ma-msg-provider", mr.provider_status_ar || "—");
      cfSetMsgField("ma-msg-sid", mr.provider_message_sid || "—");
      cfSetMsgField("ma-msg-key", mr.recovery_key || "—");
      cfSetMsgField("ma-msg-provider-resp", mr.provider_response_ar || "—");
      cfSetMsgField("ma-msg-session", mr.session_id || "—");
      cfSetMsgField("ma-msg-cartid", mr.cart_id || "—");
      cfSetMsgField("ma-msg-logid", mr.log_id || "—");

      cfRenderDeliveryTimeline(mr.delivery_timeline);
      cfRenderCommTimeline(mr.communication_timeline);

      var replyWrap = byId("ma-msg-reply-wrap");
      if (replyWrap) {
        if (mr.customer_reply_ar) {
          cfSetMsgField("ma-msg-reply", mr.customer_reply_ar);
          replyWrap.hidden = false;
        } else {
          cfSetMsgField("ma-msg-reply", "لا يوجد رد");
          replyWrap.hidden = false;
        }
      }

      cfMsgModalCartId = mr.cart_id || "";
      var openCartBtn = byId("ma-msg-open-cart");
      if (openCartBtn) {
        openCartBtn.disabled = false;
      }
      var m = byId("ma-msg-modal");
      if (m) {
        m.hidden = false;
        m.classList.add("open");
      }
    } catch (eOpen) {}
  }

  function cfCloseMessageModal() {
    var m = byId("ma-msg-modal");
    if (m) {
      m.hidden = true;
      m.classList.remove("open");
    }
  }

  function cfOpenRelatedCart() {
    cfCloseMessageModal();
    try {
      if (typeof window.goTo === "function") {
        window.goTo("carts");
        return;
      }
    } catch (eGo) {}
    try {
      window.location.hash = "#carts";
    } catch (eHash) {}
  }

  try {
    document.addEventListener(
      "keydown",
      function (ev) {
        if (ev && ev.key === "Escape") {
          cfCloseMessageModal();
        }
      },
      false
    );
  } catch (eKd) {}

  window.cfOpenMessageModal = cfOpenMessageModal;
  window.cfCloseMessageModal = cfCloseMessageModal;
  window.cfOpenRelatedCart = cfOpenRelatedCart;

  function applyMessages(d) {
    if (!d || !d.ok) return;
    ingestRefreshToken(d, "messages");
    var card = byId("ma-messages-card");
    if (!card) return;
    var rows = d.merchant_message_history_rows || [];
    cfMsgRows = rows;
    if (!rows.length) {
      card.innerHTML =
        '<div class="empty-state" style="padding:40px 20px;"><div class="empty-icon">💬</div><div class="empty-text">لا توجد رسائل مرسلة بعد</div></div>';
    } else {
      card.innerHTML = rows
        .map(function (mr, i) {
          return messageRowHtml(mr, i);
        })
        .join("");
    }
    setText("ma-wa-last-send", d.merchant_wa_last_send_ar || "—");
  }

  function setCk(id, on) {
    var el = byId(id);
    if (el) el.checked = !!on;
  }

  function setRadio(name, val) {
    var q = document.querySelector(
      'input[name="' + name + '"][value="' + val + '"]'
    );
    if (q) q.checked = true;
  }

  function setSel(id, val) {
    var el = byId(id);
    if (!el) return;
    el.value = val == null ? "" : String(val);
    try {
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {}
  }

  function reasonEditorRowHtml(r) {
    var k = esc(String(r.key || "").trim().toLowerCase());
    var lab = esc(r.label_ar || "");
    var on = r.enabled ? " checked" : "";
    return (
      '<tr data-mw-reason-row>' +
      "<td>" +
      '<input type="hidden" class="mw-reason-key" value="' +
      k +
      '">' +
      '<p class="ma-fw-field-hint" style="margin:0 0 4px 0;opacity:0.85;">هذا النص هو ما يظهر للعميل داخل الودجيت.</p>' +
      '<input class="ma-fw-input mw-reason-label" type="text" maxlength="80" value="' +
      lab +
      '" dir="rtl" autocomplete="off">' +
      '</td><td class="ma-fw-td-center"><input class="mw-reason-on" type="checkbox"' +
      on +
      "></td>" +
      '<td class="ma-fw-td-center">' +
      '<button type="button" class="ma-fw-mini" data-mw-reason-up title="تحريك لأعلى">↑</button>' +
      '<button type="button" class="ma-fw-mini" data-mw-reason-down title="تحريك لأسفل">↓</button>' +
      "</td></tr>"
    );
  }

  function applyWidgetPanel(d) {
    if (!d || !d.ok) return;
    var wp = d.merchant_widget_panel || {};
    var tg = wp.trigger || {};
    var boot = byId("ma-widget-bootstrap");
    if (boot) {
      try {
        boot.textContent = JSON.stringify(wp);
      } catch (e) {}
    }
    var wn = byId("mw-widget-name");
    if (wn) wn.value = String(wp.widget_name || "مساعد المتجر");
    var wc = byId("mw-widget-color");
    if (wc) wc.value = String(wp.widget_primary_color || "#6C5CE7");
    setCk("mw-widget-enabled", wp.cartflow_widget_enabled !== false);

    var tb = byId("mw-reason-tbody");
    if (tb) {
      var rr = wp.reason_rows || [];
      tb.innerHTML = rr.map(reasonEditorRowHtml).join("");
    }

    setCk("mw-exit-enabled", tg.exit_intent_enabled !== false);
    setSel("mw-exit-delay", String(parseInt(tg.exit_intent_delay_seconds, 10) || 0));
    setSel("mw-exit-sens", String(tg.exit_intent_sensitivity || "medium"));
    setSel("mw-exit-freq", String(tg.exit_intent_frequency || "per_session"));

    setCk("mw-hes-enabled", tg.hesitation_trigger_enabled !== false);
    var hesSec = parseInt(tg.hesitation_after_seconds, 10);
    if (!isFinite(hesSec)) hesSec = 20;
    var presets = [0, 5, 10, 20, 30, 15, 45, 60, 90, 120];
    var sel = presets.indexOf(hesSec) >= 0 ? String(hesSec) : "custom";
    setSel("mw-hes-sec", sel);
    var hsc = byId("mw-hes-sec-custom");
    if (hsc) {
      hsc.value = String(hesSec);
      hsc.style.display = sel === "custom" ? "" : "none";
    }
    var lbl = byId("mw-hes-sec-custom-label");
    if (lbl) lbl.style.display = sel === "custom" ? "" : "none";

    setSel("mw-hes-cond", String(tg.hesitation_condition || "after_cart_add"));
    setSel("mw-scope", String(tg.visibility_page_scope || "all"));

    setCk("mw-sup-dismiss", tg.suppress_after_widget_dismiss !== false);
    setCk("mw-sup-purchase", tg.suppress_after_purchase !== false);
    setCk("mw-sup-checkout", tg.suppress_when_checkout_started !== false);

    setRadio("mw-phone", String(tg.widget_phone_capture_mode || "after_reason"));

    setText("ma-settings-widget-title", d.merchant_widget_title_ar || "—");
    var we = byId("ma-settings-widget-enabled");
    if (we) {
      we.textContent = d.merchant_widget_installed ? "نعم" : "لا";
    }

    if (window.cartflowMerchantWidgetPanelRebindReasons) {
      window.cartflowMerchantWidgetPanelRebindReasons();
    } else if (window.cartflowMerchantWidgetPanelRefresh) {
      window.cartflowMerchantWidgetPanelRefresh();
    }
  }

  function fetchSection(url, applyFn, label) {
    var u = String(url || "");
    var sep = u.indexOf("?") >= 0 ? "&" : "?";
    var bust = "_ts=" + Date.now();
    return fetch(u + sep + bust, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        applyFn(d);
      })
      .catch(function () {
        /* section failed — shell remains */
      });
  }

  function refreshCoreSections(reason) {
    if (merchantRefreshInFlight) return;
    merchantRefreshInFlight = true;
    logClientRefresh("refresh_start", {
      reason: reason || "unknown",
      token: merchantDashboardRefreshToken,
    });
    Promise.allSettled([
      fetchSection("/api/dashboard/summary", applySummary, "summary"),
      fetchSection("/api/dashboard/messages", applyMessages, "messages"),
      fetchVipCarts("refresh_core"),
    ]).finally(function () {
      merchantRefreshInFlight = false;
      logClientRefresh("refresh_end", {
        reason: reason || "unknown",
        token: merchantDashboardRefreshToken,
      });
      if (window.__maNormalCartsTokenRefetchAfterBoot) {
        var lbl = window.__maNormalCartsTokenRefetchAfterBoot;
        window.__maNormalCartsTokenRefetchAfterBoot = "";
        fetchNormalCarts(lbl);
      }
    });
    fetchNormalCarts("refresh_core");
  }

  function checkRefreshState() {
    if (normalCartsBootInFlight && !normalCartsBootComplete) {
      return Promise.resolve();
    }
    var u = "/api/dashboard/refresh-state?_ts=" + Date.now();
    return fetch(u, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.ok) return;
        var next = String(d.merchant_dashboard_refresh_token || "");
        if (!next) return;
        if (!merchantDashboardRefreshToken) {
          merchantDashboardRefreshToken = next;
          logClientRefresh("token_init", { token: next });
          return;
        }
        if (next !== merchantDashboardRefreshToken) {
          var prev = merchantDashboardRefreshToken;
          merchantDashboardRefreshToken = next;
          logClientRefresh("token_changed", { from: prev, to: next });
          scheduleNormalCartsTokenRefetch("token_refresh_state");
        }
      })
      .catch(function () {
        /* ignore refresh watcher failures */
      });
  }

  function startRefreshWatcher() {
    if (merchantRefreshTimer) return;
    checkRefreshState();
    merchantRefreshTimer = window.setInterval(function () {
      if (document.hidden) return;
      checkRefreshState();
    }, 2500);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) {
        checkRefreshState();
        if (!lastNormalCartsPageRows.length) {
          fetchNormalCarts("visibility_resume");
        }
        startPendingNewCartWatcher();
      }
    });
  }

  function bootLazyDashboard() {
    logSetupRenderDebug("boot", {
      hasRenderUnified: typeof renderUnifiedSetupExperience === "function",
      hasShouldHide: typeof shouldHideUnifiedSetupCard === "function",
    });
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-kpi-abandoned")) return;

    /* Stale-while-revalidate: paint cached rows immediately, then refresh. */
    hydrateNormalCartsCache();
    hydrateVipCartsCache();
    fetchSection("/api/dashboard/summary", applySummary, "summary");
    bootSetupReadinessHydration();
    var bootHash = (location.hash || "").split("?")[0].toLowerCase();
    fetchVipCarts(bootHash === "#vip" ? "boot_vip_hash" : "boot_parallel");
    normalCartsBootInFlight = true;
    fetchNormalCarts("boot_priority").finally(function () {
      normalCartsBootInFlight = false;
      if (window.__maNormalCartsTokenRefetchAfterBoot) {
        var bootLbl = window.__maNormalCartsTokenRefetchAfterBoot;
        window.__maNormalCartsTokenRefetchAfterBoot = "";
        fetchNormalCarts(bootLbl);
      }
      ensureNormalCartsPageReady("boot_done");
      startPendingNewCartWatcher();
      var jobs = [
        fetchSection("/api/dashboard/followups", applyFollowups, "followups"),
        fetchSection("/api/dashboard/widget-panel", applyWidgetPanel, "widget_panel"),
        fetchSection("/api/dashboard/messages", applyMessages, "messages"),
      ];
      Promise.allSettled(jobs);
      startRefreshWatcher();
    });
  }

  window.maApplyVipCartsPayload = applyVipCarts;
  window.maSyncHomeActivation = syncHomeActivationFromCache;
  window.maApplyDashboardSummary = applySummary;
  window.maBootSetupReadinessHydration = bootSetupReadinessHydration;
  window.MERCHANT_SETUP_RENDER_BUILD = MERCHANT_SETUP_RENDER_BUILD;
  window.maFetchNormalCartsNow = function (label) {
    return fetchNormalCarts(label || "manual_now");
  };
  window.maEnsureNormalCartsPageReady = ensureNormalCartsPageReady;
  window.maFetchVipCartsNow = function (label) {
    return fetchVipCarts(label || "manual_now");
  };

  window.__maNormalCartsTestHooks = {
    applyNormalCarts: applyNormalCarts,
    fetchNormalCarts: fetchNormalCarts,
    renderNormalCartsTables: renderNormalCartsTables,
    hydrateNormalCartsCache: hydrateNormalCartsCache,
    getLastRows: function () {
      return lastNormalCartsPageRows.slice();
    },
    getLastArchivedRows: function () {
      return lastArchivedCartsPageRows.slice();
    },
    syncReopenedCartRowMemory: syncReopenedCartRowMemory,
    completedCartsFromRows: completedCartsFromRows,
    isCompletedDashboardRow: isCompletedDashboardRow,
    getFetchGen: function () {
      return normalCartsFetchGen;
    },
    getAppliedGen: function () {
      return normalCartsAppliedGen;
    },
    normalCartsIsDegraded: normalCartsIsDegraded,
    reapplyNormalCartFilterAfterRender: reapplyNormalCartFilterAfterRender,
    sanitizeNormalCartRowLifecycleCopy: sanitizeNormalCartRowLifecycleCopy,
    sanitizeNormalCartRows: sanitizeNormalCartRows,
    effectiveFilterCounts: effectiveFilterCounts,
    prepareNormalCartsPayload: prepareNormalCartsPayload,
    deriveFilterCountsFromRows: deriveFilterCountsFromRows,
    normalCartsShouldRejectThinPayload: normalCartsShouldRejectThinPayload,
    normalCartsPayloadIsPartialOrThin: normalCartsPayloadIsPartialOrThin,
    normalCartsIsConfirmedFullEmpty: normalCartsIsConfirmedFullEmpty,
    normalCartsFilterCountsExplicitZero: normalCartsFilterCountsExplicitZero,
    ensureNormalCartsPageReady: ensureNormalCartsPageReady,
    migrateNormalCartsCacheV1ToV2: migrateNormalCartsCacheV1ToV2,
    DEPRECATED_LIFECYCLE_WHAT_NEXT_AR: DEPRECATED_LIFECYCLE_WHAT_NEXT_AR,
    NORMAL_CARTS_CACHE_KEY: NORMAL_CARTS_CACHE_KEY,
    NORMAL_CARTS_CACHE_KEY_V1: NORMAL_CARTS_CACHE_KEY_V1,
  };

  window.__maVipCartsTestHooks = {
    applyVipCarts: applyVipCarts,
    fetchVipCarts: fetchVipCarts,
    renderVipCartsTables: renderVipCartsTables,
    hydrateVipCartsCache: hydrateVipCartsCache,
    getLastRows: function () {
      return lastVipPageRows.slice();
    },
    getFetchGen: function () {
      return vipCartsFetchGen;
    },
    getAppliedGen: function () {
      return vipCartsAppliedGen;
    },
  };

  window.addEventListener("hashchange", function () {
    syncHomeActivationFromCache();
    try {
      syncCartsPageOnHashChange();
      var hashRaw = (location.hash || "").split("?")[0].toLowerCase();
      if (hashRaw === "#vip") {
        if (!lastVipPageRows.length) {
          hydrateVipCartsCache();
        }
        fetchVipCarts("hash_vip");
      }
      if (
        hashRaw === "#completed" &&
        typeof window.maRefreshCompletedCartsTable === "function"
      ) {
        window.maRefreshCompletedCartsTable();
      }
    } catch (eHash) {
      /* ignore */
    }
  });

  function countNoPhoneRowsInPage() {
    var n = 0;
    (lastNormalCartsPageRows || []).forEach(function (mc) {
      if (cartRowMatchesFilterMode(mc, "nophone")) n += 1;
    });
    return n;
  }

  function updateNoPhoneFilterEmptyHint(mode) {
    var m = String(mode || "all").trim().toLowerCase();
    var tbody = byId("ma-tbody-all-carts");
    if (!tbody) return;
    var hint = byId("ma-nophone-page-hint");
    if (!hint) {
      hint = document.createElement("tr");
      hint.id = "ma-nophone-page-hint";
      hint.style.display = "none";
      hint.innerHTML =
        '<td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">📵</div><div class="empty-text ma-nophone-page-hint-text"></div></td>';
      tbody.appendChild(hint);
    }
    if (m !== "nophone") {
      hint.style.display = "none";
      return;
    }
    var visible = 0;
    tbody.querySelectorAll("tr[data-ma-filter]").forEach(function (tr) {
      if (tr.id === "ma-nophone-page-hint") return;
      if (tr.style.display !== "none") visible += 1;
    });
    var storeN = parseInt(
      (lastNormalCartsFilterCounts && lastNormalCartsFilterCounts.nophone) || 0,
      10
    );
    var pageMatch = countNoPhoneRowsInPage();
    if (visible === 0 && storeN > 0 && pageMatch === 0) {
      var el = hint.querySelector(".ma-nophone-page-hint-text");
      if (el) {
        el.textContent =
          "يوجد " +
          String(storeN) +
          " سلة بدون جوال في المتجر، لكنها ليست ضمن الصفحة المحمّلة حالياً.";
      }
      hint.style.display = "";
      return;
    }
    hint.style.display = "none";
  }

  (function patchApplyCartFilterModeForNoPhone() {
    var orig = window.applyCartFilterMode;
    if (typeof orig !== "function") return;
    window.applyCartFilterMode = function (mode) {
      orig(mode);
      updateNoPhoneFilterEmptyHint(mode);
    };
  })();

  function earlyHydrateDashboardCaches() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    hydrateNormalCartsCache();
    hydrateVipCartsCache();
  }

  earlyHydrateDashboardCaches();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootLazyDashboard);
  } else {
    bootLazyDashboard();
  }
})();
