/**
 * Storefront Cart Bridge Core (v1) — validate, dedupe, POST /api/cart-event.
 *
 * Only this module posts cart persistence payloads. Adapters read; triggers
 * orchestrate widget display separately via CartBridge (legacy path).
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var Contract = Cf.StorefrontCartBridgeContract || {};

  var bridgeState = {
    last_adapter: null,
    last_read_source: null,
    last_normalized: null,
    last_post_key: null,
    last_post_at: null,
    last_post_ok: null,
    last_post_status: null,
    last_skip_reason: null,
    last_error: null,
    cart_persisted: false,
    reason_orphan_risk: false,
    in_flight: false,
  };

  var lastDedupeKey = "";
  var lastDedupeAt = 0;
  var DEDUPE_MS = 2500;
  var inFlightPromise = null;
  var RETRY_DELAYS_MS = [500, 1200, 2500];
  var emptyRetryGeneration = 0;

  function isEmptyValidationResult(v) {
    if (!v || v.ok) {
      return false;
    }
    var errs = v.errors || [];
    return (
      errs.indexOf("empty_cart_value") >= 0 ||
      errs.indexOf("empty_item_count") >= 0
    );
  }

  function isAddFlowReason(opts) {
    return String(opts.reason || "add").toLowerCase() === "add";
  }

  function isPriorityAddTrigger(opts) {
    if (opts && opts.allowFreshAfterInFlight) {
      return true;
    }
    var h = String((opts && (opts.source_hint || opts.trigger)) || "");
    return /post_items|cart_sources|zid_network_hook|empty_retry|early_click/i.test(
      h
    );
  }

  function logRetryStop(reason, meta) {
    blog("[CF CART BRIDGE RETRY STOP]", Object.assign({ reason: reason }, meta || {}));
  }

  function scheduleEmptyRetries(opts, attempt) {
    attempt = attempt || 0;
    if (bridgeState.cart_persisted) {
      logRetryStop("already_persisted");
      return;
    }
    if (attempt >= RETRY_DELAYS_MS.length) {
      logRetryStop("max_attempts", { attempts: attempt });
      return;
    }
    var gen = emptyRetryGeneration;
    var delay = RETRY_DELAYS_MS[attempt];
    blog("[CF CART BRIDGE RETRY SCHEDULED]", {
      attempt: attempt + 1,
      delay_ms: delay,
      trigger: opts.source_hint || null,
    });
    setTimeout(function () {
      if (gen !== emptyRetryGeneration) {
        return;
      }
      if (bridgeState.cart_persisted) {
        logRetryStop("already_persisted");
        return;
      }
      blog("[CF CART BRIDGE RETRY FIRED]", {
        attempt: attempt + 1,
        delay_ms: delay,
      });
      readAndPersist({
        reason: "add",
        force: true,
        source_hint: opts.source_hint || "empty_retry",
        retryAttempt: attempt + 1,
        allowFreshAfterInFlight: true,
        _freshRun: true,
      });
    }, delay);
  }

  function cancelEmptyRetries() {
    emptyRetryGeneration += 1;
  }

  function blog(tag, meta) {
    try {
      if (meta !== undefined && meta !== null) {
        console.log(tag, meta);
      } else {
        console.log(tag);
      }
    } catch (eL) {}
  }

  function apiBase() {
    try {
      if (Cf.Api && typeof Cf.Api.apiBase === "function") {
        return Cf.Api.apiBase();
      }
    } catch (eA) {}
    try {
      if (window.CARTFLOW_API_BASE) {
        return String(window.CARTFLOW_API_BASE).replace(/\/+$/, "");
      }
    } catch (eB) {}
    return "";
  }

  function cartEventUrl() {
    var b = apiBase();
    return b ? b + "/api/cart-event" : "/api/cart-event";
  }

  function selectAdapter() {
    var Adapters = Cf.StorefrontCartAdapters;
    if (!Adapters || typeof Adapters.select !== "function") {
      return null;
    }
    return Adapters.select();
  }

  function validateAndNormalize(raw) {
    if (Contract.validateNormalizedCart) {
      return Contract.validateNormalizedCart(raw);
    }
    return { ok: false, errors: ["contract_missing"], cart: null };
  }

  function shouldSkipDedupe(cart, force) {
    if (force) {
      return false;
    }
    var key = Contract.dedupeKey ? Contract.dedupeKey(cart) : "";
    var now = Date.now();
    if (key && key === lastDedupeKey && now - lastDedupeAt < DEDUPE_MS) {
      return true;
    }
    return false;
  }

  function markDedupe(cart) {
    lastDedupeKey = Contract.dedupeKey ? Contract.dedupeKey(cart) : "";
    lastDedupeAt = Date.now();
  }

  function postCartEvent(cart, reason) {
    var payload = Contract.toCartEventPayload
      ? Contract.toCartEventPayload(cart, reason)
      : null;
    if (!payload) {
      bridgeState.last_error = "payload_build_failed";
      blog("[CF CART BRIDGE ERROR]", { error: bridgeState.last_error });
      return Promise.resolve({ ok: false, error: "payload_build_failed" });
    }
    blog("[CF CART BRIDGE POST]", {
      store_slug: cart.store_slug,
      session_id: cart.session_id,
      cart_id: cart.cart_id,
      cart_value: cart.cart_value,
      item_count: cart.item_count,
      source: cart.source,
      reason: payload.reason,
    });
    return fetch(cartEventUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        bridgeState.last_post_status = r.status;
        return r
          .json()
          .catch(function () {
            return {};
          })
          .then(function (body) {
            var ok = r.ok && body && body.ok !== false;
            bridgeState.last_post_ok = ok;
            if (ok) {
              bridgeState.cart_persisted = true;
              bridgeState.reason_orphan_risk = false;
              cancelEmptyRetries();
              try {
                if (
                  Cf.Triggers &&
                  typeof Cf.Triggers.onStorefrontCartPersisted === "function"
                ) {
                  Cf.Triggers.onStorefrontCartPersisted(cart);
                }
              } catch (eTrigPersist) {}
            }
            return { ok: ok, status: r.status, body: body };
          });
      })
      .catch(function (err) {
        bridgeState.last_post_ok = false;
        bridgeState.last_error = String(err || "post_failed");
        blog("[CF CART BRIDGE ERROR]", { error: bridgeState.last_error });
        return { ok: false, error: bridgeState.last_error };
      });
  }

  /**
   * Read cart via platform adapter, validate, dedupe, POST.
   * @param {Object} opts reason, force, source_hint, retryAttempt
   */
  function readAndPersistOnce(opts) {
    opts = opts || {};
    var adapter = selectAdapter();
    if (!adapter || typeof adapter.readCart !== "function") {
      bridgeState.last_skip_reason = "no_adapter";
      blog("[CF CART BRIDGE SKIP]", { reason: bridgeState.last_skip_reason });
      return Promise.resolve({ ok: false, skipped: true, reason: "no_adapter" });
    }
    bridgeState.last_adapter = adapter.sourceName || adapter.platform || null;
    blog("[CF CART BRIDGE ADAPTER]", {
      adapter: bridgeState.last_adapter,
      sourceName: adapter.sourceName,
    });

    return adapter
      .readCart()
      .then(function (raw) {
        bridgeState.last_read_source = raw && raw.source ? raw.source : null;
        blog("[CF CART BRIDGE READ]", {
          adapter: bridgeState.last_adapter,
          source: bridgeState.last_read_source,
          has_raw: !!raw,
        });
        if (!raw) {
          bridgeState.last_skip_reason = "cart_read_empty";
          blog("[CF CART BRIDGE SKIP]", { reason: bridgeState.last_skip_reason });
          if (isAddFlowReason(opts)) {
            scheduleEmptyRetries(opts, opts.retryAttempt || 0);
          }
          return { ok: false, skipped: true, reason: "cart_read_empty" };
        }
        var normalized =
          typeof adapter.normalize === "function"
            ? adapter.normalize(raw) || raw
            : raw;
        var v = validateAndNormalize(normalized);
        try {
          console.log("[CF CART BRIDGE TIMING]", {
            step: "validateNormalizedCart",
            timestamp: Date.now(),
            ok: v.ok,
            errors: v.errors || [],
            cart_value: v.cart ? v.cart.cart_value : null,
            item_count: v.cart ? v.cart.item_count : null,
            source: v.cart ? v.cart.source : null,
          });
        } catch (eVal) {}
        if (!v.ok) {
          bridgeState.last_skip_reason = v.errors.join(",");
          bridgeState.last_normalized = v.cart;
          blog("[CF CART BRIDGE SKIP]", {
            reason: bridgeState.last_skip_reason,
            errors: v.errors,
          });
          if (isEmptyValidationResult(v) && isAddFlowReason(opts)) {
            scheduleEmptyRetries(opts, opts.retryAttempt || 0);
          }
          return { ok: false, skipped: true, reason: bridgeState.last_skip_reason };
        }
        bridgeState.last_normalized = v.cart;
        blog("[CF CART BRIDGE NORMALIZED]", {
          platform: v.cart.platform,
          store_slug: v.cart.store_slug,
          session_id: v.cart.session_id,
          cart_id: v.cart.cart_id,
          cart_token: v.cart.cart_token,
          cart_value: v.cart.cart_value,
          item_count: v.cart.item_count,
          source: v.cart.source,
        });
        if (shouldSkipDedupe(v.cart, opts.force)) {
          bridgeState.last_skip_reason = "dedupe_unchanged";
          blog("[CF CART BRIDGE SKIP]", { reason: bridgeState.last_skip_reason });
          return {
            ok: bridgeState.cart_persisted,
            skipped: true,
            reason: "dedupe_unchanged",
          };
        }
        markDedupe(v.cart);
        bridgeState.last_post_key = Contract.dedupeKey
          ? Contract.dedupeKey(v.cart)
          : null;
        bridgeState.last_post_at = Date.now();
        return postCartEvent(v.cart, opts.reason || "add");
      });
  }

  function readAndPersist(opts) {
    opts = opts || {};
    try {
      console.log("[CF CART BRIDGE TIMING]", {
        step: "readAndPersist_start",
        timestamp: Date.now(),
        reason: opts.reason || "add",
        trigger: opts.source_hint || opts.trigger || null,
        in_flight: !!inFlightPromise,
        retry_attempt: opts.retryAttempt || 0,
      });
    } catch (eRp) {}
    if (inFlightPromise) {
      if (isPriorityAddTrigger(opts) && !opts._freshRun) {
        try {
          console.log("[CF CART BRIDGE TIMING]", {
            step: "readAndPersist_defer_after_inflight",
            timestamp: Date.now(),
            trigger: opts.source_hint || null,
          });
        } catch (eDef) {}
        return inFlightPromise.finally(function () {
          if (bridgeState.cart_persisted) {
            return { ok: true, persisted: true, already: true };
          }
          return readAndPersist(
            Object.assign({}, opts, {
              _freshRun: true,
              force: opts.force !== false,
            })
          );
        });
      }
      try {
        console.log("[CF CART BRIDGE TIMING]", {
          step: "readAndPersist_coalesced",
          timestamp: Date.now(),
          reason: opts.reason || "add",
          trigger: opts.source_hint || opts.trigger || null,
        });
      } catch (eCo) {}
      return inFlightPromise;
    }
    inFlightPromise = readAndPersistOnce(opts).finally(function () {
      inFlightPromise = null;
    });
    return inFlightPromise;
  }

  /** Called from trigger bridge after normalized cart signal (add/update). */
  function persistFromTrigger(evt) {
    evt = evt || {};
    var reason = "add";
    if (evt.event_type === "cart_empty" || evt.event_type === "cart_removed") {
      reason = "clear";
    }
    return readAndPersist({ reason: reason, source_hint: evt.detected_by, allowFreshAfterInFlight: true });
  }

  /**
   * Phase 6 / Fast Path V1: ensure cart truth before reason save — fail-fast.
   *
   * Must NOT await empty-retry ladders or in-flight cart-event POSTs on the
   * reason critical path (prod P50 wait was ~3391ms).
   *
   * Paths:
   * 1) cart_persisted → return immediately
   * 2) stable session (+ optional cart id / last normalized) → return immediately;
   *    schedule best-effort background persist (non-blocking) for durability
   * 3) no session → fail fast (caller shows retry); do not wait
   */
  function resolveStableSessionId() {
    try {
      if (Cf.Api && typeof Cf.Api.sessionId === "function") {
        var s = String(Cf.Api.sessionId() || "").trim();
        if (s) return s;
      }
    } catch (eSid) {}
    try {
      var ss = sessionStorage.getItem("cartflow_recovery_session_id");
      if (ss && String(ss).trim()) return String(ss).trim();
    } catch (eSs) {}
    return "";
  }

  function resolveStableCartId() {
    try {
      if (typeof window.cartflowGetStableCartEventIdForTracking === "function") {
        var c = String(window.cartflowGetStableCartEventIdForTracking() || "").trim();
        if (c) return c;
      }
    } catch (eCid) {}
    try {
      if (bridgeState.last_normalized && bridgeState.last_normalized.cart_id) {
        var c2 = String(bridgeState.last_normalized.cart_id || "").trim();
        if (c2) return c2;
      }
    } catch (eLn) {}
    return "";
  }

  function scheduleBackgroundPersistAfterReason() {
    /* Defer so reason POST can start first on the wire (connection contention). */
    window.setTimeout(function () {
      try {
        if (bridgeState.cart_persisted) {
          return;
        }
        readAndPersist({
          reason: "add",
          source_hint: "ensure_before_reason_bg",
          force: false,
          /* Intentionally NOT allowFreshAfterInFlight — coalesce, never chain-wait. */
        });
      } catch (eBg) {}
    }, 0);
  }

  function ensureCartTruthBeforeReason(opts) {
    opts = opts || {};
    var t0 =
      typeof performance !== "undefined" && performance.now
        ? performance.now()
        : Date.now();

    function done(payload) {
      var ms = Math.round(
        ((typeof performance !== "undefined" && performance.now
          ? performance.now()
          : Date.now()) -
          t0) *
          10
      ) / 10;
      try {
        console.log(
          "[CF BRIDGE ENSURE FAIL FAST]",
          Object.assign({ ms: ms }, payload || {})
        );
      } catch (eLog) {}
      return Promise.resolve(
        Object.assign(
          {
            skipped_wait: true,
            ms: ms,
          },
          payload || {}
        )
      );
    }

    if (bridgeState.cart_persisted && !opts.force) {
      return done({
        ok: true,
        persisted: true,
        already: true,
        fail_fast_path: "already_persisted",
        reason_orphan_risk: false,
      });
    }

    var sid = resolveStableSessionId();
    var cid = resolveStableCartId();
    var hasNormalized = !!(
      bridgeState.last_normalized &&
      (bridgeState.last_normalized.session_id || bridgeState.last_normalized.cart_id)
    );

    if (sid && (cid || hasNormalized || bridgeState.last_post_ok === true)) {
      /* Do NOT schedule cart-event here — it races the reason POST on the
         single uvicorn worker and re-inflates client TTFB (Fast Path V1.1).
         Flows call scheduleBackgroundPersistAfterReason after reason OK. */
      return done({
        ok: true,
        persisted: !!bridgeState.cart_persisted,
        fail_fast_path: "stable_identity_no_wait",
        session_id: sid,
        cart_id: cid || null,
        reason_orphan_risk: !bridgeState.cart_persisted,
        defer_cart_persist: !bridgeState.cart_persisted,
      });
    }

    if (sid) {
      /* Reason API scopes by store_slug + session_id — safe to persist reason now. */
      return done({
        ok: true,
        persisted: false,
        fail_fast_path: "session_only_no_wait",
        session_id: sid,
        reason_orphan_risk: true,
        defer_cart_persist: true,
      });
    }

    return done({
      ok: false,
      persisted: false,
      fail_fast_path: "missing_identity",
      reason_orphan_risk: true,
    });
  }

  function getDiagnostics() {
    return {
      adapter: bridgeState.last_adapter,
      read_source: bridgeState.last_read_source,
      normalized: bridgeState.last_normalized,
      last_post_key: bridgeState.last_post_key,
      last_post_at: bridgeState.last_post_at,
      last_post_ok: bridgeState.last_post_ok,
      last_post_status: bridgeState.last_post_status,
      last_skip_reason: bridgeState.last_skip_reason,
      last_error: bridgeState.last_error,
      cart_persisted: bridgeState.cart_persisted,
      reason_orphan_risk: bridgeState.reason_orphan_risk,
    };
  }

  function installZidNetworkHooks() {
    var Adapters = Cf.StorefrontCartAdapters;
    var zid = Adapters && Adapters.zid;
    if (!zid || !zid.canHandle || !zid.canHandle()) {
      return;
    }
    if (window.__cfStorefrontBridgeNetHook) {
      return;
    }
    window.__cfStorefrontBridgeNetHook = true;
    try {
      if (typeof window.fetch === "function") {
        var orig = window.fetch;
        window.fetch = function (input, init) {
          var url = typeof input === "string" ? input : input && input.url;
          var method =
            (init && init.method) ||
            (input && typeof input === "object" && input.method) ||
            "GET";
          var p = orig.apply(this, arguments);
          try {
            var u = String(url || "");
            if (/\/api\/v1\/cart\/items/i.test(u) && /POST/i.test(method)) {
              p.then(function (r) {
                if (!r.ok) {
                  return;
                }
                r.clone()
                  .json()
                  .then(function (body) {
                    try {
                      console.log("[CF CART BRIDGE TIMING]", {
                        step: "post_cart_items_hook",
                        timestamp: Date.now(),
                      });
                    } catch (ePi) {}
                    zid.cacheCartItemResponse(body);
                    readAndPersist({
                      reason: "add",
                      source_hint: "zid_network_hook_post_items",
                      allowFreshAfterInFlight: true,
                      force: true,
                    });
                  })
                  .catch(function () {});
              }).catch(function () {});
            } else if (/\/api\/v1\/cart(?:\?|$|\/)/i.test(u)) {
              p.then(function (r) {
                if (!r.ok) {
                  return;
                }
                r.clone()
                  .json()
                  .then(function (body) {
                    zid.cacheCartBody(body);
                    if (/POST|PUT|PATCH|DELETE/i.test(String(method || ""))) {
                      readAndPersist({ reason: "add" });
                    }
                  })
                  .catch(function () {});
              }).catch(function () {});
            }
          } catch (eHook) {}
          return p;
        };
      }
    } catch (eF) {}
  }

  Cf.StorefrontCartBridge = {
    readAndPersist: readAndPersist,
    persistFromTrigger: persistFromTrigger,
    ensureCartTruthBeforeReason: ensureCartTruthBeforeReason,
    scheduleBackgroundPersistAfterReason: scheduleBackgroundPersistAfterReason,
    getDiagnostics: getDiagnostics,
    installZidNetworkHooks: installZidNetworkHooks,
  };

  try {
    setTimeout(installZidNetworkHooks, 0);
  } catch (eStart) {}
})();
