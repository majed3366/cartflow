/**
 * Cart Page Rendering State Controller V1
 *
 * Sole owner of merchant-visible Cart page composition.
 * Presenters (Verdict / MI / Pending / Empty / Stories) paint only.
 *
 * Design: docs/architecture/rendering_state_controller_v1.md
 */
(function (global) {
  "use strict";

  var PHASE = {
    BOOT: "boot",
    CACHED: "cached",
    REFRESHING: "refreshing",
    FINAL: "final",
    FAILED: "failed",
  };

  var EVENTS = {
    CACHE_HYDRATED: "CACHE_HYDRATED",
    FETCH_STARTED: "FETCH_STARTED",
    APPLY_SUCCESS: "APPLY_SUCCESS",
    APPLY_KEEP: "APPLY_KEEP",
    APPLY_CONFIRMED_EMPTY: "APPLY_CONFIRMED_EMPTY",
    FETCH_FAILED: "FETCH_FAILED",
    ROWS_PATCHED: "ROWS_PATCHED",
  };

  function cloneRows(rows) {
    return Array.isArray(rows) ? rows.slice() : [];
  }

  function hasMiPayload(mi) {
    if (!mi || typeof mi !== "object") return false;
    if (
      mi.merchant_value_stories_v1 &&
      Array.isArray(mi.merchant_value_stories_v1.stories) &&
      mi.merchant_value_stories_v1.stories.length
    ) {
      return true;
    }
    return !!(
      mi.merchant_intelligence_store_v1 &&
      Array.isArray(mi.merchant_intelligence_store_v1.groups)
    );
  }

  function extractMi(payload) {
    if (!payload || typeof payload !== "object") return null;
    if (!hasMiPayload(payload)) return null;
    return {
      merchant_value_stories_v1: payload.merchant_value_stories_v1 || null,
      merchant_intelligence_store_v1: payload.merchant_intelligence_store_v1 || null,
    };
  }

  function emptyCounts() {
    return {
      contact_customer: 0,
      follow_up_manually: 0,
      review_cart: 0,
      wait: 0,
      no_action_required: 0,
      reopen: 0,
      archive: 0,
      other: 0,
      total_active: 0,
      needs_you: 0,
    };
  }

  function defaultSnapshot() {
    return {
      phase: PHASE.BOOT,
      freshness: "pending",
      bodyMode: "loading",
      verdictMode: "loading",
      rowsSource: "none",
      miSource: "none",
      rows: [],
      miPayload: null,
      lastGood: null,
      reason: "boot",
      fetchGen: 0,
      appliedGen: 0,
      counts: emptyCounts(),
      verdict: {
        mode: "loading",
        headline: "CartFlow يجهّز صورة الانتباه…",
        detail: "",
        continue_hint: "",
        freshness: "pending",
      },
    };
  }

  function createController(opts) {
    opts = opts || {};
    var countPrimaryActions =
      typeof opts.countPrimaryActions === "function"
        ? opts.countPrimaryActions
        : function () {
            return emptyCounts();
          };
    var buildFinalVerdict =
      typeof opts.buildFinalVerdict === "function"
        ? opts.buildFinalVerdict
        : null;
    var onCommit = typeof opts.onCommit === "function" ? opts.onCommit : null;

    var snap = defaultSnapshot();

    function buildRefreshingVerdict(counts) {
      counts = counts || emptyCounts();
      return {
        mode: "refreshing",
        headline: "جارٍ تحديث الصورة...",
        detail: counts.total_active
          ? "نؤكّد حالة السلال الآن — الأرقام النهائية تظهر بعد التحديث."
          : "CartFlow يجهّز صورة الانتباه…",
        continue_hint: "",
        freshness: "pending",
        counts: counts,
      };
    }

    function buildLoadingVerdict() {
      return {
        mode: "loading",
        headline: "CartFlow يجهّز صورة الانتباه…",
        detail: "",
        continue_hint: "",
        freshness: "pending",
        counts: emptyCounts(),
      };
    }

    function deriveFinalVerdict(rows) {
      var counts = countPrimaryActions(rows || []);
      if (buildFinalVerdict) {
        var v = buildFinalVerdict(rows || [], { freshness: "final", pending: false });
        if (v) {
          v.freshness = "final";
          v.counts = counts;
          return v;
        }
      }
      if (!counts.total_active) {
        return {
          mode: "empty",
          headline: "لا يوجد ما يحتاج انتباهك الآن",
          detail: "لا توجد سلال نشطة في المتجر حالياً.",
          continue_hint: "",
          freshness: "final",
          counts: counts,
        };
      }
      if (counts.needs_you > 0) {
        return {
          mode: "needs_you",
          headline:
            counts.needs_you === 1
              ? "لديك سلة واحدة تحتاج انتباهك"
              : "لديك " + counts.needs_you + " سلال تحتاج انتباهك",
          detail: "",
          continue_hint: "تابع من البطاقات أدناه",
          freshness: "final",
          counts: counts,
        };
      }
      if (counts.wait > 0) {
        return {
          mode: "automatic",
          headline: "لا يلزم إجراء منك الآن",
          detail:
            "CartFlow يتابع " +
            counts.wait +
            (counts.wait === 1 ? " سلة تلقائياً." : " سلال تلقائياً."),
          continue_hint: "",
          freshness: "final",
          counts: counts,
        };
      }
      return {
        mode: "calm",
        headline: "لا يلزم إجراء منك الآن",
        detail: "الحالات النشطة لا تتطلب تدخلاً في هذه اللحظة.",
        continue_hint: "",
        freshness: "final",
        counts: counts,
      };
    }

    function resolveBodyMode(phase, freshness, rows, mi, lastGood) {
      var miOk = hasMiPayload(mi);
      var lastMiOk = !!(lastGood && hasMiPayload(lastGood.miPayload));
      if (phase === PHASE.FINAL && freshness === "final") {
        if (!rows || !rows.length) return "empty";
        if (miOk) return "stories";
        // Final rows but MI missing: prefer last-good stories over pending wipe.
        if (lastMiOk) return "stories";
        return rows.length ? "pending" : "empty";
      }
      // cached / refreshing / failed / boot
      if (lastMiOk) return "stories";
      if (miOk) return "stories";
      if (rows && rows.length) return "pending";
      if (phase === PHASE.BOOT) return "loading";
      return "loading";
    }

    function resolveMiForPaint(bodyMode, mi, lastGood) {
      if (bodyMode !== "stories") return null;
      if (hasMiPayload(mi)) return mi;
      if (lastGood && hasMiPayload(lastGood.miPayload)) return lastGood.miPayload;
      return null;
    }

    function resolveMiSource(mi, lastGood, livePreferred) {
      if (livePreferred && hasMiPayload(mi)) return "live";
      if (hasMiPayload(mi)) return livePreferred ? "live" : "last_good";
      if (lastGood && hasMiPayload(lastGood.miPayload)) return "last_good";
      return "none";
    }

    function commit(next) {
      snap = next;
      if (onCommit) {
        try {
          onCommit(getSnapshot());
        } catch (_e) {
          /* presenters must not break state */
        }
      }
      return getSnapshot();
    }

    function getSnapshot() {
      return {
        phase: snap.phase,
        freshness: snap.freshness,
        bodyMode: snap.bodyMode,
        verdictMode: snap.verdictMode,
        rowsSource: snap.rowsSource,
        miSource: snap.miSource,
        rows: cloneRows(snap.rows),
        miPayload: snap.miPayload,
        lastGood: snap.lastGood
          ? {
              rows: cloneRows(snap.lastGood.rows),
              miPayload: snap.lastGood.miPayload,
              verdictMode: snap.lastGood.verdictMode,
              bodyMode: snap.lastGood.bodyMode,
              appliedGen: snap.lastGood.appliedGen,
            }
          : null,
        reason: snap.reason,
        fetchGen: snap.fetchGen,
        appliedGen: snap.appliedGen,
        counts: snap.counts || emptyCounts(),
        verdict: snap.verdict,
      };
    }

    function rememberLastGood(rows, mi, verdictMode, bodyMode, appliedGen) {
      if (bodyMode !== "stories" && bodyMode !== "empty") return snap.lastGood;
      return {
        rows: cloneRows(rows),
        miPayload: hasMiPayload(mi) ? mi : snap.lastGood && snap.lastGood.miPayload,
        verdictMode: verdictMode,
        bodyMode: bodyMode,
        appliedGen: appliedGen || 0,
      };
    }

    function dispatch(eventType, payload) {
      payload = payload || {};
      var rows = cloneRows(payload.rows);
      var mi = extractMi(payload.miPayload || payload.payload || payload);
      var reason = String(payload.reason || eventType || "");
      var fetchGen = payload.fetchGen != null ? payload.fetchGen : snap.fetchGen;
      var appliedGen =
        payload.appliedGen != null ? payload.appliedGen : snap.appliedGen;
      var rowsSource = payload.rowsSource || snap.rowsSource;
      var next = getSnapshot();
      next.reason = reason;
      next.fetchGen = fetchGen;

      if (eventType === EVENTS.CACHE_HYDRATED) {
        next.phase = PHASE.CACHED;
        next.freshness = "pending";
        next.rows = rows;
        next.rowsSource = "cache";
        // Prefer incoming MI if present; else keep last-good MI.
        if (hasMiPayload(mi)) {
          next.miPayload = mi;
        } else if (snap.lastGood && hasMiPayload(snap.lastGood.miPayload)) {
          next.miPayload = snap.lastGood.miPayload;
        } else {
          next.miPayload = null;
        }
        next.bodyMode = resolveBodyMode(
          next.phase,
          next.freshness,
          next.rows,
          next.miPayload,
          snap.lastGood
        );
        next.miSource = resolveMiSource(next.miPayload, snap.lastGood, false);
        next.counts = countPrimaryActions(next.rows);
        next.verdict = buildRefreshingVerdict(next.counts);
        next.verdictMode = next.verdict.mode;
        return commit(next);
      }

      if (eventType === EVENTS.FETCH_STARTED) {
        if (snap.phase === PHASE.BOOT) {
          next.phase = PHASE.REFRESHING;
        } else if (
          snap.phase === PHASE.CACHED ||
          snap.phase === PHASE.FINAL ||
          snap.phase === PHASE.FAILED ||
          snap.phase === PHASE.REFRESHING
        ) {
          next.phase = PHASE.REFRESHING;
        } else {
          next.phase = PHASE.REFRESHING;
        }
        next.freshness = "pending";
        // Keep rows/MI from last snapshot / last-good — never wipe.
        if (!next.rows.length && snap.rows.length) next.rows = cloneRows(snap.rows);
        if (!hasMiPayload(next.miPayload)) {
          if (hasMiPayload(snap.miPayload)) next.miPayload = snap.miPayload;
          else if (snap.lastGood && hasMiPayload(snap.lastGood.miPayload)) {
            next.miPayload = snap.lastGood.miPayload;
          }
        }
        next.bodyMode = resolveBodyMode(
          next.phase,
          next.freshness,
          next.rows,
          next.miPayload,
          snap.lastGood
        );
        next.miSource = resolveMiSource(next.miPayload, snap.lastGood, false);
        next.counts = countPrimaryActions(next.rows);
        next.verdict = buildRefreshingVerdict(next.counts);
        next.verdictMode = next.verdict.mode;
        return commit(next);
      }

      if (eventType === EVENTS.APPLY_KEEP) {
        next.phase = PHASE.REFRESHING;
        next.freshness = "pending";
        if (rows.length) {
          next.rows = rows;
          next.rowsSource = payload.rowsSource || "memory";
        } else if (snap.rows.length) {
          next.rows = cloneRows(snap.rows);
          next.rowsSource = "memory";
        }
        // Critical: never clear last-good MI on keep.
        if (hasMiPayload(mi)) next.miPayload = mi;
        else if (hasMiPayload(snap.miPayload)) next.miPayload = snap.miPayload;
        else if (snap.lastGood && hasMiPayload(snap.lastGood.miPayload)) {
          next.miPayload = snap.lastGood.miPayload;
        }
        next.bodyMode = resolveBodyMode(
          next.phase,
          next.freshness,
          next.rows,
          next.miPayload,
          snap.lastGood
        );
        next.miSource = resolveMiSource(next.miPayload, snap.lastGood, false);
        next.counts = countPrimaryActions(next.rows);
        next.verdict = buildRefreshingVerdict(next.counts);
        next.verdictMode = next.verdict.mode;
        return commit(next);
      }

      if (eventType === EVENTS.APPLY_CONFIRMED_EMPTY) {
        next.phase = PHASE.FINAL;
        next.freshness = "final";
        next.rows = [];
        next.miPayload = null;
        next.rowsSource = rowsSource || "live";
        next.miSource = "none";
        next.bodyMode = "empty";
        next.appliedGen = appliedGen;
        next.counts = emptyCounts();
        next.verdict = deriveFinalVerdict([]);
        next.verdictMode = next.verdict.mode;
        next.lastGood = rememberLastGood([], null, next.verdictMode, "empty", appliedGen);
        return commit(next);
      }

      if (eventType === EVENTS.APPLY_SUCCESS) {
        next.phase = PHASE.FINAL;
        next.freshness = "final";
        next.rows = rows;
        next.rowsSource = rowsSource || "live";
        next.miPayload = hasMiPayload(mi) ? mi : null;
        // If live MI missing but last-good exists, keep stories visible (miSource last_good).
        next.bodyMode = resolveBodyMode(
          next.phase,
          next.freshness,
          next.rows,
          next.miPayload,
          snap.lastGood
        );
        if (next.bodyMode === "stories" && !hasMiPayload(next.miPayload)) {
          next.miPayload =
            snap.lastGood && hasMiPayload(snap.lastGood.miPayload)
              ? snap.lastGood.miPayload
              : null;
        }
        next.miSource = resolveMiSource(
          next.miPayload,
          snap.lastGood,
          hasMiPayload(mi)
        );
        next.appliedGen = appliedGen;
        next.counts = countPrimaryActions(next.rows);
        next.verdict = deriveFinalVerdict(next.rows);
        next.verdictMode = next.verdict.mode;
        if (next.bodyMode === "stories" || next.bodyMode === "empty") {
          next.lastGood = rememberLastGood(
            next.rows,
            hasMiPayload(mi) ? mi : next.miPayload,
            next.verdictMode,
            next.bodyMode,
            appliedGen
          );
        }
        return commit(next);
      }

      if (eventType === EVENTS.FETCH_FAILED) {
        next.phase = PHASE.FAILED;
        next.freshness = "pending";
        if (!next.rows.length && snap.rows.length) next.rows = cloneRows(snap.rows);
        if (!hasMiPayload(next.miPayload)) {
          if (hasMiPayload(snap.miPayload)) next.miPayload = snap.miPayload;
          else if (snap.lastGood && hasMiPayload(snap.lastGood.miPayload)) {
            next.miPayload = snap.lastGood.miPayload;
          }
        }
        next.bodyMode = resolveBodyMode(
          next.phase,
          next.freshness,
          next.rows,
          next.miPayload,
          snap.lastGood
        );
        next.miSource = resolveMiSource(next.miPayload, snap.lastGood, false);
        next.counts = countPrimaryActions(next.rows);
        next.verdict = buildRefreshingVerdict(next.counts);
        next.verdictMode = next.verdict.mode;
        return commit(next);
      }

      if (eventType === EVENTS.ROWS_PATCHED) {
        next.rows = rows.length ? rows : cloneRows(snap.rows);
        next.counts = countPrimaryActions(next.rows);
        if (snap.freshness === "final" && snap.phase === PHASE.FINAL) {
          next.verdict = deriveFinalVerdict(next.rows);
          next.verdictMode = next.verdict.mode;
          next.freshness = "final";
        } else {
          next.verdict = buildRefreshingVerdict(next.counts);
          next.verdictMode = next.verdict.mode;
          next.freshness = "pending";
        }
        // Keep phase/body/mi unless empty.
        if (!next.rows.length && next.freshness === "final") {
          next.bodyMode = "empty";
        }
        return commit(next);
      }

      return getSnapshot();
    }

    return {
      PHASE: PHASE,
      EVENTS: EVENTS,
      dispatch: dispatch,
      getSnapshot: getSnapshot,
      hasMiPayload: hasMiPayload,
      extractMi: extractMi,
      reset: function () {
        snap = defaultSnapshot();
        return getSnapshot();
      },
    };
  }

  var api = {
    PHASE: PHASE,
    EVENTS: EVENTS,
    createController: createController,
    hasMiPayload: hasMiPayload,
    extractMi: extractMi,
  };

  global.CartPageRenderingStateController = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
