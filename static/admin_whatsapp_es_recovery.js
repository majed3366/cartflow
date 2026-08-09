/**
 * CartFlow — Admin Embedded Signup Recovery (Phase 2B).
 * Loads FB SDK, launches ES with config_id, posts code to server.
 * Never logs tokens. Never calls /register.
 */
(function () {
  "use strict";

  var cfg = window.CARTFLOW_ES_RECOVERY || {};
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
    setText("esr-result-status", obj && obj.ok ? "SUCCESS — Phase 2B complete (STOP before /register)" : "Result updated");
    var pre = $("esr-result-json");
    if (pre) {
      try {
        pre.textContent = JSON.stringify(obj || {}, null, 2);
      } catch (e) {
        pre.textContent = "{}";
      }
    }
  }

  function redactClientPayload(payload) {
    var copy = Object.assign({}, payload || {});
    if (copy.code) copy.code = "[redacted]";
    return copy;
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
      // TEMPORARY SAFE DIAGNOSTICS (Phase 2B session-event audit) — no secrets / no PII values.
      try {
        var diag = safeMessageDiag(event);
        pushDiag(diag);
        // Surface latest non-secret diag line for operator (not tokens/codes).
        if (diag && diag.keep) {
          setText(
            "esr-session-status",
            "Diag: origin=" +
              (diag.origin || "?") +
              " dataType=" +
              (diag.dataType || "?") +
              " type=" +
              (diag.type || "(none)") +
              " event=" +
              (diag.eventName || "(none)") +
              " keys=" +
              ((diag.topKeys || []).join(",") || "(none)")
          );
        }
      } catch (eDiag) {
        /* ignore diag failures */
      }

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
        "esr-session-status",
        "Session: " +
          (state.session.event || "event") +
          " waba=" +
          (state.session.waba_id || "?") +
          " phone=" +
          (state.session.phone_number_id || "?")
      );

      // Hard client-side pre-check (server still asserts).
      if (
        state.session.waba_id &&
        state.session.waba_id !== cfg.targetWabaId
      ) {
        showResult({
          ok: false,
          aborted: true,
          error: "client_waba_mismatch",
          waba_id: state.session.waba_id,
          expected: cfg.targetWabaId,
        });
        return;
      }
      if (
        state.session.phone_number_id &&
        state.session.phone_number_id !== cfg.targetPhoneNumberId
      ) {
        showResult({
          ok: false,
          aborted: true,
          error: "client_phone_mismatch",
          phone_number_id: state.session.phone_number_id,
          expected: cfg.targetPhoneNumberId,
        });
      }
    });
  }

  var messageDiag = [];

  function pushDiag(entry) {
    if (!entry) return;
    messageDiag.push(entry);
    if (messageDiag.length > 40) messageDiag.shift();
  }

  function safeMessageDiag(event) {
    var origin = typeof event.origin === "string" ? event.origin : "";
    var raw = event.data;
    var dataType = raw === null ? "null" : typeof raw;
    var parsed = null;
    var parseOk = false;
    if (dataType === "string") {
      try {
        parsed = JSON.parse(raw);
        parseOk = true;
        dataType = "string->object";
      } catch (e) {
        parseOk = false;
      }
    } else if (dataType === "object" && raw) {
      parsed = raw;
      parseOk = true;
    }

    var topKeys = [];
    var nestedKeys = [];
    var type = null;
    var eventName = null;
    var keep = false;
    if (parseOk && parsed && typeof parsed === "object") {
      topKeys = Object.keys(parsed).slice(0, 20);
      type = parsed.type != null ? String(parsed.type) : null;
      eventName = parsed.event != null ? String(parsed.event) : null;
      if (parsed.data && typeof parsed.data === "object") {
        nestedKeys = Object.keys(parsed.data).slice(0, 20);
      }
      // Keep facebook-ish or WA-ish messages; skip noisy non-FB noise lightly.
      keep =
        origin.indexOf("facebook.com") !== -1 ||
        type === "WA_EMBEDDED_SIGNUP" ||
        (topKeys && topKeys.length > 0 && origin.indexOf("facebook") !== -1);
    } else if (origin.indexOf("facebook.com") !== -1) {
      keep = true;
    }

    return {
      at: Date.now(),
      origin: origin.slice(0, 120),
      dataType: dataType,
      parseOk: parseOk,
      type: type,
      eventName: eventName,
      topKeys: topKeys,
      nestedKeys: nestedKeys,
      // booleans only — never values of ids/tokens
      hasWabaKey: nestedKeys.indexOf("waba_id") !== -1,
      hasPhoneKey: nestedKeys.indexOf("phone_number_id") !== -1,
      originAllowsFacebookSubstring: origin.indexOf("facebook.com") !== -1,
      wouldAcceptType: type === "WA_EMBEDDED_SIGNUP",
      keep: keep,
    };
  }

  var completing = false;

  function maybeComplete() {
    if (completing) return;
    if (!state.code) return;
    if (!state.session.waba_id || !state.session.phone_number_id) {
      setText(
        "esr-result-status",
        "Authorization code received — waiting for WA_EMBEDDED_SIGNUP session IDs…"
      );
      return;
    }
    completing = true;
    completeOnServer();
  }

  function completeOnServer(opts) {
    opts = opts || {};
    var allowFallback = !!opts.allowSharedWabaFallback;
    setText(
      "esr-result-status",
      allowFallback
        ? "Exchanging code + resolving shared WABA on server…"
        : "Exchanging authorization code on server…"
    );
    var payload = {
      code: state.code,
      waba_id: state.session.waba_id || "",
      phone_number_id: state.session.phone_number_id || "",
      business_id: state.session.business_id || "",
      session_event: state.session.event || "",
      allow_shared_waba_fallback: allowFallback,
      dialog_redirect_uri: state.dialogRedirectUri || "",
      spawn_page_uri: state.spawnPageUri || "",
    };
    fetch("/admin/api/whatsapp/embedded-signup-recovery/complete", {
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
        // Never keep code in memory after attempt.
        state.code = null;
        var body = res.body || { ok: false, http_status: res.status };
        if (!body.ok && allowFallback) {
          body.message_diagnostics = messageDiag.slice(-20);
          body.client = redactClientPayload({
            code: "present",
            session: state.session,
          });
        }
        showResult(body);
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
      if (ru) {
        // Meta may pass redirect_uri URL-encoded once; keep decoded form from URLSearchParams.
        state.dialogRedirectUri = ru;
      }
      var fallback = u.searchParams.get("fallback_redirect_uri");
      if (fallback && !state.dialogRedirectUri) {
        state.dialogRedirectUri = fallback;
      }
    } catch (e) {
      /* ignore parse failures */
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
    state.spawnPageUri =
      window.location.origin + window.location.pathname;
    setText("esr-result-status", "Opening Meta Embedded Signup…");
    withDialogUriCapture(function () {
      window.FB.login(
        function (response) {
          if (response && response.authResponse && response.authResponse.code) {
            state.code = String(response.authResponse.code);
            setText(
              "esr-result-status",
              "Authorization code captured (not logged). Completing…"
            );
            maybeComplete();
            // Retry briefly if session message arrives after code.
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
                // Session IDs still missing — keep listener, try server shared-WABA fallback.
                setText(
                  "esr-result-status",
                  "Session IDs missing — attempting server shared-WABA fallback…"
                );
                completing = true;
                completeOnServer({ allowSharedWabaFallback: true });
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
    fetch("/admin/api/whatsapp/embedded-signup-recovery/config", {
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
        setText("esr-app-id", state.appId || "missing");
        setText("esr-config-id", state.configurationId || "missing");
        setText(
          "esr-secret",
          body.app_secret_configured ? "configured (server-only)" : "MISSING"
        );
        setText("esr-ready", state.ready ? "yes" : "no");
        setText(
          "esr-config-status",
          state.ready
            ? "Config ready — App ID + Configuration ID + App Secret present"
            : "Config incomplete — check Railway META_WHATSAPP_* secrets"
        );

        if (!state.appId || !state.configurationId) {
          setText("esr-sdk-status", "Facebook SDK: blocked (missing config)");
          return;
        }

        loadFacebookSdk(state.appId, body.fb_sdk_version, function (err) {
          if (err) {
            setText("esr-sdk-status", "Facebook SDK: failed to load");
            showResult({ ok: false, error: "sdk_load_failed" });
            return;
          }
          state.sdkReady = true;
          setText("esr-sdk-status", "Facebook SDK: ready (FB.init ok)");
          var btn = $("esr-launch");
          if (btn && state.ready) btn.disabled = false;
        });
      })
      .catch(function () {
        setText("esr-config-status", "Failed to load recovery config");
        showResult({ ok: false, error: "config_fetch_failed" });
      });

    var launchBtn = $("esr-launch");
    if (launchBtn) launchBtn.addEventListener("click", launch);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
