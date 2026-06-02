/* Merchant dashboard — store platform connection (Zid OAuth) */
(function () {
  "use strict";

  var bound = false;
  var loading = false;
  var lastPayload = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function setBoxVisible(el, on) {
    if (!el) return;
    el.style.display = on ? "" : "none";
  }

  function showErr(msg) {
    setBoxVisible(byId("ma-store-connection-ok"), false);
    var el = byId("ma-store-connection-err");
    if (el) {
      el.textContent = msg || "تعذّر إكمال العملية";
      setBoxVisible(el, true);
    }
  }

  function showOk(msg) {
    setBoxVisible(byId("ma-store-connection-err"), false);
    var el = byId("ma-store-connection-ok");
    if (el) {
      el.textContent = msg || "تم بنجاح";
      setBoxVisible(el, true);
    }
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-store-connection-err"), false);
    setBoxVisible(byId("ma-store-connection-ok"), false);
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) el.textContent = t == null ? "" : String(t);
  }

  function applyStatus(d) {
    if (!d) return;
    lastPayload = d;
    var connected = !!d.connected;
    var pill = byId("ma-sc-status-pill");
    if (pill) {
      pill.textContent = d.status_label_ar || (connected ? "تم الربط" : "غير مربوط");
      pill.classList.toggle("is-connected", connected);
      pill.classList.toggle("is-disconnected", !connected);
    }
    setText("ma-sc-status-desc", connected ? "" : d.status_description_ar || "");
    var desc = byId("ma-sc-status-desc");
    if (desc) desc.style.display = connected ? "none" : "";

    var meta = byId("ma-sc-connected-meta");
    if (meta) meta.hidden = !connected;
    if (connected) {
      setText("ma-sc-store-name", d.store_name || "—");
      setText("ma-sc-platform", d.platform_ar || "—");
      setText("ma-sc-connected-at", d.connected_at_ar || "—");
      setText(
        "ma-sc-store-connected-check",
        d.store_connected_ok ? "✅" : "—"
      );
      var wPill = byId("ma-sc-widget-pill");
      if (wPill) {
        var wStatus = (d.widget_installation_status || "").toLowerCase();
        wPill.textContent = d.widget_status_label_ar || "—";
        wPill.classList.remove(
          "is-widget-installed",
          "is-widget-installing",
          "is-widget-failed",
          "is-widget-unsupported"
        );
        if (d.widget_installed_ok || wStatus === "installed") {
          wPill.classList.add("is-widget-installed");
        } else if (wStatus === "installing" || wStatus === "pending_partner_snippet") {
          wPill.classList.add("is-widget-installing");
        } else if (wStatus === "failed") {
          wPill.classList.add("is-widget-failed");
        } else if (wStatus === "unsupported") {
          wPill.classList.add("is-widget-unsupported");
        }
      }
      var wDesc = byId("ma-sc-widget-desc");
      if (wDesc) {
        var wCopy = (d.widget_status_description_ar || "").trim();
        wDesc.textContent = wCopy;
        wDesc.hidden = !wCopy;
      }
    } else {
      setText("ma-sc-store-connected-check", "—");
      var wPillOff = byId("ma-sc-widget-pill");
      if (wPillOff) wPillOff.textContent = "—";
      var wDescOff = byId("ma-sc-widget-desc");
      if (wDescOff) {
        wDescOff.textContent = "";
        wDescOff.hidden = true;
      }
    }

    var notConn = byId("ma-sc-actions-not-connected");
    var conn = byId("ma-sc-actions-connected");
    if (notConn) notConn.hidden = connected;
    if (conn) conn.hidden = !connected;
  }

  function pendingMessage() {
    return (
      (lastPayload && lastPayload.pending_setup_message_ar) ||
      "ميزة الربط قيد الإعداد"
    );
  }

  function startZidConnect() {
    if (!lastPayload || !lastPayload.zid_connect_available) {
      showErr(pendingMessage());
      return;
    }
    var url = lastPayload.zid_connect_url || "/api/merchant/store-connection/zid/connect";
    window.location.href = url;
  }

  function onSallaClick() {
    showErr(pendingMessage());
  }

  function disconnectStore() {
    if (!window.confirm("هل تريد فصل ربط المتجر؟ لن يُحذف حسابك.")) return;
    hideMsgs();
    fetch("/api/merchant/store-connection/disconnect", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (x.data && x.data.ok) {
          showOk(x.data.message_ar || "تم فصل الربط");
          return loadStatus(true);
        }
        showErr((x.data && x.data.message_ar) || "تعذّر فصل الربط");
      })
      .catch(function () {
        showErr("خطأ في الشبكة");
      });
  }

  function loadStatus(force) {
    if (loading && !force) return Promise.resolve();
    loading = true;
    hideMsgs();
    return fetch("/api/merchant/store-connection", { credentials: "same-origin" })
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (x.status === 401) {
          showErr("يلزم تسجيل الدخول.");
          return;
        }
        if (x.data && x.data.ok && x.data.store_connection) {
          applyStatus(x.data.store_connection);
        } else {
          showErr("تعذّر تحميل حالة الربط");
        }
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء التحميل");
      })
      .finally(function () {
        loading = false;
      });
  }

  function checkHashFlash() {
    var h = (location.hash || "").toLowerCase();
    var qs = "";
    var qi = (location.hash || "").indexOf("?");
    if (qi >= 0) qs = (location.hash || "").slice(qi + 1);
    var params = qs ? new URLSearchParams(qs) : null;
    if (params && params.get("store_connected") === "1") {
      showOk("تم ربط متجرك بنجاح.");
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", "#settings");
      } else {
        location.hash = "#settings";
      }
    } else if (params && params.get("store_connect_pending") === "1") {
      showErr(pendingMessage());
      location.hash = "#settings";
    } else if (params && params.get("store_connect_error") === "1") {
      showErr("تعذّر بدء الربط. حاول مرة أخرى.");
      location.hash = "#settings";
    }
  }

  function bindOnce() {
    if (bound) return;
    var root = byId("ma-store-connection-root");
    if (!root) return;
    bound = true;
    var zid = byId("ma-sc-connect-zid");
    var reconnect = byId("ma-sc-reconnect-zid");
    var salla = byId("ma-sc-connect-salla");
    var disc = byId("ma-sc-disconnect");
    if (zid) zid.addEventListener("click", startZidConnect);
    if (reconnect) reconnect.addEventListener("click", startZidConnect);
    if (salla) salla.addEventListener("click", onSallaClick);
    if (disc) disc.addEventListener("click", disconnectStore);
  }

  window.maInitStoreConnectionPage = function () {
    bindOnce();
    checkHashFlash();
    loadStatus(true);
  };
})();
