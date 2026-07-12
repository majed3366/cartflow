/**
 * Cart Workspace Merchant Experience V1 — flag-gated surface.
 * Fetches projection, paints via RenderController, dispatches commands.
 * No ownership/admission logic in this file.
 */
(function (global) {
  "use strict";

  var COMMAND_MAP = {
    approve_discount: "approve_discount",
    reject_exception: "reject_exception",
    provide_information: "provide_information",
    fix_channel_configuration: "fix_channel_configuration",
    take_over_conversation: "take_over_conversation",
    dismiss_with_reason: "dismiss_with_reason",
    return_to_cartflow: "return_to_cartflow",
    approve_next_step: "return_to_cartflow",
    approve_or_deny_discount: "approve_discount",
    override_decision_action: "take_over_conversation",
    provide_confirm_phone: "provide_information",
    judgment_action: "return_to_cartflow",
    recovery_action: "return_to_cartflow",
  };

  function host() {
    return document.getElementById("cw-merchant-host");
  }

  function statusEl() {
    return document.getElementById("cw-merchant-status");
  }

  function setStatus(t) {
    var el = statusEl();
    if (el) el.textContent = t || "";
  }

  function paint(projection) {
    var ctrl = global.CartWorkspaceRenderControllerV1;
    var h = host();
    if (!ctrl || !h) return;
    var result = ctrl.applyProjection(h, projection);
    setStatus(
      result.painted
        ? "تم التحديث · الإصدار " + (projection && projection.projection_version)
        : "بدون إعادة رسم · نفس الإصدار"
    );
  }

  function fetchProjection() {
    return fetch("/api/cart-workspace/v1/projection", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok || !data.ok) {
          throw new Error((data && data.error) || "projection_failed");
        }
        return data.projection;
      });
    });
  }

  function load() {
    setStatus("جاري التحميل…");
    return fetchProjection()
      .then(function (proj) {
        if (global.CartWorkspaceRenderControllerV1) {
          global.CartWorkspaceRenderControllerV1.resetForTests();
        }
        paint(proj);
      })
      .catch(function (e) {
        setStatus("تعذر التحميل: " + e.message);
      });
  }

  function postCommand(decisionId, requiredActionOrCommand) {
    var commandType =
      COMMAND_MAP[requiredActionOrCommand] || requiredActionOrCommand;
    var commandId =
      "cw-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    return fetch("/api/cart-workspace/v1/commands", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        decision_id: decisionId,
        command_type: commandType,
        command_id: commandId,
      }),
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok || !data.ok) {
          throw new Error((data && data.error) || "command_failed");
        }
        return data;
      });
    });
  }

  function onClick(ev) {
    var btn = ev.target && ev.target.closest
      ? ev.target.closest("[data-cw-command]")
      : null;
    if (!btn) return;
    var decisionId = btn.getAttribute("data-decision-id");
    var cmd = btn.getAttribute("data-cw-command");
    if (!decisionId || !cmd) return;
    btn.disabled = true;
    setStatus("جاري تنفيذ القرار…");
    postCommand(decisionId, cmd)
      .then(function (data) {
        if (data.projection) {
          paint(data.projection);
          if (data.calm_recovery) {
            setStatus("تمت إعادة المتابعة لـ CartFlow.");
          }
        } else {
          return load();
        }
      })
      .catch(function (e) {
        setStatus("فشل التنفيذ: " + e.message);
        btn.disabled = false;
      });
  }

  function seedDemo() {
    return fetch("/api/cart-workspace/v1/demo-seed", {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data.ok) throw new Error(data.error || "seed_failed");
        if (global.CartWorkspaceRenderControllerV1) {
          global.CartWorkspaceRenderControllerV1.resetForTests();
        }
        paint(data.projection);
        setStatus("تم تجهيز أمثلة للفهم الداخلي.");
      })
      .catch(function (e) {
        setStatus("تعذر التجهيز: " + e.message);
      });
  }

  function bind() {
    var h = host();
    if (h && !h._cwBound) {
      h.addEventListener("click", onClick);
      h._cwBound = true;
    }
    var refresh = document.getElementById("cw-merchant-refresh");
    if (refresh) refresh.onclick = function () {
      load();
    };
    var seed = document.getElementById("cw-merchant-seed");
    if (seed) seed.onclick = function () {
      seedDemo();
    };
  }

  function initIfActive() {
    var page = document.getElementById("page-workspace");
    if (!page) return;
    bind();
    if (page.classList.contains("active")) load();
  }

  global.CartWorkspaceMerchantV1 = {
    load: load,
    seedDemo: seedDemo,
    paint: paint,
    initIfActive: initIfActive,
  };

  document.addEventListener("DOMContentLoaded", function () {
    bind();
  });
})(typeof window !== "undefined" ? window : globalThis);
