/* Merchant dashboard — WhatsApp template registry layer (#whatsapp) */
(function () {
  "use strict";

  var bound = false;
  var rows = [];

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setStatus(msg) {
    var el = byId("ma-wa-templates-status");
    if (el) el.textContent = msg || "";
  }

  function renderList() {
    var host = byId("ma-wa-templates-list");
    if (!host) return;
    if (!rows.length) {
      host.innerHTML = "<p class='ma-wa-templates-empty'>لا توجد قوالب</p>";
      return;
    }
    host.innerHTML = rows
      .map(function (row, idx) {
        var customized = row.is_customized ? " · مخصص" : "";
        return (
          "<div class='ma-wa-template-row' data-idx='" +
          idx +
          "'>" +
          "<div class='ma-wa-template-head'>" +
          "<strong>" +
          esc(row.display_name_ar) +
          "</strong>" +
          "<span class='ma-wa-template-meta'>" +
          esc(row.template_key) +
          customized +
          "</span>" +
          "<label class='ma-fw-check ma-wa-template-enabled'>" +
          "<input type='checkbox' data-field='enabled' " +
          (row.enabled !== false ? "checked" : "") +
          " />" +
          "<span>مفعّل</span></label>" +
          "</div>" +
          "<textarea class='ma-fw-input ma-wa-template-text' rows='3' data-field='content'>" +
          esc(row.effective_content || row.default_content || "") +
          "</textarea>" +
          "<button type='button' class='ma-fw-mini ma-wa-template-restore' data-key='" +
          esc(row.template_key) +
          "'>استعادة الافتراضي</button>" +
          "</div>"
        );
      })
      .join("");

    host.querySelectorAll(".ma-wa-template-restore").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-key");
        var row = rows.find(function (r) {
          return r.template_key === key;
        });
        if (!row) return;
        var wrap = btn.closest(".ma-wa-template-row");
        var ta = wrap && wrap.querySelector(".ma-wa-template-text");
        if (ta) ta.value = row.default_content || "";
        var en = wrap && wrap.querySelector('[data-field="enabled"]');
        if (en) en.checked = true;
        setStatus("تمت استعادة النص الافتراضي — احفظ لتطبيق التغيير");
      });
    });
  }

  function collectOverrides() {
    var host = byId("ma-wa-templates-list");
    if (!host) return {};
    var out = {};
    host.querySelectorAll(".ma-wa-template-row").forEach(function (wrap, idx) {
      var row = rows[idx];
      if (!row) return;
      var ta = wrap.querySelector(".ma-wa-template-text");
      var en = wrap.querySelector('[data-field="enabled"]');
      var content = ta ? ta.value.trim() : "";
      var enabled = en ? en.checked : true;
      var entry = { enabled: enabled };
      if (content && content !== (row.default_content || "").trim()) {
        entry.custom_content = content;
      } else if (!enabled) {
        entry.custom_content = "";
      }
      out[row.template_key] = entry;
    });
    return out;
  }

  function loadTemplates() {
    setStatus("جاري التحميل…");
    return fetch("/api/recovery-settings")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) {
          setStatus("تعذّر تحميل القوالب");
          return;
        }
        rows = data.whatsapp_template_merchant_rows || [];
        renderList();
        setStatus("عدد القوالب: " + rows.length);
      })
      .catch(function () {
        setStatus("خطأ في الشبكة");
      });
  }

  function saveTemplates() {
    var btn = byId("ma-wa-templates-save");
    if (btn) btn.disabled = true;
    setStatus("جاري الحفظ…");
    fetch("/api/recovery-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ whatsapp_template_overrides: collectOverrides() }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok) {
          rows = data.whatsapp_template_merchant_rows || rows;
          renderList();
          setStatus("تم حفظ القوالب");
        } else {
          setStatus((data && data.error) || "فشل الحفظ");
        }
      })
      .catch(function () {
        setStatus("خطأ في الشبكة أثناء الحفظ");
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function bindOnce() {
    if (bound) return;
    if (!byId("ma-wa-templates-list")) return;
    bound = true;
    var saveBtn = byId("ma-wa-templates-save");
    if (saveBtn) saveBtn.addEventListener("click", saveTemplates);
  }

  window.maInitWhatsappTemplateRegistryPage = function () {
    bindOnce();
    loadTemplates();
  };
})();
