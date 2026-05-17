/* Merchant dashboard — VIP preferences via /api/recovery-settings */
(function () {
  "use strict";

  var bound = false;
  var loadedOnce = false;
  var saving = false;
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
    var ok = byId("ma-vip-settings-ok");
    if (ok) {
      ok.textContent = "تم حفظ إعدادات السلال المهمة";
      setBoxVisible(ok, true);
    }
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-vip-settings-err"), false);
    setBoxVisible(byId("ma-vip-settings-ok"), false);
  }

  function parseThresholdInput() {
    var el = byId("ma-vip-threshold");
    if (!el) return { ok: false, error: "حقل العتبة غير متوفر" };
    var raw = String(el.value == null ? "" : el.value).trim();
    if (!raw) {
      return { ok: false, error: "أدخل قيمة السلة المهمة (رقم موجب)" };
    }
    var n = parseInt(raw, 10);
    if (!isFinite(n) || n < 1) {
      return { ok: false, error: "قيمة السلة المهمة يجب أن تكون رقماً موجباً (مثل 300 أو 1000)" };
    }
    return { ok: true, value: n };
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

  function thresholdFromApi(d) {
    var n = parseInt(d && d.vip_cart_threshold, 10);
    if (typeof n === "number" && isFinite(n) && n >= 1) return n;
    return null;
  }

  function fillForm(d) {
    if (!d) return;
    var en = byId("ma-vip-enabled");
    if (en) en.checked = d.vip_enabled !== false;
    var th = byId("ma-vip-threshold");
    if (th) {
      var saved = thresholdFromApi(d);
      th.value = saved != null ? String(saved) : String(DEFAULT_THRESHOLD);
      th.placeholder = String(DEFAULT_THRESHOLD);
    }
    var nt = byId("ma-vip-notify-enabled");
    if (nt) nt.checked = d.vip_notify_enabled !== false;
    var note = byId("ma-vip-note");
    if (note) note.value = d.vip_note != null ? String(d.vip_note) : "";
    setReadOnly(d);
  }

  function collectSaveBody() {
    var th = parseThresholdInput();
    if (!th.ok) return th;
    return {
      ok: true,
      body: {
        vip_enabled: !!(byId("ma-vip-enabled") && byId("ma-vip-enabled").checked),
        vip_cart_threshold: th.value,
        vip_notify_enabled: !!(
          byId("ma-vip-notify-enabled") && byId("ma-vip-notify-enabled").checked
        ),
        vip_note:
          byId("ma-vip-note") && byId("ma-vip-note").value != null
            ? String(byId("ma-vip-note").value)
            : "",
        merchant_settings_scope: "vip",
      },
    };
  }

  function loadSettings(force) {
    if (!force && loadedOnce) return Promise.resolve();
    hideMsgs();
    return fetch("/api/recovery-settings", { credentials: "same-origin" })
      .then(function (r) {
        return r.json().then(function (d) {
          return { status: r.status, data: d };
        });
      })
      .then(function (x) {
        if (x.data && x.data.ok) {
          fillForm(x.data);
          loadedOnce = true;
        } else {
          showErr((x.data && x.data.error) || "تعذّر تحميل الإعدادات");
        }
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء التحميل");
      });
  }

  function onSubmit(e) {
    e.preventDefault();
    if (saving) return;
    hideMsgs();
    var collected = collectSaveBody();
    if (!collected.ok) {
      showErr(collected.error);
      return;
    }
    var body = collected.body;
    var btn = byId("ma-vip-settings-save");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "جاري الحفظ…";
    }
    saving = true;
    fetch("/api/recovery-settings", {
      method: "POST",
      credentials: "same-origin",
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
        saving = false;
        if (btn) {
          btn.disabled = false;
          btn.textContent = "حفظ إعدادات السلال المهمة";
        }
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
    var modeReady =
      window.maVipAutomation && typeof window.maVipAutomation.ensureModeLoaded === "function"
        ? window.maVipAutomation.ensureModeLoaded()
        : Promise.resolve();
    modeReady.then(function () {
      if (window.maVipAutomation) {
        window.maVipAutomation.rerenderFromCache();
      }
    });
    loadSettings(false);
  };

  window.maReloadVipSettingsPage = function () {
    loadSettings(true);
  };
})();
