/* Merchant dashboard — WhatsApp settings read/save via /api/recovery-settings */
(function () {
  "use strict";

  var bound = false;
  var loading = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function setBoxVisible(el, on) {
    if (!el) return;
    el.style.display = on ? "" : "none";
  }

  function showErr(msg) {
    var el = byId("ma-wa-settings-err");
    var ok = byId("ma-wa-settings-ok");
    setBoxVisible(ok, false);
    if (el) {
      el.textContent = msg || "تعذّر الحفظ";
      setBoxVisible(el, true);
    }
  }

  function showOk() {
    var el = byId("ma-wa-settings-err");
    var ok = byId("ma-wa-settings-ok");
    setBoxVisible(el, false);
    setBoxVisible(ok, true);
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-wa-settings-err"), false);
    setBoxVisible(byId("ma-wa-settings-ok"), false);
  }

  function setReadOnly(d) {
    if (!d) return;
    var st = byId("ma-wa-status-display");
    if (st) st.textContent = d.whatsapp_status_display || "—";
    var ls = byId("ma-wa-last-send-status");
    if (ls) ls.textContent = d.last_send_status_ar || "—";
    var at = byId("ma-wa-last-send");
    if (at) {
      var t = d.last_send_at_ar || "";
      if (t && t !== "—") at.textContent = t;
    }
    var hint = byId("ma-wa-provider-hint");
    if (hint) hint.textContent = d.whatsapp_provider_mode_hint_ar || "";
  }

  function fillForm(d) {
    if (!d) return;
    var num = byId("ma-wa-store-number");
    if (num) num.value = d.store_whatsapp_number || "";
    var en = byId("ma-wa-recovery-enabled");
    if (en) en.checked = d.whatsapp_recovery_enabled !== false;
    var mode = byId("ma-wa-provider-mode");
    if (mode) {
      var m = (d.whatsapp_provider_mode || "sandbox").toString().toLowerCase();
      if (m !== "sandbox" && m !== "test" && m !== "production") m = "sandbox";
      mode.value = m;
    }
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
    var btn = byId("ma-wa-settings-save");
    if (btn) btn.disabled = true;
    var body = {
      store_whatsapp_number: (byId("ma-wa-store-number") && byId("ma-wa-store-number").value) || "",
      whatsapp_recovery_enabled: !!(
        byId("ma-wa-recovery-enabled") && byId("ma-wa-recovery-enabled").checked
      ),
      whatsapp_provider_mode:
        (byId("ma-wa-provider-mode") && byId("ma-wa-provider-mode").value) || "sandbox",
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
    var form = byId("ma-wa-settings-form");
    if (!form) return;
    bound = true;
    form.addEventListener("submit", onSubmit);
    var mode = byId("ma-wa-provider-mode");
    if (mode) {
      mode.addEventListener("change", function () {
        var hint = byId("ma-wa-provider-hint");
        if (!hint) return;
        var v = mode.value;
        if (v === "sandbox") {
          hint.textContent = "وضع تجربة — مناسب للاختبار وليس للإنتاج";
        } else if (v === "production") {
          hint.textContent = "";
        } else {
          hint.textContent = "وضع اختبار";
        }
      });
    }
  }

  window.maInitWhatsappSettingsPage = function () {
    bindOnce();
    loadSettings();
  };
})();
