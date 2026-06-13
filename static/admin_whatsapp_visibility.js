(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(id, msg) {
    var el = byId(id);
    if (el) el.textContent = msg || "";
  }

  function setMetaField(id, value) {
    var el = byId(id);
    if (el) el.textContent = value != null && value !== "" ? String(value) : "—";
  }

  function loadMetaStatus() {
    setStatus("awm-meta-status", "جاري التحقق من Meta…");
    fetch("/admin/api/whatsapp/meta-status", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || data.ok !== true) {
          setStatus("awm-meta-status", "تعذّر التحقق من Meta");
          return;
        }
        setMetaField(
          "awm-meta-connected",
          data.connected ? "متصل — نجح الاتصال" : "غير متصل"
        );
        setMetaField("awm-meta-phone", data.display_phone_number);
        setMetaField("awm-meta-verified-name", data.verified_name);
        setMetaField("awm-meta-waba", data.waba_id);
        setMetaField("awm-meta-phone-id", data.phone_number_id);
        var resultParts = [];
        if (data.meta_response_ok) {
          resultParts.push("Meta Graph OK");
        } else {
          resultParts.push("Meta Graph فشل");
        }
        if (data.error) {
          resultParts.push(String(data.error));
        }
        if (data.verified_at) {
          resultParts.push(data.verified_at);
        }
        setMetaField("awm-meta-last-result", resultParts.join(" · "));
        if (data.error) {
          setStatus(
            "awm-meta-status",
            "فشل التحقق من Meta: " + String(data.error)
          );
        } else if (data.connected) {
          setStatus(
            "awm-meta-status",
            "تم التحقق — CartFlow يتواصل مع Meta بنجاح."
          );
        } else {
          setStatus(
            "awm-meta-status",
            "التحقق لم يؤكد اتصالاً ناجحاً."
          );
        }
      })
      .catch(function () {
        setStatus("awm-meta-status", "خطأ في الشبكة أثناء التحقق من Meta");
      });
  }

  function sendMetaTestMessage() {
    var toInput = byId("awm-meta-send-to");
    var to = (toInput && toInput.value) ? String(toInput.value).trim() : "";
    if (!to) {
      setStatus("awm-meta-send-status", "أدخل رقم الهاتف.");
      return;
    }
    setStatus("awm-meta-send-status", "جاري الإرسال عبر Meta…");
    setMetaField("awm-meta-send-result", "—");
    setMetaField("awm-meta-send-message-id", "—");
    fetch("/admin/api/whatsapp/meta-send-test", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to: to }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) {
          setStatus("awm-meta-send-status", "تعذّر إرسال الرسالة التجريبية");
          return;
        }
        if (data.ok) {
          if (data.meta_response) {
            setMetaField(
              "awm-meta-send-result",
              "نجح الإرسال · " + JSON.stringify(data.meta_response)
            );
          } else {
            setMetaField("awm-meta-send-result", "نجح الإرسال");
          }
          setMetaField("awm-meta-send-message-id", data.message_id);
          setStatus(
            "awm-meta-send-status",
            "تم إرسال hello_world بنجاح عبر Meta."
          );
        } else {
          setMetaField("awm-meta-send-result", "فشل الإرسال");
          setMetaField("awm-meta-send-message-id", data.message_id || "—");
          setStatus(
            "awm-meta-send-status",
            data.error ? "فشل الإرسال: " + String(data.error) : "فشل الإرسال"
          );
        }
      })
      .catch(function () {
        setStatus("awm-meta-send-status", "خطأ في الشبكة أثناء الإرسال");
      });
  }

  function loadRegistry() {
    setStatus("awt-registry-status", "جاري التحميل…");
    fetch("/api/admin/whatsapp/templates", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) {
          setStatus("awt-registry-status", "تعذّر تحميل السجل");
          return;
        }
        renderRegistry(data.rows || []);
        setStatus("awt-registry-status", "عدد القوالب: " + (data.rows || []).length);
      })
      .catch(function () {
        setStatus("awt-registry-status", "خطأ في الشبكة");
      });
  }

  function renderRegistry(rows) {
    var tbody = byId("awt-registry-rows");
    if (!tbody) return;
    tbody.innerHTML = rows
      .map(function (row) {
        return (
          "<tr class='border-b border-slate-100'>" +
          "<td class='py-2 pe-3' dir='ltr'>" +
          (row.template_key || "—") +
          "</td>" +
          "<td class='py-2 pe-3' dir='ltr'>" +
          (row.reason_tag || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.enabled ? "نعم" : "لا") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.default_or_customized_ar || "افتراضي") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.future_meta_status_ar || row.future_meta_status || "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function loadStoreTemplates() {
    var q = (byId("awt-store-search") && byId("awt-store-search").value) || "";
    setStatus("awt-store-status", "جاري التحميل…");
    fetch("/api/admin/whatsapp/store-templates?q=" + encodeURIComponent(q), {
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) {
          setStatus("awt-store-status", "تعذّر تحميل القائمة");
          return;
        }
        renderStoreRows(data.rows || []);
        setStatus("awt-store-status", "عدد السجلات: " + (data.rows || []).length);
      })
      .catch(function () {
        setStatus("awt-store-status", "خطأ في الشبكة");
      });
  }

  function renderStoreRows(rows) {
    var tbody = byId("awt-store-rows");
    if (!tbody) return;
    tbody.innerHTML = rows
      .map(function (row) {
        return (
          "<tr class='border-b border-slate-100'>" +
          "<td class='py-2 pe-3'>" +
          (row.store_name || row.store_slug || "—") +
          "</td>" +
          "<td class='py-2 pe-3' dir='ltr'>" +
          (row.template_key || "—") +
          "</td>" +
          "<td class='py-2 pe-3' dir='ltr'>" +
          (row.reason_tag || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.enabled ? "نعم" : "لا") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.default_or_customized_ar || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.future_meta_status_ar || row.future_meta_status || "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function loadRows() {
    var q = (byId("awv-search") && byId("awv-search").value) || "";
    setStatus("awv-status", "جاري التحميل…");
    fetch("/api/admin/whatsapp/stores?q=" + encodeURIComponent(q), {
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) {
          setStatus("awv-status", "تعذّر تحميل القائمة");
          return;
        }
        renderRows(data.rows || []);
        setStatus("awv-status", "عدد السجلات: " + (data.rows || []).length);
      })
      .catch(function () {
        setStatus("awv-status", "خطأ في الشبكة");
      });
  }

  function renderRows(rows) {
    var tbody = byId("awv-rows");
    if (!tbody) return;
    tbody.innerHTML = rows
      .map(function (row) {
        return (
          "<tr class='border-b border-slate-100'>" +
          "<td class='py-2 pe-3'>" +
          (row.store_name || row.store_slug || "—") +
          "<div class='text-xs text-slate-400'>" +
          (row.merchant_email || "—") +
          "</div></td>" +
          "<td class='py-2 pe-3'>" +
          (row.whatsapp_mode_label || row.whatsapp_mode || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.whatsapp_onboarding_journey_ar || row.whatsapp_onboarding_journey || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.whatsapp_onboarding_journey_status_ar ||
            row.whatsapp_onboarding_journey_status ||
            "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.connection_state_ar || row.connection_status_ar || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.readiness_state_ar || row.readiness_state || "—") +
          "</td>" +
          "<td class='py-2 pe-3 text-xs'>" +
          ((row.missing_requirements_ar || []).slice(0, 2).join(" · ") || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.last_validation_status_ar || "—") +
          " · " +
          (row.last_validation_ar || "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function bind() {
    var refresh = byId("awv-refresh");
    if (refresh) refresh.addEventListener("click", loadRows);
    var storeRefresh = byId("awt-store-refresh");
    if (storeRefresh) storeRefresh.addEventListener("click", loadStoreTemplates);
    var metaRefresh = byId("awm-meta-refresh");
    if (metaRefresh) metaRefresh.addEventListener("click", loadMetaStatus);
    var metaSendBtn = byId("awm-meta-send-btn");
    if (metaSendBtn) metaSendBtn.addEventListener("click", sendMetaTestMessage);
    loadMetaStatus();
    loadRegistry();
    loadStoreTemplates();
    loadRows();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
