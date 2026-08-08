/**
 * CartFlow Signature Primitives V1
 * Visual grammar layer — maps REAL product truth → structural attributes.
 * Presentation only. No business logic. No invented metrics.
 *
 * Grammar atoms (Figma CIM + Signature System):
 * Living Evidence · Evidence Density · Decision Tension · Attention Gravity
 * Commerce Momentum · Living Routes · Visual Breathing · Decision Densification
 * Recovery Scoop · Tapered Direction · Open-C geometry · Core Silence
 */
(function (global) {
  "use strict";

  function _n(v) {
    return String(v == null ? "" : v).trim();
  }

  function evidenceCount(card) {
    if (!card || typeof card !== "object") return 0;
    if (Array.isArray(card.evidence_lines_ar) && card.evidence_lines_ar.length) {
      return card.evidence_lines_ar.filter(function (x) {
        return _n(x);
      }).length;
    }
    if (_n(card.evidence_ar) || _n(card.observation_ar) || _n(card.diagnosis_ar)) {
      return 1;
    }
    return 0;
  }

  function readinessOf(card) {
    var r = _n(card && card.execution_readiness).toUpperCase();
    if (
      r === "READY" ||
      r === "NEEDS_MORE_EVIDENCE" ||
      r === "BLOCKED" ||
      r === "EXTERNAL_DEPENDENCY"
    ) {
      return r;
    }
    if (card && card.execution_available === true) return "READY";
    if (card && card.quiet) return "UNKNOWN";
    return "UNKNOWN";
  }

  /**
   * Density ordinal from real readiness + evidence + decision presence.
   * 1 quiet · 2 evidence-held · 3 understood/not ready · 4 actionable · 5 primary+ready
   */
  function densityOf(card, role) {
    if (!card || card.quiet || role === "quiet") return 1;
    var ready = readinessOf(card);
    var hasDecision = !!(
      _n(card.decision_sentence_ar) ||
      _n(card.commitment_ar) ||
      _n(card.operational_guidance_ar) ||
      card.has_decision !== false
    );
    var n = evidenceCount(card);
    if (ready === "NEEDS_MORE_EVIDENCE" || ready === "BLOCKED" || (!hasDecision && n)) {
      return 2;
    }
    if (hasDecision && ready !== "READY" && ready !== "EXTERNAL_DEPENDENCY") {
      return 3;
    }
    if (ready === "READY" || ready === "EXTERNAL_DEPENDENCY") {
      return role === "primary" ? 5 : 4;
    }
    if (hasDecision) return 3;
    if (n) return 2;
    return 1;
  }

  function roleOf(card) {
    if (!card || card.quiet) return "quiet";
    if (card.is_primary_decision) return "primary";
    return "next";
  }

  function momentumOf(card) {
    var ready = readinessOf(card);
    if (ready === "READY") return "forward";
    if (ready === "EXTERNAL_DEPENDENCY") return "external";
    if (ready === "NEEDS_MORE_EVIDENCE" || ready === "BLOCKED") return "held";
    if (card && card.quiet) return "calm";
    return "forming";
  }

  function tensionOf(card) {
    var ready = readinessOf(card);
    if (ready === "NEEDS_MORE_EVIDENCE" || ready === "BLOCKED") return "high";
    if (ready === "EXTERNAL_DEPENDENCY") return "open";
    if (ready === "READY" && roleOf(card) === "primary") return "resolved";
    return "low";
  }

  function stampAttrs(el, map) {
    if (!el || !map) return;
    Object.keys(map).forEach(function (k) {
      var v = map[k];
      if (v == null || v === "") el.removeAttribute(k);
      else el.setAttribute(k, String(v));
    });
  }

  function attrsForCard(card) {
    var role = roleOf(card);
    var n = evidenceCount(card);
    var ready = readinessOf(card);
    var density = densityOf(card, role);
    var hasDecision =
      role !== "quiet" &&
      !!(
        _n(card && card.decision_sentence_ar) ||
        _n(card && card.commitment_ar) ||
        card.has_decision !== false
      );
    return {
      "data-cf-sig": "decision-card",
      "data-cf-role": role,
      "data-cf-evidence-n": String(n),
      "data-cf-evidence-gap": card && card.missing_evidence ? "1" : "0",
      "data-cf-readiness": ready,
      "data-cf-has-decision": hasDecision ? "1" : "0",
      "data-cf-density": String(density),
      "data-cf-tension": tensionOf(card),
      "data-cf-momentum": momentumOf(card),
      "data-cf-gravity": role === "primary" ? "primary" : role === "next" ? "secondary" : "quiet",
    };
  }

  function applyCard(el, card) {
    if (!el) return;
    stampAttrs(el, attrsForCard(card || { quiet: true }));
  }

  function applyCardHtml(html, card) {
    var attrs = attrsForCard(card || { quiet: true });
    var bits = Object.keys(attrs)
      .map(function (k) {
        return k + '="' + String(attrs[k]).replace(/"/g, "&quot;") + '"';
      })
      .join(" ");
    if (!html) return html;
    if (html.indexOf("data-cf-sig=") !== -1) return html;
    return html.replace(/^(<\w+)/, "$1 " + bits);
  }

  function applyWorkspace(root, projection) {
    if (!root) return;
    var p = projection && typeof projection === "object" ? projection : {};
    var zoneB = Array.isArray(p.zone_b) ? p.zone_b : [];
    var quiet = !!(p.quiet || !zoneB.length);
    var routeCount = quiet ? 0 : Math.min(1 + Math.max(0, zoneB.length - 1), 4);
    stampAttrs(root, {
      "data-cf-sig": "workspace",
      "data-cf-quiet": quiet ? "1" : "0",
      "data-cf-route-count": String(routeCount),
      "data-cf-breathing": quiet ? "open" : routeCount === 1 ? "focused" : "active",
    });
    var cards = root.querySelectorAll("[data-cf-sig='decision-card'], .cw-card");
    var idx = 0;
    cards.forEach(function (el) {
      if (el.getAttribute("data-cw-quiet") === "1" || el.classList.contains("cw-card--quiet")) {
        applyCard(el, { quiet: true });
        return;
      }
      var card = zoneB[idx] || {};
      if (!el.getAttribute("data-cf-sig")) {
        applyCard(el, card);
      }
      idx += 1;
    });
  }

  function applyHomeSection(el, sec) {
    if (!el || !sec) return;
    var dominant = !!(sec.dominant || sec.id === "decisions");
    var rank = Number(sec.executive_rank || 0) || (dominant ? 1 : 2);
    stampAttrs(el, {
      "data-cf-sig": "home-section",
      "data-cf-gravity": dominant ? "primary" : rank <= 2 ? "secondary" : "quiet",
      "data-cf-rank": String(rank),
      "data-cf-momentum": sec.recommendation_ar || sec.cta_ar ? "forward" : "forming",
      "data-cf-has-decision": sec.id === "decisions" || dominant ? "1" : "0",
    });
  }

  function enhanceRenderedWorkspace(host, projection) {
    if (!host) return;
    applyWorkspace(host, projection);
    var ops = host.querySelector(".cw-ops");
    if (ops) applyWorkspace(ops, projection);
    var articles = host.querySelectorAll("article.cw-card");
    var zoneB = (projection && projection.zone_b) || [];
    var primary = null;
    var next = [];
    zoneB.forEach(function (c) {
      if (!c) return;
      if (c.is_primary_decision && !primary) primary = c;
      else next.push(c);
    });
    if (!primary && zoneB.length) {
      primary = zoneB[0];
      next = zoneB.slice(1);
    }
    articles.forEach(function (el) {
      if (el.classList.contains("cw-card--quiet")) {
        applyCard(el, { quiet: true });
        return;
      }
      if (el.classList.contains("cw-card--primary") || el.getAttribute("data-primary-decision") === "1") {
        applyCard(el, primary || { is_primary_decision: true });
        return;
      }
      if (el.classList.contains("cw-card--next")) {
        var id = el.getAttribute("data-decision-id");
        var match = next.filter(function (c) {
          return c && String(c.decision_id || "") === String(id || "");
        })[0];
        applyCard(el, match || { is_primary_decision: false });
      }
    });
  }

  global.CFSignature = {
    evidenceCount: evidenceCount,
    readinessOf: readinessOf,
    densityOf: densityOf,
    roleOf: roleOf,
    attrsForCard: attrsForCard,
    applyCard: applyCard,
    applyCardHtml: applyCardHtml,
    applyWorkspace: applyWorkspace,
    applyHomeSection: applyHomeSection,
    enhanceRenderedWorkspace: enhanceRenderedWorkspace,
  };
})(typeof window !== "undefined" ? window : globalThis);
