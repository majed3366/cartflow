/**
 * Cart Workspace Render Controller V1 — sole P4 owner for Workspace composition.
 *
 * Input: WorkspaceProjection only.
 * Must never: classify ownership, evaluate admission, infer VIP, derive counters,
 * reorder by business logic.
 *
 * Desktop and mobile consume the identical projection object.
 */
(function (global) {
  "use strict";

  var lastProjection = null;
  var lastPaintVersion = null;

  function versionApi() {
    return global.CartWorkspaceProjectionVersionV1;
  }

  function gridApi() {
    return global.CartWorkspaceGridV1;
  }

  /**
   * Apply projection envelope to a host element.
   * @param {HTMLElement|null} host
   * @param {object} projection
   * @returns {{ painted: boolean, compare: object }}
   */
  function applyProjection(host, projection) {
    var cmpApi = versionApi();
    var compare = cmpApi
      ? cmpApi.compareProjectionEnvelope(lastProjection, projection)
      : { decision: "ACCEPT", should_paint: true, reason: "no_version_module" };

    if (!compare.should_paint) {
      return { painted: false, compare: compare, last_version: lastPaintVersion };
    }

    var grid = gridApi();
    var html = grid ? grid.renderGridHtml(projection) : "";
    if (host && typeof host.innerHTML !== "undefined") {
      host.innerHTML = html;
      host.setAttribute(
        "data-cw-projection-version",
        String(projection && projection.projection_version != null ? projection.projection_version : "")
      );
      host.setAttribute("data-cw-quiet", projection && projection.quiet ? "1" : "0");
    }

    lastProjection = projection;
    lastPaintVersion =
      projection && projection.projection_version != null
        ? Number(projection.projection_version)
        : null;

    return { painted: true, compare: compare, last_version: lastPaintVersion };
  }

  function getLastProjection() {
    return lastProjection;
  }

  function resetForTests() {
    lastProjection = null;
    lastPaintVersion = null;
  }

  /**
   * Structural audit — proves renderer has no business-rule hooks.
   * Returns forbidden symbol hits if someone later adds them (tests).
   */
  function forbiddenBusinessLogicAudit(sourceText) {
    // Patterns split so this file itself does not contain forbidden literals for static scans.
    var parts = [
      ["evaluate", "_admission"],
      ["matrix", "_row"],
      ["apply", "_transition"],
      ["override", "_eligible"],
    ];
    var hits = [];
    var text = String(sourceText || "");
    parts.forEach(function (p) {
      var token = p.join("");
      if (text.indexOf(token) !== -1) hits.push(token);
    });
    if (/\bR0[0-9]\b/.test(text)) hits.push("R0x");
    return hits;
  }

  global.CartWorkspaceRenderControllerV1 = {
    applyProjection: applyProjection,
    getLastProjection: getLastProjection,
    resetForTests: resetForTests,
    forbiddenBusinessLogicAudit: forbiddenBusinessLogicAudit,
  };
})(typeof window !== "undefined" ? window : globalThis);
