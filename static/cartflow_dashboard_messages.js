(function () {
      var MODE = (document.body.getAttribute("data-cf-msg-mode") || "").trim();

      var errBox = document.getElementById("errBox");
      var okBox = document.getElementById("okBox");
      var TEMPLATE_KEYS = [
        "template_price",
        "template_shipping",
        "template_quality",
        "template_delivery",
        "template_warranty",
        "template_other",
      ];

      /** عبارات جاهزة لودجت الاكتشاف — حسب الأسلوب فقط (بدون تكرار أسماء الأسلوب في القائمة). */
      var LS_CHEER = "cf_tpl_cheerful_discovery";
      var DISCOVERY_PRESET_PHRASES_BY_TONE = {
        friendly: [
          "هلا 👋 فيه خيارات ممكن تعجبك، تحب أشوفها لك بسرعة؟",
          "جبت لك خيارات مناسبة 👇\nتقدر تختار اللي يناسبك وتضيفه للسلة بسهولة 👍",
          "أقدر أساعدك تختار الأنسب لك؟",
        ],
        cheerful: [
          "هيه 👋 جاهزين نضحك معاك ونختار أحلى خيار بسرعة؟ 😄",
          "شوف الخيارات الحلوة هنا 👇\nيلا نكمّل السلة على مزاجك ✨",
          "نبي نفرحك باختيار يناسبك — نبدأ؟ 🎉",
        ],
        formal: [
          "مرحباً، يمكنني مساعدتك في استعراض خيارات مناسبة لك.",
          "تم توفير خيارات مناسبة لك.",
          "هل ترغب بالاطلاع على الخيارات المتاحة؟",
        ],
        sales: [
          "قبل ما تطلع، عندي خيارات ممكن تناسبك أكثر.",
          "هذه أفضل الخيارات لك الآن 👇\nتقدر تختار اللي يناسبك وتضيفه للسلة بسهولة 👍",
          "خلني أوريك الخيار الأنسب لك بسرعة.",
        ],
      };

      /** عبارات خروج قبل السلة — حسب الأسلوب فقط. */
      var EXIT_PRESET_PHRASES_BY_TONE = {
        friendly: [
          "هلا 👋 فيه خيارات ممكن تعجبك، تحب أشوفها لك بسرعة؟",
          "جبت لك خيارات مناسبة 👇",
          "أقدر أساعدك تختار الأنسب لك؟",
        ],
        formal: [
          "مرحباً، يمكنني مساعدتك في استعراض خيارات مناسبة لك.",
          "تم توفير خيارات مناسبة لك.",
          "هل ترغب بالاطلاع على الخيارات المتاحة؟",
        ],
        sales: [
          "قبل ما تطلع، عندي خيارات ممكن تناسبك أكثر.",
          "هذه أفضل الخيارات لك الآن.",
          "خلني أوريك الخيار الأنسب لك بسرعة.",
        ],
      };

      /** قوالب واتساب — عبارات فقط حسب ‎template_tone‎ (بدون تكرار أسماء الأسلوب في القائمة). */
      var WA_RECOVERY_PHRASES_BY_TONE = {
        friendly: [
          "هلا 👋 لاحظنا إنك ما كمّلت الطلب — نقدر نساعدك بخطوة بسيطة إذا حاب.",
        ],
        formal: ["مرحباً، يمكننا مساعدتك على إتمام طلبك عند رغبتك."],
        sales: ["لا تفوّت الفرصة 👌 كمّل طلبك الآن وخلينا نسهّل عليك."],
      };

      function populateAllWaPhrasePicks() {
        var toneEl = document.getElementById("template_tone");
        if (!toneEl) return;
        document.querySelectorAll(".wa-phrase-pick").forEach(function (sel) {
          populatePresetPhraseSelect(sel, toneEl.value, WA_RECOVERY_PHRASES_BY_TONE);
        });
      }

      function encodePresetBodyForAttr(text) {
        return String(text || "")
          .replace(/\r\n/g, "\n")
          .replace(/\n/g, "&#10;");
      }

      function populatePresetPhraseSelect(selectEl, toneKey, phrasesByTone, extraAllowed) {
        if (!selectEl || !phrasesByTone) return;
        var allowed = ["friendly", "formal", "sales"];
        if (extraAllowed && extraAllowed.length) {
          allowed = allowed.concat(extraAllowed);
        }
        var tk =
          allowed.indexOf(String(toneKey || "").trim()) >= 0
            ? String(toneKey).trim()
            : "friendly";
        var list = phrasesByTone[tk] || phrasesByTone.friendly || [];
        while (selectEl.firstChild) {
          selectEl.removeChild(selectEl.firstChild);
        }
        var ph = document.createElement("option");
        ph.value = "";
        ph.textContent = "اختر عبارة جاهزة";
        ph.disabled = true;
        ph.hidden = true;
        ph.selected = true;
        selectEl.appendChild(ph);
        list.forEach(function (fullText, idx) {
          var o = document.createElement("option");
          o.value = "preset_" + tk + "_" + idx;
          o.setAttribute("data-body", encodePresetBodyForAttr(fullText));
          o.textContent = fullText.replace(/\n/g, " ").replace(/\s+/g, " ").trim();
          selectEl.appendChild(o);
        });
      }

      function clearPhrasePreview(previewRootId, previewBodyId) {
        var root = document.getElementById(previewRootId);
        var bodyEl = document.getElementById(previewBodyId);
        if (root) root.classList.add("hidden");
        if (bodyEl) bodyEl.textContent = "";
      }

      function effectiveDiscoveryTone() {
        var toneEl = document.getElementById("template_tone");
        var b = toneEl ? String(toneEl.value || "friendly").trim() : "friendly";
        if (b === "friendly") {
          try {
            if (localStorage.getItem(LS_CHEER) === "1") return "cheerful";
          } catch (eLs) {
            /* ignore */
          }
        }
        return b;
      }

      function refreshPhraseBubbles(selectId, hostId) {
        var sel = document.getElementById(selectId);
        var host = document.getElementById(hostId);
        if (!sel || !host) return;
        host.innerHTML = "";
        for (var i = 1; i < sel.options.length; i++) {
          (function (idx) {
            var opt = sel.options[idx];
            var b = document.createElement("button");
            b.type = "button";
            b.className = "cf-msg-bubble";
            b.setAttribute("type", "button");
            b.textContent = opt.textContent;
            b.addEventListener("click", function () {
              sel.selectedIndex = idx;
              sel.dispatchEvent(new Event("change", { bubbles: true }));
              host.querySelectorAll(".cf-msg-bubble").forEach(function (x) {
                x.classList.remove("cf-msg-bubble--on");
              });
              b.classList.add("cf-msg-bubble--on");
            });
            host.appendChild(b);
          })(i);
        }
      }

      function updateReadyTitle() {
        var el = document.getElementById("cf-ready-title");
        if (!el) return;
        var toneEl = document.getElementById("template_tone");
        var api = toneEl ? toneEl.value : "friendly";
        var lab =
          api === "formal"
            ? "رسمي"
            : api === "sales"
              ? "مقنع"
              : effectiveDiscoveryTone() === "cheerful"
                ? "مرح"
                : "ودي";
        el.textContent = "💡 عبارات جاهزة (" + lab + ")";
      }

      function syncDiscoveryToneCards() {
        var toneEl = document.getElementById("template_tone");
        if (!toneEl) return;
        var api = String(toneEl.value || "friendly").trim();
        var cheer = false;
        try {
          cheer = localStorage.getItem(LS_CHEER) === "1";
        } catch (e2) {
          cheer = false;
        }
        document.querySelectorAll("[data-cf-tone-card]").forEach(function (btn) {
          var a = btn.getAttribute("data-cf-tone-api");
          var btnCheer = btn.getAttribute("data-cf-cheer") === "1";
          var on = false;
          if (api === "formal" && a === "formal") on = true;
          if (api === "sales" && a === "sales") on = true;
          if (api === "friendly" && a === "friendly") {
            on = btnCheer === cheer;
          }
          btn.classList.toggle("cf-tone-card--on", on);
        });
        updateReadyTitle();
      }

      function applyDiscoveryToneFromCard(btn) {
        var toneEl = document.getElementById("template_tone");
        if (!toneEl || !btn) return;
        var api = btn.getAttribute("data-cf-tone-api") || "friendly";
        var cheer = btn.getAttribute("data-cf-cheer") === "1";
        toneEl.value = api;
        try {
          if (api === "friendly" && cheer) localStorage.setItem(LS_CHEER, "1");
          else localStorage.removeItem(LS_CHEER);
        } catch (e3) {
          /* ignore */
        }
        syncDiscoveryToneCards();
        populateDiscoveryPresetPhrases();
        populateAllWaPhrasePicks();
      }

      function populateDiscoveryPresetPhrases() {
        var sel = document.getElementById("discovery_phrase_pick");
        if (!sel) return;
        populatePresetPhraseSelect(
          sel,
          effectiveDiscoveryTone(),
          DISCOVERY_PRESET_PHRASES_BY_TONE,
          ["cheerful"]
        );
        clearPhrasePreview("discovery_phrase_preview", "discovery_phrase_preview_body");
        refreshPhraseBubbles("discovery_phrase_pick", "discovery_bubbles");
      }

      function populateExitPresetPhrases() {
        var sel = document.getElementById("exit_intent_phrase_pick");
        var toneEl = document.getElementById("exit_intent_template_tone");
        if (!sel || !toneEl) return;
        populatePresetPhraseSelect(sel, toneEl.value, EXIT_PRESET_PHRASES_BY_TONE);
        clearPhrasePreview("exit_intent_phrase_preview", "exit_intent_phrase_preview_body");
        refreshPhraseBubbles("exit_intent_phrase_pick", "exit_intent_bubbles");
      }

      function showErr(t) {
        errBox.textContent = t || "حدث خطأ";
        errBox.classList.remove("hidden");
        okBox.classList.add("hidden");
      }
      function showOk() {
        okBox.classList.remove("hidden");
        errBox.classList.add("hidden");
      }
      function hideMsg() {
        errBox.classList.add("hidden");
        okBox.classList.add("hidden");
      }

      var recoveryState = null;
      var REC_REASON_KEYS = [
        "price",
        "shipping",
        "delivery",
        "warranty",
        "quality",
        "thinking",
        "other",
      ];
      var SLOT_DELAY_DEFAULTS = {
        price: [[2, "minute"], [2, "hour"], [24, "hour"]],
        shipping: [[5, "minute"], [1, "hour"], [12, "hour"]],
        delivery: [[4, "minute"], [1, "hour"], [18, "hour"]],
        warranty: [[5, "minute"], [2, "hour"], [24, "hour"]],
        thinking: [[3, "minute"], [1, "hour"], [24, "hour"]],
        other: [[3, "minute"], [1, "hour"], [24, "hour"]],
        quality: [[3, "minute"], [2, "hour"], [24, "hour"]],
      };
      function defaultGuidedLine(uiKey, si) {
        var g = window.__CF_GUIDED_DEFAULTS || {};
        var row = g[uiKey] || {};
        return String(row[String(si)] != null ? row[String(si)] : "").trim();
      }
      function buildGuidedAttemptsPayload(uiKey, mc) {
        var ga = {};
        for (var si = 1; si <= mc; si++) {
          var tEl = getSlotTextEl(uiKey, si);
          var body = tEl ? String(tEl.value || "").trim() : "";
          var defl = defaultGuidedLine(uiKey, si);
          ga[String(si)] = body !== defl ? body : "";
        }
        return ga;
      }
      function slotDelayDefaults(uiKey) {
        return SLOT_DELAY_DEFAULTS[uiKey] || [[3, "minute"], [1, "hour"], [24, "hour"]];
      }
      function selectedMessageCount(uiKey) {
        var sel = document.querySelector('input[name="rec-msgcount-' + uiKey + '"]:checked');
        var v = sel ? parseInt(sel.value, 10) : 1;
        return v >= 1 && v <= 3 ? v : 1;
      }
      function getSlotDelayEl(uiKey, slotIdx) {
        return document.querySelector('[data-rec-slot-delay="' + uiKey + '"][data-slot-index="' + slotIdx + '"]');
      }
      function getSlotUnitEl(uiKey, slotIdx) {
        return document.querySelector('[data-rec-slot-unit="' + uiKey + '"][data-slot-index="' + slotIdx + '"]');
      }
      function getSlotTextEl(uiKey, slotIdx) {
        return document.querySelector('[data-rec-slot-text="' + uiKey + '"][data-slot-index="' + slotIdx + '"]');
      }
      function updateSlotVisibility(uiKey) {
        var n = selectedMessageCount(uiKey);
        for (var si = 1; si <= 3; si++) {
          var wrap = document.querySelector('[data-rec-slot-wrap="' + uiKey + '"][data-slot-index="' + si + '"]');
          if (wrap) wrap.classList.toggle("hidden", si > n);
        }
      }
      function syncToggleVisual(uiKey) {
        var cb = document.querySelector('[data-rec-trigger-toggle="' + uiKey + '"]');
        var onBtn = document.querySelector('[data-rec-trigger-on="' + uiKey + '"]');
        var offBtn = document.querySelector('[data-rec-trigger-off="' + uiKey + '"]');
        if (!cb || !onBtn || !offBtn) return;
        var en = !!cb.checked;
        onBtn.classList.toggle("cf-seg-btn--active", en);
        onBtn.classList.toggle("cf-seg-btn--inactive", !en);
        offBtn.classList.toggle("cf-seg-btn--active", !en);
        offBtn.classList.toggle("cf-seg-btn--inactive", en);
        onBtn.setAttribute("aria-pressed", en ? "true" : "false");
        offBtn.setAttribute("aria-pressed", en ? "false" : "true");
      }
      function syncHint(uiKey) {
        var cb = document.querySelector('[data-rec-trigger-toggle="' + uiKey + '"]');
        var hintEl = document.querySelector('[data-rec-trigger-hint="' + uiKey + '"]');
        if (!cb || !hintEl) return;
        hintEl.textContent = cb.checked
          ? "سيتم إرسال الرسائل تلقائيًا لهذا السبب"
          : "لن يتم إرسال رسائل لهذا السبب";
      }

      function fillTemplates(data) {
        TEMPLATE_KEYS.forEach(function (k) {
          var el = document.getElementById(k);
          if (!el) return;
          el.value = typeof data[k] === "string" ? data[k] : "";
        });
      }

      function applyTriggerTemplatesFromApi(rt) {
        var map = rt && typeof rt === "object" ? rt : {};
        REC_REASON_KEYS.forEach(function (uiKey) {
          var row = map[uiKey] || {};
          var enabled = row.enabled !== false;
          var msgs = Array.isArray(row.messages) ? row.messages : [];
          var mc = parseInt(row.message_count, 10);
          if (!(mc >= 1 && mc <= 3)) mc = msgs.length ? Math.min(3, msgs.length) : 1;
          var rr = document.querySelector('input[name="rec-msgcount-' + uiKey + '"][value="' + mc + '"]');
          if (rr) rr.checked = true;
          var cb = document.querySelector('[data-rec-trigger-toggle="' + uiKey + '"]');
          if (cb) cb.checked = enabled;
          for (var si = 1; si <= 3; si++) {
            var pair = slotDelayDefaults(uiKey)[si - 1] || [3, "minute"];
            var item = msgs[si - 1] && typeof msgs[si - 1] === "object" ? msgs[si - 1] : {};
            var dEl = getSlotDelayEl(uiKey, si);
            var uEl = getSlotUnitEl(uiKey, si);
            var tEl = getSlotTextEl(uiKey, si);
            if (dEl) dEl.value = item.delay !== undefined && item.delay !== null && String(item.delay).trim() !== "" ? String(item.delay) : String(pair[0]);
            if (uEl) {
              var uv = item.unit ? String(item.unit).trim().toLowerCase() : pair[1];
              if (uv === "minutes") uv = "minute";
              if (uv === "hours") uv = "hour";
              if (uv === "days") uv = "day";
              uEl.value = uv;
            }
            if (tEl) {
              var fromMsg = typeof item.text === "string" ? item.text.trim() : "";
              var ga = row.guided_attempts && typeof row.guided_attempts === "object" ? row.guided_attempts : {};
              var fromG = ga[String(si)] != null ? String(ga[String(si)]).trim() : "";
              var defL = defaultGuidedLine(uiKey, si);
              tEl.value = fromMsg || fromG || defL;
            }
          }
          updateSlotVisibility(uiKey);
          syncToggleVisual(uiKey);
          syncHint(uiKey);
          refreshGuidedForReason(uiKey);
        });
      }

      function populateOneGuidedPresetSelect(uiKey, slotIdx) {
        var sel = document.querySelector(
          '.cf-guided-preset[data-guided-preset="' + uiKey + '"][data-slot-index="' + slotIdx + '"]'
        );
        if (!sel) return;
        var defBody = defaultGuidedLine(uiKey, slotIdx);
        while (sel.firstChild) {
          sel.removeChild(sel.firstChild);
        }
        var ph = document.createElement("option");
        ph.value = "";
        ph.textContent = "عبارات مقترحة";
        ph.disabled = true;
        ph.hidden = true;
        ph.selected = true;
        sel.appendChild(ph);
        if (defBody) {
          var o = document.createElement("option");
          o.value = "def";
          o.setAttribute("data-body", encodePresetBodyForAttr(defBody));
          o.textContent = "المقترح من CartFlow";
          sel.appendChild(o);
        }
      }

      function syncGuidedPreview(uiKey, slotIdx) {
        var tEl = getSlotTextEl(uiKey, slotIdx);
        var prev = document.querySelector('[data-guided-preview="' + uiKey + "-" + slotIdx + '"]');
        if (!prev || !tEl) return;
        var txt = String(tEl.value || "").trim();
        if (!txt) {
          prev.classList.add("hidden");
          prev.textContent = "";
          return;
        }
        prev.textContent = txt;
        prev.classList.remove("hidden");
      }

      function refreshGuidedForReason(uiKey) {
        for (var si = 1; si <= 3; si++) {
          populateOneGuidedPresetSelect(uiKey, si);
          syncGuidedPreview(uiKey, si);
        }
      }

      function bindGuidedRecoveryUi() {
        var root = document.getElementById("reason-recovery-settings");
        if (!root) return;
        root.addEventListener("change", function (ev) {
          var t = ev.target;
          if (!t || !t.classList || !t.classList.contains("cf-guided-preset")) return;
          var uiKey = t.getAttribute("data-guided-preset");
          var si = parseInt(t.getAttribute("data-slot-index"), 10);
          if (!uiKey || !(si >= 1 && si <= 3)) return;
          if (t.selectedIndex <= 0) return;
          var opt = t.options[t.selectedIndex];
          var body = opt.getAttribute("data-body");
          if (!body) return;
          try {
            body = body.replace(/&#10;/g, "\n");
          } catch (eG) {
            /* ignore */
          }
          var ta = getSlotTextEl(uiKey, si);
          if (ta) ta.value = body;
          t.selectedIndex = 0;
          syncGuidedPreview(uiKey, si);
        });
        root.addEventListener("click", function (ev) {
          var t = ev.target;
          if (!t || !t.closest) return;
          var btn = t.closest("[data-guided-restore]");
          if (!btn) return;
          var uiKey = btn.getAttribute("data-guided-restore");
          var si = parseInt(btn.getAttribute("data-slot-index"), 10);
          if (!uiKey || !(si >= 1 && si <= 3)) return;
          var ta = getSlotTextEl(uiKey, si);
          if (ta) ta.value = defaultGuidedLine(uiKey, si);
          syncGuidedPreview(uiKey, si);
        });
        root.addEventListener("input", function (ev) {
          var ta = ev.target;
          if (!ta || !ta.getAttribute) return;
          if (!ta.getAttribute("data-rec-slot-text")) return;
          var uiKey = ta.getAttribute("data-rec-slot-text");
          var si = parseInt(ta.getAttribute("data-slot-index"), 10);
          if (uiKey && si >= 1 && si <= 3) syncGuidedPreview(uiKey, si);
        });
      }

      function buildReasonTemplatesPayload() {
        var out = {};
        REC_REASON_KEYS.forEach(function (uiKey) {
          var cb = document.querySelector('[data-rec-trigger-toggle="' + uiKey + '"]');
          var mc = selectedMessageCount(uiKey);
          var messages = [];
          for (var si = 1; si <= mc; si++) {
            var dEl = getSlotDelayEl(uiKey, si);
            var uEl = getSlotUnitEl(uiKey, si);
            var tEl = getSlotTextEl(uiKey, si);
            var delayRaw = dEl ? parseFloat(String(dEl.value || "1"), 10) : 1;
            if (!(delayRaw >= 1)) delayRaw = 1;
            var unitRaw = uEl ? String(uEl.value || "minute") : "minute";
            if (unitRaw === "day") {
              unitRaw = "hour";
              delayRaw = delayRaw * 24;
            }
            messages.push({ delay: delayRaw, unit: unitRaw, text: tEl ? String(tEl.value || "") : "" });
          }
          out[uiKey] = {
            enabled: cb ? !!cb.checked : true,
            message: messages[0] ? messages[0].text : "",
            message_count: mc,
            messages: messages,
            guided_attempts: buildGuidedAttemptsPayload(uiKey, mc),
          };
        });
        return out;
      }

      function mirrorTriggerTemplatesForLegacyApi(rt) {
        var o = {};
        ["price", "shipping", "warranty", "quality"].forEach(function (k) {
          if (!rt[k]) return;
          o[k] = {
            enabled: rt[k].enabled,
            message:
              rt[k].messages && rt[k].messages[0] && rt[k].messages[0].text ? rt[k].messages[0].text : "",
          };
        });
        if (rt.delivery) {
          o.delivery = {
            enabled: rt.delivery.enabled,
            message:
              rt.delivery.messages && rt.delivery.messages[0] && rt.delivery.messages[0].text
                ? rt.delivery.messages[0].text
                : "",
          };
        }
        if (rt.other) {
          o.other = {
            enabled: rt.other.enabled,
            message:
              rt.other.messages && rt.other.messages[0] && rt.other.messages[0].text
                ? rt.other.messages[0].text
                : "",
          };
        } else if (rt.thinking) {
          o.other = {
            enabled: rt.thinking.enabled,
            message:
              rt.thinking.messages && rt.thinking.messages[0] && rt.thinking.messages[0].text
                ? rt.thinking.messages[0].text
                : "",
          };
        }
        return o;
      }

      function bindReasonRecoveryControls() {
        REC_REASON_KEYS.forEach(function (uiKey) {
          var cb = document.querySelector('[data-rec-trigger-toggle="' + uiKey + '"]');
          var onBtn = document.querySelector('[data-rec-trigger-on="' + uiKey + '"]');
          var offBtn = document.querySelector('[data-rec-trigger-off="' + uiKey + '"]');
          if (cb && onBtn && offBtn) {
            onBtn.addEventListener("click", function () {
              cb.checked = true;
              syncToggleVisual(uiKey);
              syncHint(uiKey);
            });
            offBtn.addEventListener("click", function () {
              cb.checked = false;
              syncToggleVisual(uiKey);
              syncHint(uiKey);
            });
          }
          document.querySelectorAll('[data-rec-msgcount="' + uiKey + '"]').forEach(function (radio) {
            radio.addEventListener("change", function () {
              updateSlotVisibility(uiKey);
            });
          });
          updateSlotVisibility(uiKey);
          syncToggleVisual(uiKey);
          syncHint(uiKey);
        });
        bindGuidedRecoveryUi();
      }

      function syncTemplateCustomVisibility() {
        var wrap = document.getElementById("template_custom_wrap");
        var custom = document.getElementById("template_mode_custom");
        var phraseRow = document.getElementById("discovery_phrase_row");
        if (!wrap || !custom) return;
        var isCustom = custom.checked;
        wrap.classList.toggle("hidden", !isCustom);
        if (phraseRow) phraseRow.classList.toggle("hidden", isCustom);
      }

      function updatePhrasePickPreview(selectEl, previewRootId, previewBodyId) {
        var root = document.getElementById(previewRootId);
        var bodyEl = document.getElementById(previewBodyId);
        if (!root || !bodyEl || !selectEl) return;
        if (selectEl.selectedIndex <= 0) {
          root.classList.add("hidden");
          bodyEl.textContent = "";
          return;
        }
        var opt = selectEl.options[selectEl.selectedIndex];
        var body = opt.getAttribute("data-body");
        if (!body) {
          root.classList.add("hidden");
          bodyEl.textContent = "";
          return;
        }
        bodyEl.textContent = body.replace(/&#10;/g, "\n");
        root.classList.remove("hidden");
      }

      function applyTonePhrasePick(selectEl, presetRadioId, customRadioId, textareaId, syncFn, previewRootId, previewBodyId) {
        if (!selectEl || selectEl.selectedIndex <= 0) return;
        var opt = selectEl.options[selectEl.selectedIndex];
        var body = opt.getAttribute("data-body");
        if (!body) return;
        try {
          body = body.replace(/&#10;/g, "\n");
        } catch (e) {
          /* ignore */
        }
        var presetEl = document.getElementById(presetRadioId);
        var customEl = document.getElementById(customRadioId);
        if (customEl) customEl.checked = true;
        if (presetEl) presetEl.checked = false;
        var ta = document.getElementById(textareaId);
        if (ta) ta.value = body;
        selectEl.selectedIndex = 0;
        if (previewRootId && previewBodyId) {
          updatePhrasePickPreview(selectEl, previewRootId, previewBodyId);
        }
        if (typeof syncFn === "function") syncFn();
      }

      function fillTemplateControl(data) {
        var toneEl = document.getElementById("template_tone");
        var allowedTones = ["friendly", "formal", "sales"];
        var tone = typeof data.template_tone === "string" ? data.template_tone : "friendly";
        if (allowedTones.indexOf(tone) < 0) tone = "friendly";
        if (toneEl) toneEl.value = tone;
        if (tone !== "friendly") {
          try {
            localStorage.removeItem(LS_CHEER);
          } catch (eR) {
            /* ignore */
          }
        }
        var mode = typeof data.template_mode === "string" ? data.template_mode : "preset";
        var presetRadio = document.getElementById("template_mode_preset");
        var customRadio = document.getElementById("template_mode_custom");
        if (presetRadio && customRadio) {
          if (mode === "custom") {
            customRadio.checked = true;
            presetRadio.checked = false;
          } else {
            presetRadio.checked = true;
            customRadio.checked = false;
          }
        }
        var ta = document.getElementById("template_custom_text");
        if (ta) ta.value = typeof data.template_custom_text === "string" ? data.template_custom_text : "";
        syncTemplateCustomVisibility();
        syncDiscoveryToneCards();
        populateDiscoveryPresetPhrases();
        populateAllWaPhrasePicks();
      }

      function attachTemplateControlListeners() {
        var presetRadio = document.getElementById("template_mode_preset");
        var customRadio = document.getElementById("template_mode_custom");
        if (presetRadio) presetRadio.addEventListener("change", syncTemplateCustomVisibility);
        if (customRadio) customRadio.addEventListener("change", syncTemplateCustomVisibility);
        document.querySelectorAll("[data-cf-tone-card]").forEach(function (btn) {
          btn.addEventListener("click", function () {
            applyDiscoveryToneFromCard(btn);
          });
        });
        var phrasePick = document.getElementById("discovery_phrase_pick");
        if (phrasePick) {
          phrasePick.addEventListener("change", function () {
            updatePhrasePickPreview(
              phrasePick,
              "discovery_phrase_preview",
              "discovery_phrase_preview_body"
            );
            applyTonePhrasePick(
              phrasePick,
              "template_mode_preset",
              "template_mode_custom",
              "template_custom_text",
              syncTemplateCustomVisibility,
              "discovery_phrase_preview",
              "discovery_phrase_preview_body"
            );
            var hb = document.getElementById("discovery_bubbles");
            if (hb) {
              hb.querySelectorAll(".cf-msg-bubble").forEach(function (x) {
                x.classList.remove("cf-msg-bubble--on");
              });
            }
          });
        }
        syncDiscoveryToneCards();
        populateDiscoveryPresetPhrases();
        populateAllWaPhrasePicks();
      }

      if (MODE !== "exit") attachTemplateControlListeners();

      function syncExitIntentCustomVisibility() {
        var wrap = document.getElementById("exit_intent_custom_wrap");
        var custom = document.getElementById("exit_intent_mode_custom");
        var phraseRow = document.getElementById("exit_intent_phrase_row");
        if (!wrap || !custom) return;
        var isCustom = custom.checked;
        wrap.classList.toggle("hidden", !isCustom);
        if (phraseRow) phraseRow.classList.toggle("hidden", isCustom);
      }

      function fillExitIntentTemplateControl(data) {
        var toneEl = document.getElementById("exit_intent_template_tone");
        var allowedTones = ["friendly", "formal", "sales"];
        var tone =
          typeof data.exit_intent_template_tone === "string"
            ? data.exit_intent_template_tone
            : "friendly";
        if (allowedTones.indexOf(tone) < 0) tone = "friendly";
        if (toneEl) toneEl.value = tone;
        var mode =
          typeof data.exit_intent_template_mode === "string"
            ? data.exit_intent_template_mode
            : "preset";
        var presetRadio = document.getElementById("exit_intent_mode_preset");
        var customRadio = document.getElementById("exit_intent_mode_custom");
        if (presetRadio && customRadio) {
          if (mode === "custom") {
            customRadio.checked = true;
            presetRadio.checked = false;
          } else {
            presetRadio.checked = true;
            customRadio.checked = false;
          }
        }
        var ta = document.getElementById("exit_intent_custom_text");
        if (ta) {
          ta.value =
            typeof data.exit_intent_custom_text === "string"
              ? data.exit_intent_custom_text
              : "";
        }
        syncExitIntentCustomVisibility();
        populateExitPresetPhrases();
      }

      function attachExitIntentListeners() {
        var presetRadio = document.getElementById("exit_intent_mode_preset");
        var customRadio = document.getElementById("exit_intent_mode_custom");
        if (presetRadio) presetRadio.addEventListener("change", syncExitIntentCustomVisibility);
        if (customRadio) customRadio.addEventListener("change", syncExitIntentCustomVisibility);
        var exitTone = document.getElementById("exit_intent_template_tone");
        if (exitTone) {
          exitTone.addEventListener("change", function () {
            populateExitPresetPhrases();
          });
        }
        var phrasePick = document.getElementById("exit_intent_phrase_pick");
        if (phrasePick) {
          phrasePick.addEventListener("change", function () {
            updatePhrasePickPreview(
              phrasePick,
              "exit_intent_phrase_preview",
              "exit_intent_phrase_preview_body"
            );
            applyTonePhrasePick(
              phrasePick,
              "exit_intent_mode_preset",
              "exit_intent_mode_custom",
              "exit_intent_custom_text",
              syncExitIntentCustomVisibility,
              "exit_intent_phrase_preview",
              "exit_intent_phrase_preview_body"
            );
            var hb = document.getElementById("exit_intent_bubbles");
            if (hb) {
              hb.querySelectorAll(".cf-msg-bubble").forEach(function (x) {
                x.classList.remove("cf-msg-bubble--on");
              });
            }
          });
        }
        populateExitPresetPhrases();
      }

      if (MODE !== "recovery") attachExitIntentListeners();
      if (MODE !== "exit") bindReasonRecoveryControls();

      document.querySelectorAll(".wa-phrase-pick").forEach(function (sel) {
        sel.addEventListener("change", function () {
          if (!sel || sel.selectedIndex <= 0) return;
          var opt = sel.options[sel.selectedIndex];
          var body = opt.getAttribute("data-body");
          if (!body) return;
          try {
            body = body.replace(/&#10;/g, "\n");
          } catch (eWa) {
            /* ignore */
          }
          var tid = sel.getAttribute("data-target");
          var ta = tid ? document.getElementById(tid) : null;
          if (ta) ta.value = body;
          sel.selectedIndex = 0;
        });
      });

      function applyDashboardDeepLinkFromHash() {
        var id = (window.location.hash || "").replace(/^#/, "");
        if (!id || id.indexOf("cf-msg-template-") !== 0) return;
        var el = document.getElementById(id);
        if (!el) return;
        window.requestAnimationFrame(function () {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("cf-msg-deep-highlight");
          window.setTimeout(function () {
            el.classList.remove("cf-msg-deep-highlight");
          }, 2600);
        });
      }

      fetch("/api/recovery-settings")
        .then(function (r) {
          return r.json().then(function (d) {
            return { status: r.status, data: d };
          });
        })
        .then(function (x) {
          if (x.data.ok) {
            recoveryState = x.data;
            if (MODE !== "exit") {
              if (x.data.guided_recovery_defaults) {
                window.__CF_GUIDED_DEFAULTS = x.data.guided_recovery_defaults;
              }
              fillTemplates(x.data);
              fillTemplateControl(x.data);
              applyTriggerTemplatesFromApi(x.data.reason_templates || {});
            }
            if (MODE !== "recovery") {
              fillExitIntentTemplateControl(x.data);
            }
            hideMsg();
          } else {
            showErr(x.data.error || "تعذّر تحميل الإعدادات.");
          }
          if (MODE !== "exit") applyDashboardDeepLinkFromHash();
        })
        .catch(function () {
          showErr("خطأ في الشبكة أثناء التحميل.");
          if (MODE !== "exit") applyDashboardDeepLinkFromHash();
        });

      document.getElementById("f").addEventListener("submit", function (e) {
        e.preventDefault();
        hideMsg();
        var body = {};
        if (MODE !== "exit") {
          TEMPLATE_KEYS.forEach(function (k) {
            var el = document.getElementById(k);
            body[k] = el ? el.value : "";
          });
          body.template_mode =
            document.getElementById("template_mode_custom") &&
            document.getElementById("template_mode_custom").checked
              ? "custom"
              : "preset";
          body.template_tone = document.getElementById("template_tone")
            ? document.getElementById("template_tone").value
            : "friendly";
          body.template_custom_text = document.getElementById("template_custom_text")
            ? document.getElementById("template_custom_text").value
            : "";
          var rt = buildReasonTemplatesPayload();
          body.reason_templates = rt;
          body.trigger_templates = mirrorTriggerTemplatesForLegacyApi(rt);
        }
        if (MODE !== "recovery") {
          body.exit_intent_template_mode =
            document.getElementById("exit_intent_mode_custom") &&
            document.getElementById("exit_intent_mode_custom").checked
              ? "custom"
              : "preset";
          body.exit_intent_template_tone = document.getElementById("exit_intent_template_tone")
            ? document.getElementById("exit_intent_template_tone").value
            : "friendly";
          body.exit_intent_custom_text = document.getElementById("exit_intent_custom_text")
            ? document.getElementById("exit_intent_custom_text").value
            : "";
        }
        fetch("/api/recovery-settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })
          .then(function (r) {
            return r.json().then(function (d) {
              return { status: r.status, data: d };
            });
          })
          .then(function (x) {
            if (x.data.ok) {
              recoveryState = x.data;
              if (MODE !== "exit") {
                if (x.data.guided_recovery_defaults) {
                  window.__CF_GUIDED_DEFAULTS = x.data.guided_recovery_defaults;
                }
                fillTemplates(x.data);
                fillTemplateControl(x.data);
                applyTriggerTemplatesFromApi(x.data.reason_templates || {});
              }
              if (MODE !== "recovery") {
                fillExitIntentTemplateControl(x.data);
              }
              showOk();
            } else {
              showErr(x.data.error || "فشل الحفظ");
            }
          })
          .catch(function () {
            showErr("خطأ في الشبكة أثناء الحفظ.");
          });
      });

      if (MODE !== "exit") window.addEventListener("hashchange", applyDashboardDeepLinkFromHash);
    })();
  