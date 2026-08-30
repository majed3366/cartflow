/**
 * CartFlow Merchant UI V2 — Settings Product Composition V1.
 * Answers: ما الذي أحتاج ضبطه لكي يعمل CartFlow بشكل صحيح وآمن؟
 * Existing configuration truth only. Overview → detail. No new writers.
 *
 * QueuePool Pressure Remediation V1: first paint is overview-only.
 * Sequential reads (store-connection, then one recovery-settings).
 * Detail maInit* runs only when that area is opened. Same-page cache shared.
 */
(function (global) {
  "use strict";

  var MARKER = "settings-product-composition-v1";
  var LOAD_MODE = "settings-queuepool-pressure-remediation-v1";

  var STATE_AR = {
    READY: "جاهز",
    NEEDS_SETUP: "يحتاج ضبط",
    PARTIAL: "مكتمل جزئياً",
    READ_ONLY: "قراءة فقط",
    UNAVAILABLE: "غير متاح",
  };

  var AREAS = [
    {
      id: "store",
      title: "المتجر",
      line: "ربط زد والباقة الحالية",
    },
    {
      id: "communication",
      title: "التواصل",
      line: "واتساب والقوالب والإشعارات",
    },
    {
      id: "recovery",
      title: "سياسة الاسترجاع",
      line: "التأخير وعدد المحاولات",
    },
    {
      id: "policy",
      title: "سياسة السلال المهمة",
      line: "عتبة VIP والتفعيل",
    },
    {
      id: "experience",
      title: "التجربة",
      line: "تفضيلات عرض الودجيت",
    },
  ];

  var HASH_AREA = {
    whatsapp: "communication",
    "whatsapp-connect": "communication",
    "trigger-templates": "communication",
    templates: "communication",
    widget: "experience",
    plans: "store",
  };

  var state = {
    root: null,
    selected: "",
    status: {},
    lines: {},
    notes: {},
    loaded: false,
    detailInited: {},
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function readCache() {
    if (!global.__cfSettingsReadCache) {
      global.__cfSettingsReadCache = {};
    }
    return global.__cfSettingsReadCache;
  }

  function jsonGet(url) {
    return fetch(url, { credentials: "same-origin" }).then(function (r) {
      return r.json().then(function (d) {
        return { ok: r.ok && d && d.ok !== false, data: d || {} };
      });
    });
  }

  function areaFromHash() {
    var raw = (location.hash || "").replace(/^#/, "");
    var name = raw.split("?")[0];
    var q = raw.indexOf("?") >= 0 ? raw.slice(raw.indexOf("?") + 1) : "";
    var params = new URLSearchParams(q);
    var asked = (params.get("area") || "").trim();
    if (asked && HASH_AREA[asked]) return HASH_AREA[asked];
    if (asked) return asked;
    if (HASH_AREA[name]) return HASH_AREA[name];
    return "";
  }

  function classifyStore(sc) {
    if (!sc) return { state: "PARTIAL", line: "تعذّر قراءة حالة الربط" };
    if (sc.connected) return { state: "READY", line: sc.status_label_ar || "المتجر مربوط" };
    return { state: "NEEDS_SETUP", line: sc.status_label_ar || "المتجر غير مربوط" };
  }

  function classifyComms(wa) {
    if (!wa) return { state: "PARTIAL", line: "تعذّر قراءة إعداد التواصل" };
    var num = String(wa.store_whatsapp_number || "").trim();
    var on = wa.whatsapp_recovery_enabled !== false;
    if (!num && !on) return { state: "NEEDS_SETUP", line: "واتساب غير جاهز" };
    if (!num || !on) return { state: "PARTIAL", line: "التواصل مكتمل جزئياً" };
    return { state: "READY", line: "واتساب مضبوط" };
  }

  function classifyRecovery(rs) {
    if (!rs) return { state: "PARTIAL", line: "تعذّر قراءة سياسة الاسترجاع" };
    var delay = parseInt(rs.recovery_delay, 10);
    var attempts = parseInt(rs.recovery_attempts, 10);
    if (!(delay >= 1) || !(attempts >= 1)) {
      return { state: "NEEDS_SETUP", line: "سياسة الاسترجاع غير مكتملة" };
    }
    return { state: "READY", line: "التأخير والمحاولات مضبوطة" };
  }

  function classifyVip(vip) {
    if (!vip) return { state: "PARTIAL", line: "تعذّر قراءة سياسة VIP" };
    var enabled = vip.vip_enabled !== false;
    var thr = vip.vip_cart_threshold;
    if (enabled && (thr == null || thr === "")) {
      return { state: "PARTIAL", line: "التفعيل بدون عتبة" };
    }
    if (enabled) return { state: "READY", line: "عتبة السلال المهمة مضبوطة" };
    return { state: "READY", line: "متابعة VIP غير مفعّلة" };
  }

  function classifyExperience(gen) {
    if (!gen) return { state: "PARTIAL", line: "تعذّر قراءة تفضيلات العرض" };
    var name = String(gen.widget_name || gen.widget_display_name || "").trim();
    return { state: "READY", line: name ? "اسم العرض: " + name : "تفضيلات العرض موجودة" };
  }

  function paintOverview() {
    var list = $("#cf2-settings-list", state.root);
    if (!list) return;
    list.innerHTML = AREAS.map(function (area) {
      var st = state.status[area.id] || "PARTIAL";
      var line = state.lines[area.id] || area.line;
      var on = state.selected === area.id;
      var notes = state.notes[area.id] || [];
      var chips =
        '<span class="cf2-settings__states">' +
        '<span class="cf2-settings__state" data-state="' +
        esc(st) +
        '">' +
        esc(STATE_AR[st] || st) +
        "</span>" +
        notes
          .map(function (note) {
            var label = STATE_AR[note.state] || note.state;
            if (note.label) label = label + " · " + note.label;
            return (
              '<span class="cf2-settings__state" data-state="' +
              esc(note.state) +
              '">' +
              esc(label) +
              "</span>"
            );
          })
          .join("") +
        "</span>";
      return (
        '<button type="button" class="cf2-settings__row' +
        (on ? " is-selected" : "") +
        (st === "NEEDS_SETUP" ? " is-needs" : "") +
        '" data-cf2-settings-area="' +
        area.id +
        '">' +
        '<span class="cf2-settings__row-title">' +
        esc(area.title) +
        "</span>" +
        '<span class="cf2-settings__row-line">' +
        esc(line) +
        "</span>" +
        chips +
        "</button>"
      );
    }).join("");

    var needs = AREAS.filter(function (a) {
      return state.status[a.id] === "NEEDS_SETUP";
    }).map(function (a) {
      return a.title;
    });
    var banner = $("#cf2-settings-needs", state.root);
    if (banner) {
      if (needs.length) {
        banner.hidden = false;
        banner.textContent = "يحتاج ضبط: " + needs.join("، ");
      } else {
        banner.hidden = true;
        banner.textContent = "";
      }
    }
  }

  function initDetail(id) {
    if (!id || state.detailInited[id]) return;
    state.detailInited[id] = true;
    if (id === "store") {
      if (typeof window.maInitStoreConnectionPage === "function") {
        window.maInitStoreConnectionPage();
      }
      if (typeof window.maInitSubscriptionPage === "function") {
        window.maInitSubscriptionPage();
      }
      return;
    }
    if (id === "communication") {
      if (typeof window.maInitWhatsappSettingsPage === "function") {
        window.maInitWhatsappSettingsPage();
      }
      return;
    }
    if (id === "recovery") {
      if (typeof window.maInitRecoveryPolicySettingsPage === "function") {
        window.maInitRecoveryPolicySettingsPage();
      }
      return;
    }
    if (id === "policy") {
      if (typeof window.maInitVipSettingsPage === "function") {
        window.maInitVipSettingsPage();
      }
      return;
    }
    if (id === "experience") {
      if (typeof window.maInitGeneralSettingsPage === "function") {
        window.maInitGeneralSettingsPage();
      }
    }
  }

  function showPanel(id, opts) {
    state.selected = id || "";
    var root = state.root;
    if (!root) return;
    root.classList.toggle("is-detail-open", !!id);
    var empty = $("#cf2-settings-detail-empty", root);
    var back = $("#cf2-settings-back", root);
    $all("[data-cf2-settings-panel]", root).forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-cf2-settings-panel") !== id;
    });
    if (empty) empty.hidden = !!id;
    if (back) {
      back.hidden = !id;
      var area = AREAS.filter(function (a) {
        return a.id === id;
      })[0];
      back.textContent = id && area ? "رجوع · " + area.title : "رجوع";
    }
    if (!id && state.root && document.activeElement && state.root.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    paintOverview();
    if (id && (!opts || opts.init !== false)) initDetail(id);
  }

  function bindOnce(root) {
    if (root.getAttribute("data-cf2-settings-bound") === "1") return;
    root.setAttribute("data-cf2-settings-bound", "1");
    var list = $("#cf2-settings-list", root);
    if (list) {
      list.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-cf2-settings-area]");
        if (!btn) return;
        showPanel(btn.getAttribute("data-cf2-settings-area"));
      });
    }
    var back = $("#cf2-settings-back", root);
    if (back) {
      back.addEventListener("click", function () {
        showPanel("");
      });
    }
  }

  function applyTruth(bundle) {
    var store = classifyStore(bundle.store);
    var comms = classifyComms(bundle.wa);
    var recovery = classifyRecovery(bundle.wa);
    var vip = classifyVip(bundle.vip);
    var exp = classifyExperience(bundle.general);
    state.status = {
      store: store.state,
      communication: comms.state,
      recovery: recovery.state,
      policy: vip.state,
      experience: exp.state,
    };
    state.lines = {
      store: store.line,
      communication: comms.line,
      recovery: recovery.line,
      policy: vip.line,
      experience: exp.line,
    };
    state.notes = {
      store: [
        { state: "READ_ONLY", label: "الباقة" },
        { state: "UNAVAILABLE", label: "سلة" },
      ],
    };
  }

  function paintFirstOverview() {
    AREAS.forEach(function (area) {
      if (!state.status[area.id]) state.status[area.id] = "PARTIAL";
      if (!state.lines[area.id]) state.lines[area.id] = "جاري التحميل…";
    });
    paintOverview();
  }

  function loadOverviewTruth() {
    var cache = readCache();
    return jsonGet("/api/merchant/store-connection")
      .catch(function () {
        return { ok: false, data: {} };
      })
      .then(function (storeRow) {
        var store =
          (storeRow.data && storeRow.data.store_connection) || storeRow.data || null;
        cache.store = store;
        return jsonGet("/api/recovery-settings").catch(function () {
          return { ok: false, data: {} };
        });
      })
      .then(function (rsRow) {
        var wa = rsRow.data || null;
        cache.recovery = wa;
        applyTruth({
          store: cache.store,
          wa: wa,
          vip: wa,
          general: wa,
        });
      });
  }

  function loadAndPaint(rootEl) {
    var root = rootEl || $("#cf2-settings-root") || $(".cf-settings-canonical");
    if (!root) return;
    state.root = root;
    root.setAttribute("data-cf-settings-marker", MARKER);
    root.setAttribute("data-cf-settings-load", LOAD_MODE);
    bindOnce(root);
    var initial = areaFromHash();
    paintFirstOverview();
    showPanel(initial, { init: false });
    loadOverviewTruth().then(function () {
      state.loaded = true;
      paintOverview();
      if (state.selected) initDetail(state.selected);
    });
  }

  window.CartFlowUiV2Settings = {
    loadAndPaint: loadAndPaint,
    marker: MARKER,
    loadMode: LOAD_MODE,
    showPanel: showPanel,
  };
})(window);
