/**
 * CartFlow — Admin Control Number Embedded Signup (Phase C2).
 * Isolated from production ES recovery. Never calls /register.
 * Never logs tokens. Aborts if production Phone Number ID appears.
 */
(function () {
  "use strict";

  var cfg = window.CARTFLOW_CONTROL_ES || {};
  var state = {
    appId: null,
    configurationId: null,
    ready: false,
    sdkReady: false,
    session: {
      waba_id: null,
      phone_number_id: null,
      business_id: null,
      event: null,
    },
    code: null,
    dialogRedirectUri: null,
    spawnPageUri: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var el = $(id);
    if (el) el.textContent = value == null ? "—" : String(value);
  }

  function showResult(obj) {
    var ok = !!(obj && obj.ok);
    setText(
      "cnes-result-status",
      ok
        ? "SUCCESS — control phone authorized (STOP before /register)"
        : "Result updated"
    );
    var pre = $("cnes-result-json");
    if (pre) {
      try {
        pre.textContent = JSON.stringify(obj || {}, null, 2);
      } catch (e) {
        pre.textContent = "{}";
      }
    }
  }

  function normalizeE164(raw) {
    var s = String(raw || "").trim();
    if (!s) return "";
    var digits = s.replace(/\D/g, "");
    if (!digits) return "";
    if (digits.indexOf("00") === 0) digits = digits.slice(2);
    return "+" + digits;
  }

  function loadFacebookSdk(appId, version, done) {
    if (window.FB) {
      window.FB.init({
        appId: appId,
        cookie: true,
        xfbml: false,
        version: version || "v21.0",
      });
      done(null);
      return;
    }
    window.fbAsyncInit = function () {
      window.FB.init({
        appId: appId,
        cookie: true,
        xfbml: false,
        version: version || "v21.0",
      });
      done(null);
    };
    var s = document.createElement("script");
    s.async = true;
    s.defer = true;
    s.crossOrigin = "anonymous";
    s.src = "https://connect.facebook.net/en_US/sdk.js";
    s.onerror = function () {
      done(new Error("sdk_load_failed"));
    };
    document.head.appendChild(s);
  }

  function listenSession() {
    window.addEventListener("message", function (event) {
      if (typeof event.origin !== "string" || event.origin.indexOf("facebook.com") === -1) {
        return;
      }
      var data = event.data;
      if (typeof data === "string") {
        try {
          data = JSON.parse(data);
        } catch (e) {
          return;
        }
      }
      if (!data || data.type !== "WA_EMBEDDED_SIGNUP") return;

      var payload = data.data || {};
      state.session.waba_id = payload.waba_id ? String(payload.waba_id) : null;
      state.session.phone_number_id = payload.phone_number_id
        ? String(payload.phone_number_id)
        : null;
      state.session.business_id = payload.business_id ? String(payload.business_id) : null;
      state.session.event = data.event ? String(data.event) : null;

      setText(
        "cnes-session-status",
        "Session: " +
          (state.session.event || "event") +
          " waba=" +
          (state.session.waba_id || "?") +
          " phone=" +
          (state.session.phone_number_id || "?")
      );

      // Client pre-checks (server still asserts).
      if (state.session.waba_id && state.session.waba_id !== cfg.controlWabaId) {
        showResult({
          ok: false,
          aborted: true,
          error: "client_waba_mismatch_or_new_waba",
          waba_id: state.session.waba_id,
          expected: cfg.controlWabaId,
        });
        return;
      }
      if (
        state.session.phone_number_id &&
        state.session.phone_number_id === cfg.productionPhoneNumberId
      ) {
        showResult({
          ok: false,
          aborted: true,
          error: "production_phone_id_appeared",
          phone_number_id: state.session.phone_number_id,
        });
      }
    });
  }

  var completing = false;

  function maybeComplete() {
    if (completing) return;
    if (!state.code) return;
    if (!state.session.waba_id || !state.session.phone_number_id) {
      setText(
        "cnes-result-status",
        "Authorization code received — waiting for WA_EMBEDDED_SIGNUP session IDs…"
      );
      return;
    }
    completing = true;
    completeOnServer();
  }

  function completeOnServer(opts) {
    opts = opts || {};
    var allowFallback = !!opts.allowWabaPhoneFallback;
    setText(
      "cnes-result-status",
      allowFallback
        ? "Exchanging code + resolving control phone on WABA…"
        : "Exchanging authorization code on server…"
    );
    var payload = {
      code: state.code,
      waba_id: state.session.waba_id || "",
      phone_number_id: state.session.phone_number_id || "",
      business_id: state.session.business_id || "",
      session_event: state.session.event || "",
      allow_waba_phone_fallback: allowFallback,
      dialog_redirect_uri: state.dialogRedirectUri || "",
      spawn_page_uri: state.spawnPageUri || "",
    };
    fetch("/admin/api/whatsapp/control-number-es/complete", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json().then(function (body) {
          return { status: r.status, body: body };
        });
      })
      .then(function (res) {
        state.code = null;
        showResult(res.body || { ok: false, http_status: res.status });
      })
      .catch(function () {
        state.code = null;
        showResult({ ok: false, error: "complete_request_failed" });
      });
  }

  function captureDialogRedirectUri(url) {
    if (!url || typeof url !== "string") return;
    try {
      var abs = url;
      if (url.indexOf("http") !== 0) {
        abs = "https://www.facebook.com" + (url.charAt(0) === "/" ? url : "/" + url);
      }
      var u = new URL(abs);
      var ru = u.searchParams.get("redirect_uri");
      if (ru) state.dialogRedirectUri = ru;
      var fallback = u.searchParams.get("fallback_redirect_uri");
      if (fallback && !state.dialogRedirectUri) state.dialogRedirectUri = fallback;
    } catch (e) {
      /* ignore */
    }
  }

  function withDialogUriCapture(fn) {
    var prevOpen = window.open;
    window.open = function (url, name, specs) {
      try {
        captureDialogRedirectUri(url);
      } catch (eCap) {
        /* ignore */
      }
      return prevOpen.call(window, url, name, specs);
    };
    try {
      return fn();
    } finally {
      window.open = prevOpen;
    }
  }

  function launch() {
    if (!state.ready || !state.sdkReady || !window.FB) {
      showResult({ ok: false, error: "sdk_or_config_not_ready" });
      return;
    }
    state.dialogRedirectUri = null;
    state.spawnPageUri = window.location.origin + window.location.pathname;
    completing = false;
    state.session = {
      waba_id: null,
      phone_number_id: null,
      business_id: null,
      event: null,
    };
    setText("cnes-result-status", "Opening Meta Embedded Signup…");
    withDialogUriCapture(function () {
      window.FB.login(
        function (response) {
          if (response && response.authResponse && response.authResponse.code) {
            state.code = String(response.authResponse.code);
            setText(
              "cnes-result-status",
              "Authorization code captured (not logged). Completing…"
            );
            maybeComplete();
            var tries = 0;
            var timer = setInterval(function () {
              tries += 1;
              if (!state.code) {
                clearInterval(timer);
                return;
              }
              if (state.session.waba_id && state.session.phone_number_id) {
                clearInterval(timer);
                maybeComplete();
              } else if (tries >= 20) {
                clearInterval(timer);
                setText(
                  "cnes-result-status",
                  "Session IDs missing — attempting WABA phone lookup fallback…"
                );
                completing = true;
                completeOnServer({ allowWabaPhoneFallback: true });
              }
            }, 500);
            return;
          }
          showResult({
            ok: false,
            error: "fb_login_no_code",
            status: response && response.status ? response.status : null,
          });
        },
        {
          config_id: state.configurationId,
          response_type: "code",
          override_default_response_type: true,
          extras: { setup: {}, sessionInfoVersion: "3" },
        }
      );
    });
  }

  function init() {
    listenSession();
    fetch("/admin/api/whatsapp/control-number-es/config", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (body) {
        state.appId = body.app_id || null;
        state.configurationId = body.configuration_id || null;
        state.ready = !!body.ready;
        setText("cnes-app-id", state.appId || "missing");
        setText("cnes-config-id", state.configurationId || "missing");
        setText(
          "cnes-secret",
          body.app_secret_configured ? "configured (server-only)" : "MISSING"
        );
        setText("cnes-ready", state.ready ? "yes" : "no");
        setText(
          "cnes-config-status",
          state.ready
            ? "Config ready — isolated control path (production env IDs untouched)"
            : "Config incomplete — check Railway META_WHATSAPP_* secrets"
        );

        if (!state.appId || !state.configurationId) {
          setText("cnes-sdk-status", "Facebook SDK: blocked (missing config)");
          return;
        }

        loadFacebookSdk(state.appId, body.fb_sdk_version, function (err) {
          if (err) {
            setText("cnes-sdk-status", "Facebook SDK: failed to load");
            showResult({ ok: false, error: "sdk_load_failed" });
            return;
          }
          state.sdkReady = true;
          setText("cnes-sdk-status", "Facebook SDK: ready (FB.init ok)");
          var btn = $("cnes-launch");
          if (btn && state.ready) btn.disabled = false;
        });
      })
      .catch(function () {
        setText("cnes-config-status", "Failed to load control ES config");
        showResult({ ok: false, error: "config_fetch_failed" });
      });

    var launchBtn = $("cnes-launch");
    if (launchBtn) launchBtn.addEventListener("click", launch);
  }

  // Expose normalize for potential future display checks (unused = ok).
  window.CARTFLOW_CONTROL_ES_NORMALIZE = normalizeE164;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
