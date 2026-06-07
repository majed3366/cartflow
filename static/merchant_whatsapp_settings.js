/* Merchant dashboard — WhatsApp mode UX (read/save via /api/recovery-settings) */
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

  function selectedWhatsappMode() {
    var managed = byId("ma-wa-mode-managed");
    if (managed && managed.checked) return "cartflow_managed";
    return "merchant_whatsapp";
  }

  function applyConnectionPill(d) {
    var pill = byId("ma-wa-connection-pill");
    if (!pill || !d) return;
    var label = d.whatsapp_customer_connection_status_ar || "غير متصل";
    var key = d.whatsapp_customer_connection_status || "not_connected";
    pill.textContent = label;
    pill.className = "ma-wa-connection-pill is-" + key;
    var summary = byId("ma-wa-connection-summary");
    if (summary) {
      summary.textContent = d.whatsapp_connection_summary_ar || d.whatsapp_status_display || "—";
    }
    var cta = byId("ma-wa-enable-recovery-btn");
    if (cta) {
      cta.hidden = d.whatsapp_recovery_enabled !== false && key !== "not_connected";
    }
  }

  function setReadOnly(d) {
    if (!d) return;
    applyConnectionPill(d);
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
    var desc = byId("ma-wa-mode-desc");
    if (desc) desc.textContent = d.whatsapp_mode_description_ar || desc.textContent;
  }

  function fillForm(d) {
    if (!d) return;
    var num = byId("ma-wa-store-number");
    if (num) num.value = d.store_whatsapp_number || "";
    var en = byId("ma-wa-recovery-enabled");
    if (en) en.checked = d.whatsapp_recovery_enabled !== false;
    var mode = (d.whatsapp_mode || "cartflow_managed").toString().toLowerCase();
    var managed = byId("ma-wa-mode-managed");
    var merchant = byId("ma-wa-mode-merchant");
    if (managed) managed.checked = mode !== "merchant_whatsapp";
    if (merchant) merchant.checked = mode === "merchant_whatsapp";
    var provider = byId("ma-wa-provider-mode");
    if (provider) {
      var m = (d.whatsapp_provider_mode || "sandbox").toString().toLowerCase();
      if (m !== "sandbox" && m !== "test" && m !== "production") m = "sandbox";
      provider.value = m;
    }
    setReadOnly(d);
  }

  function buildSaveBody(extra) {
    extra = extra || {};
    return {
      store_whatsapp_number: (byId("ma-wa-store-number") && byId("ma-wa-store-number").value) || "",
      whatsapp_recovery_enabled:
        extra.whatsapp_recovery_enabled != null
          ? !!extra.whatsapp_recovery_enabled
          : !!(byId("ma-wa-recovery-enabled") && byId("ma-wa-recovery-enabled").checked),
      whatsapp_mode: extra.whatsapp_mode || selectedWhatsappMode(),
      whatsapp_provider_mode:
        (byId("ma-wa-provider-mode") && byId("ma-wa-provider-mode").value) || "sandbox",
    };
  }

  function postSettings(body) {
    return fetch("/api/recovery-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) {
        return { status: r.status, data: d };
      });
    });
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
    postSettings(buildSaveBody())
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

  function onEnableRecovery() {
    hideMsgs();
    var btn = byId("ma-wa-enable-recovery-btn");
    if (btn) btn.disabled = true;
    postSettings(buildSaveBody({ whatsapp_recovery_enabled: true }))
      .then(function (x) {
        if (x.data && x.data.ok) {
          fillForm(x.data);
          showOk();
        } else {
          showErr((x.data && x.data.error) || "فشل التفعيل");
        }
      })
      .catch(function () {
        showErr("خطأ في الشبكة أثناء التفعيل");
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
    var enableBtn = byId("ma-wa-enable-recovery-btn");
    if (enableBtn) enableBtn.addEventListener("click", onEnableRecovery);
    var modeRadios = form.querySelectorAll('input[name="whatsapp_mode"]');
    modeRadios.forEach(function (radio) {
      radio.addEventListener("change", function () {
        var managed = selectedWhatsappMode() === "cartflow_managed";
        var desc = byId("ma-wa-mode-desc");
        if (desc) {
          desc.textContent = managed
            ? "CartFlow يتولى رسائل العملاء — أنت تضبط سلوك الاسترجاع فقط."
            : "رسائل العملاء من بنية واتساب تخص متجرك — للمتاجر المتقدمة.";
        }
      });
    });
    var provider = byId("ma-wa-provider-mode");
    if (provider) {
      provider.addEventListener("change", function () {
        var hint = byId("ma-wa-provider-hint");
        if (!hint) return;
        var v = provider.value;
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
