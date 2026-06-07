(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = byId("awv-status");
    if (el) el.textContent = msg || "";
  }

  function loadRows() {
    var q = (byId("awv-search") && byId("awv-search").value) || "";
    setStatus("جاري التحميل…");
    fetch("/api/admin/whatsapp/stores?q=" + encodeURIComponent(q), {
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
          (row.connection_status_ar || "—") +
          "</td>" +
          "<td class='py-2 pe-3' dir='ltr'>" +
          (row.vip_destination_ar || "—") +
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
    loadRows();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
