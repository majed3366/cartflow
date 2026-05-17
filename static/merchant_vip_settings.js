/* Merchant dashboard — VIP preferences via /api/recovery-settings */
(function () {
  "use strict";

  var bound = false;
  var loading = false;
  var DEFAULT_THRESHOLD = 500;

  function byId(id) {
    return document.getElementById(id);
  }

  function setBoxVisible(el, on) {
    if (!el) return;
    el.style.display = on ? "" : "none";
  }

  function showErr(msg) {
    setBoxVisible(byId("ma-vip-settings-ok"), false);
    var el = byId("ma-vip-settings-err");
    if (el) {
      el.textContent = msg || "تعذّر الحفظ";
      setBoxVisible(el, true);
    }
  }

  function showOk() {
    setBoxVisible(byId("ma-vip-settings-err"), false);
    setBoxVisible(byId("ma-vip-settings-ok"), true);
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-vip-settings-err"), false);
    setBoxVisible(byId("ma-vip-settings-ok"), false);
  }

  function setReadOnly(d) {
    if (!d) return;
    var st = byId("ma-vip-status-display");
    if (st) st.textContent = d.vip_status_display_ar || "—";
    var th = byId("ma-vip-threshold-display");
    if (th) th.textContent = d.vip_threshold_display_ar || "—";
    var lc = byId("ma-vip-last-cart");
    if (lc) {
      var cart = d.last_vip_cart_ar || "—";
      var at = d.last_vip_cart_at_ar || "";
      lc.textContent =
        cart !== "—" && at && at !== "—" ? cart + " — " + at : cart;
    }
    var la = byId("ma-vip-last-alert");
    if (la) {
      var alert = d.last_vip_alert_ar || "—";
      var at2 = d.last_vip_alert_at_ar || "";
      la.textContent =
        alert !== "—" && at2 && at2 !== "—" ? alert + " — " + at2 : alert;
    }
  }

  function fillForm(d) {
    if (!d) return;
    var en = byId("ma-vip-enabled");
    if (en) en.checked = d.vip_enabled !== false;
    var th = byId("ma-vip-threshold");
    if (th) {
      var n = parseInt(d.vip_cart_threshold, 10);
      th.value =
        typeof n === "number" && isFinite(n) && n >= 1
          ? String(n)
          : String(DEFAULT_THRESHOLD);
    }
    var nt = byId("ma-vip-notify-enabled");
    if (nt) nt.checked = d.vip_notify_enabled !== false;
    var note = byId("ma-vip-note");
    if (note) note.value = d.vip_note || "";
    setReadOnly(d);
  }

  function loadSettings() {
    if (loading) return Promise.resolve();
    loading = true;
    hideMsgs();
    return fetch("/api/recovery-settings")
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (x.data && x.data.ok) fillForm(x.data);
        else showErr((x.data && x.data.error) || "تعذّر تحميل الإعدادات");
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء التحميل");
      })
      .finally(function () {
        loading = false;
      });
  }

  function onSubmit(e) {
    e.preventDefault();
    hideMsgs();
    var btn = byId("ma-vip-settings-save");
    if (btn) btn.disabled = true;
    var rawTh = parseInt(byId("ma-vip-threshold") && byId("ma-vip-threshold").value, 10);
    var threshold =
      typeof rawTh === "number" && isFinite(rawTh) && rawTh >= 1
        ? rawTh
        : DEFAULT_THRESHOLD;
    var body = {
      vip_enabled: !!(byId("ma-vip-enabled") && byId("ma-vip-enabled").checked),
      vip_cart_threshold: threshold,
      vip_notify_enabled: !!(
        byId("ma-vip-notify-enabled") && byId("ma-vip-notify-enabled").checked
      ),
      vip_note: (byId("ma-vip-note") && byId("ma-vip-note").value) || "",
    };
    fetch("/api/recovery-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (x.data && x.data.ok) {
          fillForm(x.data);
          showOk();
        } else {
          showErr((x.data && x.data.error) || "فشل الحفظ");
        }
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء الحفظ");
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function bindOnce() {
    if (bound) return;
    var form = byId("ma-vip-settings-form");
    if (!form) return;
    bound = true;
    form.addEventListener("submit", onSubmit);
  }

  window.maInitVipSettingsPage = function () {
    bindOnce();
    loadSettings();
  };
})();
