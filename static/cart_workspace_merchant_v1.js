/**
 * Cart Workspace Merchant Experience V1 — Decision-First surface.
 * Fetches projection, paints via RenderController, dispatches commands.
 * VIP "تتابعه أنت الآن" is presentation-only session state (no projection change).
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

  var FOLLOWING_KEY = "cw_following_vip_v1";

  function host() {
    return document.getElementById("cw-merchant-host");
  }

  function statusEl() {
    return document.getElementById("cw-merchant-status");
  }

  function setStatus(t, isError) {
    var el = statusEl();
    if (!el) return;
    var msg = t || "";
    el.textContent = msg;
    el.hidden = !msg;
    el.classList.toggle("cw-status--error", !!isError && !!msg);
  }

  function storeSlug() {
    return String(global.CARTFLOW_STORE_SLUG || "default");
  }

  function readFollowing() {
    try {
      var raw = sessionStorage.getItem(FOLLOWING_KEY + ":" + storeSlug());
      var list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function writeFollowing(list) {
    try {
      sessionStorage.setItem(
        FOLLOWING_KEY + ":" + storeSlug(),
        JSON.stringify(list || [])
      );
    } catch (e) {
      /* ignore quota */
    }
  }

  function getFollowingVip() {
    return readFollowing();
  }

  function upsertFollowing(card) {
    if (!card || !card.decision_id) return;
    var list = readFollowing().filter(function (c) {
      return c.decision_id !== card.decision_id;
    });
    list.unshift({
      decision_id: card.decision_id,
      recovery_key: card.recovery_key,
      store_slug: card.store_slug,
      decision_class: card.decision_class || "override",
      required_action: "return_to_cartflow",
      override_mode: "active",
      action_label_ar: card.action_label_ar,
      explanation: card.explanation,
      status: "following",
    });
    writeFollowing(list);
  }

  function removeFollowing(decisionId) {
    writeFollowing(
      readFollowing().filter(function (c) {
        return c.decision_id !== decisionId;
      })
    );
  }

  function findCardInProjection(projection, decisionId) {
    if (!projection) return null;
    var pools = []
      .concat(projection.zone_a || [])
      .concat(projection.zone_b || []);
    for (var i = 0; i < pools.length; i++) {
      if (pools[i] && pools[i].decision_id === decisionId) return pools[i];
    }
    return null;
  }

  function paint(projection) {
    var ctrl = global.CartWorkspaceRenderControllerV1;
    var h = host();
    if (!ctrl || !h) return;
    ctrl.applyProjection(h, projection);
    setStatus("");
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
    setStatus("");
    return fetchProjection()
      .then(function (proj) {
        if (global.CartWorkspaceRenderControllerV1) {
          global.CartWorkspaceRenderControllerV1.resetForTests();
        }
        paint(proj);
      })
      .catch(function (e) {
        setStatus("تعذر التحميل. حاول مرة أخرى.", true);
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
    var detailsToggle = ev.target && ev.target.closest
      ? ev.target.closest("summary")
      : null;
    if (detailsToggle) return;

    var btn = ev.target && ev.target.closest
      ? ev.target.closest("[data-cw-command]")
      : null;
    if (!btn) return;
    var decisionId = btn.getAttribute("data-decision-id");
    var cmd = btn.getAttribute("data-cw-command");
    var isFollowingBtn = btn.getAttribute("data-cw-following") === "1";
    if (!decisionId || !cmd) return;
    btn.disabled = true;

    var last = global.CartWorkspaceRenderControllerV1
      ? global.CartWorkspaceRenderControllerV1.getLastProjection()
      : null;
    var cardSnap = findCardInProjection(last, decisionId);
    if (!cardSnap && isFollowingBtn) {
      cardSnap = readFollowing().filter(function (c) {
        return c.decision_id === decisionId;
      })[0];
    }

    var mapped = COMMAND_MAP[cmd] || cmd;
    var isVipTakeOver =
      mapped === "take_over_conversation" &&
      cardSnap &&
      (cardSnap.decision_class === "override" ||
        cardSnap.override_mode === "active");

    postCommand(decisionId, cmd)
      .then(function (data) {
        if (isVipTakeOver && cardSnap) {
          upsertFollowing(cardSnap);
        }
        if (mapped === "return_to_cartflow") {
          removeFollowing(decisionId);
        }
        if (data.projection) {
          if (global.CartWorkspaceRenderControllerV1) {
            global.CartWorkspaceRenderControllerV1.resetForTests();
          }
          paint(data.projection);
        } else {
          return load();
        }
      })
      .catch(function (e) {
        setStatus("تعذر تنفيذ القرار. حاول مرة أخرى.", true);
        btn.disabled = false;
      });
  }

  function bind() {
    var h = host();
    if (h && !h._cwBound) {
      h.addEventListener("click", onClick);
      h._cwBound = true;
    }
  }

  function initIfActive() {
    var page = document.getElementById("page-workspace");
    if (!page) return;
    bind();
    if (page.classList.contains("active")) load();
  }

  global.CartWorkspaceMerchantV1 = {
    load: load,
    paint: paint,
    initIfActive: initIfActive,
    getFollowingVip: getFollowingVip,
    upsertFollowing: upsertFollowing,
    removeFollowing: removeFollowing,
  };

  document.addEventListener("DOMContentLoaded", function () {
    bind();
  });
})(typeof window !== "undefined" ? window : globalThis);
