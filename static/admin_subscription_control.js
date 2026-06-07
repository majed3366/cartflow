(function () {
  "use strict";

  var selectedId = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = byId("asc-status");
    if (el) el.textContent = msg || "";
  }

  function loadRows() {
    var q = (byId("asc-search") && byId("asc-search").value) || "";
    setStatus("جاري التحميل…");
    fetch("/api/admin/subscriptions?q=" + encodeURIComponent(q), {
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) {
          setStatus("تعذّر تحميل القائمة");
          return;
        }
        renderRows(data.rows || []);
        setStatus("عدد السجلات: " + (data.rows || []).length);
      })
      .catch(function () {
        setStatus("خطأ في الشبكة");
      });
  }

  function renderRows(rows) {
    var tbody = byId("asc-rows");
    if (!tbody) return;
    tbody.innerHTML = rows
      .map(function (row) {
        return (
          "<tr class='border-b border-slate-100'>" +
          "<td class='py-2 pe-3'>" +
          (row.store_name || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.merchant_email || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.current_plan_label || row.current_plan) +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.plan_status_label || row.plan_status) +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.plan_source || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.trial_expires_at_ar || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.plan_expires_at_ar || "—") +
          "</td>" +
          "<td class='py-2 pe-3'>" +
          (row.updated_at_ar || "—") +
          "</td>" +
          "<td class='py-2'><button type='button' class='text-indigo-700 underline asc-edit' data-id='" +
          row.merchant_user_id +
          "' data-label='" +
          (row.merchant_email || "") +
          "'>تعديل</button></td>" +
          "</tr>"
        );
      })
      .join("");
    tbody.querySelectorAll(".asc-edit").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openPanel(btn.getAttribute("data-id"), btn.getAttribute("data-label"));
      });
    });
  }

  function openPanel(id, label) {
    selectedId = id;
    var panel = byId("asc-action-panel");
    if (panel) panel.hidden = false;
    var merchantLabel = byId("asc-action-merchant");
    if (merchantLabel) merchantLabel.textContent = label || id;
    var hid = byId("asc-merchant-id");
    if (hid) hid.value = id;
    var msg = byId("asc-action-msg");
    if (msg) msg.textContent = "";
    var audit = byId("asc-audit-out");
    if (audit) audit.classList.add("hidden");
  }

  function setInputValue(id, t) {
    var el = byId(id);
    if (el) el.value = t != null ? String(t) : "";
  }

  function submitAction(ev) {
    ev.preventDefault();
    if (!selectedId) return;
    var payload = {
      action: byId("asc-action").value,
      plan: byId("asc-plan").value,
      reason: byId("asc-reason").value,
      trial_days: parseInt(byId("asc-trial-days").value, 10) || 14,
      extend_days: parseInt(byId("asc-extend-days").value, 10) || 7,
    };
    var exp = byId("asc-plan-expires").value;
    if (exp) payload.plan_expires_at = exp;
    fetch("/api/admin/subscriptions/" + encodeURIComponent(selectedId) + "/action", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var msg = byId("asc-action-msg");
        if (msg) {
          msg.textContent = data.ok
            ? "تم التطبيق — audit #" + (data.audit_log_id || "—")
            : "فشل: " + (data.message || "unknown");
          msg.className = "mt-3 text-sm " + (data.ok ? "text-emerald-700" : "text-rose-700");
        }
        if (data.ok) loadRows();
      });
  }

  function loadAudit() {
    if (!selectedId) return;
    fetch("/api/admin/subscriptions/" + encodeURIComponent(selectedId) + "/audit", {
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var pre = byId("asc-audit-out");
        if (!pre) return;
        pre.classList.remove("hidden");
        pre.textContent = JSON.stringify(data.audit_logs || [], null, 2);
      });
  }

  function bind() {
    var refresh = byId("asc-refresh");
    if (refresh) refresh.addEventListener("click", loadRows);
    var form = byId("asc-action-form");
    if (form) form.addEventListener("submit", submitAction);
    var auditBtn = byId("asc-audit-btn");
    if (auditBtn) auditBtn.addEventListener("click", loadAudit);
    loadRows();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
