/* Merchant dashboard — general operational preferences via /api/recovery-settings */
(function () {
  "use strict";

  var bound = false;
  var loadedOnce = false;
  var saving = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function setBoxVisible(el, on) {
    if (!el) return;
    el.style.display = on ? "" : "none";
  }

  function showErr(msg) {
    setBoxVisible(byId("ma-general-settings-ok"), false);
    var el = byId("ma-general-settings-err");
    if (el) {
      el.textContent = msg || "تعذّر الحفظ";
      setBoxVisible(el, true);
    }
  }

  function showOk() {
    setBoxVisible(byId("ma-general-settings-err"), false);
    var ok = byId("ma-general-settings-ok");
    if (ok) {
      ok.textContent = "تم حفظ الإعدادات";
      setBoxVisible(ok, true);
    }
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-general-settings-err"), false);
    setBoxVisible(byId("ma-general-settings-ok"), false);
  }

  function setRadio(name, val) {
    var q = document.querySelector(
      'input[name="' + name + '"][value="' + val + '"]'
    );
    if (q) q.checked = true;
  }

  function getRadio(name) {
    var q = document.querySelector('input[name="' + name + '"]:checked');
    return q ? q.value : null;
  }

  function setReadOnly(d) {
    if (!d) return;
    setText("ma-general-mode-display", d.merchant_automation_mode_ar || "—");
    setText(
      "ma-general-notify-display",
      d.settings_notifications_summary_ar || "—"
    );
    setText("ma-general-widget-name-display", d.settings_widget_name_display_ar || "—");
    setText("ma-general-updated-display", d.settings_updated_at_ar || "—");
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) el.textContent = t == null ? "" : String(t);
  }

  function fillForm(d) {
    if (!d) return;
    setCk("ma-general-notify-vip", d.settings_notify_vip !== false);
    setCk("ma-general-notify-recovery", d.settings_notify_recovery_success !== false);
    setCk("ma-general-notify-wa-fail", d.settings_notify_whatsapp_failure !== false);
    setCk("ma-general-widget-enabled", d.widget_enabled !== false);
    var name = byId("ma-general-widget-name");
    if (name) name.value = d.widget_display_name != null ? String(d.widget_display_name) : "";
    var mode = d.merchant_automation_mode || "manual";
    setRadio("merchant_automation_mode", mode);
    setReadOnly(d);
  }

  function setCk(id, on) {
    var el = byId(id);
    if (el) el.checked = !!on;
  }

  function collectSaveBody() {
    return {
      settings_notify_vip: !!(
        byId("ma-general-notify-vip") && byId("ma-general-notify-vip").checked
      ),
      settings_notify_recovery_success: !!(
        byId("ma-general-notify-recovery") &&
        byId("ma-general-notify-recovery").checked
      ),
      settings_notify_whatsapp_failure: !!(
        byId("ma-general-notify-wa-fail") && byId("ma-general-notify-wa-fail").checked
      ),
      widget_enabled: !!(
        byId("ma-general-widget-enabled") && byId("ma-general-widget-enabled").checked
      ),
      widget_display_name:
        byId("ma-general-widget-name") && byId("ma-general-widget-name").value != null
          ? String(byId("ma-general-widget-name").value)
          : "",
      merchant_automation_mode:
        getRadio("merchant_automation_mode") || "manual",
      merchant_settings_scope: "general",
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
    var body = collectSaveBody();
    var btn = byId("ma-general-settings-save");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "جاري الحفظ...";
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
          if (window.maVipAutomation && x.data.merchant_automation_mode) {
            window.maVipAutomation.setMode(x.data.merchant_automation_mode);
            window.maVipAutomation.rerenderFromCache();
          }
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
          btn.textContent = "حفظ الإعدادات";
        }
      });
  }

  function bindOnce() {
    if (bound) return;
    var form = byId("ma-general-settings-form");
    if (!form) return;
    bound = true;
    form.addEventListener("submit", onSubmit);
  }

  window.maInitGeneralSettingsPage = function () {
    bindOnce();
    loadSettings(true);
  };
})();
