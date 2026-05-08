/**
 * Unified CartFlow runtime bootstrap: return tracker + widget load after window.load.
 * يحمّل ‎cartflow_widget.js‎ بعد ‎window.load‎ (لا يحجب اللوحة الأولى).
 */
(function () {
  "use strict";

  var RUNTIME_VERSION = "unified-bootstrap-v1";
  var RETURN_TRACKER_SRC =
    "/static/cartflow_return_tracker.js?v=" + encodeURIComponent(RUNTIME_VERSION);

  function cartflowLoaderPerfDemoDevLog(line) {
    try {
      var p = window.location.pathname || "";
      if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
        console.log(line);
      }
    } catch (eL) {
      /* ignore */
    }
  }

  function probeTrackingLoaded() {
    try {
      return (
        typeof window.cartflowGetSessionId === "function" ||
        typeof window.cartflowMarkRecoveryFlowStarted === "function" ||
        typeof window.cartflowSyncCartState === "function"
      );
    } catch (e) {
      return false;
    }
  }

  try {
    window.CARTFLOW_RUNTIME_STATUS = {
      tracking_loaded: probeTrackingLoaded(),
      return_tracker_loaded: false,
      return_state_found: false,
      return_event_sent: false,
      last_skip_reason: null,
      runtime_version: RUNTIME_VERSION,
    };
  } catch (eSt) {
    try {
      window.CARTFLOW_RUNTIME_STATUS = {
        tracking_loaded: false,
        return_tracker_loaded: false,
        return_state_found: false,
        return_event_sent: false,
        last_skip_reason: "status_init_failed",
        runtime_version: RUNTIME_VERSION,
      };
    } catch (e2) {
      /* ignore */
    }
  }

  try {
    window.CartFlowRuntime = {
      widget: null,
      tracking: {
        probeLoaded: probeTrackingLoaded,
      },
      returnTracker: null,
      observability: {
        getStatus: function () {
          try {
            if (window.CARTFLOW_RUNTIME_STATUS) {
              window.CARTFLOW_RUNTIME_STATUS.tracking_loaded =
                probeTrackingLoaded();
            }
            return window.CARTFLOW_RUNTIME_STATUS;
          } catch (eG) {
            return null;
          }
        },
      },
    };
  } catch (eRt) {
    try {
      window.CartFlowRuntime = {
        widget: null,
        tracking: null,
        returnTracker: null,
        observability: null,
      };
    } catch (e3) {
      /* ignore */
    }
  }

  try {
    console.log("[CARTFLOW RUNTIME] bootstrap_start", RUNTIME_VERSION);
  } catch (eLb) {
    /* ignore */
  }

  window.__cartflow_loader_build = RUNTIME_VERSION;
  try {
    console.log("[CARTFLOW RUNTIME] loader_build=" + RUNTIME_VERSION);
  } catch (eB) {
    /* ignore */
  }

  function scheduleReturnTrackerModule() {
    try {
      if (window.__CARTFLOW_RT_SCRIPT_SCHEDULED__) {
        return;
      }
      window.__CARTFLOW_RT_SCRIPT_SCHEDULED__ = true;
    } catch (eF) {
      return;
    }

    var s = document.createElement("script");
    s.src = RETURN_TRACKER_SRC;
    s.async = true;
    s.onload = function () {
      try {
        var st = window.CARTFLOW_RUNTIME_STATUS;
        var rt = window.CartFlowRuntime;
        if (
          st &&
          rt &&
          typeof window.__cartflowInitReturnTracker === "function"
        ) {
          window.__cartflowInitReturnTracker(st, rt);
        } else {
          try {
            st.return_tracker_loaded = false;
            st.last_skip_reason = "return_tracker_init_missing";
            console.warn("[RETURN TRACKER ERROR]", "init_fn_missing");
          } catch (eM) {
            /* ignore */
          }
        }
      } catch (eOn) {
        try {
          if (window.CARTFLOW_RUNTIME_STATUS) {
            window.CARTFLOW_RUNTIME_STATUS.last_skip_reason =
              "return_tracker_onload_crash";
          }
          console.warn("[RETURN TRACKER ERROR]", eOn);
        } catch (eW) {
          /* ignore */
        }
      }
    };
    s.onerror = function () {
      try {
        if (window.CARTFLOW_RUNTIME_STATUS) {
          window.CARTFLOW_RUNTIME_STATUS.return_tracker_loaded = false;
          window.CARTFLOW_RUNTIME_STATUS.last_skip_reason =
            "return_tracker_script_load_failed";
        }
        console.warn("[RETURN TRACKER ERROR]", "script_load_failed");
      } catch (eEr) {
        /* ignore */
      }
    };
    try {
      (document.head || document.body || document.documentElement).appendChild(
        s
      );
    } catch (eApp) {
      try {
        window.CARTFLOW_RUNTIME_STATUS.last_skip_reason =
          "return_tracker_script_append_failed";
        console.warn("[RETURN TRACKER ERROR]", eApp);
      } catch (eZ) {
        /* ignore */
      }
    }
  }

  try {
    scheduleReturnTrackerModule();
  } catch (eSch) {
    try {
      console.warn("[RETURN TRACKER ERROR]", "schedule_crash", eSch);
    } catch (eC) {
      /* ignore */
    }
  }

  try {
    console.log("[CARTFLOW RUNTIME] return_tracker_scheduled");
  } catch (eL2) {
    /* ignore */
  }

  function cartflowBlockWidgetAfterConversion() {
    try {
      if (
        typeof window.cartflowIsSessionConverted === "function" &&
        window.cartflowIsSessionConverted()
      ) {
        return true;
      }
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (e) {
      return false;
    }
  }

  function loadWidget() {
    if (cartflowBlockWidgetAfterConversion()) {
      return;
    }
    try {
      if (window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ === true) {
        cartflowLoaderPerfDemoDevLog(
          "[CF PERF] widget loader skipped duplicate"
        );
        return;
      }
    } catch (eAct) {
      /* ignore */
    }

    try {
      var scripts = document.getElementsByTagName("script");
      var si;
      for (si = 0; si < scripts.length; si++) {
        var prevSrc = scripts[si].getAttribute("src") || "";
        if (prevSrc.indexOf("/static/cartflow_widget.js") >= 0) {
          cartflowLoaderPerfDemoDevLog(
            "[CF PERF] widget loader skipped duplicate"
          );
          window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
          return;
        }
      }
    } catch (eScr) {
      /* ignore */
    }

    try {
      if (window.CartFlowRuntime) {
        window.CartFlowRuntime.widget = { loading: true };
      }
    } catch (eWm) {
      /* ignore */
    }

    window.__CARTFLOW_WIDGET_LOADER_ACTIVE__ = true;
    var s = document.createElement("script");
    s.src = "/static/cartflow_widget.js?v=" + encodeURIComponent(RUNTIME_VERSION);
    s.async = true;
    (document.body || document.documentElement).appendChild(s);
  }

  if (document.readyState === "complete") {
    loadWidget();
  } else {
    window.addEventListener("load", loadWidget);
  }
})();
