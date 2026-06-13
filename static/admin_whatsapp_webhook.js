(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var el = byId(id);
    if (!el) return;
    el.textContent = value != null && value !== "" ? String(value) : "—";
  }

  function setStatus(msg) {
    setText("aww-status", msg || "");
  }

  function fillStatusBlock(prefix, obj) {
    if (!obj) {
      setText(prefix + "-wamid", null);
      setText(prefix + "-status", null);
      setText(prefix + "-recipient", null);
      setText(prefix + "-received", null);
      return;
    }
    setText(prefix + "-wamid", obj.wamid);
    setText(prefix + "-status", obj.status);
    setText(prefix + "-recipient", obj.recipient_id);
    setText(prefix + "-received", obj.received_at);
  }

  function loadDiagnostics() {
    setStatus("جاري التحميل…");
    fetch("/admin/api/whatsapp-webhook/diagnostics", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || data.ok !== true) {
          setStatus("تعذّر تحميل التشخيص");
          return;
        }
        setText("aww-last-received", data.last_webhook_received_at);
        fillStatusBlock("aww-delivered", data.last_delivered);
        fillStatusBlock("aww-read", data.last_read);
        if (!data.last_inbound) {
          setText("aww-inbound-from", null);
          setText("aww-inbound-id", null);
          setText("aww-inbound-type", null);
          setText("aww-inbound-text", null);
          setText("aww-inbound-received", null);
        } else {
          setText("aww-inbound-from", data.last_inbound.from);
          setText("aww-inbound-id", data.last_inbound.message_id);
          setText("aww-inbound-type", data.last_inbound.type);
          setText("aww-inbound-text", data.last_inbound.text);
          setText("aww-inbound-received", data.last_inbound.received_at);
        }
        var rawEl = byId("aww-raw-payload");
        if (rawEl) {
          if (data.last_webhook_raw) {
            try {
              rawEl.textContent = JSON.stringify(data.last_webhook_raw, null, 2);
            } catch (e) {
              rawEl.textContent = String(data.last_webhook_raw);
            }
          } else {
            rawEl.textContent = "—";
          }
        }
        var verifyNote = data.verify_token_configured
          ? "verify token configured"
          : "verify token not configured";
        setStatus("تم التحديث · " + verifyNote);
      })
      .catch(function () {
        setStatus("خطأ في الاتصال");
      });
  }

  var refreshBtn = byId("aww-refresh");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadDiagnostics);
  }

  loadDiagnostics();
})();
