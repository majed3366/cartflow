/* Lazy-load merchant dashboard JSON sections (shell-first). Not storefront widget V2. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function stripSkel(el) {
    if (!el) return;
    el.classList.remove("ma-dash-skel");
  }

  function setText(id, t) {
    var el = byId(id);
    if (el) {
      el.textContent = t == null ? "" : String(t);
      stripSkel(el);
    }
  }

  function setNavBadge(id, n) {
    var el = byId(id);
    if (!el) return;
    var v = parseInt(n, 10) || 0;
    el.textContent = String(v);
    el.style.display = v > 0 ? "" : "none";
  }

  function applyTopbarReadiness(d) {
    var sk = (d.wa_state_key || "").trim();
    var badge = d.wa_badge_ar || "—";
    var wrap = byId("ma-topbar-wa-wrap");
    if (wrap) {
      var muted = sk === "ready" ? "" : " wa-muted";
      wrap.innerHTML =
        '<div class="wa-pill' +
        muted +
        '"><div class="wa-dot"></div><span id="ma-topbar-wa-text">' +
        esc(badge) +
        "</span></div>";
    }
    var pPill = byId("ma-page-whatsapp-ready-pill");
    var pTxt = byId("ma-page-whatsapp-ready-text");
    if (pPill && pTxt) {
      pPill.classList.toggle("wa-muted", sk !== "ready");
      pTxt.textContent = badge;
    }
  }

  function reasonWeekRowHtml(rr) {
    var pct = parseFloat(rr.count_pct) || 0;
    var col = esc(rr.fill_color || "#6C5CE7");
    return (
      '<div class="r-row">' +
      '<div class="r-head"><span class="r-name">' +
      esc(rr.label_ar) +
      '</span><span class="r-pct">' +
      Math.round(pct) +
      "٪</span></div>" +
      '<div class="track"><div class="fill" style="width:' +
      pct +
      "%;background:" +
      col +
      ';"></div></div></div>'
    );
  }

  function reasonMonthRowHtml(rb) {
    var pct = parseFloat(rb.count_pct) || 0;
    var col = esc(rb.fill_color || "#6C5CE7");
    return (
      '<div class="r-big">' +
      '<div class="r-big-head"><span class="r-big-name">' +
      esc(rb.label_ar) +
      '</span><span class="r-big-pct">' +
      Math.round(pct) +
      "٪</span></div>" +
      '<div class="track-lg"><div class="fill-lg" style="width:' +
      pct +
      "%;background:" +
      col +
      ';"></div></div></div>'
    );
  }

  function applySummary(d) {
    if (!d || !d.ok) return;
    setText("ma-topbar-date", d.merchant_ar_date_header || "");
    applyTopbarReadiness(d);

    setText("ma-kpi-abandoned", d.merchant_kpi_abandoned_fmt || "0");
    setText("ma-kpi-recovered", d.merchant_kpi_recovered_fmt || "0");
    setText("ma-kpi-wa", d.merchant_kpi_wa_sent_fmt || "0");
    setText("ma-kpi-revenue", d.merchant_kpi_revenue_fmt || "0");

    var pct = parseFloat(d.merchant_kpi_recovered_pct_vs_abandoned) || 0;
    var note = byId("ma-kpi-recovered-note");
    if (note) {
      stripSkel(note);
      if (pct > 0) {
        note.textContent = "↑ نسبة " + Math.round(pct) + "٪";
        note.className = "kpi-note up";
      } else {
        note.textContent = "—";
        note.className = "kpi-note neutral";
      }
    }

    setText("ma-month-abandoned", d.merchant_month_abandoned_fmt || "0");
    setText("ma-month-recovered", d.merchant_month_recovered_fmt || "0");
    setText("ma-month-pct", (d.merchant_month_recovery_pct_fmt || "0") + "٪");
    setText("ma-month-revenue", (d.merchant_month_revenue_fmt || "0") + " ر");

    var wk = byId("ma-reasons-week-body");
    if (wk) {
      var rowsW = d.merchant_reason_rows_week || [];
      var htmlW = "";
      if (!rowsW.length) {
        htmlW =
          '<div class="empty-text" style="padding:12px;color:var(--muted);">لا توجد بيانات أسباب التردد لهذا الأسبوع</div>';
      } else {
        htmlW = rowsW.map(reasonWeekRowHtml).join("");
      }
      if (d.merchant_reason_insight_ar) {
        htmlW +=
          '<div class="r-insight">' + esc(d.merchant_reason_insight_ar) + "</div>";
      }
      wk.innerHTML = htmlW;
    }

    var mo = byId("ma-reasons-month-body");
    if (mo) {
      var h3 = mo.querySelector("h3");
      var h3txt = h3 ? h3.outerHTML : "<h3>توزيع الأسباب — آخر 30 يوماً</h3>";
      var rowsM = d.merchant_reason_rows_month || [];
      if (!rowsM.length) {
        mo.innerHTML =
          h3txt +
          '<div class="empty-text" style="padding:16px;">لا توجد بيانات أسباب كافية لهذه الفترة</div>';
      } else {
        mo.innerHTML = h3txt + rowsM.map(reasonMonthRowHtml).join("");
      }
    }

    var ins = byId("ma-reasons-insights");
    if (ins) {
      var lines = d.merchant_reason_recommendations_ar || [];
      var body = lines
        .map(function (ln) {
          return '<div class="ib-item">📌 ' + esc(ln) + "</div>";
        })
        .join("");
      if (!body) {
        body = '<div class="ib-item">—</div>';
      }
      ins.innerHTML = '<div class="ib-title">💡 توصيات</div>' + body;
    }

    setNavBadge("ma-nav-badge-abandoned", d.merchant_nav_badge_abandoned);
    setNavBadge("ma-nav-badge-followup", d.merchant_nav_badge_followup);
    setNavBadge("ma-nav-badge-vip", d.merchant_nav_badge_vip);

    var sm = byId("ma-settings-month-cart-line");
    if (sm) {
      sm.textContent =
        (d.merchant_month_abandoned_fmt || "0") + " سلة مسجّلة";
    }
  }

  var MERCHANT_INTERVENTION_PRIMARY_KEYS = {
    channel_failed: 1,
    needs_phone: 1,
    needs_reason: 1,
    attempts_exhausted: 1,
    stopped_manual: 1,
  };

  var MERCHANT_REASON_GOAL_AR = {
    price: "معالجة قلق السعر",
    price_high: "معالجة قلق السعر",
    shipping: "طمأنة حول الشحن",
    delivery: "طمأنة حول الشحن",
    thinking: "دعم اتخاذ القرار",
    warranty: "طمأنة حول الجودة",
    quality: "طمأنة حول الجودة",
    human_support: "طمأنة حول الجودة",
    trust: "طمأنة حول الجودة",
  };

  function merchantReasonGoalAr(reasonTag) {
    var k = String(reasonTag || "")
      .trim()
      .toLowerCase();
    if (!k) return "";
    return MERCHANT_REASON_GOAL_AR[k] || "متابعة سبب التردد";
  }

  function merchantTruncateText(text, maxLen) {
    var raw = String(text || "").trim();
    if (!raw) return "";
    if (raw.length <= maxLen) return raw;
    return raw.slice(0, maxLen - 1).trim() + "…";
  }

  function merchantPreviewFromWhatsappLine(line) {
    var s = String(line || "").trim();
    if (!s || s.indexOf("—") < 0) return "";
    var tail = s.split("—").slice(1).join("—").trim();
    if (tail.indexOf("(") === 0 && tail.lastIndexOf(")") === tail.length - 1) {
      tail = tail.slice(1, -1).trim();
    }
    if (tail && tail.indexOf("ننتظر") !== 0) return tail;
    return "";
  }

  function merchantSentMessageLine(mc) {
    var prev =
      String(mc.message_preview || "").trim() ||
      merchantPreviewFromWhatsappLine(mc.merchant_whatsapp_line_ar);
    if (prev) return '"' + merchantTruncateText(prev, 80) + '"';
    return "تم إرسال رسالة مناسبة لسبب التردد";
  }

  function merchantAttemptsDisplayAr(fr) {
    fr = fr || {};
    var raw = String(fr.attempts_ar || "").trim();
    var inbound = String(fr.inbound_message || "").trim();
    var replied = !!inbound;
    if (!replied) {
      var line = String(fr.last_message_line_ar || "").trim();
      replied =
        line.length > 0 &&
        line.indexOf("لا يوجد رد") < 0 &&
        line.indexOf("يتابع النظام") < 0;
    }
    var m = raw.match(/(\d+)\s*رسالة/);
    var n = m ? parseInt(m[1], 10) : 0;
    if (raw.indexOf("عدد الرسائل:") === 0) return raw;
    if (raw.indexOf("تمت متابعة") === 0) return raw;
    if (raw.indexOf("أُرسلت رسالة —") === 0) return raw;
    if (raw.indexOf("تم إرسال أول") === 0) return raw;
    if (raw.indexOf("لم تبدأ") === 0) return raw;
    if (n >= 3) return "عدد الرسائل: " + n;
    if (n === 2) return "تمت متابعة إضافية";
    if (n === 1) return "أُرسلت رسالة — لا توجد متابعات إضافية بعد";
    if (replied) return "تم إرسال أول رسالة استرداد";
    if (n === 0 && raw.indexOf("لا توجد") >= 0) {
      return replied ? "تم إرسال أول رسالة استرداد" : "لم تبدأ عملية الاسترداد بعد";
    }
    return raw || "—";
  }

  function merchantReplyPreview(fr) {
    var raw = String((fr && fr.inbound_message) || "").trim();
    if (!raw && fr && fr.last_message_line_ar) {
      var line = String(fr.last_message_line_ar).trim();
      if (
        line &&
        line.indexOf("لا يوجد رد") < 0 &&
        line.indexOf("يتابع النظام") < 0
      ) {
        raw = line;
      }
    }
    if (!raw) return "";
    return '"' + merchantTruncateText(raw, 60) + '"';
  }

  function merchantNeedsIntervention(mc) {
    if (!mc) return false;
    if (mc.merchant_next_action_urgent) return true;
    var pk = String(mc.merchant_lifecycle_primary_key || "")
      .trim()
      .toLowerCase();
    return !!MERCHANT_INTERVENTION_PRIMARY_KEYS[pk];
  }


  function merchantLifecycleCompact(mc) {
    var pk = String(mc.merchant_lifecycle_primary_key || "")
      .trim()
      .toLowerCase();
    var coarse = String(
      mc.merchant_coarse_status || mc.recovery_status || ""
    )
      .trim()
      .toLowerCase();
    var needs = merchantNeedsIntervention(mc);
    var pur = String(mc.merchant_purchase_line_ar || "").trim();
    var ret = String(mc.merchant_return_line_ar || "").trim();
    var status = "قيد المتابعة";
    var action = "النظام يتابع تلقائياً";
    var waiting = "النظام يتابع تلقائياً";
    if (pk === "customer_replied" || coarse === "replied" || coarse === "engaged") {
      status = "تفاعل العميل";
      action = "بدأ النظام متابعة الاعتراض";
      waiting = "النظام يتابع تلقائياً";
    } else if (pur || pk === "purchase_complete" || coarse === "converted") {
      status = "اكتمل الشراء";
      action = "انتهت مهمة الاسترجاع";
      waiting = "—";
    } else if (ret || pk === "customer_returned" || coarse === "returned") {
      status = "عاد للموقع";
      action = "أوقفنا الرسائل";
      waiting = "—";
    } else if (
      pk === "awaiting_customer_after_send" ||
      pk === "message_sent" ||
      coarse === "sent"
    ) {
      status = "أُرسلت رسالة";
      action = "—";
      waiting = "ننتظر تفاعل العميل";
    } else if (
      pk === "delay_waiting" ||
      pk === "no_engagement_yet" ||
      pk === "automation_paused" ||
      pk === "pending_schedule" ||
      coarse === "pending"
    ) {
      status = "بانتظار الإرسال";
      action = "—";
      waiting = "بانتظار وقت الإرسال";
    } else if (
      pk === "channel_failed" ||
      pk === "needs_phone" ||
      pk === "needs_reason" ||
      pk === "attempts_exhausted"
    ) {
      status = "يحتاج إجراء";
      action = "راجع الإعدادات";
      waiting = "—";
    }
    var isSent =
      pk === "awaiting_customer_after_send" ||
      pk === "message_sent" ||
      coarse === "sent";
    var isInteraction =
      pk === "customer_replied" || coarse === "replied" || coarse === "engaged";
    return {
      status: status,
      action: action,
      waiting: waiting,
      needsIntervention: needs,
      messageLine: isSent ? merchantSentMessageLine(mc) : "",
      goalLine: merchantReasonGoalAr(mc.reason_tag) || "",
      isSent: isSent,
      isInteraction: isInteraction,
    };
  }

  function merchantLifecycleCompactHtml(mc) {
    var c = merchantLifecycleCompact(mc);
    var h =
      '<div class="recovery-truth recovery-truth-compact" aria-label="ملخص المسار">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> ' +
      esc(c.status) +
      "</div>";
    if (c.messageLine) {
      h +=
        '<div class="recovery-truth-line"><strong>الرسالة:</strong> ' +
        esc(c.messageLine) +
        "</div>";
    }
    if (c.goalLine) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> ' +
        esc(c.goalLine) +
        "</div>";
    } else if (c.isSent) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> اختار النظام رسالة مناسبة بناءً على سبب التردد.</div>';
    }
    if (c.waiting && c.waiting !== "—") {
      h +=
        '<div class="recovery-truth-line"><strong>الانتظار:</strong> ' +
        esc(c.waiting) +
        "</div>";
    }
    if (c.action && c.action !== "—" && !c.isSent) {
      h +=
        '<div class="recovery-truth-line"><strong>الإجراء:</strong> ' +
        esc(c.action) +
        "</div>";
    }
    h +=
      '<div class="recovery-truth-line' +
      (c.needsIntervention ? "" : " recovery-truth-muted") +
      '"><strong>تدخل:</strong> ' +
      (c.needsIntervention ? "نعم" : "لا") +
      "</div>";
    return h + "</div>";
  }

  function followupCompactHtml(fr) {
    fr = fr || {};
    var goal = merchantReasonGoalAr(fr.reason_tag_raw || fr.reason_tag_ar);
    var reply = merchantReplyPreview(fr);
    var h =
      '<div class="recovery-truth recovery-truth-compact" aria-label="ملخص التفاعل">';
    h +=
      '<div class="recovery-truth-line"><strong>الحالة:</strong> تفاعل العميل</div>';
    if (reply) {
      h +=
        '<div class="recovery-truth-line"><strong>رد العميل:</strong> ' +
        esc(reply) +
        "</div>";
    }
    h +=
      '<div class="recovery-truth-line"><strong>الإجراء:</strong> بدأ النظام متابعة الاعتراض</div>';
    if (goal) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> ' +
        esc(goal) +
        "</div>";
    } else if (fr.reason_tag_raw) {
      h +=
        '<div class="recovery-truth-line"><strong>الهدف:</strong> اختار النظام رسالة مناسبة بناءً على سبب التردد.</div>';
    }
    h +=
      '<div class="recovery-truth-line"><strong>الانتظار:</strong> النظام يتابع تلقائياً</div>';
    h +=
      '<div class="recovery-truth-line recovery-truth-muted"><strong>تدخل:</strong> لا</div>';
    return h + "</div>";
  }

  function merchantNextLineShort(mc) {
    return merchantLifecycleCompact(mc).status;
  }

  function lifecycleTruthHtml(mc) {
    return merchantLifecycleCompactHtml(mc);
  }

  function cartRowHome(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var phoneOk =
      (mc.merchant_phone_line_ar || "").indexOf("متوفر") >= 0;
    var ph = phoneOk
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    var urg = mc.merchant_next_action_urgent ? " urgent" : "";
    return (
      "<tr>" +
      "<td><div class=\"camt\">" +
      v.toLocaleString("en-US") +
      ' ر</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(mc.merchant_status_row_class || "s-waiting") +
      '\"><span class="sd"></span>' +
      esc(mc.merchant_status_label_ar || "—") +
      "</span></td>" +
      '<td><div class="next' +
      urg +
      '">' +
      esc(merchantNextLineShort(mc) || mc.merchant_next_action_ar || "—") +
      "</div>" +
      lifecycleTruthHtml(mc) +
      "</td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function cartRowFull(mc) {
    var v = Math.round(parseFloat(mc.merchant_cart_value) || 0);
    var hasPh = !!mc.merchant_has_customer_phone;
    var ph = hasPh
      ? '<span class="ph-ok">✓</span>'
      : '<span class="ph-no">✗</span>';
    var b = esc(mc.merchant_cart_bucket || "other");
    var urg = mc.merchant_next_action_urgent ? " urgent" : "";
    return (
      '<tr data-ma-filter="' +
      b +
      '">' +
      "<td><div class=\"camt\">" +
      v.toLocaleString("en-US") +
      ' ر</div><div class="ctime">' +
      esc(mc.merchant_time_relative_ar || "—") +
      "</div></td>" +
      '<td><span class="chip ' +
      esc(mc.merchant_reason_chip_class || "c-other") +
      '">' +
      esc(mc.merchant_reason_chip_label_ar || "—") +
      "</span></td>" +
      '<td><span class="st ' +
      esc(mc.merchant_status_row_class || "s-waiting") +
      '\"><span class="sd"></span>' +
      esc(mc.merchant_status_label_ar || "—") +
      "</span></td>" +
      '<td><div class="next' +
      urg +
      '">' +
      esc(merchantNextLineShort(mc) || mc.merchant_next_action_ar || "—") +
      "</div>" +
      lifecycleTruthHtml(mc) +
      "</td>" +
      '<td><div class="ctime">' +
      esc(mc.merchant_last_seen_display || "—") +
      "</div></td>" +
      "<td>" +
      ph +
      "</td></tr>"
    );
  }

  function applyNormalCarts(d) {
    if (!d || !d.ok) return;
    var home = byId("ma-tbody-home-carts");
    if (home) {
      var tr = d.merchant_table_rows || [];
      if (!tr.length) {
        home.innerHTML =
          '<tr><td colspan="5" class="empty-text" style="text-align:center;padding:24px;color:var(--muted);">لا توجد سلال ضمن النشاط الحالي</td></tr>';
      } else {
        home.innerHTML = tr.map(cartRowHome).join("");
      }
    }
    var allb = byId("ma-tbody-all-carts");
    if (allb) {
      var pr = d.merchant_carts_page_rows || [];
      if (!pr.length) {
        allb.innerHTML =
          '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">🛒</div><div class="empty-text">لا توجد سلال متروكة مسجّلة حالياً ضمن نطاق متجرك</div></td></tr>';
      } else {
        allb.innerHTML = pr.map(cartRowFull).join("");
      }
    }
    var fc = d.merchant_cart_filter_counts || {};
    function sf(k, id) {
      var el = byId(id);
      if (el) el.textContent = String(fc[k] != null ? fc[k] : 0);
    }
    sf("all", "ma-filt-all");
    sf("recovered", "ma-filt-recovered");
    sf("sent", "ma-filt-sent");
    sf("attention", "ma-filt-attention");
    sf("nophone", "ma-filt-nophone");
    if (window.merchantAppReinitCartFilters) {
      window.merchantAppReinitCartFilters();
    }
  }

  function applyVipHomeBanner(ban) {
    var host = byId("ma-home-vip-banner");
    if (!host) return;
    if (!ban || !ban.amount_line) {
      host.style.display = "none";
      host.innerHTML = "";
      return;
    }
    host.style.display = "";
    var href = ban.contact_href || "";
    var btn = href
      ? '<a class="va-btn" href="' +
        esc(href) +
        '">تواصل يدوي (VIP) ←</a>'
      : '<span class="va-btn is-disabled" role="button" aria-disabled="true">تواصل يدوي (VIP) ←</span>';
    host.innerHTML =
      '<div class="vip-alert"><div class="va-icon">👑</div><div class="va-body">' +
      '<div class="va-title">عميل VIP يحتاج تدخلك — لن يُرسَل له واتساب تلقائياً</div>' +
      '<div class="va-sub">' +
      esc(ban.amount_line) +
      "</div></div>" +
      btn +
      "</div>";
  }

  function vipItemHtml(vr) {
    var href = vr.contact_href || "";
    var btn = href
      ? '<a class="vbtn" href="' + esc(href) + '">تواصل يدوي (VIP)</a>'
      : '<span class="vbtn is-disabled">تواصل يدوي (VIP)</span>';
    return (
      '<div class="vip-item">' +
      '<div class="vav">' +
      esc(vr.avatar_letter || "") +
      "</div>" +
      '<div class="vi"><div class="vamt">' +
      esc(vr.amount_display) +
      ' ريال</div><div class="vtm">' +
      esc(vr.subtitle_ar) +
      '</div></div><span class="vtag">VIP</span>' +
      btn +
      "</div>"
    );
  }

  function vipRowTable(vr) {
    var href = vr.contact_href || "";
    var btn = href
      ? '<a class="va-btn" href="' +
        esc(href) +
        '" rel="noopener noreferrer">تواصل يدوي (VIP) ←</a>'
      : '<span class="va-btn is-disabled">تواصل يدوي (VIP) ←</span>';
    var hp = vr.has_phone
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    return (
      "<tr><td><div class=\"camt\">" +
      esc(vr.amount_display) +
      ' ريال</div></td><td><div class="ctime">' +
      esc(vr.subtitle_ar) +
      "</div></td><td>" +
      hp +
      "</td><td>" +
      btn +
      "</td></tr>"
    );
  }

  function applyVipCarts(d) {
    if (!d || !d.ok) return;
    applyVipHomeBanner(d.merchant_vip_banner || null);
    var list = byId("ma-vip-home-list");
    if (list) {
      var rows = d.merchant_vip_rows || [];
      if (!rows.length) {
        list.innerHTML =
          '<div class="empty-state"><div class="empty-icon">👑</div><div class="empty-text">لا سلال VIP تحتاج تدخلك حالياً</div></div>';
      } else {
        list.innerHTML = rows.map(vipItemHtml).join("");
      }
    }
    var tb = byId("ma-tbody-vip-page");
    if (tb) {
      var pr = d.merchant_vip_page_rows || [];
      if (!pr.length) {
        tb.innerHTML =
          '<tr><td colspan="4" class="empty-state" style="border:none;"><div class="empty-icon">👑</div><div class="empty-text">لا توجد سلال VIP نشطة تحتاج تدخلك الآن</div></td></tr>';
      } else {
        tb.innerHTML = pr.map(vipRowTable).join("");
      }
    }
    setNavBadge("ma-nav-badge-vip", d.merchant_nav_badge_vip);
  }

  function followRowHtml(fr) {
    var cv = fr.cart_value;
    var camt =
      cv != null && cv !== ""
        ? '<div class="camt">' +
          Math.round(parseFloat(cv)) +
          " ر</div>"
        : '<div class="camt">—</div>';
    var digits = !!fr.customer_wa_digits;
    var ph = digits
      ? '<span class="ph-ok">✓ متوفر</span>'
      : '<span class="ph-no">✗ غير متوفر</span>';
    var act = followupCompactHtml(fr);
    return (
      "<tr>" +
      "<td>" +
      camt +
      '<div class="ctime">' +
      esc(fr.replied_at || "—") +
      "</div></td>" +
      '<td><span class="chip c-other">' +
      esc(fr.reason_tag_ar || fr.reason_ar || "—") +
      "</span></td>" +
      '<td><div class="msg-text" style="margin:0;">' +
      esc(fr.last_message_line_ar || "—") +
      '</div></td><td><div class="ctime" style="font-size:12px;font-weight:600;">' +
      esc(merchantAttemptsDisplayAr(fr)) +
      "</div></td><td>" +
      ph +
      "</td><td>" +
      act +
      "</td></tr>"
    );
  }

  function applyFollowups(d) {
    if (!d || !d.ok) return;
    var tb = byId("ma-tbody-followups");
    if (tb) {
      var fr = d.merchant_followup_rows || [];
      if (!fr.length) {
        tb.innerHTML =
          '<tr><td colspan="6" class="empty-state" style="border:none;"><div class="empty-icon">🔔</div><div class="empty-text">لا توجد سلال تفاعل حالياً</div></td></tr>';
      } else {
        tb.innerHTML = fr.map(followRowHtml).join("");
      }
    }
    setNavBadge("ma-nav-badge-followup", d.merchant_nav_badge_followup);
  }

  function messageRowHtml(mr) {
    return (
      '<div class="msg-row">' +
      '<div class="msg-avatar">💬</div>' +
      '<div class="msg-body">' +
      '<div class="msg-header">' +
      '<div class="msg-name">' +
      esc(mr.title_ar || "رسالة استرداد") +
      '</div><div class="msg-time">' +
      esc(mr.time_ar || "—") +
      "</div></div>" +
      '<div class="msg-text">' +
      esc(mr.preview_ar || "—") +
      '</div><div class="msg-tags">' +
      '<span class="st ' +
      esc(mr.status_row_class || "s-sent") +
      '\"><span class="sd"></span>' +
      esc(mr.status_ar || "—") +
      '</span><span class="chip c-other" style="margin-right:6px;">' +
      esc(mr.step_ar || "—") +
      "</span></div></div></div>"
    );
  }

  function applyMessages(d) {
    if (!d || !d.ok) return;
    var card = byId("ma-messages-card");
    if (!card) return;
    var rows = d.merchant_message_history_rows || [];
    if (!rows.length) {
      card.innerHTML =
        '<div class="empty-state" style="padding:40px 20px;"><div class="empty-icon">💬</div><div class="empty-text">لا توجد رسائل مرسلة بعد</div></div>';
    } else {
      card.innerHTML = rows.map(messageRowHtml).join("");
    }
    setText("ma-wa-last-send", d.merchant_wa_last_send_ar || "—");
  }

  function setCk(id, on) {
    var el = byId(id);
    if (el) el.checked = !!on;
  }

  function setRadio(name, val) {
    var q = document.querySelector(
      'input[name="' + name + '"][value="' + val + '"]'
    );
    if (q) q.checked = true;
  }

  function setSel(id, val) {
    var el = byId(id);
    if (!el) return;
    el.value = val == null ? "" : String(val);
    try {
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {}
  }

  function reasonEditorRowHtml(r) {
    var k = esc(String(r.key || "").trim().toLowerCase());
    var lab = esc(r.label_ar || "");
    var on = r.enabled ? " checked" : "";
    return (
      '<tr data-mw-reason-row>' +
      "<td>" +
      '<input type="hidden" class="mw-reason-key" value="' +
      k +
      '">' +
      '<p class="ma-fw-field-hint" style="margin:0 0 4px 0;font-size:12px;opacity:0.85;">هذا النص هو ما يظهر للعميل داخل الودجيت.</p>' +
      '<input class="ma-fw-input mw-reason-label" type="text" maxlength="80" value="' +
      lab +
      '" dir="rtl" autocomplete="off">' +
      '</td><td class="ma-fw-td-center"><input class="mw-reason-on" type="checkbox"' +
      on +
      "></td>" +
      '<td class="ma-fw-td-center">' +
      '<button type="button" class="ma-fw-mini" data-mw-reason-up title="تحريك لأعلى">↑</button>' +
      '<button type="button" class="ma-fw-mini" data-mw-reason-down title="تحريك لأسفل">↓</button>' +
      "</td></tr>"
    );
  }

  function applyWidgetPanel(d) {
    if (!d || !d.ok) return;
    var wp = d.merchant_widget_panel || {};
    var tg = wp.trigger || {};
    var boot = byId("ma-widget-bootstrap");
    if (boot) {
      try {
        boot.textContent = JSON.stringify(wp);
      } catch (e) {}
    }
    var wn = byId("mw-widget-name");
    if (wn) wn.value = String(wp.widget_name || "مساعد المتجر");
    var wc = byId("mw-widget-color");
    if (wc) wc.value = String(wp.widget_primary_color || "#6C5CE7");
    setCk("mw-widget-enabled", wp.cartflow_widget_enabled !== false);

    var tb = byId("mw-reason-tbody");
    if (tb) {
      var rr = wp.reason_rows || [];
      tb.innerHTML = rr.map(reasonEditorRowHtml).join("");
    }

    setCk("mw-exit-enabled", tg.exit_intent_enabled !== false);
    setSel("mw-exit-delay", String(parseInt(tg.exit_intent_delay_seconds, 10) || 0));
    setSel("mw-exit-sens", String(tg.exit_intent_sensitivity || "medium"));
    setSel("mw-exit-freq", String(tg.exit_intent_frequency || "per_session"));

    setCk("mw-hes-enabled", tg.hesitation_trigger_enabled !== false);
    var hesSec = parseInt(tg.hesitation_after_seconds, 10);
    if (!isFinite(hesSec)) hesSec = 20;
    var presets = [0, 5, 10, 20, 30, 15, 45, 60, 90, 120];
    var sel = presets.indexOf(hesSec) >= 0 ? String(hesSec) : "custom";
    setSel("mw-hes-sec", sel);
    var hsc = byId("mw-hes-sec-custom");
    if (hsc) {
      hsc.value = String(hesSec);
      hsc.style.display = sel === "custom" ? "" : "none";
    }
    var lbl = byId("mw-hes-sec-custom-label");
    if (lbl) lbl.style.display = sel === "custom" ? "" : "none";

    setSel("mw-hes-cond", String(tg.hesitation_condition || "after_cart_add"));
    setSel("mw-scope", String(tg.visibility_page_scope || "all"));

    setCk("mw-sup-dismiss", tg.suppress_after_widget_dismiss !== false);
    setCk("mw-sup-purchase", tg.suppress_after_purchase !== false);
    setCk("mw-sup-checkout", tg.suppress_when_checkout_started !== false);

    setRadio("mw-phone", String(tg.widget_phone_capture_mode || "after_reason"));

    setText("ma-settings-widget-title", d.merchant_widget_title_ar || "—");
    var we = byId("ma-settings-widget-enabled");
    if (we) {
      we.textContent = d.merchant_widget_installed ? "نعم" : "لا";
    }

    if (window.cartflowMerchantWidgetPanelRebindReasons) {
      window.cartflowMerchantWidgetPanelRebindReasons();
    } else if (window.cartflowMerchantWidgetPanelRefresh) {
      window.cartflowMerchantWidgetPanelRefresh();
    }
  }

  function fetchSection(url, applyFn, label) {
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        applyFn(d);
      })
      .catch(function () {
        /* section failed — shell remains */
      });
  }

  function bootLazyDashboard() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-kpi-abandoned")) return;

    var jobs = [
      fetchSection("/api/dashboard/summary", applySummary, "summary"),
      fetchSection("/api/dashboard/normal-carts", applyNormalCarts, "normal_carts"),
      fetchSection("/api/dashboard/vip-carts", applyVipCarts, "vip_carts"),
      fetchSection("/api/dashboard/followups", applyFollowups, "followups"),
      fetchSection("/api/dashboard/widget-panel", applyWidgetPanel, "widget_panel"),
      fetchSection("/api/dashboard/messages", applyMessages, "messages"),
      fetch("/api/dashboard/recovery-trend", { credentials: "same-origin" }).then(
        function () {
          return null;
        },
        function () {
          return null;
        }
      ),
    ];
    Promise.allSettled(jobs);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootLazyDashboard);
  } else {
    bootLazyDashboard();
  }
})();
