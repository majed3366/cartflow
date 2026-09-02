/* Merchant Settings — recovery delay / attempts (existing Store fields). */
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
    setBoxVisible(byId("ma-recovery-policy-ok"), false);
    var el = byId("ma-recovery-policy-err");
    if (el) {
      el.textContent = msg || "تعذّر الحفظ";
      setBoxVisible(el, true);
    }
  }

  function showOk() {
    setBoxVisible(byId("ma-recovery-policy-err"), false);
    var ok = byId("ma-recovery-policy-ok");
    if (ok) {
      ok.textContent = "تم حفظ سياسة الاسترجاع";
      setBoxVisible(ok, true);
    }
  }

  function hideMsgs() {
    setBoxVisible(byId("ma-recovery-policy-err"), false);
    setBoxVisible(byId("ma-recovery-policy-ok"), false);
  }

  function paintSummary(d) {
    var attEl = byId("ma-rec-sum-attempts");
    if (!d) return;
    /* First-message summary is owned by trigger templates (absolute stage-0 delays). */
    if (attEl) {
      var a = parseInt(d.recovery_attempts, 10);
      attEl.textContent = isFinite(a) ? String(a) : "—";
    }
    if (typeof window.maUpdateRecoveryReasonsSummary === "function") {
      window.maUpdateRecoveryReasonsSummary();
    }
  }

  function fillForm(d) {
    if (!d) return;
    var delay = byId("ma-recovery-delay");
    if (delay) delay.value = d.recovery_delay != null ? String(d.recovery_delay) : "15";
    var unit = byId("ma-recovery-delay-unit");
    if (unit) unit.value = d.recovery_delay_unit || "minutes";
    var attempts = parseInt(d.recovery_attempts, 10);
    if (!isFinite(attempts) || attempts < 1) attempts = 1;
    if (attempts > 3) attempts = 3;
    var hidden = byId("ma-recovery-attempts");
    if (hidden) hidden.value = String(attempts);
    var pick = document.querySelector(
      'input[name="ma_recovery_attempts_pick"][value="' + attempts + '"]'
    );
    if (pick) pick.checked = true;
    paintSummary(d);
  }

  function collectBody() {
    var delayEl = byId("ma-recovery-delay");
    var n = parseInt(delayEl && delayEl.value, 10);
    if (!isFinite(n) || n < 1) {
      return { ok: false, error: "أدخل مدة انتظار صحيحة" };
    }
    var unit = (byId("ma-recovery-delay-unit") && byId("ma-recovery-delay-unit").value) || "minutes";
    var pick = document.querySelector('input[name="ma_recovery_attempts_pick"]:checked');
    var attempts = pick ? parseInt(pick.value, 10) : 1;
    if (!isFinite(attempts) || attempts < 1) attempts = 1;
    return {
      ok: true,
      body: {
        recovery_delay: n,
        recovery_delay_unit: unit,
        recovery_attempts: attempts,
        merchant_settings_scope: "recovery",
        settings_write_owner: "merchant_settings",
      },
    };
  }

  function loadSettings(force) {
    if (!force && loadedOnce) return Promise.resolve();
    var cached = window.__cfSettingsReadCache && window.__cfSettingsReadCache.recovery;
    if (!force && cached && cached.ok !== false) {
      fillForm(cached);
      loadedOnce = true;
      return Promise.resolve();
    }
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
          showErr((x.data && x.data.error) || "تعذّر تحميل سياسة الاسترجاع");
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
    var collected = collectBody();
    if (!collected.ok) {
      showErr(collected.error);
      return;
    }
    if (
      !window.confirm(
        "تغيير سياسة الاسترجاع يؤثر على متى وكم مرة تُرسل رسائل الاسترجاع. متابعة؟"
      )
    ) {
      return;
    }
    var btn = byId("ma-recovery-policy-save");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "جاري الحفظ…";
    }
    saving = true;
    fetch("/api/recovery-settings", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collected.body),
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
          btn.textContent = "حفظ التوقيت العام";
        }
      });
  }

  function bindOnce() {
    if (bound) return;
    var form = byId("ma-recovery-policy-form");
    if (!form) return;
    bound = true;
    form.addEventListener("submit", onSubmit);
  }

  window.maInitRecoveryPolicySettingsPage = function () {
    bindOnce();
    loadSettings(false);
  };
})();
