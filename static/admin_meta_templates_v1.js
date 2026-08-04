/* Meta Template Operations V1 — Admin → WhatsApp */
(function () {
  "use strict";

  var creating = false;
  var lastCanCreate = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var el = byId(id);
    if (el) el.textContent = value != null && value !== "" ? String(value) : "—";
  }

  function setCreateEnabled(enabled) {
    var btn = byId("awm-tpl-create");
    if (!btn) return;
    btn.disabled = !enabled || creating;
  }

  function hideModal() {
    var m = byId("awm-tpl-confirm-modal");
    if (m) m.classList.add("hidden");
  }

  function showModal() {
    var m = byId("awm-tpl-confirm-modal");
    if (m) m.classList.remove("hidden");
  }

  function applyStatus(data) {
    if (!data) {
      setText("awm-tpl-status", "تعذّر تحميل حالة القالب");
      setCreateEnabled(false);
      return;
    }
    var conn =
      data.meta_connection_ok === true
        ? "متصل"
        : data.credential_configured === false
          ? "بيانات الاعتماد ناقصة"
          : data.waba_configured === false
            ? "WABA ناقص"
            : "غير مؤكد";
    setText("awm-tpl-meta-conn", conn);
    setText("awm-tpl-waba", data.waba_masked);
    setText("awm-tpl-name", data.template_name || "cartflow_cart_reminder_ar_v1");
    var lc = data.local_contract || {};
    setText(
      "awm-tpl-local",
      (lc.category || "MARKETING") + " · " + (lc.language || "ar") + " · BODY + BUTTONS"
    );
    setText("awm-tpl-meta-status", data.status);
    setText("awm-tpl-category", data.category);
    setText("awm-tpl-language", data.language);
    setText("awm-tpl-comparison", data.comparison);
    setText("awm-tpl-checked", data.checked_at);
    if (data.error_message_safe || data.error_code) {
      setText(
        "awm-tpl-error",
        String(data.error_message_safe || data.error_code) +
          (data.trace_id ? " · trace " + data.trace_id : "")
      );
    } else {
      setText("awm-tpl-error", "—");
    }
    var bodyEl = byId("awm-tpl-body-preview");
    if (bodyEl && lc.body_text) {
      bodyEl.textContent = lc.body_text;
    }
    lastCanCreate = data.can_create === true && data.ok !== false;
    if (data.exists === true) {
      lastCanCreate = false;
    }
    if (data.credential_configured === false || data.waba_configured === false) {
      lastCanCreate = false;
    }
    setCreateEnabled(lastCanCreate);
    if (data.ok) {
      setText(
        "awm-tpl-status",
        "تم التحديث · " + String(data.status || "—") + " · " + String(data.comparison || "—")
      );
    } else {
      setText(
        "awm-tpl-status",
        "تعذّر التحديث: " + String(data.error_message_safe || data.error_code || "error")
      );
    }
  }

  function loadRecoveryContractStatus() {
    setText("awm-tpl-status", "جاري التحقق من قالب الاسترجاع…");
    fetch("/admin/api/whatsapp/meta-templates/recovery-contract", {
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(applyStatus)
      .catch(function () {
        setText("awm-tpl-status", "خطأ في الشبكة أثناء التحقق من القالب");
        setCreateEnabled(false);
      });
  }

  function submitCreate() {
    if (creating || !lastCanCreate) return;
    creating = true;
    setCreateEnabled(false);
    setText("awm-tpl-status", "جاري إنشاء القالب في Meta…");
    hideModal();
    fetch("/admin/api/whatsapp/meta-templates/recovery-contract/create", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirm: true,
        template_name: "cartflow_cart_reminder_ar_v1",
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        creating = false;
        applyStatus(data);
        if (data && data.ok) {
          setText(
            "awm-tpl-status",
            "تم قبول الإنشاء من Graph · الحالة " +
              String(data.status || "PENDING") +
              " (ليست موافقة نهائية)"
          );
        }
        loadRecoveryContractStatus();
      })
      .catch(function () {
        creating = false;
        setText("awm-tpl-status", "خطأ في الشبكة أثناء الإنشاء");
        setCreateEnabled(lastCanCreate);
      });
  }

  function bind() {
    var refresh = byId("awm-tpl-refresh");
    if (refresh) refresh.addEventListener("click", loadRecoveryContractStatus);
    var createBtn = byId("awm-tpl-create");
    if (createBtn) {
      createBtn.addEventListener("click", function () {
        if (creating || !lastCanCreate) return;
        showModal();
      });
    }
    var yes = byId("awm-tpl-confirm-yes");
    if (yes) yes.addEventListener("click", submitCreate);
    var no = byId("awm-tpl-confirm-no");
    if (no) no.addEventListener("click", hideModal);
    loadRecoveryContractStatus();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
