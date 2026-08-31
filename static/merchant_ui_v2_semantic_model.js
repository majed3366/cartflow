/**
 * CartFlow Semantic Visual Model V1 — derivation only.
 * RAW CANONICAL TRUTH → bounded semantic variables.
 * Painters must not guess state independently.
 */
(function (global) {
  "use strict";

  var VERSION = "semantic-visual-model-v1";
  var STATUS_INSUFFICIENT_AR = "أدلة غير كافية";
  var STATUS_WAITING_AR = "بانتظار متابعة";
  var STATUS_NO_TASKS_AR = "لا مهام";
  var READY = "READY";
  var NEEDS_MORE = "NEEDS_MORE_EVIDENCE";
  var BLOCKED = "BLOCKED";
  var EXTERNAL = "EXTERNAL_DEPENDENCY";

  function norm(v) {
    return String(v == null ? "" : v).trim();
  }

  function asBool(v) {
    return v === true || v === "true" || v === 1;
  }

  function coreSilenceHome(pkg) {
    if (!pkg || typeof pkg !== "object" || pkg.enabled === false) return "QUIET";
    var sections = Array.isArray(pkg.sections) ? pkg.sections.filter(function (s) {
      return s && typeof s === "object";
    }) : [];
    if (!sections.length) return "QUIET";
    var primary = null;
    var i;
    for (i = 0; i < sections.length; i++) {
      if (sections[i].dominant || norm(sections[i].id) === "decisions") {
        primary = sections[i];
        break;
      }
    }
    if (!primary) primary = sections[0];
    var others = sections.filter(function (s) {
      return s !== primary;
    });
    if (asBool(primary.empty) && !others.length) return "QUIET";
    return "ACTIVE";
  }

  function coreSilenceWorkspace(projection) {
    if (!projection || typeof projection !== "object") return "QUIET";
    if (asBool(projection.quiet)) return "QUIET";
    if (!Array.isArray(projection.zone_b) || projection.zone_b.length === 0) {
      return "QUIET";
    }
    return "ACTIVE";
  }

  function attentionIntensity(opts) {
    if (opts.silence === "QUIET") return "NONE";
    if (opts.surface === "home") {
      var sec = opts.section || {};
      if (asBool(sec.empty)) return "NONE";
      if (sec.dominant || norm(sec.id) === "decisions") return "PRIMARY";
      return "SECONDARY";
    }
    var card = opts.card || {};
    if (card.is_primary_decision === true) return "PRIMARY";
    return "SECONDARY";
  }

  function decisionReadiness(opts) {
    if (opts.surface !== "workspace") return "UNKNOWN";
    var raw = norm(opts.card && opts.card.execution_readiness);
    if (
      raw === READY ||
      raw === NEEDS_MORE ||
      raw === BLOCKED ||
      raw === EXTERNAL
    ) {
      return raw;
    }
    return "UNKNOWN";
  }

  function evidenceSufficiency(opts) {
    var readiness = opts.readiness || "UNKNOWN";
    if (opts.surface === "home") {
      var sec = opts.section || {};
      if (asBool(sec.empty) || norm(sec.status_ar) === STATUS_INSUFFICIENT_AR) {
        return "INSUFFICIENT";
      }
      return "UNKNOWN";
    }
    var card = opts.card || {};
    if (card.has_decision === false) return "INSUFFICIENT";
    if (norm(card.missing_evidence)) return "INSUFFICIENT";
    if (readiness === NEEDS_MORE) return "INSUFFICIENT";
    if (readiness === READY || readiness === EXTERNAL || readiness === BLOCKED) {
      return "SUFFICIENT";
    }
    return "UNKNOWN";
  }

  function evidenceConflict(opts) {
    if (opts.surface !== "workspace") return "UNKNOWN";
    var card = opts.card || {};
    if (!Object.prototype.hasOwnProperty.call(card, "diagnosis_status")) {
      return "UNKNOWN";
    }
    var status = norm(card.diagnosis_status).toLowerCase();
    if (status === "conflicting_evidence" || status === "conflicting") {
      return "CONFLICT";
    }
    return "NONE";
  }

  function uncertaintyLevel(opts) {
    if (opts.silence === "QUIET") return "NONE";
    if (opts.conflict === "CONFLICT") return "HIGH";
    if (
      opts.sufficiency === "SUFFICIENT" &&
      opts.conflict !== "CONFLICT" &&
      opts.readiness === READY
    ) {
      return "NONE";
    }
    if (opts.sufficiency === "INSUFFICIENT" || opts.readiness === NEEDS_MORE) {
      return "MEDIUM";
    }
    return "UNKNOWN";
  }

  function waitKind(opts) {
    if (opts.silence === "QUIET") return "NO_ACTION";
    if (opts.surface === "home") {
      var status = norm(opts.section && opts.section.status_ar);
      if (status === STATUS_WAITING_AR) return "WAITING_READINESS";
      if (status === STATUS_NO_TASKS_AR) return "NO_ACTION";
      return "UNKNOWN";
    }
    if (opts.readiness === READY) return "ACTION_REQUIRED";
    if (opts.readiness === EXTERNAL) return "WAITING_EXTERNAL";
    if (opts.readiness === BLOCKED) return "BLOCKED";
    if (opts.readiness === NEEDS_MORE) return "WAITING_READINESS";
    var waits = opts.card && opts.card.action_wait_lines_ar;
    if (Array.isArray(waits) && waits.some(function (x) { return norm(x); })) {
      return "WAITING_READINESS";
    }
    return "UNKNOWN";
  }

  function densityState(sufficiency) {
    if (sufficiency === "INSUFFICIENT") return "LOW";
    if (sufficiency === "SUFFICIENT") return "PRESENT";
    return "NEUTRAL";
  }

  function massState(readiness) {
    if (readiness === READY) return "READY";
    if (readiness === BLOCKED || readiness === EXTERNAL) return "HELD";
    return "OPEN";
  }

  function tensionState(conflict, readiness) {
    if (conflict === "CONFLICT" || readiness === BLOCKED) return "HIGH";
    if (conflict === "UNKNOWN" && readiness === "UNKNOWN") return "UNKNOWN";
    return "NONE";
  }

  function clauseRoles(sem) {
    if (norm(sem && sem.core_silence) === "QUIET") return [];
    var roles = [];
    var att = norm(sem.attention_intensity);
    if (att === "PRIMARY" || att === "SECONDARY") {
      roles.push({
        role: "attention",
        kind: "attention",
        label: "انتباه",
        attention: att.toLowerCase(),
      });
    }
    if (norm(sem.evidence_sufficiency) === "INSUFFICIENT") {
      roles.push({
        role: "evidence",
        kind: "insufficient",
        label: "أدلة ناقصة",
        sufficiency: "insufficient",
      });
    }
    var unc = norm(sem.uncertainty_level);
    if (unc === "MEDIUM" || unc === "HIGH") {
      roles.push({
        role: "uncertainty",
        kind: "uncertainty",
        label: "عدم يقين",
        uncertainty: unc.toLowerCase(),
        tension: norm(sem.evidence_conflict) === "CONFLICT" ? "high" : "none",
      });
    }
    return roles;
  }

  function pack(opts) {
    var sem = {
      model: VERSION,
      surface: opts.surface,
      core_silence: opts.silence,
      attention_intensity: opts.attention,
      decision_readiness: opts.readiness,
      evidence_sufficiency: opts.sufficiency,
      evidence_conflict: opts.conflict,
      uncertainty_level: opts.uncertainty,
      wait_kind: opts.wait,
      density: densityState(opts.sufficiency),
      mass: massState(opts.readiness),
      tension: tensionState(opts.conflict, opts.readiness),
    };
    sem.roles = clauseRoles(sem);
    return sem;
  }

  function projectHomeSurface(pkg, section) {
    var silence = coreSilenceHome(pkg);
    var readiness = "UNKNOWN";
    var sufficiency = evidenceSufficiency({
      surface: "home",
      section: section,
      readiness: readiness,
    });
    var conflict = "UNKNOWN";
    var attention = attentionIntensity({
      silence: silence,
      surface: "home",
      section: section,
    });
    var uncertainty = uncertaintyLevel({
      silence: silence,
      sufficiency: sufficiency,
      conflict: conflict,
      readiness: readiness,
    });
    var wait = waitKind({
      surface: "home",
      silence: silence,
      readiness: readiness,
      section: section,
    });
    return pack({
      surface: "home",
      silence: silence,
      attention: attention,
      readiness: readiness,
      sufficiency: sufficiency,
      conflict: conflict,
      uncertainty: uncertainty,
      wait: wait,
    });
  }

  function projectWorkspace(projection, card) {
    var silence = coreSilenceWorkspace(projection);
    var readiness = decisionReadiness({ surface: "workspace", card: card });
    var sufficiency = evidenceSufficiency({
      surface: "workspace",
      card: card,
      readiness: readiness,
    });
    var conflict = evidenceConflict({ surface: "workspace", card: card });
    var attention = attentionIntensity({
      silence: silence,
      surface: "workspace",
      card: card,
    });
    var uncertainty = uncertaintyLevel({
      silence: silence,
      sufficiency: sufficiency,
      conflict: conflict,
      readiness: readiness,
    });
    var wait = waitKind({
      surface: "workspace",
      silence: silence,
      readiness: readiness,
      card: card,
    });
    return pack({
      surface: "workspace",
      silence: silence,
      attention: attention,
      readiness: readiness,
      sufficiency: sufficiency,
      conflict: conflict,
      uncertainty: uncertainty,
      wait: wait,
    });
  }

  try {
    if (
      global.document &&
      global.location &&
      /(?:\?|&)cf_sem_proof=labels-hidden(?:&|$)/.test(String(global.location.search || ""))
    ) {
      global.document.documentElement.setAttribute("data-cf2-sem-proof", "labels-hidden");
      if (global.document.body) {
        global.document.body.setAttribute("data-cf2-sem-proof", "labels-hidden");
      }
    }
  } catch (e) {
    /* review-only */
  }

  global.CartFlowSemanticVisualV1 = {
    VERSION: VERSION,
    projectHomeSurface: projectHomeSurface,
    projectWorkspace: projectWorkspace,
    clauseRoles: clauseRoles,
    densityState: densityState,
    massState: massState,
    tensionState: tensionState,
    coreSilenceHome: coreSilenceHome,
    coreSilenceWorkspace: coreSilenceWorkspace,
  };
})(typeof window !== "undefined" ? window : globalThis);
